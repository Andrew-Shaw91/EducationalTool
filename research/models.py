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

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.participant.code} -> activity {self.activity_id}"
