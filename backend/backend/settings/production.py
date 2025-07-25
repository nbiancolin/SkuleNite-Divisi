from .base import *

DEBUG = False
ALLOWED_HOSTS = ["146.190.255.211", "localhost", "127.0.0.1", "divisi.nbiancolin.ca"] #TODO[SC-70]: Create domain and add it here

STATIC_ROOT = BASE_DIR / "static"

MEDIA_URL = "blob/"
MEDIA_ROOT = BASE_DIR / "blob"

CSRF_COOKIE_SECURE = False
SESSION_COOKIE_SECURE = False  #TODO: Change these once we get SSL up and running
SECURE_SSL_REDIRECT = False  #TODO Remoe for prod

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