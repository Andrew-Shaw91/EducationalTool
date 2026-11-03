"""
Adaptive progression engine: a small, deterministic, rule-based state machine.

THE AI HAS NO ROLE HERE. The flow is:

    1. the learner completes an activity;
    2. the existing evaluation (`practice.evaluation`) judges it;
    3. `outcome_from_assessment` turns that judgement into success or failure;
    4. `apply_outcome` (this module) updates the learner's level by fixed rules;
    5. only afterwards is the resulting level given to the exercise generator.

Nothing in this module touches the database, the network or any AI service, so
the same inputs always give the same result and every rule is unit-testable.
Storage lives in `research.progress`; exercise choice in `practice.selection`.

MASTERY IS PER TOPIC. Each learner has one state for every topic: a Bloom level
within that topic, two streaks and a few counters. Activities are grouped by
(topic, Bloom level). A learner stays in the same topic and level, served a
different unseen activity where one exists, until they show mastery; only then
does the level change, and only after every level of a topic is mastered does
the learner move on to the next topic.

THE RULES (defaults are the constants below; each can be overridden through the
ADAPTIVE dict in settings.py or an environment variable)

    success -> success streak + 1, failure streak reset to 0
    failure -> failure streak + 1, success streak reset to 0
    PROMOTE_AFTER consecutive successes at a level   -> level + 1
    the same at the top level                        -> the topic is COMPLETED
    DEMOTE_AFTER consecutive failures                -> level - 1 (never below
                                                        MIN_LEVEL; 0 switches
                                                        demotion off)
    any level change resets both streaks, so a new level starts from zero

A single failure never changes the level: the learner stays on the same topic
and level and is given another activity there.

REMEDIATION. A demotion puts the learner in "remediation". They are served
activities at the lower level of the same topic at once, and because both
streaks restart at zero a single correct answer can never promote them straight
back: they must string together REMEDIATION_PROMOTE_AFTER (at least 2)
consecutive successes first. Remediation ends at the next promotion.

WHICH ACTIVITIES COUNT. By default only activities at the learner's current
level in that topic change the streaks (COUNT_OFF_LEVEL = False), so doing easy
items cannot farm promotions and trying a hard item does not cause a demotion.
Off-level attempts are still recorded for research. Once a topic is completed
its state is frozen; further attempts are free practice and do not count.
"""

from collections.abc import Collection, Sequence
from dataclasses import dataclass, replace
from enum import Enum

# --- Configuration constants (the only numbers the rules depend on) -----------
MIN_LEVEL = 1  # Bloom level 1 (Knowledge)
MAX_LEVEL = 6  # Bloom level 6 (Evaluation)

ADAPTIVE_ENABLED = True
START_LEVEL = 1
PROMOTE_AFTER = 3  # consecutive successes needed to move up a level
DEMOTE_AFTER = 2  # consecutive failures that move the learner down (0 = never)
REMEDIATION_PROMOTE_AFTER = 3  # successes needed to move up again after a demotion
COUNT_OFF_LEVEL = False
# Open (free-text) answers have no right/wrong; they succeed when the share of
# target ideas shown reaches this. 0.6 means 2 of 3 ideas, 3 of 4, 2 of 2.
OPEN_SUCCESS_SCORE = 0.6


class Outcome(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"


class Event(str, Enum):
    NONE = ""
    PROMOTION = "promotion"
    DEMOTION = "demotion"
    TOPIC_COMPLETE = "topic_complete"


@dataclass(frozen=True)
class ProgressionConfig:
    enabled: bool = ADAPTIVE_ENABLED
    start_level: int = START_LEVEL
    promote_after: int = PROMOTE_AFTER
    demote_after: int = DEMOTE_AFTER
    remediation_promote_after: int = REMEDIATION_PROMOTE_AFTER
    count_off_level: bool = COUNT_OFF_LEVEL
    open_success_score: float = OPEN_SUCCESS_SCORE
    min_level: int = MIN_LEVEL
    max_level: int = MAX_LEVEL

    def __post_init__(self):
        if self.promote_after < 1:
            raise ValueError("PROMOTE_AFTER must be at least 1.")
        if self.demote_after < 0:
            raise ValueError("DEMOTE_AFTER must be 0 (never demote) or more.")
        if self.remediation_promote_after < 2:
            raise ValueError(
                "REMEDIATION_PROMOTE_AFTER must be at least 2: a learner who has been "
                "demoted must not be promoted again after a single correct answer."
            )
        if not self.min_level <= self.start_level <= self.max_level:
            raise ValueError("START_LEVEL must be between the minimum and maximum level.")
        if not 0 < self.open_success_score <= 1:
            raise ValueError("OPEN_SUCCESS_SCORE must be above 0 and at most 1.")

    @property
    def can_demote(self) -> bool:
        return self.demote_after > 0


def get_config() -> ProgressionConfig:
    """Defaults above, overridden by settings.ADAPTIVE (keys in upper case)."""
    from django.conf import settings

    o = getattr(settings, "ADAPTIVE", {}) or {}
    return ProgressionConfig(
        enabled=bool(o.get("ENABLED", ADAPTIVE_ENABLED)),
        start_level=int(o.get("START_LEVEL", START_LEVEL)),
        promote_after=int(o.get("PROMOTE_AFTER", PROMOTE_AFTER)),
        demote_after=int(o.get("DEMOTE_AFTER", DEMOTE_AFTER)),
        remediation_promote_after=int(
            o.get("REMEDIATION_PROMOTE_AFTER", REMEDIATION_PROMOTE_AFTER)
        ),
        count_off_level=bool(o.get("COUNT_OFF_LEVEL", COUNT_OFF_LEVEL)),
        open_success_score=float(o.get("OPEN_SUCCESS_SCORE", OPEN_SUCCESS_SCORE)),
    )


@dataclass(frozen=True)
class LearnerState:
    """A learner's standing in ONE topic."""

    level: int = START_LEVEL
    consecutive_successes: int = 0
    consecutive_failures: int = 0
    total_promotions: int = 0
    total_demotions: int = 0
    in_remediation: bool = False
    completed: bool = False  # every level of the topic has been mastered


@dataclass(frozen=True)
class ProgressionResult:
    """What one completed activity did. `before`/`after` are full states."""

    before: LearnerState
    after: LearnerState
    outcome: Outcome
    counted: bool  # did this attempt take part in the streak rules?
    event: Event = Event.NONE
    at_boundary: bool = False  # a demotion was due but the lowest level was reached

    @property
    def level_start(self) -> int:
        return self.before.level

    @property
    def level_end(self) -> int:
        return self.after.level

    @property
    def promoted(self) -> bool:
        return self.event is Event.PROMOTION

    @property
    def demoted(self) -> bool:
        return self.event is Event.DEMOTION

    @property
    def topic_completed(self) -> bool:
        return self.event is Event.TOPIC_COMPLETE


def outcome_from_assessment(assessment, config: ProgressionConfig | None = None) -> Outcome:
    """
    Success or failure from the EXISTING scoring; no new judgement is made here.

    - Choice, matching and accept/reject items: `is_correct` (matching requires
      every pair right).
    - Open answers (`is_correct` is None): the concept score against the
      configured threshold. No score means failure.
    """
    config = config or get_config()
    if assessment.is_correct is not None:
        return Outcome.SUCCESS if assessment.is_correct else Outcome.FAILURE
    if assessment.score is not None and assessment.score >= config.open_success_score:
        return Outcome.SUCCESS
    return Outcome.FAILURE


def successes_needed(state: LearnerState, config: ProgressionConfig) -> int:
    """Consecutive successes this learner needs to be promoted from here."""
    return config.remediation_promote_after if state.in_remediation else config.promote_after


def apply_outcome(
    state: LearnerState,
    outcome: Outcome,
    *,
    on_level: bool = True,
    config: ProgressionConfig | None = None,
) -> ProgressionResult:
    """
    Apply one activity outcome to a learner's state in one topic. Pure and
    deterministic: returns a new state and never modifies the one passed in.
    """
    config = config or get_config()
    counted = (on_level or config.count_off_level) and not state.completed
    if not counted:
        return ProgressionResult(state, state, outcome, counted=False)

    if outcome is Outcome.SUCCESS:
        return _after_success(state, config)
    return _after_failure(state, config)


def _after_success(state: LearnerState, config: ProgressionConfig) -> ProgressionResult:
    needed = successes_needed(state, config)
    successes = state.consecutive_successes + 1
    updated = replace(state, consecutive_successes=successes, consecutive_failures=0)

    if successes < needed:
        return ProgressionResult(state, updated, Outcome.SUCCESS, True)

    if state.level < config.max_level:
        updated = replace(
            updated,
            level=state.level + 1,
            consecutive_successes=0,
            consecutive_failures=0,
            total_promotions=state.total_promotions + 1,
            in_remediation=False,
        )
        return ProgressionResult(state, updated, Outcome.SUCCESS, True, event=Event.PROMOTION)

    # Mastery of the top level completes the topic.
    updated = replace(updated, consecutive_successes=needed, in_remediation=False, completed=True)
    return ProgressionResult(state, updated, Outcome.SUCCESS, True, event=Event.TOPIC_COMPLETE)


def _after_failure(state: LearnerState, config: ProgressionConfig) -> ProgressionResult:
    failures = state.consecutive_failures + 1
    updated = replace(state, consecutive_failures=failures, consecutive_successes=0)

    if not config.can_demote or failures < config.demote_after:
        return ProgressionResult(state, updated, Outcome.FAILURE, True)

    if state.level > config.min_level:
        updated = replace(
            updated,
            level=state.level - 1,
            consecutive_successes=0,
            consecutive_failures=0,
            total_demotions=state.total_demotions + 1,
            in_remediation=True,
        )
        return ProgressionResult(state, updated, Outcome.FAILURE, True, event=Event.DEMOTION)

    # Bottom level: the streak is held at the threshold instead of growing.
    updated = replace(updated, consecutive_failures=config.demote_after)
    return ProgressionResult(state, updated, Outcome.FAILURE, True, at_boundary=True)


def initial_state(config: ProgressionConfig | None = None) -> LearnerState:
    config = config or get_config()
    return LearnerState(level=config.start_level)


def next_topic_id(
    ordered_topic_ids: Sequence[int],
    completed_topic_ids: Collection[int],
    preferred_id: int | None = None,
) -> int | None:
    """
    Which topic the learner should work on.

    Stay on `preferred_id` (normally the topic of the last activity) until it is
    completed. Then move to the next unfinished topic in curriculum order,
    wrapping round to earlier topics the learner skipped. With no preference,
    start with the first unfinished topic. None when every topic is completed.
    """
    remaining = [t for t in ordered_topic_ids if t not in completed_topic_ids]
    if not remaining:
        return None
    if preferred_id in remaining:
        return preferred_id
    if preferred_id in ordered_topic_ids:
        after = list(ordered_topic_ids)[list(ordered_topic_ids).index(preferred_id) + 1:]
        for topic_id in after:
            if topic_id in remaining:
                return topic_id
    return remaining[0]


# --- Presentation helper (still pure: no database) ------------------------------
@dataclass(frozen=True)
class ProgressView:
    """Everything the interface needs, so templates contain no rules."""

    level: int
    label: str
    next_label: str  # "" at the top level
    successes: int
    successes_needed: int
    failures: int
    failures_allowed: int  # misses before stepping back; 0 when demotion is off
    at_top: bool
    at_bottom: bool
    in_remediation: bool
    promotions: int
    demotions: int
    completed: bool = False
    topic_name: str = ""

    @property
    def success_percent(self) -> int:
        if self.completed:
            return 100
        return round(100 * min(self.successes, self.successes_needed) / self.successes_needed)


def describe(
    state: LearnerState, config: ProgressionConfig | None = None, topic_name: str = ""
) -> ProgressView:
    from practice.models import BloomLevel  # local import keeps this module model-free

    config = config or get_config()
    at_top = state.level >= config.max_level
    at_bottom = state.level <= config.min_level
    return ProgressView(
        level=state.level,
        label=BloomLevel(state.level).label,
        next_label="" if at_top else BloomLevel(state.level + 1).label,
        successes=state.consecutive_successes,
        successes_needed=successes_needed(state, config),
        failures=state.consecutive_failures,
        failures_allowed=config.demote_after,
        at_top=at_top,
        at_bottom=at_bottom,
        in_remediation=state.in_remediation,
        promotions=state.total_promotions,
        demotions=state.total_demotions,
        completed=state.completed,
        topic_name=topic_name,
    )
