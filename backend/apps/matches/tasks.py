"""
Match-related Celery tasks.

Polling architecture
────────────────────
Beat fires `update_live_scores` every 60 s (cheap: just reads Redis).
The task gate-keeps actual API calls via a `next_live_check_at` timestamp
stored in Redis.  After each real poll the task:
  1. reads hitsUsed/hitsLimit from the last API response (stored by cricapi)
  2. calls get_poll_interval(live_match_count) to get the next wait (seconds)
  3. stores  now + wait  as the next allowed check time

This lets the interval shrink or grow throughout the day based on how much
budget remains, without touching the beat schedule.

Budget math (worst-case day):
  - 2 live matches × 4 h each, polled together every 5 min
  - 2 calls/poll × (240 min / 5 min) = 96 calls for live monitoring
  - + 1 call for fetch_upcoming  =  97 calls total  ← under 100 limit
  When budget drops, interval automatically widens (up to 30 min).
"""
import logging
from datetime import datetime, timezone, timedelta

from celery import shared_task
from django.core.cache import cache
from django.db.models import Q

from teams.models import Match, Team
from apps.core import cricapi

logger = logging.getLogger(__name__)

CACHE_KEY_NEXT_CHECK = 'matches_next_live_check_at'


def _now_ts() -> float:
    return datetime.now(timezone.utc).timestamp()


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def update_live_scores(self):
    """
    Beat fires this every 60 s.
    Actual API calls are gated by next_live_check_at in Redis.
    """
    # ── 1. Are any matches live? ──────────────────────────────────────────────
    live_matches = list(
        Match.objects.filter(
            Q(result='IP') | Q(result='TOSS')
        ).select_related('team1', 'team2')
    )

    if not live_matches:
        logger.debug('update_live_scores: no live matches — skipping.')
        cache.delete(CACHE_KEY_NEXT_CHECK)   # reset gate when nothing is live
        return 'no live matches'

    # ── 2. Budget gate ────────────────────────────────────────────────────────
    hits = cricapi.get_hits_status()
    if hits['remaining'] <= cricapi.CIRCUIT_BREAKER_RESERVE:
        logger.warning(
            'update_live_scores: circuit breaker open '
            '(%d/%d hits used) — skipping all API calls.',
            hits['used'], hits['limit']
        )
        return 'circuit breaker open'

    # ── 3. Time gate — is it time for the next poll? ──────────────────────────
    next_check = cache.get(CACHE_KEY_NEXT_CHECK)
    now = _now_ts()
    if next_check and now < next_check:
        wait = int(next_check - now)
        logger.debug('update_live_scores: next poll in %d s — skipping.', wait)
        return f'too early (next poll in {wait}s)'

    # ── 4. Make API calls ─────────────────────────────────────────────────────
    updated = 0
    for match in live_matches:
        try:
            info   = cricapi.get_match_info(match.match_id)
            winner = info['winner']

            # Always persist latest scores + status even if match is still live
            score_changed = (
                info['scores'] != match.scores or
                info['status_text'] != match.status_text
            )
            if score_changed:
                match.scores      = info['scores']
                match.status_text = info['status_text']
                match.save(update_fields=['scores', 'status_text', 'updated_at'])

            if winner in ('TBD', 'IP', 'ERR'):
                continue

            if winner == 'No Winner':
                match.result = 'NR'
            elif match.team1 and winner == match.team1.name:
                match.result = 'team1'
            elif match.team2 and winner == match.team2.name:
                match.result = 'team2'
            else:
                logger.warning(
                    'Unknown winner "%s" for match %s (%s vs %s)',
                    winner, match.id, match.team1, match.team2
                )
                continue

            match.save(update_fields=['result', 'updated_at'])
            updated += 1
            logger.info('Match %s (%s) → %s', match.id, match.description, match.result)
            finalize_match_results.delay(match.id)

        except Exception as exc:
            logger.error('Error checking match %s: %s', match.id, exc)
            self.retry(exc=exc)

    # ── 5. Set next gate based on current budget ──────────────────────────────
    interval = cricapi.get_poll_interval(live_match_count=len(live_matches))
    cache.set(CACHE_KEY_NEXT_CHECK, _now_ts() + interval, timeout=interval + 120)

    hits_after = cricapi.get_hits_status()
    logger.info(
        'update_live_scores: %d updated | %d/%d hits used | next poll in %d s (~%d min)',
        updated, hits_after['used'], hits_after['limit'], interval, interval // 60
    )
    return f'{updated} matches updated; next poll in {interval}s'


@shared_task
def update_match_statuses():
    """
    Beat fires every 10 min.
    DB-only: transitions TBD → IP for matches whose start time has passed.
    Zero API calls.
    """
    now = datetime.now(timezone.utc)
    updated = Match.objects.filter(result='TBD', datetime__lte=now).update(result='IP')
    if updated:
        logger.info('update_match_statuses: %d matches TBD→IP', updated)
    return f'{updated} matches set to IP'


@shared_task
def fetch_upcoming_matches():
    """
    Beat fires at 6 AM daily.
    Fetches the tournament schedule and creates any missing Match + Team rows.
    Costs 1 API call (cached 1 h so manual retriggers don't waste budget).
    """
    now = datetime.now(timezone.utc)
    matches_data = cricapi.get_series_info()
    if not matches_data:
        logger.warning('fetch_upcoming_matches: no data returned.')
        return 'no data'

    added = 0
    updated_ids = 0
    for md in matches_data:
        try:
            match_dt = datetime.strptime(
                md['datetime'], '%Y-%m-%dT%H:%M:%S'
            ).replace(tzinfo=timezone.utc)

            if match_dt < now:
                continue

            # Check if a TBD match exists for this datetime with a different match_id
            # (CricAPI can reassign IDs for upcoming matches mid-series)
            existing = Match.objects.filter(datetime=match_dt, result='TBD').first()
            if existing:
                if existing.match_id != md['match_id']:
                    existing.match_id = md['match_id']
                    existing.save(update_fields=['match_id'])
                    updated_ids += 1
                    logger.info(
                        'Updated match_id for %s @ %s: %s → %s',
                        existing.description, match_dt, existing.match_id, md['match_id'],
                    )
                continue

            if Match.objects.filter(match_id=md['match_id']).exists():
                continue

            team1, _ = Team.objects.get_or_create(
                name=md['Team1'],
                defaults={
                    'logo_url':    md['Team1Info'].get('img', ''),
                    'description': md['Team1Info'].get('shortname', ''),
                },
            )
            team2, _ = Team.objects.get_or_create(
                name=md['Team2'],
                defaults={
                    'logo_url':    md['Team2Info'].get('img', ''),
                    'description': md['Team2Info'].get('shortname', ''),
                },
            )

            Match.objects.create(
                match_id=md['match_id'],
                team1=team1,
                team2=team2,
                description=md['Description'],
                venue=md['venue'],
                result='TBD',
                datetime=match_dt,
                tournament=md['tournament'],
                match_points=_decide_match_weight(md['Description']),
                playoff=_is_playoff(md['Description']),
            )
            added += 1
            logger.info('Added match: %s vs %s @ %s', md['Team1'], md['Team2'], match_dt)

        except Exception as exc:
            logger.error('Error adding match %s: %s', md.get('match_id'), exc)

    return f'{added} new matches added; {updated_ids} match_ids updated'


@shared_task
def finalize_match_results(match_id):
    """Triggered after a match result is set. Dispatches pick processing."""
    from apps.picks.tasks import process_pick_results
    process_pick_results.delay(match_id)
    return f'finalize triggered for match {match_id}'


def _decide_match_weight(description: str) -> int:
    if description == 'Final':
        return 5
    if description.startswith('Semi Final'):
        return 3
    if description.startswith('Super 8'):
        return 2
    if description in ('Qualifier 1', 'Qualifier 2'):
        return 3
    if description == 'Eliminator':
        return 2
    return 1


def _is_playoff(description: str) -> bool:
    return _decide_match_weight(description) > 1
