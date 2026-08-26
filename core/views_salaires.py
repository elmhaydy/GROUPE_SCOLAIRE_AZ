from decimal import Decimal
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Q
from django.db.models.functions import Coalesce
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from core.forms_salaires import FichePaieForm
from core.models import AnneeScolaire, Enseignant, FichePaie

ZERO = Decimal("0.00")

MOIS_LABELS = {
    1: "Janvier", 2: "Février", 3: "Mars", 4: "Avril", 5: "Mai", 6: "Juin",
    7: "Juillet", 8: "Août", 9: "Septembre", 10: "Octobre", 11: "Novembre", 12: "Décembre"
}


def _check_finance_perm(user):
    return user.is_superuser or user.is_staff or user.has_perm("core.view_paiement")


@login_required
def salaire_list(request):
    if not _check_finance_perm(request.user):
        raise Http404()

    annee_active = AnneeScolaire.objects.filter(is_active=True).first()
    annee_id = request.GET.get("annee")
    if annee_id:
        annee = get_object_or_404(AnneeScolaire, pk=annee_id)
    else:
        annee = annee_active

    if not annee:
        return render(request, "admin/salaires/list.html", {"no_annee": True})

    qs = FichePaie.objects.filter(annee=annee)

    # Filte par mois
    mois = request.GET.get("mois")
    if mois and mois.isdigit():
        qs = qs.filter(mois_index=int(mois))

    # Filtre par statut
    statut = request.GET.get("statut")
    if statut in ["A_PAYER", "PAYE"]:
        qs = qs.filter(statut=statut)

    # Filtre par type
    personnel_type = request.GET.get("personnel_type")
    if personnel_type in ["ENSEIGNANT", "STAFF"]:
        qs = qs.filter(personnel_type=personnel_type)

    # Recherche texte (nom/prénom)
    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(
            Q(enseignant__nom__icontains=q)
            | Q(enseignant__prenom__icontains=q)
            | Q(user__first_name__icontains=q)
            | Q(user__last_name__icontains=q)
            | Q(user__username__icontains=q)
        )

    # KPIs
    total_paie = qs.aggregate(s=Coalesce(Sum("net_a_payer"), ZERO))["s"]
    total_paye = qs.filter(statut="PAYE").aggregate(s=Coalesce(Sum("net_a_payer"), ZERO))["s"]
    total_a_payer = qs.filter(statut="A_PAYER").aggregate(s=Coalesce(Sum("net_a_payer"), ZERO))["s"]

    annees = AnneeScolaire.objects.order_by("-is_active", "-date_debut")

    return render(
        request,
        "admin/salaires/list.html",
        {
            "annee": annee,
            "annees": annees,
            "fiches": qs.select_related("enseignant", "user"),
            "total_paie": total_paie,
            "total_paye": total_paye,
            "total_a_payer": total_a_payer,
            "nb_fiches": qs.count(),
            "mois_selected": int(mois) if mois and mois.isdigit() else None,
            "statut_selected": statut,
            "personnel_type_selected": personnel_type,
            "q": q,
            "mois_labels": MOIS_LABELS,
        },
    )


@login_required
def salaire_create(request):
    if not _check_finance_perm(request.user):
        raise Http404()

    annee_active = AnneeScolaire.objects.filter(is_active=True).first()

    if request.method == "POST":
        form = FichePaieForm(request.POST)
        if form.is_valid():
            fiche = form.save()
            messages.success(request, f"✅ Fiche de paie enregistrée pour {fiche.get_beneficiaire_nom()}.")
            return redirect("core:salaire_list")
        else:
            messages.error(request, "⚠️ Formulaire invalide. Vérifiez les champs.")
    else:
        initial = {}
        if annee_active:
            initial["annee"] = annee_active.id
        initial["mois_index"] = timezone.now().month
        initial["date_paiement"] = timezone.localdate()
        form = FichePaieForm(initial=initial)

    return render(request, "admin/salaires/form.html", {"form": form, "mode": "create"})


@login_required
def salaire_edit(request, pk):
    if not _check_finance_perm(request.user):
        raise Http404()

    fiche = get_object_or_404(FichePaie, pk=pk)

    if request.method == "POST":
        form = FichePaieForm(request.POST, instance=fiche)
        if form.is_valid():
            fiche = form.save()
            messages.success(request, f"✅ Fiche de paie mise à jour pour {fiche.get_beneficiaire_nom()}.")
            return redirect("core:salaire_list")
        else:
            messages.error(request, "⚠️ Formulaire invalide.")
    else:
        form = FichePaieForm(instance=fiche)

    return render(request, "admin/salaires/form.html", {"form": form, "fiche": fiche, "mode": "edit"})


@login_required
def salaire_pay_toggle(request, pk):
    if not _check_finance_perm(request.user):
        raise Http404()

    fiche = get_object_or_404(FichePaie, pk=pk)
    if request.method == "POST":
        if fiche.statut == "A_PAYER":
            fiche.statut = "PAYE"
            if not fiche.date_paiement:
                fiche.date_paiement = timezone.localdate()
            messages.success(request, f"✅ Paie de {fiche.get_beneficiaire_nom()} marquée comme PAYÉE.")
        else:
            fiche.statut = "A_PAYER"
            messages.info(request, f"ℹ️ Paie de {fiche.get_beneficiaire_nom()} remise À PAYER.")
        fiche.save()

    return redirect("core:salaire_list")


@login_required
def salaire_delete(request, pk):
    if not _check_finance_perm(request.user):
        raise Http404()

    fiche = get_object_or_404(FichePaie, pk=pk)
    if request.method == "POST":
        benef = fiche.get_beneficiaire_nom()
        fiche.delete()
        messages.success(request, f"🗑️ Fiche de paie de {benef} supprimée.")

    return redirect("core:salaire_list")


@login_required
def salaire_recu(request, pk):
    if not _check_finance_perm(request.user):
        raise Http404()

    fiche = get_object_or_404(FichePaie.objects.select_related("enseignant", "user", "annee"), pk=pk)
    mois_nom = MOIS_LABELS.get(fiche.mois_index, f"Mois {fiche.mois_index}")

    return render(
        request,
        "admin/salaires/recu.html",
        {
            "fiche": fiche,
            "mois_nom": mois_nom,
        },
    )
