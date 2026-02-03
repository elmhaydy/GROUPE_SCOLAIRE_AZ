from .utils import has_group

def user_roles(request):
    u = request.user
    return {
        "is_admin": has_group(u, "ADMIN"),
        "is_scolarite": has_group(u, "SCOLARITE"),
        "is_compta": has_group(u, "COMPTA"),
        "is_prof": has_group(u, "PROF"),
        "is_parent": has_group(u, "PARENT"),
    }
