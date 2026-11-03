from abc import ABC, abstractmethod
from dataclasses import dataclass

from practice.exercise_prompts import build_exercise_prompt
from practice.models import Activity, Topic
from practice.selection import select_activity


class AIService(ABC):
    """
    Single entry point for future language-model *scaffolding*.

    Assessing a student's written answer is a separate concern handled by
    `practice.feedback.FeedbackService`, so the two can evolve independently.

    Contract:
    - Never return a complete solution to the current activity.
    - Prefer questions, contrasts, and partial observations.
    - Keep the learner responsible for judging code.
    """

    @abstractmethod
    def hint(self, activity: Activity) -> str:
        raise NotImplementedError

    @abstractmethod
    def explanation(self, activity: Activity) -> str:
        raise NotImplementedError

    @abstractmethod
    def follow_up(self, activity: Activity, was_correct: bool | None) -> str:
        raise NotImplementedError

    @abstractmethod
    def extra_example(self, activity: Activity) -> str:
        raise NotImplementedError

    @abstractmethod
    def generate_exercise(self, request: "ExerciseRequest") -> Activity | None:
        """
        Produce the next exercise for a learner at `request.level`.

        The level is an INPUT. Implementations generate content for it and must
        not choose, change or comment on the learner's level; that is decided
        only by `practice.progression`. Return None if nothing suitable exists.
        """
        raise NotImplementedError


@dataclass(frozen=True)
class ExerciseRequest:
    """Everything a generator is given. The level is already decided."""

    level: int
    prompt: str  # level-aware text from practice.exercise_prompts
    topic: Topic | None = None
    attempted_order: tuple[int, ...] = ()  # activity ids, oldest first


@dataclass(frozen=True)
class ExerciseChoice:
    activity: Activity
    prompt: str
    source: str  # "ai" if the service's exercise was used, else "bank-fallback"


class HintGenerator:
    def __init__(self, service: AIService):
        self.service = service

    def generate(self, activity: Activity) -> str:
        return self.service.hint(activity)


class ExerciseGenerator:
    def __init__(self, service: AIService):
        self.service = service

    def generate(self, activity: Activity, was_correct: bool | None) -> str:
        return self.service.follow_up(activity, was_correct)

    def next_activity(
        self,
        level: int,
        topic: Topic | None = None,
        attempted_order=(),
    ) -> ExerciseChoice | None:
        """
        The next exercise for a learner working on `topic` at `level`.

        The level and topic go into the prompt; the service generates content
        for them. Whatever the service returns is checked: if it is missing or
        is from a different level or topic, the deterministic bank selection is
        used instead, so a generator can never push a learner up, down or into
        another topic by serving other content.
        """
        prompt = build_exercise_prompt(level, topic.name if topic else None)
        request = ExerciseRequest(
            level=level,
            prompt=prompt,
            topic=topic,
            attempted_order=tuple(attempted_order),
        )
        activity = self.service.generate_exercise(request)
        if (
            activity is not None
            and activity.bloom_level == level
            and (topic is None or activity.topic_id == topic.pk)
        ):
            return ExerciseChoice(activity, prompt, "ai")

        fallback = select_activity(
            level, topic=topic, attempted_order=request.attempted_order
        )
        if fallback is None:
            return None
        return ExerciseChoice(fallback, prompt, "bank-fallback")


class ExplanationGenerator:
    def __init__(self, service: AIService):
        self.service = service

    def generate(self, activity: Activity) -> str:
        return self.service.explanation(activity)
