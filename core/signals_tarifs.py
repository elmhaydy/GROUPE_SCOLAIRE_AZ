# core/signals_tarifs.py
from decimal import Decimal
from django.apps import apps
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender="core.FraisNiveau")
def update_echeances_when_tarif_changes(sender, instance, created, **kwargs):
    """
    ✅ Quand FraisNiveau change:
    - Maj INSCRIPTIONS standard (tarif_override=False)
    - Maj ECHEANCES NON PAYEES pour TOUS les élèves du niveau
      (condition: montant_paye == 0 et statut != PAYE)
    - Ne touche JAMAIS aux mois payés/partiels
    """

    Inscription = apps.get_model("core", "Inscription")
    EcheanceMensuelle = apps.get_model("core", "EcheanceMensuelle")

    mensuel = instance.frais_scolarite_mensuel or Decimal("0.00")
    frais_insc = instance.frais_inscription or Decimal("0.00")
    total = frais_insc + mensuel * Decimal("10")

    def _apply():
        # 1) Toutes les inscriptions du niveau (override ou non)
        inscs_all = Inscription.objects.filter(
            annee_id=instance.annee_id,
            groupe__niveau_id=instance.niveau_id,
        )

        if not inscs_all.exists():
            return

        # 2) Mettre à jour Inscription seulement si pas override
        inscs_std = inscs_all.filter(tarif_override=False)
        if inscs_std.exists():
            inscs_std.update(
                frais_inscription_du=frais_insc,
                frais_scolarite_mensuel=mensuel,
                montant_total=total,
            )

        # 3) Mettre à jour les échéances NON payées pour tous
        # IMPORTANT: on filtre par inscription_id (clé réelle)
        echeances = (
            EcheanceMensuelle.objects
            .select_related("inscription")
            .filter(
                inscription_id__in=inscs_all.values_list("id", flat=True),
                montant_paye=Decimal("0.00"),
            )
            .exclude(statut="PAYE")
        )

        for e in echeances:
            insc = e.inscription
            changed = False

            # réparer snapshot
            if e.eleve_id != insc.eleve_id:
                e.eleve_id = insc.eleve_id
                changed = True
            if e.annee_id != insc.annee_id:
                e.annee_id = insc.annee_id
                changed = True
            if e.groupe_id != insc.groupe_id:
                e.groupe_id = insc.groupe_id
                changed = True

            # appliquer nouveau mensuel (uniquement non payé)
            if (e.montant_du or Decimal("0.00")) != mensuel:
                e.montant_du = mensuel
                changed = True

            if changed:
                # statut cohérent (puisque paye=0)
                e.statut = "PAYE" if mensuel <= Decimal("0.00") else "A_PAYER"
                e.save(update_fields=["eleve_id", "annee_id", "groupe_id", "montant_du", "statut"])

    transaction.on_commit(_apply)
