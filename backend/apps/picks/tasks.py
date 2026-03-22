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

    if match.result not in ('team1', 'team2', 'NR'):
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

    # Snapshot the leaderboard state after this match result and refresh cache
    from apps.leaderboard.views import take_snapshot
    take_snapshot(match_id)

    return f'processed {selections.count()} picks for match {match_id}'
