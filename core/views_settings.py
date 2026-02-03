from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group, Permission
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render



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

    return render(request, "admin/settings/roles/delete.html", {
        "role": role
    })
