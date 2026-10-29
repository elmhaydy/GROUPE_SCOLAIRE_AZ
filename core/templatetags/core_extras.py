from django import template
from accounts.models import get_user_avatar_url

register = template.Library()

@register.filter
def avatar_url(user):
    return get_user_avatar_url(user)

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

@register.filter
def initials(obj):
    """
    Retourne les 1ères lettres du nom / prénom en majuscules (ex: 'AB' pour Ali Bennani,
    ou pour une instance Eleve, Enseignant, Parent, User).
    """
    if not obj:
        return ""
    
    # Instance avec nom et prénom (Eleve, Enseignant, Parent, etc.)
    if hasattr(obj, 'nom') or hasattr(obj, 'prenom'):
        nom = (getattr(obj, 'nom', '') or '').strip()
        prenom = (getattr(obj, 'prenom', '') or '').strip()
        if nom and prenom:
            return f"{nom[0]}{prenom[0]}".upper()
        elif nom:
            return nom[:2].upper()
        elif prenom:
            return prenom[:2].upper()

    # Instance User
    if hasattr(obj, 'get_full_name'):
        first = (getattr(obj, 'first_name', '') or '').strip()
        last = (getattr(obj, 'last_name', '') or '').strip()
        if first and last:
            return f"{first[0]}{last[0]}".upper()
        elif last:
            return last[:2].upper()
        elif first:
            return first[:2].upper()
        username = (getattr(obj, 'username', '') or '').strip()
        return username[:2].upper()

    # Chaîne de caractères
    s = str(obj).strip()
    if not s:
        return ""
    words = s.split()
    if len(words) >= 2:
        return f"{words[0][0]}{words[1][0]}".upper()
    return s[:2].upper()

