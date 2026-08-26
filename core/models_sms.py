from django.conf import settings
from django.db import models


class SmsTemplate(models.Model):
    """
    Modèle de template SMS réutilisable (auto / manuel / campagnes).
    """
    TYPE_CHOICES = [
        ("absence", "Absence"),
        ("impaye", "Impayé"),
        ("info", "Information"),
        ("inscription", "Inscription"),
        ("manuel", "Manuel"),
    ]

    nom = models.CharField(max_length=120)
    code = models.CharField(max_length=60, unique=True, db_index=True)
    type_template = models.CharField(max_length=20, choices=TYPE_CHOICES, default="manuel", db_index=True)
    contenu = models.TextField(
        help_text="Variables : {nom_parent}, {nom_eleve}, {niveau}, {groupe}, {montant}, {date}, {annee}"
    )
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="sms_templates_created"
    )

    class Meta:
        verbose_name = "Template SMS"
        verbose_name_plural = "Templates SMS"
        ordering = ["code"]

    def __str__(self) -> str:
        return f"{self.code} ({self.get_type_template_display()})"


class SmsCampaign(models.Model):
    STATUT_CHOICES = [
        ("draft", "Brouillon"),
        ("running", "En cours"),
        ("done", "Terminé"),
        ("failed", "Échec"),
    ]

    nom = models.CharField(max_length=120)
    type_campagne = models.CharField(max_length=40, default="manuel")
    filtre_json = models.JSONField(default=dict, blank=True)
    total_envoyes = models.PositiveIntegerField(default=0)
    total_echecs = models.PositiveIntegerField(default=0)
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default="draft")
    cree_par = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="sms_campaigns"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Campagne SMS"
        verbose_name_plural = "Campagnes SMS"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.nom


class SmsProviderConfig(models.Model):
    PROVIDER_CHOICES = [
        ("twilio", "Twilio"),
        ("mock", "Mock"),
    ]

    nom = models.CharField(max_length=80)
    provider_type = models.CharField(max_length=20, choices=PROVIDER_CHOICES, default="mock")
    api_key = models.CharField(max_length=255, blank=True, default="")
    sender_id = models.CharField(max_length=32, blank=True, default="")
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Configuration SMS"
        verbose_name_plural = "Configurations SMS"
        ordering = ["-is_active", "nom"]

    def __str__(self) -> str:
        return f"{self.nom} ({self.provider_type})"
