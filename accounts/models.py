import uuid
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone


def _default_expires_at():
    return timezone.now() + timedelta(hours=24)


class PasswordResetToken(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="password_reset_tokens",
    )
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True)
    otp_code = models.CharField(max_length=6, blank=True, default="")
    expires_at = models.DateTimeField(default=_default_expires_at)
    used = models.BooleanField(default=False)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Jeton de réinitialisation"

    def is_valid(self):
        return not self.used and self.expires_at > timezone.now()

    @classmethod
    def create_for_user(cls, user, ip_address=None):
        import random
        # Invalidate any previous unused tokens
        cls.objects.filter(user=user, used=False).update(used=True)
        # Generate 6-digit OTP code
        code = f"{random.randint(100000, 999999)}"
        # OTP valid for 15 minutes
        expires = timezone.now() + timedelta(minutes=15)
        return cls.objects.create(
            user=user,
            otp_code=code,
            expires_at=expires,
            ip_address=ip_address
        )

    def __str__(self):
        return f"Reset({self.user.username}, OTP: {self.otp_code}, {'ok' if self.is_valid() else 'invalide'})"


import os


def avatar_upload_path(instance, filename: str) -> str:
    ext = filename.split(".")[-1].lower() if "." in filename else "jpg"
    new_name = f"{uuid.uuid4().hex}.{ext}"
    username = instance.user.username if instance.user else "tmp"
    return os.path.join("avatars", username, new_name)


def get_user_avatar_url(user):
    if not user or not user.is_authenticated:
        return None
    try:
        sec = getattr(user, "security_profile", None)
        if sec and sec.avatar and hasattr(sec.avatar, "url") and sec.avatar.name:
            return sec.avatar.url
    except Exception:
        pass
    try:
        ens = getattr(user, "enseignant_profile", None)
        if ens and ens.photo and hasattr(ens.photo, "url") and ens.photo.name:
            return ens.photo.url
    except Exception:
        pass
    try:
        el = getattr(user, "eleve_profile", None)
        if el and el.photo and hasattr(el.photo, "url") and el.photo.name:
            return el.photo.url
    except Exception:
        pass
    return None


class UserSecurityProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="security_profile",
    )
    avatar = models.ImageField(upload_to=avatar_upload_path, null=True, blank=True, verbose_name="Photo de profil")
    must_change_password = models.BooleanField(default=False)
    failed_login_attempts = models.PositiveSmallIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)
    last_failed_login = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Profil de sécurité utilisateur"

    def is_locked(self):
        return bool(self.locked_until and self.locked_until > timezone.now())

    def record_failed_attempt(self):
        self.failed_login_attempts += 1
        self.last_failed_login = timezone.now()
        if self.failed_login_attempts >= 5:
            self.locked_until = timezone.now() + timedelta(minutes=15)
        self.save(update_fields=["failed_login_attempts", "last_failed_login", "locked_until"])

    def reset_attempts(self):
        self.failed_login_attempts = 0
        self.locked_until = None
        self.last_failed_login = None
        self.save(update_fields=["failed_login_attempts", "locked_until", "last_failed_login"])

    @classmethod
    def get_for(cls, user):
        profile, _ = cls.objects.get_or_create(user=user)
        return profile

    def __str__(self):
        return f"SecProfile({self.user.username})"
