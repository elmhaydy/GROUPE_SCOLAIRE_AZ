# core/templatetags/auth_extras.py
from django import template

register = template.Library()

@register.filter
def has_group(user, group_name: str) -> bool:
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return user.groups.filter(name=group_name).exists()

@register.filter
def has_any_group(user, group_names: str) -> bool:
    """
    Utilisation:
      {% if request.user|has_any_group:"ADMIN,SCOLARITE" %}
    """
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True

    names = [g.strip() for g in (group_names or "").split(",") if g.strip()]
    if not names:
        return False
    return user.groups.filter(name__in=names).exists()
