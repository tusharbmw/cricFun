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
    Creates an in-app notification and sends a Web Push if they have subscriptions.
    """
    from django.contrib.auth.models import User
    from teams.models import Match, Selection
    from apps.notifications.models import Notification, PushSubscription
    from apps.notifications.utils import send_push_notification

    try:
        sel   = Selection.objects.select_related('user', 'match', 'selection').get(pk=selection_id)
        match = sel.match
    except Selection.DoesNotExist:
        logger.error('notify_pick_result: selection %s not found', selection_id)
        return

    if match.result == 'team1':
        winner = match.team1
    elif match.result == 'team2':
        winner = match.team2
    else:
        winner = None

    if winner:
        if sel.selection == winner:
            message = f'✅ Correct pick! {winner.name} won.'
        else:
            message = f'❌ Wrong pick. {winner.name} won.'
    else:
        message = f'Match result recorded.'

    Notification.objects.create(
        user=sel.user,
        type='pick_result',
        message=message,
        meta={'match_id': match_id, 'selection_id': selection_id},
    )

    # Web Push
    for sub in PushSubscription.objects.filter(user=sel.user):
        send_push_notification(sub, title='CricFun', body=message, url='/results')

    logger.info('notify_pick_result: notified user %s for selection %s', sel.user_id, selection_id)


@shared_task
def notify_rank_change(new_leader, match_id, prev_leader=None):
    """
    Create an in-app Notification for ALL active users when rank #1 changes,
    and send a Web Push to each user's subscribed devices.
    """
    from django.contrib.auth.models import User
    from apps.notifications.models import Notification, PushSubscription
    from apps.notifications.utils import send_push_notification

    if prev_leader:
        message = f'🏆 {new_leader} has taken the lead!'
    else:
        message = f'🏆 {new_leader} is leading the standings!'

    meta  = {'new_leader': new_leader, 'prev_leader': prev_leader, 'match_id': match_id}
    users = list(User.objects.filter(is_active=True))

    Notification.objects.bulk_create([
        Notification(user=u, type='rank_change', message=message, meta=meta)
        for u in users
    ])

    # Web Push — one per subscription (users may have multiple devices)
    subs = PushSubscription.objects.filter(user__is_active=True).select_related('user')
    sent = 0
    for sub in subs:
        if send_push_notification(sub, title='CricFun', body=message, url='/standings'):
            sent += 1

    logger.info(
        'notify_rank_change: %d in-app + %d push notifications sent (%s took rank 1)',
        len(users), sent, new_leader,
    )
