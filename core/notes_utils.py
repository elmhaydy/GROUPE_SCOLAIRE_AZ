from decimal import Decimal
from django.db.models import Avg

from .models import Note, Matiere, Periode, Eleve, Inscription


def _to20(valeur: Decimal, note_max: int) -> Decimal:
    """
    Normalise une note sur 20.
    """
    if note_max in (None, 0):
        return Decimal("0.00")
    return (Decimal(valeur) * Decimal("20")) / Decimal(note_max)


def moyenne_matiere_ponderee(eleve, periode, matiere):
    notes = (
        Note.objects
        .select_related("evaluation")
        .filter(eleve=eleve, evaluation__periode=periode, evaluation__matiere=matiere)
    )

    total_points = Decimal("0.00")
    total_coef = Decimal("0.00")

    for n in notes:
        ev = n.evaluation
        coef_ev = getattr(ev, "coefficient", Decimal("1.00")) or Decimal("1.00")
        note20 = _to20(n.valeur, ev.note_max)
        total_points += (note20 * Decimal(coef_ev))
        total_coef += Decimal(coef_ev)

    if total_coef == 0:
        return None

    return total_points / total_coef


def moyenne_generale_ponderee(eleve, periode):
    """
    Moyenne générale pondérée par coefficient matière.
    - moyenne_matiere (déjà pondérée par coef évaluation)
    - puis pondération par matiere.coefficient
    """
    matieres = Matiere.objects.filter(is_active=True)

    total_points = Decimal("0.00")
    total_coef = Decimal("0.00")

    for m in matieres:
        moy_m = moyenne_matiere_ponderee(eleve, periode, m)
        if moy_m is None:
            continue
        coef_m = getattr(m, "coefficient", Decimal("1.00")) or Decimal("1.00")
        total_points += (Decimal(moy_m) * Decimal(coef_m))
        total_coef += Decimal(coef_m)

    if total_coef == 0:
        return None
    return total_points / total_coef


def bulletin_data(eleve, periode):
    """
    Données bulletin: moyennes par matière + moyenne générale pondérée.
    """
    matieres = Matiere.objects.filter(is_active=True).order_by("nom")

    rows = []
    for m in matieres:
        moy = moyenne_matiere_ponderee(eleve, periode, m)
        if moy is None:
            continue
        rows.append({
            "matiere": m.nom,
            "coef": float(getattr(m, "coefficient", 1) or 1),
            "moyenne": float(moy),
        })

    mg = moyenne_generale_ponderee(eleve, periode)
    mg_val = float(mg) if mg is not None else None

    return {
        "rows": rows,
        "moyenne_generale": mg_val,
    }


def classement_groupe(periode, groupe):
    """
    Classement (rang) des élèves du groupe pour une période.
    On prend les élèves inscrits dans (periode.annee, groupe)
    et on calcule moyenne_generale_ponderee.
    Retour: liste triée desc: [(eleve, moyenne), ...]
    """
    inscriptions = (
        Inscription.objects
        .select_related("eleve")
        .filter(annee=periode.annee, groupe=groupe)
        .order_by("eleve__nom", "eleve__prenom")
    )
    eleves = [i.eleve for i in inscriptions]

    results = []
    for e in eleves:
        mg = moyenne_generale_ponderee(e, periode)
        if mg is None:
            mg = Decimal("0.00")
        results.append((e, mg))

    results.sort(key=lambda x: x[1], reverse=True)
    return results


def rang_eleve(periode, groupe, eleve):
    """
    Rang 1..N et effectif.
    """
    classement = classement_groupe(periode, groupe)
    n = len(classement)
    rank = None
    for i, (e, _) in enumerate(classement, start=1):
        if e.id == eleve.id:
            rank = i
            break
    return rank, n
