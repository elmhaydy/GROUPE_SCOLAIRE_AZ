# accounts/views.py
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect


def login_view(request):
    if request.method == "POST":
        username = (request.POST.get("username") or "").strip()
        password = (request.POST.get("password") or "").strip()

        user = authenticate(request, username=username, password=password)
        if user is None:
            return render(request, "accounts/login.html", {"error": "Identifiants invalides"})

        if not user.is_active:
            return render(request, "accounts/login.html", {"error": "Compte désactivé"})

        login(request, user)

        # ✅ PROF
        if user.groups.filter(name="PROF").exists():
            return redirect("prof:dashboard")   # /prof/

        # ✅ PARENT
        if user.groups.filter(name="ELEVE").exists():
            return redirect("eleve:dashboard")

        # ✅ ADMIN / SUPERADMIN (ton URL qui marche déjà)
        if user.is_staff or user.is_superuser:
            return redirect("core:dashboard")

        # ✅ fallback
        return redirect("core:dashboard")

    return render(request, "accounts/login.html")


def logout_view(request):
    logout(request)
    return redirect("accounts:login")


# accounts/views.py
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect
from django.utils import timezone

from core.models import TempPassword  # si TempPassword est dans core
# sinon adapte l'import selon où est TempPassword

@login_required
def password_change(request):
    u = request.user

    if request.method == "POST":
        pwd1 = (request.POST.get("password1") or "").strip()
        pwd2 = (request.POST.get("password2") or "").strip()

        if not pwd1 or len(pwd1) < 6:
            messages.error(request, "⛔ Mot de passe trop court (min 6).")
            return redirect("accounts:password_change")

        if pwd1 != pwd2:
            messages.error(request, "⛔ Les mots de passe ne correspondent pas.")
            return redirect("accounts:password_change")

        u.set_password(pwd1)
        u.save(update_fields=["password"])

        # (optionnel) stocker mdp temporaire comme tu fais
        TempPassword.objects.update_or_create(
            user=u,
            defaults={"password": pwd1, "updated_at": timezone.now()}
        )

        messages.success(request, "✅ Mot de passe mis à jour. Reconnecte-toi.")
        return redirect("accounts:login")

    return render(request, "accounts/password_change.html")

# accounts/views.py
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth import update_session_auth_hash

from accounts.decorators import eleve_required
from core.models import TempPassword  # si tu veux continuer à stocker le dernier mdp
from django.utils import timezone

from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.shortcuts import redirect
from django.views.decorators.http import require_POST

@eleve_required
@require_POST
def eleve_password_change(request):
    user = request.user
    current_password = request.POST.get("current_password", "")
    p1 = request.POST.get("password1", "")
    p2 = request.POST.get("password2", "")

    if not user.check_password(current_password):
        messages.error(request, "Mot de passe actuel incorrect.")
        return redirect(request.META.get("HTTP_REFERER", "eleve:dashboard"))

    if len(p1) < 8:
        messages.error(request, "Le nouveau mot de passe doit contenir au moins 8 caractères.")
        return redirect(request.META.get("HTTP_REFERER", "eleve:dashboard"))

    if p1 != p2:
        messages.error(request, "La confirmation ne correspond pas.")
        return redirect(request.META.get("HTTP_REFERER", "eleve:dashboard"))

    user.set_password(p1)
    user.save()
    update_session_auth_hash(request, user)  # ✅ reste connecté
    messages.success(request, "Mot de passe mis à jour avec succès ✅")
    return redirect(request.META.get("HTTP_REFERER", "eleve:dashboard"))




