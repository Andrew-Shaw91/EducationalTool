from abc import ABC, abstractmethod

from practice.models import Activity


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


class ExplanationGenerator:
    def __init__(self, service: AIService):
        self.service = service

    def generate(self, activity: Activity) -> str:
        return self.service.explanation(activity)
