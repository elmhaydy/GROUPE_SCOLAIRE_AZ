# core/services/echeances.py
from decimal import Decimal
from datetime import date as date_cls
from django.db import transaction
from dateutil.relativedelta import relativedelta

from core.models import Inscription, EcheanceMensuelle

MONTHS_COUNT = 10


@transaction.atomic
def sync_echeances_with_tarif(inscription_id: int) -> None:
    insc = (
        Inscription.objects
        .select_related("annee", "groupe")
        .get(pk=inscription_id)
    )

    start = insc.annee.date_debut
    start_first = date_cls(start.year, start.month, 1)

    mensuel = insc.frais_scolarite_mensuel or Decimal("0.00")

    for i in range(MONTHS_COUNT):
        mois_index = i + 1
        date_echeance = start_first + relativedelta(months=i)

        obj, created = EcheanceMensuelle.objects.get_or_create(
            inscription_id=insc.id,
            mois_index=mois_index,
            defaults={
                "eleve_id": insc.eleve_id,
                "annee_id": insc.annee_id,
                "groupe_id": insc.groupe_id,
                "date_echeance": date_echeance,
                "montant_du": mensuel,
                "montant_paye": Decimal("0.00"),
                "statut": "A_PAYER",
            }
        )

        updated = []

        # snapshot toujours correct
        if obj.eleve_id != insc.eleve_id:
            obj.eleve_id = insc.eleve_id; updated.append("eleve_id")
        if obj.annee_id != insc.annee_id:
            obj.annee_id = insc.annee_id; updated.append("annee_id")
        if obj.groupe_id != insc.groupe_id:
            obj.groupe_id = insc.groupe_id; updated.append("groupe_id")
        if obj.date_echeance != date_echeance:
            obj.date_echeance = date_echeance; updated.append("date_echeance")

        # changer prix seulement si non payé
        paid = obj.montant_paye or Decimal("0.00")
        if paid == Decimal("0.00") and obj.statut != "PAYE":
            if (obj.montant_du or Decimal("0.00")) != mensuel:
                obj.montant_du = mensuel
                updated.append("montant_du")

        if updated:
            obj.save(update_fields=sorted(set(updated)))

        obj.refresh_statut(save=True)

    # supprimer hors 1..10 mais uniquement pour cette inscription
    EcheanceMensuelle.objects.filter(inscription_id=insc.id).exclude(
        mois_index__in=range(1, MONTHS_COUNT + 1)
    ).delete()
