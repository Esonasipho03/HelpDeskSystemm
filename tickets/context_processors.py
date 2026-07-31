from .models import ITTask, ITTaskStatus, Notification


def notifications(request):
    if not request.user.is_authenticated:
        return {}

    role = str(getattr(request.user, "role", "")).upper()
    audience = "technician" if role == "TECHNICIAN" else "employee"

    qs = Notification.objects.filter(user=request.user, audience=audience)[:10]
    unread_count = Notification.objects.filter(
        user=request.user, audience=audience, is_read=False
    ).count()

    return {
        "notifications": qs,
        "unread_notifications_count": unread_count,
    }


def it_tasks(request):
    """Exposes the open IT-task count so the sidebar badge shows on
    every technician page, not just the dashboard."""
    if not request.user.is_authenticated:
        return {}

    role = str(getattr(request.user, "role", "")).upper()
    if role != "TECHNICIAN":
        return {}

    open_count = ITTask.objects.filter(
        assigned_to=request.user
    ).exclude(status=ITTaskStatus.COMPLETED).count()

    return {
        "it_tasks_open_count": open_count,
    }