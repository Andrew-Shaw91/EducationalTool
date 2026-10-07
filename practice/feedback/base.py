from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from practice.models import Activity


@dataclass(frozen=True)
class Concept:
    """
    One idea a strong answer should contain.

    `description` is what an LLM judges against (meaning, not wording).
    `keywords` is what the keyword service looks for (wording, not meaning).
    Both live with the activity so switching services needs no content changes.
    """

    name: str
    description: str = ""
    keywords: tuple[str, ...] = ()


def concepts_for(activity: Activity) -> list[Concept]:
    """Read Activity.expected_concepts: [{"name", "description", "keywords"}]."""
    concepts = []
    for raw in activity.expected_concepts or []:
        concepts.append(
            Concept(
                name=raw["name"],
                description=raw.get("description", ""),
                keywords=tuple(raw.get("keywords", ())),
            )
        )
    return concepts


@dataclass
class FeedbackResult:
    """
    The contract every FeedbackService returns.

    score is the share of target concepts demonstrated (0.0 - 1.0). It is a
    formative signal, not a grade. `service` records which implementation
    produced the result so evaluation data stays interpretable later.
    """

    concepts_found: list[str] = field(default_factory=list)
    concepts_missing: list[str] = field(default_factory=list)
    score: float = 0.0
    feedback: str = ""
    service: str = ""

    def as_dict(self) -> dict:
        return {
            "concepts_found": self.concepts_found,
            "concepts_missing": self.concepts_missing,
            "score": self.score,
            "feedback": self.feedback,
        }


def compose_feedback(found: list[str], missing: list[str]) -> str:
    """
    Plain-language comment shared by services that do not write their own.

    It names missing concepts as prompts to think about; it never supplies
    the missing explanation.
    """
    if not missing:
        return (
            "Your answer touches every idea this activity targets: "
            f"{', '.join(found)}. Check the expert explanation to compare wording and precision."
        )
    if not found:
        return (
            "Your answer does not yet show the ideas this activity targets. "
            f"Try saying something about: {', '.join(missing)}. "
            "Read the code one line at a time and describe what changes."
        )
    return (
        f"Good: you covered {', '.join(found)}. "
        f"Still to address: {', '.join(missing)}. "
        "Add what happens to the data, not only what the syntax looks like."
    )


class FeedbackService(ABC):
    """
    Evaluates a free-text response against an activity's expected concepts.

    Subclasses implement `_evaluate`. The public `evaluate` handles the cases
    that are identical for every implementation (no concepts defined, empty
    answer) so those rules cannot drift between services.
    """

    name = "base"

    def evaluate(self, activity: Activity, response_text: str) -> FeedbackResult:
        concepts = concepts_for(activity)
        text = (response_text or "").strip()

        if not concepts:
            return FeedbackResult(
                feedback="No target concepts are defined for this activity.",
                service=self.name,
            )
        if not text:
            missing = [c.name for c in concepts]
            return FeedbackResult(
                concepts_missing=missing,
                feedback=compose_feedback([], missing),
                service=self.name,
            )
        return self._evaluate(activity, concepts, text)

    @abstractmethod
    def _evaluate(
        self, activity: Activity, concepts: list[Concept], text: str
    ) -> FeedbackResult:
        raise NotImplementedError
