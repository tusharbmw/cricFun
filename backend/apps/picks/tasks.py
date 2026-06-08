"""
Pick-related Celery tasks.
"""
import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task
def process_pick_results(match_id):
    """
    Called after a match result is finalised.
    Triggers per-user pick result notifications and snapshots the leaderboard.
    """
    from teams.models import Match, Selection

    try:
        match = Match.objects.select_related('team1', 'team2').get(pk=match_id)
    except Match.DoesNotExist:
        logger.error('process_pick_results: match %s not found', match_id)
        return

    if match.result not in ('team1', 'team2', 'draw', 'NR'):
        logger.warning('process_pick_results: match %s has no final result yet (%s)', match_id, match.result)
        return

    selections = Selection.objects.filter(match=match).select_related('user', 'selection')
    logger.info(
        'process_pick_results: match %s (%s vs %s) result=%s, %d selections',
        match_id, match.team1, match.team2, match.result, selections.count()
    )

    # Trigger notification task for each user with a pick on this match
    from apps.notifications.tasks import notify_pick_result
    for sel in selections:
        notify_pick_result.delay(sel.id, match_id)

    # For playoff matches, also notify users who didn't pick — they were
    # auto-assigned to the losing side and lost points.
    if match.playoff and match.result in ('team1', 'team2'):
        from django.contrib.auth.models import User
        from apps.notifications.models import Notification, PushSubscription
        from apps.notifications.utils import send_push_notification

        loser = match.team2 if match.result == 'team1' else match.team1
        t1    = match.team1.name if match.team1 else '?'
        t2    = match.team2.name if match.team2 else '?'
        message = (
            f'💀 Playoff auto-loss: you didn\'t pick {t1} vs {t2}. '
            f'You were assigned to the losing side ({loser.name}).'
        )
        picked_user_ids = set(selections.values_list('user_id', flat=True))
        non_pickers = list(
            User.objects.filter(
                is_active=True,
                tournament_enrollments__tournament=match.tournament,
            ).exclude(id__in=picked_user_ids)
        )
        Notification.objects.bulk_create([
            Notification(
                user=u, type='pick_result', message=message,
                meta={'match_id': match_id, 'auto_loss': True},
            )
            for u in non_pickers
        ])
        for u in non_pickers:
            for sub in PushSubscription.objects.filter(user=u):
                send_push_notification(
                    sub, title='TushFun', body=message,
                    url='/results', tag=f'pick-result-{match_id}',
                )
        logger.info(
            'process_pick_results: playoff auto-loss notifications sent to %d non-pickers for match %s',
            len(non_pickers), match_id,
        )

    # Snapshot the leaderboard state after this match result and refresh cache
    from apps.leaderboard.views import take_snapshot
    take_snapshot(match_id)

    return f'processed {selections.count()} picks for match {match_id}'
