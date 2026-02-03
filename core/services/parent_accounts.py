from django.contrib.auth import get_user_model
from django.utils import timezone

from core.models import TempPassword, Enseignant
from core.utils_users import get_or_create_user_with_group


def ensure_parent_user(parent, eleve=None):
    """
    Garantit qu'un Parent a un compte User (groupe PARENT).
    - si déjà user => rien
    - username basé sur matricule de l'élève (si dispo), sinon PARENT-<id>
    - évite collision
    """
    if parent.user_id:
        return parent.user

    base_username = (getattr(eleve, "matricule", "") or "").strip() or f"PARENT-{parent.pk}"
    username = base_username

    User = get_user_model()
    if User.objects.filter(username=username).exists():
        username = f"{base_username}-P{parent.pk}"

    u, pwd, created_user = get_or_create_user_with_group(username, "PARENT", length=10)

    u.first_name = parent.prenom or ""
    u.last_name = parent.nom or ""
    if parent.email:
        u.email = parent.email
    u.is_active = parent.is_active
    u.save(update_fields=["first_name", "last_name", "email", "is_active"])

    parent.user = u
    parent.save(update_fields=["user"])

    if created_user and pwd:
        TempPassword.objects.update_or_create(
            user=u,
            defaults={"password": pwd, "created_at": timezone.now()}
        )

    return u
from django.db.models.signals import post_save
from django.dispatch import receiver
from core.models import ParentEleve
from core.services.parent_accounts import ensure_parent_user

@receiver(post_save, sender=ParentEleve)
def create_parent_user_from_first_child(sender, instance: ParentEleve, created, **kwargs):
    if not created:
        return
    parent = instance.parent
    eleve = instance.eleve

    # ✅ crée le compte parent si absent
    ensure_parent_user(parent, eleve=eleve)
