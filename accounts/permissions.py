# accounts/permissions.py
from functools import wraps
from django.core.exceptions import PermissionDenied
from django.contrib.auth.views import redirect_to_login

def group_required(*group_names):
    """
    Autorise si:
    - user pas connecté => redirect login (?next=...)
    - superuser => OK
    - user dans AU MOINS un des groupes => OK
    Sinon => 403
    Supporte:
        @group_required("ADMIN", "SCOLARITE")
        @group_required(["ADMIN", "SCOLARITE"])
    """

    # normaliser: group_required(["A","B"])
    if len(group_names) == 1 and isinstance(group_names[0], (list, tuple, set)):
        group_names = tuple(group_names[0])

    group_names = tuple(g for g in group_names if g)

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path())

            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)

            user_groups = set(request.user.groups.values_list("name", flat=True))
            if user_groups.intersection(set(group_names)):
                return view_func(request, *args, **kwargs)

            raise PermissionDenied("Accès refusé.")
        return _wrapped
    return decorator
