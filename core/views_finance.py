# core/views_finance.py
# ✅ FINAL — Finance AZ (Wizard + Impayés + Fratrie + Batch) + FILTRE ÉLÈVES INACTIFS (AJAX)
from __future__ import annotations

import json
import uuid
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.db import transaction
from django.db.models import (
    Q, Sum, F, Value, Exists, OuterRef,
    DecimalField, BooleanField, Case, When
)
from django.db.models.functions import Coalesce
from django.http import JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.db import transaction
from django.db.models import Max
from accounts.permissions import group_required
from core.services.parents import get_primary_parent_for_eleve
from django.views.decorators.http import require_GET, require_POST

from core.models import (
    AnneeScolaire,
    Niveau, Groupe,
    Eleve, Inscription,
    EcheanceMensuelle,
    EleveTransport, EcheanceTransportMensuelle,
    Parent, ParentEleve,
    TransactionFinance, TransactionLigne,
    RemboursementFinance,TransactionFinance, Tarification

)

# =========================================================
# Helpers
# =========================================================
def _D(x, default=Decimal("0.00")) -> Decimal:
    """
    Decimal safe:
    - accepte "1200", "1200,50", "1 200,50"
    - refuse NaN/Inf
    """
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

def assign_receipt_seq_for_batch(batch_token: str) -> int:
    with transaction.atomic():
        last = TransactionFinance.objects.aggregate(m=Max("receipt_seq"))["m"] or 0
        seq = int(last) + 1
        TransactionFinance.objects.filter(batch_token=batch_token, receipt_seq__isnull=True).update(receipt_seq=seq)
        return seq


def _has_field(model, field_name: str) -> bool:
    try:
        model._meta.get_field(field_name)
        return True
    except Exception:
        return False

def _save_tx_justificatifs(tx, files, type_piece="AUTRE"):
    """
    Option A: justificatifs rattachés à TransactionFinance.
    - files: request.FILES.getlist("justificatifs")
    """
    if not files:
        return

    from core.models import TransactionJustificatif  # import local

    tp = (type_piece or "AUTRE").strip().upper()
    allowed = {"RECU", "CHEQUE", "VIREMENT", "AUTRE"}
    if tp not in allowed:
        tp = "AUTRE"

    for f in files:
        TransactionJustificatif.objects.create(
            tx=tx,
            type_piece=tp,
            fichier=f,
            original_name=getattr(f, "name", "") or "",
        )

def _eleve_active_filter_q() -> Q:
    """
    ✅ Filtre robuste des élèves actifs selon ton modèle.
    Champs essayés (dans cet ordre) :
    - is_active (bool)
    - actif (bool)
    - is_actif (bool)
    - statut (str) attendu "ACTIF"/"INACTIF" (si tu l’utilises)
    """
    if _has_field(Eleve, "is_active"):
        return Q(eleve__is_active=True)
    if _has_field(Eleve, "actif"):
        return Q(eleve__actif=True)
    if _has_field(Eleve, "is_actif"):
        return Q(eleve__is_actif=True)
    if _has_field(Eleve, "statut"):
        # adapte si tu as "A"/"I" etc.
        return Q(eleve__statut__in=["ACTIF", "Actif", "active", "ACTIVE"])
    # si aucun champ trouvé -> on ne filtre pas (mais au moins ça ne casse pas)
    return Q()


def _eleve_is_active_obj(e: Eleve) -> bool:
    """Même logique mais côté objet."""
    if hasattr(e, "is_active"):
        return bool(getattr(e, "is_active"))
    if hasattr(e, "actif"):
        return bool(getattr(e, "actif"))
    if hasattr(e, "is_actif"):
        return bool(getattr(e, "is_actif"))
    if hasattr(e, "statut"):
        return str(getattr(e, "statut") or "").upper() in {"ACTIF", "ACTIVE"}
    return True


def _parent_full_name(parent_obj) -> str:
    """Parent peut être Parent(nom/prenom) ou User(first_name/last_name)."""
    if not parent_obj:
        return ""

    nom = (getattr(parent_obj, "nom", "") or "").strip()
    prenom = (getattr(parent_obj, "prenom", "") or "").strip()
    if nom or prenom:
        return f"{nom} {prenom}".strip()

    first = (getattr(parent_obj, "first_name", "") or "").strip()
    last = (getattr(parent_obj, "last_name", "") or "").strip()
    if first or last:
        return f"{last} {first}".strip()

    return ""


def _build_parent_map_from_eleve_ids(eleve_ids):
    """Retourne { eleve_id: 'NOM Prénom' } en 1 requête."""
    if not eleve_ids:
        return {}

    qs = (
        ParentEleve.objects
        .filter(eleve_id__in=list(set(eleve_ids)))
        .select_related("parent")
    )

    mp = {}
    for pe in qs:
        label = _parent_full_name(getattr(pe, "parent", None))
        if label:
            mp[pe.eleve_id] = label
    return mp


def _annotate_refund_flags(qs):
    """
    Ajoute:
    - montant_rembourse
    - is_rembourse
    - is_rembourse_partiel
    - is_annulee_zero
    """
    qs = qs.prefetch_related("remboursements").annotate(
        montant_rembourse=Coalesce(
            Sum("remboursements__montant"),
            Value(Decimal("0.00")),
            output_field=DecimalField(max_digits=10, decimal_places=2),
        ),
        has_annulation=Exists(
            RemboursementFinance.objects.filter(
                transaction_id=OuterRef("pk"),
                is_annulation=True
            )
        ),
    ).annotate(
        is_rembourse=Case(
            When(
                montant_total__gt=Value(Decimal("0.00")),
                montant_rembourse__gte=F("montant_total"),
                then=Value(True),
            ),
            default=Value(False),
            output_field=BooleanField(),
        ),
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
        is_annulee_zero=Case(
            When(
                montant_total=Value(Decimal("0.00")),
                has_annulation=True,
                then=Value(True),
            ),
            default=Value(False),
            output_field=BooleanField(),
        ),
    )
    return qs


# =========================================================
# 1) Détail finance inscription
# =========================================================
@login_required
@group_required("SUPER_ADMIN", "ADMIN", "COMPTABLE")
def inscription_finance_detail(request, inscription_id: int):
    insc = get_object_or_404(
        Inscription.objects.select_related(
            "eleve", "annee", "groupe", "groupe__niveau", "groupe__niveau__degre", "periode"
        ),
        pk=inscription_id
    )

    echeances = (
        EcheanceMensuelle.objects
        .filter(eleve_id=insc.eleve_id, annee_id=insc.annee_id)
        .order_by("mois_index")
    )

    # si tu as insc.paiements (relation), garde; sinon enlève
    paiements = getattr(insc, "paiements", None)
    paiements = paiements.select_related("echeance").all() if paiements is not None else []

    total_mensuel_du = sum((e.montant_du or Decimal("0.00")) for e in echeances)
    total_mensuel_paye = sum((e.montant_paye or Decimal("0.00")) for e in echeances)
    total_mensuel_reste = total_mensuel_du - total_mensuel_paye

    total_insc_du = insc.frais_inscription_du or Decimal("0.00")
    total_insc_paye = insc.frais_inscription_paye or Decimal("0.00")
    total_insc_reste = getattr(insc, "reste_inscription", total_insc_du - total_insc_paye)

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

# =========================================================
# 3) API — groupes par niveau (année active)
# =========================================================
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


# =========================================================
# 4) AJAX — inscription by élève + fratrie (FILTRÉ actifs)
# =========================================================
@login_required
@group_required("SUPER_ADMIN", "ADMIN", "COMPTABLE", "SCOLARITE")
def ajax_inscription_by_eleve(request):
    """
    GET ?eleve_id=XX
    -> retourne inscription année active + fratrie (même parent)
    ✅ Ne renvoie JAMAIS un élève inactif dans la fratrie
    """
    eleve_id = (request.GET.get("eleve_id") or "").strip()
    if not eleve_id.isdigit():
        return JsonResponse({"inscription_id": None, "fratrie": []})

    annee_active = AnneeScolaire.objects.filter(is_active=True).first()
    if not annee_active:
        return JsonResponse({"inscription_id": None, "fratrie": []})

    # ✅ si l'élève est inactif -> rien
    eleve = Eleve.objects.filter(id=int(eleve_id)).first()
    if not eleve or not _eleve_is_active_obj(eleve):
        return JsonResponse({"inscription_id": None, "fratrie": []})

    insc = (
        Inscription.objects
        .select_related("groupe")
        .filter(eleve_id=int(eleve_id), annee_id=annee_active.id)
        .first()
    )

    parent_ids = (
        ParentEleve.objects
        .filter(eleve_id=int(eleve_id))
        .values_list("parent_id", flat=True)
    )

    fratrie_ids = (
        ParentEleve.objects
        .filter(parent_id__in=parent_ids)
        .exclude(eleve_id=int(eleve_id))
        .values_list("eleve_id", flat=True)
        .distinct()
    )

    fratrie_qs = (
        Eleve.objects
        .filter(id__in=fratrie_ids)
        .order_by("nom", "prenom")
    )

    # ✅ filtre actifs
    fratrie = []
    for e in fratrie_qs:
        if not _eleve_is_active_obj(e):
            continue

        insc2 = (
            Inscription.objects
            .filter(eleve_id=e.id, annee_id=annee_active.id)
            .select_related("groupe")
            .first()
        )

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


# =========================================================
# 5) API — fratrie (FILTRÉ actifs)
# =========================================================
@login_required
@group_required("SUPER_ADMIN", "ADMIN", "COMPTABLE", "SCOLARITE")
def api_fratrie(request):
    """
    GET /core/api/fratrie/?eleve_id=XX
    -> {results:[{id,label,groupe}]}
    ✅ Ne renvoie JAMAIS un élève inactif
    """
    eleve_id = (request.GET.get("eleve_id") or "").strip()
    if not eleve_id.isdigit():
        return JsonResponse({"results": []})

    eleve_id = int(eleve_id)

    # ✅ refuse si élève inactif
    e0 = Eleve.objects.filter(id=eleve_id).first()
    if not e0 or not _eleve_is_active_obj(e0):
        return JsonResponse({"results": []})

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
        if not _eleve_is_active_obj(e):
            continue

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


# =========================================================
# 6) Page raccourci — ouvrir wizard pré-rempli
# =========================================================
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


# =========================================================
# 7) Wizard
# =========================================================
@login_required
@permission_required("core.view_transactionfinance", raise_exception=True)
def transaction_wizard(request):
    niveaux = Niveau.objects.select_related("degre").order_by("degre__ordre", "ordre", "nom")

    inscription_id = (request.GET.get("inscription_id") or "").strip()
    type_pref = (request.GET.get("type") or "").strip().upper()

    prefill = {
        "eleve_id": request.GET.get("eleve_id", ""),
        "niveau_id": request.GET.get("niveau_id", ""),
        "groupe_id": request.GET.get("groupe_id", ""),
        "inscription_id": inscription_id,
        "type": type_pref,
    }

    if inscription_id.isdigit():
        insc = (
            Inscription.objects
            .select_related("eleve", "groupe", "groupe__niveau")
            .filter(id=int(inscription_id))
            .first()
        )
        if insc and _eleve_is_active_obj(insc.eleve):
            prefill.update({
                "eleve_id": str(insc.eleve_id),
                "niveau_id": str(insc.groupe.niveau_id),
                "groupe_id": str(insc.groupe_id),
            })
        else:
            # élève inactif => on ne préremplit pas
            prefill.update({"eleve_id": "", "niveau_id": "", "groupe_id": "", "inscription_id": ""})

    return render(request, "admin/paiements/wizard.html", {"niveaux": niveaux, "prefill": prefill})


# =========================================================
# 8) APPLY HELPERS (partagés single/batch)
# =========================================================
def _apply_scolarite_for_insc(insc: Inscription, tx: TransactionFinance, payload_obj: dict) -> Decimal:
    selected_ids = payload_obj.get("selected_ids") or []
    prices = payload_obj.get("prices") or {}

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
        if (e.montant_paye or Decimal("0.00")) > Decimal("0.00") or e.statut == "PAYE":
            raise ValueError(f"{getattr(e, 'mois_nom', e.mois_index)} a déjà un paiement. (Pas de reprise)")

        key = str(e.id)
        m = _D(prices.get(key, e.montant_du), default=Decimal("0.00"))
        if m < 0:
            raise ValueError(f"Montant invalide pour {getattr(e, 'mois_nom', e.mois_index)}.")

        TransactionLigne.objects.create(
            transaction=tx,
            echeance=e,
            libelle=f"Scolarité — {getattr(e, 'mois_nom', e.mois_index)}",
            montant=m
        )

        # ✅ m=0 accepté
        e.montant_du = m
        e.montant_paye = m
        if hasattr(e, "refresh_statut"):
            e.refresh_statut(save=False)
        e.save(update_fields=["montant_du", "montant_paye", "statut"])

        total += m

    return total


def _apply_transport_for_insc(insc: Inscription, tx: TransactionFinance, payload_obj: dict) -> Decimal:
    cfg = EleveTransport.objects.filter(eleve_id=insc.eleve_id).first()
    if not cfg or not cfg.enabled:
        raise ValueError("Transport désactivé pour cet élève.")

    selected_ids = payload_obj.get("selected_ids") or []
    prices = payload_obj.get("prices") or {}

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
            raise ValueError(f"Transport {getattr(e, 'mois_nom', e.mois_index)} a déjà un paiement. (Pas de reprise)")

        key = str(e.id)
        m = _D(prices.get(key, e.montant_du), default=Decimal("0.00"))
        if m < 0:
            raise ValueError(f"Montant invalide pour Transport {getattr(e, 'mois_nom', e.mois_index)}.")

        TransactionLigne.objects.create(
            transaction=tx,
            echeance_transport=e,
            libelle=f"Transport — {getattr(e, 'mois_nom', e.mois_index)}",
            montant=m
        )

        # ✅ m=0 accepté
        e.montant_du = m
        e.montant_paye = m
        if hasattr(e, "refresh_statut"):
            e.refresh_statut(save=False)
        e.save(update_fields=["montant_du", "montant_paye", "statut"])

        total += m

    return total


def _apply_inscription_for_insc(insc: Inscription, tx: TransactionFinance, montant: Decimal) -> Decimal:
    max_rest = getattr(insc, "reste_inscription", Decimal("0.00")) or Decimal("0.00")

    if (getattr(insc, "frais_inscription_paye", Decimal("0.00")) or Decimal("0.00")) > Decimal("0.00"):
        raise ValueError("Inscription déjà encaissée. Pas de reprise.")
    if montant < 0 or montant > max_rest:
        raise ValueError(f"Montant inscription invalide. Max = {max_rest} MAD.")

    # ✅ protège: ne jamais mettre mensuel à 0 par erreur
    current_mensuel = getattr(insc, "frais_scolarite_mensuel", Decimal("0.00")) or Decimal("0.00")
    if hasattr(insc, "override_frais_scolarite_mensuel"):
        if (getattr(insc, "override_frais_scolarite_mensuel") or Decimal("0.00")) <= Decimal("0.00"):
            insc.override_frais_scolarite_mensuel = current_mensuel

    insc.tarif_override = True
    if hasattr(insc, "override_frais_inscription_du"):
        insc.override_frais_inscription_du = montant
    insc.frais_inscription_du = montant
    insc.frais_inscription_paye = montant  # one-shot même 0
    insc.save()

    TransactionLigne.objects.create(
        transaction=tx,
        echeance=None,
        libelle="Frais d'inscription",
        montant=montant
    )
    return montant


def _apply_pack_for_insc(insc: Inscription, tx: TransactionFinance, pack: dict) -> Decimal:
    ins_on = bool(pack.get("ins_on", True))
    sco_on = bool(pack.get("sco_on", True))
    tr_on = bool(pack.get("tr_on", True))

    total = Decimal("0.00")

    if ins_on:
        amt = _D(pack.get("ins_amount"), default=Decimal("0.00"))
        total += _apply_inscription_for_insc(insc, tx, amt)

    if sco_on:
        total += _apply_scolarite_for_insc(insc, tx, pack.get("sco") or {})

    if tr_on:
        total += _apply_transport_for_insc(insc, tx, pack.get("tr") or {})

    return total


# =========================================================
# 9) CREATE — Single ou Batch (fratrie)
# =========================================================

@login_required
@require_GET
def ajax_eleve_meta(request):
    """
    GET ?inscription=<id>
    Renvoie niveau/groupe/année + infos élève.
    """
    insc_id = (request.GET.get("inscription") or "").strip()
    if not insc_id.isdigit():
        return JsonResponse({"ok": False, "error": "inscription invalide"}, status=400)

    insc = (
        Inscription.objects
        .select_related("eleve", "annee", "groupe", "groupe__niveau", "groupe__niveau__degre")
        .filter(pk=int(insc_id))
        .first()
    )
    if not insc:
        return JsonResponse({"ok": False, "error": "introuvable"}, status=404)

    e = insc.eleve
    g = insc.groupe
    n = getattr(g, "niveau", None)
    d = getattr(n, "degre", None)

    return JsonResponse({
        "ok": True,
        "eleve": {
            "id": e.id,
            "matricule": getattr(e, "matricule", "") or "",
            "nom": getattr(e, "nom", "") or "",
            "prenom": getattr(e, "prenom", "") or "",
            "actif": bool(_eleve_is_active_obj(e)),
        },
        "annee": {"id": insc.annee_id, "label": str(insc.annee) if insc.annee else ""},
        "degre": {"id": getattr(d, "id", None), "label": getattr(d, "nom", "") if d else ""},
        "niveau": {"id": getattr(n, "id", None), "label": getattr(n, "nom", "") if n else ""},
        "groupe": {"id": getattr(g, "id", None), "label": getattr(g, "nom", "") if g else ""},
    })

# =========================================================
# Helpers
# =========================================================
def _dec_or_none(v):
    s = (v or "").strip().replace(",", ".")
    if s == "":
        return None
    try:
        d = Decimal(s)
    except Exception:
        return None
    if d < Decimal("0"):
        return None
    return d

# =========================================================
# ✅ ECHEANCES SCOLARITE (override via Inscription.sco_default_mensuel)
# GET /core/ajax/echeances/?inscription=ID
# =========================================================
@login_required
@require_GET
def ajax_echeances(request):
    insc_id = (request.GET.get("inscription") or "").strip()
    if not insc_id.isdigit():
        return JsonResponse({"items": [], "tarifs": {}}, status=200)

    insc = get_object_or_404(
        Inscription.objects.select_related("eleve", "annee", "groupe"),
        pk=int(insc_id)
    )

    # ✅ sécurité: si élève inactif -> vide
    if not _eleve_is_active_obj(insc.eleve):
        return JsonResponse({"items": [], "tarifs": {}}, status=200)

    # ✅ override mensuel (ce que tu veux)
    sco_default = getattr(insc, "sco_default_mensuel", None)  # Decimal | None

    qs = (
        EcheanceMensuelle.objects
        .filter(eleve_id=insc.eleve_id, annee_id=insc.annee_id)
        .order_by("mois_index")
    )

    items = []
    for e in qs:
        is_paye = (e.statut == "PAYE")

        # 🔥 SI override défini -> on l’affiche partout sur les échéances NON payées
        if (not is_paye) and (sco_default is not None):
            du = sco_default
        else:
            du = e.montant_du or Decimal("0.00")

        items.append({
            "id": e.id,
            "mois_index": int(e.mois_index),
            "mois_nom": getattr(e, "mois_nom", str(e.mois_index)),
            "du": str(du),
            "is_paye": bool(is_paye),
            "statut": e.statut,
            "date_echeance": str(e.date_echeance),
        })

    tarifs = {
        "frais_scolarite_mensuel": str(getattr(insc, "frais_scolarite_mensuel", Decimal("0.00")) or Decimal("0.00")),
        "reste_inscription": str(getattr(insc, "reste_inscription", Decimal("0.00")) or Decimal("0.00")),
        "tarif_override": bool(getattr(insc, "tarif_override", False)),

        # ✅ NEW: prix par défaut saisi par comptable (peut être null)
        "sco_default_mensuel": str(getattr(insc, "sco_default_mensuel", None) or ""),
    }


    return JsonResponse({"items": items, "tarifs": tarifs}, status=200)


# =========================================================
# ✅ ECHEANCES TRANSPORT (override via Inscription.tr_default_mensuel)
# GET /core/ajax/transport-echeances/?inscription=ID
# =========================================================
@login_required
@permission_required("core.view_anneescolaire", raise_exception=True)
@require_GET
def ajax_transport_echeances(request):
    insc_id = (request.GET.get("inscription") or "").strip()
    if not insc_id.isdigit():
        return JsonResponse({"enabled": False, "items": [], "tarif_mensuel": "0.00", "tr_default_mensuel": ""}, status=200)

    insc = get_object_or_404(
        Inscription.objects.select_related("eleve", "annee", "groupe"),
        pk=int(insc_id)
    )

    tr = getattr(insc.eleve, "transport", None)
    if not tr or not tr.enabled:
        return JsonResponse({"enabled": False, "items": [], "tarif_mensuel": "0.00", "tr_default_mensuel": ""}, status=200)

    tr_default = getattr(insc, "tr_default_mensuel", None)  # Decimal | None

    qs = (
        EcheanceTransportMensuelle.objects
        .filter(eleve_id=insc.eleve_id, annee_id=insc.annee_id)
        .order_by("mois_index")
    )

    items = []
    for e in qs:
        is_paye = (e.statut == "PAYE")

        if (not is_paye) and (tr_default is not None):
            du = tr_default
        else:
            du = e.montant_du or Decimal("0.00")

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
        # ✅ NEW
        "tr_default_mensuel": str(getattr(insc, "tr_default_mensuel", None) or ""),
        "items": items
    }, status=200)


# =========================================================
# ✅ SAVE DEFAULT PRICES (appelés par le JS)
# POST JSON: { inscription_id, amount }
# =========================================================
@login_required
@permission_required("core.change_inscription", raise_exception=True)
@require_POST
def ajax_set_default_sco_price(request):
    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except Exception:
        payload = {}

    insc_id = payload.get("inscription_id")
    amount = _dec_or_none(payload.get("amount"))

    if not insc_id:
        return JsonResponse({"ok": False, "error": "inscription_id manquant"}, status=400)

    insc = get_object_or_404(Inscription.objects.select_related("eleve"), pk=int(insc_id))

    if not _eleve_is_active_obj(insc.eleve):
        return JsonResponse({"ok": False, "error": "Élève inactif"}, status=403)

    insc.sco_default_mensuel = amount
    insc.save(update_fields=["sco_default_mensuel"])

    return JsonResponse({"ok": True, "value": str(insc.sco_default_mensuel or "")})


@login_required
@permission_required("core.change_inscription", raise_exception=True)
@require_POST
def ajax_set_default_tr_price(request):
    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except Exception:
        payload = {}

    insc_id = payload.get("inscription_id")
    amount = _dec_or_none(payload.get("amount"))

    if not insc_id:
        return JsonResponse({"ok": False, "error": "inscription_id manquant"}, status=400)

    insc = get_object_or_404(Inscription.objects.select_related("eleve"), pk=int(insc_id))

    if not _eleve_is_active_obj(insc.eleve):
        return JsonResponse({"ok": False, "error": "Élève inactif"}, status=403)

    insc.tr_default_mensuel = amount
    insc.save(update_fields=["tr_default_mensuel"])

    return JsonResponse({"ok": True, "value": str(insc.tr_default_mensuel or "")})



@login_required
@permission_required("core.add_transactionfinance", raise_exception=True)
@transaction.atomic
def transaction_create(request):
    if request.method != "POST":
        return redirect("core:transaction_wizard")

    batch_raw = (request.POST.get("batch_payload") or "").strip()
    if batch_raw:
        return _transaction_create_batch(request, batch_raw)

    tx_type = (request.POST.get("type_transaction") or "SCOLARITE").strip().upper()
    inscription_id = (request.POST.get("inscription_id") or "").strip()
    mode = (request.POST.get("mode") or "ESPECES").strip()
    reference = (request.POST.get("reference") or "").strip()
    note = (request.POST.get("note") or "").strip()

    # justificatifs (Option A)
    justifs = request.FILES.getlist("justificatifs")
    justif_type = (request.POST.get("justificatif_type") or "AUTRE").strip().upper()

    # ✅ Tarif (nouveau)
    tarif_id = (request.POST.get("tarif_id") or "").strip()
    save_tarif = (request.POST.get("save_tarif") or "").strip() == "1"

    if not inscription_id.isdigit():
        messages.error(request, "Inscription invalide.")
        return redirect("core:transaction_wizard")

    insc = get_object_or_404(
        Inscription.objects.select_related(
            "eleve", "annee", "groupe", "groupe__niveau", "groupe__niveau__degre"
        ),
        pk=int(inscription_id)
    )

    # ✅ stop net si élève inactif
    if not _eleve_is_active_obj(insc.eleve):
        messages.error(request, "Élève inactif : paiement impossible.")
        return redirect("core:transaction_wizard")

    # ✅ Sauvegarder le tarif sur l'inscription (si demandé)
    if save_tarif and tarif_id.isdigit():
        t = Tarification.objects.filter(pk=int(tarif_id), is_active=True).first()
        if t:
            insc.tarification = t
            insc.save(update_fields=["tarification"])

    parent_owner = get_primary_parent_for_eleve(insc.eleve_id)
    batch_token = str(uuid.uuid4())

    tx = TransactionFinance.objects.create(
        parent=parent_owner,
        inscription=insc,
        type_transaction=tx_type,
        montant_total=Decimal("0.00"),
        mode=mode,
        reference=reference,
        note=note,
        batch_token=batch_token,
    )

    # ✅ Sauvegarde justificatifs
    _save_tx_justificatifs(tx, justifs, justif_type)

    try:
        if tx_type == "INSCRIPTION":
            montant = _D(request.POST.get("montant_inscription"), default=Decimal("0.00"))
            total = _apply_inscription_for_insc(insc, tx, montant)

        elif tx_type == "SCOLARITE":
            payload = json.loads(request.POST.get("echeances_payload") or "{}")
            total = _apply_scolarite_for_insc(insc, tx, payload)

        elif tx_type == "TRANSPORT":
            payload = json.loads(request.POST.get("transport_payload") or "{}")
            total = _apply_transport_for_insc(insc, tx, payload)

        elif tx_type == "PACK":
            pack = json.loads(request.POST.get("pack_payload") or "{}")
            total = _apply_pack_for_insc(insc, tx, pack)

        else:
            raise ValueError("Type de transaction invalide.")

    except ValueError as e:
        messages.error(request, str(e))
        return redirect("core:transaction_wizard")
    except Exception:
        messages.error(request, "Erreur payload transaction.")
        return redirect("core:transaction_wizard")

    tx.montant_total = total
    tx.save(update_fields=["montant_total"])
    assign_receipt_seq_for_batch(batch_token)

    messages.success(request, "Transaction enregistrée ✅")
    return redirect("core:transaction_success", tx_id=tx.id)


def _transaction_create_batch(request, batch_raw: str):
    try:
        batch = json.loads(batch_raw)
        if not isinstance(batch, dict):
            batch = {}
    except Exception:
        batch = {}

    tx_type = (batch.get("type_transaction") or "SCOLARITE").strip().upper()
    items = batch.get("items") or []
    if not isinstance(items, list) or not items:
        messages.error(request, "Batch vide.")
        return redirect("core:transaction_wizard")

    clean_items = []
    for it in items:
        if not isinstance(it, dict):
            continue
        try:
            insc_id = int(it.get("inscription_id"))
        except Exception:
            continue
        it["_insc_id"] = insc_id
        clean_items.append(it)

    if not clean_items:
        messages.error(request, "Batch vide.")
        return redirect("core:transaction_wizard")

    mode = (request.POST.get("mode") or "ESPECES").strip()
    reference = (request.POST.get("reference") or "").strip()
    note = (request.POST.get("note") or "").strip()

    # justificatifs (Option A)
    justifs = request.FILES.getlist("justificatifs")
    justif_type = (request.POST.get("justificatif_type") or "AUTRE").strip().upper()

    # ✅ Tarif (nouveau)
    tarif_id = (request.POST.get("tarif_id") or "").strip()
    save_tarif = (request.POST.get("save_tarif") or "").strip() == "1"
    tarif_obj = None
    if save_tarif and tarif_id.isdigit():
        tarif_obj = Tarification.objects.filter(pk=int(tarif_id), is_active=True).first()

    # ✅ SINGLE direct
    if len(clean_items) == 1:
        it = clean_items[0]
        insc = get_object_or_404(
            Inscription.objects.select_related(
                "eleve", "annee", "groupe", "groupe__niveau", "groupe__niveau__degre"
            ),
            pk=it["_insc_id"]
        )

        if not _eleve_is_active_obj(insc.eleve):
            messages.error(request, "Élève inactif : paiement impossible.")
            return redirect("core:transaction_wizard")

        # ✅ sauvegarde tarif sur inscription
        if tarif_obj:
            insc.tarification = tarif_obj
            insc.save(update_fields=["tarification"])

        parent_owner = get_primary_parent_for_eleve(insc.eleve_id)
        batch_token = str(uuid.uuid4())

        tx = TransactionFinance.objects.create(
            parent=parent_owner,
            inscription=insc,
            type_transaction=tx_type,
            montant_total=Decimal("0.00"),
            mode=mode,
            reference=reference,
            note=note,
            batch_token=batch_token
        )

        _save_tx_justificatifs(tx, justifs, justif_type)

        try:
            if tx_type == "SCOLARITE":
                total = _apply_scolarite_for_insc(insc, tx, it.get("echeances_payload") or {})
            elif tx_type == "TRANSPORT":
                total = _apply_transport_for_insc(insc, tx, it.get("transport_payload") or {})
            elif tx_type == "INSCRIPTION":
                total = _apply_inscription_for_insc(
                    insc, tx, _D(it.get("montant_inscription"), default=Decimal("0.00"))
                )
            elif tx_type == "PACK":
                total = _apply_pack_for_insc(insc, tx, it.get("pack_payload") or {})
            else:
                raise ValueError("Type batch invalide.")
        except ValueError as e:
            messages.error(request, str(e))
            return redirect("core:transaction_wizard")

        tx.montant_total = total
        tx.save(update_fields=["montant_total"])
        assign_receipt_seq_for_batch(batch_token)

        messages.success(request, "Paiement enregistré ✅")
        return redirect("core:transaction_success", tx_id=tx.id)

    # ✅ BATCH réel
    batch_token = str(uuid.uuid4())
    created_ids = []

    for it in clean_items:
        insc = get_object_or_404(
            Inscription.objects.select_related(
                "eleve", "annee", "groupe", "groupe__niveau", "groupe__niveau__degre"
            ),
            pk=it["_insc_id"]
        )

        if not _eleve_is_active_obj(insc.eleve):
            messages.error(request, f"Élève inactif : {insc.eleve.nom} {insc.eleve.prenom} (batch annulé).")
            return redirect("core:transaction_wizard")

        # ✅ sauvegarde tarif sur chaque inscription du batch
        if tarif_obj:
            insc.tarification = tarif_obj
            insc.save(update_fields=["tarification"])

        parent_owner = get_primary_parent_for_eleve(insc.eleve_id)

        tx = TransactionFinance.objects.create(
            parent=parent_owner,
            inscription=insc,
            type_transaction=tx_type,
            montant_total=Decimal("0.00"),
            mode=mode,
            reference=reference,
            note=note,
            batch_token=batch_token
        )

        _save_tx_justificatifs(tx, justifs, justif_type)

        try:
            if tx_type == "SCOLARITE":
                total = _apply_scolarite_for_insc(insc, tx, it.get("echeances_payload") or {})
            elif tx_type == "TRANSPORT":
                total = _apply_transport_for_insc(insc, tx, it.get("transport_payload") or {})
            elif tx_type == "INSCRIPTION":
                total = _apply_inscription_for_insc(
                    insc, tx, _D(it.get("montant_inscription"), default=Decimal("0.00"))
                )
            elif tx_type == "PACK":
                total = _apply_pack_for_insc(insc, tx, it.get("pack_payload") or {})
            else:
                raise ValueError("Type batch invalide.")
        except ValueError as e:
            messages.error(request, str(e))
            return redirect("core:transaction_wizard")

        tx.montant_total = total
        tx.save(update_fields=["montant_total"])
        created_ids.append(tx.id)

    if not created_ids:
        messages.error(request, "Aucune transaction créée.")
        return redirect("core:transaction_wizard")

    assign_receipt_seq_for_batch(batch_token)

    messages.success(request, "Paiement fratrie enregistré ✅ (reçu unique)")
    return redirect("core:transaction_batch_success", batch_token=batch_token)

# =========================================================
# 10) SUCCESS (single/batch)
# =========================================================
@login_required
@permission_required("core.view_transactionfinance", raise_exception=True)
def transaction_success(request, tx_id=None, batch_token=None):
    ctx = {
        "mode": None,
        "tx": None,
        "txs": None,
        "batch_token": None,
        "total": Decimal("0.00"),
        "parent_label": "",
        
    }

    if batch_token:
        base = (
            TransactionFinance.objects
            .select_related(
                "inscription", "inscription__eleve", "inscription__annee",
                "inscription__groupe", "inscription__groupe__niveau",
                "inscription__groupe__niveau__degre",
            )
            .prefetch_related(
                "lignes", "lignes__echeance", "lignes__echeance_transport",
                "justificatifs"  # ✅ NEW
            )
            .filter(batch_token=batch_token)
            .order_by("id")
        )

        txs = _annotate_refund_flags(base)
        if not txs.exists():
            messages.error(request, "Paiement introuvable.")
            return redirect("core:transaction_wizard")

        total = sum((t.montant_total or Decimal("0.00")) for t in txs)

        eleve_ids = list(txs.values_list("inscription__eleve_id", flat=True))
        parent_map = _build_parent_map_from_eleve_ids(eleve_ids)

        for t in txs:
            eid = getattr(t.inscription, "eleve_id", None)
            t.parent_label = parent_map.get(eid, "") if eid else ""

            mt = t.montant_total or Decimal("0.00")
            if mt == Decimal("0.00"):
                t.can_refund = (not getattr(t, "is_annulee_zero", False))
            else:
                remb = getattr(t, "montant_rembourse", Decimal("0.00")) or Decimal("0.00")
                t.can_refund = remb < mt

        parent_label = ""
        for t in txs:
            if getattr(t, "parent_label", ""):
                parent_label = t.parent_label
                break

        ctx.update({
            "mode": "BATCH",
            "txs": txs,
            "batch_token": batch_token,
            "total": total,
            "parent_label": parent_label,
            "group_key": batch_token,
        })
        return render(request, "admin/paiements/transaction_success.html", ctx)

    if tx_id:
        base = (
            TransactionFinance.objects
            .select_related(
                "inscription", "inscription__eleve", "inscription__annee",
                "inscription__groupe", "inscription__groupe__niveau",
                "inscription__groupe__niveau__degre",
            )
            .prefetch_related(
                "lignes", "lignes__echeance", "lignes__echeance_transport",
                "justificatifs"  # ✅ NEW
            )
        )

        tx = get_object_or_404(_annotate_refund_flags(base), pk=tx_id)

        eleve_id = getattr(tx.inscription, "eleve_id", None)
        parent_map = _build_parent_map_from_eleve_ids([eleve_id] if eleve_id else [])
        parent_label = parent_map.get(eleve_id, "") if eleve_id else ""

        mt = tx.montant_total or Decimal("0.00")
        if mt == Decimal("0.00"):
            tx.can_refund = (not getattr(tx, "is_annulee_zero", False))
        else:
            remb = getattr(tx, "montant_rembourse", Decimal("0.00")) or Decimal("0.00")
            tx.can_refund = remb < mt

        ctx.update({
            "mode": "SINGLE",
            "tx": tx,
            "total": mt,
            "parent_label": parent_label,
            "group_key": f"TX-{tx.id}",
        })
        return render(request, "admin/paiements/transaction_success.html", ctx)

    return redirect("core:transaction_wizard")


# =========================================================
# 11) PDF single / batch
# =========================================================
@login_required
@group_required("SUPER_ADMIN", "ADMIN", "COMPTABLE", "SCOLARITE")
def transaction_pdf(request, tx_id: int):
    tx = get_object_or_404(
        TransactionFinance.objects
        .select_related(
            "inscription", "inscription__eleve", "inscription__annee",
            "inscription__groupe", "inscription__groupe__niveau", "inscription__groupe__niveau__degre"
        )
        .prefetch_related("lignes", "lignes__echeance", "lignes__echeance_transport", "justificatifs"),
        pk=tx_id
    )
    from core.pdf.transaction import build_transaction_pdf_bytes
    pdf_bytes = build_transaction_pdf_bytes(tx)
    resp = HttpResponse(pdf_bytes, content_type="application/pdf")
    resp["Content-Disposition"] = f'inline; filename="transaction_{tx.id}.pdf"'
    return resp


@login_required
@permission_required("core.view_transactionfinance", raise_exception=True)
def transaction_batch_pdf(request, batch_token: str):
    txs = (
        TransactionFinance.objects
        .select_related(
            "inscription", "inscription__eleve", "inscription__annee",
            "inscription__groupe", "inscription__groupe__niveau", "inscription__groupe__niveau__degre"
        )
        .prefetch_related("lignes", "lignes__echeance", "lignes__echeance_transport", "justificatifs")
        .filter(batch_token=batch_token)
        .order_by("id")
    )
    if not txs.exists():
        return HttpResponse("Batch introuvable.", status=404)

    from core.pdf.transaction import build_transaction_batch_pdf_bytes
    pdf_bytes = build_transaction_batch_pdf_bytes(list(txs), batch_token=batch_token)

    resp = HttpResponse(pdf_bytes, content_type="application/pdf")
    resp["Content-Disposition"] = f'inline; filename="transactions_{batch_token}.pdf"'
    return resp


# =========================================================
# 12) API — élèves par groupe (FILTRÉ actifs)
# =========================================================
@login_required
@group_required("SUPER_ADMIN", "ADMIN", "COMPTABLE", "SCOLARITE")
def api_eleves_par_groupe(request):
    groupe_id = (request.GET.get("groupe_id") or "").strip()
    if not groupe_id.isdigit():
        return JsonResponse({"results": []})

    g = get_object_or_404(Groupe, pk=int(groupe_id))

    inscs = (
        Inscription.objects
        .filter(groupe_id=g.id, annee_id=g.annee_id)
        .select_related("eleve")
        .filter(_eleve_active_filter_q())  # ✅ filtre actifs
        .order_by("eleve__nom", "eleve__prenom")
    )

    results = []
    for i in inscs:
        e = i.eleve
        results.append({
            "id": e.id,
            "label": f'{(e.matricule or "").strip()} — {e.nom} {e.prenom}'.strip(" —")
        })
    return JsonResponse({"results": results})


# =========================================================
# 13) AJAX — search parents / enfants by parent (FILTRÉ actifs)
# =========================================================

from django.http import JsonResponse
from django.db.models import Q

@login_required
@group_required("SUPER_ADMIN", "ADMIN", "COMPTABLE", "SCOLARITE")
def ajax_parents_search(request):
    q = (request.GET.get("q") or "").strip()

    annee_active = AnneeScolaire.objects.filter(is_active=True).first()
    if not annee_active:
        return JsonResponse({"items": [], "results": []})

    # ✅ Filtre: parent actif + au moins 1 élève actif + inscription VALIDEE année active
    qs = (
        Parent.objects
        .filter(is_active=True)
        .filter(
            liens__eleve__inscriptions__annee=annee_active,
            liens__eleve__inscriptions__statut__in=["VALIDEE", "EN_COURS"],
        )
        .distinct()
    )

    # ✅ Si tu as un helper "élève actif", mets-le ici.
    # Si ton helper ne supporte pas prefix, commente cette ligne.
    try:
        qs = qs.filter(_eleve_active_filter_q(prefix="liens__eleve__"))
    except TypeError:
        # helper sans prefix -> on ignore pour éviter de tout casser
        pass

    if q:
        qs = qs.filter(
            Q(nom__icontains=q) |
            Q(prenom__icontains=q) |
            Q(telephone__icontains=q) |
            Q(telephone_norm__icontains=q) |
            Q(email__icontains=q)
        )

    qs = qs.order_by("nom", "prenom")[:50]

    items = []
    for p in qs:
        label = f"{p.nom} {p.prenom}".strip()
        tel = (p.telephone or "").strip()
        if tel:
            label = f"{label} — {tel}"
        items.append({"id": p.id, "label": label})

    # ✅ renvoyer items + results pour compat TomSelect
    return JsonResponse({"items": items, "results": items})


@login_required
@group_required("SUPER_ADMIN", "ADMIN", "COMPTABLE", "SCOLARITE")
def ajax_enfants_by_parent(request):
    parent_id = (request.GET.get("parent_id") or "").strip()
    if not parent_id.isdigit():
        return JsonResponse({"items": []})

    annee_active = AnneeScolaire.objects.filter(is_active=True).first()
    if not annee_active:
        return JsonResponse({"items": []})

    eleve_ids = list(
        ParentEleve.objects.filter(parent_id=int(parent_id))
        .values_list("eleve_id", flat=True)
        .distinct()
    )
    if not eleve_ids:
        return JsonResponse({"items": []})

    # ✅ uniquement inscriptions VALIDEE sur année active + élève actif
    insc_qs = (
        Inscription.objects
        .select_related("groupe", "eleve")
        .filter(annee_id=annee_active.id, eleve_id__in=eleve_ids, statut="VALIDEE")
        .filter(_eleve_active_filter_q())  # ton helper actuel
    )

    insc_map = {i.eleve_id: i for i in insc_qs}
    allowed_eleve_ids = list(insc_map.keys())
    if not allowed_eleve_ids:
        return JsonResponse({"items": []})

    items = []
    for e in Eleve.objects.filter(id__in=allowed_eleve_ids).order_by("nom", "prenom"):
        if not _eleve_is_active_obj(e):
            continue
        insc = insc_map.get(e.id)
        items.append({
            "eleve_id": e.id,
            "inscription_id": insc.id,
            "label": f"{e.matricule} — {e.nom} {e.prenom}".strip(),
        })

    return JsonResponse({"items": items})
