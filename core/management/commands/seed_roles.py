from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

from core.models import (
    AnneeScolaire, Degre, Niveau, Groupe,
    Eleve, Inscription, Paiement, Absence, Seance,
    Parent, ParentEleve,
    Enseignant
)

class Command(BaseCommand):
    help = "Crée les rôles (groups) et attribue les permissions."

    def handle(self, *args, **options):
        roles = {
            "ADMIN": {
                "models": [
                    AnneeScolaire, Degre, Niveau, Groupe,
                    Eleve, Inscription, Paiement, Absence, Seance,
                    Parent, ParentEleve,
                    Enseignant
                ],
                "perms": ["add", "change", "delete", "view"],
            },
            "SCOLARITE": {
                "models": [
                    AnneeScolaire, Degre, Niveau, Groupe,
                    Eleve, Inscription, Absence, Seance,
                    Parent, ParentEleve,
                    Enseignant
                ],
                "perms": ["add", "change", "delete", "view"],
            },
            "COMPTABLE": {
                "models": [Paiement],
                "perms": ["add", "change", "delete", "view"],
                "extra_view_models": [Inscription, Eleve],  # lecture
            },
            "PROF": {
                "models": [Seance, Absence],
                "perms": ["view"],  # V1 lecture seulement
            }
        }

        for role_name, cfg in roles.items():
            group, _ = Group.objects.get_or_create(name=role_name)
            group.permissions.clear()

            # perms principales
            for model in cfg.get("models", []):
                ct = ContentType.objects.get_for_model(model)
                for action in cfg.get("perms", []):
                    codename = f"{action}_{model._meta.model_name}"
                    perm = Permission.objects.filter(content_type=ct, codename=codename).first()
                    if perm:
                        group.permissions.add(perm)

            # perms view extra (COMPTABLE)
            for model in cfg.get("extra_view_models", []):
                ct = ContentType.objects.get_for_model(model)
                codename = f"view_{model._meta.model_name}"
                perm = Permission.objects.filter(content_type=ct, codename=codename).first()
                if perm:
                    group.permissions.add(perm)

            self.stdout.write(self.style.SUCCESS(f"✅ Rôle prêt : {role_name}"))

        self.stdout.write(self.style.SUCCESS("✅ Seed roles terminé."))
