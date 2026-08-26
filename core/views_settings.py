from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group, Permission
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.http import Http404
from django.utils import timezone

from core.forms_sms import SmsTemplateForm
from core.forms_sms_settings import SmsSettingsForm
from core.models import SmsHistorique, SmsSettings
from core.models_sms import SmsTemplate
from core.services.sms_provider import normalize_phone, send_sms_via_bulksms_ma



# ---------- Helpers ----------
def _group_perms_by_app():
    """
    Retourne les permissions triées par app_label + model.
    Format: { "core": { "eleve": [perm,...], "paiement": [...] }, "auth": {...} }
    """
    perms = Permission.objects.select_related("content_type").order_by(
        "content_type__app_label", "content_type__model", "codename"
    )
    out = {}
    for p in perms:
        app = p.content_type.app_label
        model = p.content_type.model
        out.setdefault(app, {}).setdefault(model, []).append(p)
    return out

def _only_crud_permissions(perms_by_app):
    """
    Option: filtre pour ne garder que add/change/delete/view (CRUD).
    """
    keep_prefix = ("add_", "change_", "delete_", "view_")
    filtered = {}
    for app, models in perms_by_app.items():
        for model, perms in models.items():
            crud = [p for p in perms if p.codename.startswith(keep_prefix)]
            if crud:
                filtered.setdefault(app, {})[model] = crud
    return filtered


# ---------- Paramètres Home ----------
@login_required
def settings_home(request):
    # Tu pourras ajouter d'autres modules ici plus tard
    return render(request, "admin/settings/home.html")


@login_required
def settings_sms(request):
    if not request.user.is_superuser:
        raise Http404()

    settings_obj = SmsSettings.load()
    form = SmsSettingsForm(request.POST or None, instance=settings_obj)
    tpl_form = SmsTemplateForm(request.POST or None)

    if request.method == "POST":
        if "submit_settings" in request.POST:
            if form.is_valid():
                form.save()
                messages.success(request, "Paramètres SMS enregistrés.")
                return redirect("core:settings_sms")
        elif "submit_test" in request.POST:
            test_phone = normalize_phone((request.POST.get("test_phone") or "").strip())
            test_message = (request.POST.get("test_message") or "").strip()
            if not test_phone or not test_message:
                messages.error(request, "Numéro et message de test obligatoires.")
            else:
                hist = SmsHistorique.objects.create(
                    telephone=test_phone,
                    message=test_message,
                    event="autre",
                    type_envoi="manuel",
                    provider="bulksms",
                    status="QUEUED",
                    envoye_par=request.user,
                    sent_at=timezone.now(),
                )
                ok, provider_id, err = send_sms_via_bulksms_ma(test_phone, test_message)
                hist.provider_message_id = provider_id or ""
                hist.error_message = err or ""
                hist.status = "SENT" if ok else "FAILED"
                hist.save(update_fields=["provider_message_id", "error_message", "status"])
                if ok:
                    messages.success(request, "SMS de test envoyé.")
                else:
                    messages.error(request, f"Échec SMS test: {err or 'Erreur inconnue'}")
                return redirect("core:settings_sms")
        elif "submit_template" in request.POST:
            if tpl_form.is_valid():
                tpl = tpl_form.save(commit=False)
                tpl.created_by = request.user
                tpl.save()
                messages.success(request, "Template SMS enregistré.")
                return redirect("core:settings_sms")

    return render(request, "admin/settings/sms.html", {
        "form": form,
        "tpl_form": tpl_form,
        "templates": SmsTemplate.objects.all().order_by("type_template", "code"),
        "logs": SmsHistorique.objects.select_related("parent").order_by("-created_at", "-id")[:50],
    })


@login_required
def sms_history(request):
    raise Http404()


# ---------- Roles ----------
@login_required
def role_list(request):
    q = (request.GET.get("q") or "").strip()
    roles = Group.objects.all().order_by("name")
    if q:
        roles = roles.filter(name__icontains=q)

    return render(request, "admin/settings/roles/list.html", {
        "roles": roles,
        "q": q,
    })


@login_required
def role_create(request):
    # sécurité simple : uniquement superuser (tu peux remplacer par admin_required si tu l'as)
    if not request.user.is_superuser:
        messages.error(request, "Accès refusé.")
        return redirect("core:settings_home")

    perms_tree = _only_crud_permissions(_group_perms_by_app())

    if request.method == "POST":
        name = (request.POST.get("name") or "").strip()
        perm_ids = request.POST.getlist("perms")  # list de Permission.id (strings)

        if not name:
            messages.error(request, "Le nom du rôle est obligatoire.")
            return render(request, "admin/settings/roles/form.html", {
                "mode": "create",
                "perms_tree": perms_tree,
                "selected": set(map(int, perm_ids)) if perm_ids else set(),
                "name": name,
            })

        if Group.objects.filter(name__iexact=name).exists():
            messages.error(request, "Ce rôle existe déjà.")
            return render(request, "admin/settings/roles/form.html", {
                "mode": "create",
                "perms_tree": perms_tree,
                "selected": set(map(int, perm_ids)) if perm_ids else set(),
                "name": name,
            })

        g = Group.objects.create(name=name)

        if perm_ids:
            g.permissions.set(Permission.objects.filter(id__in=perm_ids))

        messages.success(request, "Rôle créé avec succès.")
        return redirect("core:role_list")

    return render(request, "admin/settings/roles/form.html", {
        "mode": "create",
        "perms_tree": perms_tree,
        "selected": set(),
        "name": "",
    })


@login_required
def role_update(request, pk):
    if not request.user.is_superuser:
        messages.error(request, "Accès refusé.")
        return redirect("core:settings_home")

    role = get_object_or_404(Group, pk=pk)
    perms_tree = _only_crud_permissions(_group_perms_by_app())

    if request.method == "POST":
        name = (request.POST.get("name") or "").strip()
        perm_ids = request.POST.getlist("perms")

        if not name:
            messages.error(request, "Le nom du rôle est obligatoire.")
        else:
            # éviter conflit nom (sauf lui-même)
            if Group.objects.filter(name__iexact=name).exclude(pk=role.pk).exists():
                messages.error(request, "Un autre rôle possède déjà ce nom.")
            else:
                role.name = name
                role.save()
                role.permissions.set(Permission.objects.filter(id__in=perm_ids))
                messages.success(request, "Rôle mis à jour.")
                return redirect("core:role_list")

    selected = set(role.permissions.values_list("id", flat=True))
    return render(request, "admin/settings/roles/form.html", {
        "mode": "edit",
        "role": role,
        "perms_tree": perms_tree,
        "selected": selected,
        "name": role.name,
    })


@login_required
def role_delete(request, pk):
    if not request.user.is_superuser:
        messages.error(request, "Accès refusé.")
        return redirect("core:settings_home")

    role = get_object_or_404(Group, pk=pk)

    if request.method == "POST":
        role.delete()
        messages.success(request, "Rôle supprimé.")
        return redirect("core:role_list")

    return redirect("core:role_list")
    
    
    if not request.user.is_superuser:
        messages.error(request, "Accès refusé.")
        return redirect("core:settings_home")

    role = get_object_or_404(Group, pk=pk)

    if request.method == "POST":
        role.delete()
        messages.success(request, "Rôle supprimé.")
        return redirect("core:role_list")

    return redirect("core:role_list")



@login_required
def role_delete_modal(request, pk):
    if not request.user.is_superuser:
        messages.error(request, "Accès refusé.")
        return redirect("core:settings_home")

    role = get_object_or_404(Group, pk=pk)

    return render(request, "admin/settings/roles/delete.html", {
        "role": role
    })
