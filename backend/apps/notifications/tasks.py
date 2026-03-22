"""
Notification Celery tasks.
"""
import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task
def notify_pick_result(selection_id, match_id):
    """
    Notify a user that their pick result is available.
    Stub for Phase 4 — will use Web Push (pywebpush) once PWA is set up.
    """
    logger.info(
        'notify_pick_result: selection=%s match=%s (push not yet implemented)',
        selection_id, match_id,
    )


@shared_task
def notify_rank_change(new_leader, match_id, prev_leader=None):
    """
    Create an in-app Notification for ALL active users when rank #1 changes.
    PWA-ready: the same Notification rows will drive push notifications once
    the PWA (Phase 5) is implemented.
    """
    from django.contrib.auth.models import User
    from apps.notifications.models import Notification

    if prev_leader:
        message = f'🏆 {new_leader} has taken the lead!'
    else:
        message = f'🏆 {new_leader} is leading the standings!'

    meta  = {'new_leader': new_leader, 'prev_leader': prev_leader, 'match_id': match_id}
    users = User.objects.filter(is_active=True)

    Notification.objects.bulk_create([
        Notification(user=u, type='rank_change', message=message, meta=meta)
        for u in users
    ])
    logger.info(
        'notify_rank_change: created %d notifications (%s took rank 1)',
        users.count(), new_leader,
    )
