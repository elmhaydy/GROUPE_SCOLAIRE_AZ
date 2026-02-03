# core/utils.py
from datetime import date as date_cls
from core.models import AnneeScolaire

MOIS_SCOLAIRES = {
    1: "Septembre",
    2: "Octobre",
    3: "Novembre",
    4: "Décembre",
    5: "Janvier",
    6: "Février",
    7: "Mars",
    8: "Avril",
    9: "Mai",
    10: "Juin",
}

def mois_nom(idx: int) -> str:
    try:
        idx = int(idx)
    except Exception:
        return ""
    return MOIS_SCOLAIRES.get(idx, f"M{idx}")

def mois_index_courant(annee: AnneeScolaire, today: date_cls) -> int:
    """
    Index mois scolaire AZ (1..10)
    Septembre=1 ... Juin=10
    Juillet/Août => 10 (fin année)
    """
    mapping = {9: 1, 10: 2, 11: 3, 12: 4, 1: 5, 2: 6, 3: 7, 4: 8, 5: 9, 6: 10}
    m = today.month
    if m not in mapping:
        return 10
    return mapping[m]
