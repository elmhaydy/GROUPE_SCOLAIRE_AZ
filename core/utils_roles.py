# core/utils_roles.py
from django.contrib.auth.models import Group

DEFAULT_GROUPS = [
    "SUPER_ADMIN",
    "ADMIN",
    "SCOLARITE",
    "SECRETAIRE",
    "PEDAGOGIQUE",
    "COMPTABLE",
    "PROF",
    "ELEVE",
    "PARENT",
]

def ensure_groups_exist():
    for name in DEFAULT_GROUPS:
        Group.objects.get_or_create(name=name)

def add_user_to_group(user, group_name: str, keep_existing: bool = True):
    ensure_groups_exist()
    g = Group.objects.get(name=group_name)
    if keep_existing:
        user.groups.add(g)
    else:
        user.groups.set([g])
    return g
