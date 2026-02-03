from django.contrib import admin
from django.urls import path, include
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.conf import settings
from django.conf.urls.static import static

def forbidden(request, exception=None):
    return render(request, "admin/403.html", status=403)

@login_required
def dashboard(request):
    return render(request, "admin/dashboard.html")

def root_redirect(request):
    if request.user.is_authenticated:
        return redirect("dashboard")  # ✅ maintenant ça marche
    return redirect("accounts:login")

handler403 = "config.urls.forbidden"

urlpatterns = [
    path("", root_redirect, name="root"),

    # ✅ dashboard direct (au lieu du include)
    path("dashboard/", dashboard, name="dashboard"),

    path("accounts/", include("accounts.urls")),

    # ✅ option : change /admin/
    path("az-admin/", admin.site.urls),

    path("core/", include("core.urls")),
    path("prof/", include("prof.urls")),
    path("eleve/", include("core.urls_eleve", namespace="eleve")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)