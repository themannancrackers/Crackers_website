"""
Django settings for crackers_ecommerce project
"""

from pathlib import Path
import os
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env file
load_dotenv(BASE_DIR / ".env")

# ---------------------------------------------------------------------
# SECURITY
# ---------------------------------------------------------------------
SECRET_KEY = os.getenv("SECRET_KEY", "django-insecure-dev-key-change-in-production")
DEBUG = os.getenv("DEBUG", "True") == "True"
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "*").split(",")
CSRF_TRUSTED_ORIGINS = os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",") if os.getenv("CSRF_TRUSTED_ORIGINS") else []


# ---------------------------------------------------------------------
# APPLICATIONS
# ---------------------------------------------------------------------
INSTALLED_APPS = [
    "unfold", 
    # Django Core
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",

    # Third-party
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",

    # Local apps
    "inventory.apps.InventoryConfig",
    "accounts.apps.AccountsConfig",
    "whatsapp_notifications.apps.WhatsappNotificationsConfig",
             
]

# ---------------------------------------------------------------------
# DJANGO-ALLAUTH CONFIGURATION
# ---------------------------------------------------------------------
SITE_ID = 1

# URLs
LOGIN_URL = "account_login"
LOGIN_REDIRECT_URL = "/accounts/oauth/callback/"     # ✅ Goes to your role-based redirect view
LOGOUT_REDIRECT_URL = "/accounts/login/"

# Account behaviour
ACCOUNT_AUTHENTICATION_METHOD = os.getenv("ACCOUNT_AUTHENTICATION_METHOD", "email")
ACCOUNT_EMAIL_REQUIRED = os.getenv("ACCOUNT_EMAIL_REQUIRED", "True") == "True"
ACCOUNT_USERNAME_REQUIRED = os.getenv("ACCOUNT_USERNAME_REQUIRED", "False") == "True"
ACCOUNT_UNIQUE_EMAIL = os.getenv("ACCOUNT_UNIQUE_EMAIL", "True") == "True"
ACCOUNT_LOGOUT_ON_GET = os.getenv("ACCOUNT_LOGOUT_ON_GET", "True") == "True"
ACCOUNT_EMAIL_VERIFICATION = os.getenv("ACCOUNT_EMAIL_VERIFICATION", "none")
ACCOUNT_DEFAULT_HTTP_PROTOCOL = os.getenv("ACCOUNT_DEFAULT_HTTP_PROTOCOL", "http")

# Social-account behaviour
SOCIALACCOUNT_AUTO_SIGNUP = os.getenv("SOCIALACCOUNT_AUTO_SIGNUP", "True") == "True"
SOCIALACCOUNT_LOGIN_ON_GET = os.getenv("SOCIALACCOUNT_LOGIN_ON_GET", "False") == "True"
SOCIALACCOUNT_QUERY_EMAIL = os.getenv("SOCIALACCOUNT_QUERY_EMAIL", "True") == "True"
SOCIALACCOUNT_STORE_TOKENS = os.getenv("SOCIALACCOUNT_STORE_TOKENS", "True") == "True"

# Custom adapter that links existing users & assigns roles
SOCIALACCOUNT_ADAPTER = "accounts.adapters.CustomSocialAccountAdapter"

# Google provider configuration
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")

SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "SCOPE": ["profile", "email"],
        "AUTH_PARAMS": {"access_type": "online"},
        "APP": {
            "client_id": GOOGLE_CLIENT_ID,
            "secret": GOOGLE_CLIENT_SECRET,
            "key": ""
        }
    }
}


# ---------------------------------------------------------------------
# MIDDLEWARE
# ---------------------------------------------------------------------
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # Serve static files efficiently
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "accounts.middleware.RoleMiddleware",
]


# ---------------------------------------------------------------------
# URLS / WSGI
# ---------------------------------------------------------------------
ROOT_URLCONF = "crackers_ecommerce.urls"

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
    },
]

WSGI_APPLICATION = "crackers_ecommerce.wsgi.application"


# ---------------------------------------------------------------------
# AUTHENTICATION
# ---------------------------------------------------------------------
AUTH_USER_MODEL = "accounts.CustomUser"

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
    "accounts.auth.RoleBasedBackend",   # your custom RBAC backend
]


# ---------------------------------------------------------------------
# DATABASE
# ---------------------------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}


# ---------------------------------------------------------------------
# PASSWORD VALIDATION
# ---------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# ---------------------------------------------------------------------
# INTERNATIONALIZATION
# ---------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True


# ---------------------------------------------------------------------
# STATIC & MEDIA FILES
# ---------------------------------------------------------------------
STATIC_URL = '/static/'
STATICFILES_DIRS = [
    BASE_DIR / "static",
]
STATIC_ROOT = BASE_DIR / "staticfiles"


MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"


# ---------------------------------------------------------------------
# EMAIL (Gmail SMTP Example)
# ---------------------------------------------------------------------
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "True") == "True"
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "themannancrackers@gmail.com")


# ---------------------------------------------------------------------
# MISC
# ---------------------------------------------------------------------
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


UNFOLD = {
    "SITE_TITLE": "The Mannan Crackers",
    "SITE_HEADER": "The Mannan Crackers Admin",
    "SITE_LOGO": "/static/images/kannan_logo.png",
    "LOGIN": {
        "SHOW_REMEMBER": True,
    },
    "COLORS": {
        "primary": {
            500: "#FF8C00",
        },
        "neutral": {
            100: "#111827",
            200: "#1F2937",
            300: "#4B5563",
            400: "#6B7280",
            500: "#9CA3AF",
            600: "#D1D5DB",  # lighter border shade
            700: "#E5E7EB",
            800: "#F3F4F6",
            900: "#F9FAFB",
        },
    },
}


# =====================================================
# WHATSAPP CLOUD API CONFIGURATION
# =====================================================
# Meta WhatsApp Cloud API for sending order notifications
# Credentials: https://developers.facebook.com/docs/whatsapp/cloud-api/get-started

WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
WHATSAPP_API_VERSION = os.getenv("WHATSAPP_API_VERSION", "v18.0")
WHATSAPP_ADMIN_NUMBER = os.getenv("WHATSAPP_ADMIN_NUMBER", "")

# Dry-run mode: True = log messages without API calls (development)
#               False = send actual messages via Meta API (production)
WHATSAPP_DRY_RUN = os.getenv("WHATSAPP_DRY_RUN", "True") == "True"

# Enable/disable WhatsApp notifications globally
WHATSAPP_NOTIFICATIONS_ENABLED = os.getenv("WHATSAPP_NOTIFICATIONS_ENABLED", "True") == "True"

# Optional: Enable Celery for async notification sending
WHATSAPP_USE_CELERY = os.getenv("WHATSAPP_USE_CELERY", "False") == "True"

