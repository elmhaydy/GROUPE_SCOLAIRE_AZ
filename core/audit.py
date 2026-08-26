"""
Helpers pour le journal d'audit.

Usage depuis n'importe où :
    from core.audit import log_action
    log_action(user, "UPDATE", instance, changes)
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

# ─── Champs systèmes à ne jamais inclure dans les diffs ───────────────────────
_EXCLUDED_ATTNAMES = frozenset({
    "id", "pk",
    "created_at", "updated_at",
    "created_by_id", "updated_by_id",
    "archived_at",
    "password", "last_login",
})


def _serialize(val: Any) -> Any:
    """Convertit une valeur en type JSON-safe."""
    if val is None:
        return None
    if isinstance(val, bool):
        return val
    if isinstance(val, int):
        return val
    if isinstance(val, Decimal):
        return str(val)
    if isinstance(val, (date, datetime)):
        return val.isoformat()
    return str(val)


def compute_diff(old_instance, new_instance) -> dict:
    """
    Compare deux instances du même modèle et retourne un dict
    {"attname": {"old": ..., "new": ...}} pour chaque champ modifié.
    """
    changes = {}
    try:
        for field in type(new_instance)._meta.get_fields():
            attname = getattr(field, "attname", None)
            if not attname or attname in _EXCLUDED_ATTNAMES or attname.endswith("_ptr_id"):
                continue
            try:
                old_val = getattr(old_instance, attname, None)
                new_val = getattr(new_instance, attname, None)
                if old_val != new_val:
                    # libellé lisible : préférer field.verbose_name si disponible
                    label = getattr(field, "verbose_name", attname)
                    changes[attname] = {
                        "label": str(label).capitalize(),
                        "old": _serialize(old_val),
                        "new": _serialize(new_val),
                    }
            except Exception:
                pass
    except Exception:
        pass
    return changes


def log_action(
    user,
    action: str,          # "CREATE" | "UPDATE" | "DELETE"
    app_label: str,
    model_name: str,
    model_label: str,     # libellé FR
    object_id,
    object_repr: str,
    changes: dict | None = None,
) -> None:
    """Écrit une ligne AuditLog. Ne lève jamais d'exception."""
    from core.models_audit import AuditLog
    from accounts.threadlocal import get_audit_ip

    try:
        AuditLog.objects.create(
            user=user if (user and getattr(user, "is_authenticated", False)) else None,
            action=action,
            app_label=app_label,
            model_name=model_name,
            model_label=model_label,
            object_id=str(object_id) if object_id is not None else "",
            object_repr=(str(object_repr) or "")[:255],
            changes=changes or {},
            ip_address=get_audit_ip(),
        )
    except Exception:
        # Le journal d'audit ne doit jamais planter l'application
        pass
