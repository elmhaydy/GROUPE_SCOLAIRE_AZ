# core/services/notification_service.py
"""
Unified multi-channel notification dispatcher.
Channels: SMS, email, internal (Notification model).
"""
import logging

from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Dispatch notifications to one or more channels.

    Usage (manual compose — admin picks channels explicitly):
        NotificationService.send_to_parents(
            parents=qs,
            title="Rappel paiement",
            message="...",
            channels=["sms", "email", "internal"],
            category="IMPAYE",
            sent_by=request.user,
        )

    Usage (automated — respects NotificationPreference):
        NotificationService.send_event_to_parent(
            parent=parent_obj,
            title="...",
            message="...",
            category="ABSENCE",
            event_key="notif_absence",
        )

    Usage (staff internal only):
        NotificationService.send_to_user(
            user=staff_user,
            title="...",
            body="...",
            category="SYSTEME",
        )
    """

    # ──────────────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────────────

    @classmethod
    def send_to_parents(
        cls,
        *,
        parents,
        title: str,
        message: str,
        channels: list,          # explicit: ["sms"], ["email"], ["sms","email","internal"]
        category: str = "INFO",
        link: str = "",
        eleve=None,
        sent_by=None,
    ) -> dict:
        """
        Send to a queryset / list of Parent objects.
        `channels` is explicitly supplied by the caller (admin compose).
        Returns stats dict: {"sms": N, "email": N, "internal": N, "errors": N}.
        """
        stats = {"sms": 0, "email": 0, "internal": 0, "errors": 0}
        for parent in parents:
            try:
                if "sms" in channels:
                    if cls._send_sms(parent, message, sent_by=sent_by):
                        stats["sms"] += 1
                if "email" in channels:
                    if cls._send_email(parent, title, message):
                        stats["email"] += 1
                if "internal" in channels:
                    if cls._create_internal(
                        parent=parent, title=title, body=message,
                        category=category, link=link, eleve=eleve,
                    ):
                        stats["internal"] += 1
            except Exception as exc:
                stats["errors"] += 1
                logger.exception("NotificationService error for parent %s: %s", parent.pk, exc)
        return stats

    @classmethod
    def send_event_to_parent(
        cls,
        *,
        parent,
        title: str,
        message: str,
        category: str = "INFO",
        event_key: str = "",
        link: str = "",
        eleve=None,
    ) -> dict:
        """
        Automated send that respects the parent's NotificationPreference.
        `event_key` matches a BooleanField on NotificationPreference
        (e.g., "notif_absence", "notif_impaye").
        """
        from core.models_notifications import NotificationPreference
        pref = NotificationPreference.get_or_default(parent)

        # Check event toggle
        if event_key and not getattr(pref, event_key, True):
            return {"sms": 0, "email": 0, "internal": 0, "errors": 0}

        channels = []
        if pref.canal_sms:
            channels.append("sms")
        if pref.canal_email:
            channels.append("email")
        if pref.canal_interne:
            channels.append("internal")

        return cls.send_to_parents(
            parents=[parent],
            title=title,
            message=message,
            channels=channels,
            category=category,
            link=link,
            eleve=eleve,
        )

    @classmethod
    def send_to_user(
        cls,
        *,
        user,
        title: str,
        body: str = "",
        category: str = "INFO",
        link: str = "",
        eleve=None,
        parent=None,
    ) -> bool:
        """Create an internal notification for a staff (or any) User."""
        from core.models_notifications import Notification
        try:
            Notification.objects.create(
                recipient=user,
                title=title,
                body=body,
                category=category,
                link=link,
                eleve=eleve,
                parent=parent,
            )
            return True
        except Exception as exc:
            logger.exception("send_to_user failed for user %s: %s", user.pk, exc)
            return False

    # ──────────────────────────────────────────────────────────────────────────
    # Private helpers
    # ──────────────────────────────────────────────────────────────────────────

    @classmethod
    def _send_sms(cls, parent, message: str, sent_by=None) -> bool:
        phone = parent.telephone_norm or parent.telephone
        if not phone:
            return False
        if not getattr(parent, "sms_optin", True):
            return False
        try:
            from core.services.sms_provider import send_sms_via_bulksms_ma
            from core.models import SmsHistorique
            ok = send_sms_via_bulksms_ma(phone, message)
            SmsHistorique.objects.create(
                parent=parent,
                telephone=phone,
                message=message,
                event="autre",
                status="SENT" if ok else "FAILED",
                type_envoi="manuel",
                envoye_par=sent_by,
            )
            return bool(ok)
        except Exception as exc:
            logger.exception("SMS send failed for parent %s: %s", parent.pk, exc)
            return False

    @classmethod
    def _send_email(cls, parent, title: str, message: str) -> bool:
        email = parent.email
        if not email:
            return False
        try:
            from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@az.local")
            send_mail(
                subject=title,
                message=message,
                from_email=from_email,
                recipient_list=[email],
                fail_silently=False,
            )
            return True
        except Exception as exc:
            logger.exception("Email send failed for parent %s (%s): %s", parent.pk, email, exc)
            return False

    @classmethod
    def _create_internal(
        cls, *, parent, title: str, body: str,
        category: str, link: str, eleve,
    ) -> bool:
        user = getattr(parent, "user", None)
        if user is None:
            return False
        from core.models_notifications import Notification
        try:
            Notification.objects.create(
                recipient=user,
                title=title,
                body=body,
                category=category,
                link=link,
                eleve=eleve,
                parent=parent,
            )
            return True
        except Exception as exc:
            logger.exception("Internal notif failed for parent %s: %s", parent.pk, exc)
            return False
