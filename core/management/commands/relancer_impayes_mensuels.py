from django.core.management.base import BaseCommand
from django.utils import timezone
from decimal import Decimal
from django.db.models import F, DecimalField, ExpressionWrapper
from django.db.models.functions import Coalesce

from core.models import EcheanceMensuelle, RelanceMensuelle

class Command(BaseCommand):
    help = "Crée des relances pour les échéances mensuelles impayées (échues)."

    def handle(self, *args, **options):
        today = timezone.now().date()

        qs = EcheanceMensuelle.objects.filter(date_echeance__lte=today).annotate(
            reste=ExpressionWrapper(
                Coalesce(F("montant_du"), Decimal("0.00")) - Coalesce(F("montant_paye"), Decimal("0.00")),
                output_field=DecimalField(max_digits=10, decimal_places=2)
            )
        ).filter(reste__gt=Decimal("0.00"))

        created = 0
        for e in qs:
            # ✅ éviter spam : 1 relance par jour max
            already = e.relances.filter(sent_at__date=today).exists()
            if already:
                continue

            RelanceMensuelle.objects.create(
                echeance=e,
                canal="AVIS",
                message=f"Mensualité M{e.mois_index} impayée : reste {e.reste} MAD"
            )
            created += 1

        self.stdout.write(self.style.SUCCESS(f"Relances créées: {created}"))
