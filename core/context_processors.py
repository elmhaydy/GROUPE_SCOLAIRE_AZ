# core/context_processors.py
from .models import AnneeScolaire


def annee_active(request):
    """
    Rend disponible dans tous les templates:
    - annee_active (objet ou None)
    """
    active = AnneeScolaire.objects.filter(is_active=True).first()
    return {"annee_active": active}

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
