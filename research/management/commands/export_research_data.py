import csv
import json

from django.core.management.base import BaseCommand

from research.models import Attempt

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
]


class Command(BaseCommand):
    help = "Export evaluation data (one row per attempt) as CSV for analysis."

    def add_arguments(self, parser):
        parser.add_argument("--output", help="CSV path. Defaults to stdout.")

    def handle(self, *args, output=None, **options):
        attempts = Attempt.objects.select_related(
            "participant", "activity__topic", "activity__question_type"
        )
        out = open(output, "w", newline="", encoding="utf-8") if output else self.stdout
        try:
            writer = csv.writer(out)
            writer.writerow(COLUMNS)
            for a in attempts:
                writer.writerow(
                    [
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
                        "" if a.score is None else a.score,
                        "|".join(a.concepts_found),
                        "|".join(a.concepts_missing),
                        a.feedback_service,
                        "" if a.hints_used is None else a.hints_used,
                        a.created_at.isoformat() if a.created_at else "",
                    ]
                )
        finally:
            if output:
                out.close()
        if output:
            self.stderr.write(self.style.SUCCESS(f"Exported {attempts.count()} attempts to {output}"))
