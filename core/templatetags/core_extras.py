from django import template

register = template.Library()

@register.filter
def get_item(d, key):
    """Permet d'accéder à un dict dans un template: dict|get_item:key"""
    if d is None:
        return None
    if not isinstance(d, dict):
        return None
    return d.get(key) if isinstance(d, dict) else None
@register.simple_tag
def test_tag():
    return "OK TAG"
