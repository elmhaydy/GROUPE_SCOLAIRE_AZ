from .threadlocal import set_current_user

class CurrentUserMiddleware:
    """
    Stocke le user connecté dans un threadlocal pour l'utiliser dans les models.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        set_current_user(getattr(request, "user", None))
        return self.get_response(request)



# accounts/middleware.py
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.utils import timezone


class InactivityLogoutMiddleware:
    """
    Déconnexion auto après X secondes d'inactivité.
    - "Inactivité" = pas de requête HTTP pendant X secondes.
    - Timeout glissant: on refresh à chaque request.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.timeout = int(getattr(settings, "AZ_IDLE_TIMEOUT_SECONDS", 10800))  # 3h par défaut

        # URLs à ignorer (évite boucle)
        self.ignore_prefixes = (
            "/accounts/login",
            "/accounts/logout",
            "/static/",
            "/media/",
        )

    def __call__(self, request):
        path = request.path or ""

        # Ignorer pages/ressources
        for p in self.ignore_prefixes:
            if path.startswith(p):
                return self.get_response(request)

        user = getattr(request, "user", None)

        # Si pas authentifié => rien
        if not user or not user.is_authenticated:
            return self.get_response(request)

        now = int(timezone.now().timestamp())
        last = request.session.get("az_last_activity")

        # Si on a déjà un last_activity et que le délai est dépassé => logout
        if last is not None:
            try:
                last = int(last)
            except Exception:
                last = None

        if last is not None and (now - last) > self.timeout:
            logout(request)
            request.session.flush()  # nettoie la session
            messages.warning(request, "Session expirée après 3h d'inactivité. Merci de vous reconnecter.")
            return redirect("accounts:login")

        # Sinon: on met à jour l'activité + on refresh l'expiration
        request.session["az_last_activity"] = now
        request.session.set_expiry(self.timeout)  # sliding expiration
        request.session.modified = True

        return self.get_response(request)
