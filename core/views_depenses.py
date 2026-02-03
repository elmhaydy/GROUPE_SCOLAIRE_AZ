# core/views_depenses.py
from decimal import Decimal
from django.contrib import messages
from django.db.models import Sum, DecimalField
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from datetime import datetime
from django.db.models import Q
from django.utils.dateparse import parse_date

from core.permissions import group_required
from core.models import AnneeScolaire, Depense, CategorieDepense
from core.forms_depenses import DepenseForm, CategorieDepenseForm


def _annee_active():
    return AnneeScolaire.objects.filter(is_active=True).first()



@group_required("SUPER_ADMIN", "ADMIN", "COMPTABLE")
def depense_list(request):
    annee_active = _annee_active()

    annee_id = request.GET.get("annee") or (annee_active.id if annee_active else "")
    cat_id = request.GET.get("cat") or ""
    mois = request.GET.get("mois") or ""  # "1".."12"
    q = (request.GET.get("q") or "").strip()

    # ✅ NOUVEAU : date de / date à (format YYYY-MM-DD)
    date_de_raw = (request.GET.get("date_de") or "").strip()
    date_a_raw  = (request.GET.get("date_a") or "").strip()

    date_de = parse_date(date_de_raw) if date_de_raw else None
    date_a  = parse_date(date_a_raw) if date_a_raw else None

    qs = Depense.objects.select_related("annee", "categorie").all()

    if annee_id:
        qs = qs.filter(annee_id=annee_id)

    if cat_id:
        qs = qs.filter(categorie_id=cat_id)

    if mois:
        qs = qs.filter(date_depense__month=int(mois))

    # ✅ filtre date range
    if date_de:
        qs = qs.filter(date_depense__gte=date_de)
    if date_a:
        qs = qs.filter(date_depense__lte=date_a)

    # ✅ recherche (corrigée) : garde tous les autres filtres
    if q:
        qs = qs.filter(Q(libelle__icontains=q) | Q(description__icontains=q))

    total = qs.aggregate(
        s=Coalesce(Sum("montant"), Decimal("0.00"), output_field=DecimalField(max_digits=10, decimal_places=2))
    )["s"] or Decimal("0.00")

    ctx = {
        "annee_active": annee_active,
        "annees": AnneeScolaire.objects.order_by("-date_debut"),
        "categories": CategorieDepense.objects.order_by("ordre", "nom"),
        "depenses": qs.order_by("-date_depense", "-id"),
        "total": total,
        "f": {
            "annee": str(annee_id),
            "cat": str(cat_id),
            "mois": str(mois),
            "q": q,
            "date_de": date_de_raw,
            "date_a": date_a_raw,
        },
    }
    return render(request, "admin/depenses/list.html", ctx)


@group_required("SUPER_ADMIN", "ADMIN", "COMPTABLE")
def depense_create(request):
    annee_active = _annee_active()

    if request.method == "POST":
        form = DepenseForm(request.POST, request.FILES, annee_default=annee_active)
        if form.is_valid():
            obj = form.save()
            messages.success(request, "✅ Dépense ajoutée.")
            return redirect("core:depense_list")
    else:
        form = DepenseForm(annee_default=annee_active)

    return render(request, "admin/depenses/form.html", {
        "annee_active": annee_active,
        "form": form,
        "mode": "create",
    })


@group_required("SUPER_ADMIN", "ADMIN", "COMPTABLE")
def depense_edit(request, pk: int):
    annee_active = _annee_active()
    obj = get_object_or_404(Depense, pk=pk)

    if request.method == "POST":
        form = DepenseForm(request.POST, request.FILES, instance=obj, annee_default=annee_active)
        if form.is_valid():
            form.save()
            messages.success(request, "✅ Dépense mise à jour.")
            return redirect("core:depense_list")
    else:
        form = DepenseForm(instance=obj, annee_default=annee_active)

    return render(request, "admin/depenses/form.html", {
        "annee_active": annee_active,
        "form": form,
        "mode": "edit",
        "obj": obj,
    })


@group_required("SUPER_ADMIN", "ADMIN", "COMPTABLE")
def depense_delete(request, pk: int):
    obj = get_object_or_404(Depense, pk=pk)
    if request.method == "POST":
        obj.delete()
        messages.success(request, "🗑️ Dépense supprimée.")
        return redirect("core:depense_list")
    return render(request, "admin/depenses/delete.html", {"obj": obj})


# ======================
# Catégories
# ======================
@group_required("SUPER_ADMIN", "ADMIN", "COMPTABLE")
def categorie_list(request):
    cats = CategorieDepense.objects.order_by("ordre", "nom")
    return render(request, "admin/depenses/categorie_list.html", {"cats": cats})


@group_required("SUPER_ADMIN", "ADMIN", "COMPTABLE")
def categorie_create(request):
    if request.method == "POST":
        form = CategorieDepenseForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "✅ Catégorie ajoutée.")
            return redirect("core:depense_categorie_list")
    else:
        form = CategorieDepenseForm()

    return render(request, "admin/depenses/categorie_form.html", {"form": form, "mode": "create"})


@group_required("SUPER_ADMIN", "ADMIN", "COMPTABLE")
def categorie_edit(request, pk: int):
    obj = get_object_or_404(CategorieDepense, pk=pk)
    if request.method == "POST":
        form = CategorieDepenseForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, "✅ Catégorie mise à jour.")
            return redirect("core:depense_categorie_list")
    else:
        form = CategorieDepenseForm(instance=obj)

    return render(request, "admin/depenses/categorie_form.html", {"form": form, "mode": "edit", "obj": obj})

from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.db.models import Count
from core.permissions import group_required
from core.models import CategorieDepense, Depense

@group_required("SUPER_ADMIN", "ADMIN", "COMPTABLE")
def categorie_delete(request, pk):
    cat = get_object_or_404(CategorieDepense, pk=pk)

    # sécurité: bloquer si utilisée
    used = Depense.objects.filter(categorie_id=cat.id).exists()
    if used:
        messages.error(request, "Impossible : cette catégorie est utilisée par des dépenses.")
        return redirect("core:depense_categorie_list")

    if request.method == "POST":
        cat.delete()
        messages.success(request, "Catégorie supprimée.")
        return redirect("core:depense_categorie_list")

    return render(request, "admin/depenses/categorie_delete.html", {"cat": cat})
