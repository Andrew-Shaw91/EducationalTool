import csv
import json

from django.core.management.base import BaseCommand

from research.models import Attempt, LearnerProgress, ProgressionEvent

# Existing columns keep their positions; progression columns are appended so
# analysis scripts written against the earlier export still work.
COLUMNS = [
    "participant",
    "activity_id",
    "topic",
    "question_type",
    "bloom_level",
    "block_level",
    "selected_choice",
    "matches",
    "ai_decision",
    "free_text",
    "reasoning",
    "is_correct",
    "score",
    "concepts_found",
    "concepts_missing",
    "feedback_service",
    "hints_used",
    "created_at",
    "level_at_start",
    "level_at_end",
    "outcome",
    "counted_for_progress",
    "successes_after",
    "failures_after",
    "progression_event",
]

EVENT_COLUMNS = [
    "participant",
    "attempt_id",
    "activity_id",
    "topic",
    "event",
    "level_before",
    "level_after",
    "created_at",
]

LEARNER_COLUMNS = [
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
]


def _blank(value):
    return "" if value is None else value


def _when(value):
    return value.isoformat() if value else ""


def progression_event(attempt) -> str:
    """promotion / demotion / topic_complete / blank for this attempt."""
    if attempt.progress_event:
        return attempt.progress_event
    # Attempts recorded before progress_event existed: infer from the levels.
    if attempt.level_at_start is None or attempt.level_at_end is None:
        return ""
    if attempt.level_at_end > attempt.level_at_start:
        return "promotion"
    if attempt.level_at_end < attempt.level_at_start:
        return "demotion"
    return ""


def attempt_row(a) -> list:
    return [
        a.participant.code,
        a.activity_id,
        a.activity.topic.slug,
        a.activity.question_type.slug,
        a.activity.bloom_level,
        a.activity.block_label,
        a.selected_choice,
        json.dumps(a.matches, ensure_ascii=False) if a.matches else "",
        a.ai_decision,
        a.free_text,
        a.reasoning,
        "" if a.is_correct is None else int(a.is_correct),
        _blank(a.score),
        "|".join(a.concepts_found),
        "|".join(a.concepts_missing),
        a.feedback_service,
        _blank(a.hints_used),
        _when(a.created_at),
        _blank(a.level_at_start),
        _blank(a.level_at_end),
        a.outcome,
        "" if a.counted_for_progress is None else int(a.counted_for_progress),
        _blank(a.successes_after),
        _blank(a.failures_after),
        progression_event(a),
    ]


def event_row(e) -> list:
    return [
        e.participant.code,
        e.attempt_id,
        e.activity_id,
        e.activity.topic.slug,
        e.kind,
        e.level_before,
        e.level_after,
        _when(e.created_at),
    ]


def learner_row(p) -> list:
    return [
        p.participant.code,
        p.topic.slug,
        p.level,
        p.consecutive_successes,
        p.consecutive_failures,
        p.total_promotions,
        p.total_demotions,
        int(p.in_remediation),
        int(p.completed),
        _when(p.updated_at),
    ]


class Command(BaseCommand):
    help = (
        "Export evaluation data as CSV for analysis. Default table: one row per "
        "attempt. Use --table events for promotions/demotions, or learners for "
        "each participant's current progression state."
    )

    def add_arguments(self, parser):
        parser.add_argument("--output", help="CSV path. Defaults to stdout.")
        parser.add_argument(
            "--table",
            choices=["attempts", "events", "learners"],
            default="attempts",
            help="Which table to export (default: attempts).",
        )

    def handle(self, *args, output=None, table="attempts", **options):
        if table == "events":
            rows = ProgressionEvent.objects.select_related("participant", "activity__topic")
            header, to_row = EVENT_COLUMNS, event_row
        elif table == "learners":
            rows = LearnerProgress.objects.select_related("participant", "topic").order_by(
                "participant__code", "topic__display_order"
            )
            header, to_row = LEARNER_COLUMNS, learner_row
        else:
            rows = Attempt.objects.select_related(
                "participant", "activity__topic", "activity__question_type"
            )
            header, to_row = COLUMNS, attempt_row

        out = open(output, "w", newline="", encoding="utf-8") if output else self.stdout
        try:
            writer = csv.writer(out)
            writer.writerow(header)
            for obj in rows:
                writer.writerow(to_row(obj))
        finally:
            if output:
                out.close()
        if output:
            self.stderr.write(self.style.SUCCESS(f"Exported {rows.count()} {table} rows to {output}"))
