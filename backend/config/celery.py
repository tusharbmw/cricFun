import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')

app = Celery('cricfun')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# ──────────────────────────────────────────────────────────────────────────────
# Beat schedule — optimised for 100 API calls/day limit
#
# Budget breakdown (typical match day):
#   - fetch_upcoming_matches  : 1 call/day
#   - update_live_scores      : ~30 calls/day (only runs when matches are live,
#                               every 60s, max ~2 live matches × 15 calls each)
#   - pre_match_updates       : ~5 calls/day (10-min checks near match start)
#   - log_api_usage_stats     : 0 API calls (internal only)
#   - cleanup_old_data        : 0 API calls (DB only)
#   Total: ~36 calls/day  ← well under 100 limit
# ──────────────────────────────────────────────────────────────────────────────
app.conf.beat_schedule = {
    # Check live scores every 60 seconds.
    # Task itself skips the API call if no matches are live.
    'update-live-scores': {
        'task': 'apps.matches.tasks.update_live_scores',
        'schedule': 60.0,
    },

    # Fetch upcoming matches once per day at 6 AM (1 API call).
    'fetch-upcoming-matches': {
        'task': 'apps.matches.tasks.fetch_upcoming_matches',
        'schedule': crontab(hour=6, minute=0),
    },

    # Pre-match check every 10 minutes — transitions TBD→IP when time is past.
    # No API call; purely a DB status update.
    'pre-match-status-update': {
        'task': 'apps.matches.tasks.update_match_statuses',
        'schedule': 600.0,
    },

    # Daily housekeeping at 2 AM
    'cleanup-old-data': {
        'task': 'apps.core.tasks.cleanup_old_data',
        'schedule': crontab(hour=2, minute=0),
    },

    # Log API usage summary at 11:55 PM each day
    'log-api-usage': {
        'task': 'apps.core.tasks.log_api_usage_stats',
        'schedule': crontab(hour=23, minute=55),
    },
}
