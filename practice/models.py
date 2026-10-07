"""
ACTIVITY DATA: the teaching content. Nothing in this module records anything
about a student. What students did lives in the separate `research` app, so
content can be edited, exported or published without touching participant data.
"""

import random

from django.db import models
from django.db.models import Q
from django.urls import reverse


class BloomLevel(models.IntegerChoices):
    KNOWLEDGE = 1, "Knowledge"
    COMPREHENSION = 2, "Comprehension"
    APPLICATION = 3, "Application"
    ANALYSIS = 4, "Analysis"
    SYNTHESIS = 5, "Synthesis"
    EVALUATION = 6, "Evaluation"


class QuestionType(models.Model):
    """
    Pedagogical activity family, not merely a UI widget.

    Each type maps onto a Bloom-inspired outcome and a stance toward AI:
    read code, judge code, or reshape code/requirements.
    """

    class Stance(models.TextChoices):
        READ = "read", "Read — build a mental model"
        JUDGE = "judge", "Judge — analyse and evaluate"
        SHAPE = "shape", "Shape — improve or specify"

    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=80)
    bloom_level = models.PositiveSmallIntegerField(choices=BloomLevel.choices)
    stance = models.CharField(max_length=12, choices=Stance.choices)
    short_description = models.CharField(max_length=220)
    pedagogical_aim = models.TextField(
        help_text="Why this activity type exists in an AI-rich classroom."
    )
    student_prompt_stem = models.CharField(
        max_length=220,
        help_text="Default instruction shown to the learner.",
    )
    ai_role = models.TextField(
        help_text="What AI may do here, and what it must not do."
    )
    display_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["display_order", "bloom_level"]

    def __str__(self):
        return self.name

    @property
    def bloom_label(self):
        return BloomLevel(self.bloom_level).label


class Topic(models.Model):
    name = models.CharField(max_length=80)
    slug = models.SlugField(unique=True)
    summary = models.TextField()
    why_it_matters = models.TextField(
        help_text="Why this concept still matters when AI can emit code."
    )
    display_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["display_order", "name"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("practice:topic_detail", args=[self.slug])

    def activity_count(self):
        return self.activities.count()


class Activity(models.Model):
    """
    One Many-Small-Problems item: a single concept, short, low-pressure,
    with a designed expert explanation and known misconceptions.
    """

    topic = models.ForeignKey(
        Topic, on_delete=models.CASCADE, related_name="activities"
    )
    question_type = models.ForeignKey(
        QuestionType, on_delete=models.PROTECT, related_name="activities"
    )
    title = models.CharField(max_length=160)
    stem = models.TextField(help_text="The question the student answers.")
    code_snippet = models.TextField(blank=True)
    ai_suggestion = models.TextField(
        blank=True,
        help_text="Suggested line or fragment for AI-evaluation tasks.",
    )
    requirements_text = models.TextField(
        blank=True,
        help_text="Problem requirements used in prompt-construction tasks.",
    )
    choices = models.JSONField(
        default=list,
        blank=True,
        help_text='List of {"key": "a", "text": "..."} objects.',
    )
    correct_choice = models.CharField(
        max_length=40,
        blank=True,
        help_text="Choice key, or 'accept'/'reject' for AI evaluation.",
    )
    match_pairs = models.JSONField(
        default=list,
        blank=True,
        help_text=(
            'Matching items: list of {"term": ..., "definition": ...}. Terms '
            "must be unique. Authors list them in the correct pairing; the "
            "definitions are shuffled for display."
        ),
    )
    match_distractors = models.JSONField(
        default=list,
        blank=True,
        help_text=(
            "Extra definitions that match no term (list of strings). They stop "
            "the last pair being answered by elimination."
        ),
    )
    model_explanation = models.TextField(
        help_text="Expert explanation shown after the student responds."
    )
    success_criteria = models.TextField(
        help_text="What a strong answer includes. Used by feedback and mocks."
    )
    expected_concepts = models.JSONField(
        default=list,
        blank=True,
        help_text=(
            "Ideas a strong free-text answer should show, as a list of "
            '{"name": ..., "description": ..., "keywords": [...]}. '
            "'description' is read by LLM feedback; 'keywords' by keyword feedback."
        ),
    )
    misconceptions = models.JSONField(
        default=list,
        blank=True,
        help_text="Known novice misconceptions this item is designed around.",
    )
    hint_text = models.TextField(
        help_text="Scaffolding that does not give the answer away."
    )
    follow_up_idea = models.TextField(
        help_text="A targeted next micro-activity if the student struggles or succeeds."
    )
    bloom_level = models.PositiveSmallIntegerField(choices=BloomLevel.choices)
    estimated_minutes = models.PositiveSmallIntegerField(default=3)
    display_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["topic__display_order", "display_order", "id"]
        verbose_name_plural = "activities"

    def __str__(self):
        return f"{self.topic.name}: {self.title}"

    def get_absolute_url(self):
        return reverse("practice:activity", args=[self.pk])

    @property
    def bloom_label(self):
        return BloomLevel(self.bloom_level).label

    @property
    def is_choice_based(self):
        return bool(self.choices)

    @property
    def is_ai_evaluation(self):
        return self.question_type.slug == "ai-suggestion"

    @property
    def is_matching(self):
        return bool(self.match_pairs)

    def match_options(self) -> list[dict]:
        """
        The definitions in display order, as [{"key": "a", "text": ...}, ...].

        The order is a shuffle seeded by the title, so it is the same on every
        request and after every reseed (a stored answer keeps its meaning). It
        is re-drawn until no true definition sits at its own term's position,
        so the list never reads as a ready-made answer key.
        """
        texts = [p["definition"] for p in self.match_pairs] + list(self.match_distractors)
        n_pairs = len(self.match_pairs)
        order = texts
        for attempt in range(50):
            order = texts[:]
            random.Random(f"{self.title}|match|{attempt}").shuffle(order)
            if all(order[i] != texts[i] for i in range(n_pairs)):
                break
        return [{"key": "abcdefghij"[i], "text": t} for i, t in enumerate(order)]

    def match_answer_keys(self) -> list[str]:
        """The correct option key for each term, in match_pairs order."""
        by_text = {o["text"]: o["key"] for o in self.match_options()}
        return [by_text[p["definition"]] for p in self.match_pairs]

    def next_in_topic(self):
        """
        The next activity in (display_order, id) order. The id tie-break matters:
        several activities can share a display_order (same Bloom level), and a
        plain "display_order greater than" would skip all of them.
        """
        return (
            Activity.objects.filter(topic=self.topic)
            .filter(
                Q(display_order__gt=self.display_order)
                | Q(display_order=self.display_order, id__gt=self.id)
            )
            .order_by("display_order", "id")
            .first()
        )