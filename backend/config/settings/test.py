"""
Test settings — uses SQLite in-memory so tests run without Oracle.
"""
from .base import *  # noqa: F401, F403

DEBUG = False

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# Speed up password hashing in tests
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']

# Disable Redis / Celery for tests
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}
CELERY_TASK_ALWAYS_EAGER = True

CORS_ORIGIN_ALLOW_ALL = True

# Silence allauth signals / email backends
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
