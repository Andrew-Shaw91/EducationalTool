"""
Deterministic choice of the next activity for a learner in a topic and level.

Activities are grouped by (topic, Bloom level). Within one group the order is:

  1. activities the learner has not tried yet, before any they have;
  2. among tried ones, the least recently attempted first;
  3. then the curriculum order (display_order, then id).

So after a wrong answer the learner gets a DIFFERENT unseen activity from the
same topic and level whenever one exists, and only repeats one (the one they
saw longest ago) once the group is used up.

There is no randomness, so the same history always gives the same activity.
"""

from collections.abc import Sequence

from practice.models import Activity


def select_activity(
    level: int,
    *,
    topic=None,
    attempted_order: Sequence[int] = (),
) -> Activity | None:
    """
    Pick an activity at exactly `level`, within `topic` when one is given.

    `attempted_order` lists activity ids the learner has attempted, oldest
    first. Returns None if the bank has no activity in that group.
    """
    candidates = Activity.objects.filter(bloom_level=level).select_related(
        "topic", "question_type"
    )
    if topic is not None:
        candidates = candidates.filter(topic=topic)

    seen_at = {activity_id: position for position, activity_id in enumerate(attempted_order)}

    def sort_key(activity: Activity):
        attempted = activity.pk in seen_at
        return (
            attempted,
            seen_at.get(activity.pk, 0),
            activity.topic.display_order,
            activity.display_order,
            activity.pk,
        )

    return min(candidates, key=sort_key, default=None)
