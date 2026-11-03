"""
Checks the extra seed content (practice/seed_content): every code claim in the
model answers is executed, and every topic has 3-5 activities at every Bloom
level so mastery-based progression always has a different item to offer.
"""

import contextlib
import io
from collections import Counter

from django.core.management import call_command
from django.test import SimpleTestCase, TestCase

from practice.management.commands import seed_activities
from practice.models import Activity, Topic
from practice.seed_content import CLAIMS, EXTRA_ACTIVITIES

MIN_PER_CELL = 3
MAX_PER_CELL = 5


def _run(source):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        exec(source, {})
    return out.getvalue().strip().splitlines()


class SeedContentClaimTests(SimpleTestCase):
    def test_claims_exist(self):
        self.assertGreater(len(CLAIMS), 50)

    def test_every_claim_is_true(self):
        for source, printed, raises in CLAIMS:
            with self.subTest(source=source[:70]):
                if raises:
                    out = io.StringIO()
                    with self.assertRaises(Exception) as ctx, contextlib.redirect_stdout(out):
                        exec(source, {})
                    self.assertEqual(type(ctx.exception).__name__, raises)
                    self.assertEqual(tuple(out.getvalue().strip().splitlines()), printed)
                else:
                    self.assertEqual(tuple(_run(source)), printed)


class SeedContentCoverageTests(SimpleTestCase):
    def test_every_topic_and_level_has_three_to_five_activities(self):
        counts = Counter((a["topic"], a["bloom_level"]) for a in seed_activities.ACTIVITIES)
        for topic in (t["slug"] for t in seed_activities.TOPICS):
            for level in range(1, 7):
                with self.subTest(topic=topic, level=level):
                    n = counts[(topic, level)]
                    self.assertGreaterEqual(n, MIN_PER_CELL)
                    self.assertLessEqual(n, MAX_PER_CELL)

    def test_titles_are_unique_within_a_topic_and_type(self):
        seen = Counter(
            (a["topic"], a["question_type"], a["title"]) for a in seed_activities.ACTIVITIES
        )
        self.assertEqual([k for k, v in seen.items() if v > 1], [])

    def test_extra_activities_are_appended_after_the_originals(self):
        originals = seed_activities.ACTIVITIES[: -len(EXTRA_ACTIVITIES)]
        self.assertEqual(len(originals), 48)

    def test_extra_items_have_the_loader_required_fields(self):
        required = {
            "topic", "question_type", "title", "bloom_level", "block_level",
            "estimated_minutes", "stem", "model_explanation", "success_criteria",
            "misconceptions", "hint_text", "follow_up_idea", "choices", "correct_choice",
        }
        for item in EXTRA_ACTIVITIES:
            with self.subTest(title=item["title"]):
                self.assertFalse(required - set(item))
                self.assertTrue(item["misconceptions"])

    def test_multiple_choice_items_have_four_distinct_options(self):
        for item in EXTRA_ACTIVITIES:
            if item["choices"]:
                texts = [c["text"] for c in item["choices"]]
                with self.subTest(title=item["title"]):
                    self.assertEqual(len(texts), 4)
                    self.assertEqual(len(set(texts)), 4)

    def test_open_items_have_concepts_with_keywords(self):
        for item in EXTRA_ACTIVITIES:
            if not item["choices"]:
                with self.subTest(title=item["title"]):
                    self.assertGreaterEqual(len(item["expected_concepts"]), 3)
                    for concept in item["expected_concepts"]:
                        self.assertTrue(concept["keywords"])

    def test_ai_suggestion_items_state_a_decision(self):
        for item in EXTRA_ACTIVITIES:
            if item["question_type"] == "ai-suggestion":
                with self.subTest(title=item["title"]):
                    self.assertIn(item["correct_choice"], ("accept", "reject"))
                    self.assertTrue(item["ai_suggestion"])

    def test_accept_and_reject_both_occur_across_the_course(self):
        # Learners must not be able to guess "always reject".
        decisions = Counter(
            a["correct_choice"]
            for a in seed_activities.ACTIVITIES
            if a["question_type"] == "ai-suggestion"
        )
        self.assertGreaterEqual(decisions["accept"], 4)
        self.assertGreaterEqual(decisions["reject"], 4)


class SeedContentLoadTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        with contextlib.redirect_stdout(io.StringIO()):
            call_command("seed_activities")

    def test_database_has_the_depth_after_seeding(self):
        for topic in Topic.objects.all():
            for level in range(1, 7):
                with self.subTest(topic=topic.slug, level=level):
                    n = Activity.objects.filter(topic=topic, bloom_level=level).count()
                    self.assertTrue(MIN_PER_CELL <= n <= MAX_PER_CELL)

    def test_model_answers_name_their_own_concepts(self):
        """The first keyword of every concept must match whole-word, so a full answer scores 1."""
        from practice.feedback.keyword import KeywordFeedbackService

        service = KeywordFeedbackService()
        titles = [i["title"] for i in EXTRA_ACTIVITIES if i["expected_concepts"]]
        for activity in Activity.objects.filter(title__in=titles):
            words = [c["keywords"][0] for c in activity.expected_concepts]
            with self.subTest(title=activity.title):
                self.assertEqual(service.evaluate(activity, " ".join(words)).score, 1.0)
                self.assertLess(service.evaluate(activity, "I am not sure.").score, 0.6)

    def test_seeding_twice_changes_nothing(self):
        before = Activity.objects.count()
        with contextlib.redirect_stdout(io.StringIO()):
            call_command("seed_activities")
        self.assertEqual(Activity.objects.count(), before)
