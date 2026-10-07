from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from .base import AIService
from .mock import MockAIService


def get_ai_service() -> AIService:
    provider = getattr(settings, "AI_PROVIDER", "mock")
    if provider == "mock":
        return MockAIService()
    raise ImproperlyConfigured(
        f"Unknown AI_PROVIDER '{provider}'. Implement an adapter in "
        "practice.ai and register it here. Views should not import vendor SDKs."
    )
