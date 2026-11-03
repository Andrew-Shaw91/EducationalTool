"""
Integration tests for per-topic mastery progression: the real views, the
persistence, the research logging and export, the privacy switches and the interface.

The rules in play:
- Activities are grouped by topic and Bloom level.
- A wrong answer keeps the learner in the same topic and level, with a different
  unseen activity where one exists.
- A level is passed after PROMOTE_AFTER successes in a row.
- The next topic starts only when every level of the current topic is passed.
"""

import csv
import io
import itertools
from unittest import mock

from django.conf import settings
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from practice import progression
from practice.models import Activity, Topic
from research import progress as learner_progress
from research.management.commands.export_research_data import COLUMNS
from research.models import Attempt, LearnerProgress, Participant, ProgressionEvent


def is_gradable(a):
    """Can the tests answer this activity both right and wrong, exactly?"""
    return (
        a.is_matching
        or a.question_type.slug == "ai-suggestion"
        or (a.is_choice_based and bool(a.correct_choice))
        or (not a.is_choice_based and bool(a.expected_concepts))
    )


def gradable(level, topic=None):
    """Activities at `level` (in `topic`, if given) that the tests can answer right or wrong."""
    activities = Activity.objects.filter(bloom_level=level).select_related("question_type", "topic")
    if topic is not None:
        activities = activities.filter(topic=topic)
    return [a for a in activities if is_gradable(a)]


class ProgressTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_activities", verbosity=0)
        cls.topics = list(Topic.objects.all())
        cls.topic, cls.other = cls.topics[0], cls.topics[1]

    def answer(self, activity, correct=True):
        """Submit a right or wrong answer to a gradable activity."""
        if activity.is_matching:
            keys = activity.match_answer_keys()
            data = {f"match_{i}": k for i, k in enumerate(keys)} if correct else {}
        elif activity.question_type.slug == "ai-suggestion":
            right = activity.correct_choice.lower()
            decision = right if correct else ("reject" if right == "accept" else "accept")
            data = {"ai_decision": decision, "reasoning": "Because of what it does."}
        elif activity.is_choice_based:
            key = activity.correct_choice
            if not correct:
                key = next(c["key"] for c in activity.choices if c["key"] != key)
            data = {"choice": key}
        else:
            # Open answer: name every target idea, or say nothing useful.
            words = [c["keywords"][0] for c in activity.expected_concepts if c.get("keywords")]
            data = {"free_text": " ".join(words) if correct else "I am not sure."}
        return self.client.post(activity.get_absolute_url(), data)

    def run_outcomes(self, level, outcomes, topic=None):
        """
        Answer activities at `level` in `topic` with a sequence of True/False results.
        Activities are reused in turn once the (small) pool is used up.
        """
        topic = topic or self.topic
        pool = gradable(level, topic)
        self.assertGreaterEqual(len(pool), 3, f"{topic.slug} L{level}")
        response = None
        for activity, ok in zip(itertools.cycle(pool), outcomes):
            response = self.answer(activity, ok)
        return response

    def master(self, topic, up_to=6):
        """Pass levels 1..up_to of a topic (three successes each); returns the last response."""
        response = None
        for level in range(1, up_to + 1):
            response = self.run_outcomes(level, [True, True, True], topic)
        return response

    def row(self, topic=None):
        return LearnerProgress.objects.get(topic=topic or self.topic)

    def target(self, **params):
        response = self.client.get(reverse("practice:next"), params)
        self.assertEqual(response.status_code, 302, response.content[:200])
        return Activity.objects.select_related("topic").get(pk=int(response.url.rstrip("/").split("/")[-1]))


class ContentAvailabilityTests(ProgressTestCase):
    def test_every_topic_and_level_can_be_driven_by_these_tests(self):
        for topic in self.topics:
            for level in range(1, 7):
                self.assertGreaterEqual(len(gradable(level, topic)), 3, f"{topic.slug} L{level}")


class PromotionFlowTests(ProgressTestCase):
    def test_new_learner_starts_at_level_one_with_nothing_stored(self):
        response = self.client.get(reverse("practice:home"))
        self.assertContains(response, "Level 1")
        self.assertContains(response, "0 / 3")
        self.assertEqual(response.context["progress"].topic_name, self.topic.name)
        self.assertEqual(LearnerProgress.objects.count(), 0)
        self.assertEqual(Participant.objects.count(), 0)

    def test_three_successes_pass_the_level_and_persist(self):
        self.run_outcomes(1, [True, True, True])
        row = self.row()
        self.assertEqual(row.level, 2)
        self.assertEqual((row.consecutive_successes, row.consecutive_failures), (0, 0))
        self.assertEqual((row.total_promotions, row.total_demotions), (1, 0))
        self.assertFalse(row.in_remediation)
        self.assertFalse(row.completed)
        self.assertIsNotNone(row.updated_at)

    def test_progress_toward_the_next_level_is_shown(self):
        self.run_outcomes(1, [True, True])
        home = self.client.get(reverse("practice:home"))
        self.assertContains(home, "2 / 3")
        self.assertContains(home, "successful activities in a row")
        self.assertContains(home, "Level 2 (Comprehension)")

    def test_feedback_page_announces_a_level_up(self):
        response = self.run_outcomes(1, [True, True, True])
        self.assertContains(response, "Level up")
        self.assertContains(response, "Level 2 (Comprehension)")
        self.assertEqual(response.context["update"].event, progression.Event.PROMOTION)

    def test_two_successes_do_not_announce_anything(self):
        response = self.run_outcomes(1, [True, True])
        self.assertNotContains(response, "Level up")
        self.assertContains(response, "2 / 3")

    def test_failure_resets_the_success_streak(self):
        self.run_outcomes(1, [True, True, False, True, True])
        row = self.row()
        self.assertEqual(row.level, 1)
        self.assertEqual((row.consecutive_successes, row.consecutive_failures), (2, 0))

    def test_success_resets_the_failure_streak(self):
        self.run_outcomes(1, [False, True, False])
        row = self.row()
        self.assertEqual(row.level, 1)
        self.assertEqual(row.consecutive_failures, 1)

    def test_lowest_level_cannot_be_demoted_further(self):
        self.run_outcomes(1, [False, False, False, False])
        row = self.row()
        self.assertEqual((row.level, row.total_demotions), (1, 0))
        self.assertEqual(ProgressionEvent.objects.count(), 0)


class SameTopicAndLevelTests(ProgressTestCase):
    """The behaviour the curriculum depends on: mastery before moving on."""

    def test_a_wrong_answer_gives_a_different_unseen_activity_in_the_same_topic_and_level(self):
        first = gradable(2, self.topic)[0]
        self.run_outcomes(1, [True, True, True])  # reach level 2
        response = self.answer(first, correct=False)
        nxt = response.context["recommended"]
        self.assertEqual((nxt.topic_id, nxt.bloom_level), (self.topic.pk, 2))
        self.assertNotEqual(nxt.pk, first.pk)
        self.assertFalse(response.context["moves_to_new_topic"])
        self.assertContains(response, f"Another activity in {self.topic.name}, Level 2")

    def test_serving_through_next_never_leaves_the_topic_and_level_after_misses(self):
        self.run_outcomes(1, [True, True, True])  # now at level 2
        served = []
        # Alternating misses and successes never reaches two misses in a row, so
        # the level stays put, and so must everything the learner is served.
        for ok in [False, True, False, True, False, True]:
            activity = self.target()
            served.append(activity)
            self.answer(activity, correct=ok)
        self.assertEqual({(a.topic_id, a.bloom_level) for a in served}, {(self.topic.pk, 2)})
        self.assertEqual(self.row().level, 2)

    def test_every_activity_in_the_cell_is_offered_before_any_repeat(self):
        pool = Activity.objects.filter(topic=self.topic, bloom_level=1)
        seen = []
        # Misses at the lowest level cannot demote, so this isolates selection.
        for _ in range(pool.count()):
            activity = self.target()
            self.assertEqual((activity.topic_id, activity.bloom_level), (self.topic.pk, 1))
            self.assertNotIn(activity.pk, seen)
            seen.append(activity.pk)
            self.answer(activity, correct=False)
        self.assertEqual(sorted(seen), sorted(pool.values_list("pk", flat=True)))
        # The cell is exhausted: the next one repeats the least recently seen item.
        again = self.target()
        self.assertEqual(again.pk, seen[0])

    def test_a_correct_answer_does_not_leave_the_level_until_the_streak_is_met(self):
        response = self.run_outcomes(1, [True])
        nxt = response.context["recommended"]
        self.assertEqual((nxt.topic_id, nxt.bloom_level), (self.topic.pk, 1))

    def test_passing_a_level_moves_to_the_next_level_of_the_same_topic(self):
        response = self.run_outcomes(1, [True, True, True])
        nxt = response.context["recommended"]
        self.assertEqual((nxt.topic_id, nxt.bloom_level), (self.topic.pk, 2))

    def test_the_topic_is_not_complete_until_all_six_levels_are_passed(self):
        response = self.master(self.topic, up_to=5)
        self.assertEqual(self.row().level, 6)
        self.assertFalse(self.row().completed)
        nxt = response.context["recommended"]
        self.assertEqual((nxt.topic_id, nxt.bloom_level), (self.topic.pk, 6))
        self.assertEqual(self.target().topic_id, self.topic.pk)
        # Two of the three successes needed at level 6 are not enough either.
        self.run_outcomes(6, [True, True], self.topic)
        self.assertFalse(self.row().completed)
        self.assertEqual(self.target().topic_id, self.topic.pk)

    def test_completing_every_level_moves_to_the_next_topic(self):
        response = self.master(self.topic)
        row = self.row()
        self.assertTrue(row.completed)
        self.assertEqual(row.level, 6)
        self.assertEqual(response.context["update"].event, progression.Event.TOPIC_COMPLETE)
        self.assertContains(response, f"{self.topic.name} completed")
        nxt = response.context["recommended"]
        self.assertEqual((nxt.topic_id, nxt.bloom_level), (self.other.pk, 1))
        self.assertTrue(response.context["moves_to_new_topic"])
        self.assertContains(response, f"Next topic: {self.other.name}")
        landing = self.target()
        self.assertEqual((landing.topic_id, landing.bloom_level), (self.other.pk, 1))

    def test_each_topic_keeps_its_own_level(self):
        self.run_outcomes(1, [True, True, True], self.topic)
        self.run_outcomes(1, [True], self.other)
        self.assertEqual(self.row(self.topic).level, 2)
        self.assertEqual((self.row(self.other).level, self.row(self.other).consecutive_successes), (1, 1))
        self.assertEqual(self.target(topic=self.topic.slug).bloom_level, 2)
        self.assertEqual(self.target(topic=self.other.slug).bloom_level, 1)

    def test_a_completed_topic_is_frozen_and_stays_completed(self):
        self.master(self.topic)
        fields = [f for f in ("level", "consecutive_successes", "consecutive_failures",
                              "total_promotions", "total_demotions", "in_remediation", "completed")]
        before = LearnerProgress.objects.values(*fields).get(topic=self.topic)
        response = self.run_outcomes(3, [False, False, False], self.topic)
        self.assertEqual(LearnerProgress.objects.values(*fields).get(topic=self.topic), before)
        self.assertContains(response, "already completed")
        last = Attempt.objects.order_by("id").last()
        self.assertFalse(last.counted_for_progress)

    def test_all_topics_completed(self):
        for topic in self.topics:
            self.master(topic)
        self.assertTrue(all(r.completed for r in LearnerProgress.objects.all()))
        self.assertRedirects(self.client.get(reverse("practice:next")), reverse("practice:topics"))
        home = self.client.get(reverse("practice:home"))
        self.assertTrue(home.context["all_topics_complete"])
        self.assertContains(home, "completed every topic")

    def test_after_the_last_topic_the_feedback_says_so(self):
        for topic in self.topics[:-1]:
            self.master(topic)
        response = self.master(self.topics[-1])
        self.assertIsNone(response.context["recommended"])
        self.assertTrue(response.context["all_topics_complete"])
        self.assertContains(response, "completed every topic")

    def test_skipped_topics_are_revisited_after_the_last_one(self):
        last = self.topics[-1]
        self.master(last)
        # Having finished the last topic the learner is sent back to the first unfinished one.
        self.assertEqual(self.target().topic_id, self.topics[0].pk)

    def test_starting_in_a_later_topic_continues_there(self):
        self.run_outcomes(1, [True], self.other)
        self.assertEqual(self.target().topic_id, self.other.pk)


class DemotionAndRemediationFlowTests(ProgressTestCase):
    def reach_level_two(self):
        self.run_outcomes(1, [True, True, True])

    def test_two_failures_step_back_within_the_topic_and_the_notice_says_so(self):
        self.reach_level_two()
        response = self.run_outcomes(2, [False, False])
        row = self.row()
        self.assertEqual(row.level, 1)
        self.assertEqual(row.total_demotions, 1)
        self.assertTrue(row.in_remediation)
        self.assertContains(response, "Stepping back to Level 1")

    def test_the_step_back_stays_in_the_same_topic(self):
        self.reach_level_two()
        response = self.run_outcomes(2, [False, False])
        nxt = response.context["recommended"]
        self.assertEqual((nxt.topic_id, nxt.bloom_level), (self.topic.pk, 1))
        self.assertContains(response, f"Another activity in {self.topic.name}, Level 1")

    def test_a_single_correct_answer_does_not_pass_the_level_again(self):
        self.reach_level_two()
        self.run_outcomes(2, [False, False])
        self.run_outcomes(1, [True])
        row = self.row()
        self.assertEqual(row.level, 1)
        self.assertTrue(row.in_remediation)
        self.assertEqual(row.consecutive_successes, 1)

    def test_competency_restores_the_higher_level(self):
        self.reach_level_two()
        self.run_outcomes(2, [False, False])
        self.run_outcomes(1, [True, True, True])
        row = self.row()
        self.assertEqual(row.level, 2)
        self.assertFalse(row.in_remediation)
        self.assertEqual((row.total_promotions, row.total_demotions), (2, 1))

    def test_remediation_message_is_shown(self):
        self.reach_level_two()
        self.run_outcomes(2, [False, False])
        home = self.client.get(reverse("practice:home"))
        self.assertContains(home, "Building back up")
        self.assertContains(home, "single correct answer is not enough")

    @override_settings(ADAPTIVE={**settings.ADAPTIVE, "DEMOTE_AFTER": 0})
    def test_with_stepping_back_switched_off_a_miss_keeps_the_same_level(self):
        self.reach_level_two()
        response = self.run_outcomes(2, [False, False, False, False])
        row = self.row()
        self.assertEqual((row.level, row.total_demotions), (2, 0))
        nxt = response.context["recommended"]
        self.assertEqual((nxt.topic_id, nxt.bloom_level), (self.topic.pk, 2))
        self.assertNotContains(response, "Stepping back")
        self.assertNotContains(self.client.get(reverse("practice:home")), "misses in a row")


class OpenAnswerTests(ProgressTestCase):
    """Level 5 is all open answers: success comes from the concept score."""

    def at_level(self, level, topic=None):
        participant = Participant.objects.create()
        LearnerProgress.objects.create(participant=participant, topic=topic or self.topic, level=level)
        session = self.client.session
        session["participant_code"] = participant.code
        session.save()

    def open_items(self, level):
        return [a for a in gradable(level, self.topic) if not a.is_choice_based and not a.is_matching]

    def test_level_five_has_open_items(self):
        self.assertGreaterEqual(len(self.open_items(5)), 3)

    def test_strong_open_answers_pass_the_level(self):
        self.at_level(5)
        for activity in self.open_items(5)[:3]:
            response = self.answer(activity, True)
        self.assertEqual(response.context["assessment"].is_correct, None)
        self.assertEqual(self.row().level, 6)
        self.assertEqual(Attempt.objects.first().outcome, "success")

    def test_weak_open_answers_step_back(self):
        self.at_level(5)
        for activity in self.open_items(5)[:2]:
            self.answer(activity, False)
        row = self.row()
        self.assertEqual((row.level, row.total_demotions), (4, 1))
        self.assertEqual(Attempt.objects.first().outcome, "failure")

    @override_settings(ADAPTIVE={**settings.ADAPTIVE, "OPEN_SUCCESS_SCORE": 1.0})
    def test_the_open_answer_threshold_is_configurable(self):
        self.at_level(5)
        activity = next(a for a in self.open_items(5) if len(a.expected_concepts) > 1)
        words = [c["keywords"][0] for c in activity.expected_concepts][:-1]
        self.client.post(activity.get_absolute_url(), {"free_text": " ".join(words)})
        self.assertEqual(Attempt.objects.get().outcome, "failure")


class OffLevelTests(ProgressTestCase):
    """Practice at a level other than the learner's level in that topic is free practice."""

    def test_activity_from_another_level_does_not_change_progress(self):
        for activity in gradable(3, self.topic)[:3]:
            self.answer(activity, True)
        self.assertFalse(LearnerProgress.objects.filter(consecutive_successes__gt=0).exists())
        row = self.row()
        self.assertEqual((row.level, row.consecutive_successes), (1, 0))
        attempts = Attempt.objects.all()
        self.assertTrue(all(a.counted_for_progress is False for a in attempts))
        self.assertTrue(all(a.level_at_start == 1 and a.level_at_end == 1 for a in attempts))

    def test_off_level_page_explains_itself(self):
        item = gradable(4, self.topic)[0]
        response = self.client.get(item.get_absolute_url())
        self.assertContains(response, "will not count towards moving up or down")
        response = self.answer(item, False)
        self.assertContains(response, "did not count towards moving up or down")

    def test_a_different_topic_is_tracked_separately_and_counts_there(self):
        # Level 1 in another topic counts for THAT topic, not for the first one.
        self.run_outcomes(1, [True, True], self.other)
        self.assertEqual(self.row(self.other).consecutive_successes, 2)
        self.assertFalse(LearnerProgress.objects.filter(topic=self.topic).exists())

    @override_settings(ADAPTIVE={**settings.ADAPTIVE, "COUNT_OFF_LEVEL": True})
    def test_off_level_attempts_count_when_configured(self):
        for activity in gradable(3, self.topic)[:3]:
            self.answer(activity, True)
        self.assertEqual(self.row().level, 2)


class ResearchLoggingTests(ProgressTestCase):
    def test_attempt_records_levels_outcome_and_streaks(self):
        self.run_outcomes(1, [True, False])
        first, second = Attempt.objects.order_by("id")
        self.assertEqual((first.level_at_start, first.level_at_end), (1, 1))
        self.assertEqual((first.outcome, first.counted_for_progress), ("success", True))
        self.assertEqual((first.successes_after, first.failures_after), (1, 0))
        self.assertEqual((second.outcome, second.successes_after, second.failures_after), ("failure", 0, 1))

    def test_level_at_start_and_end_differ_on_the_promoting_attempt(self):
        self.run_outcomes(1, [True, True, True])
        last = Attempt.objects.order_by("id").last()
        self.assertEqual((last.level_at_start, last.level_at_end), (1, 2))
        self.assertEqual((last.successes_after, last.failures_after), (0, 0))
        self.assertEqual(last.progress_event, "promotion")

    def test_promotion_event_is_logged_once_with_context(self):
        self.run_outcomes(1, [True, True, True])
        (event,) = ProgressionEvent.objects.all()
        last = Attempt.objects.order_by("id").last()
        self.assertEqual(event.kind, "promotion")
        self.assertEqual((event.level_before, event.level_after), (1, 2))
        self.assertEqual(event.attempt, last)
        self.assertEqual(event.activity, last.activity)
        self.assertEqual(event.participant, last.participant)
        self.assertIsNotNone(event.created_at)

    def test_demotion_event_is_logged(self):
        self.run_outcomes(1, [True, True, True])
        self.run_outcomes(2, [False, False])
        kinds = list(ProgressionEvent.objects.values_list("kind", "level_before", "level_after"))
        self.assertEqual(kinds, [("promotion", 1, 2), ("demotion", 2, 1)])

    def test_topic_completion_is_logged(self):
        self.master(self.topic)
        kinds = list(ProgressionEvent.objects.values_list("kind", flat=True))
        self.assertEqual(kinds, ["promotion"] * 5 + ["topic_complete"])
        done = ProgressionEvent.objects.get(kind="topic_complete")
        self.assertEqual((done.level_before, done.level_after), (6, 6))
        self.assertEqual(done.activity.topic, self.topic)
        self.assertEqual(Attempt.objects.order_by("id").last().progress_event, "topic_complete")

    def test_no_event_without_a_level_change(self):
        self.run_outcomes(1, [True, False, True])
        self.assertEqual(ProgressionEvent.objects.count(), 0)

    def test_history_can_be_reconstructed_in_order(self):
        self.run_outcomes(1, [True, True, True])
        self.run_outcomes(2, [True, False, False])
        levels = list(Attempt.objects.order_by("id").values_list("level_at_start", "level_at_end"))
        self.assertEqual(levels, [(1, 1), (1, 1), (1, 2), (2, 2), (2, 2), (2, 1)])
        for earlier, later in zip(levels, levels[1:]):
            self.assertEqual(earlier[1], later[0])

    @override_settings(RESEARCH={**settings.RESEARCH, "STORE_TIMESTAMPS": False})
    def test_timestamps_respect_the_privacy_switch(self):
        self.run_outcomes(1, [True, True, True])
        self.assertIsNone(self.row().updated_at)
        self.assertIsNone(ProgressionEvent.objects.get().created_at)
        self.assertIsNone(Attempt.objects.first().created_at)


class PersistenceTests(ProgressTestCase):
    def test_state_survives_between_requests(self):
        self.run_outcomes(1, [True, True])
        self.assertEqual(self.row().consecutive_successes, 2)
        home = self.client.get(reverse("practice:home"))
        self.assertEqual(home.context["progress"].successes, 2)
        self.run_outcomes(1, [True])
        self.assertEqual(self.row().level, 2)

    def test_there_is_one_row_per_participant_and_topic(self):
        self.run_outcomes(1, [True, True, True], self.topic)
        self.run_outcomes(1, [True], self.other)
        self.assertEqual(LearnerProgress.objects.count(), 2)
        self.assertEqual(LearnerProgress.objects.values("participant").distinct().count(), 1)

    def test_each_participant_has_their_own_state(self):
        self.run_outcomes(1, [True, True, True])
        self.client.cookies.clear()
        self.assertEqual(self.client.get(reverse("practice:home")).context["progress"].level, 1)
        self.run_outcomes(1, [True])
        self.assertEqual(sorted(LearnerProgress.objects.values_list("level", flat=True)), [1, 2])

    def test_a_failed_write_changes_nothing(self):
        """State and log commit together: if logging fails, the level does not move."""
        self.run_outcomes(1, [True, True])
        self.client.raise_request_exception = False
        with mock.patch("research.recording.Attempt.objects.create", side_effect=RuntimeError("boom")):
            response = self.answer(gradable(1, self.topic)[2], True)
        self.assertEqual(response.status_code, 500)
        row = self.row()
        self.assertEqual((row.level, row.consecutive_successes), (1, 2))
        self.assertEqual(Attempt.objects.count(), 2)


class PrivacyAndSwitchTests(ProgressTestCase):
    @override_settings(RESEARCH={**settings.RESEARCH, "ANALYTICS_ENABLED": False})
    def test_progression_works_with_analytics_off_and_stores_nothing(self):
        self.run_outcomes(1, [True, True, True])
        home = self.client.get(reverse("practice:home"))
        self.assertEqual(home.context["progress"].level, 2)
        self.assertEqual(
            (Attempt.objects.count(), Participant.objects.count(),
             LearnerProgress.objects.count(), ProgressionEvent.objects.count()),
            (0, 0, 0, 0),
        )

    @override_settings(RESEARCH={**settings.RESEARCH, "ANALYTICS_ENABLED": False})
    def test_session_state_is_kept_per_topic(self):
        self.run_outcomes(1, [True, True, True], self.topic)
        self.run_outcomes(1, [True], self.other)
        stored = self.client.session[learner_progress.SESSION_KEY]
        self.assertEqual(set(stored), {str(self.topic.pk), str(self.other.pk)})
        self.assertEqual(stored[str(self.topic.pk)]["level"], 2)
        self.assertEqual(stored[str(self.other.pk)]["consecutive_successes"], 1)

    @override_settings(RESEARCH={**settings.RESEARCH, "ANALYTICS_ENABLED": False})
    def test_topics_complete_and_advance_with_analytics_off(self):
        response = self.master(self.topic)
        self.assertTrue(self.client.session[learner_progress.SESSION_KEY][str(self.topic.pk)]["completed"])
        self.assertEqual(response.context["recommended"].topic_id, self.other.pk)
        self.assertEqual(Attempt.objects.count(), 0)

    @override_settings(RESEARCH={**settings.RESEARCH, "ANALYTICS_ENABLED": False})
    def test_session_state_is_tolerant_of_tampering(self):
        session = self.client.session
        session[learner_progress.SESSION_KEY] = {
            str(self.topic.pk): {"level": 99, "consecutive_successes": "x"},
            "not-a-topic": {"level": 3},
        }
        session.save()
        home = self.client.get(reverse("practice:home"))
        self.assertEqual(home.context["progress"].level, 1)
        # The old course-wide shape (before topics) is ignored rather than trusted.
        session[learner_progress.SESSION_KEY] = {"level": 5, "consecutive_successes": 2}
        session.save()
        self.assertEqual(self.client.get(reverse("practice:home")).context["progress"].level, 1)

    @override_settings(ADAPTIVE={**settings.ADAPTIVE, "ENABLED": False})
    def test_disabled_mechanism_leaves_everything_as_before(self):
        response = self.run_outcomes(1, [True, True, True])
        self.assertNotContains(response, "Your level")
        self.assertNotIn("update", response.context)
        self.assertEqual(LearnerProgress.objects.count(), 0)
        self.assertEqual(ProgressionEvent.objects.count(), 0)
        attempt = Attempt.objects.first()
        self.assertIsNone(attempt.level_at_start)
        self.assertEqual(attempt.outcome, "")
        self.assertEqual(attempt.progress_event, "")
        home = self.client.get(reverse("practice:home"))
        self.assertNotContains(home, "Start learning")
        self.assertRedirects(self.client.get(reverse("practice:next")), reverse("practice:topics"))

    @override_settings(ADAPTIVE={**settings.ADAPTIVE, "PROMOTE_AFTER": 2})
    def test_thresholds_come_from_settings(self):
        self.run_outcomes(1, [True, True])
        self.assertEqual(self.row().level, 2)
        self.assertContains(self.client.get(reverse("practice:home")), "0 / 2")


class NextActivityViewTests(ProgressTestCase):
    def test_new_learner_is_sent_to_a_level_one_activity_in_the_first_topic(self):
        activity = self.target()
        self.assertEqual((activity.topic_id, activity.bloom_level), (self.topic.pk, 1))

    def test_a_learner_who_passed_level_one_is_sent_to_level_two_of_the_same_topic(self):
        self.run_outcomes(1, [True, True, True])
        activity = self.target()
        self.assertEqual((activity.topic_id, activity.bloom_level), (self.topic.pk, 2))

    def test_visiting_next_never_changes_state(self):
        self.run_outcomes(1, [True, True])
        before = LearnerProgress.objects.values().get()
        for _ in range(5):
            self.client.get(reverse("practice:next"))
        self.assertEqual(LearnerProgress.objects.values().get(), before)
        self.assertEqual(Attempt.objects.count(), 2)

    def test_next_moves_on_after_an_attempt(self):
        first = self.target()
        self.answer(first, True)
        self.assertNotEqual(self.target().pk, first.pk)

    def test_topic_parameter_is_respected_and_falls_back_safely(self):
        activity = self.target(topic=self.other.slug)
        self.assertEqual((activity.topic_id, activity.bloom_level), (self.other.pk, 1))
        unknown = self.client.get(reverse("practice:next"), {"topic": "no-such-topic"})
        self.assertEqual(unknown.status_code, 302)

    def test_post_is_not_allowed(self):
        self.assertEqual(self.client.post(reverse("practice:next")).status_code, 405)

    def test_home_offers_learning_at_my_level(self):
        home = self.client.get(reverse("practice:home"))
        self.assertContains(home, reverse("practice:next"))
        self.assertContains(home, "Start learning")
        self.run_outcomes(1, [True])
        self.assertContains(self.client.get(reverse("practice:home")), "Continue learning")

    def test_nothing_at_the_level_redirects_to_topics(self):
        Activity.objects.filter(topic=self.topic, bloom_level=1).delete()
        self.assertRedirects(self.client.get(reverse("practice:next")), reverse("practice:topics"))

    def test_topics_page_shows_each_topics_standing(self):
        self.master(self.topic)
        self.run_outcomes(1, [True, True, True], self.other)
        page = self.client.get(reverse("practice:topics"))
        self.assertContains(page, "Completed")
        self.assertContains(page, "Not started")
        rows = {r["topic"].pk: r for r in page.context["rows"]}
        self.assertTrue(rows[self.topic.pk]["view"].completed)
        self.assertEqual(rows[self.other.pk]["view"].level, 2)
        self.assertFalse(rows[self.topics[2].pk]["started"])


class DeterminismThroughTheViewsTests(ProgressTestCase):
    def trajectory(self):
        self.client.cookies.clear()
        steps = []
        for ok in [True, True, True, True, False, False, True, True, True, True, True]:
            activity = self.target()
            if not is_gradable(activity):
                continue
            response = self.answer(activity, ok)
            steps.append((activity.pk, response.context["progress"].level))
        return steps

    def test_same_answers_give_the_same_path(self):
        self.assertEqual(self.trajectory(), self.trajectory())


class ExportTests(ProgressTestCase):
    def export(self, **kwargs):
        out = io.StringIO()
        call_command("export_research_data", stdout=out, **kwargs)
        return list(csv.DictReader(io.StringIO(out.getvalue())))

    def test_attempt_export_includes_progression_columns(self):
        self.run_outcomes(1, [True, True, True])
        rows = self.export()
        self.assertEqual(len(rows), 3)
        for column in ("level_at_start", "level_at_end", "outcome", "counted_for_progress",
                       "successes_after", "failures_after", "progression_event"):
            self.assertIn(column, rows[0])
        last = rows[-1]
        self.assertEqual((last["level_at_start"], last["level_at_end"]), ("1", "2"))
        self.assertEqual(last["progression_event"], "promotion")
        self.assertEqual((rows[0]["outcome"], rows[0]["counted_for_progress"]), ("success", "1"))
        self.assertEqual(rows[0]["progression_event"], "")

    def test_topic_completion_is_exported(self):
        self.master(self.topic)
        self.assertEqual(self.export()[-1]["progression_event"], "topic_complete")

    def test_earlier_columns_keep_their_positions(self):
        self.assertEqual(COLUMNS[0], "participant")
        self.assertEqual(COLUMNS[17], "created_at")
        self.assertEqual(COLUMNS[18], "level_at_start")

    def test_events_table(self):
        self.run_outcomes(1, [True, True, True])
        self.run_outcomes(2, [False, False])
        rows = self.export(table="events")
        self.assertEqual(
            [(r["event"], r["level_before"], r["level_after"]) for r in rows],
            [("promotion", "1", "2"), ("demotion", "2", "1")],
        )
        self.assertTrue(all(r["participant"].startswith("P-") and r["created_at"] for r in rows))
        self.assertEqual({r["topic"] for r in rows}, {self.topic.slug})

    def test_learners_table_has_one_row_per_participant_and_topic(self):
        self.run_outcomes(1, [True, True, True], self.topic)
        self.run_outcomes(1, [True], self.other)
        rows = {r["topic"]: r for r in self.export(table="learners")}
        self.assertEqual(set(rows), {self.topic.slug, self.other.slug})
        first = rows[self.topic.slug]
        self.assertEqual(first["level"], "2")
        self.assertEqual((first["total_promotions"], first["total_demotions"]), ("1", "0"))
        self.assertEqual((first["in_remediation"], first["completed"]), ("0", "0"))
        self.assertEqual(rows[self.other.slug]["level"], "1")

    def test_learners_table_marks_completed_topics(self):
        self.master(self.topic)
        (row,) = self.export(table="learners")
        self.assertEqual((row["level"], row["completed"]), ("6", "1"))

    def test_rows_without_progression_data_export_blank_cells(self):
        participant = Participant.objects.create()
        Attempt.objects.create(participant=participant, activity=Activity.objects.first())
        (row,) = self.export()
        self.assertEqual((row["level_at_start"], row["outcome"], row["progression_event"]), ("", "", ""))

    def test_export_contains_no_identifying_columns(self):
        self.run_outcomes(1, [True, True, True])
        self.run_outcomes(2, [False, False])
        for table in ("attempts", "events", "learners"):
            for row in self.export(table=table):
                self.assertFalse({"name", "email", "ip", "session"} & set(row))
