"""
Additional Many Small Problems activities.

The original 48 activities live in `practice/management/commands/seed_activities.py`.
These files add more activities so that EVERY TOPIC HAS 3-5 ACTIVITIES AT EVERY
BLOOM LEVEL (tests enforce it). Mastery-based progression needs that depth: a
learner who misses an item stays on the same topic and level and is given a
different, unseen item, and cannot do that from a single activity.

How to add an activity: use `mc` (multiple choice), `op` (open answer) or `ai`
(accept or reject an AI suggestion) from this module, in the file for its topic.
The Bloom level comes from the question type, so the two cannot disagree. Rules:

- Append only. The loader spreads correct answers evenly across positions by the
  order of items, so inserting earlier would move every later answer.
- Any claim about what code prints or raises must be registered with `claim(...)`
  next to the activity. `practice/test_content_claims.py` runs every claim.
- Give each activity a unique title within its topic.
- For multiple choice, write the correct option as `correct=` and the near-miss
  options as `wrong=`; the loader moves the correct option to a balanced position.
- Keywords for open answers are matched as whole words (see practice/feedback).
  Avoid common words ("a", "is", "the") that vague answers would contain.
"""

import textwrap

from practice.models import BlockLevel

# Bloom level of each question type (the same mapping as the original activities).
TYPE_LEVEL = {
    "terminology": 1, "define-concept": 1, "match-terms": 1,
    "explain-code": 2, "tracing": 2, "purpose": 2,
    "prompt-construction": 3, "code-completion": 3, "modify-code": 3,
    "debugging": 4, "compare-solutions": 4, "misconception-analysis": 4,
    "code-improvement": 5, "extend-code": 5,
    "ai-suggestion": 6, "code-quality-review": 6,
}

ATOMS, BLOCKS, RELATIONS, MACRO = (
    BlockLevel.ATOMS, BlockLevel.BLOCKS, BlockLevel.RELATIONS, BlockLevel.MACRO
)

# (code, expected printed lines, expected exception name or "") checked by tests.
CLAIMS: list[tuple[str, tuple[str, ...], str]] = []


def code(text: str) -> str:
    """Dedent a triple-quoted code block."""
    return textwrap.dedent(text).strip("\n")


def claim(source: str, *printed: str, raises: str = "") -> None:
    """
    Register a verifiable statement: running `source` prints exactly `printed`
    (one string per line) and, if `raises` is given, then fails with that error.
    """
    CLAIMS.append((source, printed, raises))


def _base(topic, qtype, title, block, minutes, stem, code_text, explain, criteria,
          misconceptions, hint, follow_up):
    return {
        "topic": topic,
        "question_type": qtype,
        "title": title,
        "bloom_level": TYPE_LEVEL[qtype],
        "block_level": block,
        "estimated_minutes": minutes,
        "stem": stem,
        "code_snippet": code_text,
        "model_explanation": explain,
        "success_criteria": criteria,
        "misconceptions": list(misconceptions),
        "hint_text": hint,
        "follow_up_idea": follow_up,
    }


def _concepts(concepts):
    return [
        {"name": name, "description": description, "keywords": list(keywords)}
        for name, description, keywords in concepts
    ]


def mc(topic, qtype, title, block, *, stem, correct, wrong, explain, criteria,
       misconceptions, hint, follow_up, code="", minutes=3):
    """A multiple-choice activity. `correct` is one option; `wrong` the others."""
    options = [correct, *wrong]
    item = _base(topic, qtype, title, block, minutes, stem, code, explain, criteria,
                 misconceptions, hint, follow_up)
    item.update(
        choices=[{"key": "abcdefgh"[i], "text": t} for i, t in enumerate(options)],
        correct_choice="a",
        expected_concepts=[],
    )
    return item


def op(topic, qtype, title, block, *, stem, concepts, explain, criteria,
       misconceptions, hint, follow_up, code="", requirements="", minutes=4):
    """An open-answer activity assessed against `concepts`."""
    item = _base(topic, qtype, title, block, minutes, stem, code, explain, criteria,
                 misconceptions, hint, follow_up)
    item.update(
        choices=[],
        correct_choice="",
        requirements_text=requirements,
        expected_concepts=_concepts(concepts),
    )
    return item


def ai(topic, title, block, *, stem, code, suggestion, decision, concepts, explain,
       criteria, misconceptions, hint, follow_up, minutes=4):
    """Accept or reject an AI suggestion (`decision` is 'accept' or 'reject')."""
    item = _base(topic, "ai-suggestion", title, block, minutes, stem, code, explain,
                 criteria, misconceptions, hint, follow_up)
    item.update(
        ai_suggestion=suggestion,
        choices=[],
        correct_choice=decision,
        expected_concepts=_concepts(concepts),
    )
    return item


# The topic modules register their activities with these imports, in curriculum
# order. They are imported last because they use the helpers above.
from . import variables, conditionals, loops, functions, lists, dictionaries  # noqa: E402

EXTRA_ACTIVITIES = [
    *variables.ACTIVITIES,
    *conditionals.ACTIVITIES,
    *loops.ACTIVITIES,
    *functions.ACTIVITIES,
    *lists.ACTIVITIES,
    *dictionaries.ACTIVITIES,
]
