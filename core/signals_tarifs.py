from decimal import Decimal
from django.apps import apps
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender="core.FraisNiveau")
def update_echeances_when_tarif_changes(sender, instance, created, **kwargs):
    Inscription = apps.get_model("core", "Inscription")
    EcheanceMensuelle = apps.get_model("core", "EcheanceMensuelle")

    mensuel = instance.frais_scolarite_mensuel or Decimal("0.00")
    frais_insc = instance.frais_inscription or Decimal("0.00")
    total = frais_insc + mensuel * Decimal("10")

    qs = Inscription.objects.filter(
        annee_id=instance.annee_id,
        groupe__niveau_id=instance.niveau_id,
        tarif_override=False,  # ✅ ne pas écraser les réductions personnalisées
    )

    if not qs.exists():
        return

    # ✅ update inscriptions standard
    Inscription.objects.filter(id__in=qs.values_list("id", flat=True)).update(
        frais_inscription_du=frais_insc,
        frais_scolarite_mensuel=mensuel,
        montant_total=total,
    )

    eleve_ids = list(qs.values_list("eleve_id", flat=True).distinct())

    # ✅ update seulement mois NON payés (paye == 0)
    echeances = EcheanceMensuelle.objects.filter(
        annee_id=instance.annee_id,
        eleve_id__in=eleve_ids,
    )

    for e in echeances:
        if (e.montant_paye or Decimal("0.00")) > Decimal("0.00"):
            # déjà payé => on touche rien
            continue

        if (e.montant_du or Decimal("0.00")) != mensuel:
            e.montant_du = mensuel

        e.refresh_statut(save=False)
        e.save(update_fields=["montant_du", "statut"])
