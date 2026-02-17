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

import os
import re
import requests
from typing import Tuple

def _bulksms_to_local_ma(phone: str) -> str:
    """
    Bulksms.ma (Maroc) : on force un format national 06/07XXXXXXXX.
    Accepte: +2126..., 2126..., 002126..., 06..., 6...
    Retourne: 06XXXXXXXX ou 07XXXXXXXX ou "" si invalide.
    """
    if not phone:
        return ""

    p = phone.strip()

    # enlever séparateurs
    p = re.sub(r"[ \-\(\)\._]", "", p)

    # 00 -> +
    if p.startswith("00"):
        p = "+" + p[2:]

    # +212...
    if p.startswith("+212"):
        rest = p[4:]
        if rest.startswith("0"):
            rest = rest[1:]
        rest = re.sub(r"\D", "", rest)
        if len(rest) == 9 and rest[0] in ("6", "7"):
            return "0" + rest
        return ""

    # 212...
    if p.startswith("212"):
        rest = p[3:]
        if rest.startswith("0"):
            rest = rest[1:]
        rest = re.sub(r"\D", "", rest)
        if len(rest) == 9 and rest[0] in ("6", "7"):
            return "0" + rest
        return ""

    # 06/07...
    if p.startswith("0"):
        digits = re.sub(r"\D", "", p)
        if len(digits) == 10 and digits[1] in ("6", "7"):
            return digits
        return ""

    # 6/7...
    digits = re.sub(r"\D", "", p)
    if len(digits) == 9 and digits[0] in ("6", "7"):
        return "0" + digits

    return ""


def send_sms_via_bulksms_ma(to_phone: str, message: str) -> Tuple[bool, str, str]:
    """
    Bulksms.ma HTTP API
    Retour: (ok, provider_message_id, error_message)
    """
    token = os.getenv("BULKSMS_TOKEN", "").strip()
    sender = os.getenv("BULKSMS_SENDER", "").strip()  # optionnel

    if not token:
        return (False, "", "BULKSMS_TOKEN manquant dans .env")

    # ⚠️ Bulksms (MA) : meilleure compatibilité en format national
    local_phone = _bulksms_to_local_ma(to_phone)
    if not local_phone:
        return (False, "", f"Numéro invalide pour Bulksms.ma: '{to_phone}'")

    # message safe
    msg = (message or "").strip()
    if not msg:
        return (False, "", "Message vide")

    url = "https://bulksms.ma/developer/sms/send"

    data = {
        "token": token,
        "tel": local_phone,   # ✅ 06/07...
        "message": msg,
    }

    # shortcode = expéditeur (si autorisé)
    if sender:
        data["shortcode"] = sender

    try:
        r = requests.post(url, data=data, timeout=25)

        # parfois Bulksms peut répondre HTML ou texte
        raw = (r.text or "").strip()

        # tentative JSON
        try:
            j = r.json()
        except Exception:
            # si HTTP != 200 on donne un message clair
            if not r.ok:
                return (False, "", f"HTTP {r.status_code}: {raw[:300]}")
            # même en 200, si non-json => on remonte le texte
            return (False, "", f"Réponse non-JSON: {raw[:300]}")

        # succès
        if str(j.get("success")) in ("1", "true", "True"):
            # Bulksms renvoie parfois juste {"success":1}
            provider_id = str(j.get("id") or j.get("message_id") or "success")
            return (True, provider_id, "")

        # erreur : message clair
        err = j.get("error") or j.get("message") or j
        err_str = str(err)

        # cas spécial essai (tu l’as déjà vu)
        if "période d" in err_str or "periode d" in err_str or "essai" in err_str:
            return (False, "", "Compte Bulksms en ESSAI : tu peux envoyer uniquement vers ton propre numéro.")

        return (False, "", err_str)

    except Exception as e:
        return (False, "", str(e))
