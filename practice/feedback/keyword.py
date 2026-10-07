import re

from practice.models import Activity

from .base import Concept, FeedbackResult, FeedbackService, compose_feedback

# Words and numbers (underscores kept, so tax_rate is one token), plus the
# operators and brackets that matter when students write code. Two-character
# operators are matched first so ">=" is one token and never a ">" plus "=",
# which keeps "> 3" and ">= 3" distinguishable.
_WORD = re.compile(r"[a-z0-9_]+|[<>=!+\-*/%]=|[<>=+\-*/%\[\]{}]")


def tokens(text: str) -> list[str]:
    return _WORD.findall(text.lower())


def _token_matches(word: str, target: str) -> bool:
    """Exact match, or prefix match for words of 4+ letters (swap -> swapped).

    Operators are at most two characters, so they only ever match exactly."""
    if word == target:
        return True
    return len(target) >= 4 and word.startswith(target)


def phrase_present(phrase: str, words: list[str]) -> bool:
    target = tokens(phrase)
    n = len(target)
    if n == 0:
        return False
    for i in range(len(words) - n + 1):
        if all(_token_matches(words[i + j], target[j]) for j in range(n)):
            return True
    return False


def concept_present(concept: Concept, words: list[str]) -> bool:
    """A concept is present if any of its keywords appears as whole word(s)."""
    phrases = concept.keywords or (concept.name,)
    return any(phrase_present(p, words) for p in phrases)


class KeywordFeedbackService(FeedbackService):
    """
    Transparent, deterministic baseline.

    A concept counts as demonstrated when one of its keywords appears as a
    whole word (light prefix stemming). Cheap, offline and reproducible, but it
    rewards vocabulary rather than understanding; see design_notes.md.
    """

    name = "keyword"

    def _evaluate(
        self, activity: Activity, concepts: list[Concept], text: str
    ) -> FeedbackResult:
        words = tokens(text)
        found = [c.name for c in concepts if concept_present(c, words)]
        missing = [c.name for c in concepts if c.name not in found]
        return FeedbackResult(
            concepts_found=found,
            concepts_missing=missing,
            score=len(found) / len(concepts),
            feedback=compose_feedback(found, missing),
            service=self.name,
        )
