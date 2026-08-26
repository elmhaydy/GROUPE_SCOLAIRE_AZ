from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.management import call_command
from django.core.paginator import Paginator
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from core.forms_relance import RelanceRuleForm
from core.models_relance import RelanceLog, RelanceRule


def _superuser_required(request):
    if not request.user.is_superuser:
        raise Http404()


# ─────────────────────────────────────────────
# Liste des règles
# ─────────────────────────────────────────────
@login_required
def relance_rule_list(request):
    _superuser_required(request)

    rules = RelanceRule.objects.all()

    # Stats rapides par règle
    now = timezone.now()
    for rule in rules:
        rule.log_count_7j  = RelanceLog.objects.filter(rule=rule, sent_at__gte=now - timedelta(days=7), dry_run=False).count()
        rule.log_count_30j = RelanceLog.objects.filter(rule=rule, sent_at__gte=now - timedelta(days=30), dry_run=False).count()

    ctx = {
        "rules": rules,
        "total_rules":  rules.count(),
        "total_actifs": rules.filter(actif=True).count(),
        "logs_7j":  RelanceLog.objects.filter(dry_run=False, sent_at__gte=now - timedelta(days=7)).count(),
        "logs_30j": RelanceLog.objects.filter(dry_run=False, sent_at__gte=now - timedelta(days=30)).count(),
    }
    return render(request, "admin/relances/rule_list.html", ctx)


# ─────────────────────────────────────────────
# Créer une règle
# ─────────────────────────────────────────────
@login_required
def relance_rule_create(request):
    _superuser_required(request)

    form = RelanceRuleForm(request.POST or None)
    if form.is_valid():
        rule = form.save(commit=False)
        rule.created_by = request.user
        rule.save()
        messages.success(request, f"Règle « {rule.nom} » créée.")
        return redirect("core:relance_rule_list")

    return render(request, "admin/relances/rule_form.html", {"form": form, "action": "Créer"})


# ─────────────────────────────────────────────
# Modifier une règle
# ─────────────────────────────────────────────
@login_required
def relance_rule_update(request, pk):
    _superuser_required(request)
    rule = get_object_or_404(RelanceRule, pk=pk)

    form = RelanceRuleForm(request.POST or None, instance=rule)
    if form.is_valid():
        form.save()
        messages.success(request, f"Règle « {rule.nom} » modifiée.")
        return redirect("core:relance_rule_list")

    return render(request, "admin/relances/rule_form.html", {"form": form, "rule": rule, "action": "Modifier"})


# ─────────────────────────────────────────────
# Supprimer une règle
# ─────────────────────────────────────────────
@login_required
def relance_rule_delete(request, pk):
    _superuser_required(request)
    rule = get_object_or_404(RelanceRule, pk=pk)
    if request.method == "POST":
        nom = rule.nom
        rule.delete()
        messages.success(request, f"Règle « {nom} » supprimée.")
        return redirect("core:relance_rule_list")
    return render(request, "admin/relances/rule_delete.html", {"rule": rule})


# ─────────────────────────────────────────────
# Toggle actif/inactif (AJAX)
# ─────────────────────────────────────────────
@login_required
def relance_rule_toggle(request, pk):
    _superuser_required(request)
    rule = get_object_or_404(RelanceRule, pk=pk)
    if request.method == "POST":
        rule.actif = not rule.actif
        rule.save(update_fields=["actif"])
        return JsonResponse({"actif": rule.actif})
    raise Http404()


# ─────────────────────────────────────────────
# Logs de relance
# ─────────────────────────────────────────────
@login_required
def relance_log_list(request):
    _superuser_required(request)

    qs = RelanceLog.objects.select_related("rule", "eleve", "parent", "echeance", "sms").order_by("-sent_at")

    # Filtres
    ftype = request.GET.get("type", "")
    fdry  = request.GET.get("dry", "")
    fok   = request.GET.get("ok", "")
    fq    = request.GET.get("q", "").strip()
    fperiod = request.GET.get("period", "30")

    if ftype:
        qs = qs.filter(type_relance=ftype)
    if fdry == "0":
        qs = qs.filter(dry_run=False)
    elif fdry == "1":
        qs = qs.filter(dry_run=True)
    if fok == "1":
        qs = qs.filter(success=True)
    elif fok == "0":
        qs = qs.filter(success=False)
    if fq:
        qs = qs.filter(message__icontains=fq)
    if fperiod.isdigit():
        cutoff = timezone.now() - timedelta(days=int(fperiod))
        qs = qs.filter(sent_at__gte=cutoff)

    paginator = Paginator(qs, 40)
    page_obj  = paginator.get_page(request.GET.get("page"))

    ctx = {
        "page_obj": page_obj,
        "total":    qs.count(),
        "ftype":    ftype,
        "fdry":     fdry,
        "fok":      fok,
        "fq":       fq,
        "fperiod":  fperiod,
        "type_choices": RelanceRule.TYPE_CHOICES,
    }
    return render(request, "admin/relances/log_list.html", ctx)


# ─────────────────────────────────────────────
# Déclenchement manuel (depuis l'interface)
# ─────────────────────────────────────────────
@login_required
def relance_trigger(request):
    _superuser_required(request)

    if request.method == "POST":
        run_type = request.POST.get("type", "all")
        dry_run  = request.POST.get("dry_run") == "1"
        limit    = int(request.POST.get("limit", 200))

        valid_types = ["all", "impaye", "absence", "retard", "renouvellement"]
        if run_type not in valid_types:
            run_type = "all"

        try:
            from io import StringIO
            out = StringIO()
            call_command(
                "relance_auto",
                type=run_type,
                dry_run=dry_run,
                limit=limit,
                stdout=out,
            )
            output = out.getvalue()
            prefix = "Simulation (dry-run)" if dry_run else "Relances"
            messages.success(request, f"{prefix} lancées avec succès. {output}")
        except Exception as e:
            messages.error(request, f"Erreur : {e}")

        return redirect("core:relance_rule_list")

    raise Http404()
