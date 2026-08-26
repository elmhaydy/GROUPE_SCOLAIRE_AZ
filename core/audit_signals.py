"""
Connexion des signaux Django pour le journal d'audit.
Appelé depuis CoreConfig.ready().

Modèles surveillés :
  Élève, Parent, Inscription, Paiement, Enseignant, Absence,
  Année scolaire, Groupe, Avis, Dépense, Recouvrement,
  Paramètres SMS, Utilisateur (auth)
"""
from django.apps import apps
from django.db.models.signals import pre_save, post_save, pre_delete
from django.dispatch import receiver

from accounts.threadlocal import get_current_user
from core.audit import compute_diff, log_action

# (app_label, model_name_lower) → libellé FR affiché dans le journal
AUDITED = {
    ("core", "eleve"):                 "Élève",
    ("core", "parent"):                "Parent",
    ("core", "parenteleve"):           "Lien Parent-Élève",
    ("core", "inscription"):           "Inscription",
    ("core", "paiement"):              "Paiement",
    ("core", "paiementligne"):         "Ligne de paiement",
    ("core", "echeancemensuelle"):     "Échéance mensuelle",
    ("core", "enseignant"):            "Enseignant",
    ("core", "absence"):               "Absence élève",
    ("core", "absenceprof"):           "Absence enseignant",
    ("core", "anneescolaire"):         "Année scolaire",
    ("core", "degre"):                 "Degré d'enseignement",
    ("core", "niveau"):                "Niveau d'études",
    ("core", "groupe"):                "Groupe / Classe",
    ("core", "matiere"):               "Matière",
    ("core", "salle"):                 "Salle",
    ("core", "seance"):                "Séance / Emploi du temps",
    ("core", "enseignantgroupe"):      "Affectation Enseignant",
    ("core", "avis"):                  "Avis / Annonce",
    ("core", "depense"):               "Dépense",
    ("core", "categoriedepense"):      "Catégorie de dépense",
    ("core", "recouvrement"):          "Recouvrement",
    ("core", "smssettings"):           "Paramètres SMS",
    ("core", "relancerule"):           "Règle de relance",
    ("core", "relancelog"):            "Log de relance",
    ("core", "tarifniveau"):           "Tarif niveau",
    ("core", "tariftransport"):        "Tarif transport",
    ("core", "temppassword"):          "Mot de passe temporaire",
    ("accounts", "passwordresettoken"): "Jeton OTP / Reset MDP",
    ("accounts", "usersecurityprofile"): "Profil de sécurité",
    ("auth", "user"):                  "Utilisateur",
    ("auth", "group"):                 "Rôle / Groupe",
    ("auth", "permission"):            "Permission",
}

EXCLUDED_MODELS = {
    ("core", "auditlog"),
    ("sessions", "session"),
    ("contenttypes", "contenttype"),
    ("admin", "logentry"),
    ("migrations", "migration"),
}


def _label(sender):
    key = (sender._meta.app_label, sender._meta.model_name)
    return AUDITED.get(key, str(sender._meta.verbose_name).capitalize())


# ──────────────────────────────────────────────────────────────────────────────
# Handlers partagés (connectés dynamiquement pour chaque modèle)
# ──────────────────────────────────────────────────────────────────────────────

def _pre_save(sender, instance, **kwargs):
    """Capture l'état DB avant la sauvegarde pour le diff UPDATE."""
    if instance.pk:
        try:
            instance._audit_old = sender.objects.get(pk=instance.pk)
        except sender.DoesNotExist:
            instance._audit_old = None
    else:
        instance._audit_old = None


def _post_save(sender, instance, created, **kwargs):
    user = get_current_user()
    meta = sender._meta

    if created:
        log_action(
            user, "CREATE",
            meta.app_label, meta.model_name, _label(sender),
            instance.pk, str(instance),
        )
    else:
        old = getattr(instance, "_audit_old", None)
        if old is not None:
            changes = compute_diff(old, instance)
            if changes:
                log_action(
                    user, "UPDATE",
                    meta.app_label, meta.model_name, _label(sender),
                    instance.pk, str(instance),
                    changes=changes,
                )


def _pre_delete(sender, instance, **kwargs):
    user = get_current_user()
    meta = sender._meta
    log_action(
        user, "DELETE",
        meta.app_label, meta.model_name, _label(sender),
        instance.pk, str(instance),
    )


# ──────────────────────────────────────────────────────────────────────────────
# Connexion au démarrage de l'app (appelé par CoreConfig.ready)
# ──────────────────────────────────────────────────────────────────────────────

def connect():
    """Connecte automatiquement le journal d'audit à TOUS les modèles de l'application."""
    for model in apps.get_models():
        meta = model._meta
        key = (meta.app_label, meta.model_name)
        if key in EXCLUDED_MODELS:
            continue

        # dispatch_uid unique par (model, signal) pour éviter les connexions doubles
        pre_save.connect(_pre_save,   sender=model, weak=False,
                         dispatch_uid=f"audit_pre_save_{meta.app_label}_{meta.model_name}")
        post_save.connect(_post_save,  sender=model, weak=False,
                          dispatch_uid=f"audit_post_save_{meta.app_label}_{meta.model_name}")
        pre_delete.connect(_pre_delete, sender=model, weak=False,
                           dispatch_uid=f"audit_pre_delete_{meta.app_label}_{meta.model_name}")
