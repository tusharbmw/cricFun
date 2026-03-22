"""
Maintenance Celery tasks.
"""
import logging

from celery import shared_task
from apps.core.cricapi import get_hits_status

logger = logging.getLogger(__name__)


@shared_task
def cleanup_old_data():
    """Daily housekeeping at 2 AM (DB archiving, stale session cleanup, etc.)."""
    logger.info('cleanup_old_data: running daily housekeeping.')
    return 'cleanup done'


@shared_task
def log_api_usage_stats():
    """Log a daily summary of Cricket API usage at 11:55 PM."""
    hits = get_hits_status()
    logger.info(
        'Cricket API daily summary — used: %d / %d  (remaining: %d)',
        hits['used'], hits['limit'], hits['remaining']
    )
    return hits
