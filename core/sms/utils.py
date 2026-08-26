from datetime import datetime
from typing import Dict
from core.services.sms_provider import normalize_phone as legacy_normalize

PLACEHOLDER_KEYS = {"nom_parent", "nom_eleve", "niveau", "groupe", "montant", "date", "annee"}


def normalize_phone(phone: str) -> str:
    """Délègue à l’utilitaire existant pour conserver la compatibilité."""
    return legacy_normalize(phone)


def render_message(template: str, data: Dict[str, object]) -> str:
    """
    Remplace les variables d'un template SMS.
    - ignore silencieusement les manquantes
    - force en str
    """
    if not template:
        return ""

    safe = {}
    for k in PLACEHOLDER_KEYS:
        v = data.get(k, "")
        if isinstance(v, datetime):
            v = v.strftime("%d/%m/%Y")
        safe[k] = "" if v is None else str(v)

    try:
        return template.format(**safe)
    except Exception:
        # en cas de clé inattendue dans le template
        try:
            return template.format_map(DefaultDict(safe))
        except Exception:
            return template


class DefaultDict(dict):
    def __missing__(self, key):
        return ""
