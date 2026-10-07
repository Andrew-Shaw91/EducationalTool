"""
The only code that writes evaluation data.

Views call `record_attempt` / `record_hint` unconditionally; whether anything
is stored is decided here, from settings, so no view needs to know the rules.
"""

from django.utils import timezone

from . import conf
from .models import Attempt, Participant

PARTICIPANT_KEY = "participant_code"
HINT_COUNTS_KEY = "hint_counts"


def get_participant(request) -> Participant | None:
    """Return this browser's anonymous participant, issuing one if needed."""
    if not conf.analytics_enabled():
        return None

    code = request.session.get(PARTICIPANT_KEY)
    participant = Participant.objects.filter(code=code).first() if code else None
    if participant is None:
        participant = Participant.objects.create(
            created_at=timezone.now() if conf.option("STORE_TIMESTAMPS") else None
        )
        request.session[PARTICIPANT_KEY] = participant.code
    return participant


def record_hint(request, activity) -> None:
    if not conf.stores("STORE_HINT_USAGE"):
        return
    counts = request.session.get(HINT_COUNTS_KEY, {})
    key = str(activity.pk)
    counts[key] = counts.get(key, 0) + 1
    request.session[HINT_COUNTS_KEY] = counts


def record_attempt(request, activity, response, assessment) -> Attempt | None:
    """Persist one submission, honouring every privacy setting."""
    if not conf.analytics_enabled():
        return None

    keep_text = conf.option("STORE_RESPONSE_TEXT")
    hints_used = None
    if conf.stores("STORE_HINT_USAGE"):
        counts = request.session.get(HINT_COUNTS_KEY, {})
        hints_used = counts.pop(str(activity.pk), 0)
        request.session[HINT_COUNTS_KEY] = counts

    return Attempt.objects.create(
        participant=get_participant(request),
        activity=activity,
        selected_choice=response.selected_choice,
        matches={r["term"]: r["chosen"] for r in assessment.match_results},
        ai_decision=response.ai_decision,
        free_text=response.free_text if keep_text else "",
        reasoning=response.reasoning if keep_text else "",
        is_correct=assessment.is_correct,
        score=assessment.score,
        concepts_found=assessment.concepts_found,
        concepts_missing=assessment.concepts_missing,
        feedback_service=assessment.service,
        hints_used=hints_used,
        created_at=timezone.now() if conf.option("STORE_TIMESTAMPS") else None,
    )
