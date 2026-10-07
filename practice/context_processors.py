from research.conf import analytics_enabled


def studio_context(request):
    return {
        "completed_count": len(request.session.get("completed_activity_ids", [])),
        # Shown in the footer so participants always know what is recorded.
        "analytics_enabled": analytics_enabled(),
    }
