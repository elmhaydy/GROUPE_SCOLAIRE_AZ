from django.core.management.base import BaseCommand
from core.models import Inscription, Periode

class Command(BaseCommand):
    help = "Assigne Semestre 1 aux inscriptions qui n'ont pas de période."

    def handle(self, *args, **options):
        updated = 0
        qs = Inscription.objects.select_related("annee").filter(periode__isnull=True)

        for ins in qs:
            p = Periode.objects.filter(annee=ins.annee, ordre=1).first()
            if p:
                ins.periode = p
                ins.save(update_fields=["periode"])
                updated += 1

        self.stdout.write(self.style.SUCCESS(f"OK — {updated} inscriptions mises à jour."))
