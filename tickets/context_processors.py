from .models import Notification


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