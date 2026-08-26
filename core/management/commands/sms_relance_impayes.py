from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import EcheanceMensuelle
from core.services.sms_dispatcher import send_event


class Command(BaseCommand):
    help = "Envoie des relances SMS pour les impayés (batch)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=200,
            help="Nombre maximal d'échéances à traiter.",
        )
        parser.add_argument(
            "--statuses",
            nargs="+",
            default=["A_PAYER", "IMPAYE", "PARTIEL"],
            help="Statuts d'échéance à relancer.",
        )

    def handle(self, *args, **options):
        limit = options["limit"]
        statuses = options["statuses"]
        now = timezone.now()

        qs = (
            EcheanceMensuelle.objects.select_related("eleve", "groupe")
            .filter(statut__in=statuses)
            .order_by("date_echeance")[:limit]
        )

        sent = 0
        for ech in qs:
            eleve = getattr(ech, "eleve", None)
            if not eleve:
                continue

            rel = getattr(eleve, "parenteleve_set", None)
            parent = rel.first().parent if rel and rel.first() else None
            if not parent:
                continue

            reste = (ech.montant_du or Decimal("0")) - (ech.montant_paye or Decimal("0"))
            if reste <= 0:
                continue

            payload = {
                "parent": parent,
                "eleve": getattr(eleve, "nom_complet", str(eleve)),
                "groupe": getattr(getattr(eleve, "groupe", None), "nom", "") or "",
                "montant": reste,
                "date": ech.date_echeance.strftime("%d/%m/%Y") if getattr(ech, "date_echeance", None) else now.strftime("%d/%m/%Y"),
                "ref": ech.id,
            }

            send_event("impaye", payload)
            sent += 1

        self.stdout.write(self.style.SUCCESS(f"Relances traitées: {sent}"))
