from decimal import Decimal
from datetime import date
from django.db import transaction
from django.utils import timezone

from core.models import (
    EleveTransport,
    Inscription,
    EcheanceTransportMensuelle,
)

MOIS_ORDER = [
    (1, 9,  "Septembre"),
    (2, 10, "Octobre"),
    (3, 11, "Novembre"),
    (4, 12, "Décembre"),
    (5, 1,  "Janvier"),
    (6, 2,  "Février"),
    (7, 3,  "Mars"),
    (8, 4,  "Avril"),
    (9, 5,  "Mai"),
    (10, 6, "Juin"),
]


def _safe_day(y, m, d=5):
    # on force un jour “safe” (ex: 5 du mois)
    return date(y, m, min(d, 28))


def build_transport_dates(annee) -> dict:
    """
    Retourne {mois_index: date_echeance} basé sur année scolaire.
    Hypothèse: annee.date_debut est en Septembre (ou proche).
    """
    if getattr(annee, "date_debut", None):
        start_year = annee.date_debut.year
        # si date_debut est Jan→Août, on considère que Sep est la même année (rare)
        # sinon Sep est start_year
        if annee.date_debut.month >= 9:
            y_sep = start_year
        else:
            y_sep = start_year  # on laisse simple
    else:
        today = timezone.now().date()
        y_sep = today.year

    # Sep..Dec => y_sep, Jan..Jun => y_sep+1
    dates = {}
    for idx, month, _ in MOIS_ORDER:
        y = y_sep if month >= 9 else (y_sep + 1)
        dates[idx] = _safe_day(y, month, 5)
    return dates


@transaction.atomic
def sync_transport_echeances_for_inscription(inscription_id: int):
    """
    Sync transport pour l'élève/année de l'inscription.
    Utilise EleveTransport (enabled + tarif_mensuel).
    """
    insc = (Inscription.objects
            .select_related("eleve", "annee", "groupe")
            .get(pk=inscription_id))

    eleve = insc.eleve
    annee = insc.annee
    groupe = insc.groupe

    tr = getattr(eleve, "transport", None)
    if not tr:
        # pas de config => on supprime les échéances non payées (si existent)
        EcheanceTransportMensuelle.objects.filter(
            eleve_id=eleve.id, annee_id=annee.id, montant_paye=Decimal("0.00")
        ).delete()
        return

    if not tr.enabled:
        # transport OFF => supprimer uniquement celles non payées
        EcheanceTransportMensuelle.objects.filter(
            eleve_id=eleve.id, annee_id=annee.id, montant_paye=Decimal("0.00")
        ).delete()
        return

    tarif = tr.tarif_mensuel or Decimal("0.00")
    if tarif <= Decimal("0.00"):
        # enabled mais tarif invalide => on fait rien (ou on supprime non payées)
        EcheanceTransportMensuelle.objects.filter(
            eleve_id=eleve.id, annee_id=annee.id, montant_paye=Decimal("0.00")
        ).delete()
        return

    dates = build_transport_dates(annee)

    # upsert 10 mois
    for idx, _, _ in MOIS_ORDER:
        obj, created = EcheanceTransportMensuelle.objects.get_or_create(
            eleve_id=eleve.id,
            annee_id=annee.id,
            mois_index=idx,
            defaults={
                "groupe": groupe,
                "date_echeance": dates[idx],
                "montant_du": tarif,
                "montant_paye": Decimal("0.00"),
                "statut": "A_PAYER",
            }
        )

        # si déjà payé => on ne touche PAS le montant_du (historique)
        if (obj.montant_paye or Decimal("0.00")) > Decimal("0.00") or obj.statut == "PAYE":
            # juste snapshot groupe/date si tu veux
            obj.groupe = groupe
            if not obj.date_echeance:
                obj.date_echeance = dates[idx]
            obj.save(update_fields=["groupe", "date_echeance"])
            continue

        # si non payé => on met tarif + groupe + date
        obj.groupe = groupe
        obj.date_echeance = dates[idx]
        obj.montant_du = tarif
        obj.montant_paye = Decimal("0.00")
        obj.refresh_statut(save=False)
        obj.save(update_fields=["groupe", "date_echeance", "montant_du", "montant_paye", "statut"])
