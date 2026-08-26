# core/models_notifications.py
from django.conf import settings
from django.db import models
from django.utils import timezone


class Notification(models.Model):
    CATEGORY_CHOICES = [
        ("INFO",          "Information"),
        ("PAIEMENT",      "Paiement"),
        ("ABSENCE",       "Absence"),
        ("IMPAYE",        "Impayé"),
        ("RELANCE",       "Relance"),
        ("AVIS",          "Avis"),
        ("RENOUVELLEMENT","Renouvellement"),
        ("SYSTEME",       "Système"),
    ]

    recipient  = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="notifications", verbose_name="destinataire",
    )
    category   = models.CharField(
        max_length=20, choices=CATEGORY_CHOICES, default="INFO",
        verbose_name="catégorie",
    )
    title      = models.CharField(max_length=200, verbose_name="titre")
    body       = models.TextField(blank=True, verbose_name="contenu")
    link       = models.CharField(max_length=255, blank=True, verbose_name="lien")
    read       = models.BooleanField(default=False, verbose_name="lue", db_index=True)
    read_at    = models.DateTimeField(null=True, blank=True, verbose_name="lue le")

    # optional references to related domain objects
    eleve      = models.ForeignKey(
        "core.Eleve", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="notifications", verbose_name="élève",
    )
    parent     = models.ForeignKey(
        "core.Parent", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="notifications", verbose_name="parent",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="créée le")

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"

    def __str__(self):
        return f"[{self.category}] {self.title} → {self.recipient}"

    def mark_read(self):
        if not self.read:
            self.read    = True
            self.read_at = timezone.now()
            self.save(update_fields=["read", "read_at"])

    @property
    def category_css(self):
        return {
            "INFO":           "info",
            "PAIEMENT":       "ok",
            "ABSENCE":        "warn",
            "IMPAYE":         "bad",
            "RELANCE":        "warn",
            "AVIS":           "info",
            "RENOUVELLEMENT": "purple",
            "SYSTEME":        "muted",
        }.get(self.category, "info")

    @property
    def category_icon(self):
        return {
            "INFO":           "fa-circle-info",
            "PAIEMENT":       "fa-coins",
            "ABSENCE":        "fa-calendar-times",
            "IMPAYE":         "fa-triangle-exclamation",
            "RELANCE":        "fa-bell",
            "AVIS":           "fa-bullhorn",
            "RENOUVELLEMENT": "fa-rotate",
            "SYSTEME":        "fa-gear",
        }.get(self.category, "fa-bell")


class NotificationPreference(models.Model):
    """Per-parent channel and event preferences for automated notifications."""
    parent          = models.OneToOneField(
        "core.Parent", on_delete=models.CASCADE,
        related_name="notif_pref", verbose_name="parent",
    )
    canal_sms      = models.BooleanField(default=True,  verbose_name="Canal SMS")
    canal_email    = models.BooleanField(default=False, verbose_name="Canal email")
    canal_interne  = models.BooleanField(default=True,  verbose_name="Notification interne")

    notif_impaye         = models.BooleanField(default=True, verbose_name="Impayés")
    notif_absence        = models.BooleanField(default=True, verbose_name="Absences")
    notif_retard         = models.BooleanField(default=True, verbose_name="Retards")
    notif_avis           = models.BooleanField(default=True, verbose_name="Avis école")
    notif_renouvellement = models.BooleanField(default=True, verbose_name="Renouvellement inscription")

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Préférences de notification"
        verbose_name_plural = "Préférences de notification"

    def __str__(self):
        return f"Préférences de {self.parent}"

    @classmethod
    def get_or_default(cls, parent):
        """Return existing preference or an unsaved default instance."""
        try:
            return cls.objects.get(parent=parent)
        except cls.DoesNotExist:
            return cls(parent=parent)
