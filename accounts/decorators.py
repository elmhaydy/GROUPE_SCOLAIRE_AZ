# accounts/decorators.py
from django.contrib.auth.decorators import user_passes_test
from .permissions import group_required  # ✅ import officiel

def is_prof(user):
    return user.is_authenticated and user.groups.filter(name="PROF").exists()

prof_required = user_passes_test(is_prof, login_url="accounts:login")

def is_eleve(user):
    return user.is_authenticated and user.groups.filter(name="ELEVE").exists()

eleve_required = user_passes_test(is_eleve, login_url="accounts:login")
