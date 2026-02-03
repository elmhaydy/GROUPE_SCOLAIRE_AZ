# core/permissions.py
from functools import wraps
from django.http import HttpResponseForbidden

def group_required(*group_names):
    """
    Autorise si superuser OU user appartient à un des groupes donnés.

    ✅ Supporte:
        @group_required("ADMIN", "SCOLARITE")
        @group_required(["ADMIN", "SCOLARITE"])

    ✅ Si refus -> 403 (pas redirect login, pas logout)
    """

    # normaliser: group_required(["A","B"])
    if len(group_names) == 1 and isinstance(group_names[0], (list, tuple, set)):
        group_names = tuple(group_names[0])

    group_names = tuple(g for g in group_names if g)

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            u = request.user

            if not u.is_authenticated:
                return HttpResponseForbidden("Accès refusé (non authentifié).")

            if u.is_superuser:
                return view_func(request, *args, **kwargs)

            if u.groups.filter(name__in=group_names).exists():
                return view_func(request, *args, **kwargs)

            return HttpResponseForbidden("Accès refusé (droits insuffisants).")

        return _wrapped

    return decorator
