from .base import *
import os

# -------------------------------
# General
# -------------------------------
DEBUG = False
ALLOWED_HOSTS = ["146.190.255.211", "divisi.nbiancolin.ca"]
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_DOMAIN = "divisi.nbiancolin.ca"
# Don't set CSRF_COOKIE_DOMAIN - let it default to None so it works with the request domain
# This ensures cookies work properly when frontend and backend are on the same domain
CSRF_COOKIE_DOMAIN = None
CSRF_COOKIE_PATH = "/"  # Ensure cookie is available for all paths
SECURE_SSL_REDIRECT = True

# Trust proxy headers (nginx is forwarding these)
USE_X_FORWARDED_HOST = True
USE_X_FORWARDED_PORT = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# CSRF Trusted Origins - required for Django 4.0+
CSRF_TRUSTED_ORIGINS = [
    'https://divisi.nbiancolin.ca',
]

# CSRF Cookie settings - allow JavaScript to read the cookie
CSRF_COOKIE_HTTPONLY = False  # Allow JavaScript to read CSRF token from cookie
CSRF_COOKIE_SAMESITE = 'Lax'  # Allow cross-site requests with credentials
CSRF_USE_SESSIONS = False  # Use cookies for CSRF token (default)

# CORS Configuration
CORS_ALLOWED_ORIGINS = [
    'https://divisi.nbiancolin.ca',
]
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]


# -------------------------------
# Logging
# -------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {"format": "{levelname} {asctime} {module} {message}", "style": "{"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "verbose"},
    },
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "django": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "gunicorn.error": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "gunicorn.access": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
}

# -------------------------------
# DigitalOcean Spaces / S3 Configuration
# -------------------------------
AWS_ACCESS_KEY_ID = os.environ["AWS_ACCESS_KEY_ID"]
AWS_SECRET_ACCESS_KEY = os.environ["AWS_SECRET_ACCESS_KEY"]
AWS_STORAGE_BUCKET_NAME = "divisi-files"
AWS_S3_REGION_NAME = "tor1"
AWS_S3_ENDPOINT_URL = f"https://{AWS_S3_REGION_NAME}.digitaloceanspaces.com"

# S3 Configuration
AWS_S3_OBJECT_PARAMETERS = {
    'CacheControl': 'max-age=86400',
}
AWS_DEFAULT_ACL = None
AWS_QUERYSTRING_AUTH = False
AWS_S3_FILE_OVERWRITE = False
AWS_S3_CUSTOM_DOMAIN = f"{AWS_STORAGE_BUCKET_NAME}.{AWS_S3_REGION_NAME}.digitaloceanspaces.com"

# -------------------------------
# Static Files Configuration  
# -------------------------------
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static')
]

# Set STATIC_ROOT (required even for S3)
STATIC_ROOT = '/tmp/static'

# Django 4.2+ storage configuration
STORAGES = {
    "default": {
        "BACKEND": "backend.storage_backends.MediaStorage",
    },
    "staticfiles": {
        "BACKEND": "backend.storage_backends.StaticStorage",
    },
}

STATIC_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/static/"

# -------------------------------
# Media Files Configuration
# -------------------------------
MEDIA_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/media/"

# -------------------------------
# Frontend URL for redirects
# -------------------------------
# Override FRONTEND_URL from base.py for production
FRONTEND_URL = os.environ.get('FRONTEND_URL', 'https://divisi.nbiancolin.ca')
LOGIN_REDIRECT_URL = FRONTEND_URL
ACCOUNT_LOGOUT_REDIRECT_URL = FRONTEND_URL


# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('POSTGRES_DB', 'TEMPDB_NAME'),
        'USER': os.environ.get('POSTGRES_USER', 'TEMPDB_USER'),
        'PASSWORD': os.environ.get('POSTGRES_PASSWORD', 'TEMPDB_PASSWORD'),
        'HOST': os.environ.get('POSTGRES_HOST', 'TEMPDB_HOST'),
        'PORT': os.environ.get('POSTGRES_PORT', '5432'),
    }
}
#SENTRY:
import sentry_sdk

sentry_sdk.init(
    # dsn="https://3d4544eb118dd04d1b5480de3a66422d@o4510709620670464.ingest.de.sentry.io/4510709626175568",
    dsn = os.environ.get('SENTRY_DSN', "NO SENTRY DSN FOUND IN ENV"),
    send_default_pii=True,
)
