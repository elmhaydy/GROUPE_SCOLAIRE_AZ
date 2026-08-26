# core/signals.py
from __future__ import annotations

from datetime import date as date_cls
from decimal import Decimal

from django.apps import apps
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from .utils_users import get_or_create_user_with_group
from core.services.sms_dispatcher import send_event


def _first_parent_for_eleve(eleve):
    if not eleve:
        return None
    ParentEleve = apps.get_model("core", "ParentEleve")
    lien = (
        ParentEleve.objects
        .select_related("parent")
        .filter(eleve=eleve, parent__is_active=True)
        .order_by("id")
        .first()
    )
    return lien.parent if lien else None


# =========================================================
# 1) Paiement -> Recouvrement (met statut REGLE si soldé)
# =========================================================
@receiver(post_save, sender="core.Paiement")
def auto_regle_recouvrement(sender, instance, created: bool, **kwargs):
    if not created:
        return

    Recouvrement = apps.get_model("core", "Recouvrement")

    try:
        dossier = instance.inscription.recouvrement
    except Recouvrement.DoesNotExist:
        return

    dossier.refresh_statut_si_regle(save=True)

    parent = _first_parent_for_eleve(getattr(instance.inscription, "eleve", None))
    if not parent:
        return

    eleve = instance.inscription.eleve
    payload = {
        "parent": parent,
        "eleve": f"{eleve.nom} {eleve.prenom}".strip(),
        "groupe": getattr(getattr(instance.inscription, "groupe", None), "nom", "") or "",
        "montant": instance.montant,
        "date": instance.date_paiement.strftime("%d/%m/%Y") if instance.date_paiement else timezone.now().strftime("%d/%m/%Y"),
        "ref": instance.reference or f"PAY-{instance.pk}",
    }
    transaction.on_commit(lambda: send_event("paiement", payload))


# =========================================================
# 2) Année scolaire -> créer Semestre 1 & 2 (à la création)
# =========================================================
@receiver(post_save, sender="core.AnneeScolaire")
def creer_periodes_auto(sender, instance, created: bool, **kwargs):
    if not created:
        return

    Periode = apps.get_model("core", "Periode")
    Periode.objects.get_or_create(annee=instance, ordre=1)
    Periode.objects.get_or_create(annee=instance, ordre=2)

# =========================================================
# 3) Inscription -> créer les échéances (Sep -> Jun = 10 mois)
# =========================================================
MONTHS_COUNT = 10

def first_day_of_month(d: date_cls) -> date_cls:
    return date_cls(d.year, d.month, 1)

def add_months_first_day(d: date_cls, months: int) -> date_cls:
    y = d.year + (d.month - 1 + months) // 12
    m = (d.month - 1 + months) % 12 + 1
    return date_cls(y, m, 1)

@receiver(post_save, sender="core.Inscription")
def creer_echeances_sep_juin(sender, instance, created: bool, **kwargs):
    if not created:
        return

    EcheanceMensuelle = apps.get_model("core", "EcheanceMensuelle")

    mensuel = instance.frais_scolarite_mensuel or Decimal("0.00")
    start_school = first_day_of_month(instance.annee.date_debut)  # ex: 2025-09-01

    for i in range(1, MONTHS_COUNT + 1):  # 1..10
        d_ech = add_months_first_day(start_school, i - 1)

        # ✅ conforme DB + conforme modèle
        EcheanceMensuelle.objects.get_or_create(
            inscription=instance,
            mois_index=i,
            defaults={
                "eleve_id": instance.eleve_id,
                "annee_id": instance.annee_id,
                "groupe_id": instance.groupe_id,
                "date_echeance": d_ech,
                "montant_du": mensuel,
                "montant_paye": Decimal("0.00"),
                "statut": "A_PAYER",
            },
        )









# =========================================================
# 5) Parent -> rien
# =========================================================
@receiver(post_save, sender="core.Parent")
def noop_parent(sender, instance, created: bool, **kwargs):
    return


@receiver(post_save, sender="core.Absence")
def auto_sms_absence(sender, instance, created: bool, **kwargs):
    if not created:
        return

    parent = _first_parent_for_eleve(getattr(instance, "eleve", None))
    if not parent:
        return

    eleve = instance.eleve
    payload = {
        "parent": parent,
        "eleve": f"{eleve.nom} {eleve.prenom}".strip(),
        "groupe": getattr(getattr(instance, "groupe", None), "nom", "") or "",
        "type": instance.get_type_display(),
        "date": instance.date.strftime("%d/%m/%Y") if instance.date else timezone.now().strftime("%d/%m/%Y"),
    }
    transaction.on_commit(lambda: send_event("absence", payload))


# =========================================================
# 5) Enseignant -> création user PROF auto
# =========================================================
@receiver(post_save, sender="core.Enseignant")
def create_user_for_enseignant(sender, instance, created: bool, **kwargs):
    if not instance.matricule:
        return
    if instance.user_id:
        return

    TempPassword = apps.get_model("core", "TempPassword")

    user, pwd, created_user = get_or_create_user_with_group(instance.matricule.strip(), "PROF", length=10)

    user.first_name = instance.prenom or ""
    user.last_name = instance.nom or ""
    if instance.email:
        user.email = instance.email
    user.is_active = instance.is_active
    user.save(update_fields=["first_name", "last_name", "email", "is_active"])

    instance.user = user
    instance.save(update_fields=["user"])

    if created_user and pwd:
        TempPassword.objects.update_or_create(
            user=user,
            defaults={"password": pwd, "created_at": timezone.now()},
        )


# =========================================================
# 6) Eleve -> créer user ELEVE automatiquement
# =========================================================
@receiver(post_save, sender="core.Eleve")
def create_user_for_eleve(sender, instance, created: bool, **kwargs):
    if not instance.matricule:
        return
    if instance.user_id:
        return

    TempPassword = apps.get_model("core", "TempPassword")

    username = instance.matricule.strip()
    user, pwd, created_user = get_or_create_user_with_group(username, "ELEVE", length=10)

    user.first_name = instance.prenom or ""
    user.last_name = instance.nom or ""
    user.is_active = instance.is_active
    user.save(update_fields=["first_name", "last_name", "is_active"])

    instance.user = user
    instance.save(update_fields=["user"])

    if created_user and pwd:
        TempPassword.objects.update_or_create(
            user=user,
            defaults={"password": pwd, "created_at": timezone.now()},
        )
