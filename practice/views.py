from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_http_methods

from practice import progression
from practice.ai import get_ai_service
from practice.ai.base import ExerciseGenerator, ExplanationGenerator, HintGenerator
from practice.evaluation import StudentResponse, evaluate_response
from practice.models import Activity, Topic
from research import progress as learner_progress
from research.recording import record_attempt, record_hint

ATTEMPT_ORDER_KEY = "attempt_order"
ATTEMPT_ORDER_LIMIT = 500


def _completed_ids(request):
    """Learner progress lives only in the session; it is not research data."""
    return [int(x) for x in request.session.get("completed_activity_ids", [])]


def _attempt_order(request) -> list[int]:
    """Activity ids the learner has attempted, oldest first (session only)."""
    return [int(x) for x in request.session.get(ATTEMPT_ORDER_KEY, [])]


def _note_attempt(request, activity_id: int) -> None:
    order = [i for i in _attempt_order(request) if i != activity_id]
    order.append(activity_id)
    request.session[ATTEMPT_ORDER_KEY] = order[-ATTEMPT_ORDER_LIMIT:]


def _last_topic_id(request) -> int | None:
    order = _attempt_order(request)
    if not order:
        return None
    return Activity.objects.filter(pk=order[-1]).values_list("topic_id", flat=True).first()


def _working_topic(request, preferred: Topic | None = None) -> Topic | None:
    """
    The topic the learner should work on: the one they are in (or `preferred`)
    until it is completed, then the next unfinished topic in curriculum order.
    None once every topic is completed.
    """
    topics = list(Topic.objects.all())
    preferred_id = preferred.pk if preferred else _last_topic_id(request)
    chosen = progression.next_topic_id(
        [t.pk for t in topics], learner_progress.completed_topic_ids(request), preferred_id
    )
    return next((t for t in topics if t.pk == chosen), None)


def _choose_next(request, topic: Topic, level: int):
    """
    The next exercise within `topic` at `level`, via the exercise generator.
    A different, unseen activity is preferred; see practice.selection.
    """
    generator = ExerciseGenerator(get_ai_service())
    return generator.next_activity(level, topic, _attempt_order(request))


def _progress_context(request, item=None, topic=None) -> dict:
    """Progression display data for a topic; empty when the adaptive mechanism is off."""
    topic = item.topic if item is not None else topic
    view = learner_progress.current_view(request, topic) if topic else None
    if view is None:
        return {}
    return {
        "progress": view,
        "off_level": item is not None and item.bloom_level != view.level,
    }


def _topic_rows(request, topics):
    """Each topic with the learner's standing in it (None when adaptive is off)."""
    config = progression.get_config()
    if not config.enabled:
        return [{"topic": t, "view": None, "started": False} for t in topics]
    states = learner_progress.topic_states(request, config)
    rows = []
    for t in topics:
        state = states.get(t.pk)
        rows.append(
            {
                "topic": t,
                "view": progression.describe(state or progression.initial_state(config), config, t.name),
                "started": state is not None,
            }
        )
    return rows


def _match_rows(item, posted=None):
    """Terms with the definition key chosen so far, so a hint keeps the student's picks."""
    if not item.is_matching:
        return []
    posted = posted or {}
    return [
        {"index": i, "term": pair["term"], "selected": posted.get(f"match_{i}", "")}
        for i, pair in enumerate(item.match_pairs)
    ]


def home(request):
    topics = list(Topic.objects.prefetch_related("activities__question_type"))
    completed = set(_completed_ids(request))
    context = {
        "topics": topics,
        "topic_rows": _topic_rows(request, topics),
        "total_activities": Activity.objects.count(),
        "done": len(completed),
    }
    if progression.get_config().enabled:
        working = _working_topic(request)
        context["all_topics_complete"] = working is None and bool(topics)
        if working is not None:
            context.update(_progress_context(request, topic=working))
    return render(request, "practice/home.html", context)


@require_GET
def next_activity(request):
    """
    Send the learner to their next activity.

    Without a parameter that is the topic they are working on (the next topic
    only once the current one is complete), at their level in it. With
    ?topic=<slug> it is that topic at the learner's level in it. Read-only: it
    never changes a level; levels only move when an activity is submitted.
    """
    config = progression.get_config()
    if not config.enabled:
        return redirect("practice:topics")

    topic = Topic.objects.filter(slug=request.GET.get("topic", "")).first()
    if topic is None:
        topic = _working_topic(request)
    if topic is None:  # every topic completed
        return redirect("practice:topics")

    state = learner_progress.current_state(request, topic, config)
    choice = _choose_next(request, topic, state.level)
    if choice is None:
        return redirect("practice:topics")
    return redirect(choice.activity)


def topic_list(request):
    completed = set(_completed_ids(request))
    topics = list(Topic.objects.prefetch_related("activities"))
    rows = []
    for row in _topic_rows(request, topics):
        ids = [a.id for a in row["topic"].activities.all()]
        rows.append(
            {
                **row,
                "total": len(ids),
                "done": sum(1 for i in ids if i in completed),
            }
        )
    return render(request, "practice/topics.html", {"rows": rows})


def topic_detail(request, slug):
    topic = get_object_or_404(
        Topic.objects.prefetch_related("activities__question_type"), slug=slug
    )
    return render(
        request,
        "practice/topic_detail.html",
        {
            "topic": topic,
            "completed": set(_completed_ids(request)),
            **_progress_context(request, topic=topic),
        },
    )


@require_http_methods(["GET", "POST"])
def activity(request, pk):
    item = get_object_or_404(
        Activity.objects.select_related("topic", "question_type"), pk=pk
    )
    ai = get_ai_service()

    if request.method == "GET":
        return render(
            request,
            "practice/activity.html",
            {
                "activity": item,
                "match_rows": _match_rows(item),
                **_progress_context(request, item),
            },
        )

    if request.POST.get("action") == "hint":
        record_hint(request, item)
        return render(
            request,
            "practice/activity.html",
            {
                "activity": item,
                "hint": HintGenerator(ai).generate(item),
                "posted": request.POST,
                "match_rows": _match_rows(item, request.POST),
                **_progress_context(request, item),
            },
        )

    response = StudentResponse.from_post(request.POST)
    # 1. The existing scoring judges the answer.
    assessment = evaluate_response(item, response)
    # 2. The deterministic rules update the level from that judgement. The AI
    #    plays no part. State and research log change together or not at all.
    with transaction.atomic():
        update = learner_progress.process_submission(request, item, assessment)
        record_attempt(request, item, response, assessment, update)
    _note_attempt(request, item.id)

    completed = _completed_ids(request)
    if item.id not in completed:
        completed.append(item.id)
        request.session["completed_activity_ids"] = completed

    # The feedback page is rendered straight from the in-memory assessment, so
    # it works identically whether or not analytics storage is enabled.
    selected_label = ""
    for choice in item.choices:
        if choice.get("key") == response.selected_choice:
            selected_label = choice.get("text", "")
            break

    # 3. Only now does the generator hear about the level, and only as input.
    #    Wrong or right, the learner stays in this topic at their level until the
    #    rules move them; only a completed topic hands over to the next one.
    adaptive = {}
    next_item = item.next_in_topic()
    if update.active:
        next_item = None  # progression, not fixed order, decides what comes next
        topic = item.topic if not update.view.completed else _working_topic(request, item.topic)
        recommended = None
        if topic is not None:
            level = learner_progress.current_state(request, topic).level
            picked = _choose_next(request, topic, level)
            recommended = picked.activity if picked else None
        adaptive = {
            "progress": update.view,
            "update": update.result,
            "off_level": not update.result.counted and not update.view.completed,
            "recommended": recommended,
            "moves_to_new_topic": bool(recommended and recommended.topic_id != item.topic_id),
            "all_topics_complete": topic is None,
        }

    return render(
        request,
        "practice/feedback.html",
        {
            **adaptive,
            "activity": item,
            "response": response,
            "assessment": assessment,
            "score_percent": None
            if assessment.score is None
            else round(assessment.score * 100),
            "has_concepts": bool(item.expected_concepts),
            "matched_count": sum(r["ok"] for r in assessment.match_results),
            "selected_label": selected_label,
            "follow_up": ExerciseGenerator(ai).generate(item, assessment.is_correct),
            "extra_explanation": ExplanationGenerator(ai).generate(item),
            "extra_example": ai.extra_example(item),
            "next_item": next_item,
        },
    )
