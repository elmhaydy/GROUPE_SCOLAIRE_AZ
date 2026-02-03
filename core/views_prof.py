# core/views_prof.py
from __future__ import annotations

from decimal import Decimal
from datetime import time

from django.contrib import messages
from django.db import IntegrityError
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.utils.timezone import localdate
from django.views.decorators.http import require_GET
from requests import request

from accounts.decorators import prof_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash

from core.forms_prof import ProfCahierTexteForm, ProfResumePDFForm, ProfEvaluationForm
from core.models import (
    Absence,
    AnneeScolaire,
    CahierTexte,
    CoursResumePDF,
    Evaluation,
    Groupe,
    Inscription,
    Matiere,
    Note,
    Periode,
    ProfGroupe,
    EnseignantGroupe,
    Seance,
)

# =========================================================
# Helpers (centrale)
# =========================================================
def _get_annee_active():
    return AnneeScolaire.objects.filter(is_active=True).first()


def _allowed_groupes(user, annee_id=None):
    """
    ✅ SAFE (AZ):
    - Les GROUPES d'un prof viennent UNIQUEMENT des affectations "group-only"
      => EnseignantGroupe(matiere_fk IS NULL)
    - Si annee_id fourni => filtre strict
    - Sinon => année active par défaut
    """
    active = _get_annee_active()
    default_annee_id = annee_id or (active.id if active else None)

    ens = getattr(user, "enseignant_profile", None)

    if ens:
        aff = (
            EnseignantGroupe.objects
            .filter(enseignant=ens, matiere_fk__isnull=True)  # ✅ IMPORTANT
        )
        if default_annee_id:
            aff = aff.filter(annee_id=default_annee_id)

        ids = aff.values_list("groupe_id", flat=True).distinct()
    else:
        # compat si jamais tu gardes ProfGroupe
        ids = (
            ProfGroupe.objects
            .filter(user=user)
            .values_list("groupe_id", flat=True)
            .distinct()
        )

    qs = (
        Groupe.objects
        .filter(id__in=ids)
        .select_related("annee", "niveau", "niveau__degre")
    )
    if default_annee_id:
        qs = qs.filter(annee_id=default_annee_id)

    return qs


def _allowed_groupes_for_user(user, annee_id: str | None = None):
    return _allowed_groupes(user, annee_id=annee_id)


def _require_groupe_allowed(user, groupe: Groupe) -> bool:
    """
    ✅ SAFE:
    - autorisation groupe = seulement group-only
    - évite qu'une ligne (matiere_fk != NULL) donne accès à un groupe
    """
    ens = getattr(user, "enseignant_profile", None)
    if ens:
        return EnseignantGroupe.objects.filter(
            enseignant=ens,
            groupe=groupe,
            matiere_fk__isnull=True,   # ✅ IMPORTANT
        ).exists()

    return ProfGroupe.objects.filter(user=user, groupe=groupe).exists()





def _matieres_for_groupes(groupes_qs):
    niveau_ids = list(groupes_qs.values_list("niveau_id", flat=True).distinct())
    if not niveau_ids:
        return Matiere.objects.none()
    return Matiere.objects.filter(is_active=True, niveaux__in=niveau_ids).distinct().order_by("nom")


def _matieres_for_prof(user, groupes_qs):
    """
    MATIERES du prof (robuste) :
    ✅ via EnseignantGroupe.matiere_fk (FK)
    Fallback : matières des niveaux des groupes (optionnel)
    """
    ens = getattr(user, "enseignant_profile", None)

    if ens:
        qs = (
            Matiere.objects
            .filter(
                is_active=True,
                affectations_enseignants_groupes__enseignant=ens,
                affectations_enseignants_groupes__groupe__in=groupes_qs,
                affectations_enseignants_groupes__matiere_fk__isnull=False,
            )
            .distinct()
            .order_by("nom")
        )
        if qs.exists():
            return qs

    # fallback si tu veux afficher quelque chose quand pas d'affectation FK
    return _matieres_for_groupes(groupes_qs)


def _safe_decimal(raw: str) -> Decimal | None:
    raw = (raw or "").strip().replace(",", ".")
    if raw == "":
        return None
    try:
        return Decimal(raw)
    except Exception:
        return None


# =========================================================
# ✅ AJAX PROF (ANTI 403)
# =========================================================
# ====== AJAX PROF (FINAL) ======


@prof_required
@require_GET
def prof_ajax_groupes(request):
    """
    Groupes du prof sur l'année active.
    """
    annee = _get_annee_active()
    if not annee:
        return JsonResponse({"results": []})

    groupes = _allowed_groupes(request.user, annee_id=annee.id).order_by(
        "niveau__degre__ordre", "niveau__ordre", "nom"
    )

    return JsonResponse({
        "results": [{"id": g.id, "label": f"{g.annee.nom} — {g.niveau.nom} — {g.nom}"} for g in groupes]
    })


@prof_required
@require_GET
def prof_ajax_periodes(request):
    """
    Périodes basées sur l'année du groupe (si groupe fourni), sinon année active.
    """
    groupe_id = (request.GET.get("groupe") or request.GET.get("groupe_id") or "").strip()

    annee = _get_annee_active()
    if not annee:
        return JsonResponse({"results": []})

    if groupe_id:
        groupes_ok = _allowed_groupes(request.user, annee_id=annee.id)
        g = Groupe.objects.select_related("annee").filter(id=groupe_id, id__in=groupes_ok.values("id")).first()
        if g:
            annee = g.annee

    qs = Periode.objects.filter(annee=annee).order_by("ordre")
    return JsonResponse({"results": [{"id": p.id, "label": p.nom} for p in qs]})


@prof_required
@require_GET
def prof_ajax_matieres(request):
    """
    Matières du prof UNIQUEMENT pour le groupe choisi.
    Source unique: EnseignantGroupe (matiere_fk)
    """
    groupe_id = (request.GET.get("groupe") or request.GET.get("groupe_id") or "").strip()
    if not groupe_id:
        return JsonResponse({"results": []})

    annee_active = _get_annee_active()
    if not annee_active:
        return JsonResponse({"results": []})

    # sécurité: groupe doit être autorisé
    groupes_ok = _allowed_groupes(request.user, annee_id=annee_active.id)
    g = Groupe.objects.select_related("annee").filter(id=groupe_id, id__in=groupes_ok.values("id")).first()
    if not g:
        return JsonResponse({"results": []}, status=403)

    ens = getattr(request.user, "enseignant_profile", None)
    if not ens:
        return JsonResponse({"results": []})

    # année = année du groupe (plus fiable)
    annee = g.annee

    # ✅ on prend les affectations prof->groupe et on extrait les matières FK
    matiere_ids = (
        EnseignantGroupe.objects
        .filter(
            annee=annee,
            groupe_id=groupe_id,
            enseignant=ens,
            matiere_fk__isnull=False,
        )
        .values_list("matiere_fk_id", flat=True)
        .distinct()
    )

    matieres = (
        Matiere.objects
        .filter(is_active=True, id__in=matiere_ids)
        .order_by("nom")
    )

    return JsonResponse({"results": [{"id": m.id, "label": m.nom} for m in matieres]})

# =========================================================
# Dashboard
# =========================================================

@prof_required
def prof_dashboard(request):
    annee_active = _get_annee_active()
    annee_id = str(annee_active.id) if annee_active else None

    groupes = _allowed_groupes(request.user, annee_id=annee_id).select_related("niveau", "niveau__degre")
    nb_groupes = groupes.count()
    today = localdate()

    # ✅ PROF connecté
    ens = getattr(request.user, "enseignant_profile", None)

    # =========================
    # KPIs (UNIQUEMENT ce prof)
    # =========================
    if nb_groupes:
        # Evaluations : par enseignant (recommandé)
        qs_evals = Evaluation.objects.filter(groupe__in=groupes)
        if ens:
            qs_evals = qs_evals.filter(enseignant=ens)
        else:
            # fallback si ton model a un champ "prof"
            qs_evals = qs_evals.filter(prof=request.user)

        kpi_evals = qs_evals.count()
        kpi_evals_today = qs_evals.filter(date=today).count()

        # Cahier : par user
        qs_cahier = CahierTexte.objects.filter(groupe__in=groupes, prof=request.user)
        kpi_cahier = qs_cahier.count()

        # PDF : par user
        qs_pdf = CoursResumePDF.objects.filter(groupe__in=groupes, prof=request.user)
        kpi_pdf = qs_pdf.count()

    else:
        kpi_evals = 0
        kpi_evals_today = 0
        kpi_cahier = 0
        kpi_pdf = 0
        qs_evals = Evaluation.objects.none()
        qs_cahier = CahierTexte.objects.none()
        qs_pdf = CoursResumePDF.objects.none()

    # =========================
    # Derniers éléments (UNIQUEMENT ce prof)
    # =========================
    last_evals = (
        qs_evals
        .select_related("groupe", "groupe__niveau", "groupe__niveau__degre", "matiere", "periode")
        .order_by("-date", "-id")[:6]
    ) if nb_groupes else []

    last_cahier = (
        qs_cahier
        .select_related("groupe", "groupe__niveau", "groupe__niveau__degre", "matiere")
        .order_by("-date", "-id")[:6]
    ) if nb_groupes else []

    last_pdf = (
        qs_pdf
        .select_related("groupe", "groupe__niveau", "groupe__niveau__degre", "matiere")
        .order_by("-date", "-id")[:6]
    ) if nb_groupes else []

    return render(request, "prof/dashboard.html", {
        "annee_active": annee_active,
        "groupes": groupes.order_by("niveau__degre__ordre", "niveau__ordre", "nom"),
        "kpi": {
            "nb_groupes": nb_groupes,
            "evals": kpi_evals,
            "evals_today": kpi_evals_today,
            "cahier": kpi_cahier,
            "pdf": kpi_pdf,
        },
        "last_evals": last_evals,
        "last_cahier": last_cahier,
        "last_pdf": last_pdf,  # ✅ si tu veux aussi afficher les derniers PDFs
        "today": today,
    })


# =========================================================
# Absences (liste)
# =========================================================

@prof_required
def prof_absences(request):
    annee_active = _get_annee_active()
    annee_id = (request.GET.get("annee") or "").strip() or (str(annee_active.id) if annee_active else "")
    groupe_id = (request.GET.get("groupe") or "").strip()
    date_str = (request.GET.get("date") or "").strip()

    groupes = _allowed_groupes(request.user, annee_id=annee_id if annee_id else None)

    absences = (
        Absence.objects
        .select_related("eleve", "groupe", "seance")
        .filter(groupe__in=groupes)
    )

    if groupe_id:
        absences = absences.filter(groupe_id=groupe_id)

    if date_str:
        d = parse_date(date_str)
        if d:
            absences = absences.filter(date=d)
        else:
            messages.warning(request, "⚠️ Date invalide, filtre ignoré.")

    return render(request, "prof/absences.html", {
        "annee_selected": annee_id,
        "groupe_selected": groupe_id,
        "date_selected": date_str,
        "groupes": groupes.order_by("niveau__degre__ordre", "niveau__ordre", "nom"),
        "absences": absences.order_by("-date", "eleve__nom", "eleve__prenom"),
    })


# =========================================================
# Absences (prise d'appel - journée)
# =========================================================

@prof_required
def prof_absences_prise(request):
    annee_active = _get_annee_active()
    if not annee_active:
        messages.error(request, "⚠️ Aucune année scolaire active.")
        return redirect("prof:dashboard")

    groupes = _allowed_groupes(request.user, annee_id=str(annee_active.id))

    groupe_id = (request.GET.get("groupe") or request.POST.get("groupe") or "").strip()
    date_str = (request.GET.get("date") or request.POST.get("date") or "").strip()
    if not date_str:
        date_str = timezone.localdate().isoformat()

    selected_date = parse_date(date_str)
    selected_groupe = None
    eleves = []
    abs_map = {}

    if groupe_id:
        selected_groupe = groupes.filter(id=groupe_id).first()
        if not selected_groupe:
            messages.error(request, "⛔ Groupe non autorisé.")
            return redirect("prof:dashboard")

        inscriptions = (
            Inscription.objects
            .select_related("eleve")
            .filter(annee=annee_active, groupe=selected_groupe)
            .order_by("eleve__nom", "eleve__prenom")
        )
        eleves = [i.eleve for i in inscriptions]

        if selected_date:
            absences = Absence.objects.filter(
                annee=annee_active,
                groupe=selected_groupe,
                date=selected_date,
                seance__isnull=True,
                eleve__in=eleves,
            )
            abs_map = {a.eleve_id: a for a in absences}

    if request.method == "POST":
        if not groupe_id or not selected_date:
            messages.error(request, "⚠️ Groupe ou date invalide.")
            return redirect("prof:absences_prise")

        if not selected_groupe:
            messages.error(request, "⛔ Groupe non autorisé.")
            return redirect("prof:dashboard")

        saved = 0
        removed = 0

        abs_map = {a.eleve_id: a for a in Absence.objects.filter(
            annee=annee_active,
            groupe=selected_groupe,
            date=selected_date,
            seance__isnull=True,
        )}

        for e in eleves:
            checked = request.POST.get(f"abs_{e.id}") == "on"
            typ = (request.POST.get(f"type_{e.id}") or "ABS").strip().upper()
            justifie = request.POST.get(f"just_{e.id}") == "on"
            motif = (request.POST.get(f"motif_{e.id}") or "").strip()

            existing = abs_map.get(e.id)

            if checked:
                Absence.objects.update_or_create(
                    annee=annee_active,
                    eleve=e,
                    groupe=selected_groupe,
                    date=selected_date,
                    seance=None,
                    defaults={
                        "type": typ if typ in ("ABS", "RET") else "ABS",
                        "justifie": justifie,
                        "motif": motif,
                    }
                )
                saved += 1
            else:
                if existing:
                    existing.delete()
                    removed += 1

        messages.success(request, f"✅ Absences enregistrées: {saved} | Présents (lignes supprimées): {removed}")
        return redirect(f"{request.path}?groupe={selected_groupe.id}&date={selected_date.isoformat()}")

    return render(request, "prof/absences_prise.html", {
        "annee_active": annee_active,
        "groupes": groupes.order_by("niveau__degre__ordre", "niveau__ordre", "nom"),
        "groupe_selected": str(selected_groupe.id) if selected_groupe else "",
        "date_selected": selected_date.isoformat() if selected_date else date_str,
        "selected_groupe": selected_groupe,
        "eleves": eleves,
        "abs_map": abs_map,
    })


# =========================================================
# Evaluations (liste)
# =========================================================

@prof_required
def prof_evaluations(request):
    annee_active = _get_annee_active()
    annee_id = (request.GET.get("annee") or "").strip() or (str(annee_active.id) if annee_active else "")

    groupes = _allowed_groupes(request.user, annee_id=annee_id if annee_id else None)

    ens = getattr(request.user, "enseignant_profile", None)

    evs = (
        Evaluation.objects
        .select_related("matiere", "periode", "groupe")
        .filter(groupe__in=groupes)
    )

    if ens:
        evs = evs.filter(enseignant=ens)   # ✅ ICI
    else:
        # fallback si jamais tu utilises prof=user
        evs = evs.filter(prof=request.user)

    return render(request, "prof/evaluations.html", {
        "evaluations": evs.order_by("-date", "-id"),
        "groupes": groupes.order_by("niveau__degre__ordre", "niveau__ordre", "nom"),
        "annee_selected": annee_id,
    })



# =========================================================
# Evaluation (create)
# =========================================================

@prof_required
def prof_evaluation_create(request):
    annee_active = _get_annee_active()
    if not annee_active:
        messages.error(request, "⚠️ Aucune année scolaire active.")
        return redirect("prof:dashboard")

    groupes = _allowed_groupes(request.user, annee_id=str(annee_active.id))

    az_api = {
        "periodes": reverse("prof:ajax_periodes"),
        "matieres": reverse("prof:ajax_matieres"),
    }

    ens = getattr(request.user, "enseignant_profile", None)
    if not ens:
        messages.error(request, "⛔ Profil enseignant introuvable pour ce compte.")
        return redirect("prof:dashboard")

    if request.method == "POST":
        form = ProfEvaluationForm(request.POST, allowed_groupes=groupes, user=request.user)
        if form.is_valid():
            ev = form.save(commit=False)

            # ✅ IMPORTANT : associer l’enseignant
            ev.enseignant = ens

            # (optionnel) si ton AuditBase a created_by/created_at, tu peux mettre created_by ici

            try:
                ev.save()
            except IntegrityError:
                form.add_error(None, "Une évaluation identique existe déjà (même groupe/matière/période/type/date).")
                return render(request, "prof/evaluation_form.html", {
                    "form": form,
                    "annee_active": annee_active,
                    "AZ_API": az_api,
                })

            messages.success(request, "✅ Évaluation créée.")
            return redirect("prof:notes_saisie", evaluation_id=ev.id)
    else:
        form = ProfEvaluationForm(allowed_groupes=groupes, user=request.user)

    return render(request, "prof/evaluation_form.html", {
        "form": form,
        "annee_active": annee_active,
        "AZ_API": az_api,
    })


# =========================================================
# Notes (saisie)
# =========================================================

@prof_required
def prof_notes_saisie(request, evaluation_id: int):
    ev = get_object_or_404(
        Evaluation.objects.select_related("groupe", "periode", "periode__annee", "matiere"),
        id=evaluation_id
    )

    if not _require_groupe_allowed(request.user, ev.groupe):
        messages.error(request, "⛔ Accès refusé.")
        return render(request, "prof/forbidden.html")

    inscriptions = (
        Inscription.objects
        .select_related("eleve")
        .filter(annee=ev.periode.annee, groupe=ev.groupe)
        .order_by("eleve__nom", "eleve__prenom")
    )
    eleves = [i.eleve for i in inscriptions]

    notes_map = {n.eleve_id: n for n in Note.objects.filter(evaluation=ev, eleve__in=eleves)}

    if request.method == "POST":
        saved = 0
        errors = 0

        for e in eleves:
            val = _safe_decimal(request.POST.get(f"note_{e.id}", ""))
            if val is None:
                continue

            if val < 0 or val > Decimal(str(ev.note_max)):
                messages.error(request, f"⚠️ Hors limite pour {e.matricule} (0–{ev.note_max})")
                errors += 1
                continue

            Note.objects.update_or_create(
                evaluation=ev,
                eleve=e,
                defaults={"valeur": val}
            )
            saved += 1

        if saved:
            messages.success(request, f"✅ Notes enregistrées : {saved}")
        if errors:
            messages.warning(request, f"⚠️ Erreurs : {errors}")

        return redirect("prof:notes_saisie", evaluation_id=ev.id)

    return render(request, "prof/notes_saisie.html", {
        "ev": ev,
        "eleves": eleves,
        "notes_map": notes_map,
    })


# =========================================================
# Cahier de texte 
# =========================================================

@prof_required
def prof_cahier_list(request):
    annee_active = _get_annee_active()
    annee_id = (request.GET.get("annee") or "").strip() or (str(annee_active.id) if annee_active else "")
    groupe_id = (request.GET.get("groupe") or "").strip()
    matiere_id = (request.GET.get("matiere") or "").strip()
    date_str = (request.GET.get("date") or "").strip()

    groupes = _allowed_groupes(request.user, annee_id=annee_id if annee_id else None)

    # ✅ QUE ce prof
    qs = (
        CahierTexte.objects
        .select_related("groupe", "matiere", "annee")
        .filter(groupe__in=groupes)
        .filter(prof=request.user)
    )

    if annee_id:
        qs = qs.filter(annee_id=annee_id)
    if groupe_id:
        qs = qs.filter(groupe_id=groupe_id)
    if matiere_id:
        qs = qs.filter(matiere_id=matiere_id)
    if date_str:
        d = parse_date(date_str)
        if d:
            qs = qs.filter(date=d)
        else:
            messages.warning(request, "⚠️ Date invalide, filtre ignoré.")

    # ✅ IMPORTANT : pour la liste des matières en filtre,
    # on peut laisser vide et la remplir en JS après choix du groupe
    matieres = Matiere.objects.none()

    return render(request, "prof/cahier_list.html", {
        "annee_active": annee_active,
        "annee_selected": annee_id,
        "groupe_selected": groupe_id,
        "matiere_selected": matiere_id,
        "date_selected": date_str,
        "groupes": groupes.order_by("niveau__degre__ordre", "niveau__ordre", "nom"),
        "matieres": matieres,  # rempli côté JS
        "items": qs.order_by("-date", "-id"),
    })

@prof_required
def prof_cahier_create(request):
    annee_active = _get_annee_active()
    if not annee_active:
        messages.error(request, "⚠️ Aucune année scolaire active.")
        return redirect("prof:dashboard")

    groupes = _allowed_groupes(request.user, annee_id=str(annee_active.id))

    if not groupes.exists():
        messages.error(
            request,
            "⚠️ Aucun groupe disponible pour toi sur l’année active. "
            "Vérifie tes affectations."
        )
        return redirect("prof:cahier_list")

    if request.method == "POST":
        form = ProfCahierTexteForm(request.POST, request.FILES, allowed_groupes=groupes, user=request.user)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.annee = annee_active
            obj.prof = request.user
            obj.save()
            messages.success(request, "✅ Cahier de texte enregistré.")
            return redirect("prof:cahier_list")
    else:
        form = ProfCahierTexteForm(allowed_groupes=groupes, user=request.user)

    return render(request, "prof/cahier_form.html", {
        "mode": "create",
        "form": form,
        "annee_active": annee_active,
    })


@prof_required
def prof_cahier_update(request, pk: int):
    obj = get_object_or_404(CahierTexte.objects.select_related("groupe", "annee"), pk=pk)

    if not _require_groupe_allowed(request.user, obj.groupe):
        messages.error(request, "⛔ Accès refusé.")
        return render(request, "prof/forbidden.html")

    annee_active = _get_annee_active()
    annee_id = str(annee_active.id) if annee_active else None
    groupes = _allowed_groupes(request.user, annee_id=annee_id)

    if request.method == "POST":
        form = ProfCahierTexteForm(
            request.POST,
            request.FILES,
            instance=obj,
            allowed_groupes=groupes,
            user=request.user,          # ✅ IMPORTANT
        )
        if form.is_valid():
            form.save()
            messages.success(request, "✅ Cahier de texte modifié.")
            return redirect("prof:cahier_list")
    else:
        form = ProfCahierTexteForm(
            instance=obj,
            allowed_groupes=groupes,
            user=request.user,          # ✅ IMPORTANT
        )

    return render(request, "prof/cahier_form.html", {
        "mode": "update",
        "form": form,
        "annee_active": annee_active,
        "obj": obj,
    })



# =========================================================
# Résumés PDF (liste + create)
# =========================================================

@prof_required
def prof_resumes_list(request):
    annee_active = _get_annee_active()
    annee_id = (request.GET.get("annee") or "").strip() or (str(annee_active.id) if annee_active else "")
    groupe_id = (request.GET.get("groupe") or "").strip()
    matiere_id = (request.GET.get("matiere") or "").strip()
    date_str = (request.GET.get("date") or "").strip()

    groupes = _allowed_groupes(request.user, annee_id=annee_id if annee_id else None)

    # ✅ IMPORTANT : QUE ce prof
    qs = (
        CoursResumePDF.objects
        .select_related("groupe", "matiere", "annee")
        .filter(groupe__in=groupes)
        .filter(prof=request.user)
    )

    if annee_id:
        qs = qs.filter(annee_id=annee_id)
    if groupe_id:
        qs = qs.filter(groupe_id=groupe_id)
    if matiere_id:
        qs = qs.filter(matiere_id=matiere_id)
    if date_str:
        d = parse_date(date_str)
        if d:
            qs = qs.filter(date=d)
        else:
            messages.warning(request, "⚠️ Date invalide, filtre ignoré.")

    # ✅ MATIERES STRICTES (pas de fallback)
    ens = getattr(request.user, "enseignant_profile", None)
    if ens:
        matieres = (
            Matiere.objects
            .filter(
                is_active=True,
                affectations_enseignants_groupes__enseignant=ens,
                affectations_enseignants_groupes__groupe__in=groupes,
                affectations_enseignants_groupes__matiere_fk__isnull=False,
            )
            .distinct()
            .order_by("nom")
        )
    else:
        matieres = Matiere.objects.none()

    return render(request, "prof/resumes_list.html", {
        "annee_active": annee_active,
        "annee_selected": annee_id,
        "groupe_selected": groupe_id,
        "matiere_selected": matiere_id,
        "date_selected": date_str,
        "groupes": groupes.order_by("niveau__degre__ordre", "niveau__ordre", "nom"),
        "matieres": matieres,
        "items": qs.order_by("-date", "-id"),
    })


@prof_required
def prof_resume_create(request):
    annee_active = _get_annee_active()
    if not annee_active:
        messages.error(request, "⚠️ Aucune année scolaire active.")
        return redirect("prof:dashboard")

    groupes = _allowed_groupes(request.user, annee_id=str(annee_active.id))

    if not groupes.exists():
        messages.error(request, "⚠️ Aucun groupe disponible pour toi sur l’année active. Vérifie tes affectations.")
        return redirect("prof:resumes_list")

    if request.method == "POST":
        form = ProfResumePDFForm(
            request.POST,
            request.FILES,
            allowed_groupes=groupes,
            user=request.user,
        )
        if form.is_valid():
            obj = form.save(commit=False)
            obj.annee = annee_active
            obj.prof = request.user
            obj.save()
            messages.success(request, "✅ PDF ajouté.")
            return redirect("prof:resumes_list")
    else:
        form = ProfResumePDFForm(
            allowed_groupes=groupes,
            user=request.user,
        )

    return render(request, "prof/resumes_form.html", {
        "form": form,
        "annee_active": annee_active,
    })


# =========================================================
# EDT
# =========================================================

@prof_required
def prof_edt(request):
    annee_active = _get_annee_active()
    if not annee_active:
        messages.error(request, "⚠️ Aucune année scolaire active.")
        return render(request, "prof/edt.html", {"annee_active": None, "has_slots": False})

    groupes = _allowed_groupes(request.user, annee_id=str(annee_active.id))
    ens = getattr(request.user, "enseignant_profile", None)

    qs = (
        Seance.objects
        .select_related("groupe", "groupe__niveau", "groupe__niveau__degre")
        .filter(annee=annee_active, groupe__in=groupes)
    )
    if ens:
        qs = qs.filter(enseignant=ens)

    groupe_id = (request.GET.get("groupe") or "").strip()
    if groupe_id:
        qs = qs.filter(groupe_id=groupe_id)

    seances = list(qs)

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

    return render(request, "prof/edt.html", {
        "annee_active": annee_active,
        "groupes": groupes.order_by("niveau__degre__ordre", "niveau__ordre", "nom"),
        "groupe_selected": groupe_id,
        "slot_labels": slot_labels,
        "rows": rows,
        "has_slots": True,
    })


# =========================================================
# Profil
# =========================================================

@prof_required
def prof_profil(request):
    annee_active = _get_annee_active()
    annee_id = str(annee_active.id) if annee_active else None
    groupes = _allowed_groupes(request.user, annee_id=annee_id)

    ens = getattr(request.user, "enseignant_profile", None)

    nb_groupes = groupes.count()
    nb_seances = 0
    if annee_active:
        qs_seances = Seance.objects.filter(annee=annee_active, groupe__in=groupes)
        if ens:
            qs_seances = qs_seances.filter(enseignant=ens)
        nb_seances = qs_seances.count()

    tab = (request.POST.get("tab") or "").strip()
    pwd_form = PasswordChangeForm(user=request.user, data=request.POST or None)

    if request.method == "POST":
        if tab == "infos":
            first_name = (request.POST.get("first_name") or "").strip()
            last_name = (request.POST.get("last_name") or "").strip()
            email = (request.POST.get("email") or "").strip()
            telephone = (request.POST.get("telephone") or "").strip()

            request.user.first_name = first_name
            request.user.last_name = last_name
            request.user.email = email
            request.user.save(update_fields=["first_name", "last_name", "email"])

            if ens is not None and hasattr(ens, "telephone"):
                ens.telephone = telephone
                ens.save()

            messages.success(request, "✅ Profil mis à jour.")
            return redirect("prof:profil")

        if tab == "password":
            if pwd_form.is_valid():
                user = pwd_form.save()
                update_session_auth_hash(request, user)
                messages.success(request, "✅ Mot de passe modifié.")
                return redirect("prof:profil")
            messages.error(request, "⚠️ Mot de passe invalide. Vérifie les champs.")

    return render(request, "prof/profil.html", {
        "annee_active": annee_active,
        "groupes": groupes.order_by("niveau__degre__ordre", "niveau__ordre", "nom"),
        "ens": ens,
        "stats": {"nb_groupes": nb_groupes, "nb_seances": nb_seances},
        "pwd_form": pwd_form,
    })
