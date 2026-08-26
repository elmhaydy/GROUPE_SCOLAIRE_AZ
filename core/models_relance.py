"""
Relances automatiques intelligentes :
  - Impayés   : J+3 / J+7 / J+15 / J+30 après date d'échéance, ton escaladant
  - Absences  : alerte quand le seuil d'occurrences mensuel est dépassé
  - Retards   : idem
  - Renouvellement : X jours avant fin d'année scolaire
"""
from django.db import models
from django.conf import settings


class RelanceRule(models.Model):
    TYPE_CHOICES = [
        ("IMPAYE",         "Impayé"),
        ("ABSENCE",        "Absence répétée"),
        ("RETARD",         "Retard répété"),
        ("RENOUVELLEMENT", "Renouvellement inscription"),
    ]

    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    nom  = models.CharField(max_length=100, help_text="Libellé de la règle")
    actif = models.BooleanField(default=True)

    # Impayé : nombre de jours APRÈS date_echeance
    # Absence/Retard : non utilisé (seuil_occurrences suffit)
    # Renouvellement : nombre de jours AVANT date_fin de l'année
    jours_apres = models.PositiveSmallIntegerField(
        default=0,
        help_text="Impayé/Renouvellement : jours après échéance (ou avant fin d'année)"
    )

    # Niveau d'escalade pour les impayés (1=rappel, 2=urgent, 3=dernier avis)
    niveau_relance = models.PositiveSmallIntegerField(
        default=1, choices=[(1, "Rappel"), (2, "Urgent"), (3, "Dernier avis")]
    )

    # Absences / Retards : nombre minimum d'occurrences ce mois pour déclencher
    seuil_occurrences = models.PositiveSmallIntegerField(
        default=3,
        help_text="Absence/Retard : nombre d'occurrences ce mois avant alerte"
    )

    # Anti-spam : minimum de jours entre 2 relances de la même règle au même élève
    intervalle_min_jours = models.PositiveSmallIntegerField(
        default=7,
        help_text="Délai minimum (jours) entre 2 relances identiques au même élève"
    )

    # Message SMS par défaut (si aucun SmsTemplate lié)
    message_defaut = models.CharField(
        max_length=320, blank=True,
        help_text="Variables : {eleve}, {groupe}, {montant}, {date}, {mois}, {nb}, {annee}"
    )

    ordre = models.PositiveSmallIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="relance_rules_created"
    )

    class Meta:
        ordering = ["type", "ordre", "niveau_relance", "jours_apres"]
        verbose_name = "Règle de relance"
        verbose_name_plural = "Règles de relance"

    def __str__(self):
        return f"[{self.get_type_display()}] {self.nom}"

    @classmethod
    def active_for(cls, rule_type):
        return cls.objects.filter(type=rule_type, actif=True).order_by("ordre", "niveau_relance", "jours_apres")


class RelanceLog(models.Model):
    """Trace chaque relance envoyée — évite les doublons et permet l'audit."""
    rule        = models.ForeignKey(RelanceRule, on_delete=models.CASCADE, related_name="logs")
    eleve       = models.ForeignKey("core.Eleve",  on_delete=models.CASCADE, related_name="relance_logs")
    parent      = models.ForeignKey("core.Parent", on_delete=models.SET_NULL, null=True, blank=True, related_name="relance_logs")
    echeance    = models.ForeignKey("core.EcheanceMensuelle", on_delete=models.SET_NULL, null=True, blank=True, related_name="relance_logs")
    inscription = models.ForeignKey("core.Inscription", on_delete=models.SET_NULL, null=True, blank=True, related_name="relance_logs")
    sms         = models.ForeignKey("core.SmsHistorique", on_delete=models.SET_NULL, null=True, blank=True, related_name="relance_logs")

    type_relance   = models.CharField(max_length=20)
    niveau_relance = models.PositiveSmallIntegerField(default=1)
    message        = models.CharField(max_length=320, blank=True)
    dry_run        = models.BooleanField(default=False)
    success        = models.BooleanField(default=True)
    error          = models.CharField(max_length=255, blank=True)

    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-sent_at"]
        indexes = [
            models.Index(fields=["eleve", "rule", "sent_at"], name="rellog_eleve_rule_idx"),
            models.Index(fields=["type_relance", "sent_at"],  name="rellog_type_idx"),
            models.Index(fields=["echeance"],                 name="rellog_echeance_idx"),
        ]
        verbose_name = "Log de relance"
        verbose_name_plural = "Logs de relance"

    def __str__(self):
        return f"{self.get_type_relance_display()} — {self.eleve_id} — {self.sent_at:%Y-%m-%d}"

    def get_type_relance_display(self):
        labels = {
            "IMPAYE": "Impayé",
            "ABSENCE": "Absence",
            "RETARD": "Retard",
            "RENOUVELLEMENT": "Renouvellement",
        }
        return labels.get(self.type_relance, self.type_relance)
