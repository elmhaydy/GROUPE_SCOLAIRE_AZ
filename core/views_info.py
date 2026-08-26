from django.contrib import messages
from django.shortcuts import render, redirect


def _get_base_template(request):
    """
    Détermine dynamiquement le template de base :
    - Visiteur non connecté -> 'public_base.html' (Clean public layout sans sidebar admin)
    - SuperAdmin / Admin / Staff -> 'admin/base_admin.html'
    - Enseignant -> 'prof/base_prof.html'
    - Élève / Parent -> 'eleve/base.html'
    """
    if not request.user.is_authenticated:
        return "public_base.html"

    user = request.user
    role = getattr(user, "role", None)

    if role == "prof":
        return "prof/base_prof.html"
    elif role == "eleve":
        return "eleve/base.html"

    return "admin/base_admin.html"


def aide_view(request):
    """Page Aide & Support (FAQ et documentation)."""
    return render(
        request,
        "admin/info/aide.html",
        {"base_template": _get_base_template(request)},
    )


def confidentialite_view(request):
    """Politique de Confidentialité et Protection des Données."""
    return render(
        request,
        "admin/info/confidentialite.html",
        {"base_template": _get_base_template(request)},
    )


def conditions_view(request):
    """Conditions Générales d'Utilisation (CGU)."""
    return render(
        request,
        "admin/info/conditions.html",
        {"base_template": _get_base_template(request)},
    )


def contact_view(request):
    """Page de Contact & Support de l'établissement."""
    if request.method == "POST":
        nom = request.POST.get("nom", "").strip()
        email = request.POST.get("email", "").strip()
        sujet = request.POST.get("sujet", "").strip()
        message_text = request.POST.get("message", "").strip()

        if nom and email and message_text:
            messages.success(
                request,
                "Votre message a été transmis avec succès à l'administration du Groupe Scolaire. Nous vous répondrons dans les plus brefs délais.",
            )
            return redirect("core:contact")
        else:
            messages.error(
                request,
                "Veuillez remplir tous les champs obligatoires du formulaire.",
            )

    return render(
        request,
        "admin/info/contact.html",
        {"base_template": _get_base_template(request)},
    )
