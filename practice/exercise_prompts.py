"""
Level-aware prompt for exercise generation.

This builds the instruction that any generator (today the offline mock, later
an LLM adapter) receives. The learner's level is an INPUT: it was decided by
the deterministic rules in `practice.progression` before this prompt is built,
and the prompt tells the generator not to question it.

Cognitive demand rises with the level in two ways: the thinking task changes
(recall -> explain -> use -> dissect -> build -> judge) and the scope grows
(one symbol -> a few lines -> interacting parts -> a whole small program).
The text is a pure function of (level, topic), so it is easy to test and audit.
"""

from dataclasses import dataclass

from practice.models import BloomLevel


@dataclass(frozen=True)
class LevelGuidance:
    thinking: str  # the cognitive task the exercise must demand
    task_types: str  # what the exercise can look like
    scope: str  # how much code and how many ideas
    avoid: str  # what would make it the wrong level


GUIDANCE: dict[int, LevelGuidance] = {
    1: LevelGuidance(
        thinking="Recall or recognise a fact, term or piece of syntax.",
        task_types="Match terms to definitions; name a symbol; pick the correct term.",
        scope="One term, symbol or single-line fragment; one idea.",
        avoid="Do not ask the learner to trace, predict, fix or justify anything.",
    ),
    2: LevelGuidance(
        thinking="Explain what given code does or means, in the learner's own words.",
        task_types="Predict the output; state the purpose of a fragment; explain a line.",
        scope="A short fragment of about 3-6 lines; one idea.",
        avoid="Do not require writing or changing code, and do not ask for evaluation.",
    ),
    3: LevelGuidance(
        thinking="Use a known idea in a new situation.",
        task_types="Complete missing code; change a value to meet a new requirement; trace new inputs.",
        scope="A short fragment of about 4-8 lines with one new situation to handle.",
        avoid="Do not make the answer a pure recall question or require comparing designs.",
    ),
    4: LevelGuidance(
        thinking="Break code into parts and explain how the parts relate or why it fails.",
        task_types="Locate and explain a bug; compare two versions; trace how data flows between parts.",
        scope="About 6-12 lines with two or more interacting parts.",
        avoid="Do not hand over the location of the fault or the relationship being asked about.",
    ),
    5: LevelGuidance(
        thinking="Combine ideas to produce or adapt a solution that did not exist before.",
        task_types="Extend working code with a new feature; recombine two fragments; specify a requirement for a function.",
        scope="A small program or function of about 8-15 lines built from several ideas.",
        avoid="Do not supply the finished solution or a step-by-step recipe.",
    ),
    6: LevelGuidance(
        thinking="Judge the quality or correctness of code, or of a suggestion, against criteria, and justify the judgement.",
        task_types="Accept or reject an AI-suggested change with reasons; critique a solution; choose between designs.",
        scope="A whole small program or an AI suggestion with at least one subtle issue.",
        avoid="Do not state whether the code is good or bad; the learner must decide and defend it.",
    ),
}

# The prompt can be audited for these promises (see tests).
RULES = (
    "Exactly one concept; answerable in about three minutes.",
    "Mostly reading and reasoning about given code.",
    "Include: the question, any code, a model answer, what a strong answer shows, "
    "the likely misconception, and a hint that does not give the answer away.",
    "Never reveal the answer in the question or the hint.",
    "Do not decide, mention, question or adjust the learner's level or progress. "
    "The level above is fixed by the course's progression rules and is not yours to change.",
)


def build_exercise_prompt(level: int, topic_name: str | None = None) -> str:
    """The generation prompt for a learner currently at `level`."""
    try:
        g = GUIDANCE[level]
    except KeyError:
        raise ValueError(f"Unknown level {level!r}; expected one of {sorted(GUIDANCE)}.") from None

    lines = [
        "Generate ONE short exercise for an introductory Python programming course.",
        "",
        f"Learner level: {level} of {max(GUIDANCE)} ({BloomLevel(level).label}).",
        "This level is an input, fixed by the course's progression rules.",
        f"Required thinking: {g.thinking}",
        f"Suitable formats: {g.task_types}",
        f"Scope and complexity: {g.scope}",
        f"Avoid: {g.avoid}",
        f"Topic: {topic_name} (stay within this topic and level)"
        if topic_name
        else "Topic: any programming topic in the course.",
        "",
        "Rules:",
    ]
    lines += [f"- {rule}" for rule in RULES]
    return "\n".join(lines)
