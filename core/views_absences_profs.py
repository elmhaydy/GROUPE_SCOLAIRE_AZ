# core/views_absences_profs.py
from datetime import date
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Sum

from .models import AbsenceProf, Enseignant, Seance, AnneeScolaire
from .services_absences_profs import stats_mensuelles_prof


def _active_annee():
    return AnneeScolaire.objects.filter(is_active=True).first()


def absence_prof_list(request):
    annee = _active_annee()
    if not annee:
        messages.error(request, "Aucune année scolaire active.")
        return render(request, "admin/absences_profs/list.html", {"annee": None})

    today = date.today()
    year = int(request.GET.get("year", today.year))
    month = int(request.GET.get("month", today.month))
    enseignant_id = (request.GET.get("enseignant") or "").strip()

    qs = (
        AbsenceProf.objects
        .filter(annee=annee)
        .select_related("enseignant", "seance", "seance__groupe")
    )

    if enseignant_id:
        qs = qs.filter(enseignant_id=enseignant_id)

    # filtre mois
    d0 = date(year, month, 1)
    d1 = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    qs = qs.filter(date__gte=d0, date__lt=d1)

    enseignants = Enseignant.objects.filter(is_active=True).order_by("nom", "prenom")

    stats = None
    if enseignant_id:
        ens = get_object_or_404(Enseignant, pk=enseignant_id)
        stats = stats_mensuelles_prof(enseignant=ens, annee=annee, year=year, month=month)

    return render(request, "admin/absences_profs/list.html", {
        "annee": annee,
        "rows": qs.order_by("-date"),
        "enseignants": enseignants,
        "enseignant_id": enseignant_id,
        "year": year,
        "month": month,
        "stats": stats,
    })


def absence_prof_create(request):
    annee = _active_annee()
    if not annee:
        messages.error(request, "Aucune année scolaire active.")
        return redirect("core:absence_prof_list")

    today = date.today()

    # ✅ Pré-remplissage depuis query params
    pre_enseignant = (request.GET.get("enseignant") or "").strip()
    year = int(request.GET.get("year", today.year))
    month = int(request.GET.get("month", today.month))

    # ✅ redirection optionnelle (retour fiche prof)
    next_url = (request.GET.get("next") or "").strip()

    if request.method == "POST":
        enseignant_id = int(request.POST.get("enseignant"))
        seance_id = int(request.POST.get("seance"))
        date_str = request.POST.get("date")

        ens = get_object_or_404(Enseignant, pk=enseignant_id)
        seance = get_object_or_404(Seance, pk=seance_id)

        a = AbsenceProf(
            annee=annee,
            enseignant=ens,
            seance=seance,
            date=date.fromisoformat(date_str),
        )
        try:
            a.full_clean()
            a.save()
            messages.success(request, "Absence enregistrée.")

            # ✅ si on vient de la fiche prof → on y retourne
            if next_url:
                return redirect(next_url)

            # sinon → retour liste filtrée sur prof/mois
            return redirect(f"{redirect('core:absence_prof_list').url}?enseignant={ens.id}&year={year}&month={month}")

        except Exception as e:
            messages.error(request, f"Erreur: {e}")

        # si POST échoue, on garde la sélection
        pre_enseignant = str(enseignant_id)

    enseignants = Enseignant.objects.filter(is_active=True).order_by("nom", "prenom")
    seances = (
        Seance.objects
        .filter(annee=annee)
        .select_related("enseignant", "groupe")
        .order_by("jour", "heure_debut")
    )

    return render(request, "admin/absences_profs/form.html", {
        "annee": annee,
        "enseignants": enseignants,
        "seances": seances,

        "pre_enseignant": pre_enseignant,
        "default_date": today.isoformat(),

        "year": year,
        "month": month,
        "next_url": next_url,
    })


def absence_prof_delete(request, pk):
    obj = get_object_or_404(AbsenceProf, pk=pk)
    next_url = (request.GET.get("next") or "").strip()

    if request.method == "POST":
        obj.delete()
        messages.success(request, "Absence supprimée.")
        return redirect(next_url or "core:absence_prof_list")

    return render(request, "admin/absences_profs/delete.html", {
        "obj": obj,
        "next_url": next_url,
    })
