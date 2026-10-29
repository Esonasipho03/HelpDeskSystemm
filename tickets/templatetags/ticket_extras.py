# templatetags/ticket_extras.py
import re
from django import template
register = template.Library()

@register.filter
def is_admin(user):
    role = str(getattr(user, "role", "")).upper()
    return role == "ADMIN" or user.is_superuser


def _names(user):
    first = (getattr(user, "first_name", "") or "").strip()
    last = (getattr(user, "last_name", "") or "").strip()
    return first, last


@register.filter
def display_name(user):
    """Full name if set, otherwise a tidy version of the username."""
    first, last = _names(user)
    full = f"{first} {last}".strip()
    if full:
        return full
    username = (getattr(user, "username", "") or "").strip()
    return re.sub(r"[._\-]+", " ", username).strip().title() or "User"


@register.filter
def initials(user):
    """'John Doe' -> 'JD', 'Admin' -> 'A', username 'jane.smith' -> 'JS'."""
    first, last = _names(user)
    if first or last:
        if not last and " " in first:
            parts = first.split()
            letters = parts[0][:1] + parts[-1][:1]
        else:
            letters = first[:1] + last[:1]
    else:
        username = (getattr(user, "username", "") or "").strip()
        parts = [p for p in re.split(r"[._\-\s]+", username) if p]
        letters = (parts[0][:1] + (parts[1][:1] if len(parts) > 1 else "")) if parts else ""
    return letters.upper() or "?"
