import csv
import io
import re

from django.core.management import call_command
from django.test import TestCase, override_settings

from practice.models import Activity
from research.models import Attempt, Participant


class ResearchTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_activities", verbosity=0)
        cls.tracing = Activity.objects.get(title__icontains="Running total")
        cls.loop = Activity.objects.get(title__icontains="letter-counting")
        cls.ai = Activity.objects.get(title__icontains="even-number")

    def submit_choice(self, activity=None, choice=None):
        """Submit the correct option by default (option order is shuffled)."""
        activity = activity or self.tracing
        choice = choice or activity.correct_choice
        return self.client.post(activity.get_absolute_url(), {"choice": choice})

    def wrong_key(self, activity=None):
        activity = activity or self.tracing
        return next(c["key"] for c in activity.choices if c["key"] != activity.correct_choice)

    def submit_text(self):
        return self.client.post(
            self.loop.get_absolute_url(),
            {"free_text": "It loops over each word, adds to a running total and prints it."},
        )


class ParticipantTests(ResearchTestCase):
    def test_anonymous_participant_is_created_once_per_browser(self):
        self.submit_choice()
        self.submit_choice(choice=self.wrong_key())
        self.assertEqual(Participant.objects.count(), 1)
        self.assertEqual(Attempt.objects.count(), 2)
        participant = Participant.objects.get()
        self.assertRegex(participant.code, r"^P-[0-9A-F]{8}$")

    def test_new_browser_gets_new_participant(self):
        self.submit_choice()
        self.client.cookies.clear()
        self.submit_choice()
        self.assertEqual(Participant.objects.count(), 2)

    def test_no_identifying_fields_exist(self):
        banned = re.compile(r"name|email|ip|agent|session|user|host", re.I)
        fields = [f.name for f in Participant._meta.get_fields()] + [
            f.name for f in Attempt._meta.get_fields()
        ]
        # "participant"/"description"-style words must not trip the check.
        offenders = [f for f in fields if banned.search(f) and f not in {"participant"}]
        self.assertEqual(offenders, [])


class AttemptRecordingTests(ResearchTestCase):
    def test_choice_attempt_fields(self):
        self.submit_choice()
        a = Attempt.objects.get()
        self.assertEqual(a.selected_choice, self.tracing.correct_choice)
        self.assertTrue(a.is_correct)
        self.assertEqual(a.score, 1.0)
        self.assertEqual(a.feedback_service, "")
        self.assertIsNotNone(a.created_at)

    def test_free_text_attempt_records_assessment(self):
        self.submit_text()
        a = Attempt.objects.get()
        self.assertIsNone(a.is_correct)
        self.assertEqual(a.concepts_found, ["Iteration", "Accumulation", "Output"])
        self.assertEqual(a.concepts_missing, [])
        self.assertEqual(a.feedback_service, "keyword")
        self.assertIn("running total", a.free_text)

    def test_ai_decision_and_reasoning_recorded(self):
        self.client.post(
            self.ai.get_absolute_url(),
            {"ai_decision": "reject", "reasoning": "It is true for odd numbers."},
        )
        a = Attempt.objects.get()
        self.assertEqual(a.ai_decision, "reject")
        self.assertTrue(a.is_correct)
        self.assertEqual(a.reasoning, "It is true for odd numbers.")

    def test_hint_usage_counted_then_reset(self):
        url = self.tracing.get_absolute_url()
        self.client.post(url, {"action": "hint"})
        self.client.post(url, {"action": "hint"})
        self.submit_choice()
        self.submit_choice()
        first, second = Attempt.objects.order_by("id")
        self.assertEqual(first.hints_used, 2)
        self.assertEqual(second.hints_used, 0)

    def test_hint_request_alone_creates_no_participant_or_attempt(self):
        self.client.post(self.tracing.get_absolute_url(), {"action": "hint"})
        self.assertEqual(Participant.objects.count(), 0)
        self.assertEqual(Attempt.objects.count(), 0)


class PrivacySettingTests(ResearchTestCase):
    @override_settings(RESEARCH={"ANALYTICS_ENABLED": False})
    def test_analytics_disabled_stores_nothing_but_app_still_works(self):
        response = self.submit_choice()
        self.assertContains(response, "matches the expert reading")
        self.client.post(self.tracing.get_absolute_url(), {"action": "hint"})
        text_response = self.submit_text()
        self.assertContains(text_response, "Iteration")
        self.assertEqual(Participant.objects.count(), 0)
        self.assertEqual(Attempt.objects.count(), 0)
        self.assertNotIn("participant_code", self.client.session)
        self.assertNotIn("hint_counts", self.client.session)

    @override_settings(RESEARCH={"ANALYTICS_ENABLED": False})
    def test_footer_states_analytics_are_off(self):
        self.assertContains(self.client.get("/"), "Analytics are off")

    def test_footer_discloses_research_mode(self):
        self.assertContains(self.client.get("/"), "random anonymous code")

    @override_settings(RESEARCH={"STORE_RESPONSE_TEXT": False})
    def test_response_text_can_be_withheld(self):
        self.submit_text()
        a = Attempt.objects.get()
        self.assertEqual(a.free_text, "")
        self.assertEqual(a.reasoning, "")
        self.assertEqual(a.concepts_found, ["Iteration", "Accumulation", "Output"])

    @override_settings(RESEARCH={"STORE_HINT_USAGE": False})
    def test_hint_usage_can_be_withheld(self):
        self.client.post(self.tracing.get_absolute_url(), {"action": "hint"})
        self.submit_choice()
        self.assertIsNone(Attempt.objects.get().hints_used)

    @override_settings(RESEARCH={"STORE_TIMESTAMPS": False})
    def test_timestamps_can_be_withheld(self):
        self.submit_choice()
        self.assertIsNone(Attempt.objects.get().created_at)
        self.assertIsNone(Participant.objects.get().created_at)


class ExportTests(ResearchTestCase):
    def test_csv_export(self):
        self.submit_choice()
        self.submit_text()
        out = io.StringIO()
        call_command("export_research_data", stdout=out)
        rows = list(csv.DictReader(io.StringIO(out.getvalue())))
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["question_type"], "tracing")
        self.assertEqual(rows[0]["block_level"], "Relations")
        self.assertEqual(rows[1]["block_level"], "Blocks")
        self.assertEqual(rows[1]["concepts_found"], "Iteration|Accumulation|Output")
        self.assertRegex(rows[0]["participant"], r"^P-[0-9A-F]{8}$")


class MatchingResearchTests(ResearchTestCase):
    def matching(self):
        return Activity.objects.filter(question_type__slug="match-terms").first()

    def answer(self, activity, wrong_first=False):
        keys = activity.match_answer_keys()
        if wrong_first:
            keys[0], keys[1] = keys[1], keys[0]
        return {f"match_{i}": k for i, k in enumerate(keys)}

    def test_matches_recorded_as_term_to_definition_text(self):
        a = self.matching()
        self.client.post(a.get_absolute_url(), self.answer(a, wrong_first=True))
        attempt = Attempt.objects.get()
        self.assertFalse(attempt.is_correct)
        self.assertEqual(set(attempt.matches), {p["term"] for p in a.match_pairs})
        self.assertEqual(attempt.matches[a.match_pairs[2]["term"]], a.match_pairs[2]["definition"])
        self.assertEqual(attempt.matches[a.match_pairs[0]["term"]], a.match_pairs[1]["definition"])
        self.assertAlmostEqual(attempt.score, (len(a.match_pairs) - 2) / len(a.match_pairs))

    @override_settings(RESEARCH={"STORE_RESPONSE_TEXT": False})
    def test_matches_survive_when_free_text_is_withheld(self):
        a = self.matching()
        self.client.post(a.get_absolute_url(), self.answer(a))
        self.assertTrue(Attempt.objects.get().matches)

    @override_settings(RESEARCH={"ANALYTICS_ENABLED": False})
    def test_nothing_stored_when_analytics_off(self):
        a = self.matching()
        response = self.client.post(a.get_absolute_url(), self.answer(a))
        self.assertContains(response, "pairs matched")
        self.assertEqual(Attempt.objects.count(), 0)

    def test_export_includes_matches_as_json(self):
        import json

        a = self.matching()
        self.client.post(a.get_absolute_url(), self.answer(a))
        out = io.StringIO()
        call_command("export_research_data", stdout=out)
        row = next(csv.DictReader(io.StringIO(out.getvalue())))
        self.assertEqual(row["question_type"], "match-terms")
        self.assertEqual(
            json.loads(row["matches"])[a.match_pairs[0]["term"]], a.match_pairs[0]["definition"]
        )