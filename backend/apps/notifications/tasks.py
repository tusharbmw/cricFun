"""
Notification Celery tasks.
"""
import logging
from datetime import datetime, timezone, timedelta

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
        t1 = match.team1.name if match.team1 else '?'
        t2 = match.team2.name if match.team2 else '?'
        message = f'🌧️ No result — {t1} vs {t2}. No points affected.'

    Notification.objects.create(
        user=sel.user,
        type='pick_result',
        message=message,
        meta={'match_id': match_id, 'selection_id': selection_id},
    )

    # Web Push
    for sub in PushSubscription.objects.filter(user=sel.user):
        send_push_notification(sub, title='CricFun', body=message, url='/results', tag=f'pick-result-{match_id}')

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
        if send_push_notification(sub, title='CricFun', body=message, url='/standings', tag='rank-change'):
            sent += 1

    logger.info(
        'notify_rank_change: %d in-app + %d push notifications sent (%s took rank 1)',
        len(users), sent, new_leader,
    )


@shared_task
def send_custom_notification(title, message, url, user_ids):
    """
    Send an admin-authored custom notification to a list of users.
    Creates in-app Notification records and sends Web Push to subscribers.
    """
    from django.contrib.auth.models import User
    from apps.notifications.models import Notification, PushSubscription
    from apps.notifications.utils import send_push_notification

    users = list(User.objects.filter(id__in=user_ids, is_active=True))

    Notification.objects.bulk_create([
        Notification(user=u, type='custom', message=message, meta={'title': title, 'url': url or '/'})
        for u in users
    ])

    subs = PushSubscription.objects.filter(user__in=users).select_related('user')
    sent = 0
    for sub in subs:
        if send_push_notification(sub, title=title, body=message, url=url or '/'):  # no tag — admin messages always stack
            sent += 1

    logger.info('send_custom_notification: %d in-app + %d push sent', len(users), sent)
    return {'in_app': len(users), 'push': sent}


@shared_task
def notify_admin_quota_warning(used: int, limit: int):
    """
    Send an in-app notification to all staff users when CricAPI quota hits 90%.
    Fired once per day from cricapi._sync_hits when hitsToday >= QUOTA_WARN_THRESHOLD.
    """
    from django.contrib.auth.models import User
    from apps.notifications.models import Notification

    staff_users = list(User.objects.filter(is_staff=True, is_active=True))
    if not staff_users:
        return

    remaining = limit - used
    message = (
        f'⚠️ CricAPI quota warning: {used}/{limit} calls used today '
        f'({remaining} remaining). Live polling will slow down automatically.'
    )
    Notification.objects.bulk_create([
        Notification(
            user=u,
            type='custom',
            message=message,
            meta={'title': 'API Quota Warning', 'url': '/admin/core/sitesettings/1/change/'},
        )
        for u in staff_users
    ])
    logger.info('notify_admin_quota_warning: notified %d staff user(s)', len(staff_users))


@shared_task
def send_pick_reminders():
    """
    Runs every 30 min via Beat.
    Sends a Web Push to users who haven't picked for matches closing in ~24h or ~1h.
    Redis cache prevents duplicate sends within each window.
    No in-app notification — the sticky dropdown notice already covers that.
    """
    from django.core.cache import cache
    from teams.models import Match, Selection
    from apps.notifications.models import PushSubscription
    from apps.notifications.utils import send_push_notification

    now = datetime.now(timezone.utc)

    windows = [
        ('24h', now + timedelta(hours=23),   now + timedelta(hours=25),   '24 hrs'),
        ('1h',  now + timedelta(minutes=50), now + timedelta(minutes=70), '1 hr'),
    ]

    total_sent = 0
    for window_key, start, end, label in windows:
        matches = (Match.objects
                   .filter(result='TBD', datetime__gte=start, datetime__lte=end)
                   .select_related('team1', 'team2'))

        for match in matches:
            picked_user_ids = set(
                Selection.objects.filter(match=match).values_list('user_id', flat=True)
            )

            subs = (PushSubscription.objects
                    .filter(user__is_active=True)
                    .exclude(user_id__in=picked_user_ids)
                    .select_related('user'))

            for sub in subs:
                cache_key = f'pick_reminder_{window_key}_{match.id}_{sub.user_id}'
                if cache.get(cache_key):
                    continue

                t1 = match.team1.name if match.team1 else '?'
                t2 = match.team2.name if match.team2 else '?'
                body = f'{t1} vs {t2} — pick locks in {label}!'

                if send_push_notification(
                    sub, title='⏰ Pick Reminder', body=body, url='/schedule',
                    tag=f'pick-reminder-{match.id}'
                ):
                    cache.set(cache_key, 1, timeout=3 * 3600)
                    total_sent += 1
                    logger.info(
                        'Pick reminder (%s) sent to user %s for match %s',
                        window_key, sub.user_id, match.id,
                    )

    logger.info('send_pick_reminders: %d push notifications sent', total_sent)
    return {'sent': total_sent}
