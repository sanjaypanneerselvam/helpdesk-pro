"""
Django settings for HelpDesk Pro.

Only the lines that differ from the default Django project are commented.
"""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# NOTE: fine for a learning project. Use an environment variable in production.
SECRET_KEY = "django-insecure-helpdesk-pro-change-me"
DEBUG = True
ALLOWED_HOSTS = []

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # third party
    "rest_framework",
    "rest_framework.authtoken",  # gives us the Token model used for login
    # our apps
    "accounts",  # custom User + auth endpoints
    "tickets",  # Category / Ticket / Comment + ticket endpoints
    "web",  # the HTML screens (S1 - S10)
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# Our own user model (must be set BEFORE the first migrate).
AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Make `manage.py test` fast: a cheap password hasher (tests only).
import sys  # noqa: E402

if "test" in sys.argv:
    PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# ---- Django REST Framework ------------------------------------------------
REST_FRAMEWORK = {
    # Token login for Postman / JS, session login for the browsable API.
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "accounts.authentication.BearerTokenAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    # Every endpoint needs a logged-in user unless it says otherwise.
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_PAGINATION_CLASS": "tickets.pagination.StandardPagination",
    # Keeps error JSON consistent: {"detail": "..."}
    "EXCEPTION_HANDLER": "config.exceptions.custom_exception_handler",
}

# Used by the browsable API's "Log in" link.
LOGIN_URL = "/api-auth/login/"
LOGIN_REDIRECT_URL = "/api/v1/"
