"""
football-data.org API client.

Free tier: 10 requests/minute. One call fetches the full competition match list.
We track calls in Redis (`football_api_calls_today`) for the admin panel display.

Mapping functions are pure (no I/O) so they're easy to unit-test.
"""
import json
import logging
import time
import urllib.request

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

BASE_URL = 'https://api.football-data.org/v4'

CALLS_TODAY_KEY = 'football_api_calls_today'
CALLS_TODAY_TTL = 86400  # 24 h — Redis key expires with the day


# ── Stage mappings ────────────────────────────────────────────────────────────

_STAGE_DESCRIPTION = {
    'LAST_32':        'Round of 32',
    'LAST_16':        'Round of 16',
    'QUARTER_FINALS': 'Quarter-final',
    'SEMI_FINALS':    'Semi-final',
    'THIRD_PLACE':    'Third Place',
    'FINAL':          'Final',
}

_STAGE_POINTS = {
    'GROUP_STAGE':    1,
    'LAST_32':        2,
    'LAST_16':        3,
    'QUARTER_FINALS': 5,
    'SEMI_FINALS':    7,
    'THIRD_PLACE':    7,
    'FINAL':          10,
}

_KNOCKOUT_STAGES = frozenset({
    'LAST_32', 'LAST_16', 'QUARTER_FINALS', 'SEMI_FINALS', 'THIRD_PLACE', 'FINAL',
})


# ── Pure mapping functions ────────────────────────────────────────────────────

def map_status(status: str, winner: str | None) -> str:
    """Map API status + winner → internal Match.result value."""
    if status in ('SCHEDULED', 'TIMED'):
        return 'TBD'
    if status in ('IN_PLAY', 'PAUSED'):
        return 'IP'
    if status == 'FINISHED':
        if winner == 'HOME_TEAM':
            return 'team1'
        if winner == 'AWAY_TEAM':
            return 'team2'
        if winner == 'DRAW':
            return 'draw'
        return 'NR'
    # POSTPONED, CANCELLED, SUSPENDED
    return 'NR'


def map_stage(stage: str, group: str | None = None) -> str:
    """Map API stage (+ optional group) → human-readable Match.description."""
    if stage == 'GROUP_STAGE':
        if group:
            # API returns "GROUP_A", "GROUP_B", etc.
            letter = group.replace('GROUP_', '')
            return f'Group {letter}'
        return 'Group Stage'
    return _STAGE_DESCRIPTION.get(stage, stage.replace('_', ' ').title())


def map_points(stage: str) -> int:
    """Map API stage → Match.match_points (PV)."""
    return _STAGE_POINTS.get(stage, 1)


def map_playoff(stage: str) -> bool:
    """True for all knockout rounds (R32 and beyond)."""
    return stage in _KNOCKOUT_STAGES


def map_duration(duration: str | None) -> str | None:
    """Map API score.duration → Match.Duration choice (or None)."""
    if duration in ('REGULAR', 'EXTRA_TIME', 'PENALTY_SHOOTOUT'):
        return duration
    return None


# ── Infrastructure ────────────────────────────────────────────────────────────

def _api_key() -> str:
    return getattr(settings, 'FOOTBALL_DATA_API_KEY', '')


def _is_paused() -> bool:
    from apps.core.models import SiteSettings
    return SiteSettings.get().football_api_paused


def _inc_calls():
    """Increment today's call counter in Redis."""
    try:
        cache.incr(CALLS_TODAY_KEY)
    except ValueError:
        cache.set(CALLS_TODAY_KEY, 1, timeout=CALLS_TODAY_TTL)


# ── API call ──────────────────────────────────────────────────────────────────

def fetch_matches(competition_code: str, **params) -> list:
    """
    Call GET /v4/competitions/{code}/matches and return raw match list.

    Optional keyword params are appended as query string:
        fetch_matches('WC', status='LIVE,IN_PLAY,PAUSED,FINISHED')

    Returns [] on pause, missing key, or any request failure.
    Increments CALLS_TODAY_KEY on each successful HTTP call.
    """
    if _is_paused():
        logger.info('fetch_matches skipped — football API paused by admin.')
        return []

    key = _api_key()
    if not key:
        logger.warning('fetch_matches skipped — FOOTBALL_DATA_API_KEY not configured.')
        return []

    url = f'{BASE_URL}/competitions/{competition_code}/matches'
    if params:
        qs = '&'.join(f'{k}={v}' for k, v in params.items())
        url = f'{url}?{qs}'

    req = urllib.request.Request(url, headers={'X-Auth-Token': key})
    last_exc = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())
            break
        except Exception as exc:
            last_exc = exc
            if attempt < 2:
                time.sleep(2 ** attempt)  # 1s, 2s
    else:
        logger.error('fetch_matches request failed for %s after 3 attempts: %s', competition_code, last_exc)
        return []

    _inc_calls()
    matches = data.get('matches', [])
    logger.info('fetch_matches(%s): %d matches returned', competition_code, len(matches))
    return matches
