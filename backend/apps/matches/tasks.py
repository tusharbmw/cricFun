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

from django.db.models import Q as DQ
from teams.models import Match, Team, Tournament
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
            Q(result='IP') | Q(result='TOSS'),
            tournament__sport=Tournament.Sport.CRICKET,
        ).select_related('team1', 'team2', 'tournament')
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
            elif match.team1 and winner in (match.team1.name, match.team1.description):
                match.result = 'team1'
            elif match.team2 and winner in (match.team2.name, match.team2.description):
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

            tournament, _ = Tournament.objects.get_or_create(
                name=md['tournament'],
                defaults={'sport': Tournament.Sport.CRICKET},
            )

            Match.objects.create(
                match_id=md['match_id'],
                team1=team1,
                team2=team2,
                description=md['Description'],
                venue=md['venue'],
                result='TBD',
                datetime=match_dt,
                tournament=tournament,
                match_points=_decide_match_weight(md['Description']),
                playoff=_is_playoff(md['Description']),
            )
            added += 1
            logger.info('Added match: %s vs %s @ %s', md['Team1'], md['Team2'], match_dt)

        except Exception as exc:
            logger.error('Error adding match %s: %s', md.get('match_id'), exc)

    # Refresh state for all tournaments touched in this run
    seen_tournaments = {
        t for t in Match.objects.filter(result='TBD').values_list('tournament', flat=True)
        if t is not None
    }
    for t_id in seen_tournaments:
        try:
            update_tournament_state(Tournament.objects.get(pk=t_id))
        except Tournament.DoesNotExist:
            pass

    return f'{added} new matches added; {updated_ids} match_ids updated'


@shared_task
def fetch_football_matches(tournament_id=None):
    """
    Fetch full match schedule from football-data.org and upsert into DB.
    Costs 1 API call per tournament. Safe to run multiple times (idempotent).

    Called daily by beat (no args → all active soccer tournaments) or on-demand
    from the admin panel (tournament_id provided for a specific tournament).
    """
    from apps.matches.footballapi import (
        fetch_matches, map_status, map_stage, map_points, map_playoff, map_duration,
    )

    if tournament_id is not None:
        tournaments = list(Tournament.objects.filter(pk=tournament_id, sport=Tournament.Sport.SOCCER))
    else:
        tournaments = list(Tournament.objects.filter(sport=Tournament.Sport.SOCCER, is_active=True))

    if not tournaments:
        return 'no active soccer tournaments'

    summary = []
    for tournament in tournaments:
        if not tournament.external_id:
            summary.append(f'{tournament.name}: no external_id')
            continue

        raw = fetch_matches(tournament.external_id)
        if not raw:
            summary.append(f'{tournament.name}: no data returned')
            continue

        created = updated = 0
        for m in raw:
            try:
                stage = m.get('stage', '')
                group = m.get('group')
                score = m.get('score') or {}
                full_time = score.get('fullTime') or {}
                status = m.get('status', '')
                winner = score.get('winner')

                home_raw = m.get('homeTeam') or {}
                away_raw = m.get('awayTeam') or {}

                # Use 'TBD' for knockout matches where opponents aren't decided yet.
                # The match is still created so it shows in the schedule; the team
                # record gets updated automatically on the next sync when the API
                # provides the real name.
                home_name = home_raw.get('name') or 'TBD'
                away_name = away_raw.get('name') or 'TBD'

                team1, _ = Team.objects.get_or_create(
                    name=home_name,
                    defaults={
                        'logo_url':    home_raw.get('crest', ''),
                        'description': home_raw.get('tla') or home_raw.get('shortName', ''),
                    },
                )
                team2, _ = Team.objects.get_or_create(
                    name=away_name,
                    defaults={
                        'logo_url':    away_raw.get('crest', ''),
                        'description': away_raw.get('tla') or away_raw.get('shortName', ''),
                    },
                )

                match_dt = datetime.strptime(
                    m['utcDate'], '%Y-%m-%dT%H:%M:%SZ'
                ).replace(tzinfo=timezone.utc)

                fields = dict(
                    team1=team1,
                    team2=team2,
                    tournament=tournament,
                    description=map_stage(stage, group),
                    datetime=match_dt,
                    result=map_status(status, winner),
                    match_points=map_points(stage),
                    playoff=map_playoff(stage),
                    home_score=full_time.get('home'),
                    away_score=full_time.get('away'),
                    duration=map_duration(score.get('duration')),
                )

                obj, was_created = Match.objects.get_or_create(
                    match_id=str(m['id']),
                    defaults=fields,
                )
                if was_created:
                    created += 1
                else:
                    changed = [k for k, v in fields.items() if getattr(obj, k) != v]
                    if changed:
                        for k in changed:
                            setattr(obj, k, fields[k])
                        obj.save(update_fields=changed + ['updated_at'])
                        updated += 1

            except Exception as exc:
                logger.error('fetch_football_matches: error on match %s: %s', m.get('id'), exc)

        update_tournament_state(tournament)
        msg = f'{tournament.name}: created {created}, updated {updated}'
        summary.append(msg)
        logger.info('fetch_football_matches: %s', msg)

    return ' | '.join(summary)


@shared_task
def sync_football_scores():
    """
    Fetch live/recently-finished soccer matches and update scores in DB.
    Beat fires every 60 s; task self-skips when no live or imminent matches.
    Costs 1 API call per active tournament when it runs.
    """
    from datetime import timedelta as _td
    from apps.matches.footballapi import fetch_matches, map_status, map_duration

    tournaments = list(Tournament.objects.filter(sport=Tournament.Sport.SOCCER, is_active=True))
    if not tournaments:
        return 'no active soccer tournaments'

    now = datetime.now(timezone.utc)
    imminent_window = now + _td(hours=2)

    summary = []
    for tournament in tournaments:
        if not tournament.external_id:
            continue

        # Skip if no live or imminent matches (avoids burning API calls needlessly)
        has_relevant = Match.objects.filter(
            tournament=tournament, result='IP',
        ).exists() or Match.objects.filter(
            tournament=tournament, result='TBD', datetime__lte=imminent_window,
        ).exists()
        if not has_relevant:
            summary.append(f'{tournament.name}: no imminent matches')
            continue

        raw = fetch_matches(tournament.external_id, status='LIVE,IN_PLAY,PAUSED,FINISHED')
        if not raw:
            summary.append(f'{tournament.name}: no data')
            continue

        updated = 0
        for m in raw:
            try:
                try:
                    match = Match.objects.get(match_id=str(m['id']))
                except Match.DoesNotExist:
                    continue

                score = m.get('score') or {}
                full_time = score.get('fullTime') or {}
                api_status   = m.get('status', '')
                new_result   = map_status(api_status, score.get('winner'))
                new_home     = full_time.get('home')
                new_away     = full_time.get('away')
                new_duration = map_duration(score.get('duration'))
                new_minute   = m.get('minute')
                injury_time  = m.get('injuryTime') or 0
                new_status_text = _build_soccer_status(
                    api_status, new_minute, injury_time, new_duration,
                )

                changed = []
                diffs = []
                for field, val in [
                    ('result',      new_result),
                    ('home_score',  new_home),
                    ('away_score',  new_away),
                    ('minute',      new_minute),
                    ('duration',    new_duration),
                    ('status_text', new_status_text),
                ]:
                    old = getattr(match, field)
                    if old != val:
                        setattr(match, field, val)
                        changed.append(field)
                        diffs.append(f'{field}: {old!r}→{val!r}')

                if changed:
                    match.save(update_fields=changed + ['updated_at'])
                    updated += 1
                    t1 = match.team1.name if match.team1 else '?'
                    t2 = match.team2.name if match.team2 else '?'
                    logger.info('sync_football_scores: %s vs %s | %s', t1, t2, ' | '.join(diffs))

                    if 'result' in changed and new_result in ('team1', 'team2', 'draw', 'NR'):
                        finalize_match_results.delay(match.id)

            except Exception as exc:
                logger.error('sync_football_scores: error on match %s: %s', m.get('id'), exc)

        summary.append(f'{tournament.name}: {updated} updated')

    return ' | '.join(summary) if summary else 'nothing to sync'


@shared_task
def finalize_match_results(match_id):
    """Triggered after a match result is set. Dispatches pick processing."""
    from apps.picks.tasks import process_pick_results
    process_pick_results.delay(match_id)
    return f'finalize triggered for match {match_id}'


def update_tournament_state(tournament):
    """
    Derive Tournament.state from the current or next match stage and save it.
    Looks at the earliest live/upcoming match, falling back to the most recent completed one.
    Called after each sync so the arena-chooser badge stays accurate automatically.
    """
    active = (
        Match.objects
        .filter(tournament=tournament)
        .filter(DQ(result='IP') | DQ(result='TBD') | DQ(result='TOSS'))
        .order_by('datetime')
        .first()
    )
    ref = active or (
        Match.objects
        .filter(tournament=tournament, result__in=['team1', 'team2', 'draw', 'NR'])
        .order_by('-datetime')
        .first()
    )
    if not ref or not ref.description:
        return

    desc = ref.description
    if 'Final' in desc and 'Semi' not in desc and 'Quarter' not in desc and 'Third' not in desc:
        state = 'Final'
    elif 'Third' in desc:
        state = 'Third Place'
    elif 'Semi' in desc:
        state = 'Semi-finals'
    elif 'Quarter' in desc:
        state = 'Quarter-finals'
    elif 'Round of 16' in desc or 'Last 16' in desc:
        state = 'Round of 16'
    elif 'Round of 32' in desc or 'Last 32' in desc:
        state = 'Round of 32'
    elif 'Playoff' in desc or 'playoff' in desc:
        state = 'Playoffs'
    else:
        state = 'Group Stage'

    if tournament.state != state:
        tournament.state = state
        tournament.save(update_fields=['state'])
        logger.info('Tournament state updated: %s → %s', tournament.name, state)


def _build_soccer_status(api_status: str, minute: int | None, injury_time: int, duration: str | None) -> str:
    """Build a compact live status string for soccer matches (time-only, no score)."""
    if api_status == 'PAUSED':
        return 'HT'
    if api_status in ('IN_PLAY',):
        if duration == 'PENALTY_SHOOTOUT':
            return 'Pens'
        if minute is None:
            return 'Live'
        time_str = f"{minute}+{injury_time}'" if injury_time > 0 else f"{minute}'"
        if duration == 'EXTRA_TIME':
            return f'ET {time_str}'
        return time_str
    return ''


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


@shared_task
def sync_match_odds():
    """
    Fetch pre-match odds from The Odds API and store in Match.odds.
    Runs every 6 hours via Beat. Skips if odds_sync_paused or no key configured.
    3 markets × 1 region = 3 credits per run → ~360 credits/month at 4×/day.
    """
    from django.conf import settings
    from apps.core.models import SiteSettings

    if not getattr(settings, 'SPORTS_ODDS_API_KEY', ''):
        logger.info('sync_match_odds: SPORTS_ODDS_API_KEY not configured, skipping')
        return 'no api key'

    if SiteSettings.get().odds_sync_paused:
        logger.info('sync_match_odds: odds sync paused (SiteSettings), skipping')
        return 'paused'

    from apps.matches.oddsapi import fetch_and_store_odds
    result = fetch_and_store_odds()
    return result
