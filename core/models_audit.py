"""
Journal d'audit : chaque CREATE / UPDATE / DELETE sur les modèles surveillés
génère une ligne AuditLog avec l'utilisateur, l'heure, l'IP et le diff champ-par-champ.
"""
from django.db import models
from django.conf import settings


class AuditLog(models.Model):
    ACTION_CREATE = "CREATE"
    ACTION_UPDATE = "UPDATE"
    ACTION_DELETE = "DELETE"

    ACTION_CHOICES = [
        (ACTION_CREATE, "Création"),
        (ACTION_UPDATE, "Modification"),
        (ACTION_DELETE, "Suppression"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="audit_logs",
        verbose_name="Utilisateur",
    )
    action = models.CharField(max_length=6, choices=ACTION_CHOICES, db_index=True)

    # Identification du modèle
    app_label   = models.CharField(max_length=50)
    model_name  = models.CharField(max_length=80, db_index=True)
    model_label = models.CharField(max_length=80)          # libellé FR lisible

    # Identification de l'objet
    object_id   = models.CharField(max_length=40, db_index=True)
    object_repr = models.CharField(max_length=255)         # str(instance)

    # Diff champ-par-champ pour UPDATE : {"field": {"old": x, "new": y}}
    changes = models.JSONField(default=dict, blank=True)

    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp  = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-timestamp"]
        verbose_name = "Log d'audit"
        verbose_name_plural = "Journal d'audit"
        indexes = [
            models.Index(fields=["model_name", "object_id"], name="audit_model_obj_idx"),
            models.Index(fields=["user", "timestamp"],       name="audit_user_ts_idx"),
            models.Index(fields=["action", "timestamp"],     name="audit_action_ts_idx"),
        ]

    def __str__(self):
        return f"{self.timestamp:%Y-%m-%d %H:%M} | {self.get_action_display()} | {self.model_label} #{self.object_id}"

    @property
    def action_css(self):
        return {"CREATE": "success", "UPDATE": "warning", "DELETE": "danger"}.get(self.action, "secondary")

    @property
    def action_icon(self):
        return {
            "CREATE": "fa-plus-circle",
            "UPDATE": "fa-pen",
            "DELETE": "fa-trash",
        }.get(self.action, "fa-circle")

    @property
    def changes_count(self):
        return len(self.changes)
