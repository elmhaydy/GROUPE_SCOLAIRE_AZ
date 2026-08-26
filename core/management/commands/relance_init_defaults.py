"""
Initialise les règles de relance par défaut.
Idempotent : ne crée que les règles manquantes.

Usage:
    python manage.py relance_init_defaults
    python manage.py relance_init_defaults --reset   # supprime tout et recrée
"""
from django.core.management.base import BaseCommand
from core.models_relance import RelanceRule


DEFAULTS = [
    # ─── Impayés ───────────────────────────────────────────────
    {
        "type": "IMPAYE", "niveau_relance": 1, "jours_apres": 3,
        "nom": "Impayé — Rappel J+3",
        "intervalle_min_jours": 3,
        "message_defaut": "AZ: Rappel — {eleve} ({groupe}) doit {montant} MAD ({mois}). Merci de régulariser.",
        "ordre": 1,
    },
    {
        "type": "IMPAYE", "niveau_relance": 1, "jours_apres": 7,
        "nom": "Impayé — Rappel J+7",
        "intervalle_min_jours": 4,
        "message_defaut": "AZ: Rappel — {eleve} ({groupe}) doit {montant} MAD ({mois}). Merci de régulariser rapidement.",
        "ordre": 2,
    },
    {
        "type": "IMPAYE", "niveau_relance": 2, "jours_apres": 15,
        "nom": "Impayé — Urgent J+15",
        "intervalle_min_jours": 7,
        "message_defaut": "AZ: URGENT — {eleve} ({groupe}) a {montant} MAD impayés ({mois}). Veuillez contacter la direction.",
        "ordre": 3,
    },
    {
        "type": "IMPAYE", "niveau_relance": 3, "jours_apres": 30,
        "nom": "Impayé — Dernier avis J+30",
        "intervalle_min_jours": 14,
        "message_defaut": "AZ: DERNIER AVIS — {eleve} ({groupe}) : {montant} MAD ({mois}) toujours impayés. Contactez l'école de toute urgence.",
        "ordre": 4,
    },
    # ─── Absences répétées ─────────────────────────────────────
    {
        "type": "ABSENCE", "niveau_relance": 1, "jours_apres": 0,
        "nom": "Absences répétées — seuil 3/mois",
        "seuil_occurrences": 3,
        "intervalle_min_jours": 7,
        "message_defaut": "AZ: {eleve} ({groupe}) a {nb} absences ce mois. Merci de nous contacter.",
        "ordre": 1,
    },
    {
        "type": "ABSENCE", "niveau_relance": 2, "jours_apres": 0,
        "nom": "Absences répétées — seuil 5/mois",
        "seuil_occurrences": 5,
        "intervalle_min_jours": 7,
        "message_defaut": "AZ: URGENT — {eleve} ({groupe}) totalise {nb} absences ce mois. Un entretien est nécessaire.",
        "ordre": 2,
    },
    # ─── Retards répétés ───────────────────────────────────────
    {
        "type": "RETARD", "niveau_relance": 1, "jours_apres": 0,
        "nom": "Retards répétés — seuil 4/mois",
        "seuil_occurrences": 4,
        "intervalle_min_jours": 7,
        "message_defaut": "AZ: {eleve} ({groupe}) a {nb} retards ce mois. Merci de veiller à la ponctualité.",
        "ordre": 1,
    },
    # ─── Renouvellement inscription ────────────────────────────
    {
        "type": "RENOUVELLEMENT", "niveau_relance": 1, "jours_apres": 30,
        "nom": "Renouvellement — 30 jours avant fin d'année",
        "intervalle_min_jours": 25,
        "message_defaut": "AZ: L'année {annee} se termine le {date}. Pensez à renouveler l'inscription de {eleve}. Contactez-nous.",
        "ordre": 1,
    },
    {
        "type": "RENOUVELLEMENT", "niveau_relance": 2, "jours_apres": 15,
        "nom": "Renouvellement — 15 jours avant fin d'année",
        "intervalle_min_jours": 12,
        "message_defaut": "AZ: Plus que 15 jours ! Renouvelez vite l'inscription de {eleve} pour l'année prochaine. Tel: direction.",
        "ordre": 2,
    },
    {
        "type": "RENOUVELLEMENT", "niveau_relance": 3, "jours_apres": 7,
        "nom": "Renouvellement — Dernière semaine",
        "intervalle_min_jours": 6,
        "message_defaut": "AZ: Dernière semaine pour renouveler l'inscription de {eleve}. Contactez l'école maintenant.",
        "ordre": 3,
    },
]


class Command(BaseCommand):
    help = "Crée les règles de relance par défaut."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Supprime toutes les règles existantes avant de recréer.")

    def handle(self, *args, **options):
        if options["reset"]:
            count, _ = RelanceRule.objects.all().delete()
            self.stdout.write(self.style.WARNING(f"  {count} règle(s) supprimée(s)."))

        created = 0
        for d in DEFAULTS:
            exists = RelanceRule.objects.filter(
                type=d["type"], niveau_relance=d["niveau_relance"], jours_apres=d["jours_apres"]
            ).exists()
            if exists:
                continue
            seuil = d.pop("seuil_occurrences", 3)
            rule = RelanceRule(**d, seuil_occurrences=seuil, actif=True)
            rule.save()
            self.stdout.write(f"  OK {rule}")
            created += 1

        self.stdout.write(self.style.SUCCESS(
            f"{created} règle(s) créée(s) — {len(DEFAULTS) - created} déjà existante(s)."
        ))
