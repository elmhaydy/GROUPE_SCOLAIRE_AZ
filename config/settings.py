"""
Django settings for config project (PROD VPS Hostinger).

- Secrets via .env
- PostgreSQL
- WhiteNoise (static)
- Security hardening (HTTPS)
"""

from pathlib import Path
import os
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# =============================
# ENV (.env)
# =============================
# Support: DJANGO_ENV_FILE=prod.env (optionnel) sinon .env
ENV_FILE = os.getenv("DJANGO_ENV_FILE", ".env").strip() or ".env"
load_dotenv(BASE_DIR / ENV_FILE, override=True)

# =============================
# SECURITY (core)
# =============================
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "CHANGE_ME")

DEBUG = os.getenv("DJANGO_DEBUG", "False").strip().lower() in ("1", "true", "yes", "on")

# ALLOWED_HOSTS CSV: "ip,domain.com,www.domain.com"
ALLOWED_HOSTS = [
    "groupescolaireaz.com",
    "www.groupescolaireaz.com",
    "127.0.0.1",
    "localhost",
]
CSRF_TRUSTED_ORIGINS = [
    "https://groupescolaireaz.com",
    "https://www.groupescolaireaz.com",
]


# Security headers (baseline)
X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"

# (legacy header, harmless)
SECURE_BROWSER_XSS_FILTER = True

# =============================
# APPLICATIONS
# =============================
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    "accounts",
    "core.apps.CoreConfig",
]

# =============================
# MIDDLEWARE
# =============================
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # ✅ WhiteNoise juste après SecurityMiddleware
    "whitenoise.middleware.WhiteNoiseMiddleware",

    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",

    "accounts.middleware.CurrentUserMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",

                "core.context_processors.annee_active",
                "django.template.context_processors.debug",

                "accounts.context_processors.user_roles",
                "core.context_processors.roles_flags",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# =============================
# DATABASE (PostgreSQL)
# =============================
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DB_NAME", "az_db_groups"),
        "USER": os.getenv("DB_USER", "az_user_groups"),
        "PASSWORD": os.getenv("DB_PASSWORD", ""),
        "HOST": os.getenv("DB_HOST", "127.0.0.1"),
        "PORT": os.getenv("DB_PORT", "5432"),
        "CONN_MAX_AGE": int(os.getenv("DB_CONN_MAX_AGE", "60")),
    }
}

# =============================
# PASSWORD VALIDATION
# =============================
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# =============================
# I18N / TZ
# =============================
LANGUAGE_CODE = "fr-fr"
TIME_ZONE = os.getenv("DJANGO_TIME_ZONE", "Africa/Casablanca")
USE_I18N = True
USE_TZ = True

# =============================
# STATIC / MEDIA
# =============================
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Dossier static dev (si existe)
STATIC_DIR = BASE_DIR / "static"
STATICFILES_DIRS = [STATIC_DIR] if STATIC_DIR.exists() else []

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# WhiteNoise storage (hash + gzip + brotli)
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

WHITENOISE_MAX_AGE = int(os.getenv("WHITENOISE_MAX_AGE", "31536000"))  # 1 an

# =============================
# AUTH REDIRECTIONS
# =============================
LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "accounts:login"

# =============================
# OPTIONAL: TWILIO (SMS)
# =============================
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_FROM = os.getenv("TWILIO_FROM", "")

# =============================
# OPTIONAL: EMAIL
# =============================
EMAIL_BACKEND = os.getenv("DJANGO_EMAIL_BACKEND", "django.core.mail.backends.smtp.EmailBackend")
EMAIL_HOST = os.getenv("EMAIL_HOST", "")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "True").strip().lower() in ("1", "true", "yes", "on")
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", EMAIL_HOST_USER or "no-reply@az.local")

# =========================
# LOGGING (journalctl)
# =========================
LOG_LEVEL_DJANGO = os.getenv("DJANGO_LOG_LEVEL", "INFO").upper()
LOG_LEVEL_APPS = os.getenv("APPS_LOG_LEVEL", "DEBUG" if DEBUG else "INFO").upper()

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[{asctime}] {levelname} {name} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "verbose"},
    },
    "loggers": {
        "django.request": {"handlers": ["console"], "level": "ERROR", "propagate": False},
        "django": {"handlers": ["console"], "level": LOG_LEVEL_DJANGO, "propagate": True},

        # tes apps
        "core": {"handlers": ["console"], "level": LOG_LEVEL_APPS, "propagate": True},
        "prof": {"handlers": ["console"], "level": LOG_LEVEL_APPS, "propagate": True},
        "accounts": {"handlers": ["console"], "level": LOG_LEVEL_APPS, "propagate": True},
    },
}

# =============================
# DEFAULT PK
# =============================
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# =============================
# SECURITY (PROD)
# =============================
# Defaults (dev / debug)
SECURE_PROXY_SSL_HEADER = None
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# SameSite (recommandé)
SESSION_COOKIE_SAMESITE = os.getenv("DJANGO_SESSION_COOKIE_SAMESITE", "Lax")
CSRF_COOKIE_SAMESITE = os.getenv("DJANGO_CSRF_COOKIE_SAMESITE", "Lax")

SECURE_HSTS_SECONDS = 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False

if not DEBUG:
    # Nginx reverse proxy : indique à Django que la requête originale était en HTTPS
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

    SECURE_SSL_REDIRECT = os.getenv("DJANGO_SECURE_SSL_REDIRECT", "True").strip().lower() in ("1", "true", "yes", "on")
    SESSION_COOKIE_SECURE = os.getenv("DJANGO_SESSION_COOKIE_SECURE", "True").strip().lower() in ("1", "true", "yes", "on")
    CSRF_COOKIE_SECURE = os.getenv("DJANGO_CSRF_COOKIE_SECURE", "True").strip().lower() in ("1", "true", "yes", "on")

    # HSTS (active uniquement si HTTPS OK)
    SECURE_HSTS_SECONDS = int(os.getenv("DJANGO_HSTS_SECONDS", "31536000"))  # 1 an
    SECURE_HSTS_INCLUDE_SUBDOMAINS = os.getenv("DJANGO_HSTS_INCLUDE_SUBDOMAINS", "True").strip().lower() in ("1", "true", "yes", "on")
    SECURE_HSTS_PRELOAD = os.getenv("DJANGO_HSTS_PRELOAD", "True").strip().lower() in ("1", "true", "yes", "on")

