from .models import Notification


def _base_template_for(user):
    """Shared pages (create ticket, history, knowledge base...) extend this, so
    each role keeps its own sidebar instead of falling back to the employee one."""
    role = str(getattr(user, "role", "")).upper()
    if role == "ADMIN" or user.is_superuser:
        return "base_admin_dashboard.html"
    if role == "TECHNICIAN":
        return "base_technician_dashboard .html"
    return "base_dashboard.html"


def notifications(request):
    if not request.user.is_authenticated:
        return {"base_template": "base_dashboard.html"}

    role = str(getattr(request.user, "role", "")).upper()
    audience = "technician" if role == "TECHNICIAN" else "employee"

    qs = Notification.objects.filter(user=request.user, audience=audience)[:10]
    unread_count = Notification.objects.filter(
        user=request.user, audience=audience, is_read=False
    ).count()

    return {
        "notifications": qs,
        "unread_notifications_count": unread_count,
        "base_template": _base_template_for(request.user),
    }
