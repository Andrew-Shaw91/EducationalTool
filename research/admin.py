from django.contrib import admin

from .models import Attempt, Participant


class ReadOnlyAdmin(admin.ModelAdmin):
    """Evaluation data is evidence: view and filter it, never edit it."""

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Participant)
class ParticipantAdmin(ReadOnlyAdmin):
    list_display = ("code", "created_at")


@admin.register(Attempt)
class AttemptAdmin(ReadOnlyAdmin):
    list_display = (
        "participant",
        "activity",
        "is_correct",
        "score",
        "feedback_service",
        "hints_used",
        "created_at",
    )
    list_filter = ("activity__question_type", "is_correct", "feedback_service")
