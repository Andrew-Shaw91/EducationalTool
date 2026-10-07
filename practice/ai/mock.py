from practice.models import Activity

from .base import AIService


class MockAIService(AIService):
    """
    Deterministic, content-aware scaffolding suitable for a dissertation demo.

    It reads the activity's designed hint, misconceptions and follow-up so it
    behaves like a constrained tutor rather than a chatbot.
    """

    def hint(self, activity: Activity) -> str:
        misconception = ""
        if activity.misconceptions:
            misconception = (
                " A common slip here is: "
                f"{activity.misconceptions[0]} "
                "Check whether that is happening in this fragment."
            )
        return (
            f"{activity.hint_text}{misconception} "
            "Do not look for a finished solution; name what the code is doing "
            "on the next one or two lines."
        )

    def explanation(self, activity: Activity) -> str:
        return (
            "Another way to read this fragment: follow one piece of data from "
            "the first line to the last, and say what is true about it after "
            f"each step. {activity.model_explanation}"
        )

    def follow_up(self, activity: Activity, was_correct: bool | None) -> str:
        if was_correct is False:
            return (
                "Follow-up (targeted at the miss): "
                f"{activity.follow_up_idea} "
                "Keep it to two minutes. The aim is to repair the specific "
                "misconception, not to start a larger exercise."
            )
        return (
            "Follow-up (stretch): "
            f"{activity.follow_up_idea} "
            "Change one value or one condition and predict the new behaviour "
            "before checking it."
        )

    def extra_example(self, activity: Activity) -> str:
        topic = activity.topic.name.lower()
        return (
            f"A nearby example on {topic}: keep the same concept, swap the "
            "data. If the original used numbers, try a short list of words; "
            "if it used a condition on a number, try a condition on a string "
            "length. Predict first, then check your prediction."
        )
