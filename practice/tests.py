import re

from django.contrib.staticfiles import finders
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from practice.feedback import get_feedback_service
from practice.feedback.ai_enhanced import AIEnhancedFeedbackService, build_prompt
from practice.feedback.base import FeedbackResult, concepts_for
from practice.feedback.keyword import KeywordFeedbackService
from practice.models import Activity


class SeededTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_activities", verbosity=0)

    def by_type(self, slug):
        return Activity.objects.filter(question_type__slug=slug).first()

    def by_title(self, fragment):
        return Activity.objects.get(title__icontains=fragment)

    @staticmethod
    def wrong_choice(activity):
        """Any option key that is not the right answer (options are shuffled)."""
        return next(
            c["key"] for c in activity.choices if c["key"] != activity.correct_choice
        )


class PrototypeFlowTests(SeededTestCase):
    def test_core_pages_render(self):
        for name in ("practice:home", "practice:topics"):
            self.assertEqual(self.client.get(reverse(name)).status_code, 200)
        for activity in Activity.objects.all():
            self.assertEqual(self.client.get(activity.get_absolute_url()).status_code, 200)
            self.assertEqual(
                self.client.get(activity.topic.get_absolute_url()).status_code, 200
            )

    def test_seed_contains_required_activity_types(self):
        for slug in ("explain-code", "tracing", "debugging", "ai-suggestion"):
            self.assertIsNotNone(self.by_type(slug), slug)

    def test_seed_is_idempotent(self):
        before = Activity.objects.count()
        call_command("seed_activities", verbosity=0)
        self.assertEqual(Activity.objects.count(), before)

    def test_tracing_correct_and_incorrect(self):
        activity = self.by_title("Running total")
        correct = self.client.post(
            activity.get_absolute_url(), {"choice": activity.correct_choice}
        )
        self.assertContains(correct, "matches the expert reading")
        wrong = self.client.post(
            activity.get_absolute_url(), {"choice": self.wrong_choice(activity)}
        )
        self.assertContains(wrong, "diverges from the expert")

    def test_debugging_choice(self):
        activity = self.by_type("debugging")
        response = self.client.post(
            activity.get_absolute_url(), {"choice": activity.correct_choice}
        )
        self.assertContains(response, "matches the expert reading")

    def test_ai_suggestion_reject_with_reasoning(self):
        activity = self.by_title("even-number")
        response = self.client.post(
            activity.get_absolute_url(),
            {
                "ai_decision": "reject",
                "reasoning": "It returns True for odd numbers; the remainder should be 0.",
            },
        )
        self.assertContains(response, "matches the expert reading")
        self.assertContains(response, "Ideas your answer showed")

    def test_ai_suggestion_accept_is_wrong(self):
        activity = self.by_title("even-number")
        response = self.client.post(
            activity.get_absolute_url(),
            {"ai_decision": "accept", "reasoning": "Looks fine."},
        )
        self.assertContains(response, "diverges from the expert")

    def test_free_text_is_formative_not_graded(self):
        activity = self.by_type("explain-code")
        response = self.client.post(
            activity.get_absolute_url(),
            {"free_text": "It stores a price and quantity, multiplies them, and prints the total."},
        )
        self.assertContains(response, "Formative check")
        self.assertNotContains(response, "matches the expert reading")
        self.assertContains(response, "Assignment")

    def test_hint_does_not_leak_into_feedback_flow(self):
        activity = self.by_type("tracing")
        response = self.client.post(activity.get_absolute_url(), {"action": "hint"})
        self.assertContains(response, "Tutor hint")


class BloomCoverageTests(SeededTestCase):
    def test_every_bloom_level_has_an_activity(self):
        levels = set(Activity.objects.values_list("bloom_level", flat=True))
        self.assertEqual(levels, {1, 2, 3, 4, 5, 6})

    def test_every_topic_has_a_knowledge_activity(self):
        from practice.models import Topic

        for topic in Topic.objects.all():
            self.assertTrue(
                topic.activities.filter(bloom_level=1).exists(), topic.name
            )

    def test_question_type_and_activity_levels_agree(self):
        for activity in Activity.objects.select_related("question_type"):
            self.assertEqual(
                activity.bloom_level, activity.question_type.bloom_level, activity.title
            )

    def test_knowledge_items_come_first_in_each_topic(self):
        from practice.models import Topic

        for topic in Topic.objects.all():
            first = topic.activities.first()
            self.assertEqual(first.bloom_level, 1, topic.name)

    def test_terminology_item_is_scored(self):
        activity = self.by_title("Parameter or argument")
        right = self.client.post(
            activity.get_absolute_url(), {"choice": activity.correct_choice}
        )
        self.assertContains(right, "matches the expert reading")
        wrong = self.client.post(
            activity.get_absolute_url(), {"choice": self.wrong_choice(activity)}
        )
        self.assertContains(wrong, "diverges from the expert")

    def test_define_concept_is_formative_with_concepts(self):
        activity = self.by_title("Define a variable")
        response = self.client.post(
            activity.get_absolute_url(),
            {"free_text": "A name that stores a value, which can change later."},
        )
        self.assertContains(response, "Formative check")
        self.assertContains(response, "Stores a value")
        self.assertNotContains(response, "Not yet:")

        partial = self.client.post(
            activity.get_absolute_url(), {"free_text": "It is a name."}
        )
        self.assertContains(partial, "Not yet: Stores a value")


class CurriculumMatrixTests(SeededTestCase):
    """The curriculum promise: every topic has every Bloom level."""

    def test_every_topic_has_every_bloom_level(self):
        from practice.models import Topic

        for topic in Topic.objects.all():
            levels = set(topic.activities.values_list("bloom_level", flat=True))
            self.assertEqual(levels, {1, 2, 3, 4, 5, 6}, f"{topic.name}: {sorted(levels)}")

    def test_levels_use_different_kinds_of_task(self):
        """Levels must assess different skills, not harder copies of one task."""
        from practice.models import Topic

        for topic in Topic.objects.all():
            by_level = {}
            for a in topic.activities.select_related("question_type"):
                by_level.setdefault(a.bloom_level, set()).add(a.question_type.slug)
            # No two levels within a topic may be served by only the same type.
            seen = {}
            for level, types in by_level.items():
                key = frozenset(types)
                self.assertNotIn(key, seen.values(), f"{topic.name} L{level}")
                seen[level] = key
            used = set().union(*by_level.values())
            self.assertGreaterEqual(len(used), 6, f"{topic.name}: {sorted(used)}")

    def test_progression_runs_from_l1_to_l6(self):
        from practice.models import Topic

        for topic in Topic.objects.all():
            order = list(topic.activities.values_list("bloom_level", flat=True))
            self.assertEqual(order, sorted(order), topic.name)

    def test_next_in_topic_visits_every_activity_once(self):
        from practice.models import Topic

        for topic in Topic.objects.all():
            expected = list(topic.activities.values_list("id", flat=True))
            walked = [expected[0]]
            current = topic.activities.first()
            while (current := current.next_in_topic()) is not None:
                walked.append(current.id)
            self.assertEqual(walked, expected, topic.name)

    def test_most_levels_mix_reading_and_writing(self):
        """Reading/judging tasks must dominate; writing-style tasks stay a minority."""
        writing_types = {"modify-code", "extend-code", "code-improvement", "prompt-construction"}
        total = Activity.objects.count()
        writing = Activity.objects.filter(question_type__slug__in=writing_types).count()
        self.assertLess(writing / total, 0.4)


class ContentIntegrityTests(SeededTestCase):
    """Every activity carries everything the brief requires."""

    def test_required_fields_are_present(self):
        for a in Activity.objects.select_related("topic", "question_type"):
            where = f"{a.topic.name}: {a.title}"
            for field in ("stem", "model_explanation", "success_criteria", "hint_text", "follow_up_idea"):
                self.assertTrue(getattr(a, field).strip(), f"{where} missing {field}")
            self.assertTrue(a.misconceptions, f"{where} has no misconceptions")
            self.assertTrue(1 <= a.bloom_level <= 6, where)

    def test_activity_level_matches_its_type_level(self):
        for a in Activity.objects.select_related("question_type"):
            self.assertEqual(a.bloom_level, a.question_type.bloom_level, a.title)

    def test_titles_are_unique_within_a_topic(self):
        from collections import Counter

        counts = Counter(Activity.objects.values_list("topic_id", "title"))
        self.assertEqual([k for k, n in counts.items() if n > 1], [])

    def test_multiple_choice_items_are_well_formed(self):
        for a in Activity.objects.filter(question_type__slug__in=[
            "terminology", "tracing", "purpose", "debugging", "code-completion",
            "compare-solutions", "misconception-analysis", "code-quality-review",
        ]):
            keys = [c["key"] for c in a.choices]
            self.assertGreaterEqual(len(keys), 3, a.title)
            self.assertEqual(len(keys), len(set(keys)), a.title)
            self.assertIn(a.correct_choice, keys, a.title)
            texts = [c["text"] for c in a.choices]
            self.assertEqual(len(texts), len(set(texts)), f"duplicate option in {a.title}")

    def test_correct_answer_position_is_not_guessable(self):
        from collections import Counter

        keys = Counter(
            a.correct_choice
            for a in Activity.objects.exclude(choices=[])
            if a.correct_choice and not a.is_ai_evaluation
        )
        # Chance level for four options is 25%; allow modest imbalance only.
        self.assertEqual(set(keys), {"a", "b", "c", "d"}, dict(keys))
        self.assertLess(max(keys.values()) / sum(keys.values()), 0.35, dict(keys))

    def test_option_order_is_stable_across_reseeding(self):
        before = {a.title: (a.choices, a.correct_choice) for a in Activity.objects.all()}
        call_command("seed_activities", verbosity=0)
        after = {a.title: (a.choices, a.correct_choice) for a in Activity.objects.all()}
        self.assertEqual(before, after)

    def test_free_text_types_define_concepts(self):
        free_text = {
            "define-concept", "explain-code", "modify-code",
            "extend-code", "code-improvement", "prompt-construction",
        }
        for a in Activity.objects.filter(question_type__slug__in=free_text).select_related("question_type"):
            self.assertTrue(a.expected_concepts, f"{a.title} has no expected_concepts")
            self.assertFalse(a.choices, a.title)
            for c in a.expected_concepts:
                self.assertTrue(c["name"] and c["description"] and c["keywords"], a.title)

    def test_ai_suggestion_items_are_balanced_and_complete(self):
        items = list(Activity.objects.filter(question_type__slug="ai-suggestion"))
        # Level 6 in every topic is an evaluation task: judging AI output, or
        # (for Lists) reviewing the quality of working code.
        for level6 in Activity.objects.filter(bloom_level=6).select_related("question_type"):
            self.assertIn(
                level6.question_type.slug,
                {"ai-suggestion", "code-quality-review"},
                level6.title,
            )
        self.assertGreaterEqual(len(items), 5)
        decisions = {a.correct_choice for a in items}
        self.assertEqual(decisions, {"accept", "reject"})  # trust must be earned, not assumed
        for a in items:
            self.assertTrue(a.ai_suggestion.strip(), a.title)
            self.assertTrue(a.expected_concepts, a.title)

    def test_each_new_activity_renders_and_can_be_answered(self):
        for a in Activity.objects.all():
            self.assertEqual(self.client.get(a.get_absolute_url()).status_code, 200, a.title)
            if a.is_ai_evaluation:
                data = {"ai_decision": a.correct_choice, "reasoning": "I checked it."}
            elif a.is_matching:
                data = {f"match_{i}": k for i, k in enumerate(a.match_answer_keys())}
            elif a.is_choice_based:
                data = {"choice": a.correct_choice}
            else:
                data = {"free_text": "I think about it carefully."}
            response = self.client.post(a.get_absolute_url(), data)
            self.assertEqual(response.status_code, 200, a.title)
            if a.is_matching:
                self.assertContains(response, "pairs matched", msg_prefix=a.title)
            elif a.is_choice_based or a.is_ai_evaluation:
                self.assertContains(response, "matches the expert reading", msg_prefix=a.title)


class CodeSymbolMatchingTests(SeededTestCase):
    def test_greater_than_and_greater_equal_are_distinguished(self):
        activity = self.by_title("does 65 qualify")
        service = KeywordFeedbackService()
        right = service.evaluate(activity, "Change it to: if age >= 65:")
        self.assertIn("Boundary included", right.concepts_found)
        wrong = service.evaluate(activity, "Change it to: if age > 66:")
        self.assertIn("Boundary included", wrong.concepts_missing)
        spaced = service.evaluate(activity, "use age>=65")
        self.assertIn("Boundary included", spaced.concepts_found)

    def test_words_are_accepted_as_well_as_code(self):
        activity = self.by_title("does 65 qualify")
        result = KeywordFeedbackService().evaluate(
            activity, "The comparison should be at least 65, so 65 is included."
        )
        self.assertEqual(result.concepts_missing, [])

    def test_extend_code_credits_code_answers(self):
        activity = self.by_title("From a total to an average")
        result = KeywordFeedbackService().evaluate(
            activity, "average = total / len(scores)\nprint(average)"
        )
        self.assertEqual(result.concepts_missing, [])

    def test_list_extension_recognises_brackets_and_append(self):
        activity = self.by_title("Collect the passing marks")
        result = KeywordFeedbackService().evaluate(
            activity,
            "passed = []\nfor m in marks:\n    if m >= 50:\n        passed.append(m)\nprint(passed)",
        )
        self.assertEqual(result.concepts_missing, [])

    def test_vague_answers_do_not_get_credit(self):
        activity = self.by_title("Collect the passing marks")
        result = KeywordFeedbackService().evaluate(activity, "I would make it better somehow.")
        self.assertEqual(result.concepts_found, [])


class FeedbackServiceTests(SeededTestCase):
    LOOP_ANSWER = (
        "It goes through each word in the list, adds the length of each to a "
        "running total, and then prints the total at the end."
    )

    def setUp(self):
        self.loop = self.by_title("letter-counting")

    def test_activity_defines_iteration_accumulation_output(self):
        self.assertEqual(
            [c.name for c in concepts_for(self.loop)],
            ["Iteration", "Accumulation", "Output"],
        )

    def assert_contract(self, result):
        self.assertIsInstance(result, FeedbackResult)
        self.assertEqual(
            set(result.as_dict()),
            {"concepts_found", "concepts_missing", "score", "feedback"},
        )
        self.assertTrue(0.0 <= result.score <= 1.0)

    def test_keyword_service_finds_and_misses_concepts(self):
        service = KeywordFeedbackService()
        full = service.evaluate(self.loop, self.LOOP_ANSWER)
        self.assert_contract(full)
        self.assertEqual(full.concepts_missing, [])
        self.assertEqual(full.score, 1.0)
        self.assertEqual(full.service, "keyword")

        partial = service.evaluate(self.loop, "It prints something.")
        self.assertEqual(partial.concepts_found, ["Output"])
        self.assertEqual(partial.concepts_missing, ["Iteration", "Accumulation"])
        self.assertAlmostEqual(partial.score, 1 / 3)

    def test_empty_answer_scores_zero(self):
        result = KeywordFeedbackService().evaluate(self.loop, "   ")
        self.assertEqual(result.score, 0.0)
        self.assertEqual(len(result.concepts_missing), 3)

    def test_whole_word_matching(self):
        prompt = self.by_type("prompt-construction")
        service = KeywordFeedbackService()
        self.assertEqual(service.evaluate(prompt, "many symbols, entirely irrelevant").score, 0.0)
        strong = (
            "Write a function that returns the number of vowels (a, e, i, o, u) in a "
            "string, ignoring case. An empty string returns 0. Treat y as not a vowel."
        )
        self.assertEqual(service.evaluate(prompt, strong).score, 1.0)

    def test_ai_service_mock_matches_contract_and_is_labelled(self):
        result = AIEnhancedFeedbackService().evaluate(self.loop, self.LOOP_ANSWER)
        self.assert_contract(result)
        self.assertEqual(result.service, "ai-mock")
        self.assertEqual(result.score, 1.0)

    def test_prompt_contains_concepts_and_forbids_solutions(self):
        prompt = build_prompt(self.loop, concepts_for(self.loop), "x")
        for name in ("Iteration", "Accumulation", "Output"):
            self.assertIn(name, prompt)
        self.assertIn("Do not write the correct explanation", prompt)

    def test_ai_service_filters_hallucinated_concepts(self):
        class FakeLLM(AIEnhancedFeedbackService):
            def _call_llm(self, prompt):
                return (
                    '{"concepts_found": ["Iteration", "Recursion"], '
                    '"concepts_missing": [], "score": 7, "feedback": "Nice."}'
                )

        result = FakeLLM(api_key="test").evaluate(self.loop, "anything")
        self.assertEqual(result.concepts_found, ["Iteration"])
        self.assertEqual(result.concepts_missing, ["Accumulation", "Output"])
        self.assertEqual(result.score, 1.0)  # clamped
        self.assertEqual(result.service, "ai-enhanced")

    def test_malformed_llm_output_falls_back_to_keywords(self):
        class BrokenLLM(AIEnhancedFeedbackService):
            def _call_llm(self, prompt):
                return "Sure! Here is my analysis..."

        result = BrokenLLM(api_key="test").evaluate(self.loop, self.LOOP_ANSWER)
        self.assertEqual(result.service, "keyword-fallback")
        self.assertEqual(result.score, 1.0)

    def test_api_key_without_client_fails_loudly(self):
        with self.assertRaises(NotImplementedError):
            AIEnhancedFeedbackService(api_key="test").evaluate(self.loop, "text")

    def test_factory_selects_service_from_settings(self):
        self.assertIsInstance(get_feedback_service(), KeywordFeedbackService)
        with override_settings(FEEDBACK_SERVICE="ai"):
            self.assertIsInstance(get_feedback_service(), AIEnhancedFeedbackService)
        with override_settings(FEEDBACK_SERVICE="nope"):
            with self.assertRaises(ImproperlyConfigured):
                get_feedback_service()

    @override_settings(FEEDBACK_SERVICE="ai")
    def test_whole_app_works_with_ai_service_selected(self):
        response = self.client.post(
            self.loop.get_absolute_url(), {"free_text": self.LOOP_ANSWER}
        )
        self.assertContains(response, "Iteration")
        self.assertEqual(response.status_code, 200)


class OfflineTests(SeededTestCase):
    def test_bootstrap_and_fonts_are_vendored(self):
        for path in (
            "css/bootstrap.min.css",
            "js/bootstrap.bundle.min.js",
            "css/codesense.css",
            "fonts/fraunces-600.woff2",
            "fonts/source-sans-3-400.woff2",
            "fonts/source-sans-3-600.woff2",
            "fonts/source-code-pro-400.woff2",
        ):
            self.assertIsNotNone(finders.find(path), path)

    def test_pages_reference_no_external_resources(self):
        external = re.compile(r"""(?:href|src)=["']\s*(?:https?:)?//""", re.I)
        urls = [reverse("practice:home"), reverse("practice:topics")]
        urls += [a.get_absolute_url() for a in Activity.objects.all()]
        for url in urls:
            html = self.client.get(url).content.decode()
            self.assertIsNone(external.search(html), url)
            self.assertIn("/static/css/bootstrap.min.css", html)

    def test_css_has_no_external_urls(self):
        with open(finders.find("css/codesense.css"), encoding="utf-8") as fh:
            self.assertNotRegex(fh.read(), r"url\(\s*['\"]?(https?:)?//")


class MatchingTests(SeededTestCase):
    """Match terms to definitions (L1): content, scoring and the page."""

    def matching(self):
        return list(Activity.objects.filter(question_type__slug="match-terms"))

    def full_answer(self, activity):
        return {f"match_{i}": k for i, k in enumerate(activity.match_answer_keys())}

    def test_every_topic_has_a_matching_item_at_level_1(self):
        from practice.models import Topic

        for topic in Topic.objects.all():
            items = [a for a in self.matching() if a.topic_id == topic.id]
            self.assertTrue(items, topic.name)
            self.assertTrue(all(a.bloom_level == 1 for a in items))

    def test_items_are_well_formed(self):
        for a in self.matching():
            terms = [p["term"] for p in a.match_pairs]
            definitions = [p["definition"] for p in a.match_pairs] + a.match_distractors
            self.assertGreaterEqual(len(terms), 4, a.title)
            self.assertEqual(len(terms), len(set(terms)), a.title)
            self.assertEqual(len(definitions), len(set(definitions)), a.title)
            self.assertTrue(a.match_distractors, f"{a.title}: last pair would fall by elimination")
            self.assertTrue(a.code_snippet.strip(), a.title)
            self.assertFalse(a.choices, a.title)

    def test_definitions_are_not_listed_in_answer_order(self):
        for a in self.matching():
            options = a.match_options()
            for i, pair in enumerate(a.match_pairs):
                self.assertNotEqual(options[i]["text"], pair["definition"], a.title)
            self.assertEqual(len({o["key"] for o in options}), len(options))

    def test_option_order_is_stable_across_reseeding(self):
        before = {a.title: a.match_options() for a in self.matching()}
        call_command("seed_activities", verbosity=0)
        after = {a.title: a.match_options() for a in self.matching()}
        self.assertEqual(before, after)

    def test_correct_answer_keys_point_at_the_right_definitions(self):
        for a in self.matching():
            text = {o["key"]: o["text"] for o in a.match_options()}
            for key, pair in zip(a.match_answer_keys(), a.match_pairs):
                self.assertEqual(text[key], pair["definition"])

    def test_all_correct_is_marked_correct(self):
        for a in self.matching():
            response = self.client.post(a.get_absolute_url(), self.full_answer(a))
            self.assertContains(response, f"{len(a.match_pairs)} of {len(a.match_pairs)} pairs matched")
            self.assertNotContains(response, "not yet")

    def test_partial_credit_and_feedback_name_the_missed_terms(self):
        from practice.evaluation import StudentResponse, evaluate_response

        a = self.matching()[0]
        answer = self.full_answer(a)
        keys = a.match_answer_keys()
        # Swap the first two answers: exactly two pairs wrong.
        answer["match_0"], answer["match_1"] = keys[1], keys[0]
        assessment = evaluate_response(a, StudentResponse.from_post(answer))
        total = len(a.match_pairs)
        self.assertFalse(assessment.is_correct)
        self.assertAlmostEqual(assessment.score, (total - 2) / total)
        self.assertIn(a.match_pairs[0]["term"], assessment.feedback)
        self.assertIn(a.match_pairs[1]["term"], assessment.feedback)
        self.assertEqual([r["ok"] for r in assessment.match_results][:2], [False, False])

    def test_unanswered_and_invalid_keys_score_zero_not_error(self):
        from practice.evaluation import StudentResponse, evaluate_response

        a = self.matching()[0]
        empty = evaluate_response(a, StudentResponse.from_post({}))
        self.assertEqual(empty.score, 0.0)
        self.assertFalse(empty.is_correct)
        junk = evaluate_response(a, StudentResponse.from_post({"match_0": "zzz", "match_99": "a"}))
        self.assertEqual(junk.score, 0.0)

    def test_picking_the_distractor_is_wrong(self):
        from practice.evaluation import StudentResponse, evaluate_response

        a = self.matching()[0]
        options = {o["text"]: o["key"] for o in a.match_options()}
        answer = self.full_answer(a)
        answer["match_0"] = options[a.match_distractors[0]]
        assessment = evaluate_response(a, StudentResponse.from_post(answer))
        self.assertFalse(assessment.match_results[0]["ok"])

    def test_activity_page_has_one_select_per_term(self):
        a = self.matching()[0]
        html = self.client.get(a.get_absolute_url()).content.decode()
        self.assertEqual(html.count('class="form-select match-select"'), len(a.match_pairs))
        for option in a.match_options():
            self.assertIn(option["text"].split(",")[0][:30], html)

    def test_hint_keeps_the_students_picks(self):
        a = self.matching()[0]
        keys = a.match_answer_keys()
        response = self.client.post(
            a.get_absolute_url(), {"action": "hint", "match_0": keys[0]}
        )
        self.assertContains(response, "Tutor hint")
        self.assertContains(response, f'value="{keys[0]}" selected')
