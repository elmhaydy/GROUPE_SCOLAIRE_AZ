# core/utils_users.py
import secrets
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.utils import timezone


def generate_temp_password(length: int = 10) -> str:
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def ensure_group(name: str) -> Group:
    g, _ = Group.objects.get_or_create(name=name)
    return g


def get_or_create_user_with_group(username, group_name, length=10):
    """
    Crée (ou récupère) un user par username, et s'assure qu'il appartient au groupe group_name.

    Retour:
      (user, password_temp, created)
    """
    User = get_user_model()
    username = (username or "").strip()

    if not username:
        raise ValueError("username vide")

    group, _ = Group.objects.get_or_create(name=group_name)

    user = User.objects.filter(username=username).first()
    created = False
    pwd = ""

    if user is None:
        pwd = generate_temp_password(length=length)
        user = User(username=username, is_active=True)
        user.set_password(pwd)
        user.save()
        created = True

    user.groups.add(group)
    return user, pwd, created


def reset_password(user) -> str:
    """
    Génère un mot de passe temporaire pour l'utilisateur et l'oblige à le changer
    à sa prochaine connexion. Le mot de passe temporaire est stocké dans TempPassword
    uniquement pour l'export CSV admin — il est effacé dès que l'utilisateur change
    son mot de passe via l'interface.
    """
    from .models import TempPassword
    from accounts.models import UserSecurityProfile

    pwd = generate_temp_password()
    user.set_password(pwd)
    user.save(update_fields=["password"])

    # Store temp password for admin CSV export only
    TempPassword.objects.update_or_create(
        user=user,
        defaults={"password": pwd},
    )

    # Force password change on next login
    sp = UserSecurityProfile.get_for(user)
    sp.must_change_password = True
    sp.save(update_fields=["must_change_password"])

    return pwd
