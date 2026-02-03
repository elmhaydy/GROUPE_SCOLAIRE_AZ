#accounts/permissions.py
from functools import wraps
from django.core.exceptions import PermissionDenied
from django.contrib.auth.views import redirect_to_login

def group_required(*group_names):
    """
    - Si user pas connecté => redirect login (?next=...)
    - Si connecté mais pas dans les groupes => 403
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path())

            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)

            user_groups = set(request.user.groups.values_list("name", flat=True))
            allowed = bool(user_groups.intersection(set(group_names)))

            if not allowed:
                raise PermissionDenied("Accès refusé.")

            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorator
