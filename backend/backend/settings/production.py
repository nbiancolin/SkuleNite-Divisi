from .base import *

DEBUG = False
ALLOWED_HOSTS = ["146.190.255.211", "localhost", "127.0.0.1", "divisi.nbiancolin.ca"]

CSRF_COOKIE_SECURE = False
SESSION_COOKIE_DOMAIN = 'divisi.nbiancolin.ca'
SECURE_SSL_REDIRECT = False  #TODO Remoe for prod

STATIC_ROOT = BASE_DIR / "static"   # required even if using S3

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',  # Use DEBUG for more verbosity
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',  # Change to DEBUG if you want all details
            'propagate': False,
        },
        'gunicorn.error': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'gunicorn.access': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# DigitalOcean Spaces settings
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_STORAGE_BUCKET_NAME = "divisi-files"
AWS_S3_ENDPOINT_URL = "https://tor1.digitaloceanspaces.com"  # change to your region
AWS_DEFAULT_ACL = "public-read"  # or "private" if you want to control access

AWS_QUERYSTRING_AUTH = False  # disables signed temporary URLs

# Static files
STATICFILES_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"
STATIC_URL = f"https://{AWS_STORAGE_BUCKET_NAME}.tor1.digitaloceanspaces.com/static/"
STATIC_ROOT = BASE_DIR / "static"

# Media files
DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"
MEDIA_URL = f"https://{AWS_STORAGE_BUCKET_NAME}.tor1.digitaloceanspaces.com/"