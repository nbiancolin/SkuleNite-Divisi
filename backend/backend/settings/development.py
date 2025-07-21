from .base import *

DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

MEDIA_URL = "blob/"
MEDIA_ROOT = BASE_DIR / "blob"

CORS_ORIGIN_WHITELIST = [
     'http://localhost:5173'
]

CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True