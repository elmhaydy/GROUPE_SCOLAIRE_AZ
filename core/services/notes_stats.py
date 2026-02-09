# core/services/notes_stats.py

from __future__ import annotations
from decimal import Decimal

from core.notes_utils import bulletin_data
from core.models import Periode, Inscription, Eleve




def moyenne_classe(periode: Periode, groupe) -> Decimal | None:
    """
    Moyenne générale de la classe (moyenne des moyennes générales des élèves du groupe).
    """
    eleves_ids = (
        Inscription.objects
        .filter(annee=periode.annee, groupe=groupe)
        .values_list("eleve_id", flat=True)
        .distinct()
    )

    moys = []
    for eid in eleves_ids:
        el = Eleve.objects.filter(id=eid).first()
        if not el:
            continue
        d = bulletin_data(el, periode)
        mg = d.get("moyenne_generale")
        if mg is not None:
            moys.append(Decimal(str(mg)))

    if not moys:
        return None
    return sum(moys) / Decimal(str(len(moys)))

