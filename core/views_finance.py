# core/views_finance.py
# ✅ Version alignée avec ton wizard + impayés mensuels + fratrie + endpoints AJAX

from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum, F, DecimalField, ExpressionWrapper
from django.db.models.functions import Coalesce
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
import json, uuid
from decimal import Decimal
from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from accounts.decorators import group_required
from decimal import Decimal, InvalidOperation
from django.contrib import messages
from django.shortcuts import redirect

from core.models import (
    Inscription, EcheanceMensuelle,
    EcheanceTransportMensuelle, EleveTransport,
    TransactionFinance, TransactionLigne
)
from accounts.permissions import group_required  # ✅ IMPORTANT (pas core.permissions)

from core.models import (
    AnneeScolaire, Inscription, EcheanceMensuelle, Paiement, PaiementLigne,
    Niveau, Groupe, Periode, Eleve
)

# si tu as ParentEleve dans core.models, laisse comme ça
from core.models import ParentEleve

from .forms import PaiementForm



@login_required
@group_required("SUPER_ADMIN", "ADMIN", "COMPTABLE")
def inscription_finance_detail(request, inscription_id: int):
    insc = get_object_or_404(
        Inscription.objects.select_related("eleve", "annee", "groupe", "groupe__niveau", "groupe__niveau__degre", "periode"),
        pk=inscription_id
    )

    echeances = EcheanceMensuelle.objects.filter(eleve_id=insc.eleve_id, annee_id=insc.annee_id).order_by("mois_index")
    paiements = insc.paiements.select_related("echeance").all()

    total_mensuel_du = sum((e.montant_du or Decimal("0.00")) for e in echeances)
    total_mensuel_paye = sum((e.montant_paye or Decimal("0.00")) for e in echeances)
    total_mensuel_reste = total_mensuel_du - total_mensuel_paye

    total_insc_du = insc.frais_inscription_du or Decimal("0.00")
    total_insc_paye = insc.frais_inscription_paye or Decimal("0.00")
    total_insc_reste = insc.reste_inscription

    total_global_du = total_insc_du + total_mensuel_du
    total_global_paye = total_insc_paye + total_mensuel_paye
    total_global_reste = total_global_du - total_global_paye

    return render(request, "admin/finance/inscription_detail.html", {
        "insc": insc,
        "echeances": echeances,
        "paiements": paiements,
        "kpi": {
            "insc_du": total_insc_du,
            "insc_paye": total_insc_paye,
            "insc_reste": total_insc_reste,
            "mensuel_du": total_mensuel_du,
            "mensuel_paye": total_mensuel_paye,
            "mensuel_reste": total_mensuel_reste,
            "global_du": total_global_du,
            "global_paye": total_global_paye,
            "global_reste": total_global_reste,
        }
    })


# =========================
# AJAX — Echeances pour wizard (format attendu par ton JS)
# =========================
@login_required
@group_required("SUPER_ADMIN", "ADMIN", "COMPTABLE", "SCOLARITE")
def ajax_echeances(request):
    """
    GET /core/ajax/echeances/?inscription=ID
    -> {items:[...], tarifs:{...}}
    """
    insc_id = (request.GET.get("inscription") or "").strip()
    if not insc_id.isdigit():
        return JsonResponse({"items": [], "tarifs": {}}, status=200)

    insc = get_object_or_404(
        Inscription.objects.select_related("eleve", "annee", "groupe"),
        pk=int(insc_id)
    )

    qs = (
        EcheanceMensuelle.objects
        .filter(eleve_id=insc.eleve_id, annee_id=insc.annee_id)
        .order_by("mois_index")
    )

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

    tarifs = {
        "frais_scolarite_mensuel": str(insc.frais_scolarite_mensuel or Decimal("0.00")),
        "reste_inscription": str(insc.reste_inscription or Decimal("0.00")),
        "tarif_override": bool(insc.tarif_override),
    }

    return JsonResponse({"items": items, "tarifs": tarifs}, status=200)


# =========================
# API — Groupes par niveau (année active)
# =========================
@login_required
@group_required("SUPER_ADMIN", "ADMIN", "COMPTABLE", "SCOLARITE")
def api_groupes_par_niveau(request):
    """
    GET /core/api/groupes-par-niveau/?niveau_id=XX
    -> {results:[{id,label}]}
    """
    niveau_id = (request.GET.get("niveau_id") or "").strip()
    if not niveau_id.isdigit():
        return JsonResponse({"results": []})

    annee_active = AnneeScolaire.objects.filter(is_active=True).first()
    if not annee_active:
        return JsonResponse({"results": []})

    qs = (
        Groupe.objects
        .select_related("niveau", "niveau__degre")
        .filter(annee=annee_active, niveau_id=int(niveau_id))
        .order_by("nom")
    )

    results = [{
        "id": g.id,
        "label": f"{g.niveau.degre.nom} • {g.niveau.nom} • {g.nom}"
    } for g in qs]

    return JsonResponse({"results": results})


# =========================
# AJAX — Inscription by élève + fratrie
# =========================
@login_required
@group_required("SUPER_ADMIN", "ADMIN", "COMPTABLE", "SCOLARITE")
def ajax_inscription_by_eleve(request):
    """
    GET ?eleve_id=XX
    -> retourne inscription année active + fratrie (même parent)
    """
    eleve_id = (request.GET.get("eleve_id") or "").strip()
    if not eleve_id.isdigit():
        return JsonResponse({"inscription_id": None, "fratrie": []})

    annee_active = AnneeScolaire.objects.filter(is_active=True).first()
    if not annee_active:
        return JsonResponse({"inscription_id": None, "fratrie": []})

    insc = (Inscription.objects
            .select_related("groupe")
            .filter(eleve_id=int(eleve_id), annee_id=annee_active.id)
            .first())

    parent_ids = ParentEleve.objects.filter(eleve_id=int(eleve_id)).values_list("parent_id", flat=True)
    fratrie_ids = (ParentEleve.objects
                   .filter(parent_id__in=parent_ids)
                   .exclude(eleve_id=int(eleve_id))
                   .values_list("eleve_id", flat=True)
                   .distinct())

    fratrie_qs = (Eleve.objects
                  .filter(id__in=fratrie_ids)
                  .order_by("nom", "prenom"))

    fratrie = []
    for e in fratrie_qs:
        insc2 = (Inscription.objects
                 .filter(eleve_id=e.id, annee_id=annee_active.id)
                 .select_related("groupe")
                 .first())
        fratrie.append({
            "id": e.id,
            "matricule": e.matricule,
            "nom": e.nom,
            "prenom": e.prenom,
            "groupe_label": insc2.groupe.nom if insc2 and insc2.groupe else ""
        })

    return JsonResponse({
        "inscription_id": insc.id if insc else None,
        "fratrie": fratrie
    })


# =========================
# API — Fratrie (liste simple)
# =========================
@login_required
@group_required("SUPER_ADMIN", "ADMIN", "COMPTABLE", "SCOLARITE")
def api_fratrie(request):
    """
    GET /core/api/fratrie/?eleve_id=XX
    Retourne les élèves partageant au moins 1 parent.
    """
    eleve_id = (request.GET.get("eleve_id") or "").strip()
    if not eleve_id.isdigit():
        return JsonResponse({"results": []})

    eleve_id = int(eleve_id)

    parent_ids = list(
        ParentEleve.objects
        .filter(eleve_id=eleve_id)
        .values_list("parent_id", flat=True)
        .distinct()
    )
    if not parent_ids:
        return JsonResponse({"results": []})

    sib_ids = list(
        ParentEleve.objects
        .filter(parent_id__in=parent_ids)
        .exclude(eleve_id=eleve_id)
        .values_list("eleve_id", flat=True)
        .distinct()
    )
    if not sib_ids:
        return JsonResponse({"results": []})

    annee_active = AnneeScolaire.objects.filter(is_active=True).first()

    insc_map = {}
    if annee_active:
        for insc in (
            Inscription.objects
            .filter(annee=annee_active, eleve_id__in=sib_ids)
            .select_related("groupe", "groupe__niveau", "groupe__niveau__degre")
        ):
            insc_map[insc.eleve_id] = insc

    results = []
    for e in Eleve.objects.filter(id__in=sib_ids).order_by("nom", "prenom"):
        insc = insc_map.get(e.id)
        groupe_label = ""
        if insc and insc.groupe:
            groupe_label = f"{insc.groupe.niveau.degre.nom} • {insc.groupe.niveau.nom} • {insc.groupe.nom}"

        results.append({
            "id": e.id,
            "label": f'{(e.matricule or "").strip()} — {e.nom} {e.prenom}'.strip(" —"),
            "groupe": groupe_label
        })

    return JsonResponse({"results": results})


# =========================
# Page raccourci — ouvrir wizard pré-rempli
# =========================
@login_required
@group_required("SUPER_ADMIN", "ADMIN", "COMPTABLE", "SCOLARITE")
def paiements_eleve(request, eleve_id: int):
    e = get_object_or_404(Eleve, pk=eleve_id)

    annee_active = AnneeScolaire.objects.filter(is_active=True).first()
    insc = None
    if annee_active:
        insc = (
            Inscription.objects
            .filter(annee=annee_active, eleve=e)
            .select_related("groupe", "groupe__niveau", "groupe__niveau__degre")
            .first()
        )

    niveaux = Niveau.objects.select_related("degre").order_by("degre__ordre", "ordre", "nom")

    return render(request, "admin/paiements/form.html", {
        "niveaux": niveaux,
        "prefill": {
            "eleve_id": e.id,
            "eleve_label": f'{(e.matricule or "").strip()} — {e.nom} {e.prenom}'.strip(" —"),
            "niveau_id": insc.groupe.niveau_id if insc and insc.groupe else "",
            "groupe_id": insc.groupe_id if insc and insc.groupe else "",
        }
    })


import json
import uuid
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from accounts.permissions import group_required

from core.models import (
    AnneeScolaire, Niveau, Groupe, Eleve, Inscription,
    EcheanceMensuelle, ParentEleve,
    TransactionFinance, TransactionLigne
)

from core.forms import PaiementForm  # on le garde pour validation payload (réutilisable)


@login_required
@group_required("SUPER_ADMIN", "ADMIN", "COMPTABLE", "SCOLARITE")
def transaction_wizard(request):
    niveaux = Niveau.objects.select_related("degre").order_by("degre__ordre", "ordre", "nom")

    # ✅ NEW: prefill via inscription_id
    inscription_id = (request.GET.get("inscription_id") or "").strip()
    type_pref = (request.GET.get("type") or "").strip().upper()  # INSCRIPTION/SCOLARITE/TRANSPORT/PACK

    prefill = {
        "eleve_id": request.GET.get("eleve_id", ""),
        "niveau_id": request.GET.get("niveau_id", ""),
        "groupe_id": request.GET.get("groupe_id", ""),
        "inscription_id": inscription_id,
        "type": type_pref,
    }

    if inscription_id.isdigit():
        insc = (Inscription.objects
                .select_related("eleve", "groupe", "groupe__niveau")
                .filter(id=int(inscription_id))
                .first())
        if insc:
            prefill.update({
                "eleve_id": str(insc.eleve_id),
                "niveau_id": str(insc.groupe.niveau_id),
                "groupe_id": str(insc.groupe_id),
            })

    return render(request, "admin/paiements/wizard.html", {
        "niveaux": niveaux,
        "prefill": prefill
    })


# core/views_finance.py

import json, uuid
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect

from accounts.permissions import group_required

from core.models import (
    Inscription,
    EcheanceMensuelle,
    EleveTransport,
    EcheanceTransportMensuelle,
    TransactionFinance,
    TransactionLigne,
)

def _D(x, default=Decimal("0.00")):
    if x is None:
        return default
    s = str(x).strip()
    if s == "":
        return default
    s_lower = s.lower()
    if s_lower in {"nan", "+nan", "-nan", "inf", "+inf", "-inf", "infinity", "+infinity", "-infinity"}:
        return default
    s = s.replace(" ", "").replace("\u202f", "").replace("\u00a0", "")
    s = s.replace(",", ".")
    try:
        return Decimal(s)
    except (InvalidOperation, ValueError):
        return default


@login_required
@group_required("SUPER_ADMIN", "ADMIN", "COMPTABLE", "SCOLARITE")
@transaction.atomic
def transaction_create(request):
    if request.method != "POST":
        return redirect("core:transaction_wizard")

    tx_type = (request.POST.get("type_transaction") or "SCOLARITE").strip().upper()
    inscription_id = (request.POST.get("inscription_id") or "").strip()
    mode = (request.POST.get("mode") or "ESPECES").strip()
    reference = (request.POST.get("reference") or "").strip()
    note = (request.POST.get("note") or "").strip()

    if not inscription_id.isdigit():
        messages.error(request, "Inscription invalide.")
        return redirect("core:transaction_wizard")

    insc = get_object_or_404(
        Inscription.objects.select_related(
            "eleve", "annee", "groupe", "groupe__niveau", "groupe__niveau__degre"
        ),
        pk=int(inscription_id)
    )

    batch_token = str(uuid.uuid4())

    def create_tx(total: Decimal, type_label: str) -> TransactionFinance:
        return TransactionFinance.objects.create(
            inscription=insc,
            type_transaction=type_label,
            montant_total=total,
            mode=mode,
            reference=reference,
            note=note,
            batch_token=batch_token
        )

    # ✅ protège : ne JAMAIS écraser mensuel par 0 à cause d’une réduction inscription
    def apply_inscription_override(amount: Decimal) -> None:
        current_mensuel = insc.frais_scolarite_mensuel or Decimal("0.00")

        # si override mensuel vide/0 => on le remet au mensuel actuel
        if (getattr(insc, "override_frais_scolarite_mensuel", None) is not None):
            if (insc.override_frais_scolarite_mensuel or Decimal("0.00")) <= Decimal("0.00"):
                insc.override_frais_scolarite_mensuel = current_mensuel

        insc.tarif_override = True
        insc.override_frais_inscription_du = amount
        insc.frais_inscription_du = amount
        insc.frais_inscription_paye = amount  # one-shot (même 0)
        insc.save()  # pas update_fields

    # =========================
    # INSCRIPTION (0 autorisé)
    # =========================
    if tx_type == "INSCRIPTION":
        max_rest = insc.reste_inscription or Decimal("0.00")

        if (insc.frais_inscription_paye or Decimal("0.00")) > Decimal("0.00"):
            messages.error(request, "❌ Inscription déjà encaissée (partiellement ou totalement). Pas de reprise.")
            return redirect("core:transaction_wizard")

        montant = _D(request.POST.get("montant_inscription"), default=Decimal("0.00"))
        if montant < 0:
            messages.error(request, "Montant inscription invalide.")
            return redirect("core:transaction_wizard")

        if montant > max_rest:
            messages.error(request, f"Montant trop élevé. Max = {max_rest} MAD.")
            return redirect("core:transaction_wizard")

        apply_inscription_override(montant)

        tx = create_tx(montant, "INSCRIPTION")
        TransactionLigne.objects.create(
            transaction=tx,
            echeance=None,
            libelle="Frais d'inscription",
            montant=montant
        )

        messages.success(request, "Transaction inscription enregistrée ✅")
        return redirect("core:transaction_success", tx_id=tx.id)

    # =========================
    # SCOLARITE (0 autorisé)
    # =========================
    def handle_scolarite(payload_raw: str, tx: TransactionFinance) -> Decimal:
        try:
            payload = json.loads(payload_raw) if payload_raw else {}
        except Exception:
            payload = {}

        selected_ids = payload.get("selected_ids") or []
        prices = payload.get("prices") or {}

        ids_int = []
        for x in selected_ids:
            try:
                ids_int.append(int(str(x).strip()))
            except Exception:
                pass
        ids_int = list(dict.fromkeys(ids_int))

        if not ids_int:
            raise ValueError("Sélectionne au moins un mois scolarité.")

        echeances = list(
            EcheanceMensuelle.objects.select_for_update()
            .filter(id__in=ids_int, eleve_id=insc.eleve_id, annee_id=insc.annee_id)
            .order_by("mois_index")
        )
        if len(echeances) != len(ids_int):
            raise ValueError("Certaines échéances scolarité ne correspondent pas à cet élève / année.")

        total = Decimal("0.00")

        for e in echeances:
            # pas de reprise si déjà encaissé > 0
            if (e.montant_paye or Decimal("0.00")) > Decimal("0.00") or e.statut == "PAYE":
                raise ValueError(f"{e.mois_nom} a déjà un paiement. (Pas de reprise)")

            key = str(e.id)
            m = _D(prices.get(key, e.montant_du), default=Decimal("0.00"))
            if m < 0:
                raise ValueError(f"Montant invalide pour {e.mois_nom}.")

            TransactionLigne.objects.create(
                transaction=tx,
                echeance=e,
                libelle=f"Scolarité — {e.mois_nom}",
                montant=m
            )

            # ✅ mois gratuit si m=0 => du=0 paye=0 statut=A_PAYER
            e.montant_du = m
            e.montant_paye = m
            e.refresh_statut(save=False)
            e.save(update_fields=["montant_du", "montant_paye", "statut"])

            total += m

        return total

    # =========================
    # TRANSPORT (0 autorisé)
    # =========================
    def handle_transport(payload_raw: str, tx: TransactionFinance) -> Decimal:
        cfg = EleveTransport.objects.filter(eleve_id=insc.eleve_id).first()
        if not cfg or not cfg.enabled:
            raise ValueError("Transport désactivé pour cet élève.")

        try:
            payload = json.loads(payload_raw) if payload_raw else {}
        except Exception:
            payload = {}

        selected_ids = payload.get("selected_ids") or []
        prices = payload.get("prices") or {}

        ids_int = []
        for x in selected_ids:
            try:
                ids_int.append(int(str(x).strip()))
            except Exception:
                pass
        ids_int = list(dict.fromkeys(ids_int))

        if not ids_int:
            raise ValueError("Sélectionne au moins un mois transport.")

        echeances = list(
            EcheanceTransportMensuelle.objects.select_for_update()
            .filter(id__in=ids_int, eleve_id=insc.eleve_id, annee_id=insc.annee_id)
            .order_by("mois_index")
        )
        if len(echeances) != len(ids_int):
            raise ValueError("Certaines échéances transport ne correspondent pas à cet élève / année.")

        total = Decimal("0.00")

        for e in echeances:
            if (e.montant_paye or Decimal("0.00")) > Decimal("0.00") or e.statut == "PAYE":
                raise ValueError(f"Transport {e.mois_nom} a déjà un paiement. (Pas de reprise)")

            key = str(e.id)
            m = _D(prices.get(key, e.montant_du), default=Decimal("0.00"))
            if m < 0:
                raise ValueError(f"Montant invalide pour Transport {e.mois_nom}.")

            TransactionLigne.objects.create(
                transaction=tx,
                echeance_transport=e,
                libelle=f"Transport — {e.mois_nom}",
                montant=m
            )

            e.montant_du = m
            e.montant_paye = m
            e.refresh_statut(save=False)
            e.save(update_fields=["montant_du", "montant_paye", "statut"])

            total += m

        return total

    # =========================
    # PACK (0 autorisé partout)
    # =========================
    if tx_type == "PACK":
        raw_pack = (request.POST.get("pack_payload") or "").strip()
        try:
            pack = json.loads(raw_pack) if raw_pack else {}
            if not isinstance(pack, dict):
                pack = {}
        except Exception:
            pack = {}

        ins_on = bool(pack.get("ins_on", True))
        sco_on = bool(pack.get("sco_on", True))
        tr_on = bool(pack.get("tr_on", True))

        total = Decimal("0.00")
        tx = create_tx(Decimal("0.00"), "PACK")

        if ins_on:
            max_rest = insc.reste_inscription or Decimal("0.00")

            if (insc.frais_inscription_paye or Decimal("0.00")) > Decimal("0.00"):
                messages.error(request, "❌ Inscription déjà encaissée. Pas de reprise.")
                return redirect("core:transaction_wizard")

            amt = _D(pack.get("ins_amount"), default=Decimal("0.00"))
            if amt < 0:
                messages.error(request, "Montant inscription (pack) invalide.")
                return redirect("core:transaction_wizard")

            if amt > max_rest:
                messages.error(request, f"Montant inscription trop élevé. Max = {max_rest} MAD.")
                return redirect("core:transaction_wizard")

            apply_inscription_override(amt)

            TransactionLigne.objects.create(
                transaction=tx,
                echeance=None,
                libelle="Frais d'inscription",
                montant=amt
            )
            total += amt

        if sco_on:
            try:
                total += handle_scolarite(json.dumps(pack.get("sco") or {}), tx)
            except ValueError as e:
                messages.error(request, str(e))
                return redirect("core:transaction_wizard")

        if tr_on:
            try:
                total += handle_transport(json.dumps(pack.get("tr") or {}), tx)
            except ValueError as e:
                messages.error(request, str(e))
                return redirect("core:transaction_wizard")

        tx.montant_total = total
        tx.save(update_fields=["montant_total"])

        messages.success(request, "Pack enregistré ✅")
        return redirect("core:transaction_success", tx_id=tx.id)

    # =========================
    # SCOLARITE simple
    # =========================
    if tx_type == "SCOLARITE":
        tx = create_tx(Decimal("0.00"), "SCOLARITE")
        try:
            total = handle_scolarite((request.POST.get("echeances_payload") or ""), tx)
        except ValueError as e:
            messages.error(request, str(e))
            return redirect("core:transaction_wizard")

        tx.montant_total = total
        tx.save(update_fields=["montant_total"])
        messages.success(request, "Transaction scolarité enregistrée ✅")
        return redirect("core:transaction_success", tx_id=tx.id)

    # =========================
    # TRANSPORT simple
    # =========================
    if tx_type == "TRANSPORT":
        tx = create_tx(Decimal("0.00"), "TRANSPORT")
        try:
            total = handle_transport((request.POST.get("transport_payload") or ""), tx)
        except ValueError as e:
            messages.error(request, str(e))
            return redirect("core:transaction_wizard")

        tx.montant_total = total
        tx.save(update_fields=["montant_total"])
        messages.success(request, "Transaction transport enregistrée ✅")
        return redirect("core:transaction_success", tx_id=tx.id)

    messages.error(request, "Type de transaction invalide.")
    return redirect("core:transaction_wizard")


@login_required
@group_required("SUPER_ADMIN", "ADMIN", "COMPTABLE", "SCOLARITE")
def transaction_success(request, tx_id: int):
    tx = get_object_or_404(
        TransactionFinance.objects.select_related(
            "inscription", "inscription__eleve", "inscription__annee",
            "inscription__groupe", "inscription__groupe__niveau", "inscription__groupe__niveau__degre"
        ).prefetch_related("lignes", "lignes__echeance", "lignes__echeance_transport"),
        pk=tx_id
    )
    return render(request, "admin/paiements/transaction_success.html", {"tx": tx})

@login_required
@group_required("SUPER_ADMIN", "ADMIN", "COMPTABLE", "SCOLARITE")
def transaction_pdf(request, tx_id: int):
    """
    PDF pro: 2 copies sur A4 (même page).
    """
    tx = get_object_or_404(
        TransactionFinance.objects.select_related(
            "inscription", "inscription__eleve", "inscription__annee",
            "inscription__groupe", "inscription__groupe__niveau", "inscription__groupe__niveau__degre"
        ).prefetch_related("lignes", "lignes__echeance", "lignes__echeance_transport"),
        pk=tx_id
    )

    from core.pdf.transaction import build_transaction_pdf_bytes
    pdf_bytes = build_transaction_pdf_bytes(tx)
    resp = HttpResponse(pdf_bytes, content_type="application/pdf")
    resp["Content-Disposition"] = f'inline; filename="transaction_{tx.id}.pdf"'
    return resp


@login_required
@group_required("SUPER_ADMIN", "ADMIN", "COMPTABLE", "SCOLARITE")
def api_eleves_par_groupe(request):
    groupe_id = (request.GET.get("groupe_id") or "").strip()
    if not groupe_id.isdigit():
        return JsonResponse({"results": []})

    g = get_object_or_404(Groupe, pk=int(groupe_id))
    # élève via inscription année du groupe
    inscs = (Inscription.objects
             .filter(groupe_id=g.id, annee_id=g.annee_id)
             .select_related("eleve")
             .order_by("eleve__nom", "eleve__prenom"))

    results = []
    for i in inscs:
        e = i.eleve
        results.append({
            "id": e.id,
            "label": f'{(e.matricule or "").strip()} — {e.nom} {e.prenom}'.strip(" —")
        })
    return JsonResponse({"results": results})


def parse_money(value, *, default=None):
    """
    Convertit une valeur (str) en Decimal en acceptant:
    - "1200", "1200.50", "1200,50", "1 200,50"
    - "" / None -> default
    Refuse: "NaN", "inf", valeurs non numériques.
    """
    if value is None:
        return default

    s = str(value).strip()
    if s == "":
        return default

    s_lower = s.lower()
    if s_lower in {"nan", "+nan", "-nan", "inf", "+inf", "-inf", "infinity", "+infinity", "-infinity"}:
        raise InvalidOperation("NaN/INF interdit")

    # enlever espaces (y compris espace insécable)
    s = s.replace(" ", "").replace("\u202f", "").replace("\u00a0", "")

    # virgule -> point
    s = s.replace(",", ".")

    try:
        return Decimal(s)
    except (InvalidOperation, ValueError):
        raise
