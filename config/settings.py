"""
Django settings for Scheduler Platform.

"""

from __future__ import annotations

import os
from pathlib import Path


"""
Paths
"""

BASE_DIR = Path(__file__).resolve().parent.parent


"""
Environment helpers
"""


def _env(key: str, default: str | None = None) -> str:
    value = os.getenv(key, default)
    if value is None:
        raise RuntimeError(f"Missing required environment variable: {key}")
    return value


def _env_bool(key: str, default: str = "0") -> bool:
    return _env(key, default).strip().lower() in {"1", "true", "yes", "y", "on"}


def _env_list(key: str, default: str = "") -> list[str]:
    raw = _env(key, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


"""
Core security
"""

SECRET_KEY = _env("DJANGO_SECRET_KEY", "dev-only-change-me")
DEBUG = _env_bool("DJANGO_DEBUG", "1")
ALLOWED_HOSTS = _env_list("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost")
if DEBUG:
    CSRF_TRUSTED_ORIGINS = [
        "http://localhost:8080",
        "http://127.0.0.1:8080",
    ]

USE_X_FORWARDED_HOST = True

LOGIN_REDIRECT_URL = "/booking/"
LOGOUT_REDIRECT_URL = "/booking/"

ACCOUNT_LOGOUT_REDIRECT_URL = "/booking/"


"""
Applications
"""

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
]

THIRD_PARTY_APPS = [
    "crispy_forms",
    "crispy_bootstrap5",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
]

LOCAL_APPS = [
    "apps.core",
    "apps.accounts",
    "apps.scheduling",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS


"""
Middleware
"""

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


"""
URLs / WSGI / ASGI
"""

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"


"""
Templates
"""

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.template.context_processors.debug",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]


"""
Database
"""

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": _env("POSTGRES_DB", "scheduler"),
        "USER": _env("POSTGRES_USER", "scheduler"),
        "PASSWORD": _env("POSTGRES_PASSWORD", "scheduler"),
        "HOST": _env("POSTGRES_HOST", "127.0.0.1"),
        "PORT": _env("POSTGRES_PORT", "5432"),
        "CONN_MAX_AGE": int(_env("POSTGRES_CONN_MAX_AGE", "60")),
    }
}


"""
Cache / Redis
"""

REDIS_URL = _env("REDIS_URL", "redis://127.0.0.1:6379/0")

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
        "TIMEOUT": int(_env("DJANGO_CACHE_TIMEOUT", "300")),
    }
}

SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"


"""
Auth / Allauth
"""

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

SITE_ID = int(_env("DJANGO_SITE_ID", "1"))

ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_AUTHENTICATION_METHOD = "email"
ACCOUNT_EMAIL_VERIFICATION = _env("ACCOUNT_EMAIL_VERIFICATION", "none")

SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "APP": {
            "client_id": os.getenv("GOOGLE_CLIENT_ID"),
            "secret": os.getenv("GOOGLE_CLIENT_SECRET"),
            "key": "",
        },
        "SCOPE": [
            "profile",
            "email",
        ],
        "AUTH_PARAMS": {
            "access_type": "online",
        },
    }
}

"""
Internationalization / Time
"""

LANGUAGE_CODE = _env("DJANGO_LANGUAGE_CODE", "en-us")
TIME_ZONE = _env("TIME_ZONE", "Europe/Berlin")
USE_I18N = True
USE_TZ = True


"""
Static / Media
"""

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"


"""
Forms (crispy)
"""

CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"


"""
Security headers
"""

CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
X_FRAME_OPTIONS = "DENY"

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https") if not DEBUG else None


"""
Email (dev-safe defaults)
"""

EMAIL_BACKEND = _env(
    "DJANGO_EMAIL_BACKEND",
    "django.core.mail.backends.console.EmailBackend",
)
DEFAULT_FROM_EMAIL = _env("DEFAULT_FROM_EMAIL", "no-reply@example.com")


"""
Logging
"""

LOG_LEVEL = _env("DJANGO_LOG_LEVEL", "INFO").upper()

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {"class": "logging.StreamHandler"},
    },
    "root": {"handlers": ["console"], "level": LOG_LEVEL},
}


"""
Django defaults
"""

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"