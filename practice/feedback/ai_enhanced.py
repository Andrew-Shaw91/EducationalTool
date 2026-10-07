import json
import logging

from practice.models import Activity

from .base import Concept, FeedbackResult, FeedbackService, compose_feedback
from .keyword import KeywordFeedbackService, concept_present, tokens

logger = logging.getLogger(__name__)

PROMPT_TEMPLATE = """You are assessing a novice programmer's written response.

Activity type: {question_type}
Question shown to the student:
{stem}

Code shown to the student:
{code}

Concepts a strong answer should demonstrate (judge by meaning, not exact words):
{concepts}

Student response:
\"\"\"{response}\"\"\"

Rules:
- Only use concept names from the list above.
- Do not write the correct explanation or solution for the student.
- Feedback must be 2-3 sentences, encouraging, and name what is still missing.

Reply with JSON only, in exactly this shape:
{{"concepts_found": [...], "concepts_missing": [...], "score": 0.0, "feedback": "..."}}
"""


def build_prompt(activity: Activity, concepts: list[Concept], text: str) -> str:
    concept_lines = "\n".join(
        f"- {c.name}: {c.description or 'no description provided'}" for c in concepts
    )
    return PROMPT_TEMPLATE.format(
        question_type=activity.question_type.name,
        stem=activity.stem,
        code=activity.code_snippet or "(none)",
        concepts=concept_lines,
        response=text,
    )


class AIEnhancedFeedbackService(FeedbackService):
    """
    LLM-ready evaluation of explanations against predefined concepts.

    Pipeline (each step is a small, replaceable seam):
        build_prompt -> _call_llm -> _parse_response -> FeedbackResult

    Today `_call_llm` is intentionally unimplemented. Without an API key the
    service answers with `_mock_llm_response`, which returns JSON in the exact
    shape a real model must return, so the surrounding code is already tested
    against the real contract. To go live: implement `_call_llm` (send the
    prompt, return the model's text) and set the API key. Nothing else changes.

    Safeguards that matter for research validity:
    - Concept names returned by the model are filtered to the known list, and
      `concepts_missing` is recomputed, so a hallucinated concept cannot
      appear in results.
    - Unparseable output falls back to keyword matching and is recorded as
      "keyword-fallback" rather than silently passed off as an LLM result.
    - Mock results are recorded as "ai-mock", never as "ai-enhanced".
    """

    name = "ai-enhanced"

    def __init__(self, api_key: str = ""):
        self.api_key = api_key or ""

    def _evaluate(
        self, activity: Activity, concepts: list[Concept], text: str
    ) -> FeedbackResult:
        prompt = build_prompt(activity, concepts, text)
        if self.api_key:
            raw = self._call_llm(prompt)
            label = self.name
        else:
            raw = self._mock_llm_response(concepts, text)
            label = "ai-mock"

        try:
            return self._parse_response(raw, concepts, label)
        except (ValueError, TypeError, KeyError) as exc:
            logger.warning("Unusable LLM response (%s); using keyword fallback.", exc)
            fallback = KeywordFeedbackService()._evaluate(activity, concepts, text)
            fallback.service = "keyword-fallback"
            return fallback

    # -- seam 1: the only method that talks to a model ------------------------
    def _call_llm(self, prompt: str) -> str:
        raise NotImplementedError(
            "No LLM client is connected. Implement AIEnhancedFeedbackService."
            "_call_llm(prompt) -> str (the model's JSON reply), or unset the "
            "API key to use the mock."
        )

    # -- seam 2: offline stand-in with the same output contract ---------------
    def _mock_llm_response(self, concepts: list[Concept], text: str) -> str:
        words = tokens(text)
        found = [c.name for c in concepts if concept_present(c, words)]
        missing = [c.name for c in concepts if c.name not in found]
        return json.dumps(
            {
                "concepts_found": found,
                "concepts_missing": missing,
                "score": round(len(found) / len(concepts), 2),
                "feedback": compose_feedback(found, missing),
            }
        )

    # -- seam 3: validate whatever came back ----------------------------------
    def _parse_response(
        self, raw: str, concepts: list[Concept], label: str
    ) -> FeedbackResult:
        data = json.loads(raw)
        known = [c.name for c in concepts]

        reported = data["concepts_found"]
        if not isinstance(reported, list):
            raise ValueError("concepts_found must be a list")
        found = [name for name in known if name in reported]
        missing = [name for name in known if name not in found]

        try:
            score = float(data["score"])
        except (TypeError, ValueError):
            score = len(found) / len(known)
        score = max(0.0, min(1.0, score))

        feedback = str(data.get("feedback") or compose_feedback(found, missing))
        return FeedbackResult(
            concepts_found=found,
            concepts_missing=missing,
            score=score,
            feedback=feedback,
            service=label,
        )
