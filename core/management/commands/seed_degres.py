# core/management/commands/seed_degres.py
from django.core.management.base import BaseCommand
from core.models import Degre


DEGRES = [
    ("MATERNELLE", "Maternelle", 1),
    ("PRIMAIRE", "Primaire", 2),
    ("COLLEGE", "Collège", 3),
    ("LYCEE", "Lycée", 4),
]


class Command(BaseCommand):
    help = "Crée les 4 degrés par défaut (sans doublons)."

    def handle(self, *args, **options):
        created_count = 0
        for code, nom, ordre in DEGRES:
            obj, created = Degre.objects.update_or_create(
                code=code,
                defaults={"nom": nom, "ordre": ordre},
            )
            if created:
                created_count += 1

        self.stdout.write(self.style.SUCCESS(f"✅ Seed degrés terminé. Nouveaux: {created_count}"))
