"""
Storage and orchestration for adaptive progression.

The rules themselves are in `practice.progression` (pure, no database). This
module only does three things: load a learner's state for a topic, hand it to
the rules together with the existing assessment, and save the new state.

Mastery is tracked PER TOPIC: a learner has one state (level, streaks, counters)
for every topic they have worked on.

Where state lives
    ANALYTICS_ENABLED on  -> one `LearnerProgress` row per participant and topic
                             (this is what the research export reads).
    ANALYTICS_ENABLED off -> the browser session only, so progression still
                             works while nothing at all is written to the
                             database.
"""

from dataclasses import asdict, dataclass

from django.utils import timezone

from practice import progression as rules

from . import conf
from .models import LearnerProgress
from .recording import get_participant, peek_participant

SESSION_KEY = "learner_progress"  # {str(topic id): state dict}


@dataclass(frozen=True)
class ProgressUpdate:
    """Outcome of processing one submission (None `result` when adaptive is off)."""

    result: rules.ProgressionResult | None
    view: rules.ProgressView | None

    @property
    def active(self) -> bool:
        return self.result is not None


NO_UPDATE = ProgressUpdate(None, None)


def _row_to_state(row: LearnerProgress) -> rules.LearnerState:
    return rules.LearnerState(
        level=row.level,
        consecutive_successes=row.consecutive_successes,
        consecutive_failures=row.consecutive_failures,
        total_promotions=row.total_promotions,
        total_demotions=row.total_demotions,
        in_remediation=row.in_remediation,
        completed=row.completed,
    )


def _clean_session_state(raw, config: rules.ProgressionConfig) -> rules.LearnerState:
    """Rebuild a state from the session, tolerating missing or altered data."""
    fallback = rules.initial_state(config)
    if not isinstance(raw, dict):
        return fallback
    try:
        state = rules.LearnerState(
            level=int(raw.get("level", fallback.level)),
            consecutive_successes=int(raw.get("consecutive_successes", 0)),
            consecutive_failures=int(raw.get("consecutive_failures", 0)),
            total_promotions=int(raw.get("total_promotions", 0)),
            total_demotions=int(raw.get("total_demotions", 0)),
            in_remediation=bool(raw.get("in_remediation", False)),
            completed=bool(raw.get("completed", False)),
        )
    except (TypeError, ValueError):
        return fallback
    if not config.min_level <= state.level <= config.max_level:
        return fallback
    return state


def topic_states(request, config: rules.ProgressionConfig | None = None) -> dict[int, rules.LearnerState]:
    """The learner's stored state for each topic they have worked on."""
    config = config or rules.get_config()
    if conf.analytics_enabled():
        participant = peek_participant(request)
        if participant is None:
            return {}
        rows = LearnerProgress.objects.filter(participant=participant)
        return {row.topic_id: _row_to_state(row) for row in rows}

    raw = request.session.get(SESSION_KEY)
    if not isinstance(raw, dict):
        return {}
    states = {}
    for key, value in raw.items():
        if str(key).isdigit():
            states[int(key)] = _clean_session_state(value, config)
    return states


def current_state(request, topic, config: rules.ProgressionConfig | None = None) -> rules.LearnerState:
    """The learner's state in `topic` right now. Never creates or changes anything."""
    config = config or rules.get_config()
    return topic_states(request, config).get(topic.pk) or rules.initial_state(config)


def current_view(request, topic) -> rules.ProgressView | None:
    """Presentation data for one topic, or None when adaptive is disabled."""
    config = rules.get_config()
    if not config.enabled:
        return None
    return rules.describe(current_state(request, topic, config), config, topic.name)


def completed_topic_ids(request) -> set[int]:
    config = rules.get_config()
    return {tid for tid, state in topic_states(request, config).items() if state.completed}


def process_submission(request, activity, assessment) -> ProgressUpdate:
    """
    Apply the result of one submission to the learner's progression in the
    activity's topic.

    Order of events (this is the contract that keeps the AI out of it):
    the assessment already exists -> it is mapped to success/failure ->
    the rules update the level -> the new state is saved.
    The caller wraps this and `record_attempt` in one transaction.
    """
    config = rules.get_config()
    if not config.enabled:
        return NO_UPDATE

    topic = activity.topic
    state = current_state(request, topic, config)
    outcome = rules.outcome_from_assessment(assessment, config)
    result = rules.apply_outcome(
        state, outcome, on_level=activity.bloom_level == state.level, config=config
    )
    _save(request, topic, result.after, config)
    return ProgressUpdate(result, rules.describe(result.after, config, topic.name))


def _save(request, topic, state: rules.LearnerState, config: rules.ProgressionConfig) -> None:
    if not conf.analytics_enabled():
        stored = request.session.get(SESSION_KEY)
        stored = dict(stored) if isinstance(stored, dict) else {}
        stored[str(topic.pk)] = asdict(state)
        request.session[SESSION_KEY] = stored
        return

    participant = get_participant(request)
    row, _ = LearnerProgress.objects.select_for_update().get_or_create(
        participant=participant, topic=topic, defaults={"level": config.start_level}
    )
    row.level = state.level
    row.consecutive_successes = state.consecutive_successes
    row.consecutive_failures = state.consecutive_failures
    row.total_promotions = state.total_promotions
    row.total_demotions = state.total_demotions
    row.in_remediation = state.in_remediation
    row.completed = state.completed
    row.updated_at = timezone.now() if conf.option("STORE_TIMESTAMPS") else None
    row.save()
