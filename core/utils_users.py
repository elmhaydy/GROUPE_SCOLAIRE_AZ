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
      - password_temp: seulement utile si user créé (ou si tu veux l’afficher).
      - created: True si nouveau user créé.
    """
    User = get_user_model()
    username = (username or "").strip()

    if not username:
        raise ValueError("username vide")

    # groupe (crée si n’existe pas)
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

    # s'assurer du rôle
    user.groups.add(group)

    return user, pwd, created

def reset_password(user) -> str:
    """
    Reset le mdp d’un user (temporaire) + le stocke dans TempPassword
    """
    # ✅ import lazy pour éviter circular import
    from .models import TempPassword

    pwd = generate_temp_password()
    user.set_password(pwd)
    user.save(update_fields=["password"])

    TempPassword.objects.update_or_create(
        user=user,
        defaults={"password": pwd, "updated_at": timezone.now()}
    )
    return pwd
