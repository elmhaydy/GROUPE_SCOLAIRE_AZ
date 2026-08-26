"""
python manage.py relance_auto
python manage.py relance_auto --type impaye
python manage.py relance_auto --type absence
python manage.py relance_auto --type retard
python manage.py relance_auto --type renouvellement
python manage.py relance_auto --dry-run
python manage.py relance_auto --limit 100
"""
from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import (
    AnneeScolaire, EcheanceMensuelle, Absence, Inscription,
    SmsHistorique, SmsSettings,
)
from core.models_relance import RelanceRule, RelanceLog
from core.services.sms_provider import normalize_phone, send_sms_via_bulksms_ma


def _get_parent(eleve):
    rel = getattr(eleve, "parenteleve_set", None)
    first = rel.select_related("parent").first() if rel else None
    return first.parent if first else None


def _fill(template: str, payload: dict) -> str:
    try:
        return template.format(**payload)
    except (KeyError, ValueError):
        return template


def _already_relanced(rule, eleve_id, since: date) -> bool:
    return RelanceLog.objects.filter(
        rule=rule,
        eleve_id=eleve_id,
        dry_run=False,
        sent_at__date__gte=since,
    ).exists()


def _send_sms(parent, phone, message, event="impaye") -> tuple[bool, str]:
    sms_settings = SmsSettings.load()
    if not phone:
        return False, "Numéro invalide"
    if not getattr(parent, "sms_optin", True):
        return False, "Parent opt-out"
    ok, msg_id, err = send_sms_via_bulksms_ma(phone, message)
    hist = SmsHistorique.objects.create(
        parent=parent,
        telephone=phone,
        message=message,
        status="SENT" if ok else "FAILED",
        provider=sms_settings.provider_name or "bulksms",
        event=event if event in ["absence", "paiement", "impaye"] else "autre",
        provider_message_id=msg_id or "",
        error_message=err or "",
    )
    return ok, hist.pk if ok else (err or "Échec envoi")


class Command(BaseCommand):
    help = "Relances automatiques intelligentes (impayés, absences, retards, renouvellements)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--type",
            choices=["all", "impaye", "absence", "retard", "renouvellement"],
            default="all",
        )
        parser.add_argument("--dry-run", action="store_true", default=False)
        parser.add_argument("--limit", type=int, default=500)

    def handle(self, *args, **options):
        run_type = options["type"]
        dry_run  = options["dry_run"]
        limit    = options["limit"]
        today    = timezone.localdate()

        sms_settings = SmsSettings.load()
        if not sms_settings.enable_impaye and run_type in ("all", "impaye"):
            self.stdout.write(self.style.WARNING("SMS impayés désactivés dans les paramètres."))

        totals = {"impaye": 0, "absence": 0, "retard": 0, "renouvellement": 0}

        if run_type in ("all", "impaye"):
            totals["impaye"] = self._run_impayes(today, dry_run, limit, sms_settings)

        if run_type in ("all", "absence"):
            totals["absence"] = self._run_absences_retards(today, dry_run, limit, "ABSENCE", "absence")

        if run_type in ("all", "retard"):
            totals["retard"] = self._run_absences_retards(today, dry_run, limit, "RETARD", "retard")

        if run_type in ("all", "renouvellement"):
            totals["renouvellement"] = self._run_renouvellements(today, dry_run, limit, sms_settings)

        prefix = "[DRY-RUN] " if dry_run else ""
        self.stdout.write(self.style.SUCCESS(
            f"{prefix}Relances: impayés={totals['impaye']}  "
            f"absences={totals['absence']}  retards={totals['retard']}  "
            f"renouvellements={totals['renouvellement']}"
        ))

    # ------------------------------------------------------------------
    # IMPAYÉS
    # ------------------------------------------------------------------
    def _run_impayes(self, today: date, dry_run: bool, limit: int, sms_settings) -> int:
        rules = RelanceRule.active_for("IMPAYE")
        if not rules.exists():
            self.stdout.write("  [impayé] Aucune règle active.")
            return 0

        sent = 0
        for rule in rules:
            threshold = today - timedelta(days=rule.jours_apres)
            cooldown  = today - timedelta(days=rule.intervalle_min_jours)

            echeances = (
                EcheanceMensuelle.objects
                .select_related("eleve", "groupe", "annee", "inscription")
                .filter(
                    statut__in=["A_PAYER", "PARTIEL"],
                    date_echeance__lte=threshold,
                )
                .order_by("date_echeance")[:limit]
            )

            for ech in echeances:
                eleve = ech.eleve
                if not eleve:
                    continue

                reste = (ech.montant_du or Decimal("0")) - (ech.montant_paye or Decimal("0"))
                if reste <= 0:
                    continue

                parent = _get_parent(eleve)
                if not parent:
                    continue

                # Cooldown : même règle + même élève
                if _already_relanced(rule, eleve.pk, cooldown):
                    continue

                groupe = ech.groupe
                payload = {
                    "eleve":   getattr(eleve, "nom_complet", str(eleve)),
                    "groupe":  getattr(groupe, "nom", "") if groupe else "",
                    "montant": f"{reste:.2f}",
                    "mois":    ech.mois_nom,
                    "date":    ech.date_echeance.strftime("%d/%m/%Y") if ech.date_echeance else "",
                    "nb":      "",
                    "annee":   getattr(getattr(ech, "annee", None), "nom", ""),
                }

                tone = {
                    1: "AZ: Rappel — {eleve} ({groupe}) doit {montant} MAD ({mois}). Merci de régulariser.",
                    2: "AZ: URGENT — {eleve} ({groupe}) a {montant} MAD impayés ({mois}). Veuillez régler rapidement.",
                    3: "AZ: DERNIER AVIS — {eleve} ({groupe}) : {montant} MAD ({mois}) toujours impayés. Contactez l'école.",
                }
                template = rule.message_defaut or tone.get(rule.niveau_relance, tone[1])
                message  = _fill(template, payload)

                log_kwargs = dict(
                    rule=rule, eleve=eleve, parent=parent,
                    echeance=ech, type_relance="IMPAYE",
                    niveau_relance=rule.niveau_relance,
                    message=message, dry_run=dry_run,
                )

                if dry_run:
                    RelanceLog.objects.create(**log_kwargs, success=True)
                    self.stdout.write(f"  [DRY impayé N{rule.niveau_relance}] {eleve} → {message[:60]}")
                    sent += 1
                    continue

                phone = normalize_phone(
                    getattr(parent, "telephone_norm", "") or getattr(parent, "telephone", "")
                )
                ok, result = _send_sms(parent, phone, message, event="impaye")

                sms_obj = None
                if ok:
                    try:
                        sms_obj = SmsHistorique.objects.get(pk=result)
                    except Exception:
                        pass

                RelanceLog.objects.create(
                    **log_kwargs, success=ok, sms=sms_obj,
                    error="" if ok else str(result),
                )
                if ok:
                    sent += 1

        return sent

    # ------------------------------------------------------------------
    # ABSENCES / RETARDS
    # ------------------------------------------------------------------
    def _run_absences_retards(
        self, today: date, dry_run: bool, limit: int,
        rule_type: str, absence_type: str
    ) -> int:
        rules = RelanceRule.active_for(rule_type)
        if not rules.exists():
            return 0

        # On travaille sur le mois en cours
        month_start = today.replace(day=1)

        sent = 0
        for rule in rules:
            cooldown = today - timedelta(days=rule.intervalle_min_jours)
            seuil    = rule.seuil_occurrences

            # Regrouper les absences/retards du mois par élève
            from django.db.models import Count
            abs_type = "ABS" if absence_type == "absence" else "RET"
            eleve_counts = (
                Absence.objects
                .filter(type=abs_type, date__gte=month_start, date__lte=today)
                .values("eleve_id", "groupe_id")
                .annotate(nb=Count("id"))
                .filter(nb__gte=seuil)
                .order_by("-nb")[:limit]
            )

            for row in eleve_counts:
                eleve_id = row["eleve_id"]
                nb       = row["nb"]

                if _already_relanced(rule, eleve_id, cooldown):
                    continue

                from core.models import Eleve, Groupe
                eleve  = Eleve.objects.select_related().filter(pk=eleve_id).first()
                groupe = Groupe.objects.filter(pk=row["groupe_id"]).first() if row["groupe_id"] else None
                parent = _get_parent(eleve) if eleve else None

                if not eleve or not parent:
                    continue

                payload = {
                    "eleve":   getattr(eleve, "nom_complet", str(eleve)),
                    "groupe":  getattr(groupe, "nom", "") if groupe else "",
                    "nb":      str(nb),
                    "montant": "",
                    "mois":    today.strftime("%B %Y"),
                    "date":    today.strftime("%d/%m/%Y"),
                    "annee":   "",
                }

                label = "absences" if absence_type == "absence" else "retards"
                default_tpl = f"AZ: {{eleve}} ({{groupe}}) a {{nb}} {label} ce mois. Merci de nous contacter."
                message = _fill(rule.message_defaut or default_tpl, payload)

                log_kwargs = dict(
                    rule=rule, eleve=eleve, parent=parent,
                    type_relance=rule_type,
                    niveau_relance=rule.niveau_relance,
                    message=message, dry_run=dry_run,
                )

                if dry_run:
                    RelanceLog.objects.create(**log_kwargs, success=True)
                    self.stdout.write(f"  [DRY {rule_type}] {eleve} nb={nb} → {message[:60]}")
                    sent += 1
                    continue

                phone = normalize_phone(
                    getattr(parent, "telephone_norm", "") or getattr(parent, "telephone", "")
                )
                ok, result = _send_sms(parent, phone, message, event="absence")

                sms_obj = None
                if ok:
                    try:
                        sms_obj = SmsHistorique.objects.get(pk=result)
                    except Exception:
                        pass

                RelanceLog.objects.create(
                    **log_kwargs, success=ok, sms=sms_obj,
                    error="" if ok else str(result),
                )
                if ok:
                    sent += 1

        return sent

    # ------------------------------------------------------------------
    # RENOUVELLEMENTS
    # ------------------------------------------------------------------
    def _run_renouvellements(self, today: date, dry_run: bool, limit: int, sms_settings) -> int:
        rules = RelanceRule.active_for("RENOUVELLEMENT")
        if not rules.exists():
            return 0

        annee_active = AnneeScolaire.objects.filter(is_active=True).first()
        if not annee_active:
            self.stdout.write("  [renouvellement] Aucune année scolaire active.")
            return 0

        sent = 0
        for rule in rules:
            # Déclencher si on est à exactement jours_apres jours de la fin
            target_date = annee_active.date_fin - timedelta(days=rule.jours_apres)
            if today != target_date:
                continue

            cooldown = today - timedelta(days=rule.intervalle_min_jours)

            inscriptions = (
                Inscription.objects
                .select_related("eleve", "groupe", "annee")
                .filter(annee=annee_active)
                .order_by("eleve__nom")[:limit]
            )

            for insc in inscriptions:
                eleve  = insc.eleve
                parent = _get_parent(eleve) if eleve else None

                if not eleve or not parent:
                    continue

                if _already_relanced(rule, eleve.pk, cooldown):
                    continue

                payload = {
                    "eleve":   getattr(eleve, "nom_complet", str(eleve)),
                    "groupe":  getattr(insc.groupe, "nom", ""),
                    "annee":   annee_active.nom,
                    "date":    annee_active.date_fin.strftime("%d/%m/%Y"),
                    "montant": "",
                    "mois":    "",
                    "nb":      str(rule.jours_apres),
                }

                default_tpl = (
                    "AZ: L'année {annee} se termine le {date}. "
                    "Pensez à renouveler l'inscription de {eleve}. Contactez-nous."
                )
                message = _fill(rule.message_defaut or default_tpl, payload)

                log_kwargs = dict(
                    rule=rule, eleve=eleve, parent=parent,
                    inscription=insc, type_relance="RENOUVELLEMENT",
                    niveau_relance=rule.niveau_relance,
                    message=message, dry_run=dry_run,
                )

                if dry_run:
                    RelanceLog.objects.create(**log_kwargs, success=True)
                    self.stdout.write(f"  [DRY renouvellement J-{rule.jours_apres}] {eleve} → {message[:60]}")
                    sent += 1
                    continue

                phone = normalize_phone(
                    getattr(parent, "telephone_norm", "") or getattr(parent, "telephone", "")
                )
                ok, result = _send_sms(parent, phone, message, event="autre")

                sms_obj = None
                if ok:
                    try:
                        sms_obj = SmsHistorique.objects.get(pk=result)
                    except Exception:
                        pass

                RelanceLog.objects.create(
                    **log_kwargs, success=ok, sms=sms_obj,
                    error="" if ok else str(result),
                )
                if ok:
                    sent += 1

        return sent
