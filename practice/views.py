from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_http_methods

from practice.ai import get_ai_service
from practice.ai.base import ExerciseGenerator, ExplanationGenerator, HintGenerator
from practice.evaluation import StudentResponse, evaluate_response
from practice.models import Activity, QuestionType, Topic
from research.recording import record_attempt, record_hint


def _completed_ids(request):
    """Learner progress lives only in the session; it is not research data."""
    return [int(x) for x in request.session.get("completed_activity_ids", [])]


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
    topics = Topic.objects.prefetch_related("activities__question_type")
    completed = set(_completed_ids(request))
    return render(
        request,
        "practice/home.html",
        {
            "topics": topics,
            "question_types": QuestionType.objects.all(),
            "total_activities": Activity.objects.count(),
            "done": len(completed),
        },
    )


def topic_list(request):
    completed = set(_completed_ids(request))
    rows = []
    for topic in Topic.objects.prefetch_related("activities"):
        ids = [a.id for a in topic.activities.all()]
        rows.append(
            {
                "topic": topic,
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
        {"topic": topic, "completed": set(_completed_ids(request))},
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
            {"activity": item, "match_rows": _match_rows(item)},
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
            },
        )

    response = StudentResponse.from_post(request.POST)
    assessment = evaluate_response(item, response)
    record_attempt(request, item, response, assessment)

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

    return render(
        request,
        "practice/feedback.html",
        {
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
            "next_item": item.next_in_topic(),
        },
    )
