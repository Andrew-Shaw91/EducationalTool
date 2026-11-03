from django.contrib import admin

from .models import Attempt, LearnerProgress, Participant, ProgressionEvent


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


@admin.register(LearnerProgress)
class LearnerProgressAdmin(ReadOnlyAdmin):
    list_display = (
        "participant",
        "topic",
        "level",
        "consecutive_successes",
        "consecutive_failures",
        "total_promotions",
        "total_demotions",
        "in_remediation",
        "completed",
        "updated_at",
    )
    list_filter = ("topic", "level", "in_remediation", "completed")


@admin.register(ProgressionEvent)
class ProgressionEventAdmin(ReadOnlyAdmin):
    list_display = ("participant", "kind", "level_before", "level_after", "activity", "created_at")
    list_filter = ("kind",)
