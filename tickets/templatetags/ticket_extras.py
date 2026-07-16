# templatetags/ticket_extras.py
from django import template
register = template.Library()

@register.filter
def is_admin(user):
    role = str(getattr(user, "role", "")).upper()
    return role == "ADMIN" or user.is_superuser