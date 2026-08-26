from typing import Dict, Optional
from django.utils import timezone

from core.models import SmsHistorique
from core.models_sms import SmsProviderConfig
from core.sms.utils import normalize_phone, render_message
from core.sms.providers.mock import MockProvider
from core.sms.providers.twilio import TwilioProvider


def _provider_from_config(cfg: Optional[SmsProviderConfig]):
    if not cfg:
        return MockProvider()
    if cfg.provider_type == "twilio":
        return TwilioProvider(api_key=cfg.api_key, sender=cfg.sender_id)
    return MockProvider()


def get_active_provider() -> MockProvider:
    cfg = SmsProviderConfig.objects.filter(is_active=True).order_by("-updated_at").first()
    return _provider_from_config(cfg)


def send_sms(message: str, telephone: str, meta: Dict) -> SmsHistorique:
    """
    Envoie un SMS via le provider actif et crée l'historique.
    meta peut contenir: parent, eleve, inscription, event, type_envoi, envoye_par
    """
    phone = normalize_phone(telephone)

    hist = SmsHistorique.objects.create(
        parent=meta.get("parent"),
        eleve=meta.get("eleve"),
        inscription=meta.get("inscription"),
        telephone=phone or telephone,
        message=message,
        event=meta.get("event", "autre"),
        type_envoi=meta.get("type_envoi", "manuel"),
        provider="twilio",
        status="QUEUED",
        envoye_par=meta.get("envoye_par"),
    )

    if not phone:
        hist.status = "FAILED"
        hist.error_message = "Numéro invalide"
        hist.save(update_fields=["status", "error_message"])
        return hist

    provider = get_active_provider()
    ok, provider_id, err = provider.send(phone, message)

    hist.provider = provider.__class__.__name__.lower()
    hist.provider_message_id = provider_id or ""
    hist.sent_at = timezone.now()
    hist.error_message = err or ""
    hist.status = "SENT" if ok else "FAILED"
    hist.save(update_fields=["provider", "provider_message_id", "sent_at", "error_message", "status"])
    return hist


def send_with_template(tpl, data: Dict, telephone: str, meta: Dict) -> SmsHistorique:
    """
    Rend le template + envoie + log.
    """
    message = render_message(tpl.contenu if tpl else "", data)
    if not message:
        message = meta.get("fallback") or ""
    meta = meta.copy()
    meta["event"] = tpl.type_template if tpl else meta.get("event", "autre")
    return send_sms(message, telephone, meta)
