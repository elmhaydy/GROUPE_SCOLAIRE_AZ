from decimal import Decimal
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.db.models.functions import Coalesce
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render

from core.models import AnneeScolaire, BudgetAnnuel, CategorieDepense, Depense, FichePaie

ZERO = Decimal("0.00")


@login_required
def budget_overview(request):
    if not (request.user.is_superuser or request.user.has_perm("core.view_paiement")):
        raise Http404()

    annee_active = AnneeScolaire.objects.filter(is_active=True).first()
    annee_id = request.GET.get("annee")
    if annee_id:
        annee = get_object_or_404(AnneeScolaire, pk=annee_id)
    else:
        annee = annee_active

    if not annee:
        return render(request, "admin/budget/overview.html", {"no_annee": True})

    categories = CategorieDepense.objects.filter(is_active=True).order_by("ordre", "nom")

    # Traitement du formulaire POST de mise à jour des allocations budgétaires
    if request.method == "POST":
        for cat in categories:
            val_str = request.POST.get(f"budget_{cat.id}", "").strip()
            if val_str:
                try:
                    val = Decimal(val_str)
                    val = max(val, ZERO)
                    BudgetAnnuel.objects.update_or_create(
                        annee=annee,
                        categorie=cat,
                        defaults={"montant_alloue": val},
                    )
                except Exception:
                    pass
        messages.success(request, "✅ Allocations budgétaires mises à jour avec succès.")
        return redirect(f"{request.path}?annee={annee.id}")

    # Récupérer les allocations existantes
    budgets_map = {
        b.categorie_id: b.montant_alloue
        for b in BudgetAnnuel.objects.filter(annee=annee)
    }

    # Récupérer les dépenses réelles par catégorie
    depenses_map = {
        d["categorie"]: d["total"]
        for d in Depense.objects.filter(annee=annee)
        .values("categorie")
        .annotate(total=Coalesce(Sum("montant"), ZERO))
    }

    # Paies / Masse Salariale
    total_salaires_payes = FichePaie.objects.filter(annee=annee, statut="PAYE").aggregate(
        s=Coalesce(Sum("net_a_payer"), ZERO)
    )["s"]
    total_salaires_prevus = FichePaie.objects.filter(annee=annee).aggregate(
        s=Coalesce(Sum("net_a_payer"), ZERO)
    )["s"]

    rows = []
    total_budget_alloue = ZERO
    total_depenses_reelles = ZERO

    for cat in categories:
        b_alloue = budgets_map.get(cat.id, ZERO)
        d_reelle = depenses_map.get(cat.id, ZERO)
        total_budget_alloue += b_alloue
        total_depenses_reelles += d_reelle

        pourcentage = int((d_reelle / b_alloue) * 100) if b_alloue > ZERO else 0
        statut_couleur = "emerald"
        if pourcentage >= 100:
            statut_couleur = "rose"
        elif pourcentage >= 80:
            statut_couleur = "amber"

        rows.append({
            "categorie": cat,
            "budget_alloue": b_alloue,
            "depense_reelle": d_reelle,
            "ecart": b_alloue - d_reelle,
            "pourcentage": min(pourcentage, 100),
            "pourcentage_raw": pourcentage,
            "statut_couleur": statut_couleur,
        })

    annees = AnneeScolaire.objects.order_by("-is_active", "-date_debut")

    return render(
        request,
        "admin/budget/overview.html",
        {
            "annee": annee,
            "annees": annees,
            "rows": rows,
            "total_budget_alloue": total_budget_alloue,
            "total_depenses_reelles": total_depenses_reelles,
            "total_salaires_payes": total_salaires_payes,
            "total_salaires_prevus": total_salaires_prevus,
            "total_sorties_global": total_depenses_reelles + total_salaires_payes,
            "solde_budgetaire": total_budget_alloue - total_depenses_reelles,
        },
    )
