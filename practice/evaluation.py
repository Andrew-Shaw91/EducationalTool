"""
Turns a student's submission into an Assessment.

- Multiple choice, matching and accept/reject decisions are checked
  deterministically.
- Free-text answers (and the reasoning on AI-suggestion items) are assessed by
  whichever FeedbackService is configured; this module does not know which.

Nothing here stores anything; see the `research` app for that.
"""

from dataclasses import dataclass, field

from practice.feedback import FeedbackService, get_feedback_service
from practice.models import Activity


@dataclass
class StudentResponse:
    selected_choice: str = ""
    free_text: str = ""
    ai_decision: str = ""
    reasoning: str = ""
    # Matching items: {term index: chosen definition key}. Unanswered terms are absent.
    matches: dict[int, str] = field(default_factory=dict)

    @classmethod
    def from_post(cls, post) -> "StudentResponse":
        matches = {}
        for name, value in post.items():
            prefix, _, index = name.partition("_")
            if prefix == "match" and index.isdigit() and value.strip():
                matches[int(index)] = value.strip()
        return cls(
            selected_choice=post.get("choice", "").strip(),
            free_text=post.get("free_text", "").strip(),
            ai_decision=post.get("ai_decision", "").strip().lower(),
            reasoning=post.get("reasoning", "").strip(),
            matches=matches,
        )


@dataclass
class Assessment:
    """
    is_correct:    True/False for choice, matching and accept/reject; None for
                   open answers, which are formative and never marked right
                   or wrong.
    score:         share of target concepts demonstrated (0-1), the share of
                   pairs matched correctly, or None.
    service:       which assessor produced the concept results ("" if none).
    match_results: matching items only, one dict per term:
                   {"term", "chosen", "correct", "ok"} where "chosen" is the
                   definition the student picked ("" if none).
    """

    is_correct: bool | None = None
    score: float | None = None
    concepts_found: list[str] = field(default_factory=list)
    concepts_missing: list[str] = field(default_factory=list)
    feedback: str = ""
    service: str = ""
    match_results: list[dict] = field(default_factory=list)


CHOICE_RIGHT = (
    "Your choice matches the expert reading. Make sure you can say why, "
    "not only that you chose well."
)
CHOICE_WRONG = (
    "Your choice differs from the expert reading. Pause on the line that "
    "actually changes the program's behaviour, not the one that merely looks "
    "unfamiliar, then compare with the explanation."
)


def evaluate_response(
    activity: Activity,
    response: StudentResponse,
    feedback_service: FeedbackService | None = None,
) -> Assessment:
    slug = activity.question_type.slug

    if activity.is_matching:
        return _assess_matching(activity, response)

    if slug == "ai-suggestion":
        correct = bool(
            response.ai_decision
            and response.ai_decision == activity.correct_choice.lower()
        )
        result = _assess_text(activity, response.reasoning, feedback_service)
        return Assessment(
            is_correct=correct,
            score=result.score,
            concepts_found=result.concepts_found,
            concepts_missing=result.concepts_missing,
            feedback=f"{CHOICE_RIGHT if correct else CHOICE_WRONG} {result.feedback}",
            service=result.service,
        )

    if activity.is_choice_based and activity.correct_choice:
        correct = response.selected_choice == activity.correct_choice
        return Assessment(
            is_correct=correct,
            score=1.0 if correct else 0.0,
            feedback=CHOICE_RIGHT if correct else CHOICE_WRONG,
        )

    result = _assess_text(activity, response.free_text, feedback_service)
    return Assessment(
        is_correct=None,
        score=result.score,
        concepts_found=result.concepts_found,
        concepts_missing=result.concepts_missing,
        feedback=result.feedback,
        service=result.service,
    )


def _assess_matching(activity: Activity, response: StudentResponse) -> Assessment:
    """Score each term separately; the whole item is correct only if all pairs are."""
    options = {o["key"]: o["text"] for o in activity.match_options()}
    results = []
    for index, pair in enumerate(activity.match_pairs):
        chosen = options.get(response.matches.get(index, ""), "")
        results.append(
            {
                "term": pair["term"],
                "chosen": chosen,
                "correct": pair["definition"],
                "ok": chosen == pair["definition"],
            }
        )

    right = sum(r["ok"] for r in results)
    total = len(results)
    wrong_terms = [r["term"] for r in results if not r["ok"]]
    if not wrong_terms:
        feedback = (
            f"All {total} pairs match. Try saying each definition without "
            "looking at the term, to check you know the idea and did not just "
            "eliminate options."
        )
    else:
        feedback = (
            f"You matched {right} of {total}. Look again at: "
            f"{', '.join(wrong_terms)}. For each, ask what the term does in "
            "the code above, and which definition describes only that."
        )
    return Assessment(
        is_correct=not wrong_terms,
        score=right / total,
        feedback=feedback,
        match_results=results,
    )


def _assess_text(activity, text, feedback_service):
    service = feedback_service or get_feedback_service()
    return service.evaluate(activity, text)
