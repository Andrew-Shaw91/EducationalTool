"""
AI integration boundary for CodeSense.

Views never call a vendor SDK. They ask an AIService for hints, feedback,
explanations, and follow-up ideas. Today's implementation is a pedagogically
informed mock so the prototype can be evaluated without an API key.
A later LLM adapter can implement the same interface.
"""

from .factory import get_ai_service

__all__ = ["get_ai_service"]
