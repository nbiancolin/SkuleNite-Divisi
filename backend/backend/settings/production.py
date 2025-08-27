from .base import *
import os

# -------------------------------
# General
# -------------------------------
DEBUG = False
ALLOWED_HOSTS = ["146.190.255.211", "localhost", "127.0.0.1", "divisi.nbiancolin.ca"]

CSRF_COOKIE_SECURE = False
SESSION_COOKIE_DOMAIN = "divisi.nbiancolin.ca"
SECURE_SSL_REDIRECT = False  # TODO: enable in production

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
# DigitalOcean Spaces / S3
# -------------------------------
AWS_ACCESS_KEY_ID = os.environ["AWS_ACCESS_KEY_ID"]
AWS_SECRET_ACCESS_KEY = os.environ["AWS_SECRET_ACCESS_KEY"]
AWS_STORAGE_BUCKET_NAME = "divisi-files"
AWS_S3_REGION_NAME = "tor1"
AWS_S3_ENDPOINT_URL = f"https://{AWS_S3_REGION_NAME}.digitaloceanspaces.com"

# Make all uploaded files public
AWS_DEFAULT_ACL = None
AWS_QUERYSTRING_AUTH = False

# -------------------------------
# Static files
# -------------------------------
STATICFILES_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"
STATIC_URL = f"https://{AWS_STORAGE_BUCKET_NAME}.{AWS_S3_REGION_NAME}.digitaloceanspaces.com/static/"

# Dummy path required by Django collectstatic (will not be used)
STATIC_ROOT = "/tmp/static/"

# -------------------------------
# Media files
# -------------------------------
DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"
MEDIA_URL = f"https://{AWS_STORAGE_BUCKET_NAME}.{AWS_S3_REGION_NAME}.digitaloceanspaces.com/media/"
