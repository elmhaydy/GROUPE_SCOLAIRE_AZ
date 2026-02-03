# core/services/sms_provider.py
import os
from typing import Tuple

class SmsProviderError(Exception):
    pass

def normalize_phone(phone: str) -> str:
    """
    Normalisation Maroc -> format E.164 (+212XXXXXXXXX)

    Accepte:
    - 06XXXXXXXX / 07XXXXXXXX
    - 2126XXXXXXXX / 2127XXXXXXXX
    - +2126XXXXXXXX / +2127XXXXXXXX
    - 002126XXXXXXXX / 002127XXXXXXXX
    - avec espaces / tirets / parenthèses

    Retour:
    - +2126XXXXXXXX ou +2127XXXXXXXX
    - "" si invalide
    """
    if not phone:
        return ""

    p = phone.strip()

    # enlever séparateurs courants
    for ch in [" ", "-", "(", ")", ".", "_"]:
        p = p.replace(ch, "")

    # convertir 00 en +
    if p.startswith("00"):
        p = "+" + p[2:]

    # si déjà +212...
    if p.startswith("+212"):
        rest = p[4:]
        # parfois écrit +21206..., on retire le 0
        if rest.startswith("0"):
            rest = rest[1:]
        digits = "".join([c for c in rest if c.isdigit()])
        if len(digits) == 9 and digits[0] in ("6", "7"):
            return "+212" + digits
        return ""

    # si commence par 212...
    if p.startswith("212"):
        rest = p[3:]
        if rest.startswith("0"):
            rest = rest[1:]
        digits = "".join([c for c in rest if c.isdigit()])
        if len(digits) == 9 and digits[0] in ("6", "7"):
            return "+212" + digits
        return ""

    # si commence par 0 (06/07)
    if p.startswith("0"):
        digits = "".join([c for c in p[1:] if c.isdigit()])
        if len(digits) == 9 and digits[0] in ("6", "7"):
            return "+212" + digits
        return ""

    # si commence directement par 6/7 (ex: 6XXXXXXXX)
    digits = "".join([c for c in p if c.isdigit()])
    if len(digits) == 9 and digits[0] in ("6", "7"):
        return "+212" + digits

    return ""


def send_sms_via_twilio(to_phone: str, message: str) -> Tuple[bool, str, str]:
    """
    Retour: (ok, provider_message_id, error_message)
    """
    # ⚠️ Nécessite: pip install twilio
    try:
        from twilio.rest import Client
    except Exception:
        return (False, "", "Le package 'twilio' n'est pas installé. Fais: pip install twilio")

    sid = os.getenv("TWILIO_ACCOUNT_SID", "")
    token = os.getenv("TWILIO_AUTH_TOKEN", "")
    from_phone = os.getenv("TWILIO_FROM_NUMBER", "")

    if not sid or not token or not from_phone:
        return (False, "", "Variables TWILIO_* manquantes (SID/TOKEN/FROM_NUMBER).")

    try:
        client = Client(sid, token)
        msg = client.messages.create(
            body=message,
            from_=from_phone,
            to=to_phone
        )
        return (True, msg.sid, "")
    except Exception as e:
        err = str(e)

        # ✅ Twilio fournit souvent plus d'infos dans e.msg / e.code / e.status si dispo
        try:
            status = getattr(e, "status", None)
            code = getattr(e, "code", None)
            msg = getattr(e, "msg", None)
            more = f" | status={status} | code={code} | msg={msg}"
            err = err + more
        except Exception:
            pass

        print("TWILIO ERROR:", err)  # ✅ console
        return (False, "", err)
