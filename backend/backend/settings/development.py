from .base import *

DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

# CSRF Trusted Origins - required for Django 4.0+
CSRF_TRUSTED_ORIGINS = [
    'http://localhost:5173',
    'http://127.0.0.1:5173',
]

# CSRF Cookie settings - allow JavaScript to read the cookie
CSRF_COOKIE_HTTPONLY = False  # Allow JavaScript to read CSRF token from cookie
CSRF_COOKIE_SAMESITE = 'Lax'  # Allow cross-site requests with credentials

MEDIA_URL = "blob/"
MEDIA_ROOT = BASE_DIR / "blob"

STATIC_ROOT = BASE_DIR / "static"

# Use filesystem storage locally
DEFAULT_FILE_STORAGE = "django.core.files.storage.FileSystemStorage"

CORS_ORIGIN_WHITELIST = [
     'http://localhost:5173'
]

CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True