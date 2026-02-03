# core/apps.py
from django.apps import AppConfig
from django.db.models.signals import post_migrate


def _run_ensure_groups(sender, **kwargs):
    # appelé après migrate
    from .utils_roles import ensure_groups_exist
    ensure_groups_exist()


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"

    def ready(self):
        from . import signals  # charge signals.py
        import core.signals_tarifs  # charge signals_tarifs.py
        post_migrate.connect(_run_ensure_groups, sender=self)
