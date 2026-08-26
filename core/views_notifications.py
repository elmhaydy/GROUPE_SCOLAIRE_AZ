# core/views_notifications.py
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms_notifications import NotifComposeForm
from .models_notifications import Notification


# ──────────────────────────────────────────────────────────────────────────────
# Helpers — résolution des destinataires
# ──────────────────────────────────────────────────────────────────────────────

def _parents_from_form(cd):
    """Parents ciblés (SMS + email + notif interne parent)."""
    from .models import Parent
    cible = cd["cible_type"]
    qs = Parent.objects.filter(is_active=True)
    if cible == "TOUS":
        return qs
    if cible == "DEGRE":
        return qs.filter(
            liens__eleve__inscriptions__groupe__niveau__degre=cd["degre"],
            liens__eleve__inscriptions__annee__is_active=True,
        ).distinct()
    if cible == "NIVEAU":
        return qs.filter(
            liens__eleve__inscriptions__groupe__niveau=cd["niveau"],
            liens__eleve__inscriptions__annee__is_active=True,
        ).distinct()
    if cible == "GROUPE":
        return qs.filter(
            liens__eleve__inscriptions__groupe=cd["groupe"],
            liens__eleve__inscriptions__annee__is_active=True,
        ).distinct()
    if cible == "ELEVE":
        return qs.filter(liens__eleve=cd["eleve"]).distinct()
    return qs.none()


def _eleves_from_form(cd):
    """
    Élèves ciblés avec un compte User — pour la notification interne directe.
    Un élève peut ne pas avoir de compte (user=None), on filtre ceux qui en ont.
    """
    from .models import Eleve
    cible = cd["cible_type"]
    qs = Eleve.objects.filter(is_active=True, user__isnull=False).select_related("user")
    if cible == "TOUS":
        return qs
    if cible == "DEGRE":
        return qs.filter(
            inscriptions__groupe__niveau__degre=cd["degre"],
            inscriptions__annee__is_active=True,
        ).distinct()
    if cible == "NIVEAU":
        return qs.filter(
            inscriptions__groupe__niveau=cd["niveau"],
            inscriptions__annee__is_active=True,
        ).distinct()
    if cible == "GROUPE":
        return qs.filter(
            inscriptions__groupe=cd["groupe"],
            inscriptions__annee__is_active=True,
        ).distinct()
    if cible == "ELEVE":
        eleve = cd.get("eleve")
        if eleve and eleve.user_id:
            return qs.filter(pk=eleve.pk)
        return qs.none()
    return qs.none()


def _send_internal_to_eleves(eleves, titre, message, category="INFO"):
    """Crée une Notification pour chaque élève ayant un compte User."""
    count = 0
    for eleve in eleves:
        try:
            Notification.objects.create(
                recipient=eleve.user,
                title=titre,
                body=message,
                category=category,
                eleve=eleve,
            )
            count += 1
        except Exception:
            pass
    return count


# ──────────────────────────────────────────────────────────────────────────────
# Inbox
# ──────────────────────────────────────────────────────────────────────────────

def _inbox_template(user):
    """Choisit le template d'inbox selon le type d'utilisateur."""
    if user.groups.filter(name="ELEVE").exists():
        return "eleve/notifications.html"
    if user.groups.filter(name="PROF").exists():
        return "prof/notifications.html"
    return "admin/notifications/inbox.html"


@login_required
def notif_inbox(request):
    qs = Notification.objects.filter(recipient=request.user).select_related("eleve", "parent")

    category = request.GET.get("category", "")
    show     = request.GET.get("show", "all")

    if category:
        qs = qs.filter(category=category)
    if show == "unread":
        qs = qs.filter(read=False)

    total_unread  = Notification.objects.filter(recipient=request.user, read=False).count()
    notifications = qs[:100]

    return render(request, _inbox_template(request.user), {
        "notifications":    notifications,
        "total_unread":     total_unread,
        "category_filter":  category,
        "show_filter":      show,
        "category_choices": Notification.CATEGORY_CHOICES,
    })


@login_required
@require_POST
def notif_mark_read(request, pk):
    notif = get_object_or_404(Notification, pk=pk, recipient=request.user)
    notif.mark_read()
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"ok": True})
    link = notif.link or request.META.get("HTTP_REFERER") or "/"
    return redirect(link)


@login_required
@require_POST
def notif_mark_all_read(request):
    Notification.objects.filter(recipient=request.user, read=False).update(read=True)
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"ok": True})
    messages.success(request, "Toutes les notifications ont été marquées comme lues.")
    return redirect("core:notif_inbox")


@login_required
def notif_api_unread(request):
    count = Notification.objects.filter(recipient=request.user, read=False).count()
    return JsonResponse({"count": count})


# ──────────────────────────────────────────────────────────────────────────────
# Compose
# ──────────────────────────────────────────────────────────────────────────────

@login_required
def notif_compose(request):
    if not (request.user.is_superuser or request.user.has_perm("core.add_smshistorique")):
        messages.error(request, "Accès refusé.")
        return redirect("core:dashboard")

    form = NotifComposeForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        from .services.notification_service import NotificationService

        cd      = form.cleaned_data
        titre   = cd["titre"]
        message = cd["message"]
        canaux  = cd["canaux"]   # ["sms", "email", "internal"]

        # 1. Envoi SMS + email + notif interne aux parents
        parents = _parents_from_form(cd)
        stats = NotificationService.send_to_parents(
            parents=parents,
            title=titre,
            message=message,
            channels=canaux,
            category="INFO",
            eleve=cd.get("eleve"),
            sent_by=request.user,
        )

        # 2. Notif interne directe à l'élève (son propre compte User)
        #    Indépendant du canal "internal" côté parent — l'élève reçoit toujours
        #    si "internal" est coché et que l'élève a un compte.
        if "internal" in canaux:
            eleves = _eleves_from_form(cd)
            nb_eleves = _send_internal_to_eleves(eleves, titre, message, category="INFO")
            stats["internal"] += nb_eleves

        # Résumé
        parts = []
        if "sms" in canaux:
            parts.append(f"{stats['sms']} SMS")
        if "email" in canaux:
            parts.append(f"{stats['email']} email(s)")
        if "internal" in canaux:
            parts.append(f"{stats['internal']} notification(s) interne(s)")

        summary = " · ".join(parts) if parts else "Aucun envoi"
        if stats["errors"]:
            messages.warning(request, f"Envoi terminé : {summary}. {stats['errors']} erreur(s).")
        else:
            messages.success(request, f"Envoi réussi : {summary}.")
        return redirect("core:notif_compose")

    return render(request, "admin/notifications/compose.html", {"form": form})
