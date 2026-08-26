from .threadlocal import set_current_user, set_audit_ip


def _get_client_ip(request) -> str | None:
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


class CurrentUserMiddleware:
    """
    Stocke le user connecté et l'IP cliente dans des threadlocals
    accessibles depuis les models et le journal d'audit.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        set_current_user(getattr(request, "user", None))
        set_audit_ip(_get_client_ip(request))
        return self.get_response(request)


from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.utils import timezone


class InactivityLogoutMiddleware:
    """
    Déconnexion auto après X secondes d'inactivité.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.timeout = int(getattr(settings, "AZ_IDLE_TIMEOUT_SECONDS", 10800))

        self.ignore_prefixes = (
            "/accounts/login",
            "/accounts/logout",
            "/static/",
            "/media/",
        )

    def __call__(self, request):
        path = request.path or ""

        for p in self.ignore_prefixes:
            if path.startswith(p):
                return self.get_response(request)

        user = getattr(request, "user", None)

        if not user or not user.is_authenticated:
            return self.get_response(request)

        now = int(timezone.now().timestamp())
        last = request.session.get("az_last_activity")

        if last is not None:
            try:
                last = int(last)
            except Exception:
                last = None

        if last is not None and (now - last) > self.timeout:
            logout(request)
            request.session.flush()
            messages.warning(request, "Session expirée après 3h d'inactivité. Merci de vous reconnecter.")
            return redirect("accounts:login")

        request.session["az_last_activity"] = now
        request.session.set_expiry(self.timeout)
        request.session.modified = True

        return self.get_response(request)


class MustChangePasswordMiddleware:
    """
    Redirige les utilisateurs dont must_change_password=True vers la page
    de changement de mot de passe. Laisse passer /accounts/*, /static/, /media/
    et les espaces élève/prof pour qu'ils puissent accéder à leur profil.
    """

    ALWAYS_ALLOWED = (
        "/accounts/",
        "/static/",
        "/media/",
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path

        # Whitelisted paths — always pass through
        if any(path.startswith(p) for p in self.ALWAYS_ALLOWED):
            return self.get_response(request)

        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return self.get_response(request)

        try:
            if not user.security_profile.must_change_password:
                return self.get_response(request)
        except Exception:
            return self.get_response(request)

        # User must change password — allow profile pages through so they can act
        if user.groups.filter(name="ELEVE").exists():
            if path.startswith("/eleve/"):
                return self.get_response(request)
            messages.warning(request, "Vous devez changer votre mot de passe avant de continuer.")
            return redirect("eleve:profil")

        if user.groups.filter(name="PROF").exists():
            if path.startswith("/prof/profil"):
                return self.get_response(request)
            messages.warning(request, "Vous devez changer votre mot de passe avant de continuer.")
            return redirect("prof:profil")

        messages.warning(request, "Vous devez changer votre mot de passe avant de continuer.")
        return redirect("accounts:password_change")
