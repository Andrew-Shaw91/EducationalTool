"""
EVALUATION DATA: what participants did. Kept apart from activity data
(`practice` app) so it can be switched off, exported, anonymised or deleted
without affecting teaching content.

Principle: no field here can identify a person. There are no names, emails,
IP addresses, user agents, session keys or login accounts. A participant is a
random code held in the browser's session; clearing cookies starts a new one.

COLLECTED FIELDS (complete list)
--------------------------------
Participant
  code        Random anonymous ID such as "P-3F9A12C4". Not derived from any
              personal or device information.
  created_at  When the code was first issued. Empty if STORE_TIMESTAMPS is off.

Attempt (one per submission)
  participant      Which anonymous code submitted it.
  activity         Which activity was attempted (links to activity data).
  selected_choice  Multiple-choice option key picked (e.g. "b"). Blank otherwise.
  matches          Matching items: {term: definition the student chose}, with ""
                   for an unanswered term. Empty otherwise. Closed-choice
                   data, so it is kept even if STORE_RESPONSE_TEXT is off.
  ai_decision      "accept" or "reject" for AI-suggestion items. Blank otherwise.
  free_text        The student's written answer. Empty if STORE_RESPONSE_TEXT off.
  reasoning        The student's justification on AI-suggestion items.
                   Empty if STORE_RESPONSE_TEXT is off.
  is_correct       Whether a choice / matching / accept-reject answer matched
                   the expert reading (matching: every pair correct).
                   Null for open responses (they are not right/wrong graded).
  score            Share of target concepts demonstrated (or of pairs matched
                   correctly, for matching items), 0.0-1.0, or null.
  concepts_found   Names of target concepts the response demonstrated.
  concepts_missing Names of target concepts it did not.
  feedback_service Which assessor produced the result ("keyword", "ai-mock",
                   "ai-enhanced", "keyword-fallback") so results stay
                   comparable across assessors. Blank for choice items.
  hints_used       Hints requested before submitting. Null if STORE_HINT_USAGE off.
  created_at       Submission time. Empty if STORE_TIMESTAMPS is off.
  Adaptive progression (all null/blank when ADAPTIVE is disabled, and on rows
  recorded before the feature existed):
  level_at_start   The learner's Bloom level (1-6) IN THE ACTIVITY'S TOPIC when
                   it was submitted, before this result changed anything.
                   Levels are tracked per topic and only change on submission,
                   so this is the level they held while working on it.
  level_at_end     Their level in that topic after this result was applied.
  progress_event   "promotion", "demotion" or "topic_complete" if this result
                   caused one; blank otherwise.
  outcome          "success" or "failure": what the existing scoring said
                   (choice items: is_correct; open answers: score at or above
                   the OPEN_SUCCESS_SCORE threshold).
  counted_for_progress  Whether the attempt took part in the streak rules.
                   False for an activity from a different Bloom level than the
                   learner's, unless COUNT_OFF_LEVEL is on.
  successes_after / failures_after
                   The two consecutive-streak counters after this result.

LearnerProgress (one per participant AND topic: the current progression state)
  participant, topic, level, consecutive_successes, consecutive_failures,
  total_promotions, total_demotions, in_remediation (True after a demotion
  until the next promotion), completed (every Bloom level of the topic
  mastered), updated_at (empty if STORE_TIMESTAMPS is off).

ProgressionEvent (one per promotion, demotion or topic completion: the
timestamped history)
  participant, attempt (the submission that caused it), activity, kind
  ("promotion", "demotion" or "topic_complete"), level_before, level_after
  (equal for a completion), created_at (empty if STORE_TIMESTAMPS is off).
  The full level trajectory can be rebuilt from these plus the Attempt rows.

Not stored here, but available in the CSV export through the activity link:
topic, question type, Bloom level and Block Model level (Atoms, Blocks,
Relations, Macro Structure). They describe the activity, not the participant.

NOT stored: the feedback text shown to the student, anything typed while
requesting a hint, or any data when ANALYTICS_ENABLED is False.
"""

import secrets

from django.db import models


def generate_participant_code() -> str:
    return f"P-{secrets.token_hex(4).upper()}"


class Participant(models.Model):
    code = models.CharField(max_length=16, unique=True, default=generate_participant_code)
    created_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.code


class Attempt(models.Model):
    participant = models.ForeignKey(
        Participant, on_delete=models.CASCADE, related_name="attempts"
    )
    # PROTECT: evaluation data must never silently vanish if content is edited.
    activity = models.ForeignKey(
        "practice.Activity", on_delete=models.PROTECT, related_name="attempts"
    )

    # Response data (what the student submitted)
    selected_choice = models.CharField(max_length=40, blank=True)
    matches = models.JSONField(default=dict, blank=True)
    ai_decision = models.CharField(max_length=12, blank=True)
    free_text = models.TextField(blank=True)
    reasoning = models.TextField(blank=True)

    # Assessment data (how the system judged it)
    is_correct = models.BooleanField(null=True, blank=True)
    score = models.FloatField(null=True, blank=True)
    concepts_found = models.JSONField(default=list, blank=True)
    concepts_missing = models.JSONField(default=list, blank=True)
    feedback_service = models.CharField(max_length=40, blank=True)

    # Behaviour data
    hints_used = models.PositiveSmallIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(null=True, blank=True)

    # Adaptive progression data (null/blank for rows that predate the feature)
    level_at_start = models.PositiveSmallIntegerField(null=True, blank=True)
    level_at_end = models.PositiveSmallIntegerField(null=True, blank=True)
    outcome = models.CharField(max_length=10, blank=True)
    counted_for_progress = models.BooleanField(null=True, blank=True)
    successes_after = models.PositiveSmallIntegerField(null=True, blank=True)
    failures_after = models.PositiveSmallIntegerField(null=True, blank=True)
    progress_event = models.CharField(max_length=20, blank=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.participant.code} -> activity {self.activity_id}"


class LearnerProgress(models.Model):
    """
    Adaptive-progression state of one anonymous participant in ONE topic.

    Mastery is tracked per topic: a participant has one row for each topic they
    have attempted, each with its own Bloom level and streaks.
    """

    participant = models.ForeignKey(
        Participant, on_delete=models.CASCADE, related_name="topic_progress"
    )
    # PROTECT, like Attempt.activity: evaluation data must not vanish silently.
    topic = models.ForeignKey(
        "practice.Topic", on_delete=models.PROTECT, related_name="learner_progress"
    )
    level = models.PositiveSmallIntegerField(default=1)
    consecutive_successes = models.PositiveSmallIntegerField(default=0)
    consecutive_failures = models.PositiveSmallIntegerField(default=0)
    total_promotions = models.PositiveIntegerField(default=0)
    total_demotions = models.PositiveIntegerField(default=0)
    in_remediation = models.BooleanField(default=False)
    completed = models.BooleanField(default=False)
    updated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name_plural = "learner progress"
        constraints = [
            models.UniqueConstraint(
                fields=["participant", "topic"], name="one_progress_row_per_topic"
            )
        ]

    def __str__(self):
        return f"{self.participant.code} / {self.topic.slug}: level {self.level}"


class ProgressionEvent(models.Model):
    """One promotion or demotion, with the attempt that caused it."""

    class Kind(models.TextChoices):
        PROMOTION = "promotion", "Promotion"
        DEMOTION = "demotion", "Demotion"
        TOPIC_COMPLETE = "topic_complete", "Topic completed"

    participant = models.ForeignKey(
        Participant, on_delete=models.CASCADE, related_name="progression_events"
    )
    attempt = models.ForeignKey(
        Attempt, on_delete=models.CASCADE, related_name="progression_events"
    )
    activity = models.ForeignKey(
        "practice.Activity", on_delete=models.PROTECT, related_name="progression_events"
    )
    kind = models.CharField(max_length=20, choices=Kind.choices)
    level_before = models.PositiveSmallIntegerField()
    level_after = models.PositiveSmallIntegerField()
    created_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.participant.code}: {self.kind} {self.level_before}->{self.level_after}"
