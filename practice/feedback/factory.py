from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from .ai_enhanced import AIEnhancedFeedbackService
from .base import FeedbackService
from .keyword import KeywordFeedbackService


def get_feedback_service() -> FeedbackService:
    """Choose the implementation with settings.FEEDBACK_SERVICE."""
    choice = getattr(settings, "FEEDBACK_SERVICE", "keyword")
    if choice == "keyword":
        return KeywordFeedbackService()
    if choice == "ai":
        return AIEnhancedFeedbackService(api_key=getattr(settings, "LLM_API_KEY", ""))
    raise ImproperlyConfigured(
        f"Unknown FEEDBACK_SERVICE '{choice}'. Use 'keyword' or 'ai'."
    )
