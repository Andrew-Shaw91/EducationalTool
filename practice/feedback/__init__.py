"""
Pluggable assessment of free-text student responses.

Views and the evaluation layer depend only on `FeedbackService` and
`FeedbackResult`. Which implementation runs is a settings choice
(`FEEDBACK_SERVICE`), so keyword matching can be replaced by an LLM without
touching views, templates or stored data.
"""

from .base import Concept, FeedbackResult, FeedbackService, concepts_for
from .factory import get_feedback_service

__all__ = [
    "Concept",
    "FeedbackResult",
    "FeedbackService",
    "concepts_for",
    "get_feedback_service",
]
