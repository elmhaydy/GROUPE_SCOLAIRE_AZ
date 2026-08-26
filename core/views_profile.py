from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from accounts.models import UserSecurityProfile, get_user_avatar_url

@login_required
def profile_view(request):
    u = request.user
    sec_profile = UserSecurityProfile.get_for(u)

    if request.method == "POST":
        if "remove_avatar" in request.POST:
            if sec_profile.avatar:
                sec_profile.avatar.delete(save=False)
                sec_profile.avatar = None
                sec_profile.save(update_fields=["avatar"])

            if hasattr(u, "enseignant_profile") and u.enseignant_profile and u.enseignant_profile.photo:
                u.enseignant_profile.photo.delete(save=False)
                u.enseignant_profile.photo = None
                u.enseignant_profile.save(update_fields=["photo"])
            if hasattr(u, "eleve_profile") and u.eleve_profile and u.eleve_profile.photo:
                u.eleve_profile.photo.delete(save=False)
                u.eleve_profile.photo = None
                u.eleve_profile.save(update_fields=["photo"])

            messages.success(request, "Photo de profil supprimée.")
            return redirect("core:profile")

        avatar_file = request.FILES.get("avatar")
        if avatar_file:
            ext = avatar_file.name.split(".")[-1].lower() if "." in avatar_file.name else ""
            if ext not in ["jpg", "jpeg", "png", "webp", "gif"]:
                messages.error(request, "Format d'image invalide. (Formats autorisés : JPG, PNG, WEBP, GIF)")
            elif avatar_file.size > 5 * 1024 * 1024:
                messages.error(request, "Taille de fichier trop grande (maximum 5 Mo).")
            else:
                if sec_profile.avatar:
                    sec_profile.avatar.delete(save=False)
                sec_profile.avatar = avatar_file
                sec_profile.save(update_fields=["avatar"])

                if hasattr(u, "enseignant_profile") and u.enseignant_profile:
                    u.enseignant_profile.photo = avatar_file
                    u.enseignant_profile.save(update_fields=["photo"])
                if hasattr(u, "eleve_profile") and u.eleve_profile:
                    u.eleve_profile.photo = avatar_file
                    u.eleve_profile.save(update_fields=["photo"])

                messages.success(request, "✅ Photo de profil mise à jour avec succès.")
                return redirect("core:profile")

    roles = [g.name for g in u.groups.all()]
    role_main = roles[0] if roles else "—"
    avatar_url = get_user_avatar_url(u)

    return render(request, "admin/profile.html", {
        "u": u,
        "roles": roles,
        "role_main": role_main,
        "avatar_url": avatar_url,
    })
