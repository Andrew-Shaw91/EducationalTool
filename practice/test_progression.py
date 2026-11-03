"""
Tests for the deterministic progression rules, the level-aware prompt, the
activity selection and the guard that keeps the AI out of level decisions.
"""

import random
from pathlib import Path

from django.core.management import call_command
from django.test import SimpleTestCase, TestCase, override_settings

from practice import progression as rules
from practice.ai.base import AIService, ExerciseGenerator
from practice.ai.mock import MockAIService
from practice.evaluation import Assessment
from practice.exercise_prompts import GUIDANCE, build_exercise_prompt
from practice.models import Activity, BloomLevel, Topic
from practice.progression import (
    Event,
    LearnerState,
    Outcome,
    ProgressionConfig,
    apply_outcome,
    describe,
    outcome_from_assessment,
)
from practice.selection import select_activity

S, F = Outcome.SUCCESS, Outcome.FAILURE
CONFIG = ProgressionConfig()  # the documented defaults: promote 3, demote 2


def run(outcomes, state=None, config=CONFIG, on_level=True):
    """Apply outcomes in order; return (final state, list of results)."""
    state = state or LearnerState()
    results = []
    for outcome in outcomes:
        result = apply_outcome(state, outcome, on_level=on_level, config=config)
        results.append(result)
        state = result.after
    return state, results


class DefaultsTests(SimpleTestCase):
    def test_documented_defaults(self):
        self.assertEqual(CONFIG.promote_after, 3)
        self.assertEqual(CONFIG.demote_after, 2)
        self.assertEqual(CONFIG.start_level, 1)
        self.assertEqual((CONFIG.min_level, CONFIG.max_level), (1, 6))

    def test_levels_match_the_bloom_scale_used_by_the_content(self):
        self.assertEqual(rules.MIN_LEVEL, min(BloomLevel.values))
        self.assertEqual(rules.MAX_LEVEL, max(BloomLevel.values))
        self.assertEqual(sorted(GUIDANCE), list(BloomLevel.values))

    def test_invalid_configuration_is_rejected(self):
        with self.assertRaises(ValueError):
            ProgressionConfig(promote_after=0)
        with self.assertRaises(ValueError):
            ProgressionConfig(demote_after=-1)
        with self.assertRaises(ValueError):
            ProgressionConfig(start_level=7)
        with self.assertRaises(ValueError):
            ProgressionConfig(open_success_score=0)

    def test_remediation_threshold_below_two_is_rejected(self):
        # One correct answer must never be enough to bounce straight back up.
        with self.assertRaises(ValueError):
            ProgressionConfig(remediation_promote_after=1)

    @override_settings(ADAPTIVE={"PROMOTE_AFTER": 4, "DEMOTE_AFTER": 3, "ENABLED": False})
    def test_settings_override_the_defaults(self):
        config = rules.get_config()
        self.assertEqual((config.promote_after, config.demote_after), (4, 3))
        self.assertFalse(config.enabled)
        self.assertEqual(config.remediation_promote_after, 3)  # untouched default

    @override_settings(ADAPTIVE={})
    def test_missing_settings_fall_back_to_defaults(self):
        self.assertEqual(rules.get_config(), ProgressionConfig())


class PromotionTests(SimpleTestCase):
    def test_three_consecutive_successes_promote(self):
        state, results = run([S, S, S])
        self.assertEqual(state.level, 2)
        self.assertEqual(results[-1].event, Event.PROMOTION)
        self.assertTrue(results[-1].promoted)
        self.assertEqual(state.total_promotions, 1)

    def test_two_successes_do_not_promote(self):
        state, results = run([S, S])
        self.assertEqual(state.level, 1)
        self.assertEqual(state.consecutive_successes, 2)
        self.assertTrue(all(r.event is Event.NONE for r in results))

    def test_counters_reset_after_promotion(self):
        state, _ = run([S, S, S])
        self.assertEqual((state.consecutive_successes, state.consecutive_failures), (0, 0))

    def test_new_level_needs_a_full_streak_again(self):
        state, _ = run([S, S, S, S, S])
        self.assertEqual(state.level, 2)
        state, _ = run([S], state)
        self.assertEqual(state.level, 3)

    def test_custom_threshold(self):
        state, _ = run([S, S], config=ProgressionConfig(promote_after=2))
        self.assertEqual(state.level, 2)


class DemotionTests(SimpleTestCase):
    START = LearnerState(level=3)

    def test_two_consecutive_failures_demote(self):
        state, results = run([F, F], self.START)
        self.assertEqual(state.level, 2)
        self.assertEqual(results[-1].event, Event.DEMOTION)
        self.assertTrue(results[-1].demoted)
        self.assertEqual(state.total_demotions, 1)

    def test_one_failure_does_not_demote(self):
        state, _ = run([F], self.START)
        self.assertEqual(state.level, 3)
        self.assertEqual(state.consecutive_failures, 1)

    def test_counters_reset_after_demotion(self):
        state, _ = run([F, F], self.START)
        self.assertEqual((state.consecutive_successes, state.consecutive_failures), (0, 0))

    def test_demotion_starts_remediation(self):
        state, _ = run([F, F], self.START)
        self.assertTrue(state.in_remediation)


class CounterResetTests(SimpleTestCase):
    def test_success_resets_the_failure_counter(self):
        state, _ = run([F, S], LearnerState(level=3))
        self.assertEqual((state.consecutive_failures, state.consecutive_successes), (0, 1))
        # ...so the next failure is a first failure, not a second.
        state, results = run([F], state)
        self.assertEqual(state.level, 3)
        self.assertEqual(state.consecutive_failures, 1)
        self.assertIs(results[-1].event, Event.NONE)

    def test_failure_resets_the_success_counter(self):
        state, _ = run([S, S, F])
        self.assertEqual((state.consecutive_successes, state.consecutive_failures), (0, 1))
        # ...so two more successes are not enough to promote.
        state, _ = run([S, S], state)
        self.assertEqual(state.level, 1)
        self.assertEqual(state.consecutive_successes, 2)

    def test_alternating_results_never_change_level(self):
        state, _ = run([S, F] * 10, LearnerState(level=3))
        self.assertEqual(state.level, 3)
        self.assertEqual((state.total_promotions, state.total_demotions), (0, 0))


class BoundaryTests(SimpleTestCase):
    def test_cannot_go_below_the_lowest_level(self):
        state, results = run([F] * 7)
        self.assertEqual(state.level, rules.MIN_LEVEL)
        self.assertEqual(state.total_demotions, 0)
        self.assertFalse(state.in_remediation)
        self.assertTrue(results[-1].at_boundary)
        # The streak is clamped rather than growing without limit.
        self.assertEqual(state.consecutive_failures, CONFIG.demote_after)

    def test_mastering_the_top_level_completes_the_topic_instead_of_promoting(self):
        top = LearnerState(level=rules.MAX_LEVEL)
        state, results = run([S] * 3, top)
        self.assertEqual(state.level, rules.MAX_LEVEL)
        self.assertEqual(state.total_promotions, 0)
        self.assertTrue(state.completed)
        self.assertIs(results[-1].event, Event.TOPIC_COMPLETE)
        self.assertTrue(results[-1].topic_completed)
        self.assertEqual([r.event for r in results[:-1]], [Event.NONE, Event.NONE])

    def test_a_completed_topic_is_frozen(self):
        done = LearnerState(level=6, consecutive_successes=3, completed=True)
        state, results = run([F, F, F, S], done)
        self.assertEqual(state, done)
        self.assertFalse(any(r.counted for r in results))

    def test_a_failure_at_the_top_still_resets_the_success_streak(self):
        top = LearnerState(level=rules.MAX_LEVEL)
        state, _ = run([S, S, F], top)
        self.assertEqual((state.consecutive_successes, state.consecutive_failures), (0, 1))
        self.assertFalse(state.completed)

    def test_all_levels_must_be_completed_in_order(self):
        state, results = run([S] * 18)
        self.assertTrue(state.completed)
        self.assertEqual(
            [r.level_end for r in results if r.promoted], [2, 3, 4, 5, 6]
        )
        self.assertEqual(sum(r.topic_completed for r in results), 1)
        self.assertTrue(results[-1].topic_completed)
        self.assertFalse(any(r.topic_completed for r in results[:-1]))

    def test_with_demotion_off_a_miss_never_changes_the_level(self):
        config = ProgressionConfig(demote_after=0)
        self.assertFalse(config.can_demote)
        state, results = run([F] * 6, LearnerState(level=4), config)
        self.assertEqual(state.level, 4)
        self.assertEqual(state.total_demotions, 0)
        self.assertFalse(state.in_remediation)
        self.assertTrue(all(r.event is Event.NONE for r in results))
        # ...and a success streak still has to be rebuilt after a miss.
        state, _ = run([S, S, F, S, S], state, config)
        self.assertEqual(state.level, 4)
        state, _ = run([S], state, config)
        self.assertEqual(state.level, 5)

    def test_full_ladder_up_and_down(self):
        state, _ = run([S] * 15)
        self.assertEqual(state.level, 6)
        state, _ = run([F] * 10, state)
        self.assertEqual(state.level, 1)
        self.assertEqual(state.total_promotions, 5)
        self.assertEqual(state.total_demotions, 5)


class RemediationTests(SimpleTestCase):
    def demoted(self):
        state, _ = run([F, F], LearnerState(level=3))
        return state

    def test_one_correct_answer_after_demotion_does_not_promote(self):
        state, results = run([S], self.demoted())
        self.assertEqual(state.level, 2)
        self.assertIs(results[-1].event, Event.NONE)

    def test_competency_is_required_before_promotion(self):
        state, results = run([S, S], self.demoted())
        self.assertEqual(state.level, 2)
        state, results = run([S], state)
        self.assertEqual(state.level, 3)
        self.assertTrue(results[-1].promoted)

    def test_remediation_ends_at_promotion(self):
        state, _ = run([S, S, S], self.demoted())
        self.assertFalse(state.in_remediation)

    def test_a_miss_during_remediation_restarts_the_streak(self):
        state, _ = run([S, S, F, S, S], self.demoted())
        self.assertEqual(state.level, 2)
        self.assertEqual(state.consecutive_successes, 2)

    def test_remediation_threshold_is_configurable_but_never_one(self):
        config = ProgressionConfig(remediation_promote_after=5)
        state, _ = run([F, F], LearnerState(level=3), config)
        state, _ = run([S] * 4, state, config)
        self.assertEqual(state.level, 2)
        state, _ = run([S], state, config)
        self.assertEqual(state.level, 3)

    def test_no_instant_bounce_even_when_normal_threshold_is_one(self):
        config = ProgressionConfig(promote_after=1)
        state, _ = run([F, F], LearnerState(level=3), config)
        state, _ = run([S], state, config)
        self.assertEqual(state.level, 2)

    def test_repeated_demotion_keeps_remediation(self):
        state, _ = run([F, F, F, F], LearnerState(level=3))
        self.assertEqual(state.level, 1)
        self.assertTrue(state.in_remediation)


class OffLevelTests(SimpleTestCase):
    def test_off_level_attempts_do_not_count_by_default(self):
        state, results = run([S, S, S, F, F], on_level=False)
        self.assertEqual(state, LearnerState())
        self.assertFalse(any(r.counted for r in results))

    def test_off_level_attempts_count_when_configured(self):
        config = ProgressionConfig(count_off_level=True)
        state, results = run([S, S, S], config=config, on_level=False)
        self.assertEqual(state.level, 2)
        self.assertTrue(all(r.counted for r in results))


class DeterminismTests(SimpleTestCase):
    def test_same_inputs_give_the_same_result(self):
        outcomes = [S, F, S, S, F, F, S, S, S, S, F, F, F, S]
        self.assertEqual(run(outcomes), run(outcomes))

    def test_state_is_never_mutated(self):
        before = LearnerState(level=3, consecutive_successes=2)
        snapshot = LearnerState(level=3, consecutive_successes=2)
        apply_outcome(before, S, config=CONFIG)
        self.assertEqual(before, snapshot)

    def test_random_sequences_stay_in_range_and_are_reproducible(self):
        rng = random.Random(20260213)
        outcomes = [S if rng.random() < 0.5 else F for _ in range(500)]
        first, results = run(outcomes)
        self.assertEqual(first, run(outcomes)[0])
        for r in results:
            self.assertTrue(CONFIG.min_level <= r.after.level <= CONFIG.max_level)
            self.assertTrue(r.after.consecutive_successes <= CONFIG.promote_after)
            self.assertTrue(r.after.consecutive_failures <= CONFIG.demote_after)
            # Only one rule fires at a time and it moves exactly one level.
            self.assertLessEqual(abs(r.level_end - r.level_start), 1)
        promotions = sum(r.promoted for r in results)
        demotions = sum(r.demoted for r in results)
        self.assertEqual(first.level, 1 + promotions - demotions)
        self.assertEqual((first.total_promotions, first.total_demotions), (promotions, demotions))


class OutcomeMappingTests(SimpleTestCase):
    def test_choice_results_follow_is_correct(self):
        self.assertIs(outcome_from_assessment(Assessment(is_correct=True, score=1.0), CONFIG), S)
        self.assertIs(outcome_from_assessment(Assessment(is_correct=False, score=0.0), CONFIG), F)

    def test_is_correct_wins_over_score(self):
        # An accept/reject item with a good justification but the wrong decision fails.
        self.assertIs(outcome_from_assessment(Assessment(is_correct=False, score=1.0), CONFIG), F)

    def test_open_answers_use_the_score_threshold(self):
        two_of_three = Assessment(is_correct=None, score=2 / 3)
        one_of_three = Assessment(is_correct=None, score=1 / 3)
        self.assertIs(outcome_from_assessment(two_of_three, CONFIG), S)
        self.assertIs(outcome_from_assessment(one_of_three, CONFIG), F)

    def test_open_answer_without_a_score_is_a_failure(self):
        self.assertIs(outcome_from_assessment(Assessment(), CONFIG), F)

    def test_threshold_is_configurable(self):
        strict = ProgressionConfig(open_success_score=0.9)
        self.assertIs(outcome_from_assessment(Assessment(score=2 / 3), strict), F)


class DescribeTests(SimpleTestCase):
    def test_view_reports_progress_toward_promotion_and_demotion(self):
        view = describe(LearnerState(level=2, consecutive_successes=2, consecutive_failures=0), CONFIG)
        self.assertEqual((view.level, view.label), (2, "Comprehension"))
        self.assertEqual((view.successes, view.successes_needed), (2, 3))
        self.assertEqual(view.success_percent, 67)
        self.assertEqual(view.next_label, "Application")
        self.assertEqual(view.failures_allowed, 2)

    def test_view_at_the_extremes(self):
        self.assertTrue(describe(LearnerState(level=1), CONFIG).at_bottom)
        top = describe(LearnerState(level=6), CONFIG)
        self.assertTrue(top.at_top)
        self.assertEqual(top.next_label, "")

    def test_remediation_uses_its_own_threshold(self):
        config = ProgressionConfig(remediation_promote_after=4)
        view = describe(LearnerState(level=2, in_remediation=True), config)
        self.assertEqual(view.successes_needed, 4)


    def test_completed_topic_is_reported_as_full(self):
        view = describe(LearnerState(level=6, consecutive_successes=3, completed=True), CONFIG, "Loops")
        self.assertTrue(view.completed)
        self.assertEqual(view.success_percent, 100)
        self.assertEqual(view.topic_name, "Loops")

    def test_open_topic_is_not_completed(self):
        self.assertFalse(describe(LearnerState(level=6), CONFIG).completed)


class NextTopicTests(SimpleTestCase):
    ORDER = [10, 20, 30, 40]

    def test_start_with_the_first_topic(self):
        self.assertEqual(rules.next_topic_id(self.ORDER, set()), 10)

    def test_stay_on_the_current_topic_until_it_is_completed(self):
        self.assertEqual(rules.next_topic_id(self.ORDER, set(), preferred_id=30), 30)
        self.assertEqual(rules.next_topic_id(self.ORDER, {10}, preferred_id=20), 20)

    def test_move_on_only_when_the_current_topic_is_completed(self):
        self.assertEqual(rules.next_topic_id(self.ORDER, {10}, preferred_id=10), 20)
        self.assertEqual(rules.next_topic_id(self.ORDER, {10, 20}, preferred_id=20), 30)

    def test_skips_completed_topics_and_wraps_to_earlier_unfinished_ones(self):
        self.assertEqual(rules.next_topic_id(self.ORDER, {30, 40}, preferred_id=40), 10)
        self.assertEqual(rules.next_topic_id(self.ORDER, {20, 30}, preferred_id=20), 40)

    def test_none_when_everything_is_completed(self):
        self.assertIsNone(rules.next_topic_id(self.ORDER, set(self.ORDER), preferred_id=40))

    def test_unknown_preferred_topic_falls_back_to_the_first_unfinished(self):
        self.assertEqual(rules.next_topic_id(self.ORDER, {10}, preferred_id=99), 20)


class ExercisePromptTests(SimpleTestCase):
    def test_prompt_names_the_learner_level(self):
        for level in range(1, 7):
            prompt = build_exercise_prompt(level)
            self.assertIn(f"Learner level: {level} of 6 ({BloomLevel(level).label})", prompt)
            self.assertIn(GUIDANCE[level].thinking, prompt)

    def test_prompts_differ_by_level(self):
        prompts = {build_exercise_prompt(level) for level in range(1, 7)}
        self.assertEqual(len(prompts), 6)
        self.assertEqual(len({g.scope for g in GUIDANCE.values()}), 6)
        self.assertEqual(len({g.thinking for g in GUIDANCE.values()}), 6)

    def test_demand_rises_with_level(self):
        self.assertIn("single-line", GUIDANCE[1].scope)
        self.assertIn("whole", GUIDANCE[6].scope)
        self.assertIn("Recall", GUIDANCE[1].thinking)
        self.assertIn("Judge", GUIDANCE[6].thinking)

    def test_prompt_forbids_the_generator_from_touching_the_level(self):
        prompt = build_exercise_prompt(3)
        self.assertIn("Do not decide, mention, question or adjust the learner's level", prompt)
        self.assertIn("Never reveal the answer", prompt)

    def test_topic_is_included_when_given(self):
        self.assertIn("Topic: Loops", build_exercise_prompt(2, "Loops"))
        self.assertIn("any programming topic", build_exercise_prompt(2))

    def test_prompt_is_deterministic(self):
        self.assertEqual(build_exercise_prompt(4, "Loops"), build_exercise_prompt(4, "Loops"))

    def test_unknown_level_is_rejected(self):
        for bad in (0, 7):
            with self.assertRaises(ValueError):
                build_exercise_prompt(bad)


class SelectionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_activities", verbosity=0)

    def test_only_the_requested_level_is_served(self):
        for level in range(1, 7):
            self.assertEqual(select_activity(level).bloom_level, level)

    def test_unseen_activities_come_before_seen_ones(self):
        at_level = list(Activity.objects.filter(bloom_level=2))
        seen = [a.pk for a in at_level[:-1]]
        self.assertEqual(select_activity(2, attempted_order=seen).pk, at_level[-1].pk)

    def test_when_all_are_seen_the_least_recent_is_served(self):
        ids = list(Activity.objects.filter(bloom_level=4).values_list("pk", flat=True))
        order = list(reversed(ids))  # oldest first
        self.assertEqual(select_activity(4, attempted_order=order).pk, order[0])

    def test_topic_filter(self):
        topic = Topic.objects.first()
        activity = select_activity(1, topic=topic)
        self.assertEqual(activity.topic_id, topic.pk)

    def test_a_topic_and_level_always_offers_a_different_unseen_activity(self):
        for topic in Topic.objects.all():
            for level in range(1, 7):
                pool = list(Activity.objects.filter(topic=topic, bloom_level=level))
                self.assertGreaterEqual(len(pool), 3, (topic.slug, level))
                attempted = []
                served = []
                for _ in range(len(pool)):
                    activity = select_activity(level, topic=topic, attempted_order=attempted)
                    self.assertEqual((activity.topic_id, activity.bloom_level), (topic.pk, level))
                    self.assertNotIn(activity.pk, attempted)
                    attempted.append(activity.pk)
                    served.append(activity.pk)
                self.assertEqual(sorted(served), sorted(a.pk for a in pool))

    def test_a_miss_never_changes_topic_even_when_other_topics_are_unseen(self):
        topic = Topic.objects.order_by("-display_order").first()
        first = select_activity(3, topic=topic)
        second = select_activity(3, topic=topic, attempted_order=[first.pk])
        self.assertEqual(second.topic_id, topic.pk)
        self.assertNotEqual(second.pk, first.pk)

    def test_once_the_cell_is_exhausted_the_least_recent_is_repeated(self):
        topic = Topic.objects.first()
        pool = list(Activity.objects.filter(topic=topic, bloom_level=2).values_list("pk", flat=True))
        order = list(reversed(pool))
        again = select_activity(2, topic=topic, attempted_order=order)
        self.assertEqual(again.pk, order[0])
        self.assertEqual(again.topic_id, topic.pk)

    def test_none_when_nothing_matches(self):
        Activity.objects.filter(bloom_level=6).delete()
        self.assertIsNone(select_activity(6))

    def test_selection_is_deterministic(self):
        kwargs = dict(attempted_order=[3, 1, 2], topic=Topic.objects.first())
        self.assertEqual(select_activity(2, **kwargs), select_activity(2, **kwargs))


class SpyService(MockAIService):
    """Records what the generator was given."""

    def __init__(self):
        self.requests = []

    def generate_exercise(self, request):
        self.requests.append(request)
        return super().generate_exercise(request)


class WrongLevelService(MockAIService):
    """A misbehaving generator that tries to serve an activity from another level."""

    def __init__(self, level):
        self.level = level

    def generate_exercise(self, request):
        return Activity.objects.filter(bloom_level=self.level).first()


class NothingService(MockAIService):
    def generate_exercise(self, request):
        return None


class ExerciseGenerationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_activities", verbosity=0)

    def test_mock_generator_serves_the_requested_level(self):
        for level in range(1, 7):
            choice = ExerciseGenerator(MockAIService()).next_activity(level)
            self.assertEqual(choice.activity.bloom_level, level)
            self.assertEqual(choice.source, "ai")

    def test_the_level_is_passed_to_the_generator_in_the_request_and_prompt(self):
        spy = SpyService()
        ExerciseGenerator(spy).next_activity(4)
        (request,) = spy.requests
        self.assertEqual(request.level, 4)
        self.assertIn("Learner level: 4 of 6", request.prompt)
        self.assertEqual(request.prompt, build_exercise_prompt(4))

    def test_a_generator_cannot_override_the_level(self):
        choice = ExerciseGenerator(WrongLevelService(6)).next_activity(2)
        self.assertEqual(choice.activity.bloom_level, 2)
        self.assertEqual(choice.source, "bank-fallback")

    def test_a_generator_cannot_override_the_topic(self):
        topics = list(Topic.objects.all()[:2])
        wanted, other = topics

        class OtherTopic(MockAIService):
            def generate_exercise(self, request):
                return Activity.objects.filter(topic=other, bloom_level=request.level).first()

        choice = ExerciseGenerator(OtherTopic()).next_activity(2, topic=wanted)
        self.assertEqual(choice.activity.topic_id, wanted.pk)
        self.assertEqual(choice.activity.bloom_level, 2)
        self.assertEqual(choice.source, "bank-fallback")

    def test_the_generator_serves_the_requested_topic_and_level(self):
        for topic in Topic.objects.all():
            choice = ExerciseGenerator(MockAIService()).next_activity(3, topic=topic)
            self.assertEqual((choice.activity.topic_id, choice.activity.bloom_level), (topic.pk, 3))
            self.assertEqual(choice.source, "ai")

    def test_a_generator_that_returns_nothing_falls_back_to_the_bank(self):
        choice = ExerciseGenerator(NothingService()).next_activity(3)
        self.assertEqual(choice.activity.bloom_level, 3)
        self.assertEqual(choice.source, "bank-fallback")

    def test_none_when_the_bank_has_nothing_at_that_level(self):
        Activity.objects.filter(bloom_level=5).delete()
        self.assertIsNone(ExerciseGenerator(MockAIService()).next_activity(5))

    def test_existing_follow_up_generation_is_preserved(self):
        activity = Activity.objects.first()
        text = ExerciseGenerator(MockAIService()).generate(activity, False)
        self.assertIn("Follow-up", text)

    def test_ai_interface_requires_generate_exercise(self):
        self.assertIn("generate_exercise", AIService.__abstractmethods__)


class AiHasNoSayOverLevelsTests(SimpleTestCase):
    """Structural guard: the modules that decide levels never import the AI."""

    def test_progression_modules_do_not_import_the_ai_layer(self):
        root = Path(__file__).resolve().parent.parent
        for relative in ("practice/progression.py", "research/progress.py"):
            source = (root / relative).read_text(encoding="utf-8")
            self.assertNotIn("practice.ai", source, relative)
            self.assertNotIn("from practice import ai", source, relative)
            self.assertNotIn("get_ai_service", source, relative)
