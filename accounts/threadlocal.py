import threading

_local = threading.local()

def set_current_user(user):
    _local.user = user

def get_current_user():
    return getattr(_local, "user", None)

# ── Adresse IP (pour le journal d'audit) ───────────────────────────────────

def set_audit_ip(ip: str | None) -> None:
    _local.audit_ip = ip

def get_audit_ip() -> str | None:
    return getattr(_local, "audit_ip", None)
