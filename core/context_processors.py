# core/context_processors.py
from .models import AnneeScolaire
from .models_notifications import Notification


def annee_active(request):
    """
    Rend disponible dans tous les templates:
    - annee_active (objet ou None)
    """
    active = AnneeScolaire.objects.filter(is_active=True).first()
    return {"annee_active": active}

def notifications(request):
    if not getattr(request, "user", None) or not request.user.is_authenticated:
        return {"notif_unread_count": 0, "notif_recent": []}
    qs    = Notification.objects.filter(recipient=request.user).order_by("-created_at")
    count = qs.filter(read=False).count()
    recent = list(qs.select_related("eleve", "parent")[:6])
    return {"notif_unread_count": count, "notif_recent": recent}


def roles_flags(request):
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {
            "is_admin": False,
            "is_scolarite": False,
            "is_compta": False,
            "is_pedagogique": False,
        }
    # Superuser = accès total
    if user.is_superuser:
        return {
            "is_admin": True,
            "is_scolarite": True,
            "is_compta": True,
            "is_pedagogique": True,
        }

    names = set(user.groups.values_list("name", flat=True))
    
    return {
        "is_admin": "ADMIN" in names or "SUPER_ADMIN" in names,
        "is_super_admin": "SUPER_ADMIN" in names,
        "is_scolarite": "SCOLARITE" in names,
        "is_compta": "COMPTABLE" in names,
        "is_pedagogique": "PEDAGOGIQUE" in names,
        "is_secretaire": "SECRETAIRE" in names,
        "is_parent": "PARENT" in names,
    }


def user_avatar(request):
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {"user_avatar_url": None}
    from accounts.models import get_user_avatar_url
    return {"user_avatar_url": get_user_avatar_url(user)}


def user_base_template(request):
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {"base_template": "admin/base_admin.html"}

    if hasattr(user, "eleve_profile") and user.eleve_profile:
        return {"base_template": "eleve/base.html"}

    groups = set(g.name.upper() for g in user.groups.all())
    if "ELEVE" in groups or "ÉLÈVE" in groups or "STUDENT" in groups:
        return {"base_template": "eleve/base.html"}

    if hasattr(user, "enseignant_profile") and user.enseignant_profile:
        return {"base_template": "prof/base_prof.html"}

    if "PROF" in groups or "ENSEIGNANT" in groups or "TEACHER" in groups or "PROFESSEUR" in groups:
        return {"base_template": "prof/base_prof.html"}

    return {"base_template": "admin/base_admin.html"}
