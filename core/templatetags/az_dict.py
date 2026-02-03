from django import template

register = template.Library()

@register.filter
def dict_get(d, key):
    """Retourne d.get(key) ou None si d est None/non-dict."""
    if isinstance(d, dict):
        return d.get(key)
    return None

@register.filter
def dict_get_default(d, key_default):
    """
    Usage: {{ d|dict_get_default:"key|[]" }}
    key_default = "KEY|DEFAULT"
    """
    if not isinstance(d, dict):
        d = {}
    try:
        key, default = key_default.split("|", 1)
    except ValueError:
        key, default = key_default, ""
    val = d.get(key)
    return val if val not in (None, "") else default
