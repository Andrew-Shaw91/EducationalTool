"""
Progression state becomes per topic (mastery of a topic before the next).

The earlier LearnerProgress rows held ONE level per participant, which cannot
be converted into per-topic levels, so they are removed. Attempt and
ProgressionEvent rows (the research record) are untouched; their level columns
simply describe the older, whole-course level for attempts made before this
migration.
"""

import django.db.models.deletion
from django.db import migrations, models


def clear_course_wide_state(apps, schema_editor):
    apps.get_model("research", "LearnerProgress").objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("practice", "0004_activity_block_level"),
        ("research", "0003_adaptive_progression"),
    ]

    operations = [
        migrations.AddField(
            model_name="learnerprogress",
            name="topic",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="learner_progress",
                to="practice.topic",
            ),
        ),
        migrations.RunPython(clear_course_wide_state, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="learnerprogress",
            name="topic",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="learner_progress",
                to="practice.topic",
            ),
        ),
        migrations.AddField(
            model_name="learnerprogress",
            name="completed",
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name="learnerprogress",
            name="participant",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="topic_progress",
                to="research.participant",
            ),
        ),
        migrations.AddConstraint(
            model_name="learnerprogress",
            constraint=models.UniqueConstraint(
                fields=("participant", "topic"), name="one_progress_row_per_topic"
            ),
        ),
        migrations.AddField(
            model_name="attempt",
            name="progress_event",
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.AlterField(
            model_name="progressionevent",
            name="kind",
            field=models.CharField(
                choices=[
                    ("promotion", "Promotion"),
                    ("demotion", "Demotion"),
                    ("topic_complete", "Topic completed"),
                ],
                max_length=20,
            ),
        ),
    ]
