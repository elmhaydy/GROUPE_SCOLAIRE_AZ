# core/views_profile.py (ou dans ton fichier views actuel)
from django.contrib.auth.decorators import login_required
from django.shortcuts import render

@login_required
def profile_view(request):
    u = request.user
    roles = [g.name for g in u.groups.all()]  # groups déjà dispo via auth context
    role_main = roles[0] if roles else "—"

    return render(request, "admin/profile.html", {
        "u": u,
        "roles": roles,
        "role_main": role_main,
    })
