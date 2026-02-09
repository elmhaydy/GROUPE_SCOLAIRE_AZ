# core/services/parents.py
from typing import Optional
from core.models import Parent, ParentEleve

PRIORITY = {"PERE": 1, "MERE": 2, "TUTEUR": 3, "AUTRE": 4}

def get_primary_parent_for_eleve(eleve_id: int) -> Optional[Parent]:
    lien = (
        ParentEleve.objects
        .select_related("parent")
        .filter(eleve_id=eleve_id, parent__is_active=True)
        .order_by("lien")  # on va re-trier en python (plus sûr)
        .first()
    )
    if not lien:
        return None

    # Si tu veux réellement la priorité stricte:
    liens = list(
        ParentEleve.objects
        .select_related("parent")
        .filter(eleve_id=eleve_id, parent__is_active=True)
    )
    liens.sort(key=lambda x: PRIORITY.get(x.lien, 99))
    return liens[0].parent if liens else None
