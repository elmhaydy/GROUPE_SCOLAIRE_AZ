# accounts/views.py
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.shortcuts import render, redirect
from django.views.decorators.http import require_POST

from .models import PasswordResetToken, UserSecurityProfile
from accounts.decorators import eleve_required


def _get_ip(request):
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    return xff.split(",")[0].strip() if xff else request.META.get("REMOTE_ADDR")


def _redirect_after_login(user):
    if user.groups.filter(name="PROF").exists():
        return redirect("prof:dashboard")
    if user.groups.filter(name="ELEVE").exists():
        return redirect("eleve:dashboard")
    return redirect("core:dashboard")


def _redirect_force_change(user):
    if user.groups.filter(name="ELEVE").exists():
        return redirect("eleve:profil")
    if user.groups.filter(name="PROF").exists():
        return redirect("prof:profil")
    return redirect("accounts:password_change")


# ─────────────────────────────────────────────
# Login / Logout
# ─────────────────────────────────────────────

def login_view(request):
    if request.user.is_authenticated:
        return _redirect_after_login(request.user)

    if request.method == "POST":
        username = (request.POST.get("username") or "").strip()
        password = (request.POST.get("password") or "").strip()

        User = get_user_model()
        try:
            u = User.objects.get(username=username)
        except User.DoesNotExist:
            return render(request, "accounts/login.html", {"error": "Identifiants invalides."})

        profile = UserSecurityProfile.get_for(u)

        if profile.is_locked():
            unlock = profile.locked_until.strftime("%H:%M")
            return render(request, "accounts/login.html", {
                "error": f"Compte bloqué après trop d'échecs. Réessayez après {unlock}."
            })

        user = authenticate(request, username=username, password=password)

        if user is None:
            profile.record_failed_attempt()
            if profile.is_locked():
                return render(request, "accounts/login.html", {
                    "error": "Compte bloqué 15 min suite à 5 tentatives échouées."
                })
            remaining = max(0, 5 - profile.failed_login_attempts)
            msg = "Identifiants invalides."
            if profile.failed_login_attempts >= 3:
                msg += f" ({remaining} tentative(s) restante(s) avant blocage)"
            return render(request, "accounts/login.html", {"error": msg})

        if not user.is_active:
            return render(request, "accounts/login.html", {"error": "Compte désactivé."})

        profile.reset_attempts()
        login(request, user)

        if request.POST.get("remember"):
            request.session.set_expiry(2592000)
        else:
            request.session.set_expiry(0)

        if profile.must_change_password:
            messages.warning(request, "Vous devez changer votre mot de passe avant de continuer.")
            return _redirect_force_change(user)

        return _redirect_after_login(user)

    return render(request, "accounts/login.html")


def logout_view(request):
    logout(request)
    return redirect("accounts:login")


# ─────────────────────────────────────────────
# Password change (admin / staff)
# ─────────────────────────────────────────────

@login_required
def password_change(request):
    u = request.user

    if request.method == "POST":
        pwd1 = (request.POST.get("password1") or "").strip()
        pwd2 = (request.POST.get("password2") or "").strip()

        if len(pwd1) < 8:
            messages.error(request, "Mot de passe trop court (minimum 8 caractères).")
            return redirect("accounts:password_change")

        if pwd1 != pwd2:
            messages.error(request, "Les mots de passe ne correspondent pas.")
            return redirect("accounts:password_change")

        u.set_password(pwd1)
        u.save(update_fields=["password"])

        # Clear forced-change flag
        try:
            sp = u.security_profile
            sp.must_change_password = False
            sp.save(update_fields=["must_change_password"])
        except Exception:
            pass

        # Delete TempPassword — plaintext no longer needed once user sets own password
        try:
            from core.models import TempPassword
            TempPassword.objects.filter(user=u).delete()
        except Exception:
            pass

        messages.success(request, "Mot de passe mis à jour. Reconnectez-vous.")
        return redirect("accounts:login")

    return render(request, "accounts/password_change.html")


# ─────────────────────────────────────────────
# Password change (élève — POST only)
# ─────────────────────────────────────────────

@eleve_required
@require_POST
def eleve_password_change(request):
    user = request.user
    current_password = request.POST.get("current_password", "")
    p1 = request.POST.get("password1", "")
    p2 = request.POST.get("password2", "")

    if not user.check_password(current_password):
        messages.error(request, "Mot de passe actuel incorrect.")
        return redirect(request.META.get("HTTP_REFERER") or "eleve:dashboard")

    if len(p1) < 8:
        messages.error(request, "Le nouveau mot de passe doit contenir au moins 8 caractères.")
        return redirect(request.META.get("HTTP_REFERER") or "eleve:dashboard")

    if p1 != p2:
        messages.error(request, "La confirmation ne correspond pas.")
        return redirect(request.META.get("HTTP_REFERER") or "eleve:dashboard")

    user.set_password(p1)
    user.save()
    update_session_auth_hash(request, user)

    try:
        sp = user.security_profile
        sp.must_change_password = False
        sp.save(update_fields=["must_change_password"])
    except Exception:
        pass

    try:
        from core.models import TempPassword
        TempPassword.objects.filter(user=user).delete()
    except Exception:
        pass

    messages.success(request, "Mot de passe mis à jour avec succès.")
    return redirect(request.META.get("HTTP_REFERER") or "eleve:dashboard")


# ─────────────────────────────────────────────
# Password reset (OTP Self-Service)
# ─────────────────────────────────────────────

def password_reset_request(request):
    if request.user.is_authenticated:
        return _redirect_after_login(request.user)

    error = None
    if request.method == "POST":
        identifier = (request.POST.get("identifier") or "").strip()
        if not identifier:
            error = "Veuillez saisir votre identifiant ou adresse email."
        else:
            User = get_user_model()
            user = (
                User.objects.filter(username__iexact=identifier).first() or
                User.objects.filter(email__iexact=identifier).first()
            )
            if user:
                if not user.email:
                    error = f"Le compte '{user.username}' n'a pas d'adresse email associée. Veuillez contacter l'administration pour mettre à jour votre profil."
                else:
                    token_obj = PasswordResetToken.create_for_user(user, ip_address=_get_ip(request))
                    request.session["reset_user_id"] = user.id
                    request.session["reset_token_id"] = token_obj.id

                    print(f"\n==========================================")
                    print(f" [OTP DEBUG] Utilisateur: {user.username} ({user.email})")
                    print(f" [OTP DEBUG] CODE OTP: {token_obj.otp_code}")
                    print(f"==========================================\n")

                    try:
                        html_content = render_to_string("emails/otp_email.html", {
                            "user_name": user.get_full_name() or user.username,
                            "otp_code": token_obj.otp_code,
                        })
                        send_mail(
                            subject=f"Votre code de vérification : {token_obj.otp_code}",
                            message=(
                                f"Bonjour {user.get_full_name() or user.username},\n\n"
                                f"Voici votre code de vérification pour réinitialiser votre mot de passe :\n\n"
                                f"   [ {token_obj.otp_code} ]\n\n"
                                f"Ce code à 6 chiffres est valable pendant 15 minutes.\n"
                                f"Si vous n'êtes pas à l'origine de cette demande, veuillez ignorer cet email.\n\n"
                                f"— Groupe Scolaire"
                            ),
                            from_email=settings.DEFAULT_FROM_EMAIL,
                            recipient_list=[user.email],
                            html_message=html_content,
                            fail_silently=False,
                        )
                    except Exception as e:
                        print(f"[EMAIL ERROR] {e}")

                    return redirect("accounts:password_reset_otp")
            else:
                error = "Aucun compte trouvé avec cet identifiant ou cet email."

    return render(request, "accounts/password_reset_request.html", {"error": error})


def password_reset_otp(request):
    user_id = request.session.get("reset_user_id")
    token_id = request.session.get("reset_token_id")

    if not user_id or not token_id:
        return redirect("accounts:password_reset_request")

    User = get_user_model()
    user = User.objects.filter(id=user_id).first()
    token_obj = PasswordResetToken.objects.filter(id=token_id, used=False).first()

    if not user or not token_obj or not token_obj.is_valid():
        messages.error(request, "Le code de vérification a expiré. Veuillez refaire une demande.")
        return redirect("accounts:password_reset_request")

    # Mask email for privacy display (e.g. el***@gmail.com)
    masked_email = ""
    if user.email:
        parts = user.email.split("@")
        if len(parts) == 2:
            name, domain = parts
            masked_email = f"{name[:2]}***@{domain}"
        else:
            masked_email = user.email

    error = None
    if request.method == "POST":
        otp = (request.POST.get("otp") or "").strip()
        if otp == token_obj.otp_code:
            request.session["otp_verified"] = True
            return redirect("accounts:password_reset_confirm_otp")
        else:
            error = "Code de vérification incorrect. Veuillez vérifier votre boîte mail et réessayer."

    return render(request, "accounts/password_reset_otp.html", {
        "user": user,
        "masked_email": masked_email,
        "error": error,
    })


def password_reset_resend_otp(request):
    user_id = request.session.get("reset_user_id")
    if not user_id:
        return redirect("accounts:password_reset_request")

    User = get_user_model()
    user = User.objects.filter(id=user_id).first()

    if user:
        token_obj = PasswordResetToken.create_for_user(user, ip_address=_get_ip(request))
        request.session["reset_token_id"] = token_obj.id

        print(f"\n==========================================")
        print(f" [DEBUG] Utilisateur: {user.username} ({user.email})")
        print(f" [DEBUG] NOUVEAU CODE DE VÉRIFICATION: {token_obj.otp_code}")
        print(f"==========================================\n")

        if user.email:
            try:
                html_content = render_to_string("emails/otp_email.html", {
                    "user_name": user.get_full_name() or user.username,
                    "otp_code": token_obj.otp_code,
                })
                send_mail(
                    subject=f"Nouveau code de vérification : {token_obj.otp_code}",
                    message=(
                        f"Bonjour {user.get_full_name() or user.username},\n\n"
                        f"Voici votre nouveau code de vérification :\n\n"
                        f"   [ {token_obj.otp_code} ]\n\n"
                        f"Ce code est valable pendant 15 minutes.\n\n"
                        f"— Groupe Scolaire"
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    html_message=html_content,
                    fail_silently=False,
                )
            except Exception as e:
                print(f"[EMAIL RESEND ERROR] {e}")

        messages.success(request, "Un nouveau code de vérification a été envoyé à votre adresse email.")

    return redirect("accounts:password_reset_otp")


def password_reset_confirm_otp(request):
    user_id = request.session.get("reset_user_id")
    token_id = request.session.get("reset_token_id")
    otp_verified = request.session.get("otp_verified")

    if not user_id or not token_id or not otp_verified:
        return redirect("accounts:password_reset_request")

    User = get_user_model()
    user = User.objects.filter(id=user_id).first()
    token_obj = PasswordResetToken.objects.filter(id=token_id, used=False).first()

    if not user or not token_obj or not token_obj.is_valid():
        messages.error(request, "Session expirée. Veuillez réitérer la demande.")
        return redirect("accounts:password_reset_request")

    error = None
    if request.method == "POST":
        p1 = (request.POST.get("password1") or "").strip()
        p2 = (request.POST.get("password2") or "").strip()

        if len(p1) < 8:
            error = "Mot de passe trop court (minimum 8 caractères)."
        elif p1 != p2:
            error = "Les mots de passe ne correspondent pas."
        else:
            user.set_password(p1)
            user.save(update_fields=["password"])

            token_obj.used = True
            token_obj.save(update_fields=["used"])

            sp = UserSecurityProfile.get_for(user)
            sp.must_change_password = False
            sp.reset_attempts()

            # Clean session reset keys
            request.session.pop("reset_user_id", None)
            request.session.pop("reset_token_id", None)
            request.session.pop("otp_verified", None)

            try:
                from core.models import TempPassword
                TempPassword.objects.filter(user=user).delete()
            except Exception:
                pass

            messages.success(request, "Votre mot de passe a été réinitialisé avec succès ! Vous pouvez maintenant vous connecter.")
            return redirect("accounts:login")

    return render(request, "accounts/password_reset_confirm_otp.html", {
        "user": user,
        "error": error,
    })


def password_reset_sent(request):
    return render(request, "accounts/password_reset_sent.html")


def password_reset_confirm(request, token):
    token_obj = PasswordResetToken.objects.select_related("user").filter(
        token=token, used=False
    ).first()

    if not token_obj or not token_obj.is_valid():
        return render(request, "accounts/password_reset_confirm.html", {
            "invalid": True,
            "error": "Ce lien de réinitialisation est invalide ou a expiré.",
        })

    error = None
    if request.method == "POST":
        p1 = (request.POST.get("password1") or "").strip()
        p2 = (request.POST.get("password2") or "").strip()

        if len(p1) < 8:
            error = "Mot de passe trop court (minimum 8 caractères)."
        elif p1 != p2:
            error = "Les mots de passe ne correspondent pas."
        else:
            user = token_obj.user
            user.set_password(p1)
            user.save(update_fields=["password"])

            token_obj.used = True
            token_obj.save(update_fields=["used"])

            sp = UserSecurityProfile.get_for(user)
            sp.must_change_password = False
            sp.reset_attempts()

            try:
                from core.models import TempPassword
                TempPassword.objects.filter(user=user).delete()
            except Exception:
                pass

            messages.success(request, "Mot de passe réinitialisé. Vous pouvez vous connecter.")
            return redirect("accounts:login")

    return render(request, "accounts/password_reset_confirm.html", {
        "token": str(token),
        "error": error,
    })
