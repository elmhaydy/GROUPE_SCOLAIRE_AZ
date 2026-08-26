from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from core.models_audit import AuditLog
from core.audit_signals import AUDITED


def _superuser_required(request):
    if not request.user.is_superuser:
        raise Http404()


# ─────────────────────────────────────────────────────────────────────────────
# Journal principal
# ─────────────────────────────────────────────────────────────────────────────
@login_required
def audit_log_list(request):
    _superuser_required(request)

    qs = AuditLog.objects.select_related("user").order_by("-timestamp")

    # ── Filtres ──────────────────────────────────────────────────────────────
    f_action = request.GET.get("action", "")
    f_model  = request.GET.get("model", "")
    f_user   = request.GET.get("user", "")
    f_q      = request.GET.get("q", "").strip()
    f_period = request.GET.get("period", "7")

    if f_action:
        qs = qs.filter(action=f_action)
    if f_model:
        qs = qs.filter(model_name=f_model)
    if f_user:
        qs = qs.filter(user__username__icontains=f_user)
    if f_q:
        qs = qs.filter(object_repr__icontains=f_q)
    if f_period.isdigit():
        cutoff = timezone.now() - timedelta(days=int(f_period))
        qs = qs.filter(timestamp__gte=cutoff)

    paginator = Paginator(qs, 50)
    page_obj  = paginator.get_page(request.GET.get("page"))

    # KPIs de la période
    period_qs = AuditLog.objects.filter(
        timestamp__gte=timezone.now() - timedelta(days=int(f_period) if f_period.isdigit() else 7)
    )

    # Modèles disponibles pour le filtre
    models_in_db = AuditLog.objects.values_list("model_name", flat=True).distinct()
    model_choices = sorted({
        (m_name, AUDITED.get(("core", m_name), AUDITED.get(("accounts", m_name), AUDITED.get(("auth", m_name), m_name.capitalize()))))
        for m_name in models_in_db if m_name
    }, key=lambda x: x[1])

    ctx = {
        "page_obj":      page_obj,
        "total":         qs.count(),
        "f_action":      f_action,
        "f_model":       f_model,
        "f_user":        f_user,
        "f_q":           f_q,
        "f_period":      f_period,
        "action_choices": AuditLog.ACTION_CHOICES,
        "model_choices":  model_choices,
        "kpi_create":  period_qs.filter(action="CREATE").count(),
        "kpi_update":  period_qs.filter(action="UPDATE").count(),
        "kpi_delete":  period_qs.filter(action="DELETE").count(),
        "kpi_total":   period_qs.count(),
    }
    return render(request, "admin/audit/list.html", ctx)


# ─────────────────────────────────────────────────────────────────────────────
# Détail d'une entrée (diff complet)
# ─────────────────────────────────────────────────────────────────────────────
@login_required
def audit_log_detail(request, pk):
    _superuser_required(request)
    log = get_object_or_404(AuditLog.objects.select_related("user"), pk=pk)

    # Récupère les autres logs du même objet pour l'historique
    related = (
        AuditLog.objects
        .filter(model_name=log.model_name, object_id=log.object_id)
        .select_related("user")
        .order_by("-timestamp")[:20]
    )

    return render(request, "admin/audit/detail.html", {"log": log, "related": related})
