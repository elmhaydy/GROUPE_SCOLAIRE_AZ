# core/views.py
from datetime import timedelta
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from core.permissions import group_required
from itertools import chain
from decimal import Decimal
from django.db.models import Avg, Count
from core.services.pedagogie import sync_enseignant_groupe_from_matiere
from core.views_prof import _allowed_groupes as _allowed_groupes_for_user
from datetime import time
from django.db.models import Q


from .forms import AnneeScolaireForm
from .models import AnneeScolaire,PaiementLigne, ProfGroupe

from .models import Degre
from .forms import DegreForm

from .models import Niveau
from .forms import NiveauForm

from django.db.models import Q
from .models import Groupe
from .forms import GroupeForm

from .models import Eleve
from .forms import EleveForm
from .models import AnneeScolaire, Niveau, FraisNiveau

from .models import Inscription
from .forms import InscriptionForm

from django.http import JsonResponse

from django.db.models import Sum, DecimalField
from django.db.models.functions import Coalesce

from .models import Paiement
from .forms import PaiementForm


from .models import Enseignant
from .forms import EnseignantForm

from .models import Seance
from .forms import SeanceForm

from .models import Absence
from .forms import AbsenceForm

from .models import Parent, ParentEleve
from .forms import ParentForm, ParentEleveFormSet

from . import pdf_utils

import openpyxl
from openpyxl.styles import Font, Alignment
from django.http import HttpResponse

from .models import Matiere, Periode, Evaluation, Note
from .forms import MatiereForm, EvaluationForm

from .notes_utils import bulletin_data, rang_eleve

from .models import Recouvrement, Relance
from django.utils import timezone

from django.db.models import Sum, DecimalField, F, ExpressionWrapper

from .models import FraisNiveau, AnneeScolaire

from django.db.models import Count, Max
from datetime import date, datetime
from django.utils import timezone

from .models import EnseignantGroupe
from .forms import EnseignantGroupeForm

from .utils_users import get_or_create_user_with_group

import csv
from django.contrib.auth import get_user_model


from .models import Avis, SmsHistorique, Parent, ParentEleve, Eleve, Groupe, Niveau, Degre
from .forms_communication import AvisForm, SmsSendForm
from .services.sms_provider import normalize_phone, send_sms_via_twilio

import calendar
from datetime import date as date_cls
from datetime import date

from django.db.models import Sum, Count, F, Value, DecimalField
from django.db.models.functions import Coalesce, TruncMonth
from django.shortcuts import render, redirect

from core.models import Eleve, Groupe, Inscription, Paiement, AnneeScolaire

from datetime import date, datetime
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import (
    Sum, Count, F, Value, DecimalField,
)
from django.db.models.functions import Coalesce, TruncMonth
from django.shortcuts import render, redirect

from core.models import (
    AnneeScolaire, Eleve, Groupe, Paiement, Inscription, Absence
)



def _as_datetime_safe(value):
    """
    Convertit value -> datetime (timezone-aware si possible).
    Accepte: datetime, date, str ISO, None.
    """
    if value is None:
        return timezone.make_aware(datetime.min) if timezone.is_naive(datetime.min) else datetime.min

    if isinstance(value, datetime):
        return timezone.make_aware(value) if timezone.is_naive(value) else value

    if isinstance(value, date):
        dt = datetime(value.year, value.month, value.day)
        return timezone.make_aware(dt)

    if isinstance(value, str):
        s = value.strip()
        try:
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
            return timezone.make_aware(dt) if timezone.is_naive(dt) else dt
        except Exception:
            return timezone.make_aware(datetime.min) if timezone.is_naive(datetime.min) else datetime.min

    return timezone.make_aware(datetime.min) if timezone.is_naive(datetime.min) else datetime.min

# ============================================================
# Helpers date (si tu les as déjà ailleurs, garde les tiens)
# ============================================================
def _month_start(d: date) -> date:
    return date(d.year, d.month, 1)

def _add_months(d: date, months: int) -> date:
    y = d.year + (d.month - 1 + months) // 12
    m = (d.month - 1 + months) % 12 + 1
    return date(y, m, 1)

# ============================================================
# Helpers roles (si tu les as déjà ailleurs, garde les tiens)
# ============================================================
def _is_superadmin(user) -> bool:
    return bool(getattr(user, "is_superuser", False))

def _is_admin(user) -> bool:
    if _is_superadmin(user):
        return True
    # adapte si tu utilises Groups
    return user.groups.filter(name__in=["ADMIN", "SUPER_ADMIN"]).exists()


# ============================================================
# Dashboard Context — FINAL (fix Decimal vs Int)
# ============================================================


# ============================================================
# Dashboard Context — FINAL (Impayés mensuels + Encaissé non 0)
# - Impayés: basé sur EcheanceMensuelle (mois courant) + (option) inscription
# - Encaissé: Paiement + TransactionFinance (nouveau système)
# ============================================================

from datetime import date, datetime
from decimal import Decimal
import json

from django.db.models import (
    Sum, Count, F, Q, Value, DecimalField, ExpressionWrapper
)
from django.db.models.functions import TruncMonth
from django.utils import timezone
from django.db.models.functions import Coalesce

MONEY_FIELD = DecimalField(max_digits=12, decimal_places=2)
ZERO_MONEY = Value(Decimal("0.00"), output_field=MONEY_FIELD)


def _month_key(x):
    if isinstance(x, datetime):
        x = x.date()
    if isinstance(x, date):
        return date(x.year, x.month, 1)
    return None


def _model_has_field(model, field_name: str) -> bool:
    try:
        model._meta.get_field(field_name)
        return True
    except Exception:
        return False


def _last_12_months_labels(today: date):
    labels = []
    d = date(today.year, today.month, 1)
    for i in range(11, -1, -1):
        y = d.year + (d.month - 1 - i) // 12
        m = (d.month - 1 - i) % 12 + 1
        labels.append(date(y, m, 1))
    return labels


def _trend(cur, prev):
    cur = Decimal(cur or "0.00")
    prev = Decimal(prev or "0.00")

    # Aucun mouvement
    if cur == 0 and prev == 0:
        return 0

    # Nouveau chiffre ce mois-ci
    if prev == 0 and cur > 0:
        return None  # ⬅️ important

    # Chute totale
    if prev > 0 and cur == 0:
        return -100

    return int(((cur - prev) / prev) * 100)





def _add_months(d: date, months: int) -> date:
    y = d.year + (d.month - 1 + months) // 12
    m = (d.month - 1 + months) % 12 + 1
    return date(y, m, 1)
# --- helper: champ élève dispo dans EcheanceMensuelle ---
def _echeance_eleve_values_key():
    """
    Retourne une clé utilisable dans QuerySet.values()
    IMPORTANT: doit être un champ RÉELLEMENT présent dans le modèle Django.
    """
    # EcheanceMensuelle a toujours "eleve" dans le modèle actuel
    return "eleve_id"



def _build_dashboard_context():
    today = timezone.now().date()
    derniers_paiements = []
    # =========================
    # Périodes
    # =========================
    start_this_month = date(today.year, today.month, 1)
    start_last_month = _add_months(start_this_month, -1)
    start_next_month = _add_months(start_this_month, 1)

    # =========================
    # Année active
    # =========================
    annee_active_obj = AnneeScolaire.objects.filter(is_active=True).first()
    annee_active = annee_active_obj.nom if annee_active_obj else "—"

    # Si pas d'année active -> safe
    if not annee_active_obj:
        return {
            "today": today,
            "current_date": today,
            "annee_active": annee_active,
            "nb_eleves": 0,
            "nb_groupes": 0,
            "total_paye": Decimal("0.00"),
            "total_impayes": Decimal("0.00"),
            "nb_paiements": 0,
            "nb_impayes": 0,
            "taux_paiement": 0,
            "eleves_trend": 0,
            "groupes_trend": 0,
            "revenue_trend": 0,
            "payment_trend": 0,
            "derniers_paiements": [],
            "nouvelles_inscriptions": [],
            "impayes_recents": [],
            "repartition_eleves": [],
            "presences": {"presents": 0, "absents": 0, "retards": 0, "total": 0, "taux_presence": 0, "taux_absence": 0, "taux_retard": 0},
            "objectif_mensuel": 0,
            "objectif_atteint": 0,
            "chart_labels": json.dumps([]),
            "chart_paiements": json.dumps([]),
            "chart_inscriptions": json.dumps([]),

            # ✅ nouveaux (mensuel)
            "mois_courant": 0,
            "mois_courant_nom": "",
        }

    # =========================
    # Helpers “mois courant scolaire”
    # (tu as déjà ces fonctions dans ton projet, utilisées dans impayes_mensuels_list)
    # =========================
    idx_courant = mois_index_courant(annee_active_obj, today)  # 1..10 (Sep..Jun)
    idx_courant = max(1, min(10, int(idx_courant or 1)))
    mois_courant_nom = mois_nom(idx_courant)

    # =========================
    # Global counts
    # =========================
    inscs_active = Inscription.objects.filter(annee_id=annee_active_obj.id)

    nb_eleves = inscs_active.values("eleve_id").distinct().count()
    nb_groupes = inscs_active.values("groupe_id").distinct().count()


    # =========================
    # ✅ ENCAISSÉ (mois courant) => Paiement + TransactionFinance
    # =========================
    pay_mois_old = (
        Paiement.objects
        .filter(
            inscription__annee_id=annee_active_obj.id,
            date_paiement__gte=start_this_month,
            date_paiement__lt=start_next_month,
        )
        .aggregate(s=Coalesce(Sum("montant"), ZERO_MONEY))["s"]
        or Decimal("0.00")
    )

    pay_mois_new = (
        TransactionFinance.objects
        .filter(
            inscription__annee_id=annee_active_obj.id,
            date_transaction__gte=start_this_month,
            date_transaction__lt=start_next_month,
        )
        .aggregate(s=Coalesce(Sum("montant_total"), ZERO_MONEY))["s"]
        or Decimal("0.00")
    )


    total_encaisse_mois = (pay_mois_old or Decimal("0.00")) + (pay_mois_new or Decimal("0.00"))

    # ✅ pour tes listes “derniers paiements” on garde Paiement (si tu veux aussi tx, dis-moi)
    nb_paiements_old = Paiement.objects.filter(inscription__annee_id=annee_active_obj.id).count()
    nb_paiements_new = TransactionFinance.objects.filter(inscription__annee_id=annee_active_obj.id).count()
    nb_paiements = nb_paiements_old + nb_paiements_new



    # =========================
    # 🎯 OBJECTIF MENSUEL (ce qui est DÛ ce mois)
    # =========================

    # Scolarité du mois courant (du total)
    objectif_sco = (
        EcheanceMensuelle.objects
        .filter(annee_id=annee_active_obj.id, mois_index=idx_courant)
        .aggregate(s=Coalesce(Sum("montant_du"), ZERO_MONEY))["s"]
        or Decimal("0.00")
    )

    # Transport du mois courant (safe)
    objectif_tr = Decimal("0.00")
    try:
        objectif_tr = (
            EcheanceTransportMensuelle.objects
            .filter(annee_id=annee_active_obj.id, mois_index=idx_courant)
            .aggregate(s=Coalesce(Sum("montant_du"), ZERO_MONEY))["s"]
            or Decimal("0.00")
        )
    except Exception:
        pass

    # Inscription (optionnel) -> ce qui est dû au total (année active)
    objectif_ins = (
        Inscription.objects
        .filter(
            annee_id=annee_active_obj.id,
            date_inscription__gte=start_this_month,
            date_inscription__lt=start_next_month,
        )
        .aggregate(s=Coalesce(Sum("frais_inscription_du"), ZERO_MONEY))["s"]
        or Decimal("0.00")
    )


    objectif_mensuel = (objectif_sco + objectif_tr + objectif_ins)

    # % atteint (cap 100%)
    if objectif_mensuel > 0:
        objectif_atteint = int(min((total_encaisse_mois / objectif_mensuel) * 100, 100))
    else:
        objectif_atteint = 0

    # =========================
    # ✅ IMPAYÉS (MENSUEL)
    # - Scolarité : EcheanceMensuelle du mois courant (reste > 0)
    # - Transport : si EcheanceTransportMensuelle existe (reste > 0)
    # - Inscription : optionnel (reste inscription) -> je l’ajoute car impayé réel
    # =========================
    sco_qs_mois = (
        EcheanceMensuelle.objects
        .filter(annee_id=annee_active_obj.id, mois_index=idx_courant)
        .annotate(
            reste=ExpressionWrapper(
                Coalesce(F("montant_du"), ZERO_MONEY) - Coalesce(F("montant_paye"), ZERO_MONEY),
                output_field=MONEY_FIELD,
            )
        )
    )

    total_impaye_sco_mois = (
        sco_qs_mois.filter(reste__gt=0)
        .aggregate(s=Coalesce(Sum("reste"), ZERO_MONEY))["s"]
        or Decimal("0.00")
    )

    k = _echeance_eleve_values_key()
    nb_impaye_sco_mois = sco_qs_mois.filter(reste__gt=0).values(k).distinct().count()

    # Transport (safe si modèle pas importé)
    total_impaye_tr_mois = Decimal("0.00")
    nb_impaye_tr_mois = 0
    try:
        tr_qs_mois = (
            EcheanceTransportMensuelle.objects
            .filter(annee_id=annee_active_obj.id, mois_index=idx_courant)
            .annotate(
                reste=ExpressionWrapper(
                    Coalesce(F("montant_du"), ZERO_MONEY) - Coalesce(F("montant_paye"), ZERO_MONEY),
                    output_field=MONEY_FIELD,
                )
            )
        )
        total_impaye_tr_mois = (
            tr_qs_mois.filter(reste__gt=0)
            .aggregate(s=Coalesce(Sum("reste"), ZERO_MONEY))["s"]
            or Decimal("0.00")
        )
        nb_impaye_tr_mois = tr_qs_mois.filter(reste__gt=0).values("eleve_id").distinct().count()
    except Exception:
        pass

    # Inscription (reste inscription)
    insc_qs = Inscription.objects.filter(annee_id=annee_active_obj.id).annotate(
        reste_ins=ExpressionWrapper(
            Coalesce(F("frais_inscription_du"), ZERO_MONEY) - Coalesce(F("frais_inscription_paye"), ZERO_MONEY),
            output_field=MONEY_FIELD,
        )
    )

    total_impaye_ins = (
        insc_qs.filter(reste_ins__gt=0)
        .aggregate(s=Coalesce(Sum("reste_ins"), ZERO_MONEY))["s"]
        or Decimal("0.00")
    )
    nb_impaye_ins = insc_qs.filter(reste_ins__gt=0).values("eleve_id").distinct().count()

    # ✅ total impayés du dashboard (mensuel)
    total_impayes_mois = (total_impaye_sco_mois + total_impaye_tr_mois + total_impaye_ins)

    # ✅ nb dossiers impayés (distinct élèves) -> on prend max simple
    # (si tu veux distinct global exact par union, je te le fais aussi)
    nb_impayes_mois = max(nb_impaye_sco_mois, nb_impaye_tr_mois, nb_impaye_ins)

    # =========================
    # Trends (encaisse)
    # =========================
    pay_last_old = (
        Paiement.objects
        .filter(
            inscription__annee_id=annee_active_obj.id,
            date_paiement__gte=start_last_month,
            date_paiement__lt=start_this_month,
        )
        .aggregate(s=Coalesce(Sum("montant"), ZERO_MONEY))["s"]
        or Decimal("0.00")
    )

    pay_last_new = (
        TransactionFinance.objects
        .filter(
            inscription__annee_id=annee_active_obj.id,
            date_transaction__gte=start_last_month,
            date_transaction__lt=start_this_month,
        )
        .aggregate(s=Coalesce(Sum("montant_total"), ZERO_MONEY))["s"]
        or Decimal("0.00")
    )

    total_encaisse_last = (pay_last_old or Decimal("0.00")) + (pay_last_new or Decimal("0.00"))

    revenue_trend = _trend(total_encaisse_mois, total_encaisse_last)

    # Trends inscriptions (ok)
    eleves_this = Inscription.objects.filter(
        annee_id=annee_active_obj.id,
        date_inscription__gte=start_this_month,
        date_inscription__lt=start_next_month,
    ).count()

    eleves_last = Inscription.objects.filter(
        annee_id=annee_active_obj.id,
        date_inscription__gte=start_last_month,
        date_inscription__lt=start_this_month,
    ).count()

    eleves_trend = _trend(eleves_this, eleves_last)

    # =========================
    # ✅ TAUX PAIEMENT (mensuel réel)
    # attendu_mois = scolarité du mois + transport du mois + inscriptions créées ce mois (optionnel)
    # =========================

    attendu_sco_mois = (
        EcheanceMensuelle.objects
        .filter(annee_id=annee_active_obj.id, mois_index=idx_courant)
        .aggregate(s=Coalesce(Sum("montant_du"), ZERO_MONEY))["s"]
        or Decimal("0.00")
    )

    # Transport du mois (safe)
    attendu_tr_mois = Decimal("0.00")
    try:
        attendu_tr_mois = (
            EcheanceTransportMensuelle.objects
            .filter(annee_id=annee_active_obj.id, mois_index=idx_courant)
            .aggregate(s=Coalesce(Sum("montant_du"), ZERO_MONEY))["s"]
            or Decimal("0.00")
        )
    except Exception:
        pass

    # Inscriptions du mois (pas toute l'année !)
    attendu_ins_mois = (
        Inscription.objects
        .filter(
            annee_id=annee_active_obj.id,
            date_inscription__gte=start_this_month,
            date_inscription__lt=start_next_month,
        )
        .aggregate(s=Coalesce(Sum("frais_inscription_du"), ZERO_MONEY))["s"]
        or Decimal("0.00")
    )

    attendu_mois = (attendu_sco_mois + attendu_tr_mois + attendu_ins_mois)

    # Taux (cap 100)
    if attendu_mois > 0:
        taux_paiement = int(min((total_encaisse_mois / attendu_mois) * 100, 100))
    else:
        taux_paiement = 0

    # ---------- Trend (mois dernier) ----------
    idx_last = max(1, min(10, idx_courant - 1))

    attendu_sco_last = (
        EcheanceMensuelle.objects
        .filter(annee_id=annee_active_obj.id, mois_index=idx_last)
        .aggregate(s=Coalesce(Sum("montant_du"), ZERO_MONEY))["s"]
        or Decimal("0.00")
    )

    attendu_tr_last = Decimal("0.00")
    try:
        attendu_tr_last = (
            EcheanceTransportMensuelle.objects
            .filter(annee_id=annee_active_obj.id, mois_index=idx_last)
            .aggregate(s=Coalesce(Sum("montant_du"), ZERO_MONEY))["s"]
            or Decimal("0.00")
        )
    except Exception:
        pass

    # inscriptions créées le mois dernier (pas toute l’année)
    attendu_ins_last = (
        Inscription.objects
        .filter(
            annee_id=annee_active_obj.id,
            date_inscription__gte=start_last_month,
            date_inscription__lt=start_this_month,
        )
        .aggregate(s=Coalesce(Sum("frais_inscription_du"), ZERO_MONEY))["s"]
        or Decimal("0.00")
    )

    attendu_last = (attendu_sco_last + attendu_tr_last + attendu_ins_last)

    taux_last = int(min((total_encaisse_last / attendu_last) * 100, 100)) if attendu_last > 0 else 0
    payment_trend = _trend(taux_paiement, taux_last)

    groupes_trend = 0  # safe

    # =========================
    # Dernières listes
    # =========================




    # =========================
    # ✅ Derniers paiements (Paiement + TransactionFinance)
    # =========================

    # A) Paiement (old)
    last_old = (
        Paiement.objects
        .select_related("inscription__eleve", "inscription__groupe")
        .filter(inscription__annee_id=annee_active_obj.id)
        .order_by("-date_paiement", "-id")[:8]
    )

    old_items = []
    for p in last_old:
        old_items.append({
            "type": "OLD",
            "eleve_nom": getattr(p.inscription.eleve, "nom_complet", str(p.inscription.eleve)),
            "groupe_nom": getattr(p.inscription.groupe, "nom", "—"),
            "montant": p.montant,
            "date": p.date_paiement,
            "mode": getattr(p, "mode", None),
            "mode_label": getattr(p, "get_mode_display", lambda: "")(),
        })

    # B) TransactionFinance (new)
    last_new = (
        TransactionFinance.objects
        .select_related("inscription__eleve", "inscription__groupe")
        .filter(inscription__annee_id=annee_active_obj.id)
        .order_by("-date_transaction", "-id")[:8]
    )

    new_items = []
    for t in last_new:
        new_items.append({
            "type": "NEW",
            "eleve_nom": getattr(t.inscription.eleve, "nom_complet", str(t.inscription.eleve)),
            "groupe_nom": getattr(t.inscription.groupe, "nom", "—"),
            "montant": t.montant_total,
            "date": t.date_transaction,
            "mode": getattr(t, "mode", None),
            "mode_label": getattr(t, "get_mode_display", lambda: "Transaction")() or "Transaction",
        })

        # C) Fusion + tri + top 8
    derniers_paiements = old_items + new_items
    derniers_paiements = sorted(
            derniers_paiements,
            key=lambda p: _as_datetime_safe(p.get("date")),
            reverse=True
    )[:8]


    nouvelles_inscriptions = (
        Inscription.objects
        .select_related("eleve", "groupe", "groupe__niveau")
        .filter(annee_id=annee_active_obj.id)
        .order_by("-date_inscription", "-id")[:8]
    )


    # Impayés récents : on garde ton ancien “reste inscription + scolarité cumulée”
    # (si tu veux “impayés du mois seulement” dans la liste, je te le change)
    impayes_recents = (
        Inscription.objects
        .select_related("eleve", "groupe")
        .filter(annee_id=annee_active_obj.id)
        .annotate(paiements_total=Coalesce(Sum("paiements__montant"), ZERO_MONEY))
        .annotate(reste=ExpressionWrapper(F("montant_total") - F("paiements_total"), output_field=MONEY_FIELD))
        .filter(reste__gt=0)
        .order_by("-reste")[:8]
    )


    # Répartition par niveau
    repartition_qs = (
        Inscription.objects
        .filter(annee_id=annee_active_obj.id)
        .select_related("groupe__niveau")
        .values("groupe__niveau__nom")
        .annotate(total=Count("id"))
        .order_by("-total")
    )

    repartition_eleves = [
        {"nom": r["groupe__niveau__nom"] or "—", "total": r["total"], "couleur": None}
        for r in repartition_qs
    ]

    # Présences
    absents = Absence.objects.filter(date=today, type="ABS").values("eleve_id").distinct().count()
    retards = Absence.objects.filter(date=today, type="RET").values("eleve_id").distinct().count()
    total = nb_eleves
    presents = max(total - absents, 0)

    presences = {
        "presents": presents,
        "absents": absents,
        "retards": retards,
        "total": total,
        "taux_presence": int((presents / total) * 100) if total else 0,
        "taux_absence": int((absents / total) * 100) if total else 0,
        "taux_retard": int((retards / total) * 100) if total else 0,
    }

    # =========================
    # Graphe Pilotage (12 mois) — Paiement + TransactionFinance + Inscriptions ✅
    # =========================
    months = _last_12_months_labels(today)

    # 1) Paiement par mois (OLD)
    pay_qs_old = (
        Paiement.objects
        .filter(inscription__annee_id=annee_active_obj.id)
        .annotate(m=TruncMonth("date_paiement"))
        .values("m")
        .annotate(total=Coalesce(Sum("montant"), ZERO_MONEY))
        .order_by("m")
    )
    old_map = {
        _month_key(row["m"]): Decimal(row["total"] or 0)
        for row in pay_qs_old
        if _month_key(row["m"]) is not None
    }

    # 2) TransactionFinance par mois (NEW)
    pay_qs_new = (
        TransactionFinance.objects
        .filter(inscription__annee_id=annee_active_obj.id)
        .annotate(m=TruncMonth("date_transaction"))
        .values("m")
        .annotate(total=Coalesce(Sum("montant_total"), ZERO_MONEY))
        .order_by("m")
    )
    new_map = {
        _month_key(row["m"]): Decimal(row["total"] or 0)
        for row in pay_qs_new
        if _month_key(row["m"]) is not None
    }

    # 3) Map finale = old + new (par mois)
    pay_map = {}
    for k in set(old_map.keys()) | set(new_map.keys()):
        pay_map[k] = float(old_map.get(k, Decimal("0.00")) + new_map.get(k, Decimal("0.00")))

    # 4) Inscriptions par mois (NB)
    # ✅ on prend date_inscription si existe, sinon fallback (created_at...)
    inscription_field = None
    for candidate in ["date_inscription", "created_at", "date_creation", "date"]:
        if _model_has_field(Inscription, candidate):
            inscription_field = candidate
            break

    ins_map = {}
    if inscription_field:
        ins_qs = (
            Inscription.objects
            .filter(annee_id=annee_active_obj.id)
            .annotate(m=TruncMonth(inscription_field))
            .values("m")
            .annotate(cnt=Count("id"))
            .order_by("m")
        )
        ins_map = {
            _month_key(row["m"]): int(row["cnt"] or 0)
            for row in ins_qs
            if _month_key(row["m"]) is not None
        }

    # Labels + séries alignées sur months
    months_fr = ["Jan", "Fév", "Mar", "Avr", "Mai", "Juin", "Juil", "Aoû", "Sep", "Oct", "Nov", "Déc"]
    chart_labels = [months_fr[m.month - 1] for m in months]
    chart_paiements = [pay_map.get(m, 0) for m in months]
    chart_inscriptions = [ins_map.get(m, 0) for m in months]

    # ✅ JSON pour le template
    chart_labels_json = json.dumps(chart_labels)
    chart_paiements_json = json.dumps(chart_paiements)
    chart_inscriptions_json = json.dumps(chart_inscriptions)


    # =========================
    # ✅ CONTEXT FINAL (ton template)
    # - total_paye => encaissé MENSUEL (plus 0)
    # - total_impayes => impayés MENSUELS (avec mois)
    # =========================
    return {
        "today": today,
        "current_date": today,

        "annee_active": annee_active,

        "nb_eleves": nb_eleves,
        "nb_groupes": nb_groupes,

        # ✅ dashboard KPI
        "total_paye": total_encaisse_mois,      # <= FIX (mensuel + tx)
        "total_impayes": total_impayes_mois,    # <= FIX (mensuel)
        "nb_paiements": nb_paiements,
        "nb_impayes": nb_impayes_mois,
        "taux_paiement": taux_paiement,

        "eleves_trend": eleves_trend,
        "groupes_trend": groupes_trend,
        "revenue_trend": revenue_trend,
        "payment_trend": payment_trend,

        "derniers_paiements": derniers_paiements,
        "nouvelles_inscriptions": nouvelles_inscriptions,
        "impayes_recents": impayes_recents,

        "repartition_eleves": repartition_eleves,
        "presences": presences,

        "objectif_mensuel": objectif_mensuel,
        "objectif_atteint": objectif_atteint,


        # ✅ Chart (Pilotage)
        "chart_labels": chart_labels_json,
        "chart_paiements": chart_paiements_json,
        "chart_inscriptions": chart_inscriptions_json,

        # ✅ pour afficher “Février” sur le dashboard
        "mois_courant": idx_courant,
        "mois_courant_nom": mois_courant_nom,
    }



def _build_staff_dashboard_context():
    today = timezone.now().date()

    # périodes mois courant
    start_this_month = date(today.year, today.month, 1)
    start_next_month = _add_months(start_this_month, 1)

    annee_active_obj = AnneeScolaire.objects.filter(is_active=True).first()
    annee_active = annee_active_obj.nom if annee_active_obj else "—"

    # ✅ SAFE si pas d'année active
    if not annee_active_obj:
        return {
            "today": today,
            "current_date": today,
            "annee_active": annee_active,
            "nb_eleves": 0,
            "nb_groupes": 0,
            "total_paye": Decimal("0.00"),
            "presences": {
                "presents": 0, "absents": 0, "retards": 0, "total": 0,
                "taux_presence": 0, "taux_absence": 0, "taux_retard": 0,
            },
        }

    inscs_active = Inscription.objects.filter(annee_id=annee_active_obj.id)
    nb_eleves = inscs_active.values("eleve_id").distinct().count()
    nb_groupes = inscs_active.values("groupe_id").distinct().count()

    # ✅ Encaissement mensuel (comme admin) => Paiement + TransactionFinance
    pay_mois_old = (
        Paiement.objects
        .filter(
            inscription__annee_id=annee_active_obj.id,
            date_paiement__gte=start_this_month,
            date_paiement__lt=start_next_month,
        )
        .aggregate(s=Coalesce(Sum("montant"), ZERO_MONEY))["s"]
        or Decimal("0.00")
    )

    pay_mois_new = (
        TransactionFinance.objects
        .filter(
            inscription__annee_id=annee_active_obj.id,
            date_transaction__gte=start_this_month,
            date_transaction__lt=start_next_month,
        )
        .aggregate(s=Coalesce(Sum("montant_total"), ZERO_MONEY))["s"]
        or Decimal("0.00")
    )

    total_paye = (pay_mois_old or Decimal("0.00")) + (pay_mois_new or Decimal("0.00"))

    # Présences
    absents = Absence.objects.filter(date=today, type="ABS").values("eleve_id").distinct().count()
    retards = Absence.objects.filter(date=today, type="RET").values("eleve_id").distinct().count()
    total = nb_eleves
    presents = max(total - absents, 0)

    presences = {
        "presents": presents,
        "absents": absents,
        "retards": retards,
        "total": total,
        "taux_presence": int((presents / total) * 100) if total else 0,
        "taux_absence": int((absents / total) * 100) if total else 0,
        "taux_retard": int((retards / total) * 100) if total else 0,
    }

    return {
        "today": today,
        "current_date": today,
        "annee_active": annee_active,

        "nb_eleves": nb_eleves,
        "nb_groupes": nb_groupes,
        "total_paye": total_paye,

        "presences": presences,
    }

# ─────────────────────────────────────────
# Route "dashboard" -> redirige selon role
# ─────────────────────────────────────────
@login_required
def dashboard(request):
    user = request.user

    if _is_superadmin(user):
        return redirect("core:dashboard_superadmin")

    if _is_admin(user):
        return redirect("core:dashboard_admin")

    return redirect("core:dashboard_staff")


@login_required
def dashboard_staff(request):
    ctx = _build_staff_dashboard_context()
    ctx["dash_kind"] = "staff"
    ctx["dash_title"] = "Dashboard Direction"
    return render(request, "admin/Dashboard/staff.html", ctx)


@login_required
def dashboard_admin(request):
    ctx = _build_dashboard_context()
    ctx["dash_kind"] = "admin"
    ctx["dash_title"] = "Tableau de bord"
    return render(request, "admin/Dashboard/admin.html", ctx)


@login_required
def dashboard_superadmin(request):
    if not _is_superadmin(request.user):
        return redirect("core:dashboard_admin")

    ctx = _build_dashboard_context()
    ctx["dash_kind"] = "superadmin"
    ctx["dash_title"] = "SuperAdmin Center"

    User = get_user_model()
    ctx["nb_users"] = User.objects.count()
    ctx["nb_staff"] = User.objects.filter(is_staff=True).count()
    ctx["nb_superusers"] = User.objects.filter(is_superuser=True).count()

    return render(request, "admin/Dashboard/superadmin.html", ctx)



def mois_index_courant(annee: AnneeScolaire, today: date_cls) -> int:
    """
    Retourne l’index du mois scolaire AZ (1..10)
    Septembre = 1, Octobre = 2, ..., Juin = 10
    """
    if not annee or not annee.date_debut:
        return 1

    mapping = {
        9: 1,   # Septembre
        10: 2,  # Octobre
        11: 3,  # Novembre
        12: 4,  # Décembre
        1: 5,   # Janvier
        2: 6,   # Février
        3: 7,   # Mars
        4: 8,   # Avril
        5: 9,   # Mai
        6: 10,  # Juin
    }

    mois_reel = today.month

    # hors année scolaire (été)
    if mois_reel not in mapping:
        return 10  # on considère fin d’année

    return mapping[mois_reel]



@login_required
@group_required("SUPER_ADMIN", "ADMIN")
def annee_list(request):
    annees = AnneeScolaire.objects.all()
    return render(request, "admin/annees/list.html", {"annees": annees})


from django.db import transaction
from django.shortcuts import redirect, render

@login_required
@group_required("SUPER_ADMIN", "ADMIN")
def annee_create(request):
    if request.method == "POST":
        form = AnneeScolaireForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    annee = form.save()
                messages.success(request, "✅ Année scolaire ajoutée + semestres créés (S1/S2).")
                return redirect("core:annee_list")

            except Exception as e:
                messages.error(request, f"⚠️ Erreur lors de la création des semestres: {e}")
        else:
            messages.error(request, "⚠️ Formulaire invalide. Vérifie les champs.")
    else:
        form = AnneeScolaireForm()

    return render(request, "admin/annees/form.html", {"form": form, "mode": "create"})

@login_required
@group_required("SUPER_ADMIN", "ADMIN")
def annee_update(request, pk):
    annee = get_object_or_404(AnneeScolaire, pk=pk)

    if request.method == "POST":
        form = AnneeScolaireForm(request.POST, instance=annee)
        if form.is_valid():
            try:
                with transaction.atomic():
                    annee = form.save()
                messages.success(request, "✅ Année scolaire mise à jour + semestres vérifiés (S1/S2).")
                return redirect("core:annee_list")

            except Exception as e:
                messages.error(request, f"⚠️ Erreur lors de la vérification des semestres: {e}")
    else:
        form = AnneeScolaireForm(instance=annee)

    return render(request, "admin/annees/form.html", {
        "form": form,
        "mode": "update",
        "annee": annee
    })


@login_required
@group_required("SUPER_ADMIN", "ADMIN")
def annee_delete(request, pk):
    annee = get_object_or_404(AnneeScolaire, pk=pk)

    if request.method == "POST":
        try:
            annee.delete()
            messages.success(request, "🗑️ Année supprimée avec succès.")
            return redirect("core:annee_list")

        except ProtectedError:
            messages.error(
                request,
                "❌ Suppression impossible : cette année contient des données "
                "(groupes, élèves, paiements, séances…). "
                "Désactive-la plutôt."
            )
            return redirect("core:annee_list")

    return render(request, "admin/annees/delete.html", {
        "annee": annee,
    })


@login_required
@group_required("SUPER_ADMIN", "ADMIN")
def annee_activer(request, pk):
    annee = get_object_or_404(AnneeScolaire, pk=pk)
    AnneeScolaire.objects.update(is_active=False)
    annee.is_active = True
    annee.save()
    messages.success(request, f"✅ Année active: {annee.nom}")
    return redirect("core:annee_list")

# ============================
# B1 — Degrés
# ============================


from django.shortcuts import render
from django.db.models import Min, Max
from .models import AnneeScolaire, Degre, FraisNiveau
from django.db.models import Min, Max, Count  # ✅ ajoute Count

@login_required
@group_required("SUPER_ADMIN", "ADMIN")
def degre_list(request):
    annee_active = AnneeScolaire.objects.filter(is_active=True).first()
    degres = Degre.objects.all().order_by("ordre", "nom")

    resume_by_degre_id = {}
    cap_by_degre_id = {}

    if annee_active:
        # ✅ résumé prix existant
        qs = (
            FraisNiveau.objects
            .filter(annee=annee_active)
            .values("niveau__degre_id")
            .annotate(
                min_ins=Min("frais_inscription"),
                max_ins=Max("frais_inscription"),
            )
        )
        resume_by_degre_id = {
            row["niveau__degre_id"]: {
                "min": row["min_ins"] or Decimal("0.00"),
                "max": row["max_ins"] or Decimal("0.00"),
            }
            for row in qs
        }

        # ✅ capacité (= nb élèves) par degré
        cap_qs = (
            Inscription.objects
            .filter(annee=annee_active)
            .values("groupe__niveau__degre_id")
            .annotate(c=Count("id"))
        )
        cap_by_degre_id = {row["groupe__niveau__degre_id"]: row["c"] for row in cap_qs}

    return render(request, "admin/degres/list.html", {
        "degres": degres,
        "annee_active": annee_active,
        "resume_by_degre_id": resume_by_degre_id,
        "cap_by_degre_id": cap_by_degre_id,  # ✅ NEW
    })


@login_required
@group_required("SUPER_ADMIN", "ADMIN")
def degre_create(request):
    if request.method == "POST":
        form = DegreForm(request.POST)
        if form.is_valid():
            nom = form.cleaned_data["nom"].strip()
            # code auto (propre, sans accents -> simple)
            code = nom.upper().replace(" ", "_").replace("É", "E").replace("È", "E").replace("Ê", "E").replace("Ë", "E") \
                              .replace("À", "A").replace("Â", "A").replace("Ä", "A") \
                              .replace("Ç", "C") \
                              .replace("Î", "I").replace("Ï", "I") \
                              .replace("Ô", "O").replace("Ö", "O") \
                              .replace("Ù", "U").replace("Û", "U").replace("Ü", "U")

            Degre.objects.create(code=code, nom=nom, ordre=form.cleaned_data["ordre"])
            messages.success(request, "✅ Degré ajouté.")
            return redirect("core:degre_list")
    else:
        form = DegreForm()

    return render(request, "admin/degres/form.html", {"form": form, "mode": "create"})


@login_required
@group_required("SUPER_ADMIN", "ADMIN")
def degre_update(request, pk):
    degre = get_object_or_404(Degre, pk=pk)
    if request.method == "POST":
        form = DegreForm(request.POST, instance=degre)
        if form.is_valid():
            form.save()
            messages.success(request, "✅ Degré mis à jour.")
            return redirect("core:degre_list")
    else:
        form = DegreForm(instance=degre)

    return render(request, "admin/degres/form.html", {"form": form, "mode": "update", "degre": degre})


@login_required
@group_required("SUPER_ADMIN", "ADMIN")
def degre_delete(request, pk):
    degre = get_object_or_404(Degre, pk=pk)

    if request.method == "POST":
        try:
            degre.delete()
            messages.success(request, "🗑️ Degré supprimé.")
        except ProtectedError:
            messages.error(
                request,
                "❌ Suppression impossible : ce degré contient des niveaux (ex: CE1, CM1...). "
                "Supprime d’abord les niveaux liés."
            )
        return redirect("core:degre_list")

    return render(request, "admin/degres/delete.html", {"degre": degre})
# ============================
# B2 — Niveaux
# ============================


@login_required
def niveau_prix_edit(request, niveau_id):
    niveau = get_object_or_404(Niveau, id=niveau_id)
    annee_active = AnneeScolaire.objects.filter(is_active=True).first()

    if not annee_active:
        messages.error(request, "Aucune année scolaire active. Active une année avant de définir les prix.")
        return redirect("core:niveau_list")

    frais_niveau, _ = FraisNiveau.objects.get_or_create(
        annee=annee_active,
        niveau=niveau,
        defaults={
            "frais_inscription": Decimal("0.00"),
            "frais_scolarite_mensuel": Decimal("0.00"),
        },
    )

    if request.method == "POST":
        insc_str = (request.POST.get("frais_inscription") or "").replace(",", ".").strip()
        mens_str = (request.POST.get("frais_scolarite_mensuel") or "").replace(",", ".").strip()

        def parse_money(v: str) -> Decimal:
            if v == "":
                return Decimal("0.00")
            d = Decimal(v)
            if d < 0:
                raise ValueError("neg")
            return d

        try:
            frais_inscription = parse_money(insc_str)
            frais_mensuel = parse_money(mens_str)
        except Exception:
            messages.error(request, "Montant invalide. Exemple: 1500 ou 1500.00")
            return render(request, "admin/niveaux/prix_edit.html", {
                "niveau": niveau,
                "annee_active": annee_active,
                "frais_niveau": frais_niveau,
            })

        frais_niveau.frais_inscription = frais_inscription
        frais_niveau.frais_scolarite_mensuel = frais_mensuel
        frais_niveau.save(update_fields=["frais_inscription", "frais_scolarite_mensuel"])

        messages.success(
            request,
            f"✅ Prix enregistrés: Inscription={frais_inscription} MAD | Mensuel={frais_mensuel} MAD ({niveau.nom})"
        )
        return redirect("core:niveau_list")

    return render(request, "admin/niveaux/prix_edit.html", {
        "niveau": niveau,
        "annee_active": annee_active,
        "frais_niveau": frais_niveau,
    })

from accounts.decorators import group_required

# ... tes imports existants ...

@login_required
@group_required("SUPER_ADMIN", "ADMIN")
def niveau_list(request):
    annee_active = AnneeScolaire.objects.filter(is_active=True).first()

    annee_id = (request.GET.get("annee") or "").strip()
    if not annee_id and annee_active:
        annee_id = str(annee_active.id)

    degre_selected = (request.GET.get("degre") or "").strip()

    degres = Degre.objects.all().order_by("ordre", "nom")
    annees = AnneeScolaire.objects.all().order_by("-id")

    niveaux_qs = Niveau.objects.select_related("degre").all()
    if degre_selected:
        niveaux_qs = niveaux_qs.filter(degre_id=degre_selected)
    niveaux_qs = niveaux_qs.order_by("degre__ordre", "ordre", "nom")

    # =========================
    # ✅ MAP FRAIS par niveau
    # =========================
    frais_map = {}
    if annee_id:
        frais_qs = FraisNiveau.objects.filter(annee_id=annee_id).select_related("niveau")
        frais_map = {f.niveau_id: f for f in frais_qs}

    # =========================
    # ✅ MAP CAPACITÉ (= nb élèves) par niveau
    # =========================
    cap_map = {}
    if annee_id:
        cap_qs = (
            Inscription.objects
            .filter(annee_id=annee_id)
            .values("groupe__niveau_id")
            .annotate(c=Count("id"))
        )
        cap_map = {row["groupe__niveau_id"]: row["c"] for row in cap_qs}

    rows = []
    for n in niveaux_qs:
        fn = frais_map.get(n.id)
        rows.append({
            "niveau": n,
            "degre": n.degre,
            "inscription": (fn.frais_inscription if fn else Decimal("0.00")),
            "mensuel": (fn.frais_scolarite_mensuel if fn else Decimal("0.00")),
            "capacite": cap_map.get(n.id, 0),  # ✅ nb élèves
        })

    return render(request, "admin/niveaux/list.html", {
        "annee_active": annee_active,
        "annees": annees,
        "annee_selected": annee_id,
        "degres": degres,
        "degre_selected": degre_selected,
        "rows": rows,
    })


@login_required
@group_required("SUPER_ADMIN", "ADMIN")
def niveau_create(request):
    if request.method == "POST":
        form = NiveauForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "✅ Niveau ajouté.")
            return redirect("core:niveau_list")
    else:
        form = NiveauForm()

    return render(request, "admin/niveaux/form.html", {"form": form, "mode": "create"})


@login_required
@group_required("SUPER_ADMIN", "ADMIN")
def niveau_update(request, pk):
    niveau = get_object_or_404(Niveau, pk=pk)
    if request.method == "POST":
        form = NiveauForm(request.POST, instance=niveau)
        if form.is_valid():
            form.save()
            messages.success(request, "✅ Niveau mis à jour.")
            return redirect("core:niveau_list")
    else:
        form = NiveauForm(instance=niveau)

    return render(request, "admin/niveaux/form.html", {"form": form, "mode": "update", "niveau": niveau})


@login_required
@group_required("SUPER_ADMIN", "ADMIN")
def niveau_delete(request, pk):
    niveau = get_object_or_404(Niveau, pk=pk)

    if request.method == "POST":
        try:
            niveau.delete()
            messages.success(request, "🗑️ Niveau supprimé.")
        except ProtectedError:
            messages.error(
                request,
                "❌ Suppression impossible : ce niveau est utilisé (groupes, frais, inscriptions...). "
                "Supprime d’abord les éléments liés ou archive-le."
            )
        return redirect("core:niveau_list")

    return render(request, "admin/niveaux/delete.html", {"niveau": niveau})

# ============================
# B3 — Groupes
# ============================

@login_required
@group_required("SUPER_ADMIN", "ADMIN", "SECRETAIRE")
def groupe_list(request):
    q = request.GET.get("q", "").strip()
    niveau_id = request.GET.get("niveau", "")
    annee_id = request.GET.get("annee", "")

    annee_active = AnneeScolaire.objects.filter(is_active=True).first()

    groupes = (
        Groupe.objects
        .select_related("annee", "niveau", "niveau__degre")
        .annotate(
            nb_eleves=Count("inscriptions", distinct=True)
            # ✅ Si tu veux compter seulement les VALIDEE, utilise plutôt ceci :
            # nb_eleves=Count("inscriptions", filter=Q(inscriptions__statut="VALIDEE"), distinct=True)
        )
    )

    # ✅ par défaut : année active
    if not annee_id and annee_active:
        annee_id = str(annee_active.id)

    if annee_id:
        groupes = groupes.filter(annee_id=annee_id)

    if niveau_id:
        groupes = groupes.filter(niveau_id=niveau_id)

    if q:
        groupes = groupes.filter(
            Q(nom__icontains=q) |
            Q(niveau__nom__icontains=q) |
            Q(niveau__degre__nom__icontains=q)
        )

    niveaux = Niveau.objects.select_related("degre").all()
    annees = AnneeScolaire.objects.all()

    return render(
        request,
        "admin/groupes/list.html",
        {
            "groupes": groupes,
            "q": q,
            "niveaux": niveaux,
            "annees": annees,
            "niveau_selected": niveau_id,
            "annee_selected": annee_id,
        },
    )


@login_required
@group_required("SUPER_ADMIN", "ADMIN", "SECRETAIRE")
def groupe_create(request):
    if request.method == "POST":
        form = GroupeForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "✅ Groupe ajouté.")
            return redirect("core:groupe_list")
    else:
        form = GroupeForm()
    return render(request, "admin/groupes/form.html", {"form": form, "mode": "create"})


@login_required
@group_required("SUPER_ADMIN", "ADMIN")
def groupe_update(request, pk):
    groupe = get_object_or_404(Groupe, pk=pk)
    if request.method == "POST":
        form = GroupeForm(request.POST, instance=groupe)
        if form.is_valid():
            form.save()
            messages.success(request, "✅ Groupe mis à jour.")
            return redirect("core:groupe_list")
    else:
        form = GroupeForm(instance=groupe)
    return render(request, "admin/groupes/form.html", {"form": form, "mode": "update", "groupe": groupe})




@login_required
@group_required("SUPER_ADMIN", "ADMIN")
def groupe_delete(request, pk):
    g = get_object_or_404(Groupe, pk=pk)

    if request.method == "POST":
        try:
            g.delete()
            messages.success(request, "🗑️ Groupe supprimé.")
        except ProtectedError:
            messages.error(
                request,
                "❌ Suppression impossible : ce groupe est utilisé (inscriptions, échéances, séances, cahier, PDF...). "
                "Supprime d’abord les éléments liés ou archive le groupe."
            )
        return redirect("core:groupe_list")

    return render(request, "admin/groupes/delete.html", {"groupe": g})

# ============================
# C1 — Élèves
# ============================

from django.db.models import Q, Exists, OuterRef

@login_required
@group_required("SUPER_ADMIN", "ADMIN", "SCOLARITE", "SECRETAIRE")
def eleve_list(request):
    q = request.GET.get("q", "").strip()
    statut = request.GET.get("statut", "")

    # ✅ nouveau filtre inscription
    # valeurs possibles: "", "inscrits", "non_inscrits"
    insc = request.GET.get("insc", "").strip()

    # ✅ filtres
    annee_active = AnneeScolaire.objects.filter(is_active=True).first()
    annee_id = request.GET.get("annee", "")
    niveau_id = request.GET.get("niveau", "")
    groupe_id = request.GET.get("groupe", "")
    periode_id = request.GET.get("periode", "")

    eleves = Eleve.objects.all()

    # ✅ statut actif/inactif (élève)
    if statut == "actifs":
        eleves = eleves.filter(is_active=True)
    elif statut == "inactifs":
        eleves = eleves.filter(is_active=False)

    # ✅ recherche
    if q:
        eleves = eleves.filter(
            Q(matricule__icontains=q) |
            Q(nom__icontains=q) |
            Q(prenom__icontains=q) |
            Q(telephone__icontains=q)
        )

    # ✅ Année par défaut = année active
    if not annee_id and annee_active:
        annee_id = str(annee_active.id)

    # ===============================
    # ✅ LOGIQUE "INSCRIPTION" (IMPORTANT)
    # ===============================
    if annee_id:
        # Sous-requêtes existence
        insc_year = Inscription.objects.filter(eleve_id=OuterRef("pk"), annee_id=annee_id)
        insc_year_validee = Inscription.objects.filter(
            eleve_id=OuterRef("pk"),
            annee_id=annee_id,
            statut="VALIDEE",
        )
        insc_year_en_cours = Inscription.objects.filter(
            eleve_id=OuterRef("pk"),
            annee_id=annee_id,
            statut="EN_COURS",
        )

        eleves = eleves.annotate(
            has_insc_year=Exists(insc_year),
            has_insc_validee=Exists(insc_year_validee),
            has_insc_en_cours=Exists(insc_year_en_cours),
        )

        # 🔹 cas 1: afficher seulement "inscrits" (inscription validée)
        if insc == "inscrits":
            eleves = eleves.filter(has_insc_validee=True)

        # 🔹 cas 2: afficher "non inscrits" = (aucune inscription) OU (inscription EN_COURS)
        elif insc == "non_inscrits":
            eleves = eleves.filter(
                Q(has_insc_year=False) | Q(has_insc_en_cours=True)
            )

        # 🔹 cas défaut (insc == "") : comportement normal = élèves ayant une inscription sur l'année
        else:
            eleves = eleves.filter(has_insc_year=True)

        # ✅ Filtrage niveau/groupe/période :
        # - si insc == non_inscrits => ces filtres ne peuvent s'appliquer qu'aux élèves qui ont une inscription (EN_COURS)
        # - donc on les applique via la relation inscriptions (ça exclura ceux qui n'ont aucune inscription, ce qui est logique)
        if niveau_id:
            eleves = eleves.filter(inscriptions__annee_id=annee_id, inscriptions__groupe__niveau_id=niveau_id)

        if groupe_id:
            eleves = eleves.filter(inscriptions__annee_id=annee_id, inscriptions__groupe_id=groupe_id)

        if periode_id:
            eleves = eleves.filter(inscriptions__annee_id=annee_id, inscriptions__periode_id=periode_id)

    eleves = eleves.distinct()

    # ✅ periodes pour dropdown
    periodes = Periode.objects.all()
    if annee_id:
        periodes = periodes.filter(annee_id=annee_id)

    # ✅ dropdowns
    annees = AnneeScolaire.objects.all()

    niveaux = Niveau.objects.all()
    if annee_id:
        niveaux = niveaux.filter(groupes__annee_id=annee_id).distinct()

    groupes = Groupe.objects.select_related("niveau", "annee").all()
    if annee_id:
        groupes = groupes.filter(annee_id=annee_id)
    if niveau_id:
        groupes = groupes.filter(niveau_id=niveau_id)

    return render(request, "admin/eleves/list.html", {
        "eleves": eleves,
        "q": q,
        "statut": statut,

        # ✅ nouveau
        "insc": insc,

        # ✅ context filtres
        "annee_active": annee_active,
        "annees": annees,
        "annee_selected": annee_id,
        "niveaux": niveaux,
        "niveau_selected": niveau_id,
        "groupes": groupes,
        "groupe_selected": groupe_id,
        "periodes": periodes,
        "periode_selected": periode_id,
    })


@login_required
def eleve_detail(request, pk):
    eleve = get_object_or_404(Eleve, pk=pk)

    liens_parents = eleve.liens_parents.select_related("parent").all()

    inscriptions = (
        Inscription.objects
        .filter(eleve=eleve)
        .select_related("annee", "groupe", "groupe__niveau", "groupe__niveau__degre", "periode")
        .prefetch_related( "paiements")
        .order_by("-annee__date_debut", "-id")
    )

    inscription_active = inscriptions.first()

    # ✅ Résumé "classe actuelle" (Degré / Niveau / Groupe)
    classe_active = None
    if inscription_active and inscription_active.groupe_id:
        g = inscription_active.groupe
        n = g.niveau
        d = n.degre
        classe_active = {
            "annee": inscription_active.annee,
            "periode": inscription_active.periode,
            "degre": d,
            "niveau": n,
            "groupe": g,
        }

    # =========================
    # FINANCE (inscription active)
    # =========================
    finance = None
    if inscription_active:
        echeances = (
                EcheanceMensuelle.objects
                .filter(eleve=eleve, annee=inscription_active.annee)
                .order_by("date_echeance", "mois_index")
            )

        total_mensuel_du = sum((e.montant_du or Decimal("0.00")) for e in echeances)
        total_mensuel_paye = sum((e.montant_paye or Decimal("0.00")) for e in echeances)
        total_mensuel_reste = total_mensuel_du - total_mensuel_paye

        total_insc_du = inscription_active.frais_inscription_du or Decimal("0.00")
        total_insc_paye = inscription_active.frais_inscription_paye or Decimal("0.00")
        total_insc_reste = total_insc_du - total_insc_paye

        paiements = (
            Paiement.objects
            .filter(inscription=inscription_active)
            .select_related("echeance")
            .order_by("-date_paiement", "-id")
        )

        finance = {
            "inscription": inscription_active,
            "echeances": echeances,
            "paiements": paiements,
            "kpi": {
                "insc_du": total_insc_du,
                "insc_paye": total_insc_paye,
                "insc_reste": total_insc_reste,
                "mensuel_du": total_mensuel_du,
                "mensuel_paye": total_mensuel_paye,
                "mensuel_reste": total_mensuel_reste,
                "global_reste": total_insc_reste + total_mensuel_reste,
            }
        }

    return render(request, "admin/eleves/detail.html", {
        "eleve": eleve,
        "liens_parents": liens_parents,
        "inscriptions": inscriptions,
        "inscription_active": inscription_active,
        "classe_active": classe_active,
        "finance": finance,
    })


@login_required
@group_required("SUPER_ADMIN", "ADMIN", "SCOLARITE", "SECRETAIRE")
def eleve_create(request):
    if request.method == "POST":
        form = EleveForm(request.POST, request.FILES)
        if form.is_valid():
            eleve = form.save()  # ✅ matricule généré via save()

        try:
            # ✅ 1) Créer le compte ÉLÈVE (username = matricule élève)
            user, pwd, created = get_or_create_user_with_group(eleve.matricule, "ELEVE")

            # ✅ 2) Lier le user au profil élève
            if getattr(eleve, "user_id", None) != user.id:
                eleve.user = user
                eleve.save(update_fields=["user"])

            # ✅ IMPORTANT : ✅ NE PAS créer de parent automatiquement ici.
            # (Le lien parent <-> élève sera fait uniquement via InscriptionFullForm
            #  ou une page dédiée "Affecter parent".)

            if created:
                messages.success(
                    request,
                    f"✅ Élève ajouté: {eleve.matricule} | Compte ÉLÈVE créé | MDP temporaire: {pwd}"
                )
            else:
                messages.info(request, f"ℹ️ Compte ÉLÈVE existe déjà pour {eleve.matricule}.")

        except Exception as e:
            messages.warning(request, f"⚠️ Élève créé mais compte ÉLÈVE non créé: {e}")

            return redirect("core:eleve_detail", pk=eleve.pk)
    else:
        form = EleveForm()

    return render(request, "admin/eleves/form.html", {"form": form, "mode": "create"})

@login_required
@group_required("SUPER_ADMIN", "ADMIN", "SCOLARITE", "SECRETAIRE")
def eleve_update(request, pk):
    eleve = get_object_or_404(Eleve, pk=pk)

    if request.method == "POST":
        # ✅ IMPORTANT : request.FILES pour update photo
        form = EleveForm(request.POST, request.FILES, instance=eleve)
        if form.is_valid():
            form.save()
            messages.success(request, "✅ Élève mis à jour.")
            return redirect("core:eleve_detail", pk=eleve.pk)
    else:
        form = EleveForm(instance=eleve)

    return render(request, "admin/eleves/form.html", {"form": form, "mode": "update", "eleve": eleve})

from core.models import Eleve, Note, RelanceMensuelle  # ajuste si besoin


def _eleve_hard_delete(eleve: Eleve) -> None:
    """
    Supprime TOUT ce qui bloque (paiements, recouvrement, echeances, inscriptions, etc.)
    ⚠️ À utiliser seulement si tu veux une suppression définitive.
    """
    # 1) Liens directs à l'élève
    eleve.liens_parents.all().delete()      # ParentEleve (FK eleve CASCADE chez toi, mais safe)
    eleve.absences.all().delete()           # Absence (PROTECT -> on delete avant)
    Note.objects.filter(eleve=eleve).delete()

    # 2) Inscriptions + dépendances
    for insc in eleve.inscriptions.all():
        # relances mensuelles liées aux échéances de l'inscription (optionnel)
        RelanceMensuelle.objects.filter(echeance__inscription=insc).delete()

        # recouvrement + relances (si existe)
        if hasattr(insc, "recouvrement"):
            insc.recouvrement.relances.all().delete()
            insc.recouvrement.delete()

        # paiements (PROTECT -> delete avant inscription)
        insc.paiements.all().delete()

        # échéances (et paiements.echeance PROTECT -> ok car paiements déjà supprimés)
        insc.echeances.all().delete()

        # delete inscription
        insc.delete()

    # 3) Delete final
    eleve.delete()


@login_required
@group_required("SUPER_ADMIN", "ADMIN", "SCOLARITE")
def eleve_delete(request, pk):
    eleve = get_object_or_404(Eleve, pk=pk)

    if request.method == "POST":
        try:
            with transaction.atomic():
                # 1) récupérer les parents liés AVANT suppression
                parents_ids = list(
                    eleve.liens_parents.values_list("parent_id", flat=True).distinct()
                )

                matricule = eleve.matricule

                # 2) supprimer l'élève
                eleve.delete()

                # 3) nettoyer les parents devenus orphelins (plus aucun lien ParentEleve)
                User = get_user_model()

                # on recharge les parents concernés avec leur user en 1 requête
                parents = Parent.objects.filter(id__in=parents_ids).select_related("user")

                for parent in parents:
                    # si parent est encore lié à au moins 1 élève -> ne rien toucher
                    if parent.liens.exists():
                        continue

                    user = parent.user

                    # supprimer la fiche Parent orpheline
                    parent.delete()

                    # supprimer/désactiver le user associé (si présent)
                    if user:
                        # sécurité : si user utilisé ailleurs (ex: enseignant), ne pas supprimer
                        if Enseignant.objects.filter(user=user).exists():
                            user.is_active = False
                            user.save(update_fields=["is_active"])
                        else:
                            user.delete()

            messages.success(request, f"Élève {matricule} supprimé (parents orphelins nettoyés).")
            return redirect("core:eleve_list")

        except ProtectedError:
            # si protégé (inscriptions / paiements...) => archivage
            if eleve.is_active:
                eleve.is_active = False
                eleve.save(update_fields=["is_active"])

            messages.error(
                request,
                "Impossible de supprimer : cet élève a des inscriptions. Tu peux l’archiver à la place."
            )
            return redirect("core:eleve_detail", pk=eleve.pk)

    return render(request, "admin/eleves/delete.html", {"eleve": eleve})

# ============================
# C3 — Inscriptions
# ============================

from .forms import InscriptionFullForm

@login_required
@group_required("SUPER_ADMIN", "ADMIN", "SCOLARITE", "SECRETAIRE")
def inscription_full_create(request):
    """
    1 seul écran:
    - Eleve + Parent + Inscription
    - Lien ParentEleve
    - Compte ELEVE créé automatiquement
    - Compte parent : optionnel (pas auto)
    - Photo élève supportée (request.FILES)
    """
    if request.method == "POST":
        # ✅ IMPORTANT: toujours passer request.FILES
        form = InscriptionFullForm(request.POST, request.FILES)

        if form.is_valid():
            with transaction.atomic():
                eleve, parent, insc = form.save()

                # ✅ Créer COMPTE ELEVE (username = matricule élève)
                try:
                    user, pwd, created = get_or_create_user_with_group(eleve.matricule, "ELEVE")

                    if eleve.user_id != user.id:
                        eleve.user = user
                        eleve.save(update_fields=["user"])

                    if created:
                        messages.success(
                            request,
                            f"✅ Inscription créée: {eleve.matricule} — Groupe: {insc.groupe.nom} | "
                            f"Compte ÉLÈVE créé | MDP: {pwd}"
                        )
                    else:
                        messages.success(
                            request,
                            f"✅ Inscription créée: {eleve.matricule} — Groupe: {insc.groupe.nom} | "
                            f"Compte ÉLÈVE déjà existant"
                        )

                except Exception as e:
                    messages.warning(
                        request,
                        f"✅ Inscription créée: {eleve.matricule} — Groupe: {insc.groupe.nom} | "
                        f"⚠️ Compte ÉLÈVE non créé: {e}"
                    )

            return redirect("core:eleve_detail", pk=eleve.pk)

    else:
        active = AnneeScolaire.objects.filter(is_active=True).first()
        form = InscriptionFullForm(initial={"annee": active} if active else None)

    return render(request, "admin/inscriptions/full_form.html", {"form": form})

@login_required
@group_required("SUPER_ADMIN", "ADMIN", "SCOLARITE", "SECRETAIRE")
def inscription_create(request):
    if request.method == "POST":
        form = InscriptionForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "✅ Inscription créée.")
            return redirect("core:inscription_list")
    else:
        form = InscriptionForm()
    return render(request, "admin/inscriptions/form.html", {"form": form, "mode": "create"})


from datetime import datetime

@login_required
@group_required("SUPER_ADMIN", "ADMIN", "SCOLARITE", "SECRETAIRE")
def inscription_list(request):
    annee_active = AnneeScolaire.objects.filter(is_active=True).first()

    # ✅ nouveaux filtres
    q = request.GET.get("q", "").strip()
    statut = request.GET.get("statut", "").strip()

    annee_id = request.GET.get("annee", "")
    niveau_id = request.GET.get("niveau", "")
    groupe_id = request.GET.get("groupe", "")
    periode_id = request.GET.get("periode", "")
    date_str = request.GET.get("date", "").strip()

    inscriptions = Inscription.objects.select_related(
        "eleve", "annee", "groupe", "groupe__niveau", "groupe__niveau__degre", "periode"
    )

    # ✅ par défaut : année active
    if not annee_id and annee_active:
        annee_id = str(annee_active.id)

    if annee_id:
        inscriptions = inscriptions.filter(annee_id=annee_id)
    if niveau_id:
        inscriptions = inscriptions.filter(groupe__niveau_id=niveau_id)
    if groupe_id:
        inscriptions = inscriptions.filter(groupe_id=groupe_id)
    if periode_id:
        inscriptions = inscriptions.filter(periode_id=periode_id)

    # ✅ date inscription
    if date_str:
        try:
            d = datetime.strptime(date_str, "%Y-%m-%d").date()
            inscriptions = inscriptions.filter(date_inscription=d)
        except ValueError:
            inscriptions = inscriptions.none()

    # ✅ filtre statut
    if statut in ("EN_COURS", "VALIDEE"):
        inscriptions = inscriptions.filter(statut=statut)

    # ✅ recherche (élève)
    if q:
        inscriptions = inscriptions.filter(
            Q(eleve__matricule__icontains=q) |
            Q(eleve__nom__icontains=q) |
            Q(eleve__prenom__icontains=q) |
            Q(eleve__telephone__icontains=q) |
            Q(groupe__nom__icontains=q) |
            Q(groupe__niveau__nom__icontains=q) |
            Q(groupe__niveau__degre__nom__icontains=q)
        )

    # ✅ dropdowns
    annees = AnneeScolaire.objects.all()

    niveaux = Niveau.objects.all()
    if annee_id:
        niveaux = niveaux.filter(groupes__annee_id=annee_id).distinct()

    groupes = Groupe.objects.all()
    if annee_id:
        groupes = groupes.filter(annee_id=annee_id)
    if niveau_id:
        groupes = groupes.filter(niveau_id=niveau_id)

    periodes = Periode.objects.all()
    if annee_id:
        periodes = periodes.filter(annee_id=annee_id)

    return render(request, "admin/inscriptions/list.html", {
        "inscriptions": inscriptions,
        "annee_active": annee_active,

        "annees": annees,
        "annee_selected": annee_id,

        "niveaux": niveaux,
        "niveau_selected": niveau_id,

        "groupes": groupes,
        "groupe_selected": groupe_id,

        "periodes": periodes,
        "periode_selected": periode_id,

        "date_selected": date_str,

        # ✅ NEW
        "q": q,
        "statut_selected": statut,
    })



@login_required
@group_required("SUPER_ADMIN", "ADMIN", "SCOLARITE", "SECRETAIRE")
def inscription_create_for_eleve(request, eleve_id):
    eleve = get_object_or_404(Eleve, pk=eleve_id)

    if request.method == "POST":
        form = InscriptionForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "✅ Inscription créée pour cet élève.")
            return redirect("core:eleve_detail", pk=eleve.id)
    else:
        form = InscriptionForm(initial={"eleve": eleve})

    return render(
        request,
        "admin/inscriptions/form.html",
        {"form": form, "mode": "create", "eleve": eleve},
    )


@login_required
@group_required("SUPER_ADMIN", "ADMIN", "SCOLARITE", "SECRETAIRE")
def inscription_update(request, pk):
    insc = get_object_or_404(Inscription, pk=pk)
    if request.method == "POST":
        form = InscriptionForm(request.POST, instance=insc)
        if form.is_valid():
            form.save()
            messages.success(request, "✅ Inscription mise à jour.")
            return redirect("core:inscription_list")
    else:
        form = InscriptionForm(instance=insc)

    return render(request, "admin/inscriptions/form.html", {"form": form, "mode": "update", "insc": insc})


@login_required
@group_required("SUPER_ADMIN", "ADMIN")
def inscription_delete(request, pk):
    insc = get_object_or_404(Inscription, pk=pk)
    if request.method == "POST":
        insc.delete()
        messages.success(request, "🗑️ Inscription supprimée.")
        return redirect("core:inscription_list")
    return render(request, "admin/inscriptions/delete.html", {"insc": insc})

@login_required
@group_required("SUPER_ADMIN", "ADMIN", "SCOLARITE", "SECRETAIRE")
def groupes_par_annee(request):
    """
    Retourne la liste des groupes pour une année donnée (JSON).
    URL: /core/api/groupes/?annee_id=XX
    """
    annee_id = request.GET.get("annee_id")
    if not annee_id:
        return JsonResponse({"results": []})

    groupes = (
        Groupe.objects
        .filter(annee_id=annee_id)
        .select_related("niveau", "niveau__degre")
        .order_by("niveau__degre__ordre", "niveau__ordre", "nom")
    )

    data = []
    for g in groupes:
        label = f"{g.niveau.degre.nom} / {g.niveau.nom} / {g.nom}"
        data.append({"id": g.id, "label": label})

    return JsonResponse({"results": data})

# =========================
# PAIEMENTS — LIST + FILTRES
# =========================

import uuid
from django.core.exceptions import ValidationError
from django.db.models import Q, Sum, DecimalField
from django.http import JsonResponse, Http404

from .models import (
    AnneeScolaire, Niveau, Groupe, Periode,
    Inscription, Eleve, ParentEleve,
    EcheanceMensuelle, Paiement
)




# =========================================================
# AJAX — fratrie
# =========================================================
@login_required
def ajax_fratrie(request):
    eleve_id_raw = (request.GET.get("eleve") or "").strip()
    if not eleve_id_raw.isdigit():
        return JsonResponse({"ok": False, "error": "eleve manquant"}, status=400)
    eleve_id = int(eleve_id_raw)

    parent_ids = ParentEleve.objects.filter(eleve_id=eleve_id).values_list("parent_id", flat=True)
    if not parent_ids:
        return JsonResponse({"ok": True, "items": []})

    freres = (Eleve.objects
        .filter(liens_parents__parent_id__in=list(parent_ids))
        .exclude(id=eleve_id)
        .distinct()
        .order_by("nom", "prenom")
    )

    items = [{"id": e.id, "matricule": e.matricule, "nom": e.nom, "prenom": e.prenom} for e in freres]
    return JsonResponse({"ok": True, "items": items})


# =========================================================
# LIST
# =========================================================

from django.db.models import Q, Sum, F, DecimalField
from django.utils.dateparse import parse_date

from accounts.permissions import group_required
from django.db.models import Sum, F, DecimalField, ExpressionWrapper, Case, When, Value, BooleanField

from core.models import (
    AnneeScolaire, Periode, Niveau, Groupe, Inscription,
    TransactionFinance
)

@login_required
@group_required("SUPER_ADMIN", "ADMIN", "COMPTABLE")
def paiement_list(request):
    """
    ✅ LISTE DES ENCAISSEMENTS (Wizard)
    -> basé sur TransactionFinance (pas Paiement)
    """
    annee_active = AnneeScolaire.objects.filter(is_active=True).first()

    q = request.GET.get("q", "").strip()
    mode = request.GET.get("mode", "").strip()

    periode_id = request.GET.get("periode", "").strip()
    annee_id = request.GET.get("annee", "").strip()
    niveau_id = request.GET.get("niveau", "").strip()
    groupe_id = request.GET.get("groupe", "").strip()

    date_from = (request.GET.get("date_from") or "").strip()
    date_to = (request.GET.get("date_to") or "").strip()

    # ✅ si aucune année choisie -> année active
    if not annee_id and annee_active:
        annee_id = str(annee_active.id)

    txs = (
        TransactionFinance.objects
        .annotate(
            montant_rembourse=Coalesce(
                Sum("remboursements__montant"),
                Value(Decimal("0.00")),
                output_field=DecimalField(max_digits=10, decimal_places=2),
            ),
        )
        .annotate(
            reste_apres_remboursement=ExpressionWrapper(
                Coalesce(F("montant_total"), Value(Decimal("0.00"))) - Coalesce(F("montant_rembourse"), Value(Decimal("0.00"))),
                output_field=DecimalField(max_digits=10, decimal_places=2),
            )
        )
        .annotate(
            # ✅ full remboursé uniquement si total > 0
            is_rembourse=Case(
                When(
                    montant_total__gt=Value(Decimal("0.00")),
                    montant_rembourse__gte=F("montant_total"),
                    then=Value(True),
                ),
                default=Value(False),
                output_field=BooleanField(),
            ),
            # ✅ partiel uniquement si total > 0
            is_rembourse_partiel=Case(
                When(
                    montant_total__gt=Value(Decimal("0.00")),
                    montant_rembourse__gt=Value(Decimal("0.00")),
                    montant_rembourse__lt=F("montant_total"),
                    then=Value(True),
                ),
                default=Value(False),
                output_field=BooleanField(),
            ),
            # ✅ annulation “0” : on veut pouvoir l’afficher proprement
            is_annulee_zero=Case(
                When(
                    montant_total=Value(Decimal("0.00")),
                    then=Value(True),
                ),
                default=Value(False),
                output_field=BooleanField(),
            ),
            # ✅ bouton “rembourser/annuler” disponible si:
            # - total > 0 et pas full remboursé
            # - OU total == 0 (annulation possible)
            can_refund=Case(
                When(montant_total=Value(Decimal("0.00")), then=Value(True)),
                When(
                    montant_total__gt=Value(Decimal("0.00")),
                    montant_rembourse__lt=F("montant_total"),
                    then=Value(True),
                ),
                default=Value(False),
                output_field=BooleanField(),
            ),
        )
    )
    
    
    # filtres
    if annee_id:
        txs = txs.filter(inscription__annee_id=annee_id)
    if niveau_id:
        txs = txs.filter(inscription__groupe__niveau_id=niveau_id)
    if groupe_id:
        txs = txs.filter(inscription__groupe_id=groupe_id)
    if periode_id:
        txs = txs.filter(inscription__periode_id=periode_id)

    # date range (inclusive) -> champ TransactionFinance.created_at (ou date_transaction si tu l'as)
    d_from = parse_date(date_from) if date_from else None
    d_to = parse_date(date_to) if date_to else None
    if d_from:
        txs = txs.filter(created_at__date__gte=d_from)
    if d_to:
        txs = txs.filter(created_at__date__lte=d_to)

    if mode:
        txs = txs.filter(mode=mode)

    if q:
        txs = txs.filter(
            Q(inscription__eleve__matricule__icontains=q) |
            Q(inscription__eleve__nom__icontains=q) |
            Q(inscription__eleve__prenom__icontains=q) |
            Q(inscription__eleve__telephone__icontains=q) |
            Q(inscription__groupe__nom__icontains=q) |
            Q(inscription__groupe__niveau__nom__icontains=q) |
            Q(inscription__groupe__niveau__degre__nom__icontains=q)
        )

    total = txs.aggregate(
        s=Coalesce(Sum("montant_total"), Decimal("0.00"), output_field=DecimalField(max_digits=10, decimal_places=2))
    )["s"]

    annees = AnneeScolaire.objects.all().order_by("-date_debut")

    periodes = Periode.objects.all().order_by("nom")
    if annee_id:
        periodes = periodes.filter(annee_id=annee_id)

    niveaux = Niveau.objects.all().order_by("nom")
    if annee_id:
        niveaux = niveaux.filter(groupes__annee_id=annee_id).distinct()

    groupes = Groupe.objects.select_related("niveau", "annee").all().order_by("nom")
    if annee_id:
        groupes = groupes.filter(annee_id=annee_id)
    if niveau_id:
        groupes = groupes.filter(niveau_id=niveau_id)

    modes = TransactionFinance._meta.get_field("mode").choices  # ✅ modes depuis TransactionFinance

    return render(request, "admin/paiements/list.html", {
        "txs": txs,  # ✅ IMPORTANT : on envoie txs, pas paiements
        "annee_active": annee_active,

        "annees": annees,
        "annee_selected": annee_id,
        "total": total,

        "niveaux": niveaux,
        "niveau_selected": niveau_id,
        "groupes": groupes,
        "groupe_selected": groupe_id,
        "periodes": periodes,
        "periode_selected": periode_id,

        "q": q,
        "modes": modes,
        "mode_selected": mode,

        "date_from_selected": date_from,
        "date_to_selected": date_to,
    })

# =========================================================
# CREATE (form unique) — multi-mois via payload
# =========================================================
@login_required
@group_required("SUPER_ADMIN", "ADMIN", "SCOLARITE", "COMPTABLE")
def paiement_create(request):
    niveaux = Niveau.objects.select_related("degre").order_by("degre__ordre", "ordre", "nom")

    if request.method == "POST":
        form = PaiementForm(request.POST)

        if not form.is_valid():
            return render(request, "admin/paiements/form.html", {"form": form, "niveaux": niveaux})

        cd = form.cleaned_data
        insc = cd["inscription"]
        nature = (cd.get("nature") or "SCOLARITE").upper()

        # ==========================
        # ✅ MULTI-MOIS (SCOLARITE)
        # ==========================
        ids_int = cd.get("payload_selected_ids") or []
        prices = cd.get("payload_prices") or {}
        is_multi = bool(ids_int)

        if nature == "SCOLARITE" and is_multi:
            batch_token = str(uuid.uuid4())

            echeances = list(
                EcheanceMensuelle.objects.filter(
                    id__in=ids_int,
                    eleve_id=insc.eleve_id,
                    annee_id=insc.annee_id,
                ).order_by("mois_index")
            )

            if len(echeances) != len(ids_int):
                form.add_error(None, "Certaines échéances ne correspondent pas à cet élève / année.")
                return render(request, "admin/paiements/form.html", {"form": form, "niveaux": niveaux})

            try:
                with transaction.atomic():
                    for e in echeances:
                        key = str(e.id)
                        montant = Decimal(str(prices.get(key, "0")).replace(",", "."))

                        if montant <= 0:
                            raise ValidationError(f"Montant invalide pour {e.mois_nom}.")

                        # ✅ interdit si déjà payé
                        if e.statut == "PAYE":
                            raise ValidationError(f"{e.mois_nom} est déjà réglé.")

                        # ✅ Règle A : on enregistre le nouveau prix DU mois
                        e.montant_du = montant

                        # ✅ full payment (pas de partiel)
                        e.montant_paye = montant
                        e.statut = "PAYE"
                        e.save(update_fields=["montant_du", "montant_paye", "statut"])

                        Paiement.objects.create(
                            inscription=insc,
                            nature="SCOLARITE",
                            echeance=e,
                            montant=montant,
                            mode=cd.get("mode"),
                            reference=cd.get("reference") or "",
                            note=cd.get("note") or "",
                            batch_token=batch_token,
                        )


            except ValidationError as ve:
                form.add_error(None, str(ve))
                return render(request, "admin/paiements/form.html", {"form": form, "niveaux": niveaux})

            messages.success(request, "✅ Paiement multi-mois enregistré.")
            return redirect("core:paiement_recu_batch", batch_token=batch_token)

        # ==========================
        # ✅ SINGLE (INSCRIPTION ou SCOLARITE single)
        # ==========================
        p = form.save(commit=False)
        p.inscription = insc
        p.nature = nature
        p.batch_token = ""
        p.save()

        messages.success(request, "✅ Paiement enregistré.")
        return redirect("core:paiement_recu", pk=p.pk)

    # GET
    form = PaiementForm()
    return render(request, "admin/paiements/form.html", {"form": form, "niveaux": niveaux})


# =========================================================
# CREATE for inscription (pré-remplie + verrouillée)
# =========================================================
@login_required
@group_required("SUPER_ADMIN", "ADMIN", "COMPTABLE", "SCOLARITE")
def paiement_create_for_inscription(request, inscription_id):
    insc = get_object_or_404(
        Inscription.objects.select_related("eleve", "annee", "groupe", "groupe__niveau", "groupe__niveau__degre"),
        pk=inscription_id
    )

    niveaux = Niveau.objects.select_related("degre").order_by("degre__ordre", "ordre", "nom")

    if request.method == "POST":
        form = PaiementForm(request.POST, inscription=insc)  # ✅ verrouillage ici

        if not form.is_valid():
            return render(request, "admin/paiements/form.html", {"form": form, "niveaux": niveaux, "insc": insc})

        cd = form.cleaned_data
        nature = (cd.get("nature") or "SCOLARITE").upper()

        ids_int = cd.get("payload_selected_ids") or []
        prices = cd.get("payload_prices") or {}
        is_multi = bool(ids_int)

        if nature == "SCOLARITE" and is_multi:
            batch_token = str(uuid.uuid4())

            echeances = list(
                EcheanceMensuelle.objects.filter(
                    id__in=ids_int,
                    eleve_id=insc.eleve_id,
                    annee_id=insc.annee_id,
                ).order_by("mois_index")
            )

            if len(echeances) != len(ids_int):
                form.add_error(None, "Certaines échéances ne correspondent pas à cet élève / année.")
                return render(request, "admin/paiements/form.html", {"form": form, "niveaux": niveaux, "insc": insc})

            try:
                with transaction.atomic():
                    for e in echeances:
                        key = str(e.id)
                        montant = Decimal(str(prices.get(key, "0")))

                        Paiement.objects.create(
                            inscription=insc,
                            nature="SCOLARITE",
                            echeance=e,
                            montant=montant,
                            mode=cd.get("mode"),
                            reference=cd.get("reference") or "",
                            note=cd.get("note") or "",
                            batch_token=batch_token,
                        )

            except ValidationError as ve:
                form.add_error(None, str(ve))
                return render(request, "admin/paiements/form.html", {"form": form, "niveaux": niveaux, "insc": insc})

            messages.success(request, "✅ Paiement multi-mois enregistré.")
            return redirect("core:paiement_recu_batch", batch_token=batch_token)

        # SINGLE
        p = form.save(commit=False)
        p.inscription = insc
        p.nature = nature
        p.batch_token = ""
        p.save()

        messages.success(request, "✅ Paiement enregistré.")
        return redirect("core:paiement_recu", pk=p.pk)

    # GET
    nat = (request.GET.get("nature") or "SCOLARITE").strip().upper()
    initial = {"inscription": insc, "nature": nat}

    form = PaiementForm(initial=initial, inscription=insc)  # ✅ verrouillage ici aussi
    return render(request, "admin/paiements/form.html", {"form": form, "niveaux": niveaux, "insc": insc})


# =========================================================
# RECU single
# =========================================================
@login_required
@group_required("SUPER_ADMIN", "ADMIN", "COMPTABLE")
def paiement_recu(request, pk):
    p = get_object_or_404(
        Paiement.objects.select_related(
            "inscription", "inscription__eleve", "inscription__annee",
            "inscription__groupe", "inscription__groupe__niveau", "inscription__groupe__niveau__degre",
            "echeance"
        ),
        pk=pk
    )

    total_paye = p.inscription.paiements.aggregate(
        s=Coalesce(Sum("montant"), Decimal("0.00"), output_field=DecimalField(max_digits=10, decimal_places=2))
    )["s"]

    reste = (p.inscription.montant_total or Decimal("0.00")) - (total_paye or Decimal("0.00"))

    return render(request, "admin/paiements/recu.html", {
        "p": p,
        "total_paye": total_paye,
        "reste": reste,
    })


# =========================================================
# RECU batch multi
# =========================================================
@login_required
@group_required("SUPER_ADMIN", "ADMIN", "COMPTABLE")
def paiement_recu_batch(request, batch_token):
    qs = (
        Paiement.objects
        .select_related("inscription", "inscription__eleve", "inscription__annee", "inscription__groupe", "echeance")
        .filter(batch_token=batch_token)
        .order_by("echeance__mois_index", "id")
    )
    if not qs.exists():
        raise Http404

    total = sum((p.montant or Decimal("0.00")) for p in qs)
    first = qs.first()

    return render(request, "admin/paiements/recu_batch.html", {
        "paiements": qs,
        "first": first,
        "total": total,
        "batch_token": batch_token,
    })


@login_required
@group_required("SUPER_ADMIN", "ADMIN", "COMPTABLE")
def impayes_list(request):
    annee_active = AnneeScolaire.objects.filter(is_active=True).first()

    annee_id = request.GET.get("annee", "").strip()
    niveau_id = request.GET.get("niveau", "").strip()
    groupe_id = request.GET.get("groupe", "").strip()
    periode_id = request.GET.get("periode", "").strip()
    q = request.GET.get("q", "").strip()

    inscriptions = Inscription.objects.select_related(
        "eleve", "annee", "groupe", "groupe__niveau", "groupe__niveau__degre", "periode"
    )

    # ✅ défaut: année active
    if not annee_id and annee_active:
        annee_id = str(annee_active.id)

    # ✅ filtres de base (AVANT annotations)
    if annee_id:
        inscriptions = inscriptions.filter(annee_id=annee_id)

    if niveau_id:
        inscriptions = inscriptions.filter(groupe__niveau_id=niveau_id)

    if groupe_id:
        inscriptions = inscriptions.filter(groupe_id=groupe_id)

    if periode_id:
        inscriptions = inscriptions.filter(periode_id=periode_id)

    if q:
        inscriptions = inscriptions.filter(
            Q(eleve__matricule__icontains=q) |
            Q(eleve__nom__icontains=q) |
            Q(eleve__prenom__icontains=q) |
            Q(groupe__nom__icontains=q) |
            Q(groupe__niveau__nom__icontains=q)
        )

    # ✅ total payé
    inscriptions = inscriptions.annotate(
        total_paye=Coalesce(
            Sum("paiements__montant"),
            Decimal("0.00"),
            output_field=DecimalField(max_digits=10, decimal_places=2),
        )
    )

    # ✅ reste
    inscriptions = inscriptions.annotate(
        reste=ExpressionWrapper(
            Coalesce(F("montant_total"), Decimal("0.00")) - F("total_paye"),
            output_field=DecimalField(max_digits=10, decimal_places=2),
        )
    )

    # ✅ vrais impayés
    inscriptions = inscriptions.filter(reste__gt=Decimal("0.00"))

    # ✅ perf: dossier recouvrement (si tu as OneToOne)
    inscriptions = inscriptions.select_related("recouvrement")

    # ✅ KPIs
    total_du = inscriptions.aggregate(
        s=Coalesce(Sum("montant_total"), Decimal("0.00"),
                   output_field=DecimalField(max_digits=10, decimal_places=2))
    )["s"] or Decimal("0.00")

    total_encaisse = inscriptions.aggregate(
        s=Coalesce(Sum("total_paye"), Decimal("0.00"),
                   output_field=DecimalField(max_digits=10, decimal_places=2))
    )["s"] or Decimal("0.00")

    total_impaye = inscriptions.aggregate(
        s=Coalesce(Sum("reste"), Decimal("0.00"),
                   output_field=DecimalField(max_digits=10, decimal_places=2))
    )["s"] or Decimal("0.00")

    # ✅ dropdowns
    annees = AnneeScolaire.objects.all()

    niveaux = Niveau.objects.all()
    if annee_id:
        niveaux = niveaux.filter(groupes__annee_id=annee_id).distinct()

    groupes = Groupe.objects.all()
    if annee_id:
        groupes = groupes.filter(annee_id=annee_id)
    if niveau_id:
        groupes = groupes.filter(niveau_id=niveau_id)

    periodes = Periode.objects.all()
    if annee_id:
        periodes = periodes.filter(annee_id=annee_id)

    return render(request, "admin/impayes/list.html", {
        "inscriptions": inscriptions,
        "annees": annees,
        "annee_selected": annee_id,
        "q": q,

        "niveaux": niveaux,
        "niveau_selected": niveau_id,
        "groupes": groupes,
        "groupe_selected": groupe_id,

        "periodes": periodes,
        "periode_selected": periode_id,

        "total_du": total_du,
        "total_encaisse": total_encaisse,
        "total_impaye": total_impaye,
    })



# =========================
# IMPAYÉS MENSUELS (NEW) — scolarité + transport + inscription
# Règle: afficher impayés du mois courant OU avant (mois_index <= mois_courant)
# =========================
from openpyxl import Workbook


from core.utils import mois_index_courant, mois_nom

@login_required
@group_required("SUPER_ADMIN", "ADMIN", "COMPTABLE")
def impayes_mensuels_list(request):
    annee_active = AnneeScolaire.objects.filter(is_active=True).first()
    if not annee_active:
        return render(request, "admin/impayes/mensuels.html", {
            "annee_active": None,
            "annees": [],
            "niveaux": [],
            "groupes": [],
            "periodes": [],
            "mois_list": list(range(1, 11)),
            "mois_selected": "",
            "type_selected": "ALL",
            "rows": [],
            "kpi": {
                "sco_du": Decimal("0.00"), "sco_paye": Decimal("0.00"), "sco_reste": Decimal("0.00"),
                "tr_du": Decimal("0.00"),  "tr_paye": Decimal("0.00"),  "tr_reste": Decimal("0.00"),
                "ins_du": Decimal("0.00"), "ins_paye": Decimal("0.00"), "ins_reste": Decimal("0.00"),
                "du": Decimal("0.00"), "encaisse": Decimal("0.00"), "impaye": Decimal("0.00"),
            },
            "annee_selected": "",
            "niveau_selected": "",
            "groupe_selected": "",
            "periode_selected": "",
            "q": "",
            "mois_courant": 0,
            "mois_limit": 0,
            "mois_courant_nom": "",
            "mois_limit_nom": "",
        })

    today = timezone.now().date()

    # =========================
    # Filters
    # =========================
    annee_id = (request.GET.get("annee") or "").strip() or str(annee_active.id)
    type_selected = (request.GET.get("type") or "ALL").strip().upper()
    mois_selected = (request.GET.get("mois") or "").strip()
    q = (request.GET.get("q") or "").strip()
    niveau_id = (request.GET.get("niveau") or "").strip()
    groupe_id = (request.GET.get("groupe") or "").strip()
    periode_id = (request.GET.get("periode") or "").strip()

    mois_list = list(range(1, 11))
    if mois_selected and (not mois_selected.isdigit() or int(mois_selected) not in mois_list):
        mois_selected = ""

    # année effective
    annee_obj = AnneeScolaire.objects.filter(id=annee_id).first() or annee_active

    # mois courant (1..10)
    idx_courant = mois_index_courant(annee_obj, today)

    # limite : Auto => mois courant, sinon mois choisi
    idx_limit = idx_courant
    if mois_selected and mois_selected.isdigit():
        idx_limit = int(mois_selected)
    idx_limit = max(1, min(10, idx_limit))

    # =========================
    # Dropdowns
    # =========================
    annees = AnneeScolaire.objects.all().order_by("-date_debut")

    niveaux = (
        Niveau.objects.select_related("degre")
        .order_by("degre__ordre", "ordre", "nom")
    )

    groupes_qs = (
        Groupe.objects.select_related("niveau", "niveau__degre")
        .filter(annee_id=annee_obj.id)
    )
    if niveau_id:
        groupes_qs = groupes_qs.filter(niveau_id=niveau_id)
    groupes = groupes_qs.order_by("niveau__degre__ordre", "niveau__ordre", "nom")

    periodes = Periode.objects.filter(annee_id=annee_obj.id).order_by("ordre")

    # =========================
    # Base inscriptions
    # =========================
    inscs = (
        Inscription.objects
        .select_related("eleve", "annee", "groupe", "groupe__niveau", "groupe__niveau__degre", "periode")
        .filter(annee_id=annee_obj.id)
    )

    if niveau_id:
        inscs = inscs.filter(groupe__niveau_id=niveau_id)
    if groupe_id:
        inscs = inscs.filter(groupe_id=groupe_id)
    if periode_id:
        inscs = inscs.filter(periode_id=periode_id)
    if q:
        inscs = inscs.filter(
            Q(eleve__matricule__icontains=q) |
            Q(eleve__nom__icontains=q) |
            Q(eleve__prenom__icontains=q) |
            Q(groupe__nom__icontains=q) |
            Q(groupe__niveau__nom__icontains=q)
        )

    insc_by_eleve = {i.eleve_id: i for i in inscs}
    eleve_ids = list(insc_by_eleve.keys())

    # =========================
    # Scolarité impayée
    # =========================
    sco_rows = []
    sco_du = sco_paye = sco_reste = Decimal("0.00")

    if type_selected in ["ALL", "SCOLARITE"]:
        sco_qs = (
    EcheanceMensuelle.objects
    .select_related("eleve", "groupe", "annee")
    .filter(annee_id=annee_obj.id, eleve_id__in=eleve_ids)
    .filter(mois_index__lte=idx_limit)
    .order_by("eleve__matricule", "mois_index")
)

        for e in sco_qs:
            du = e.montant_du or Decimal("0.00")
            paye = e.montant_paye or Decimal("0.00")
            reste = max(du - paye, Decimal("0.00"))
            if reste <= 0:
                continue

            eleve = e.eleve
            insc = insc_by_eleve.get(e.eleve_id)

            sco_rows.append({
                "type": "SCOLARITE",
                "eleve": eleve,
                "inscription": insc,
                "groupe": (insc.groupe if insc else None),
                "mois_index": int(e.mois_index),
                "mois_nom": mois_nom(int(e.mois_index)),
                "date_echeance": e.date_echeance,
                "du": du,
                "paye": paye,
                "reste": reste,
                "statut": e.statut,
                "target_id": e.id,
            })

            sco_du += du
            sco_paye += paye
            sco_reste += reste


    # =========================
    # Transport impayé
    # =========================
    tr_rows = []
    tr_du = tr_paye = tr_reste = Decimal("0.00")

    if type_selected in ["ALL", "TRANSPORT"]:
        tr_qs = (
            EcheanceTransportMensuelle.objects
            .select_related("eleve", "groupe", "annee")
            .filter(annee_id=annee_obj.id, eleve_id__in=eleve_ids)
            .filter(mois_index__lte=idx_limit)
            .order_by("eleve__matricule", "mois_index")
        )

        for e in tr_qs:
            du = e.montant_du or Decimal("0.00")
            paye = e.montant_paye or Decimal("0.00")
            reste = max(du - paye, Decimal("0.00"))
            if reste <= 0:
                continue

            eleve = e.eleve
            insc = insc_by_eleve.get(e.eleve_id)

            tr_rows.append({
                "type": "TRANSPORT",
                "eleve": eleve,
                "inscription": insc,
                "groupe": (insc.groupe if insc else None),  # on garde ton affichage groupe via inscription
                "mois_index": int(e.mois_index),
                "mois_nom": mois_nom(int(e.mois_index)),
                "date_echeance": e.date_echeance,
                "du": du,
                "paye": paye,
                "reste": reste,
                "statut": e.statut,
                "target_id": e.id,
            })

            tr_du += du
            tr_paye += paye
            tr_reste += reste

    # =========================
    # Inscription impayée
    # =========================
    ins_rows = []
    ins_du = ins_paye = ins_reste = Decimal("0.00")

    if type_selected in ["ALL", "INSCRIPTION"]:
        for insc in inscs:
            du = insc.frais_inscription_du or Decimal("0.00")
            paye = insc.frais_inscription_paye or Decimal("0.00")
            reste = max(du - paye, Decimal("0.00"))
            if reste <= 0:
                continue

            ins_rows.append({
                "type": "INSCRIPTION",
                "eleve": insc.eleve,
                "inscription": insc,
                "groupe": insc.groupe,
                "mois_index": None,
                "mois_nom": "Inscription",
                "date_echeance": insc.date_inscription,
                "du": du,
                "paye": paye,
                "reste": reste,
                "statut": "A_PAYER" if paye <= 0 else ("PARTIEL" if paye < du else "PAYE"),
                "target_id": insc.id,
            })

            ins_du += du
            ins_paye += paye
            ins_reste += reste

    rows = sco_rows + tr_rows + ins_rows
    def sort_key(r):
        type_rank = {"INSCRIPTION": 0, "SCOLARITE": 1, "TRANSPORT": 2}
        mi = r["mois_index"] if r["mois_index"] is not None else 0
        matricule = (getattr(r["eleve"], "matricule", "") or "")
        return (matricule, type_rank.get(r["type"], 9), mi)


    rows.sort(key=sort_key)

    kpi = {
        "sco_du": sco_du, "sco_paye": sco_paye, "sco_reste": sco_reste,
        "tr_du": tr_du, "tr_paye": tr_paye, "tr_reste": tr_reste,
        "ins_du": ins_du, "ins_paye": ins_paye, "ins_reste": ins_reste,
        "du": (sco_du + tr_du + ins_du),
        "encaisse": (sco_paye + tr_paye + ins_paye),
        "impaye": (sco_reste + tr_reste + ins_reste),
    }

    return render(request, "admin/impayes/mensuels.html", {
        "annee_active": annee_active,
        "annees": annees,
        "niveaux": niveaux,
        "groupes": groupes,
        "periodes": periodes,
        "rows": rows,
        "kpi": kpi,
        "annee_selected": str(annee_obj.id),
        "mois_selected": mois_selected,
        "mois_list": mois_list,
        "type_selected": type_selected,
        "niveau_selected": niveau_id,
        "groupe_selected": groupe_id,
        "periode_selected": periode_id,
        "q": q,
        "mois_courant": idx_courant,
        "mois_limit": idx_limit,
        "mois_courant_nom": mois_nom(idx_courant),
        "mois_limit_nom": mois_nom(idx_limit),
    })


@login_required
@group_required("SUPER_ADMIN", "ADMIN", "COMPTABLE")
def impayes_mensuels_excel_export(request):
    """
    Export EXACT du même écran (NEW) : scolarité + transport + inscription
    """
    annee_active = AnneeScolaire.objects.filter(is_active=True).first()
    if not annee_active:
        return HttpResponse("Aucune année active", status=400)

    today = timezone.now().date()

    annee_id = (request.GET.get("annee") or "").strip() or str(annee_active.id)
    type_selected = (request.GET.get("type") or "ALL").strip().upper()
    mois_selected = (request.GET.get("mois") or "").strip()
    q = (request.GET.get("q") or "").strip()
    niveau_id = (request.GET.get("niveau") or "").strip()
    groupe_id = (request.GET.get("groupe") or "").strip()
    periode_id = (request.GET.get("periode") or "").strip()

    annee_obj = AnneeScolaire.objects.filter(id=annee_id).first() or annee_active
    idx_courant = mois_index_courant(annee_obj, today)
    idx_limit = idx_courant
    if mois_selected and mois_selected.isdigit():
        idx_limit = min(int(mois_selected), idx_courant)

    # base inscriptions filtrées (comme page)
    inscs = (
        Inscription.objects
        .select_related("eleve", "annee", "groupe", "groupe__niveau", "groupe__niveau__degre", "periode")
        .filter(annee_id=annee_obj.id)
    )
    if niveau_id:
        inscs = inscs.filter(groupe__niveau_id=niveau_id)
    if groupe_id:
        inscs = inscs.filter(groupe_id=groupe_id)
    if periode_id:
        inscs = inscs.filter(periode_id=periode_id)
    if q:
        inscs = inscs.filter(
            Q(eleve__matricule__icontains=q) |
            Q(eleve__nom__icontains=q) |
            Q(eleve__prenom__icontains=q) |
            Q(groupe__nom__icontains=q) |
            Q(groupe__niveau__nom__icontains=q)
        )

    insc_by_eleve = {i.eleve_id: i for i in inscs}
    eleve_ids = list(insc_by_eleve.keys())

    rows = []

    # scolarité
    if type_selected in ["ALL", "SCOLARITE"]:
        sco_qs = (
    EcheanceMensuelle.objects
    .select_related("eleve", "groupe", "annee")
    .filter(
        annee_id=annee_obj.id,
        eleve_id__in=eleve_ids,
        mois_index__lte=idx_limit,
    )
    .order_by("eleve__matricule", "mois_index")
)
        for e in sco_qs:
            du = e.montant_du or Decimal("0.00")
            paye = e.montant_paye or Decimal("0.00")
            reste = max(du - paye, Decimal("0.00"))
            if reste <= 0:
                continue

            eleve = e.eleve
            insc = insc_by_eleve.get(e.eleve_id)
            g = insc.groupe if insc else None
            rows.append(("SCOLARITE", eleve, g, mois_nom(int(e.mois_index)), e.date_echeance, du, paye, reste))


    # transport

    if type_selected in ["ALL", "TRANSPORT"]:
        tr_qs = (
            EcheanceTransportMensuelle.objects
            .select_related("eleve", "groupe", "annee")
            .filter(
                annee_id=annee_obj.id,
                eleve_id__in=eleve_ids,
                mois_index__lte=idx_limit,
            )
            .order_by("eleve__matricule", "mois_index")
        )

        for e in tr_qs:
            du = e.montant_du or Decimal("0.00")
            paye = e.montant_paye or Decimal("0.00")
            reste = max(du - paye, Decimal("0.00"))
            if reste <= 0:
                continue

            eleve = e.eleve
            insc = insc_by_eleve.get(e.eleve_id)
            g = insc.groupe if insc else None

            rows.append(("TRANSPORT", eleve, g, mois_nom(int(e.mois_index)), e.date_echeance, du, paye, reste))


    # inscription
    if type_selected in ["ALL", "INSCRIPTION"]:
        for insc in inscs:
            du = insc.frais_inscription_du or Decimal("0.00")
            paye = insc.frais_inscription_paye or Decimal("0.00")
            reste = max(du - paye, Decimal("0.00"))
            if reste <= 0:
                continue
            rows.append(("INSCRIPTION", insc.eleve, insc.groupe, "Inscription", insc.date_inscription, du, paye, reste))

    # build excel
    wb = Workbook()
    ws = wb.active
    ws.title = "Impayes"

    ws.append(["Type", "Matricule", "Nom", "Prenom", "Groupe", "Mois", "Date", "Du", "Paye", "Reste"])

    for t, eleve, groupe, mois_nom_str, dte, du, paye, reste in rows:
        ws.append([
            t,
            getattr(eleve, "matricule", "") if eleve else "",
            getattr(eleve, "nom", "") if eleve else "",
            getattr(eleve, "prenom", "") if eleve else "",
            (groupe.nom if groupe else ""),
            mois_nom_str,
            str(dte),
            float(du),
            float(paye),
            float(reste),
        ])

    resp = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    resp["Content-Disposition"] = 'attachment; filename="impayes.xlsx"'
    wb.save(resp)
    return resp


# ============================
# F2 — Recouvrement (MVP)
# ============================

@login_required
@group_required("SUPER_ADMIN", "ADMIN", "COMPTABLE")
def recouvrement_list(request):
    annee_active = AnneeScolaire.objects.filter(is_active=True).first()
    annee_id = request.GET.get("annee", "")
    statut = request.GET.get("statut", "")
    q = request.GET.get("q", "").strip()

    sans_relance = request.GET.get("sans_relance", "") 
    
    date_limite = timezone.now().date() - timedelta(days=30)
    
    dossiers = (
        Recouvrement.objects
        .select_related("inscription", "inscription__eleve", "inscription__annee", "inscription__groupe")
        .annotate(
            relances_count=Count("relances", distinct=True),
            last_relance_at=Max("relances__created_at"),
        )
    )
    # défaut: année active
    if not annee_id and annee_active:
        annee_id = str(annee_active.id)

    if annee_id:
        dossiers = dossiers.filter(inscription__annee_id=annee_id)

    if statut:
        dossiers = dossiers.filter(statut=statut)

    if q:
        dossiers = dossiers.filter(
            Q(inscription__eleve__matricule__icontains=q) |
            Q(inscription__eleve__nom__icontains=q) |
            Q(inscription__eleve__prenom__icontains=q) |
            Q(inscription__groupe__nom__icontains=q)
        )

    if sans_relance == "1":
        dossiers = dossiers.filter(relances_count=0)
    # KPIs
    total_dossiers = dossiers.count()

    annees = AnneeScolaire.objects.all()

    return render(request, "admin/recouvrements/list.html", {
        "dossiers": dossiers,
        "annees": annees,
        "annee_selected": annee_id,
        "statut_selected": statut,
        "q": q,
        "total_dossiers": total_dossiers,
        "STATUT_CHOICES": Recouvrement.STATUT_CHOICES,
    })


@login_required
@group_required("SUPER_ADMIN", "ADMIN", "COMPTABLE")
def recouvrement_create_for_inscription(request, inscription_id):
    insc = get_object_or_404(
        Inscription.objects.select_related("eleve", "annee", "groupe"),
        pk=inscription_id
    )

    # Bloquer si déjà existant
    if hasattr(insc, "recouvrement"):
        messages.info(request, "ℹ️ Un dossier de recouvrement existe déjà pour cette inscription.")
        return redirect("core:recouvrement_detail", pk=insc.recouvrement.pk)

    # Calcul solde via annotation simple
    total_paye = insc.paiements.aggregate(
        s=Coalesce(Sum("montant"), Decimal("0.00"), output_field=DecimalField(max_digits=10, decimal_places=2))
    )["s"] or Decimal("0.00")
    solde = (insc.montant_total or Decimal("0.00")) - total_paye

    if solde <= Decimal("0.00"):
        messages.warning(request, "✅ Cette inscription est déjà réglée. Aucun dossier nécessaire.")
        return redirect("core:impayes_list")

    # Création dossier
    dossier = Recouvrement.objects.create(
        inscription=insc,
        statut="EN_COURS",
        date_ouverture=timezone.now().date(),
    )

    messages.success(request, "✅ Dossier de recouvrement créé.")
    return redirect("core:recouvrement_detail", pk=dossier.pk)


@login_required
@group_required("SUPER_ADMIN", "ADMIN", "COMPTABLE")
def recouvrement_detail(request, pk):
    dossier = get_object_or_404(
        Recouvrement.objects.select_related(
            "inscription", "inscription__eleve", "inscription__annee", "inscription__groupe"
        ),
        pk=pk
    )

    # Totaux
    total_paye = dossier.total_paye
    solde = dossier.solde

    # Auto réglé si solde = 0
    dossier.refresh_statut_si_regle(save=True)

    relances = dossier.relances.select_related("created_by").all()
    paiements = dossier.inscription.paiements.all().order_by("-date_paiement", "-id")

    # Parents liés
    liens_parents = ParentEleve.objects.select_related("parent").filter(eleve=dossier.inscription.eleve)

    return render(request, "admin/recouvrements/detail.html", {
        "dossier": dossier,
        "relances": relances,
        "paiements": paiements,
        "liens_parents": liens_parents,
        "total_paye": total_paye,
        "solde": solde,
        "TYPE_CHOICES": Relance.TYPE_CHOICES,
    })


@login_required
@group_required("SUPER_ADMIN", "ADMIN", "COMPTABLE")
def relance_create(request, dossier_id):
    dossier = get_object_or_404(Recouvrement, pk=dossier_id)

    if request.method == "POST":
        type_ = (request.POST.get("type") or "SMS").strip().upper()
        message_txt = (request.POST.get("message") or "").strip()

        # sécurité type
        allowed = [t[0] for t in Relance.TYPE_CHOICES]
        if type_ not in allowed:
            type_ = "SMS"

        Relance.objects.create(
            recouvrement=dossier,
            type=type_,
            message=message_txt
        )

        # passage en relance si pas réglé/clôturé
        if dossier.statut not in ["REGLE", "CLOTURE"]:
            dossier.statut = "EN_RELANCE"
            dossier.save(update_fields=["statut", "updated_at", "updated_by"])

        messages.success(request, "✅ Relance ajoutée.")
        return redirect("core:recouvrement_detail", pk=dossier.pk)

    # GET => renvoie vers detail (on utilise le form intégré dans la page)
    return redirect("core:recouvrement_detail", pk=dossier.pk)


@login_required
@group_required("SUPER_ADMIN", "ADMIN", "COMPTABLE")
def recouvrement_cloturer(request, pk):
    dossier = get_object_or_404(Recouvrement, pk=pk)

    if request.method == "POST":
        dossier.statut = "CLOTURE"
        dossier.date_cloture = timezone.now().date()
        dossier.save(update_fields=["statut", "date_cloture", "updated_at", "updated_by"])
        messages.success(request, "✅ Dossier clôturé.")
        return redirect("core:recouvrement_detail", pk=dossier.pk)

    return redirect("core:recouvrement_detail", pk=dossier.pk)

# ============================
# E1 — Enseignants
# ============================
from .models import Enseignant, AnneeScolaire, AbsenceProf
from .services_absences_profs import stats_mensuelles_prof



from core.models import (
    Enseignant, AnneeScolaire, Niveau, Groupe, Periode,
    EnseignantGroupe, Seance, AbsenceProf
)

@login_required
@group_required("SUPER_ADMIN", "ADMIN", "PEDAGOGIQUE")
def enseignant_list(request):
    annee_active = AnneeScolaire.objects.filter(is_active=True).first()
    matieres = Matiere.objects.filter(is_active=True).order_by("nom")

    # --- GET (strings) ---
    annee_id  = (request.GET.get("annee") or "").strip()
    niveau_id = (request.GET.get("niveau") or "").strip()
    groupe_id = (request.GET.get("groupe") or "").strip()
    periode_id = (request.GET.get("periode") or "").strip()
    matiere_id = (request.GET.get("matiere") or "").strip()  # ✅ optionnel si tu ajoutes un filtre matière

    q = (request.GET.get("q") or "").strip()
    statut = (request.GET.get("statut") or "").strip()  # "actifs" / "inactifs" / ""

    # --- année par défaut (pour UI) ---
    if not annee_id.isdigit():
        annee_id = str(annee_active.id) if annee_active else ""

    enseignants = Enseignant.objects.all()

    # ✅ Statut
    if statut == "actifs":
        enseignants = enseignants.filter(is_active=True)
    elif statut == "inactifs":
        enseignants = enseignants.filter(is_active=False)

    # ✅ Recherche
    if q:
        enseignants = enseignants.filter(
            Q(matricule__icontains=q) |
            Q(nom__icontains=q) |
            Q(prenom__icontains=q) |
            Q(telephone__icontains=q) |
            Q(email__icontains=q)
        )

    # =========================================================
    # ✅ FILTRES PEDAGOGIQUES (via EnseignantGroupe)
    # =========================================================
    # On filtre via affectations seulement si l'utilisateur a choisi un filtre pédagogique
    filter_via_affectations = False
    aff_qs = EnseignantGroupe.objects.all()

    if annee_id.isdigit():
        aff_qs = aff_qs.filter(annee_id=int(annee_id))

    if niveau_id.isdigit():
        aff_qs = aff_qs.filter(groupe__niveau_id=int(niveau_id))
        filter_via_affectations = True

    if groupe_id.isdigit():
        aff_qs = aff_qs.filter(groupe_id=int(groupe_id))
        filter_via_affectations = True

    if matiere_id.isdigit():
        aff_qs = aff_qs.filter(matiere_fk_id=int(matiere_id))
        filter_via_affectations = True

    # Si on a déclenché un filtrage pédagogique → on restreint les enseignants via affectations
    if filter_via_affectations:
        enseignants = enseignants.filter(id__in=aff_qs.values("enseignant_id"))

    # =========================================================
    # ✅ FILTRE PERIODE (optionnel) : via AbsenceProf ou Seance
    # =========================================================
    # ⚠️ Ce filtre est "activité" et peut exclure des enseignants sans absences/séances.
    periode_obj = None
    if periode_id.isdigit():
        periode_obj = Periode.objects.filter(id=int(periode_id)).first()
        if periode_obj and periode_obj.date_debut and periode_obj.date_fin and annee_id.isdigit():
            # Ici je filtre via AbsenceProf (plus logique que Absence eleves)
            enseignants = enseignants.filter(
                absences_profs__annee_id=int(annee_id),
                absences_profs__date__gte=periode_obj.date_debut,
                absences_profs__date__lte=periode_obj.date_fin,
            )

    enseignants = enseignants.distinct().order_by("nom", "prenom")

    # =========================================================
    # ✅ Listes pour filtres UI
    # =========================================================
    annees = AnneeScolaire.objects.all().order_by("-date_debut")

    niveaux = Niveau.objects.select_related("degre").all().order_by("degre__ordre", "ordre", "nom")
    if annee_id.isdigit():
        niveaux = niveaux.filter(groupes__annee_id=int(annee_id)).distinct()

    groupes = Groupe.objects.select_related("niveau", "niveau__degre", "annee").all().order_by(
        "niveau__degre__ordre", "niveau__ordre", "nom"
    )
    if annee_id.isdigit():
        groupes = groupes.filter(annee_id=int(annee_id))
    if niveau_id.isdigit():
        groupes = groupes.filter(niveau_id=int(niveau_id))

    periodes = Periode.objects.select_related("annee").all().order_by("ordre")
    if annee_id.isdigit():
        periodes = periodes.filter(annee_id=int(annee_id))

    # ✅ Bonus : si tu veux aussi un filtre matière (facultatif)
    # matieres = Matiere.objects.filter(is_active=True).order_by("nom")

    return render(request, "admin/enseignants/list.html", {
        "enseignants": enseignants,

        "annees": annees,
        "annee_selected": annee_id,

        "niveaux": niveaux,
        "niveau_selected": niveau_id,

        "groupes": groupes,
        "groupe_selected": groupe_id,

        "periodes": periodes,
        "periode_selected": periode_id,

        "matieres": matieres,
        "matiere_selected": matiere_id,

        "q": q,
        "statut": statut,
    })

@login_required
@group_required("SUPER_ADMIN", "ADMIN")
def enseignant_detail(request, pk):
    ens = get_object_or_404(Enseignant, pk=pk)

    annee = AnneeScolaire.objects.filter(is_active=True).first()

    # mois/année (par défaut aujourd’hui)
    today = date.today()
    year = int(request.GET.get("year", today.year))
    month = int(request.GET.get("month", today.month))

    stats = None
    absences = AbsenceProf.objects.none()

    if annee:
        stats = stats_mensuelles_prof(enseignant=ens, annee=annee, year=year, month=month)

        absences = (
            AbsenceProf.objects
            .filter(annee=annee, enseignant=ens, date__year=year, date__month=month)
            .select_related("seance", "seance__groupe")
            .order_by("-date")
        )

    return render(request, "admin/enseignants/detail.html", {
        "ens": ens,
        "annee": annee,
        "year": year,
        "month": month,
        "stats": stats,
        "absences_profs": absences,  # 👈 important
    })


@login_required
@group_required("SUPER_ADMIN", "ADMIN")
def enseignant_create(request):
    if request.method == "POST":
        form = EnseignantForm(request.POST, request.FILES)  # ✅ IMPORTANT
        if form.is_valid():
            ens = form.save()

            try:
                user, pwd, created = get_or_create_user_with_group(ens.matricule, "PROF")

                if ens.user_id != user.id:
                    ens.user = user
                    ens.save(update_fields=["user"])

                if created:
                    messages.success(request, f"✅ Enseignant ajouté: {ens.matricule} | MDP temporaire: {pwd}")
                else:
                    messages.info(request, f"ℹ️ User existe déjà pour {ens.matricule}. Rôle PROF assuré.")
            except Exception as e:
                messages.warning(request, f"⚠️ Enseignant créé mais user non créé: {e}")

            return redirect("core:enseignant_detail", pk=ens.pk)
    else:
        form = EnseignantForm()

    return render(request, "admin/enseignants/form.html", {"form": form, "mode": "create"})

@login_required
@group_required("SUPER_ADMIN", "ADMIN")
def enseignant_update(request, pk):
    ens = get_object_or_404(Enseignant, pk=pk)
    if request.method == "POST":
        form = EnseignantForm(request.POST, request.FILES, instance=ens)  # ✅ IMPORTANT
        if form.is_valid():
            form.save()
            messages.success(request, "✅ Enseignant mis à jour.")
            return redirect("core:enseignant_detail", pk=ens.pk)
    else:
        form = EnseignantForm(instance=ens)

    return render(request, "admin/enseignants/form.html", {
        "form": form,
        "mode": "update",
        "ens": ens,
    })


@login_required
@group_required("SUPER_ADMIN", "ADMIN", "SCOLARITE")
def enseignant_delete(request, pk):
    ens = get_object_or_404(Enseignant, pk=pk)

    # Séances qui bloquent la suppression
    seances_bloquantes = (
        Seance.objects
        .filter(enseignant=ens)
        .select_related("annee", "groupe", "groupe__niveau", "groupe__niveau__degre")
        .order_by("jour", "heure_debut")
    )

    if request.method == "POST":
        try:
            ens.delete()
            messages.success(request, "✅ Enseignant supprimé avec succès.")
            return redirect("core:enseignant_list")

        except ProtectedError:
            messages.error(
                request,
                "❌ Suppression impossible : cet enseignant est utilisé dans l'emploi du temps."
            )

    return render(request, "admin/enseignants/delete.html", {
        "ens": ens,
        "seances_bloquantes": seances_bloquantes,
    })


# E1.5 — Affectations Enseignant <-> Groupes
# ============================
@login_required
@group_required("SUPER_ADMIN", "ADMIN", "PEDAGOGIQUE")
def enseignant_affectations(request, pk):
    ens = get_object_or_404(Enseignant, pk=pk)

    affectations = (
        EnseignantGroupe.objects
        .select_related("annee", "groupe", "groupe__niveau", "groupe__niveau__degre")
        .filter(enseignant=ens, matiere_fk__isnull=True)  # ✅ group-only
        .order_by("-created_at")
    )

    form = EnseignantGroupeForm()

    return render(request, "admin/enseignants/affectations.html", {
        "ens": ens,
        "affectations": affectations,
        "form": form,
    })


@login_required
@group_required("SUPER_ADMIN", "ADMIN", "PEDAGOGIQUE")
def enseignant_affectation_add(request, pk):
    ens = get_object_or_404(Enseignant, pk=pk)

    if request.method != "POST":
        return redirect("core:enseignant_affectations", pk=ens.pk)

    form = EnseignantGroupeForm(request.POST)
    if form.is_valid():
        obj = form.save(commit=False)
        obj.enseignant = ens
        obj.matiere_fk = None  # ✅ group-only

        if obj.groupe_id:
            obj.annee_id = obj.groupe.annee_id

        try:
            obj.full_clean()
            obj.save()
            messages.success(request, "✅ Groupe affecté au professeur.")
        except Exception as e:
            messages.error(request, f"⚠️ Erreur: {e}")
    else:
        messages.error(request, "⚠️ Formulaire invalide. Vérifie l’année et le groupe.")

    return redirect("core:enseignant_affectations", pk=ens.pk)


@login_required
@group_required("SUPER_ADMIN", "ADMIN", "PEDAGOGIQUE")
def enseignant_affectation_delete(request, pk, aff_id):
    ens = get_object_or_404(Enseignant, pk=pk)
    aff = get_object_or_404(
        EnseignantGroupe,
        pk=aff_id,
        enseignant=ens,
        matiere_fk__isnull=True
    )

    if request.method == "POST":
        aff.delete()
        messages.success(request, "🗑️ Affectation supprimée.")

    return redirect("core:enseignant_affectations", pk=ens.pk)

# ============================
# E2 — Emploi du temps (Séances)
# ============================


from django.db.models.deletion import ProtectedError

from .models import Seance, Absence



from .models import AnneeScolaire, Groupe, Niveau, Enseignant, Seance


def _jour_code_from_date(date_str: str):
    """
    Convertit une date 'YYYY-MM-DD' vers code jour Seance (LUN..SAM).
    Retourne None si invalide.
    """
    if not date_str:
        return None
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return None

    # weekday(): lundi=0 ... dimanche=6
    mapping = {0: "LUN", 1: "MAR", 2: "MER", 3: "JEU", 4: "VEN", 5: "SAM"}
    return mapping.get(d.weekday())  # dimanche => None


@login_required
@group_required("SUPER_ADMIN", "ADMIN", "PEDAGOGIQUE")
def seance_list(request):
    annee_active = AnneeScolaire.objects.filter(is_active=True).first()

    annee_id = (request.GET.get("annee") or "").strip()
    niveau_id = (request.GET.get("niveau") or "").strip()
    groupe_id = (request.GET.get("groupe") or "").strip()
    enseignant_id = (request.GET.get("enseignant") or "").strip()
    date_str = (request.GET.get("date") or "").strip()
    q = (request.GET.get("q") or "").strip()

    # ✅ année par défaut = active
    if not annee_id and annee_active:
        annee_id = str(annee_active.id)

    jour_code = _jour_code_from_date(date_str)

    # ✅ Queryset de base
    seances = Seance.objects.select_related(
        "annee", "groupe", "groupe__niveau", "groupe__niveau__degre", "enseignant"
    )

    # ✅ IMPORTANT : appliquer le filtre année (sinon => toutes les années)
    if annee_id and annee_id.isdigit():
        seances = seances.filter(annee_id=int(annee_id))

    # ✅ Filtre niveau/groupe (via groupe)
    if niveau_id and niveau_id.isdigit():
        seances = seances.filter(groupe__niveau_id=int(niveau_id))

    if groupe_id and groupe_id.isdigit():
        seances = seances.filter(groupe_id=int(groupe_id))

    # ✅ Filtre enseignant
    if enseignant_id and enseignant_id.isdigit():
        seances = seances.filter(enseignant_id=int(enseignant_id))

    # ✅ Filtre DATE -> convertit en jour (LUN/MAR/...)
    if date_str:
        if jour_code:
            seances = seances.filter(jour=jour_code)
        else:
            seances = seances.none()

    # ✅ Recherche
    if q:
        seances = seances.filter(
            Q(matiere__icontains=q) |
            Q(salle__icontains=q) |
            Q(groupe__nom__icontains=q) |
            Q(enseignant__nom__icontains=q) |
            Q(enseignant__prenom__icontains=q)
        )

    # Listes filtres
    annees = AnneeScolaire.objects.all()

    niveaux = Niveau.objects.select_related("degre").all()
    if annee_id and annee_id.isdigit():
        niveaux = niveaux.filter(groupes__annee_id=int(annee_id)).distinct()

    groupes = Groupe.objects.select_related("niveau", "niveau__degre", "annee").all()
    if annee_id and annee_id.isdigit():
        groupes = groupes.filter(annee_id=int(annee_id))
    if niveau_id and niveau_id.isdigit():
        groupes = groupes.filter(niveau_id=int(niveau_id))

    # ✅ Enseignants proposés : uniquement ceux qui ont des séances selon filtres
    ens_qs = Seance.objects.all()
    if annee_id and annee_id.isdigit():
        ens_qs = ens_qs.filter(annee_id=int(annee_id))
    if niveau_id and niveau_id.isdigit():
        ens_qs = ens_qs.filter(groupe__niveau_id=int(niveau_id))
    if groupe_id and groupe_id.isdigit():
        ens_qs = ens_qs.filter(groupe_id=int(groupe_id))
    if date_str and jour_code:
        ens_qs = ens_qs.filter(jour=jour_code)

    enseignants = Enseignant.objects.filter(
        id__in=ens_qs.values_list("enseignant_id", flat=True).distinct()
    )

    return render(request, "admin/seances/list.html", {
        "seances": seances,

        "annees": annees,
        "annee_selected": annee_id,
        "annee_active": annee_active,  # ✅ pour ton template

        "niveaux": niveaux,
        "niveau_selected": niveau_id,

        "groupes": groupes,
        "groupe_selected": groupe_id,

        "enseignants": enseignants,
        "enseignant_selected": enseignant_id,

        "date_selected": date_str,
        "q": q,
    })


@login_required
@group_required("SUPER_ADMIN", "ADMIN", "PEDAGOGIQUE")
def seance_create(request):
    if request.method == "POST":
        form = SeanceForm(request.POST)
        if form.is_valid():
            s = form.save()
            messages.success(request, "✅ Séance ajoutée.")
            
            action = request.POST.get("action", "save")
            if action == "save_add":
                # on repart sur create avec mêmes filtres
                url = reverse("core:seance_create")
                params = f"?annee={s.annee_id}&groupe={s.groupe_id}&jour={s.jour}"
                return redirect(url + params)

            # sinon retour EDT semaine filtré
            return redirect(reverse("core:edt_week") + f"?annee={s.annee_id}&groupe={s.groupe_id}")
    else:
        initial = {}
        if request.GET.get("annee"):
            initial["annee"] = request.GET.get("annee")
        if request.GET.get("groupe"):
            initial["groupe"] = request.GET.get("groupe")
        if request.GET.get("jour"):
            initial["jour"] = request.GET.get("jour")

        form = SeanceForm(initial=initial)
    return render(request, "admin/seances/form.html", {"form": form, "mode": "create"})


@login_required
@group_required("SUPER_ADMIN", "ADMIN", "PEDAGOGIQUE")
def seance_update(request, pk):
    s = get_object_or_404(Seance, pk=pk)
    if request.method == "POST":
        form = SeanceForm(request.POST, instance=s)
        if form.is_valid():
            form.save()
            messages.success(request, "✅ Séance mise à jour.")
            return redirect("core:seance_list")
    else:
        form = SeanceForm(instance=s)
    return render(request, "admin/seances/form.html", {"form": form, "mode": "update", "s": s})


@login_required
@group_required("SUPER_ADMIN", "ADMIN", "PEDAGOGIQUE")
def seance_delete(request, pk):
    s = get_object_or_404(
        Seance.objects.select_related(
            "annee", "groupe", "groupe__niveau", "groupe__niveau__degre", "enseignant"
        ),
        pk=pk
    )

    absences_bloquantes = (
        Absence.objects
        .filter(seance=s)
        .select_related("eleve", "groupe", "annee")
        .order_by("-date", "eleve__nom", "eleve__prenom")
    )

    if request.method == "POST":
        action = (request.POST.get("action") or "delete").strip().lower()

        # ✅ CAS 1 — suppression normale
        if action == "delete":
            try:
                s.delete()
                messages.success(request, "🗑️ Séance supprimée.")
                return redirect("core:seance_list")

            except ProtectedError:
                messages.error(
                    request,
                    "❌ Suppression impossible : cette séance est liée à des absences. "
                    "Tu peux soit supprimer ces absences, soit cliquer sur 'Forcer la suppression'."
                )

        # ✅ CAS 2 — FORCER : supprime d’abord les absences liées puis la séance
        elif action == "force":
            count_abs = absences_bloquantes.count()

            try:
                with transaction.atomic():
                    # 1) supprimer toutes les absences liées à cette séance
                    absences_bloquantes.delete()

                    # 2) supprimer la séance
                    s.delete()

                messages.success(
                    request,
                    f"🗑️ Séance supprimée (FORCÉ) + {count_abs} absence(s) supprimée(s)."
                )
                return redirect("core:seance_list")

            except ProtectedError:
                # normalement après delete des absences ça passe,
                # mais on garde une sécurité
                messages.error(
                    request,
                    "❌ Forçage impossible : la séance est encore référencée ailleurs."
                )

    return render(request, "admin/seances/delete.html", {
        "s": s,
        "absences_bloquantes": absences_bloquantes,
    })

@login_required
@group_required("SUPER_ADMIN", "ADMIN", "PEDAGOGIQUE")
def edt_week(request):
    annee_active = AnneeScolaire.objects.filter(is_active=True).first()

    # --- GET (toujours en str) ---
    annee_id = (request.GET.get("annee") or "").strip()
    niveau_id = (request.GET.get("niveau") or "").strip()
    groupe_id = (request.GET.get("groupe") or "").strip()

    # --- Année par défaut : année active si annee_id vide/invalide ---
    if not annee_id.isdigit():
        annee_id = str(annee_active.id) if annee_active else ""

    # Listes
    annees = AnneeScolaire.objects.all()

    # ✅ Niveaux (filtrés par année)
    niveaux = Niveau.objects.select_related("degre").all()
    if annee_id.isdigit():
        niveaux = niveaux.filter(groupes__annee_id=int(annee_id)).distinct()

    # ✅ Groupes (filtrés par année + niveau)
    groupes = Groupe.objects.select_related("annee", "niveau", "niveau__degre").all()
    if annee_id.isdigit():
        groupes = groupes.filter(annee_id=int(annee_id))
    if niveau_id.isdigit():
        groupes = groupes.filter(niveau_id=int(niveau_id))

    # ✅ Groupe par défaut = 1er groupe du queryset
    if (not groupe_id.isdigit()) and groupes.exists():
        groupe_id = str(groupes.first().id)

    # ✅ Séances : ne filtre par annee/groupe que si IDs valides
    seances = Seance.objects.select_related("enseignant", "groupe").all()
    if annee_id.isdigit():
        seances = seances.filter(annee_id=int(annee_id))
    if groupe_id.isdigit():
        seances = seances.filter(groupe_id=int(groupe_id))

    days = [
        ("LUN", "Lundi"),
        ("MAR", "Mardi"),
        ("MER", "Mercredi"),
        ("JEU", "Jeudi"),
        ("VEN", "Vendredi"),
        ("SAM", "Samedi"),
    ]

    by_day = {code: [] for code, _ in days}
    for s in seances.order_by("jour", "heure_debut"):
        by_day[s.jour].append(s)

    return render(request, "admin/seances/week.html", {
        "annees": annees,
        "annee_selected": annee_id,

        "niveaux": niveaux,
        "niveau_selected": niveau_id,

        "groupes": groupes,
        "groupe_selected": groupe_id,

        "days": days,
        "by_day": by_day,
    })


# ============================
# F1 — Absences
# ============================
from django.views.decorators.http import require_GET, require_POST

@login_required
@group_required("SUPER_ADMIN", "ADMIN", "SCOLARITE", "PEDAGOGIQUE", "SECRETAIRE")
def absences_pratique(request):
    """
    Page 1:
    1) choisir niveau + groupe
    2) choisir date
    3) affiche séances du jour (via api_seances_par_groupe_date)
    """
    annee_active = AnneeScolaire.objects.filter(is_active=True).first()
    annee_id = request.GET.get("annee", "") or (str(annee_active.id) if annee_active else "")

    niveau_id = request.GET.get("niveau", "")
    groupe_id = request.GET.get("groupe", "")
    date_str = request.GET.get("date", "")

    if not date_str:
        date_str = timezone.now().date().isoformat()

    annees = AnneeScolaire.objects.all()

    # ✅ niveaux disponibles pour cette année (via groupes)
    niveaux = Niveau.objects.select_related("degre").all()
    if annee_id:
        niveaux = niveaux.filter(groupes__annee_id=annee_id).distinct()

    # ✅ groupes filtrés par année (+ niveau si choisi)
    groupes = Groupe.objects.select_related("niveau", "niveau__degre").all()
    if annee_id:
        groupes = groupes.filter(annee_id=annee_id)
    if niveau_id:
        groupes = groupes.filter(niveau_id=niveau_id)

    return render(request, "admin/absences/pratique.html", {
        "annees": annees,
        "annee_selected": annee_id,

        "niveaux": niveaux,
        "niveau_selected": niveau_id,

        "groupes": groupes,
        "groupe_selected": groupe_id,

        "date_selected": date_str,
    })

@login_required
@group_required("SUPER_ADMIN", "ADMIN", "SCOLARITE", "PEDAGOGIQUE", "SECRETAIRE")
def absences_feuille(request):
    """
    Page 2:
    Affiche la feuille de présence (JS charge les données via api_feuille_presence)
    """
    seance_id = request.GET.get("seance_id") or request.GET.get("seance")
    date_str = request.GET.get("date")

    if not seance_id or not date_str:
        messages.error(request, "⚠️ Séance ou date manquante.")
        return redirect("core:absences_pratique")

    return render(request, "admin/absences/feuille.html", {
        "seance_id": seance_id,
        "date_selected": date_str,
    })


@require_GET
@login_required
@group_required("SUPER_ADMIN", "ADMIN", "SCOLARITE", "PEDAGOGIQUE", "SECRETAIRE")
def api_feuille_presence(request):
    """
    GET /core/api/feuille-presence/?seance_id=..&date=YYYY-MM-DD
    Retour:
      seance: infos
      eleves: liste + statut PRESENT/ABSENT/RETARD (calculé depuis Absence)
    """
    seance_id = request.GET.get("seance_id")
    date_str = request.GET.get("date")

    if not seance_id or not date_str:
        return JsonResponse({"error": "missing_params"}, status=400)

    try:
        d = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return JsonResponse({"error": "invalid_date"}, status=400)

    seance = get_object_or_404(
        Seance.objects.select_related("enseignant", "groupe", "annee"),
        id=seance_id
    )

    # élèves du groupe via inscriptions (année de la séance)
    inscriptions = (
        Inscription.objects
        .select_related("eleve")
        .filter(annee=seance.annee, groupe=seance.groupe)
        .order_by("eleve__nom", "eleve__prenom")
    )
    eleves = [i.eleve for i in inscriptions]

    # absences existantes pour cette date + séance
    abs_qs = Absence.objects.filter(
        annee=seance.annee,
        groupe=seance.groupe,
        seance=seance,
        date=d,
        eleve__in=eleves
    ).values("eleve_id", "type")

    abs_map = {row["eleve_id"]: row["type"] for row in abs_qs}

    # build response
    eleves_data = []
    for e in eleves:
        t = abs_map.get(e.id)
        if t == "RET":
            statut = "RETARD"
        elif t == "ABS":
            statut = "ABSENT"
        else:
            statut = "PRESENT"

        eleves_data.append({
            "id": e.id,
            "matricule": e.matricule,
            "nom": e.nom,
            "prenom": e.prenom,
            "statut": statut,
        })

    seance_data = {
        "id": seance.id,
        "date": d.isoformat(),
        "jour": seance.jour,
        "heure_debut": seance.heure_debut.strftime("%H:%M") if seance.heure_debut else "",
        "heure_fin": seance.heure_fin.strftime("%H:%M") if seance.heure_fin else "",
        "matiere": seance.matiere or "",
        "salle": seance.salle or "",
        "prof": f"{seance.enseignant.nom} {seance.enseignant.prenom}",
        "groupe": seance.groupe.nom,
        "annee_id": seance.annee_id,
    }

    return JsonResponse({"seance": seance_data, "eleves": eleves_data})


from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404
import json

@require_POST
@login_required
@group_required("SUPER_ADMIN", "ADMIN", "SCOLARITE", "PEDAGOGIQUE", "SECRETAIRE")
def api_feuille_presence_save(request):
    """
    POST JSON:
    {
      "seance_id": 15,
      "date": "2025-12-29",
      "items": [{"eleve_id":1,"statut":"PRESENT"|"ABSENT"|"RETARD"}, ...]
    }

    Règle:
    - PRESENT => supprime Absence si existe
    - ABSENT  => Absence(type="ABS") upsert
    - RETARD  => Absence(type="RET") upsert
    """

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"ok": False, "error": "invalid_json"}, status=400)

    seance_id = payload.get("seance_id")
    date_str  = payload.get("date")
    items     = payload.get("items", [])

    if not seance_id or not date_str or not isinstance(items, list):
        return JsonResponse({"ok": False, "error": "missing_params"}, status=400)

    try:
        d = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return JsonResponse({"ok": False, "error": "invalid_date"}, status=400)

    seance = get_object_or_404(
        Seance.objects.select_related("annee", "groupe"),
        id=seance_id
    )

    # ids élèves soumis
    eleve_ids = []
    for x in items:
        if x.get("eleve_id"):
            try:
                eleve_ids.append(int(x["eleve_id"]))
            except Exception:
                pass

    # sécurité: seulement élèves inscrits dans ce groupe/année
    allowed_ids = set(
        Inscription.objects.filter(
            annee=seance.annee,
            groupe=seance.groupe,
            eleve_id__in=eleve_ids
        ).values_list("eleve_id", flat=True)
    )

    saved = 0

    with transaction.atomic():
        for row in items:
            eleve_id = row.get("eleve_id")
            statut = (row.get("statut") or "PRESENT").upper().strip()

            if not eleve_id:
                continue
            try:
                eleve_id = int(eleve_id)
            except Exception:
                continue

            if eleve_id not in allowed_ids:
                continue

            # ✅ IMPORTANT : lookup aligné avec UniqueConstraint (eleve, date, seance)
            lookup = {"eleve_id": eleve_id, "date": d, "seance": seance}

            if statut == "PRESENT":
                Absence.objects.filter(**lookup).delete()
                saved += 1
                continue

            if statut == "ABSENT":
                Absence.objects.update_or_create(
                    **lookup,
                    defaults={
                        "annee": seance.annee,
                        "groupe": seance.groupe,
                        "type": "ABS",
                    }
                )
                saved += 1
                continue

            if statut == "RETARD":
                Absence.objects.update_or_create(
                    **lookup,
                    defaults={
                        "annee": seance.annee,
                        "groupe": seance.groupe,
                        "type": "RET",
                    }
                )
                saved += 1
                continue

            # statut inconnu => ignore

    return JsonResponse({"ok": True, "saved": saved})


@login_required
@group_required("SUPER_ADMIN", "ADMIN", "SCOLARITE", "PEDAGOGIQUE", "SECRETAIRE")
def absence_list(request):
    annee_active = AnneeScolaire.objects.filter(is_active=True).first()

    annee_id = request.GET.get("annee", "").strip()
    niveau_id = request.GET.get("niveau", "").strip()
    groupe_id = request.GET.get("groupe", "").strip()
    periode_id = request.GET.get("periode", "").strip()
    date_str = request.GET.get("date", "").strip()

    type_sel = request.GET.get("type", "").strip()
    q = request.GET.get("q", "").strip()

    if not annee_id and annee_active:
        annee_id = str(annee_active.id)

    absences = Absence.objects.select_related(
        "eleve", "groupe", "groupe__niveau", "groupe__niveau__degre",
        "seance", "seance__enseignant", "annee"
    )

    if annee_id:
        absences = absences.filter(annee_id=annee_id)

    if niveau_id:
        absences = absences.filter(groupe__niveau_id=niveau_id)

    if groupe_id:
        absences = absences.filter(groupe_id=groupe_id)

    if type_sel:
        absences = absences.filter(type=type_sel)

    if date_str:
        absences = absences.filter(date=date_str)

    # ✅ filtre période (2 modes)
    if periode_id:
        p = Periode.objects.filter(id=periode_id).first()
        if p and p.date_debut and p.date_fin:
            # meilleur : par dates
            absences = absences.filter(date__gte=p.date_debut, date__lte=p.date_fin)
        else:
            # fallback : via inscription.periode (si tes inscriptions ont la période)
            absences = absences.filter(
                eleve__inscriptions__annee_id=annee_id,
                eleve__inscriptions__periode_id=periode_id
            ).distinct()

    if q:
        absences = absences.filter(
            Q(eleve__matricule__icontains=q) |
            Q(eleve__nom__icontains=q) |
            Q(eleve__prenom__icontains=q)
        )

    annees = AnneeScolaire.objects.all()

    niveaux = Niveau.objects.select_related("degre").all()
    if annee_id:
        niveaux = niveaux.filter(groupes__annee_id=annee_id).distinct()

    groupes = Groupe.objects.select_related("niveau", "niveau__degre").all()
    if annee_id:
        groupes = groupes.filter(annee_id=annee_id)
    if niveau_id:
        groupes = groupes.filter(niveau_id=niveau_id)

    periodes = Periode.objects.all()
    if annee_id:
        periodes = periodes.filter(annee_id=annee_id)

    return render(request, "admin/absences/list.html", {
        "absences": absences,

        "annees": annees,
        "annee_selected": annee_id,

        "niveaux": niveaux,
        "niveau_selected": niveau_id,

        "groupes": groupes,
        "groupe_selected": groupe_id,

        "periodes": periodes,
        "periode_selected": periode_id,

        "date_selected": date_str,
        "type_selected": type_sel,
        "q": q,
    })


def _get_annee_active():
    return AnneeScolaire.objects.filter(is_active=True).first()

@login_required
@group_required("SUPER_ADMIN", "ADMIN", "SCOLARITE", "PEDAGOGIQUE", "SECRETAIRE")
def absence_create(request):
    annee_active = _get_annee_active()
    if not annee_active:
        messages.error(request, "⚠️ Aucune année scolaire active.")
        return redirect("core:absence_list")

    # ✅ Pré-remplissage depuis l'URL
    initial = {"annee": annee_active.id}
    if request.GET.get("groupe"):
        initial["groupe"] = request.GET.get("groupe")
    if request.GET.get("date"):
        initial["date"] = request.GET.get("date")
    if request.GET.get("seance"):
        initial["seance"] = request.GET.get("seance")

    if request.method == "POST":
        form = AbsenceForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)

            # ✅ sécurité : force année active
            obj.annee = annee_active

            obj.save()
            messages.success(request, "✅ Absence enregistrée.")
            return redirect("core:absence_list")
        # ✅ si invalid: on retombe sur le render avec erreurs
    else:
        form = AbsenceForm(initial=initial)

    return render(request, "admin/absences/form.html", {
        "form": form,
        "mode": "create",
        "annee_active": annee_active,
    })

@login_required
@group_required("SUPER_ADMIN", "ADMIN", "SCOLARITE", "PEDAGOGIQUE", "SECRETAIRE")
def absence_update(request, pk):
    a = get_object_or_404(Absence, pk=pk)
    if request.method == "POST":
        form = AbsenceForm(request.POST, instance=a)
        if form.is_valid():
            form.save()
            messages.success(request, "✅ Absence mise à jour.")
            return redirect("core:absence_list")
    else:
        form = AbsenceForm(instance=a)
    return render(request, "admin/absences/form.html", {"form": form, "mode": "update", "a": a})


@login_required
@group_required("SUPER_ADMIN", "ADMIN", "SCOLARITE", "PEDAGOGIQUE", "SECRETAIRE")
def absence_delete(request, pk):
    a = get_object_or_404(Absence, pk=pk)
    if request.method == "POST":
        a.delete()
        messages.success(request, "🗑️ Absence supprimée.")
        return redirect("core:absence_list")
    return render(request, "admin/absences/delete.html", {"a": a})

@login_required
@group_required("SUPER_ADMIN", "ADMIN", "SCOLARITE", "PEDAGOGIQUE", "SECRETAIRE")
def api_seances_par_groupe_date(request):
    """
    Retourne les séances (JSON) filtrées par annee + groupe + date.
    URL: /core/api/seances/?annee_id=..&groupe_id=..&date=YYYY-MM-DD
    """
    annee_id = request.GET.get("annee_id")
    groupe_id = request.GET.get("groupe_id")
    date_str = request.GET.get("date")

    if not (annee_id and groupe_id and date_str):
        return JsonResponse({"results": []})

    # mapping jour python -> code modèle
    # Monday=0 .. Sunday=6
    from datetime import datetime
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return JsonResponse({"results": []})

    jour_map = {0: "LUN", 1: "MAR", 2: "MER", 3: "JEU", 4: "VEN", 5: "SAM"}
    if d.weekday() not in jour_map:
        # dimanche = pas de séances
        return JsonResponse({"results": []})

    jour_code = jour_map[d.weekday()]

    seances = (
        Seance.objects
        .select_related("enseignant")
        .filter(annee_id=annee_id, groupe_id=groupe_id, jour=jour_code)
        .order_by("heure_debut")
    )

    data = []
    for s in seances:
        label = f"{s.heure_debut}-{s.heure_fin} — {s.enseignant.nom} {s.enseignant.prenom}"
        if s.matiere:
            label += f" — {s.matiere}"
        if s.salle:
            label += f" (Salle {s.salle})"
        data.append({"id": s.id, "label": label})

    return JsonResponse({"results": data})


@login_required
@group_required("SUPER_ADMIN", "ADMIN", "SCOLARITE", "PEDAGOGIQUE", "SECRETAIRE")
def absences_jour(request):
    from datetime import date as ddate

    annee_active = AnneeScolaire.objects.filter(is_active=True).first()
    annee_id = request.GET.get("annee", "")
    groupe_id = request.GET.get("groupe", "")
    date_str = request.GET.get("date", "")

    if not annee_id and annee_active:
        annee_id = str(annee_active.id)

    if not date_str:
        date_str = ddate.today().isoformat()

    absences = Absence.objects.select_related(
        "eleve", "groupe", "seance", "seance__enseignant"
    )
    if annee_id:
        absences = absences.filter(annee_id=annee_id)

    absences = absences.filter(date=date_str)
    if groupe_id:
        absences = absences.filter(groupe_id=groupe_id)

    annees = AnneeScolaire.objects.all()
    groupes = Groupe.objects.all()
    if annee_id:
        groupes = groupes.filter(annee_id=annee_id)

    return render(request, "admin/absences/jour.html", {
        "absences": absences,
        "annees": annees,
        "groupes": groupes,
        "annee_selected": annee_id,
        "groupe_selected": groupe_id,
        "date_selected": date_str,
    })
# ============================
# G1 — Parents + liens (Formset)
# ============================


from .models import Parent, AnneeScolaire, Niveau, Groupe  # + ParentEleve pas obligatoire ici

@login_required
@group_required("SUPER_ADMIN", "ADMIN", "SCOLARITE", "SECRETAIRE")
def parent_list(request):
    q = request.GET.get("q", "").strip()
    statut = request.GET.get("statut", "").strip()

    # ✅ nouveaux filtres
    annee_active = AnneeScolaire.objects.filter(is_active=True).first()
    annee_id = request.GET.get("annee", "").strip()
    niveau_id = request.GET.get("niveau", "").strip()
    groupe_id = request.GET.get("groupe", "").strip()

    parents = Parent.objects.all()

    # ✅ statut
    if statut == "actifs":
        parents = parents.filter(is_active=True)
    elif statut == "inactifs":
        parents = parents.filter(is_active=False)

    # ✅ recherche
    if q:
        parents = parents.filter(
            Q(nom__icontains=q) |
            Q(prenom__icontains=q) |
            Q(telephone__icontains=q) |
            Q(email__icontains=q)
        )

    # ✅ défaut: année active
    if not annee_id and annee_active:
        annee_id = str(annee_active.id)

    # ✅ filtres via enfants -> inscriptions
    if annee_id:
        parents = parents.filter(liens__eleve__inscriptions__annee_id=annee_id)

    if niveau_id:
        parents = parents.filter(liens__eleve__inscriptions__groupe__niveau_id=niveau_id)

    if groupe_id:
        parents = parents.filter(liens__eleve__inscriptions__groupe_id=groupe_id)

    # ✅ éviter doublons (un parent peut avoir plusieurs enfants)
    parents = parents.distinct()

    # ✅ dropdowns
    annees = AnneeScolaire.objects.all()

    niveaux = Niveau.objects.all()
    if annee_id:
        niveaux = niveaux.filter(groupes__annee_id=annee_id).distinct()

    groupes = Groupe.objects.all()
    if annee_id:
        groupes = groupes.filter(annee_id=annee_id)
    if niveau_id:
        groupes = groupes.filter(niveau_id=niveau_id)

    return render(request, "admin/parents/list.html", {
        "parents": parents,
        "q": q,
        "statut": statut,

        "annees": annees,
        "annee_selected": annee_id,
        "niveaux": niveaux,
        "niveau_selected": niveau_id,
        "groupes": groupes,
        "groupe_selected": groupe_id,
    })


@login_required
@group_required("SUPER_ADMIN", "ADMIN", "SCOLARITE", "SECRETAIRE")
def parent_detail(request, pk):
    p = get_object_or_404(Parent, pk=pk)
    liens = ParentEleve.objects.select_related("eleve").filter(parent=p)
    return render(request, "admin/parents/detail.html", {
        "p": p,
        "liens": liens,
    })


@login_required
@group_required("SUPER_ADMIN", "ADMIN", "SCOLARITE", "SECRETAIRE")
def parent_create(request):
    if request.method == "POST":
        form = ParentForm(request.POST)
        if form.is_valid():
            p = form.save()
            formset = ParentEleveFormSet(request.POST, instance=p)
            if formset.is_valid():
                formset.save()
                messages.success(request, "✅ Parent ajouté + liens enregistrés.")
                return redirect("core:parent_detail", pk=p.pk)
            else:
                # rollback propre si formset invalide
                p.delete()
        else:
            formset = ParentEleveFormSet(request.POST)
    else:
        form = ParentForm()
        formset = ParentEleveFormSet()

    return render(request, "admin/parents/form.html", {
        "form": form,
        "formset": formset,
        "mode": "create",
    })


@login_required
@group_required("SUPER_ADMIN", "ADMIN", "SCOLARITE", "SECRETAIRE")
def parent_update(request, pk):
    p = get_object_or_404(Parent, pk=pk)

    if request.method == "POST":
        form = ParentForm(request.POST, instance=p)
        formset = ParentEleveFormSet(request.POST, instance=p)

        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            messages.success(request, "✅ Parent mis à jour.")
            return redirect("core:parent_detail", pk=p.pk)
    else:
        form = ParentForm(instance=p)
        formset = ParentEleveFormSet(instance=p)

    return render(request, "admin/parents/form.html", {
        "form": form,
        "formset": formset,
        "mode": "update",
        "p": p,
    })


@login_required
@group_required("SUPER_ADMIN", "ADMIN")
def parent_delete(request, pk):
    p = get_object_or_404(Parent, pk=pk)
    if request.method == "POST":
        p.delete()
        messages.success(request, "🗑️ Parent supprimé.")
        return redirect("core:parent_list")
    return render(request, "admin/parents/delete.html", {"p": p})


#================================================================

from .pdf_utils import paiement_recu_pdf, paiement_recu_batch_pdf

@login_required
@group_required("SUPER_ADMIN", "ADMIN", "COMPTABLE")
def paiement_recu_pdf_auto(request, pk: int):
    p = get_object_or_404(
        Paiement.objects.select_related(
            "inscription", "inscription__eleve", "inscription__annee",
            "inscription__groupe", "inscription__groupe__niveau", "inscription__groupe__niveau__degre",
            "echeance"
        ),
        pk=pk
    )

    # total payé (inscription) + reste (global)
    total_paye = p.inscription.paiements.aggregate(
        s=Coalesce(Sum("montant"), Decimal("0.00"), output_field=DecimalField(max_digits=10, decimal_places=2))
    )["s"] or Decimal("0.00")

    reste = p.inscription.total_reste  # (tu as déjà la property)

    # ✅ Si batch => PDF batch
    if p.batch_token:
        qs = (
            Paiement.objects
            .select_related("echeance", "inscription", "inscription__eleve", "inscription__annee", "inscription__groupe")
            .filter(batch_token=p.batch_token)
            .order_by("echeance__mois_index", "id")
        )
        if not qs.exists():
            raise Http404("Batch introuvable")

        total_batch = sum((x.montant or Decimal("0.00")) for x in qs)
        first = qs.first()
        return paiement_recu_batch_pdf(first, qs, total_batch, p.batch_token)

    # ✅ Sinon => PDF single
    return paiement_recu_pdf(p, total_paye, reste)



@login_required
@group_required("SUPER_ADMIN", "ADMIN", "SCOLARITE")
def absences_jour_pdf_view(request):
    annee_active = AnneeScolaire.objects.filter(is_active=True).first()
    annee_id = request.GET.get("annee", "") or (str(annee_active.id) if annee_active else "")
    groupe_id = request.GET.get("groupe", "")
    date_str = request.GET.get("date", "")

    absences = Absence.objects.select_related("eleve", "groupe", "seance", "seance__enseignant")
    annee_obj = None
    groupe_label = ""

    if annee_id:
        absences = absences.filter(annee_id=annee_id)
        annee_obj = AnneeScolaire.objects.filter(id=annee_id).first()

    if date_str:
        absences = absences.filter(date=date_str)

    if groupe_id:
        absences = absences.filter(groupe_id=groupe_id)
        g = Groupe.objects.select_related("niveau", "niveau__degre").filter(id=groupe_id).first()
        if g:
            groupe_label = f"{g.niveau.degre.nom}/{g.niveau.nom}/{g.nom}"

    return pdf_utils.absences_jour_pdf(date_str or "—", annee_obj, groupe_label, absences.order_by("eleve__nom"))


@login_required
@group_required("SUPER_ADMIN", "ADMIN", "COMPTABLE")
def impayes_pdf_view(request):
    annee_active = AnneeScolaire.objects.filter(is_active=True).first()
    annee_id = request.GET.get("annee", "") or (str(annee_active.id) if annee_active else "")

    inscriptions = Inscription.objects.select_related(
        "eleve", "annee", "groupe", "groupe__niveau", "groupe__niveau__degre"
    )

    annee_obj = None
    if annee_id:
        inscriptions = inscriptions.filter(annee_id=annee_id)
        annee_obj = AnneeScolaire.objects.filter(id=annee_id).first()


    inscriptions = inscriptions.annotate(
        total_paye=Coalesce(
            Sum("paiements__montant"),
            Decimal("0.00"),
            output_field=DecimalField(max_digits=10, decimal_places=2),
        )
    ).annotate(
        reste=ExpressionWrapper(
            Coalesce(F("montant_total"), Decimal("0.00")) - Coalesce(F("total_paye"), Decimal("0.00")),
            output_field=DecimalField(max_digits=10, decimal_places=2),
        )
    ).filter(
        reste__gt=Decimal("0.00")
    )

    total_du = inscriptions.aggregate(
        s=Coalesce(Sum("montant_total"), Decimal("0.00"),
                output_field=DecimalField(max_digits=10, decimal_places=2))
    )["s"]

    total_encaisse = inscriptions.aggregate(
        s=Coalesce(Sum("paiements__montant"), Decimal("0.00"),
                output_field=DecimalField(max_digits=10, decimal_places=2))
    )["s"]

    total_impaye = inscriptions.aggregate(
        s=Coalesce(Sum("reste"), Decimal("0.00"),
                output_field=DecimalField(max_digits=10, decimal_places=2))
    )["s"]

    return pdf_utils.impayes_pdf(annee_obj, inscriptions, total_du, total_encaisse, total_impaye)


@login_required
@group_required("SUPER_ADMIN", "ADMIN", "SCOLARITE")
def eleves_pdf_view(request):
    q = request.GET.get("q", "").strip()
    statut = request.GET.get("statut", "")

    eleves = Eleve.objects.all()

    if statut == "actifs":
        eleves = eleves.filter(is_active=True)
    elif statut == "inactifs":
        eleves = eleves.filter(is_active=False)

    if q:
        eleves = eleves.filter(
            Q(matricule__icontains=q) |
            Q(nom__icontains=q) |
            Q(prenom__icontains=q) |
            Q(telephone__icontains=q)
        )

    title = f"Filtre: q={q or '—'} / statut={statut or '—'}"
    return pdf_utils.eleves_list_pdf(title, eleves.order_by("nom", "prenom"))

@login_required
@group_required("SUPER_ADMIN", "ADMIN", "SCOLARITE")
def eleves_excel_export(request):
    q = request.GET.get("q", "").strip()
    statut = request.GET.get("statut", "")

    qs = Eleve.objects.all()

    if statut == "actifs":
        qs = qs.filter(is_active=True)
    elif statut == "inactifs":
        qs = qs.filter(is_active=False)

    if q:
        qs = qs.filter(
            Q(matricule__icontains=q) |
            Q(nom__icontains=q) |
            Q(prenom__icontains=q) |
            Q(telephone__icontains=q)
        )

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Eleves"

    headers = ["matricule", "nom", "prenom", "telephone", "is_active"]
    ws.append(headers)

    # style header
    for col in range(1, len(headers)+1):
        cell = ws.cell(row=1, column=col)
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal="center")

    for e in qs.order_by("nom", "prenom"):
        ws.append([e.matricule, e.nom, e.prenom, e.telephone or "", "1" if e.is_active else "0"])

    # auto width simple
    for col in ws.columns:
        max_len = 0
        col_letter = col[0].column_letter
        for cell in col:
            val = str(cell.value) if cell.value is not None else ""
            max_len = max(max_len, len(val))
        ws.column_dimensions[col_letter].width = min(max_len + 2, 40)

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = 'attachment; filename="eleves.xlsx"'
    wb.save(response)
    return response

@login_required
@group_required("SUPER_ADMIN", "ADMIN", "SCOLARITE")
def eleves_excel_import(request):
    """
    Import Excel format:
    matricule | nom | prenom | telephone | is_active(1/0)
    """
    errors = []
    created = 0
    updated = 0

    if request.method == "POST":
        f = request.FILES.get("file")
        if not f:
            messages.error(request, "⚠️ Aucun fichier uploadé.")
            return redirect("core:eleve_list")

        try:
            wb = openpyxl.load_workbook(f)
            ws = wb.active
        except Exception:
            messages.error(request, "⚠️ Fichier Excel invalide.")
            return redirect("core:eleve_list")

        # headers
        headers = [str(c.value).strip().lower() if c.value else "" for c in ws[1]]
        expected = ["matricule", "nom", "prenom", "telephone", "is_active"]
        if headers[:5] != expected:
            messages.error(request, f"⚠️ Colonnes attendues: {expected}")
            return redirect("core:eleve_list")

        for idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
            matricule, nom, prenom, telephone, is_active = row[:5]

            if not matricule or not nom or not prenom:
                errors.append(f"Ligne {idx}: matricule/nom/prenom obligatoire.")
                continue

            matricule = str(matricule).strip()
            nom = str(nom).strip()
            prenom = str(prenom).strip()
            telephone = str(telephone).strip() if telephone else ""
            is_active = str(is_active).strip() if is_active is not None else "1"
            active_bool = True if is_active in ["1", "true", "True", "OUI", "oui", "YES", "yes"] else False

            obj, created_flag = Eleve.objects.update_or_create(
                matricule=matricule,
                defaults={
                    "nom": nom,
                    "prenom": prenom,
                    "telephone": telephone,
                    "is_active": active_bool,
                }
            )

            if created_flag:
                created += 1
            else:
                updated += 1

        if errors:
            messages.warning(request, f"⚠️ Import terminé avec erreurs ({len(errors)}).")
        messages.success(request, f"✅ Import terminé: {created} créés / {updated} mis à jour.")
        # On affiche erreurs dans une page dédiée
        return render(request, "admin/eleves/import_result.html", {
            "errors": errors,
            "created": created,
            "updated": updated,
        })

    # GET -> page upload
    return render(request, "admin/eleves/import.html")

@login_required
@group_required("SUPER_ADMIN", "ADMIN", "SCOLARITE")
def parents_excel_export(request):
    wb = openpyxl.Workbook()

    # Feuille Parents
    ws1 = wb.active
    ws1.title = "Parents"
    headers1 = ["parent_id", "nom", "prenom", "telephone", "email", "adresse", "is_active"]
    ws1.append(headers1)
    for col in range(1, len(headers1)+1):
        c = ws1.cell(row=1, column=col)
        c.font = Font(bold=True)
        c.alignment = Alignment(horizontal="center")

    for p in Parent.objects.order_by("nom", "prenom"):
        ws1.append([
            p.id,
            p.nom,
            p.prenom,
            p.telephone or "",
            p.email or "",
            p.adresse or "",
            "1" if p.is_active else "0",
        ])

    # Feuille Liens
    ws2 = wb.create_sheet("Liens")
    headers2 = ["parent_id", "parent_email", "eleve_matricule", "lien"]
    ws2.append(headers2)
    for col in range(1, len(headers2)+1):
        c = ws2.cell(row=1, column=col)
        c.font = Font(bold=True)
        c.alignment = Alignment(horizontal="center")

    liens = ParentEleve.objects.select_related("parent", "eleve").order_by("parent_id")
    for l in liens:
        ws2.append([
            l.parent.id,
            l.parent.email or "",
            l.eleve.matricule,
            l.lien
        ])

    # widths simple
    for ws in [ws1, ws2]:
        for col in ws.columns:
            max_len = 0
            col_letter = col[0].column_letter
            for cell in col:
                val = str(cell.value) if cell.value is not None else ""
                max_len = max(max_len, len(val))
            ws.column_dimensions[col_letter].width = min(max_len + 2, 45)

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = 'attachment; filename="parents_liens.xlsx"'
    wb.save(response)
    return response


@login_required
@group_required("SUPER_ADMIN", "ADMIN", "SCOLARITE")
def parents_excel_import(request):
    errors = []
    parents_created = 0
    parents_updated = 0
    liens_created = 0

    if request.method == "POST":
        f = request.FILES.get("file")
        if not f:
            messages.error(request, "⚠️ Aucun fichier uploadé.")
            return redirect("core:parent_list")

        try:
            wb = openpyxl.load_workbook(f)
        except Exception:
            messages.error(request, "⚠️ Fichier Excel invalide.")
            return redirect("core:parent_list")

        if "Parents" not in wb.sheetnames or "Liens" not in wb.sheetnames:
            messages.error(request, "⚠️ Le fichier doit contenir 2 feuilles: Parents + Liens.")
            return redirect("core:parent_list")

        ws1 = wb["Parents"]
        ws2 = wb["Liens"]

        # ---- Parents ----
        headers1 = [str(c.value).strip().lower() if c.value else "" for c in ws1[1]]
        expected1 = ["parent_id", "nom", "prenom", "telephone", "email", "adresse", "is_active"]
        if headers1[:7] != expected1:
            messages.error(request, f"⚠️ Feuille Parents: colonnes attendues {expected1}")
            return redirect("core:parent_list")

        # mapping utile (email -> parent, id -> parent)
        parent_by_email = {}
        parent_by_id = {}

        for idx, row in enumerate(ws1.iter_rows(min_row=2, values_only=True), start=2):
            parent_id, nom, prenom, telephone, email, adresse, is_active = row[:7]

            if not nom or not prenom:
                errors.append(f"Parents ligne {idx}: nom/prenom obligatoires.")
                continue

            nom = str(nom).strip()
            prenom = str(prenom).strip()
            telephone = str(telephone).strip() if telephone else ""
            email = str(email).strip() if email else ""
            adresse = str(adresse).strip() if adresse else ""
            is_active = str(is_active).strip() if is_active is not None else "1"
            active_bool = True if is_active in ["1", "true", "True", "OUI", "oui", "YES", "yes"] else False

            # règle: si parent_id fourni -> update_or_create sur id
            if parent_id:
                try:
                    pid = int(parent_id)
                except Exception:
                    errors.append(f"Parents ligne {idx}: parent_id invalide.")
                    continue

                obj = Parent.objects.filter(id=pid).first()
                if obj:
                    obj.nom = nom
                    obj.prenom = prenom
                    obj.telephone = telephone
                    obj.email = email
                    obj.adresse = adresse
                    obj.is_active = active_bool
                    obj.save()
                    parents_updated += 1
                else:
                    obj = Parent.objects.create(
                        id=pid,
                        nom=nom, prenom=prenom,
                        telephone=telephone, email=email, adresse=adresse,
                        is_active=active_bool
                    )
                    parents_created += 1
            else:
                # sinon, si email existe -> update_or_create par email (sinon create simple)
                if email:
                    obj, created_flag = Parent.objects.update_or_create(
                        email=email,
                        defaults={
                            "nom": nom,
                            "prenom": prenom,
                            "telephone": telephone,
                            "adresse": adresse,
                            "is_active": active_bool,
                        }
                    )
                    parents_created += 1 if created_flag else 0
                    parents_updated += 0 if created_flag else 1
                else:
                    obj = Parent.objects.create(
                        nom=nom, prenom=prenom,
                        telephone=telephone, email=email, adresse=adresse,
                        is_active=active_bool
                    )
                    parents_created += 1

            if obj.email:
                parent_by_email[obj.email.lower()] = obj
            parent_by_id[obj.id] = obj

        # ---- Liens ----
        headers2 = [str(c.value).strip().lower() if c.value else "" for c in ws2[1]]
        expected2 = ["parent_id", "parent_email", "eleve_matricule", "lien"]
        if headers2[:4] != expected2:
            messages.error(request, f"⚠️ Feuille Liens: colonnes attendues {expected2}")
            return redirect("core:parent_list")

        for idx, row in enumerate(ws2.iter_rows(min_row=2, values_only=True), start=2):
            parent_id, parent_email, eleve_matricule, lien = row[:4]

            eleve_matricule = str(eleve_matricule).strip() if eleve_matricule else ""
            lien = str(lien).strip().upper() if lien else ""

            if not eleve_matricule or not lien:
                errors.append(f"Liens ligne {idx}: eleve_matricule et lien obligatoires.")
                continue

            if lien not in ["PERE", "MERE", "TUTEUR", "AUTRE"]:
                errors.append(f"Liens ligne {idx}: lien invalide ({lien}).")
                continue

            # retrouver parent
            parent_obj = None
            if parent_id:
                try:
                    parent_obj = parent_by_id.get(int(parent_id)) or Parent.objects.filter(id=int(parent_id)).first()
                except Exception:
                    parent_obj = None

            if not parent_obj and parent_email:
                pe = str(parent_email).strip().lower()
                parent_obj = parent_by_email.get(pe) or Parent.objects.filter(email__iexact=pe).first()

            if not parent_obj:
                errors.append(f"Liens ligne {idx}: parent introuvable (id/email).")
                continue

            eleve = Eleve.objects.filter(matricule=eleve_matricule).first()
            if not eleve:
                errors.append(f"Liens ligne {idx}: élève introuvable ({eleve_matricule}).")
                continue

            obj, created_flag = ParentEleve.objects.update_or_create(
                parent=parent_obj,
                eleve=eleve,
                defaults={"lien": lien}
            )
            if created_flag:
                liens_created += 1

        if errors:
            messages.warning(request, f"⚠️ Import terminé avec erreurs ({len(errors)}).")
        messages.success(
            request,
            f"✅ Import terminé: Parents {parents_created} créés / {parents_updated} mis à jour — Liens ajoutés {liens_created}"
        )

        return render(request, "admin/parents/import_result.html", {
            "errors": errors,
            "parents_created": parents_created,
            "parents_updated": parents_updated,
            "liens_created": liens_created,
        })

    return render(request, "admin/parents/import.html")

@login_required
@group_required("SUPER_ADMIN", "ADMIN", "SCOLARITE")
def inscriptions_excel_export(request):
    annee_active = AnneeScolaire.objects.filter(is_active=True).first()
    annee_id = request.GET.get("annee", "") or (str(annee_active.id) if annee_active else "")

    qs = Inscription.objects.select_related(
        "eleve", "annee", "groupe", "groupe__niveau", "groupe__niveau__degre"
    )

    if annee_id:
        qs = qs.filter(annee_id=annee_id)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Inscriptions"

    headers = ["eleve_matricule", "annee_nom", "groupe_nom", "montant_total"]
    ws.append(headers)

    for col in range(1, len(headers)+1):
        c = ws.cell(row=1, column=col)
        c.font = Font(bold=True)
        c.alignment = Alignment(horizontal="center")

    for insc in qs.order_by("eleve__nom", "eleve__prenom"):
        ws.append([
            insc.eleve.matricule,
            insc.annee.nom,
            insc.groupe.nom,
            str(insc.montant_total or ""),
        ])

    for col in ws.columns:
        max_len = 0
        col_letter = col[0].column_letter
        for cell in col:
            val = str(cell.value) if cell.value is not None else ""
            max_len = max(max_len, len(val))
        ws.column_dimensions[col_letter].width = min(max_len + 2, 45)

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = 'attachment; filename="inscriptions.xlsx"'
    wb.save(response)
    return response


@login_required
@group_required("SUPER_ADMIN", "ADMIN", "SCOLARITE")
def inscriptions_excel_import(request):
    errors = []
    created = 0
    updated = 0

    if request.method == "POST":
        f = request.FILES.get("file")
        if not f:
            messages.error(request, "⚠️ Aucun fichier uploadé.")
            return redirect("core:inscription_list")

        try:
            wb = openpyxl.load_workbook(f)
            ws = wb.active
        except Exception:
            messages.error(request, "⚠️ Fichier Excel invalide.")
            return redirect("core:inscription_list")

        headers = [str(c.value).strip().lower() if c.value else "" for c in ws[1]]
        expected = ["eleve_matricule", "annee_nom", "groupe_nom", "montant_total"]
        if headers[:4] != expected:
            messages.error(request, f"⚠️ Colonnes attendues: {expected}")
            return redirect("core:inscription_list")

        for idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
            eleve_matricule, annee_nom, groupe_nom, montant_total = row[:4]

            eleve_matricule = str(eleve_matricule).strip() if eleve_matricule else ""
            annee_nom = str(annee_nom).strip() if annee_nom else ""
            groupe_nom = str(groupe_nom).strip() if groupe_nom else ""
            montant_total = str(montant_total).strip() if montant_total is not None else ""

            if not eleve_matricule or not annee_nom or not groupe_nom or not montant_total:
                errors.append(f"Ligne {idx}: champs obligatoires manquants.")
                continue

            eleve = Eleve.objects.filter(matricule=eleve_matricule).first()
            if not eleve:
                errors.append(f"Ligne {idx}: élève introuvable ({eleve_matricule}).")
                continue

            annee = AnneeScolaire.objects.filter(nom=annee_nom).first()
            if not annee:
                errors.append(f"Ligne {idx}: année introuvable ({annee_nom}).")
                continue

            groupe = Groupe.objects.filter(annee=annee, nom=groupe_nom).first()
            if not groupe:
                errors.append(f"Ligne {idx}: groupe introuvable ({groupe_nom}) pour année {annee_nom}.")
                continue

            try:
                mt = Decimal(montant_total)
            except Exception:
                errors.append(f"Ligne {idx}: montant_total invalide ({montant_total}).")
                continue

            obj, created_flag = Inscription.objects.update_or_create(
                eleve=eleve,
                annee=annee,
                defaults={
                    "groupe": groupe,
                    "montant_total": mt,
                }
            )

            if created_flag:
                created += 1
            else:
                updated += 1

        if errors:
            messages.warning(request, f"⚠️ Import terminé avec erreurs ({len(errors)}).")
        messages.success(request, f"✅ Import terminé: {created} créées / {updated} mises à jour.")

        return render(request, "admin/inscriptions/import_result.html", {
            "errors": errors,
            "created": created,
            "updated": updated,
        })

    return render(request, "admin/inscriptions/import.html")


@login_required
@group_required("SUPER_ADMIN", "ADMIN", "COMPTABLE")
def paiements_excel_export(request):
    annee_active = AnneeScolaire.objects.filter(is_active=True).first()
    annee_id = request.GET.get("annee", "") or (str(annee_active.id) if annee_active else "")

    qs = Paiement.objects.select_related(
        "inscription", "inscription__eleve", "inscription__annee"
    )

    if annee_id:
        qs = qs.filter(inscription__annee_id=annee_id)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Paiements"

    headers = ["eleve_matricule", "annee_nom", "date_paiement", "montant", "mode", "reference"]
    ws.append(headers)

    for col in range(1, len(headers)+1):
        c = ws.cell(row=1, column=col)
        c.font = Font(bold=True)
        c.alignment = Alignment(horizontal="center")

    for p in qs.order_by("-date_paiement", "-id"):
        # champs optionnels
        mode = getattr(p, "mode", "") or ""
        reference = getattr(p, "reference", "") or ""
        date_val = getattr(p, "date_paiement", None)
        date_str = date_val.strftime("%Y-%m-%d") if date_val else ""
        ws.append([
            p.inscription.eleve.matricule,
            p.inscription.annee.nom,
            date_str,
            str(p.montant),
            mode,
            reference,
        ])

    for col in ws.columns:
        max_len = 0
        col_letter = col[0].column_letter
        for cell in col:
            val = str(cell.value) if cell.value is not None else ""
            max_len = max(max_len, len(val))
        ws.column_dimensions[col_letter].width = min(max_len + 2, 45)

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = 'attachment; filename="paiements.xlsx"'
    wb.save(response)
    return response


@login_required
@group_required("SUPER_ADMIN", "ADMIN", "COMPTABLE")
def paiements_excel_import(request):
    errors = []
    created = 0

    if request.method == "POST":
        f = request.FILES.get("file")
        if not f:
            messages.error(request, "⚠️ Aucun fichier uploadé.")
            return redirect("core:paiement_list")

        try:
            wb = openpyxl.load_workbook(f)
            ws = wb.active
        except Exception:
            messages.error(request, "⚠️ Fichier Excel invalide.")
            return redirect("core:paiement_list")

        headers = [str(c.value).strip().lower() if c.value else "" for c in ws[1]]
        expected = ["eleve_matricule", "annee_nom", "date_paiement", "montant", "mode", "reference"]
        if headers[:6] != expected:
            messages.error(request, f"⚠️ Colonnes attendues: {expected}")
            return redirect("core:paiement_list")

        for idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
            eleve_matricule, annee_nom, date_paiement, montant, mode, reference = row[:6]

            eleve_matricule = str(eleve_matricule).strip() if eleve_matricule else ""
            annee_nom = str(annee_nom).strip() if annee_nom else ""
            mode = str(mode).strip() if mode else ""
            reference = str(reference).strip() if reference else ""

            if not eleve_matricule or not annee_nom or not date_paiement or montant is None:
                errors.append(f"Ligne {idx}: champs obligatoires manquants.")
                continue

            eleve = Eleve.objects.filter(matricule=eleve_matricule).first()
            if not eleve:
                errors.append(f"Ligne {idx}: élève introuvable ({eleve_matricule}).")
                continue

            annee = AnneeScolaire.objects.filter(nom=annee_nom).first()
            if not annee:
                errors.append(f"Ligne {idx}: année introuvable ({annee_nom}).")
                continue

            insc = Inscription.objects.filter(eleve=eleve, annee=annee).first()
            if not insc:
                errors.append(f"Ligne {idx}: inscription introuvable pour {eleve_matricule} / {annee_nom}.")
                continue

            # parse date
            try:
                if isinstance(date_paiement, str):
                    dp = datetime.strptime(date_paiement.strip(), "%Y-%m-%d").date()
                else:
                    dp = date_paiement  # openpyxl peut fournir un datetime/date
                    if hasattr(dp, "date"):
                        dp = dp.date()
            except Exception:
                errors.append(f"Ligne {idx}: date_paiement invalide ({date_paiement}). Utilise YYYY-MM-DD.")
                continue

            # parse montant
            try:
                mt = Decimal(str(montant).strip())
            except Exception:
                errors.append(f"Ligne {idx}: montant invalide ({montant}).")
                continue

            p = Paiement.objects.create(
                inscription=insc,
                montant=mt,
                date_paiement=dp,
            )

            # champs optionnels (si existent)
            if hasattr(p, "mode"):
                p.mode = mode
            if hasattr(p, "reference"):
                p.reference = reference
            p.save()

            created += 1

        if errors:
            messages.warning(request, f"⚠️ Import terminé avec erreurs ({len(errors)}).")
        messages.success(request, f"✅ Import terminé: {created} paiements créés.")

        return render(request, "admin/paiements/import_result.html", {
            "errors": errors,
            "created": created,
        })

    return render(request, "admin/paiements/import.html")
# ============================
# O1 — Notes & Evaluations
# ============================




@login_required
@group_required("ADMIN", "SCOLARITE")
def matiere_list(request):
    degre_id = request.GET.get("degre", "")
    niveau_id = request.GET.get("niveau", "")

    matieres = Matiere.objects.prefetch_related("niveaux", "enseignants").all()

    if niveau_id:
        matieres = matieres.filter(niveaux__id=niveau_id)
    elif degre_id:
        matieres = matieres.filter(niveaux__degre_id=degre_id)

    degres = Degre.objects.all().order_by("ordre", "nom")
    niveaux = Niveau.objects.select_related("degre").all().order_by("degre__ordre", "ordre", "nom")

    if degre_id:
        niveaux = niveaux.filter(degre_id=degre_id)

    return render(request, "admin/matieres/list.html", {
        "matieres": matieres.distinct().order_by("nom"),
        "degres": degres,
        "niveaux": niveaux,
        "degre_selected": degre_id,
        "niveau_selected": niveau_id,
    })



@login_required
@group_required("ADMIN", "SCOLARITE")
def matiere_create(request):
    if request.method == "POST":
        form = MatiereForm(request.POST)
        if form.is_valid():
            matiere = form.save()

            transaction.on_commit(lambda: sync_enseignant_groupe_from_matiere(matiere))

            messages.success(request, "✅ Matière ajoutée.")
            return redirect("core:matiere_list")
    else:
        form = MatiereForm()

    return render(request, "admin/matieres/form.html", {"form": form, "mode": "create"})


@login_required
@group_required("ADMIN", "SCOLARITE")
def matiere_update(request, pk):
    matiere = get_object_or_404(Matiere, pk=pk)

    if request.method == "POST":
        form = MatiereForm(request.POST, instance=matiere)
        if form.is_valid():
            matiere = form.save()

            transaction.on_commit(lambda: sync_enseignant_groupe_from_matiere(matiere))

            messages.success(request, "✅ Matière modifiée.")
            return redirect("core:matiere_list")
    else:
        form = MatiereForm(instance=matiere)

    return render(request, "admin/matieres/form.html", {"form": form, "mode": "update", "matiere": matiere})

@login_required
@group_required("ADMIN", "SCOLARITE")
def matiere_delete(request, pk):
    matiere = get_object_or_404(Matiere, pk=pk)

    if request.method == "POST":
        # ✅ Soft delete : on désactive au lieu de supprimer
        matiere.is_active = False
        matiere.save(update_fields=["is_active"])
        messages.success(request, "✅ Matière désactivée (historique conservé).")
        return redirect("core:matiere_list")

    return render(request, "admin/matieres/delete.html", {
        "matiere": matiere
    })


# core/views_notes.py (ou core/views.py selon ton projet)

from .models import (
    AnneeScolaire, Niveau, Groupe, Periode,
    Matiere, Enseignant, Evaluation, EnseignantGroupe
)


# =========================
# AJAX — Élèves par groupe (pour Communication / SMS)
# =========================

@login_required
def ajax_eleves_par_groupe(request):
    """
    Retourne les élèves liés au groupe via Inscription.
    Params:
      - groupe_id
    """
    groupe_id = request.GET.get("groupe_id")
    if not groupe_id:
        return JsonResponse({"results": []})

    qs = (
        Eleve.objects
        .filter(inscriptions__groupe_id=groupe_id)
        .distinct()
        .order_by("nom", "prenom")
        .values("id", "matricule", "nom", "prenom")
    )

    results = [
        {
            "id": e["id"],
            "label": f'{e["matricule"] or ""} — {e["nom"]} {e["prenom"]}'.strip()
        }
        for e in qs
    ]
    return JsonResponse({"results": results})


@login_required
@require_GET
def ajax_enseignants(request):
    """
    ADMIN: Enseignants en cascade:
    - annee + groupe => enseignants affectés au groupe (EnseignantGroupe)
    Retour: {"results":[{"id":..,"label":"..."}]}
    """
    annee_id = (request.GET.get("annee") or "").strip()
    groupe_id = (request.GET.get("groupe") or request.GET.get("groupe_id") or "").strip()

    # fallback année active
    if not annee_id:
        annee_active = AnneeScolaire.objects.filter(is_active=True).first()
        annee_id = str(annee_active.id) if annee_active else ""

    if not (annee_id and groupe_id and groupe_id.isdigit()):
        return JsonResponse({"results": []})

    # sécurité cohérence année (optionnel mais propre)
    g = Groupe.objects.filter(id=groupe_id).values("id", "annee_id").first()
    if not g or (annee_id and str(g["annee_id"]) != str(annee_id)):
        return JsonResponse({"results": []})

    ens_qs = (
        Enseignant.objects
        .filter(is_active=True)
        .filter(
            id__in=(
                EnseignantGroupe.objects
                .filter(annee_id=annee_id, groupe_id=groupe_id)
                .values_list("enseignant_id", flat=True)
                .distinct()
            )
        )
        .order_by("nom", "prenom")
    )

    data = [{
        "id": e.id,
        "label": f"{e.matricule or ''} — {e.nom} {e.prenom}".strip(" —")
    } for e in ens_qs]

    return JsonResponse({"results": data})

@login_required
@require_GET
def ajax_matieres(request):
    """
    ADMIN: Matières en cascade:
    - si (annee + groupe + enseignant) => matières exactes via EnseignantGroupe.matiere_fk
    - sinon si groupe => matières du niveau du groupe
    - sinon si niveau => matières du niveau
    """
    annee_id = (request.GET.get("annee") or "").strip()
    groupe_id = (request.GET.get("groupe") or request.GET.get("groupe_id") or "").strip()
    niveau_id = (request.GET.get("niveau") or "").strip()
    enseignant_id = (request.GET.get("enseignant") or "").strip()

    # fallback année active
    if not annee_id:
        annee_active = AnneeScolaire.objects.filter(is_active=True).first()
        annee_id = str(annee_active.id) if annee_active else ""

    qs = Matiere.objects.filter(is_active=True)

    # ✅ CAS 1: enseignant + groupe + annee => matières exactes (AZ)
    if annee_id and groupe_id and enseignant_id and groupe_id.isdigit() and enseignant_id.isdigit():
        matiere_ids = (
            EnseignantGroupe.objects
            .filter(
                annee_id=annee_id,
                groupe_id=groupe_id,
                enseignant_id=enseignant_id,
                matiere_fk__isnull=False,
            )
            .values_list("matiere_fk_id", flat=True)
            .distinct()
        )

        qs = qs.filter(id__in=matiere_ids).order_by("nom")
        return JsonResponse({"results": [{"id": m.id, "label": m.nom} for m in qs]})

    # ✅ CAS 2: groupe => matières du niveau du groupe
    if groupe_id and groupe_id.isdigit():
        g = Groupe.objects.select_related("annee", "niveau").filter(id=groupe_id).first()
        if not g or not g.niveau_id:
            return JsonResponse({"results": []})

        # sécurité cohérence année
        if annee_id and str(g.annee_id) != str(annee_id):
            return JsonResponse({"results": []})

        qs = qs.filter(niveaux=g.niveau).distinct().order_by("nom")
        return JsonResponse({"results": [{"id": m.id, "label": m.nom} for m in qs]})

    # ✅ CAS 3: niveau => matières du niveau
    if niveau_id and niveau_id.isdigit():
        qs = qs.filter(niveaux__id=niveau_id).distinct().order_by("nom")
        return JsonResponse({"results": [{"id": m.id, "label": m.nom} for m in qs]})

    return JsonResponse({"results": []})


@login_required
@group_required("ADMIN", "SCOLARITE")
def evaluation_list(request):
    annee_active = AnneeScolaire.objects.filter(is_active=True).first()
    annee_id = request.GET.get("annee", "") or (str(annee_active.id) if annee_active else "")

    # ✅ filtres GET
    date_str = (request.GET.get("date") or "").strip()      # YYYY-MM-DD
    niveau_id = (request.GET.get("niveau") or "").strip()
    groupe_id = (request.GET.get("groupe") or "").strip()
    enseignant_id = (request.GET.get("enseignant") or "").strip()
    matiere_id = (request.GET.get("matiere") or "").strip()
    periode_id = (request.GET.get("periode") or "").strip()

    # ✅ Si groupe choisi => force niveau cohérent
    groupe_obj = None
    if groupe_id:
        groupe_obj = (
            Groupe.objects
            .select_related("niveau", "niveau__degre", "annee")
            .filter(id=groupe_id)
            .first()
        )
        if groupe_obj:
            niveau_id = str(groupe_obj.niveau_id)

    # =========================
    # Query Evaluations
    # =========================
    qs = Evaluation.objects.select_related(
        "matiere", "enseignant",
        "periode", "periode__annee",
        "groupe", "groupe__niveau", "groupe__niveau__degre"
    )

    # année via période
    if annee_id:
        qs = qs.filter(periode__annee_id=annee_id)

    # date exacte
    if date_str:
        try:
            d = datetime.strptime(date_str, "%Y-%m-%d").date()
            qs = qs.filter(date=d)
        except ValueError:
            qs = qs.none()

    if periode_id:
        qs = qs.filter(periode_id=periode_id)

    if niveau_id:
        qs = qs.filter(groupe__niveau_id=niveau_id)

    if groupe_id:
        qs = qs.filter(groupe_id=groupe_id)

    if enseignant_id:
        qs = qs.filter(enseignant_id=enseignant_id)

    if matiere_id:
        qs = qs.filter(matiere_id=matiere_id)

    # =========================
    # Dropdowns (listes filtres)
    # =========================
    annees = AnneeScolaire.objects.all()

    niveaux = Niveau.objects.select_related("degre").all()
    if annee_id:
        niveaux = niveaux.filter(groupes__annee_id=annee_id).distinct()

    groupes = Groupe.objects.select_related("annee", "niveau", "niveau__degre").all()
    if annee_id:
        groupes = groupes.filter(annee_id=annee_id)
    if niveau_id:
        groupes = groupes.filter(niveau_id=niveau_id)

    periodes = Periode.objects.select_related("annee").all()
    if annee_id:
        periodes = periodes.filter(annee_id=annee_id)

    # ✅ Matières: filtrage correct (par groupe -> niveau)
    matieres = Matiere.objects.filter(is_active=True)
    if groupe_obj:
        matieres = matieres.filter(niveaux=groupe_obj.niveau).distinct()
    elif niveau_id:
        matieres = matieres.filter(niveaux__id=niveau_id).distinct()
    matieres = matieres.order_by("nom")

    if matiere_id and not matieres.filter(id=matiere_id).exists():
        matiere_id = ""

    # ✅ Enseignants: via EnseignantGroupe
    enseignants = Enseignant.objects.filter(is_active=True)

    if annee_id and groupe_id:
        enseignants = enseignants.filter(
            affectations_groupes__annee_id=annee_id,
            affectations_groupes__groupe_id=groupe_id
        ).distinct()
    elif annee_id and niveau_id:
        enseignants = enseignants.filter(
            affectations_groupes__annee_id=annee_id,
            affectations_groupes__groupe__niveau_id=niveau_id
        ).distinct()

    enseignants = enseignants.order_by("nom", "prenom")

    if enseignant_id and not enseignants.filter(id=enseignant_id).exists():
        enseignant_id = ""

    return render(request, "admin/notes/evaluations_list.html", {
        "evaluations": qs.order_by("-date", "-id"),

        "annees": annees,
        "annee_selected": annee_id,

        "date_selected": date_str,

        "niveaux": niveaux,
        "niveau_selected": niveau_id,

        "groupes": groupes,
        "groupe_selected": groupe_id,

        "periodes": periodes,
        "periode_selected": periode_id,

        "enseignants": enseignants,
        "enseignant_selected": enseignant_id,

        "matieres": matieres,
        "matiere_selected": matiere_id,
    })

@login_required
@group_required("ADMIN", "SCOLARITE")
def evaluation_create(request):
    annee_active = AnneeScolaire.objects.filter(is_active=True).first()
    if not annee_active:
        messages.error(request, "⚠️ Aucune année scolaire active.")
        return redirect("core:evaluation_list")  # adapte si besoin

    niveau_ui = (
        (request.POST.get("niveau_ui") if request.method == "POST" else request.GET.get("niveau_ui"))
        or ""
    ).strip()

    niveaux = (
        Niveau.objects
        .select_related("degre")
        .all()
        .order_by("degre__ordre", "ordre", "nom")
    )

    if request.method == "POST":
        form = EvaluationForm(request.POST, niveau_ui=niveau_ui)
        if form.is_valid():
            ev = form.save()
            messages.success(request, "✅ Évaluation créée.")
            return redirect("core:notes_saisie", evaluation_id=ev.id)
    else:
        form = EvaluationForm(niveau_ui=niveau_ui)

    return render(request, "admin/notes/evaluations_form.html", {
        "form": form,
        "mode": "create",
        "annee_active": annee_active,
        "niveaux": niveaux,
        "niveau_ui_selected": niveau_ui,
    })


def _clean_int(value):
    """
    Retourne '' si value n'est pas un entier (ex: 'ANGLAIS'),
    sinon retourne la valeur en string.
    """
    value = (value or "").strip()
    return value if value.isdigit() else ""


@login_required
@group_required("ADMIN", "SCOLARITE")
def notes_saisie_home(request):
    """
    Page 1: choisir une évaluation à saisir
    + filtres: q, niveau, groupe, periode, matiere
    + affiche le nom d'enseignant (direct ou fallback via EnseignantGroupe.matiere_fk)
    """
    annee_active = AnneeScolaire.objects.filter(is_active=True).first()
    if not annee_active:
        messages.error(request, "⚠️ Aucune année scolaire active.")
        return redirect("core:dashboard")

    # -------------------------
    # ✅ GET (safe)
    # -------------------------
    q = (request.GET.get("q") or "").strip()

    niveau_id = _clean_int(request.GET.get("niveau"))
    groupe_id = _clean_int(request.GET.get("groupe"))
    periode_id = _clean_int(request.GET.get("periode"))

    # ⚠️ matiere peut arriver en texte => on corrige
    raw_matiere = (request.GET.get("matiere") or "").strip()
    matiere_id = raw_matiere if raw_matiere.isdigit() else ""

    if raw_matiere and not raw_matiere.isdigit():
        m = Matiere.objects.filter(is_active=True, nom__iexact=raw_matiere).first()
        matiere_id = str(m.id) if m else ""

    # -------------------------
    # ✅ Dropdowns
    # -------------------------
    niveaux = (
        Niveau.objects
        .select_related("degre")
        .all()
        .order_by("degre__ordre", "ordre", "nom")
    )

    groupes = (
        Groupe.objects
        .select_related("niveau", "niveau__degre")
        .filter(annee=annee_active)
    )
    if niveau_id:
        groupes = groupes.filter(niveau_id=niveau_id)

    periodes = Periode.objects.filter(annee=annee_active).order_by("ordre")

    # matières filtrées selon niveau/groupe
    matieres = Matiere.objects.filter(is_active=True)

    if groupe_id:
        g = Groupe.objects.select_related("niveau").filter(id=groupe_id, annee=annee_active).first()
        if g:
            matieres = matieres.filter(niveaux=g.niveau).distinct()
        else:
            matieres = matieres.none()
    elif niveau_id:
        matieres = matieres.filter(niveaux__id=niveau_id).distinct()

    matieres = matieres.order_by("nom")

    if matiere_id and not matieres.filter(id=matiere_id).exists():
        matiere_id = ""

    # -------------------------
    # ✅ Evaluations
    # -------------------------
    evaluations = (
        Evaluation.objects
        .select_related("matiere", "enseignant", "periode", "groupe", "groupe__niveau", "groupe__niveau__degre")
        .filter(groupe__annee=annee_active, periode__annee=annee_active)
    )

    if niveau_id and not groupe_id:
        evaluations = evaluations.filter(groupe__niveau_id=niveau_id)

    if groupe_id:
        evaluations = evaluations.filter(groupe_id=groupe_id)

    if periode_id:
        evaluations = evaluations.filter(periode_id=periode_id)

    if matiere_id:
        evaluations = evaluations.filter(matiere_id=matiere_id)

    if q:
        evaluations = evaluations.filter(
            Q(titre__icontains=q) |
            Q(matiere__nom__icontains=q) |
            Q(enseignant__nom__icontains=q) |
            Q(enseignant__prenom__icontains=q)
        )

    evaluations = evaluations.order_by("-date", "matiere__nom", "titre")

    # -------------------------
    # ✅ Fallback enseignant via EnseignantGroupe
    #   clé robuste: (groupe_id, matiere_id) -> enseignant
    # -------------------------
    ens_map = {}

    eg_qs = (
        EnseignantGroupe.objects
        .select_related("enseignant", "groupe", "matiere_fk")
        .filter(annee=annee_active, matiere_fk__isnull=False)
    )

    for eg in eg_qs:
        # ✅ mapping par IDs (propre)
        ens_map[(eg.groupe_id, eg.matiere_fk_id)] = eg.enseignant

    # ✅ label prêt pour template
    for ev in evaluations:
        if ev.enseignant:
            ev.enseignant_label = f"{ev.enseignant.nom} {ev.enseignant.prenom}"
        else:
            ens = ens_map.get((ev.groupe_id, ev.matiere_id))
            ev.enseignant_label = f"{ens.nom} {ens.prenom}" if ens else "—"

    return render(request, "admin/notes/notes_saisie_home.html", {
        "annee_active": annee_active,

        "q": q,

        "niveaux": niveaux,
        "niveau_selected": niveau_id,

        "groupes": groupes,
        "groupe_selected": groupe_id,

        "periodes": periodes,
        "periode_selected": periode_id,

        "matieres": matieres,
        "matiere_selected": matiere_id,

        "evaluations": evaluations,
    })


@login_required
@group_required("ADMIN", "SCOLARITE")
def notes_saisie(request, evaluation_id):
    """
    Page 2: saisie notes
    ✅ Après Enregistrer => on reste sur page et on revoit les anciennes notes
    ✅ Champ vide => supprime la note
    """
    ev = get_object_or_404(
        Evaluation.objects.select_related("groupe", "periode", "matiere", "enseignant"),
        id=evaluation_id
    )

    inscriptions = (
        Inscription.objects
        .select_related("eleve")
        .filter(annee=ev.periode.annee, groupe=ev.groupe)
        .order_by("eleve__nom", "eleve__prenom")
    )
    eleves = [i.eleve for i in inscriptions]

    if request.method == "POST":
        saved = 0
        deleted = 0

        for e in eleves:
            key = f"note_{e.id}"
            raw = (request.POST.get(key) or "").strip()

            if raw == "":
                Note.objects.filter(evaluation=ev, eleve=e).delete()
                deleted += 1
                continue

            try:
                val = Decimal(raw.replace(",", "."))
            except Exception:
                messages.error(request, f"⚠️ Note invalide pour {e.matricule} : {raw}")
                continue

            if val < 0 or val > Decimal(ev.note_max):
                messages.error(request, f"⚠️ Note hors limite pour {e.matricule} (0–{ev.note_max})")
                continue

            Note.objects.update_or_create(
                evaluation=ev,
                eleve=e,
                defaults={"valeur": val}
            )
            saved += 1

        messages.success(request, f"✅ Enregistré: {saved} note(s) | supprimé: {deleted} (vides)")
        return redirect("core:notes_saisie", evaluation_id=ev.id)

    notes_map = {
        n.eleve_id: n
        for n in Note.objects.filter(evaluation=ev, eleve__in=eleves)
    }

    return render(request, "admin/notes/notes_saisie.html", {
        "ev": ev,
        "eleves": eleves,
        "notes_map": notes_map,
    })


from django.shortcuts import get_object_or_404, render, redirect

from core.models import (
    Eleve, Inscription, AnneeScolaire, Periode,
    Note, Absence
)

# si tu as déjà group_required, garde le tien
 # adapte le chemin si besoin

# si tu as ton pdf_utils existant
from core import pdf_utils  # adapte si besoin


# =========================
# Utils notes
# =========================
def _to20(valeur, note_max) -> Decimal:
    """
    Convertit une note / note_max vers /20.
    """
    try:
        v = Decimal(str(valeur))
        m = Decimal(str(note_max or 20))
        if m <= 0:
            return Decimal("0")
        return (v / m) * Decimal("20")
    except Exception:
        return Decimal("0")


def bulletin_data(eleve: Eleve, periode: Periode) -> dict:
    """
    Retourne :
    - rows : liste par matière (moyenne, best, nb, items...)
    - moyenne_generale : moyenne générale pondérée par coefficient matière
    - recap : infos utiles
    """
    # élève doit être inscrit dans l’année de la période
    insc = (
        Inscription.objects
        .select_related("groupe", "annee")
        .filter(eleve=eleve, annee=periode.annee)
        .first()
    )
    if not insc:
        return {
            "rows": [],
            "moyenne_generale": None,
            "best": None,
            "nb_notes": 0,
        }

    notes_qs = (
        Note.objects
        .select_related(
            "evaluation",
            "evaluation__matiere",
            "evaluation__enseignant",
            "evaluation__groupe",
            "evaluation__periode",
        )
        .filter(
            eleve=eleve,
            evaluation__periode=periode,
            evaluation__groupe=insc.groupe,
        )
        .order_by("evaluation__matiere__nom", "-evaluation__date", "-id")
    )

    bucket = {}
    recap_best = None
    nb_notes = 0

    for n in notes_qs:
        ev = n.evaluation
        mat = ev.matiere

        note20 = _to20(n.valeur, ev.note_max)
        mat_coef = Decimal(str(mat.coefficient or 1))
        ev_coef = Decimal(str(ev.coefficient or 1))
        w = mat_coef * ev_coef

        if mat.id not in bucket:
            bucket[mat.id] = {
                "matiere": mat.nom,
                "coef": mat_coef,
                "sum_w": Decimal("0"),
                "sum_vw": Decimal("0"),
                "best20": None,
                "items": [],
            }

        b = bucket[mat.id]
        b["sum_w"] += w
        b["sum_vw"] += (note20 * w)
        b["best20"] = note20 if b["best20"] is None else max(b["best20"], note20)

        ens_name = "—"
        if ev.enseignant:
            ens_name = f"{ev.enseignant.prenom} {ev.enseignant.nom}".strip()

        b["items"].append({
            "date": ev.date,
            "titre": ev.titre,
            "type": ev.get_type_display() if hasattr(ev, "get_type_display") else (ev.type or "—"),
            "coef": ev_coef,
            "note": n.valeur,
            "note_max": ev.note_max,
            "note20": note20,
            "enseignant": ens_name,
        })

        nb_notes += 1
        recap_best = note20 if recap_best is None else max(recap_best, note20)

    # rows + moyenne générale pondérée par coef matière (pas double pondération)
    rows = []
    sum_general = Decimal("0")
    sum_general_w = Decimal("0")

    for _, b in sorted(bucket.items(), key=lambda kv: kv[1]["matiere"]):
        avg = (b["sum_vw"] / b["sum_w"]) if b["sum_w"] > 0 else None

        if avg is not None:
            sum_general += (avg * b["coef"])
            sum_general_w += b["coef"]

        rows.append({
            "matiere": b["matiere"],
            "coef": b["coef"],
            "moyenne": avg,
            "best20": b["best20"],
            "nb": len(b["items"]),
            "items": b["items"],
        })

    moyenne_generale = (sum_general / sum_general_w) if sum_general_w > 0 else None

    return {
        "rows": rows,
        "moyenne_generale": moyenne_generale,
        "best": recap_best,
        "nb_notes": nb_notes,
    }


def moyenne_classe(periode: Periode, groupe) -> Decimal | None:
    """
    Moyenne générale de la classe (moyenne des moyennes générales des élèves du groupe).
    """
    eleves_ids = (
        Inscription.objects
        .filter(annee=periode.annee, groupe=groupe)
        .values_list("eleve_id", flat=True)
        .distinct()
    )

    moys = []
    for eid in eleves_ids:
        el = Eleve.objects.filter(id=eid).first()
        if not el:
            continue
        d = bulletin_data(el, periode)
        mg = d.get("moyenne_generale")
        if mg is not None:
            moys.append(Decimal(str(mg)))

    if not moys:
        return None
    return sum(moys) / Decimal(str(len(moys)))


def rang_eleve(periode: Periode, groupe, eleve: Eleve) -> tuple[int | None, int | None]:
    """
    Rang de l'élève dans son groupe pour la période (sur moyenne générale).
    """
    eleves = (
        Eleve.objects
        .filter(inscriptions__annee=periode.annee, inscriptions__groupe=groupe)
        .distinct()
    )

    scores = []
    for e in eleves:
        d = bulletin_data(e, periode)
        mg = d.get("moyenne_generale")
        if mg is None:
            continue
        scores.append((e.id, Decimal(str(mg))))

    if not scores:
        return None, None

    scores.sort(key=lambda x: x[1], reverse=True)
    effectif = len(scores)

    rank = None
    for i, (eid, _) in enumerate(scores, start=1):
        if eid == eleve.id:
            rank = i
            break

    return rank, effectif


# =========================
# Views
# =========================
@login_required
@group_required("ADMIN", "SCOLARITE")
def bulletin_view(request, eleve_id):
    eleve = get_object_or_404(Eleve, id=eleve_id)

    annee_active = AnneeScolaire.objects.filter(is_active=True).first()
    annee_id = (request.GET.get("annee", "") or "").strip() or (str(annee_active.id) if annee_active else "")
    periode_id = (request.GET.get("periode", "") or "").strip()

    annees = AnneeScolaire.objects.all().order_by("-date_debut")

    periodes = Periode.objects.select_related("annee").all()
    if annee_id:
        periodes = periodes.filter(annee_id=annee_id).order_by("ordre")

    periode = None
    if periode_id:
        qs = Periode.objects.filter(id=periode_id)
        if annee_id:
            qs = qs.filter(annee_id=annee_id)
        periode = qs.first()
    else:
        periode = periodes.first()

    data = {"rows": [], "moyenne_generale": None, "best": None, "nb_notes": 0}
    groupe = None
    rank = effectif = None
    moyenne_cls = None

    if periode:
        # groupe via inscription
        insc = (
            Inscription.objects
            .select_related("groupe", "groupe__niveau", "annee")
            .filter(eleve=eleve, annee=periode.annee)
            .first()
        )
        groupe = insc.groupe if insc else None

        data = bulletin_data(eleve, periode)

        if groupe:
            rank, effectif = rang_eleve(periode, groupe, eleve)
            moyenne_cls = moyenne_classe(periode, groupe)

    return render(request, "admin/notes/bulletin.html", {
        "eleve": eleve,
        "annees": annees,
        "annee_selected": annee_id,
        "periodes": periodes,
        "periode_selected": str(periode.id) if periode else "",
        "periode": periode,
        "data": data,
        "groupe": groupe,
        "rank": rank,
        "effectif": effectif,
        "moyenne_classe": moyenne_cls,
    })


@login_required
@group_required("ADMIN", "SCOLARITE")
def bulletin_pdf_view(request, eleve_id):
    eleve = get_object_or_404(Eleve, id=eleve_id)
    periode_id = request.GET.get("periode")

    if not periode_id:
        messages.error(request, "⚠️ Période manquante.")
        return redirect("core:bulletin_view", eleve_id=eleve.id)

    periode = get_object_or_404(Periode, id=periode_id)

    insc = (
        Inscription.objects
        .select_related("groupe")
        .filter(eleve=eleve, annee=periode.annee)
        .first()
    )
    if not insc:
        messages.error(request, "⚠️ Cet élève n'est pas inscrit dans l'année de cette période.")
        return redirect("core:bulletin_view", eleve_id=eleve.id)

    groupe = insc.groupe
    data = bulletin_data(eleve, periode)

    rank, effectif = rang_eleve(periode, groupe, eleve) if groupe else (None, None)
    moyenne_cls = moyenne_classe(periode, groupe) if groupe else None

    # adapte si ton pdf_utils ne prend pas moyenne_classe
    return pdf_utils.bulletin_pdf(
        eleve, periode, data,
        groupe=groupe, rank=rank, effectif=effectif,
        moyenne_classe=moyenne_cls
    )

from .models import ParentEleve

@login_required
def parent_dashboard(request):
    user = request.user

    # ✅ uniquement PARENT
    if not user.groups.filter(name="PARENT").exists():
        return render(request, "parent/forbidden.html", status=403)

    # ✅ Parent lié au user
    parent = getattr(user, "parent_profile", None)
    if parent is None:
        return render(
            request,
            "parent/forbidden.html",
            {"message": "Votre compte n'est pas encore lié à un parent. Contactez l'administration."},
            status=403,
        )

    # ✅ récupérer les liens + enfants
    liens = (
        ParentEleve.objects
        .select_related("eleve")
        .filter(parent=parent)
        .order_by("eleve__nom", "eleve__prenom")
    )

    enfants = [l.eleve for l in liens]

    return render(request, "parent/dashboard.html", {
        "parent": parent,
        "enfants": enfants,  # ✅ ton template attend ça
        "liens": liens,      # (optionnel, utile plus tard)
    })

from django.db.models import (
    Count, Sum, F, Value, DecimalField, IntegerField, Q
)


from .models import Eleve, Groupe, Inscription, Paiement, Niveau
# Si ton modèle Absence existe, décommente:
# from .models import Absence


def _pct_change(current, previous):
    """Retourne une variation % arrondie (int)."""
    current = float(current or 0)
    previous = float(previous or 0)
    if previous <= 0:
        return 0
    return int(round(((current - previous) / previous) * 100))



from django.db.models import Count, Sum, F, Value, DecimalField

from .models import Eleve, Groupe, Inscription, Paiement


def _month_start(d: date) -> date:
    return date(d.year, d.month, 1)


def _add_months(d: date, months: int) -> date:
    # petit utilitaire sans dépendance externe
    y = d.year + (d.month - 1 + months) // 12
    m = (d.month - 1 + months) % 12 + 1
    return date(y, m, 1)



# ============================
# U1 — Users (liste + export)
# ============================

@login_required
@group_required("SUPER_ADMIN", "ADMIN")
def users_list(request):
    User = get_user_model()

    q = (request.GET.get("q") or "").strip()
    group_filter = (request.GET.get("group") or "").strip()  # PROF / PARENT / ...

    users = User.objects.all().prefetch_related("groups").order_by("username")

    if q:
        users = users.filter(
            Q(username__icontains=q) |
            Q(first_name__icontains=q) |
            Q(last_name__icontains=q) |
            Q(email__icontains=q)
        )

    if group_filter:
        users = users.filter(groups__name=group_filter)

    # groups pour dropdown filtre
    from django.contrib.auth.models import Group
    groups = Group.objects.all().order_by("name")

    return render(request, "admin/users/list.html", {
        "users": users,
        "q": q,
        "group_filter": group_filter,
        "groups": groups,
    })


@login_required
@group_required("SUPER_ADMIN", "ADMIN")
def users_export_csv(request):
    User = get_user_model()
    q = (request.GET.get("q") or "").strip()
    group_filter = (request.GET.get("group") or "").strip()

    users = User.objects.all().prefetch_related("groups").order_by("username")

    if q:
        users = users.filter(
            Q(username__icontains=q) |
            Q(first_name__icontains=q) |
            Q(last_name__icontains=q) |
            Q(email__icontains=q)
        )
    if group_filter:
        users = users.filter(groups__name=group_filter)

    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="users_export.csv"'

    writer = csv.writer(response)
    writer.writerow(["matricule", "nom", "role", "is_active"])

    for u in users:
        nom = f"{(u.last_name or '').strip()} {(u.first_name or '').strip()}".strip() or "—"
        roles = [g.name for g in u.groups.all()]
        role = roles[0] if roles else "—"
        writer.writerow([u.username, nom, role, "1" if u.is_active else "0"])

    return response


from .utils_users import reset_password
from .models import TempPassword


@login_required
@group_required("SUPER_ADMIN", "ADMIN")
def users_reset_passwords_export_csv(request):
    """
    Reset + export CSV des mots de passe temporaires
    Format: matricule | nom | mdp_temp | role
    """
    User = get_user_model()

    q = (request.GET.get("q") or "").strip()
    group_filter = (request.GET.get("group") or "").strip()

    users = User.objects.all().prefetch_related("groups").order_by("username")

    if q:
        users = users.filter(
            Q(username__icontains=q) |
            Q(first_name__icontains=q) |
            Q(last_name__icontains=q)
        )

    if group_filter:
        users = users.filter(groups__name=group_filter)

    # sécurité : jamais toucher aux superusers
    users = users.filter(is_superuser=False)

    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="users_passwords_temp.csv"'

    writer = csv.writer(response)
    writer.writerow(["matricule", "nom", "mdp_temp", "role"])

    for u in users:
        temp_pwd = reset_password(u)

        # stocker le mdp temporaire
        TempPassword.objects.update_or_create(
            user=u,
            defaults={"password": temp_pwd}
        )

        nom = f"{u.last_name or ''} {u.first_name or ''}".strip() or "—"
        roles = [g.name for g in u.groups.all()]
        role = roles[0] if roles else "—"

        writer.writerow([u.username, nom, temp_pwd, role])

    return response

# ============================
# U1 — Users (CRUD + mdp + roles)
# ============================

from django.contrib.auth.models import Group

from .forms_users import UserCreateForm, UserUpdateForm, PasswordChangeForm
from .utils_users import generate_temp_password, reset_password


@login_required
@group_required("SUPER_ADMIN", "ADMIN")
def users_detail(request, user_id):
    User = get_user_model()
    u = get_object_or_404(User.objects.prefetch_related("groups"), id=user_id)

    temp = TempPassword.objects.filter(user=u).first()
    roles = [g.name for g in u.groups.all()]

    return render(request, "admin/users/detail.html", {
        "u": u,
        "roles": roles,
        "temp": temp,
    })


@login_required
@group_required("SUPER_ADMIN", "ADMIN")
def users_create(request):
    User = get_user_model()

    if request.method == "POST":
        form = UserCreateForm(request.POST)
        if form.is_valid():
            auto = form.cleaned_data["auto_password"]
            pwd = (form.cleaned_data.get("password") or "").strip()

            # créer user
            user = User(
                username=form.cleaned_data["username"].strip(),
                last_name=form.cleaned_data.get("last_name", "").strip(),
                first_name=form.cleaned_data.get("first_name", "").strip(),
                email=form.cleaned_data.get("email", "").strip(),
                is_active=form.cleaned_data["is_active"],
            )

            # mdp
            if auto:
                pwd = generate_temp_password()
            user.set_password(pwd)
            user.save()

            # groupes
            groups = form.cleaned_data.get("groups")
            if groups:
                user.groups.set(groups)

            # stocker mdp temporaire (tu le veux pour export)
            TempPassword.objects.update_or_create(
                user=user,
                defaults={"password": pwd, "updated_at": timezone.now()}
            )

            messages.success(request, f"✅ User créé: {user.username} | MDP: {pwd}")
            return redirect("core:users_detail", user_id=user.id)
    else:
        form = UserCreateForm()

    return render(request, "admin/users/form.html", {
        "form": form,
        "mode": "create",
    })


@login_required
@group_required("SUPER_ADMIN", "ADMIN")
def users_update(request, user_id):
    User = get_user_model()
    u = get_object_or_404(User.objects.prefetch_related("groups"), id=user_id)

    if u.is_superuser:
        messages.error(request, "⛔ Modification superuser bloquée ici.")
        return redirect("core:users_detail", user_id=u.id)

    if request.method == "POST":
        form = UserUpdateForm(request.POST, instance=u)
        if form.is_valid():
            obj = form.save()
            groups = form.cleaned_data.get("groups")
            obj.groups.set(groups)
            messages.success(request, "✅ User mis à jour.")
            return redirect("core:users_detail", user_id=obj.id)
    else:
        form = UserUpdateForm(instance=u)
        form.fields["groups"].initial = u.groups.all()

    return render(request, "admin/users/form.html", {
        "form": form,
        "mode": "update",
        "u": u,
    })


@login_required
@group_required("SUPER_ADMIN", "ADMIN")
def users_password(request, user_id):
    User = get_user_model()
    u = get_object_or_404(User, id=user_id)

    # Sécurité: on bloque superuser
    if u.is_superuser:
        messages.error(request, "⛔ Reset mdp superuser bloqué.")
        return redirect("core:users_detail", pk=u.id)  # ✅ adapte si ton url est pk

    if request.method == "POST":
        form = PasswordChangeForm(request.POST)
        if form.is_valid():
            auto = form.cleaned_data["auto_password"]
            pwd_input = (form.cleaned_data.get("password") or "").strip()

            if auto:
                # ✅ reset_password() fait déjà TempPassword.update_or_create()
                pwd = reset_password(u)
            else:
                pwd = pwd_input
                u.set_password(pwd)
                u.save(update_fields=["password"])

                TempPassword.objects.update_or_create(
                    user=u,
                    defaults={"password": pwd, "updated_at": timezone.now()}
                )

            messages.success(request, f"✅ Mot de passe mis à jour: {u.username} | MDP: {pwd}")
            return redirect("core:users_detail", user_id=u.id)  # ✅ adapte si ton url est user_id
    else:
        form = PasswordChangeForm(initial={"auto_password": True})

    return render(request, "admin/users/password.html", {
        "u": u,
        "form": form,
    })

def _has_linked_profile(user):
    """
    Empêche suppression si lié à un profil Parent/Enseignant.
    (sécurise FK/OneToOne)
    """
    # Parent: tu utilises user.parent_profile
    try:
        _ = user.parent_profile
        return True
    except Exception:
        pass

    # Enseignant: on ne connait pas ton related_name exact, donc on tente plusieurs
    for attr in ["enseignant", "enseignant_profile", "enseignant_set"]:
        try:
            obj = getattr(user, attr)
            if obj:
                return True
        except Exception:
            continue

    return False



@login_required
@group_required("SUPER_ADMIN", "ADMIN")
def users_delete(request, user_id):
    User = get_user_model()
    u = get_object_or_404(User, id=user_id)

    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"

    # 1) Sécurité superuser
    if u.is_superuser:
        msg = "⛔ Suppression superuser bloquée."
        if is_ajax:
            return JsonResponse({"ok": False, "redirect": None, "message": msg}, status=403)
        messages.error(request, msg)
        return redirect("core:users_detail", user_id=u.id)

    # 2) Profils liés
    parent = Parent.objects.select_related("user").filter(user=u).first()
    ens = Enseignant.objects.select_related("user").filter(user=u).first()

    if request.method == "POST":
        try:
            with transaction.atomic():

                # === CAS A: lié à Enseignant => on désactive (pas de suppression)
                if ens:
                    if u.is_active:
                        u.is_active = False
                        u.save(update_fields=["is_active"])
                    msg = "✅ User désactivé (lié à un Enseignant)."
                    if is_ajax:
                        return JsonResponse({"ok": True, "redirect": "detail", "user_id": u.id, "message": msg})
                    messages.success(request, msg)
                    return redirect("core:users_detail", user_id=u.id)

                # === CAS B: lié à Parent ===
                if parent:
                    # Parent a encore des élèves ? => désactive uniquement
                    if parent.liens.exists():
                        if u.is_active:
                            u.is_active = False
                            u.save(update_fields=["is_active"])
                        msg = "✅ User désactivé (Parent encore lié à des élèves)."
                        if is_ajax:
                            return JsonResponse({"ok": True, "redirect": "detail", "user_id": u.id, "message": msg})
                        messages.success(request, msg)
                        return redirect("core:users_detail", user_id=u.id)

                    # Parent orphelin => supprimer Parent + User
                    parent.delete()
                    u.delete()
                    msg = "🗑️ Parent orphelin + User supprimés."
                    if is_ajax:
                        return JsonResponse({"ok": True, "redirect": "list", "message": msg})
                    messages.success(request, msg)
                    return redirect("core:users_list")

                # === CAS C: aucun profil lié => suppression
                u.delete()
                msg = "🗑️ User supprimé."
                if is_ajax:
                    return JsonResponse({"ok": True, "redirect": "list", "message": msg})
                messages.success(request, msg)
                return redirect("core:users_list")

        except ProtectedError:
            # FK PROTECT => désactivation fallback
            if u.is_active:
                u.is_active = False
                u.save(update_fields=["is_active"])
            msg = "⛔ Suppression impossible (références existantes). User désactivé."
            if is_ajax:
                return JsonResponse({"ok": True, "redirect": "detail", "user_id": u.id, "message": msg})
            messages.error(request, msg)
            return redirect("core:users_detail", user_id=u.id)

    # ✅ GET : si AJAX => renvoyer le fragment modal, sinon page normale
    # (ton delete.html doit être le HTML modal AZ, sans <style> ni <script>)
    return render(request, "admin/users/delete.html", {"u": u, "parent": parent, "ens": ens})

@login_required
@group_required("SUPER_ADMIN", "ADMIN", "SCOLARITE", "PEDAGOGIQUE", "SECRETAIRE")
def api_enseignants(request):
    annee_id = request.GET.get("annee_id")
    groupe_id = request.GET.get("groupe_id")

    if not (annee_id and groupe_id):
        return JsonResponse({"results": []})

    qs = (
        Enseignant.objects.filter(
            affectations_groupes__annee_id=annee_id,
            affectations_groupes__groupe_id=groupe_id,
            is_active=True,
        )
        .distinct()
        .order_by("nom", "prenom")
    )

    data = [
        {"id": e.id, "label": f"{e.nom} {e.prenom} ({e.matricule})"}
        for e in qs
    ]
    return JsonResponse({"results": data})



@login_required
def api_matieres_par_groupe(request):
    """
    GET /api/matieres/?groupe_id=XX
    Retour: {"results": [{id, label}]}

    Règles:
    - Sécurité: uniquement groupes autorisés pour l'utilisateur.
    - Catalogue: matières filtrées par Niveau via Matiere.niveaux.
    - Pas de fallback "toutes les matières" si le niveau n'a rien.
    - Optionnel: pour un PROF, filtrer aussi par Matiere.enseignants (compétences).
    """
    groupe_id = (request.GET.get("groupe_id") or "").strip()
    if not groupe_id.isdigit():
        return JsonResponse({"results": []})

    allowed = _allowed_groupes_for_user(request.user)
    g = allowed.filter(id=int(groupe_id)).select_related("niveau").first()
    if not g or not getattr(g, "niveau_id", None):
        return JsonResponse({"results": []})

    qs = (
        Matiere.objects
        .filter(is_active=True, niveaux=g.niveau)
        .distinct()
        .order_by("nom")
    )

    # ✅ option: si c'est un PROF, limiter aux matières où il est "capable"
    # (si tu utilises Matiere.enseignants comme catalogue)
    ens = getattr(request.user, "enseignant_profile", None)
    if ens:
        qs_prof = qs.filter(enseignants=ens)
        # si tu veux STRICT (prof ne voit que ses matières):
        qs = qs_prof
        # si tu veux LOOSE (si pas paramétré, il voit quand même tout du niveau):
        # qs = qs_prof if qs_prof.exists() else qs

    data = [{"id": m.id, "label": m.nom} for m in qs]
    return JsonResponse({"results": data})


@login_required
@group_required("SUPER_ADMIN", "ADMIN", "COMPTABLE", "SCOLARITE")
def ajax_niveaux(request):
    """
    Retourne les niveaux disponibles pour une année (annee_id).
    GET: /ajax/niveaux/?annee=<id>
    """
    annee_id = request.GET.get("annee", "").strip()

    qs = Niveau.objects.select_related("degre").all()

    # Filtrer uniquement les niveaux qui ont des groupes dans cette année
    if annee_id:
        qs = qs.filter(groupes__annee_id=annee_id).distinct()

    data = [
        {
            "id": n.id,
            "label": f"{n.degre.nom} — {n.nom}",
        }
        for n in qs.order_by("degre__ordre", "ordre", "nom")
    ]
    return JsonResponse({"results": data})


@login_required
@group_required("SUPER_ADMIN", "ADMIN", "COMPTABLE", "SCOLARITE")
def ajax_groupes(request):
    """
    Retourne les groupes selon année + niveau.
    GET: /ajax/groupes/?annee=<id>&niveau=<id>
    Si annee vide => année active.
    """
    annee_id = (request.GET.get("annee") or "").strip()
    niveau_id = (request.GET.get("niveau") or "").strip()

    # ✅ fallback annee => année active
    if not annee_id:
        annee_active = AnneeScolaire.objects.filter(is_active=True).first()
        if annee_active:
            annee_id = str(annee_active.id)

    qs = Groupe.objects.select_related("niveau", "niveau__degre", "annee").all()

    if annee_id:
        qs = qs.filter(annee_id=annee_id)

    if niveau_id:
        qs = qs.filter(niveau_id=niveau_id)

    qs = qs.order_by("niveau__degre__ordre", "niveau__ordre", "nom")

    data = [
        {
            "id": g.id,
            "label": f"{g.niveau.nom} / {g.nom}"
        }
        for g in qs
    ]
    return JsonResponse({"results": data})

@login_required
@group_required("SUPER_ADMIN", "ADMIN", "COMPTABLE", "SCOLARITE", "SECRETAIRE")
def ajax_periodes(request):
    """
    GET: /ajax/periodes/?annee=<id>
    """
    annee_id = request.GET.get("annee", "").strip()

    qs = Periode.objects.select_related("annee").all()
    if annee_id:
        qs = qs.filter(annee_id=annee_id)

    data = [{"id": p.id, "label": p.nom} for p in qs.order_by("ordre")]
    return JsonResponse({"results": data})



# =========================
# I — Communication (Avis)
# =========================

from django.utils import timezone
from datetime import timedelta

@login_required
@group_required("SUPER_ADMIN", "ADMIN")
def avis_list(request):
    q = (request.GET.get("q") or "").strip()
    cible = (request.GET.get("cible") or "").strip()      # cible_type
    period = (request.GET.get("period") or "").strip()    # 7d, 30d, ytd, all

    items = Avis.objects.all()

    # 🔎 Search
    if q:
        items = items.filter(Q(titre__icontains=q) | Q(contenu__icontains=q))

    # 🎯 Cible type
    if cible:
        items = items.filter(cible_type=cible)

    # ⏱️ Période (date_publication)
    now = timezone.now()
    if period == "7d":
        items = items.filter(date_publication__gte=now - timedelta(days=7))
    elif period == "30d":
        items = items.filter(date_publication__gte=now - timedelta(days=30))
    elif period == "ytd":
        start_year = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        items = items.filter(date_publication__gte=start_year)
    # "all" ou vide => rien

    items = items.order_by("-date_publication", "-id")

    # ✅ pour remplir le select des cibles dynamiquement
    # (Avis.CIBLE_CHOICES si tu l'as dans le model)
    cible_choices = getattr(Avis, "CIBLE_CHOICES", None)

    return render(request, "admin/avis/list.html", {
        "items": items,
        "q": q,
        "cible": cible,
        "period": period,
        "cible_choices": cible_choices,
    })

@login_required
@group_required("SUPER_ADMIN", "ADMIN")
def avis_create(request):
    form = AvisForm(request.POST or None)

    if request.method == "POST":
        if form.is_valid():
            form.save()
            messages.success(request, "✅ Avis enregistré.")
            return redirect("core:avis_list")
        else:
            # Debug: tu verras l’erreur exacte dans console serveur
            print("AVIS FORM ERRORS =>", form.errors)

    return render(request, "admin/avis/form.html", {"form": form, "mode": "create"})

@login_required
def avis_detail(request, pk):
    obj = get_object_or_404(Avis, pk=pk)
    return render(request, "admin/avis/detail.html", {"obj": obj})


@login_required
def avis_delete(request, pk):
    obj = get_object_or_404(Avis, pk=pk)
    if request.method == "POST":
        obj.delete()
        messages.success(request, "🗑️ Avis supprimé.")
        return redirect("core:avis_list")
    return render(request, "admin/avis/delete.html", {"obj": obj})


# =========================
# I — Communication (SMS)
# =========================

def _parents_from_cible(cible_type: str, degre_id=None, niveau_id=None, groupe_id=None, eleve_id=None):
    """
    Retourne une QuerySet de Parent ciblés via ParentEleve.
    """
    liens = ParentEleve.objects.select_related("parent", "eleve")

    if cible_type == "TOUS":
        pass

    elif cible_type == "DEGRE":
        liens = liens.filter(eleve__inscriptions__groupe__niveau__degre_id=degre_id)

    elif cible_type == "NIVEAU":
        liens = liens.filter(eleve__inscriptions__groupe__niveau_id=niveau_id)

    elif cible_type == "GROUPE":
        liens = liens.filter(eleve__inscriptions__groupe_id=groupe_id)

    elif cible_type == "ELEVE":
        liens = liens.filter(eleve_id=eleve_id)

    # parents uniques
    parent_ids = liens.values_list("parent_id", flat=True).distinct()
    return Parent.objects.filter(id__in=parent_ids, is_active=True)


@login_required
def sms_send(request):
    """
    Envoi réel SMS + historique.
    """
    if request.method == "POST":
        form = SmsSendForm(request.POST)
        if form.is_valid():
            msg = form.cleaned_data["message"]
            cible_type = form.cleaned_data["cible_type"]

            degre_id = form.cleaned_data.get("degre")
            niveau_id = form.cleaned_data.get("niveau")
            groupe_id = form.cleaned_data.get("groupe")
            eleve_id = form.cleaned_data.get("eleve")

            parents = _parents_from_cible(cible_type, degre_id, niveau_id, groupe_id, eleve_id)

            sent = 0
            failed = 0

            for p in parents:
                tel = normalize_phone(p.telephone)
                if not tel:
                    # on log quand même, en FAILED
                    SmsHistorique.objects.create(
                        parent=p,
                        telephone="",
                        message=msg,
                        status="FAILED",
                        provider="twilio",
                        error_message="Téléphone parent vide.",
                    )
                    failed += 1
                    continue

                hist = SmsHistorique.objects.create(
                    parent=p,
                    telephone=tel,
                    message=msg,
                    status="PENDING",
                    provider="twilio",
                )

                ok, provider_id, err = send_sms_via_twilio(tel, msg)

                if ok:
                    hist.status = "SENT"
                    hist.provider_message_id = provider_id
                    hist.sent_at = timezone.now()
                    hist.error_message = ""
                    sent += 1
                else:
                    hist.status = "FAILED"
                    hist.error_message = err
                    failed += 1

                hist.save(update_fields=["status", "provider_message_id", "error_message", "sent_at", "updated_at", "updated_by"])

            messages.success(request, f"📩 SMS terminé — Envoyés: {sent} | Échecs: {failed}")
            return redirect("core:sms_history")
    else:
        form = SmsSendForm()

    # Pour aider l’UI : listes (select)
    degres = Degre.objects.all()
    niveaux = Niveau.objects.select_related("degre").all()
    groupes = Groupe.objects.select_related("niveau", "annee").all()
    eleves = Eleve.objects.all()

    return render(request, "admin/communication/sms_send.html", {
        "form": form,
        "degres": degres,
        "niveaux": niveaux,
        "groupes": groupes,
        "eleves": eleves,
    })


@login_required
def sms_history(request):
    q = (request.GET.get("q") or "").strip()
    status = (request.GET.get("status") or "").strip()     # SENT/FAILED/PENDING/...
    period = (request.GET.get("period") or "").strip()     # 7d / 30d / ytd / all

    qs = SmsHistorique.objects.select_related("parent").all()

    if q:
        qs = qs.filter(
            Q(parent__nom__icontains=q) |
            Q(parent__prenom__icontains=q) |
            Q(telephone__icontains=q) |
            Q(message__icontains=q) |
            Q(error_message__icontains=q)
        )

    if status:
        qs = qs.filter(status=status)

    now = timezone.now()
    if period == "7d":
        qs = qs.filter(created_at__gte=now - timedelta(days=7))
    elif period == "30d":
        qs = qs.filter(created_at__gte=now - timedelta(days=30))
    elif period == "ytd":
        start_year = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        qs = qs.filter(created_at__gte=start_year)

    qs = qs.order_by("-created_at", "-id")

    # ✅ liste statuts pour select
    status_choices = ["PENDING", "SENT", "DELIVERED", "FAILED", "ERROR"]

    return render(request, "admin/communication/sms_history.html", {
        "items": qs,
        "q": q,
        "status_selected": status,
        "period_selected": period,
        "status_choices": status_choices,
    })



from django.shortcuts import render, get_object_or_404

User = get_user_model()

def users_detail_modal(request, pk):
    u = get_object_or_404(User, pk=pk)

    # roles (selon ton système : groups, role field, etc.)
    roles = list(u.groups.values_list("name", flat=True)) if hasattr(u, "groups") else []

    # temp password (si tu as un modèle pour ça)
    temp = getattr(u, "temp_password", None)  # adapte selon ton code
    # ou mets temp=None si tu n’as pas de modèle

    return render(request, "admin/users/_detail_modal.html", {
        "u": u,
        "roles": roles,
        "temp": temp,
    })

from django.db import IntegrityError

@login_required
@group_required("SUPER_ADMIN", "ADMIN", "SCOLARITE", "SECRETAIRE")
def eleve_reinscrire(request, pk):
    eleve = get_object_or_404(Eleve, pk=pk)

    # ✅ année active (par défaut)
    annee_active = AnneeScolaire.objects.filter(is_active=True).first()
    annees = AnneeScolaire.objects.all().order_by("-date_debut")

    # ✅ filtres (GET) pour remplir les dropdowns
    annee_id = request.GET.get("annee", "")
    niveau_id = request.GET.get("niveau", "")
    groupe_id = request.GET.get("groupe", "")
    periode_id = request.GET.get("periode", "")

    # ✅ par défaut : année active si rien choisi
    if not annee_id and annee_active:
        annee_id = str(annee_active.id)

    # ✅ dropdowns dépendants
    niveaux = Niveau.objects.select_related("degre").all()
    if annee_id:
        niveaux = niveaux.filter(groupes__annee_id=annee_id).distinct()

    groupes = Groupe.objects.select_related("niveau", "annee").all()
    if annee_id:
        groupes = groupes.filter(annee_id=annee_id)
    if niveau_id:
        groupes = groupes.filter(niveau_id=niveau_id)

    periodes = Periode.objects.all()
    if annee_id:
        periodes = periodes.filter(annee_id=annee_id)

    # ✅ POST = créer la nouvelle inscription
    if request.method == "POST":
        annee_id_post = request.POST.get("annee")
        groupe_id_post = request.POST.get("groupe")
        periode_id_post = request.POST.get("periode") or None

        if not annee_id_post or not groupe_id_post:
            messages.error(request, "Année et groupe sont obligatoires.")
            return redirect("core:eleve_reinscrire", pk=eleve.id)

        # ✅ sécurité : le groupe doit exister
        groupe = get_object_or_404(Groupe, pk=groupe_id_post)

        try:
            Inscription.objects.create(
                eleve=eleve,
                annee_id=annee_id_post,
                groupe=groupe,
                periode_id=periode_id_post,
                statut="VALIDEE",
            )
            messages.success(request, "Réinscription effectuée ✅")
            return redirect("core:eleve_list")
        except IntegrityError:
            # ✅ ta contrainte unique (eleve, annee) déclenche ici
            messages.error(request, "Cet élève est déjà inscrit sur cette année.")
            return redirect("core:eleve_reinscrire", pk=eleve.id)

    return render(request, "admin/eleves/reinscrire.html", {
        "eleve": eleve,
        "annees": annees,
        "annee_selected": annee_id,
        "niveaux": niveaux,
        "niveau_selected": niveau_id,
        "groupes": groupes,
        "groupe_selected": groupe_id,
        "periodes": periodes,
        "periode_selected": periode_id,
    })


from decimal import Decimal, InvalidOperation


from core.models import Degre, AnneeScolaire




from .models import EcheanceMensuelle



from core.models import Periode
from .views_prof import _allowed_groupes_for_user

@login_required
def api_periodes_par_groupe(request):
    gid = (request.GET.get("groupe_id") or "").strip()
    if not gid.isdigit():
        return JsonResponse([], safe=False)

    groupes = _allowed_groupes_for_user(request.user)
    g = groupes.filter(id=int(gid)).select_related("annee").first()
    if not g:
        return JsonResponse([], safe=False)

    periodes = Periode.objects.filter(annee=g.annee).order_by("ordre")
    return JsonResponse([{"id": p.id, "label": p.nom} for p in periodes], safe=False)


from core.services.transport_echeances import sync_transport_echeances_for_inscription
from core.models import Inscription, EleveTransport, EcheanceTransportMensuelle

@login_required
@group_required("SUPER_ADMIN", "ADMIN", "COMPTABLE", "SCOLARITE")
def ajax_transport_echeances(request):
    """
    GET /core/ajax/transport-echeances/?inscription=ID
    -> {enabled:bool, items:[...], tarif_mensuel:"0.00"}
    """
    insc_id = (request.GET.get("inscription") or "").strip()
    if not insc_id.isdigit():
        return JsonResponse({"enabled": False, "items": [], "tarif_mensuel": "0.00"}, status=200)

    insc = get_object_or_404(
        Inscription.objects.select_related("eleve", "annee", "groupe"),
        pk=int(insc_id)
    )

    tr = getattr(insc.eleve, "transport", None)
    if not tr or not tr.enabled:
        return JsonResponse({"enabled": False, "items": [], "tarif_mensuel": "0.00"}, status=200)

    qs = (EcheanceTransportMensuelle.objects
          .filter(eleve_id=insc.eleve_id, annee_id=insc.annee_id)
          .order_by("mois_index"))

    items = []
    for e in qs:
        du = e.montant_du or Decimal("0.00")
        is_paye = (e.statut == "PAYE")
        items.append({
            "id": e.id,
            "mois_index": int(e.mois_index),
            "mois_nom": e.mois_nom,
            "du": str(du),
            "is_paye": bool(is_paye),
            "statut": e.statut,
            "date_echeance": str(e.date_echeance),
        })

    return JsonResponse({
        "enabled": True,
        "tarif_mensuel": str(tr.tarif_mensuel or Decimal("0.00")),
        "items": items
    }, status=200)

from django.shortcuts import get_object_or_404, redirect

from core.models import Eleve, EleveTransport, Inscription


def _d(x) -> Decimal:
    try:
        return Decimal(str(x or "0").replace(",", "."))
    except Exception:
        return Decimal("0.00")


@login_required
@group_required("SUPER_ADMIN", "ADMIN", "SCOLARITE")
def transport_toggle(request, eleve_id: int):
    eleve = get_object_or_404(Eleve, pk=eleve_id)
    obj, _ = EleveTransport.objects.get_or_create(eleve=eleve)

    obj.enabled = not obj.enabled

    # règle: enabled => tarif > 0
    if obj.enabled and (obj.tarif_mensuel or Decimal("0.00")) <= Decimal("0.00"):
        obj.enabled = False
        obj.save(update_fields=["enabled"])
        messages.error(request, "Transport non activé : tarif mensuel = 0.00. Défini d’abord le tarif.")
        return redirect(request.META.get("HTTP_REFERER", "/"))

    obj.save(update_fields=["enabled"])

    # sync année active (inscription active)
    insc = (Inscription.objects
            .select_related("annee")
            .filter(eleve_id=eleve.id, annee__is_active=True)
            .first())
    if insc:
        sync_transport_echeances_for_inscription(insc.id)

    messages.success(request, f"Transport {'activé' if obj.enabled else 'désactivé'} pour {eleve.matricule}.")
    return redirect(request.META.get("HTTP_REFERER", "/"))


@login_required
@group_required("SUPER_ADMIN", "ADMIN", "SCOLARITE")
@require_POST
def transport_set_tarif(request, eleve_id: int):
    eleve = get_object_or_404(Eleve, pk=eleve_id)
    obj, _ = EleveTransport.objects.get_or_create(eleve=eleve)

    tarif = _d(request.POST.get("tarif_mensuel"))

    if tarif <= Decimal("0.00"):
        obj.tarif_mensuel = Decimal("0.00")
        obj.enabled = False
        obj.save(update_fields=["tarif_mensuel", "enabled"])

        insc = Inscription.objects.filter(eleve_id=eleve.id, annee__is_active=True).first()
        if insc:
            sync_transport_echeances_for_inscription(insc.id)

        messages.success(request, "Tarif transport mis à 0.00 → transport désactivé.")
        return redirect(request.META.get("HTTP_REFERER", "/"))

    obj.tarif_mensuel = tarif
    # si tu veux auto-enable quand tarif>0 :
    if not obj.enabled:
        obj.enabled = True
    obj.save(update_fields=["tarif_mensuel", "enabled"])

    insc = Inscription.objects.filter(eleve_id=eleve.id, annee__is_active=True).first()
    if insc:
        sync_transport_echeances_for_inscription(insc.id)

    messages.success(request, f"Transport activé + tarif mis à jour : {tarif:.2f} MAD.")
    return redirect(request.META.get("HTTP_REFERER", "/"))


@login_required
@group_required("SUPER_ADMIN", "ADMIN", "COMPTABLE", "SCOLARITE")
def ajax_transport_status(request):
    eleve_id = (request.GET.get("eleve_id") or "").strip()
    if not eleve_id.isdigit():
        return JsonResponse({"enabled": False, "tarif_mensuel": "0.00"})

    eleve = get_object_or_404(Eleve, pk=int(eleve_id))
    obj = getattr(eleve, "transport", None)

    if not obj:
        return JsonResponse({"enabled": False, "tarif_mensuel": "0.00"})

    return JsonResponse({
        "enabled": bool(obj.enabled),
        "tarif_mensuel": f"{(obj.tarif_mensuel or Decimal('0.00')):.2f}",
    })


# core/views_finance.py
from core.models import TransactionFinance, RemboursementFinance
from django.db import models


def _D(v, default=Decimal("0.00")):
    try:
        s = str(v or "").strip()
        if s == "":
            return default
        s = s.replace(" ", "").replace(",", ".")
        return Decimal(s)
    except (InvalidOperation, ValueError):
        return default

@login_required
@group_required("SUPER_ADMIN", "ADMIN", "COMPTABLE")
def transaction_remboursement_create(request, tx_id: int):
    tx = get_object_or_404(
        TransactionFinance.objects
        .select_related("inscription", "inscription__eleve", "inscription__annee", "inscription__groupe")
        .prefetch_related("lignes", "lignes__echeance", "lignes__echeance_transport", "remboursements"),
        pk=tx_id
    )

    total = tx.montant_total or Decimal("0.00")
    is_zero_tx = (total == Decimal("0.00"))

    deja = tx.remboursements.aggregate(s=models.Sum("montant"))["s"] or Decimal("0.00")
    max_remb = max(total - deja, Decimal("0.00"))

    if request.method == "POST":
        montant = _D(request.POST.get("montant"), default=Decimal("0.00"))
        mode = (request.POST.get("mode") or "ESPECES").strip()
        raison = (request.POST.get("raison") or "").strip()

        # ✅ sécurité: tx=0 => montant doit être 0
        if is_zero_tx and montant != Decimal("0.00"):
            messages.error(request, "Transaction à 0 => montant doit rester à 0.")
            return redirect("core:paiement_remboursement_create", tx_id=tx.id)

        r = RemboursementFinance(
            transaction=tx,
            montant=montant,
            mode=mode,
            raison=raison,
            created_by=request.user
        )

        try:
            r.save()
            messages.success(request, "✅ Remboursement / Annulation enregistré.")
            return redirect("core:paiement_list")
        except Exception as e:
            messages.error(request, f"⚠️ {e}")

    return render(request, "admin/paiements/remboursement_form.html", {
        "tx": tx,
        "max_remb": max_remb,
        "is_zero_tx": is_zero_tx,
        "modes": RemboursementFinance.MODE_CHOICES,
    })


@login_required
@group_required("SUPER_ADMIN", "ADMIN", "PEDAGOGIQUE")
def edt_prof_week(request, pk=None):
    annee_active = AnneeScolaire.objects.filter(is_active=True).first()

    # --- GET (toujours en str) ---
    annee_id = (request.GET.get("annee") or "").strip()
    niveau_id = (request.GET.get("niveau") or "").strip()
    groupe_id = (request.GET.get("groupe") or "").strip()
    enseignant_id = (request.GET.get("enseignant") or "").strip()

    # ✅ si accès depuis fiche enseignant (/enseignants/<pk>/edt/)
    if pk and not enseignant_id:
        enseignant_id = str(pk)

    # ✅ Année par défaut = active
    if not annee_id.isdigit():
        annee_id = str(annee_active.id) if annee_active else ""

    # Listes filtres
    annees = AnneeScolaire.objects.all()

    niveaux = Niveau.objects.select_related("degre").all()
    if annee_id.isdigit():
        niveaux = niveaux.filter(groupes__annee_id=int(annee_id)).distinct()

    groupes = Groupe.objects.select_related("annee", "niveau", "niveau__degre").all()
    if annee_id.isdigit():
        groupes = groupes.filter(annee_id=int(annee_id))
    if niveau_id.isdigit():
        groupes = groupes.filter(niveau_id=int(niveau_id))

    # ✅ Enseignants possibles (selon filtres) = ceux qui ont des séances
    ens_qs = Seance.objects.all()
    if annee_id.isdigit():
        ens_qs = ens_qs.filter(annee_id=int(annee_id))
    if niveau_id.isdigit():
        ens_qs = ens_qs.filter(groupe__niveau_id=int(niveau_id))
    if groupe_id.isdigit():
        ens_qs = ens_qs.filter(groupe_id=int(groupe_id))

    enseignants = Enseignant.objects.filter(
        id__in=ens_qs.values_list("enseignant_id", flat=True).distinct()
    ).order_by("nom", "prenom", "matricule")

    # ✅ si enseignant_id vide, on prend le 1er (UX pratique)
    if (not enseignant_id.isdigit()) and enseignants.exists():
        enseignant_id = str(enseignants.first().id)

    # =========================
    # Séances (EDT prof)
    # =========================
    seances = Seance.objects.select_related("enseignant", "groupe", "groupe__niveau").all()

    if annee_id.isdigit():
        seances = seances.filter(annee_id=int(annee_id))

    if niveau_id.isdigit():
        seances = seances.filter(groupe__niveau_id=int(niveau_id))

    if groupe_id.isdigit():
        seances = seances.filter(groupe_id=int(groupe_id))

    if enseignant_id.isdigit():
        seances = seances.filter(enseignant_id=int(enseignant_id))
    else:
        # aucun enseignant => aucune séance
        seances = seances.none()

    seances = list(seances)

    # =========================
    # Grille semaine (même algo que prof_edt)
    # =========================
    days = [("LUN", "Lu"), ("MAR", "Ma"), ("MER", "Me"), ("JEU", "Je"), ("VEN", "Ve"), ("SAM", "Sa")]
    slots = [
        (time(8, 30),  time(9, 30)),
        (time(9, 30),  time(10, 30)),
        (time(10, 30), time(11, 30)),
        (time(11, 30), time(12, 30)),
        (time(14, 30), time(15, 30)),
        (time(15, 30), time(16, 30)),
        (time(16, 30), time(17, 30)),
        (time(17, 30), time(18, 30)),
    ]

    def fmt(t): return t.strftime("%H:%M") if t else ""

    def find_slot_index_start(t_):
        for i, (a, b) in enumerate(slots):
            if a <= t_ < b:
                return i
        return None

    def find_slot_index_end(t_):
        for i, (a, b) in enumerate(slots):
            if a < t_ <= b:
                return i
        return None

    slot_labels = [{"num": i, "start": fmt(a), "end": fmt(b)} for i, (a, b) in enumerate(slots, start=1)]
    n = len(slots)

    seances_by_day = {}
    for se in seances:
        seances_by_day.setdefault(se.jour, []).append(se)

    rows = []
    for code, short in days:
        occ = [None] * n

        for se in seances_by_day.get(code, []):
            i0 = find_slot_index_start(se.heure_debut)
            i1 = find_slot_index_end(se.heure_fin)
            if i0 is None or i1 is None:
                continue

            colspan = max(1, (i1 - i0 + 1))
            if isinstance(occ[i0], dict):
                occ[i0]["items"].append(se)
                occ[i0]["colspan"] = max(occ[i0]["colspan"], colspan)
            else:
                occ[i0] = {"items": [se], "colspan": colspan}

            for k in range(i0 + 1, min(i0 + colspan, n)):
                occ[k] = "SKIP"

        cells_render = []
        i = 0
        while i < n:
            if occ[i] == "SKIP":
                i += 1
                continue

            if isinstance(occ[i], dict):
                cell = occ[i]
                span = min(cell["colspan"], n - i)
                cells_render.append({"kind": "event", "colspan": span, "items": cell["items"]})
                i += span
            else:
                cells_render.append({"kind": "empty", "colspan": 1, "items": []})
                i += 1

        rows.append({"code": code, "short": short, "cells": cells_render})

    # pour header (nom enseignant sélectionné)
    ens_obj = None
    if enseignant_id.isdigit():
        ens_obj = Enseignant.objects.filter(id=int(enseignant_id)).first()

    return render(request, "admin/seances/edt_prof_week.html", {
        "annee_active": annee_active,

        "annees": annees,
        "annee_selected": annee_id,

        "niveaux": niveaux,
        "niveau_selected": niveau_id,

        "groupes": groupes,
        "groupe_selected": groupe_id,

        "enseignants": enseignants,
        "enseignant_selected": enseignant_id,
        "enseignant_obj": ens_obj,

        "slot_labels": slot_labels,
        "rows": rows,
        "has_slots": bool(seances),
    })
