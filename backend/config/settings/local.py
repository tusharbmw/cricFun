"""
Local development settings.
Use this for local development: DJANGO_SETTINGS_MODULE=config.settings.local
"""

from .base import *  # noqa: F401, F403

DEBUG = True

ALLOWED_HOSTS = ['127.0.0.1', 'localhost']

CORS_ORIGIN_ALLOW_ALL = True

# Allow popup windows for Google OAuth in development
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
SECURE_CROSS_ORIGIN_OPENER_POLICY = 'same-origin-allow-popups'

# django-sslserver for local HTTPS (optional)
INSTALLED_APPS = INSTALLED_APPS + ['sslserver']  # noqa: F405

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {'console': {'class': 'logging.StreamHandler'}},
    'loggers': {
        'apps.core.cricapi': {'handlers': ['console'], 'level': 'INFO', 'propagate': False},
    },
}
