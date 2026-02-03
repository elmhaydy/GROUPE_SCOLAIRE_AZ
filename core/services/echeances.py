from decimal import Decimal
from datetime import date as date_cls
from django.db import transaction
from dateutil.relativedelta import relativedelta

from core.models import Inscription, EcheanceMensuelle

MONTHS_COUNT = 10  # Sep -> Jun


@transaction.atomic
def sync_echeances_with_tarif(inscription_id: int) -> None:
    """
    Sync des 10 échéances (Sep->Jun) pour une inscription.
    ✅ Met à jour uniquement les mois NON payés (montant_paye == 0).
    ✅ Ne casse jamais un mois déjà payé / partiellement payé.
    """

    insc = (
        Inscription.objects
        .select_related("eleve", "annee", "groupe")
        .get(pk=inscription_id)
    )

    start = insc.annee.date_debut
    start_first = date_cls(start.year, start.month, 1)

    mensuel = insc.frais_scolarite_mensuel or Decimal("0.00")

    for i in range(MONTHS_COUNT):
        mois_index = i + 1  # 1..10
        d = start_first + relativedelta(months=i)
        date_echeance = d

        obj, created = EcheanceMensuelle.objects.get_or_create(
            eleve_id=insc.eleve_id,
            annee_id=insc.annee_id,
            mois_index=mois_index,
            defaults={
                "groupe_id": insc.groupe_id,
                "date_echeance": date_echeance,
                "montant_du": mensuel,
                "montant_paye": Decimal("0.00"),
                "statut": "A_PAYER",
            },
        )

        updated_fields = []

        # ✅ toujours sync groupe/date
        if obj.groupe_id != insc.groupe_id:
            obj.groupe_id = insc.groupe_id
            updated_fields.append("groupe")

        if obj.date_echeance != date_echeance:
            obj.date_echeance = date_echeance
            updated_fields.append("date_echeance")

        # ✅ NE CHANGER LE PRIX QUE SI AUCUN PAIEMENT
        paid = obj.montant_paye or Decimal("0.00")
        is_already_paid_somehow = (paid > Decimal("0.00")) or (obj.statut == "PAYE")

        if not is_already_paid_somehow:
            # si pas payé → on peut appliquer le nouveau mensuel
            if (obj.montant_du or Decimal("0.00")) != mensuel:
                obj.montant_du = mensuel
                updated_fields.append("montant_du")
        else:
            # sécurité : du ne doit jamais être < payé
            if (obj.montant_du or Decimal("0.00")) < paid:
                obj.montant_du = paid
                updated_fields.append("montant_du")

        if updated_fields:
            obj.save(update_fields=updated_fields)

        # ✅ recalcul statut
        obj.refresh_statut(save=True)

    # sécurité : supprimer hors 1..10
    EcheanceMensuelle.objects.filter(
        eleve_id=insc.eleve_id,
        annee_id=insc.annee_id,
    ).exclude(
        mois_index__in=range(1, MONTHS_COUNT + 1)
    ).delete()
