# core/services_absences_profs.py
from datetime import date, timedelta
from django.db.models import Sum
from .models import Seance, AbsenceProf, AnneeScolaire, Enseignant

MAP_JOUR = {"LUN": 0, "MAR": 1, "MER": 2, "JEU": 3, "VEN": 4, "SAM": 5}

def month_range(year: int, month: int):
    start = date(year, month, 1)
    if month == 12:
        end = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        end = date(year, month + 1, 1) - timedelta(days=1)
    return start, end

def count_weekday_in_interval(d0: date, d1: date, weekday: int) -> int:
    """
    Nombre de fois que 'weekday' apparaît entre d0 et d1 inclus.
    weekday: 0=lundi ... 6=dimanche
    """
    if d1 < d0:
        return 0
    # avancer jusqu'au premier 'weekday'
    delta = (weekday - d0.weekday()) % 7
    first = d0 + timedelta(days=delta)
    if first > d1:
        return 0
    return 1 + ( (d1 - first).days // 7 )

def stats_mensuelles_prof(*, enseignant: Enseignant, annee: AnneeScolaire, year: int, month: int) -> dict:
    m0, m1 = month_range(year, month)

    # on intersecte le mois avec la période de l'année scolaire
    d0 = max(m0, annee.date_debut)
    d1 = min(m1, annee.date_fin)

    # minutes prévues = somme( occurrences_mois(seance.jour) * duree_minutes )
    seances = Seance.objects.filter(annee=annee, enseignant=enseignant)

    prevues = 0
    for s in seances:
        wd = MAP_JOUR.get(s.jour)
        if wd is None:
            continue
        occ = count_weekday_in_interval(d0, d1, wd)
        prevues += occ * (s.duree_minutes or 0)

    manquees = (
        AbsenceProf.objects
        .filter(annee=annee, enseignant=enseignant, date__gte=d0, date__lte=d1)
        .aggregate(x=Sum("minutes_perdues"))["x"] or 0
    )

    faites = max(prevues - manquees, 0)

    return {
        "d0": d0, "d1": d1,
        "prevues_minutes": prevues,
        "manquees_minutes": manquees,
        "faites_minutes": faites,
        "prevues_heures": round(prevues / 60, 2),
        "manquees_heures": round(manquees / 60, 2),
        "faites_heures": round(faites / 60, 2),
    }
