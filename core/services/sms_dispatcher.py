from datetime import datetime, time
from django.utils import timezone
from django.db import transaction

from core.models import SmsSettings, SmsHistorique
from core.models_sms import SmsTemplate
from core.services.sms_provider import normalize_phone, send_sms_via_bulksms_ma

DEFAULT_TEMPLATES = {
    "absence": "AZ: {eleve} ({groupe}) {type} le {date}.",
    "paiement": "AZ: Reçu {montant} MAD le {date}. Réf: {ref}. Merci.",
    "impaye": "AZ: Rappel {eleve} ({groupe}) montant dû {montant} MAD. Merci de régler.",
}

EVENT_TO_TEMPLATE = {
    "absence": "absence",
    "paiement": "paiement",
    "impaye": "impaye",
}


def _safe_parent(parent_obj):
    try:
        from core.models import Parent
        if isinstance(parent_obj, Parent):
            return parent_obj
    except Exception:
        pass
    return None

def _is_quiet(now: datetime, settings: SmsSettings) -> bool:
    qs, qe = settings.quiet_start, settings.quiet_end
    if not qs or not qe:
        return False
    # Comparaison sur l'heure locale, sans tzinfo pour éviter les TypeError
    t = now.timetz().replace(microsecond=0, tzinfo=None)
    if qs < qe:
        return qs <= t < qe
    # plage qui traverse minuit
    return t >= qs or t < qe

def _recently_sent(parent_id, event, date_only):
    return SmsHistorique.objects.filter(
        parent_id=parent_id,
        event=event,
        created_at__date=date_only
    ).exists()

def _fill(template: str, payload: dict) -> str:
    try:
        return template.format(**payload)
    except Exception:
        return template

def _log_failed(event, parent, phone, message, reason):
    """
    Crée une ligne d'historique même si l'envoi est bloqué (utile pour debug).
    """
    try:
        SmsHistorique.objects.create(
            parent=_safe_parent(parent),
            telephone=phone or "",
            message=message or "",
            status="FAILED",
            provider="bulksms",
            event=event if event in ["absence", "paiement", "impaye"] else "autre",
            error_message=reason or "",
        )
    except Exception:
        # ne jamais planter l'app à cause d'un log
        return


def send_event(event: str, payload: dict) -> None:
    settings = SmsSettings.load()

    toggles = {
        "absence": settings.enable_absence,
        "paiement": settings.enable_paiement,
        "impaye": settings.enable_impaye,
    }
    raw_parent = payload.get("parent")
    parent = _safe_parent(raw_parent)
    phone_source = raw_parent if raw_parent is not None else parent
    phone = normalize_phone(
        getattr(phone_source, "telephone", "")
        or getattr(phone_source, "telephone_norm", "")
        or payload.get("telephone", "")
    )

    # Préparer message (même si on ne l'envoie pas)
    template_code = EVENT_TO_TEMPLATE.get(event, event)
    template_text = DEFAULT_TEMPLATES.get(template_code, "")
    tpl = SmsTemplate.objects.filter(type_template=template_code, is_active=True).first()
    if tpl:
        template_text = tpl.contenu or template_text
    message = _fill(template_text, payload)

    if not toggles.get(event, False):
        _log_failed(event, parent, phone, message, "Envoi désactivé dans les paramètres.")
        return

    if not phone:
        _log_failed(event, parent, phone, message, "Numéro parent manquant ou invalide.")
        return

    if not getattr(parent, "sms_optin", True) or not settings.optin_default:
        _log_failed(event, parent, phone, message, "Parent en opt-out SMS.")
        return

    now = timezone.now()
    if _is_quiet(now, settings):
        _log_failed(event, parent, phone, message, "Plage silence active.")
        return

    if _recently_sent(getattr(parent, "id", None), event, now.date()):
        _log_failed(event, parent, phone, message, "Déjà envoyé aujourd'hui.")
        return

    if not message:
        _log_failed(event, parent, phone, message, "Template SMS vide.")
        return

    with transaction.atomic():
        hist = SmsHistorique.objects.create(
            parent=parent,
            telephone=phone,
            message=message,
            status="QUEUED",
            provider="bulksms",
            event=event if event in ["absence", "paiement", "impaye"] else "autre",
        )

    ok, msg_id, err = send_sms_via_bulksms_ma(phone, message)
    hist.provider_message_id = msg_id or ""
    hist.error_message = err or ""
    hist.status = "SENT" if ok else "FAILED"
    hist.save(update_fields=["provider_message_id", "error_message", "status"])


def update_status_from_webhook(message_id: str, status: str, error: str = ""):
    """
    Met à jour le SmsHistorique à partir du provider (webhook).
    status attendu: 'delivered', 'failed', 'sent'...
    """
    if not message_id:
        return
    try:
        hist = SmsHistorique.objects.filter(provider_message_id=message_id).order_by("-id").first()
        if not hist:
            return
        status_map = {
            "delivered": "SENT",
            "sent": "SENT",
            "failed": "FAILED",
            "undelivered": "FAILED",
        }
        hist.status = status_map.get(status.lower(), hist.status)
        hist.error_message = error or hist.error_message
        hist.save(update_fields=["status", "error_message"])
    except Exception:
        return
