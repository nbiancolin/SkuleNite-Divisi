from .settings import *

DEBUG = False
ALLOWED_HOSTS = ["138.197.171.221"]  #TODO[SC-70]: Create domain and add it here

STATIC_ROOT = BASE_DIR / "static"
MEDIA_ROOT = BASE_DIR / "media"

CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = True