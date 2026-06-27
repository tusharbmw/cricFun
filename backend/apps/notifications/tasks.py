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
    from apps.core.models import SiteSettings
    if SiteSettings.get().notifications_paused:
        logger.info('notify_pick_result: notifications paused (SiteSettings), skipping')
        return

    from django.contrib.auth.models import User
    from teams.models import Match, Selection
    from apps.notifications.models import Notification, PushSubscription
    from apps.notifications.utils import send_push_notification

    from django.core.cache import cache

    try:
        sel = Selection.objects.select_related(
            'user', 'match__team1', 'match__team2', 'match__tournament', 'selection',
        ).get(pk=selection_id)
        match = sel.match
    except Selection.DoesNotExist:
        logger.error('notify_pick_result: selection %s not found', selection_id)
        return

    cache_key = f'pick_result_notified_{match_id}_{sel.user_id}'
    if cache.get(cache_key):
        logger.info('notify_pick_result: duplicate skipped for user %s match %s', sel.user_id, match_id)
        return

    t1 = match.team1.name if match.team1 else '?'
    t2 = match.team2.name if match.team2 else '?'
    tournament_suffix = f' ({match.tournament.name})' if match.tournament else ''

    if match.result in ('team1', 'team2'):
        winner = match.team1 if match.result == 'team1' else match.team2
        if sel.draw:
            message = f'❌ Wrong pick — {winner.name} won, you picked Draw.{tournament_suffix}'
        elif sel.selection == winner:
            message = f'✅ Correct pick! {winner.name} won.{tournament_suffix}'
        else:
            message = f'❌ Wrong pick. {winner.name} won.{tournament_suffix}'
    elif match.result == 'draw':
        if sel.draw:
            message = f'⚖ Draw — you got it right! {t1} vs {t2} drew.{tournament_suffix}'
        else:
            message = f'⚖ Draw — {t1} vs {t2} drew. Your team pick missed.{tournament_suffix}'
    else:
        message = f'🌧️ No result — {t1} vs {t2}. No points affected.{tournament_suffix}'

    Notification.objects.create(
        user=sel.user,
        type='pick_result',
        message=message,
        meta={'match_id': match_id, 'selection_id': selection_id, 'tournament_id': match.tournament_id},
    )

    for sub in PushSubscription.objects.filter(user=sel.user):
        send_push_notification(sub, title='TushFun', body=message, url='/results', tag=f'pick-result-{match_id}')

    cache.set(cache_key, 1, timeout=24 * 3600)
    logger.info('notify_pick_result: notified user %s for selection %s', sel.user_id, selection_id)


@shared_task
def notify_rank_change(new_leader, match_id, prev_leader=None):
    """
    Create an in-app Notification for ALL active users when rank #1 changes,
    and send a Web Push to each user's subscribed devices.
    """
    from apps.core.models import SiteSettings
    if SiteSettings.get().notifications_paused:
        logger.info('notify_rank_change: notifications paused (SiteSettings), skipping')
        return

    from django.contrib.auth.models import User
    from teams.models import Match
    from apps.notifications.models import Notification, PushSubscription
    from apps.notifications.utils import send_push_notification

    try:
        tournament = Match.objects.select_related('tournament').get(pk=match_id).tournament
        tournament_suffix = f' ({tournament.name})' if tournament else ''
    except Match.DoesNotExist:
        tournament_suffix = ''

    if prev_leader:
        message = f'🏆 {new_leader} has taken the lead!{tournament_suffix}'
    else:
        message = f'🏆 {new_leader} is leading the standings!{tournament_suffix}'

    tournament_id = None
    try:
        tournament_id = Match.objects.get(pk=match_id).tournament_id
    except Exception:
        pass
    meta  = {'new_leader': new_leader, 'prev_leader': prev_leader, 'match_id': match_id, 'tournament_id': tournament_id}
    users = list(User.objects.filter(is_active=True))

    Notification.objects.bulk_create([
        Notification(user=u, type='rank_change', message=message, meta=meta)
        for u in users
    ])

    subs = PushSubscription.objects.filter(user__is_active=True).select_related('user')
    sent = 0
    for sub in subs:
        if send_push_notification(sub, title='TushFun', body=message, url='/standings', tag='rank-change'):
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
    from apps.core.models import SiteSettings
    if SiteSettings.get().notifications_paused:
        logger.info('send_custom_notification: notifications paused (SiteSettings), skipping')
        return {'in_app': 0, 'push': 0}

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
    from apps.core.models import SiteSettings
    if SiteSettings.get().notifications_paused:
        logger.info('send_pick_reminders: notifications paused (SiteSettings), skipping')
        return {'sent': 0}

    from django.core.cache import cache
    from teams.models import Match, Selection
    from apps.notifications.models import PushSubscription
    from apps.notifications.utils import send_push_notification

    now = datetime.now(timezone.utc)

    windows = [
        ('24h', now + timedelta(hours=23),   now + timedelta(hours=25),   '24 hrs'),
        ('1h',  now + timedelta(minutes=45), now + timedelta(minutes=75), '1 hr'),
    ]

    total_sent = 0
    for window_key, start, end, label in windows:
        matches = (Match.objects
                   .filter(result='TBD', datetime__gte=start, datetime__lte=end,
                           team1__isnull=False, team2__isnull=False)
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
                    sub, title='⏰ Pick Reminder', body=body, url=f'/match/{match.id}',
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


@shared_task
def notify_personal_rank_changes(changes, match_id):
    """
    Notify each user whose rank moved after a match result.
    changes: [{'user_id': int, 'old_rank': int, 'new_rank': int, 'moved_up': bool}]
    """
    from apps.core.models import SiteSettings
    if SiteSettings.get().notifications_paused:
        logger.info('notify_personal_rank_changes: notifications paused (SiteSettings), skipping')
        return

    from django.contrib.auth.models import User
    from teams.models import Match
    from apps.notifications.models import Notification, PushSubscription
    from apps.notifications.utils import send_push_notification

    try:
        tournament = Match.objects.select_related('tournament').get(pk=match_id).tournament
        tournament_suffix = f' ({tournament.name})' if tournament else ''
    except Match.DoesNotExist:
        tournament_suffix = ''

    sent = 0
    for change in changes:
        try:
            user = User.objects.get(pk=change['user_id'])
        except User.DoesNotExist:
            continue

        if change['moved_up']:
            message = f"📈 You moved up to rank #{change['new_rank']} (was #{change['old_rank']}){tournament_suffix}"
        else:
            message = f"📉 You dropped to rank #{change['new_rank']} (was #{change['old_rank']}){tournament_suffix}"

        Notification.objects.create(
            user=user,
            type='rank_change',
            message=message,
            meta={'match_id': match_id, 'old_rank': change['old_rank'], 'new_rank': change['new_rank'], 'tournament_id': tournament.id if tournament else None},
        )
        for sub in PushSubscription.objects.filter(user=user):
            if send_push_notification(
                sub, title='TushFun', body=message,
                url='/standings', tag=f'my-rank-{match_id}',
            ):
                sent += 1

    logger.info(
        'notify_personal_rank_changes: %d users notified, %d push sent for match %s',
        len(changes), sent, match_id,
    )


@shared_task
def notify_tournament_over(match_id, top3_text):
    """
    Notify all active approved users that the tournament is over with top-3 results.
    Fired once after the Final match snapshot is taken.
    """
    from apps.core.models import SiteSettings
    if SiteSettings.get().notifications_paused:
        logger.info('notify_tournament_over: notifications paused (SiteSettings), skipping')
        return

    from django.contrib.auth.models import User
    from apps.notifications.models import Notification, PushSubscription
    from apps.notifications.utils import send_push_notification

    from teams.models import Match
    from apps.users.models import TournamentEnrollment
    try:
        match = Match.objects.select_related('tournament').get(pk=match_id)
        tournament = match.tournament
        enrolled_user_ids = TournamentEnrollment.objects.filter(
            tournament=tournament
        ).values_list('user_id', flat=True)
        users = list(User.objects.filter(is_active=True, id__in=enrolled_user_ids))
        push_title = f'🏆 {tournament.name}' if tournament else '🏆 Tournament Over'
    except Match.DoesNotExist:
        users = []
        push_title = '🏆 Tournament Over'

    Notification.objects.bulk_create([
        Notification(
            user=u, type='rank_change', message=top3_text,
            meta={'match_id': match_id, 'tournament_over': True, 'tournament_id': tournament.id if tournament else None},
        )
        for u in users
    ])

    subs = (PushSubscription.objects
            .filter(user__is_active=True, user__id__in=[u.id for u in users])
            .select_related('user'))
    sent = 0
    for sub in subs:
        if send_push_notification(
            sub, title=push_title, body=top3_text,
            url='/standings', tag='tournament-over',
        ):
            sent += 1

    logger.info(
        'notify_tournament_over: %d in-app + %d push sent for match %s',
        len(users), sent, match_id,
    )
