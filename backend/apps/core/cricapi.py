"""
Cricket API client — wraps CricAPI v1.

Rate-limit strategy
───────────────────
Budget: 100 calls/day (hard limit from CricAPI).

Every API response includes an `info` block:
    { "hitsToday": 15, "hitsLimit": 100, ... }

We use that as the authoritative remaining count (not an internal counter that
can drift on restarts).  After each call we store:
    cache["cricket_api_hits_used"]  ← server-reported hitsToday value
    cache["cricket_api_hits_limit"] ← server-reported value (usually 100)

The task layer (matches/tasks.py) calls `get_poll_interval(live_match_count)`
to decide how many seconds to wait before the next API poll, scaling down
as the budget shrinks.

Dynamic poll-interval table (per call, 2 calls per poll with 2 live matches):
    remaining > 80  → every 3 min   (early in the day, plenty left)
    remaining 50-80 → every 5 min   (normal; ~36 calls used in 3-hr window)
    remaining 25-50 → every 8 min   (conservation mode)
    remaining 10-25 → every 15 min  (critical conservation)
    remaining 3-10  → every 30 min  (emergency — drain as slowly as possible)
    remaining ≤ 3   → circuit open  (refuse all calls)
"""
import json
import logging
import urllib.request

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

# ── Cache keys ────────────────────────────────────────────────────────────────
CACHE_KEY_HITS_USED    = 'cricket_api_hits_used'
CACHE_KEY_HITS_LIMIT   = 'cricket_api_hits_limit'
CACHE_KEY_QUOTA_WARNED = 'cricket_api_quota_warned'
CACHE_KEY_MATCH_PFX    = 'cricket_api_match_v2_'   # v2: stores dict not string
CACHE_KEY_SERIES       = 'cricket_api_series_info'

# ── Cache TTLs ────────────────────────────────────────────────────────────────
MATCH_LIVE_TTL      = 60       # live match: re-check after 1 min
MATCH_COMPLETED_TTL = 86400    # completed: stable for 24 h
SERIES_TTL          = 3600     # series listing: stable for 1 h
HITS_COUNTER_TTL    = 86400    # reset with the API's day boundary

# ── Safety reserve ────────────────────────────────────────────────────────────
CIRCUIT_BREAKER_RESERVE = 3    # refuse all calls below this
QUOTA_WARN_THRESHOLD    = 90   # notify admin when hits reach this


def _api_key():
    return getattr(settings, 'CRICKET_API_KEY', '')


def _is_paused() -> bool:
    """Return True if admin has paused all CricAPI calls."""
    from apps.core.models import SiteSettings
    return SiteSettings.get().api_paused


# ── Hits tracking (server-authoritative) ──────────────────────────────────────

def _sync_hits(info: dict):
    """
    Called after every successful API response.
    Stores the server-reported hitsToday / hitsLimit in Redis.
    Also fires a one-shot admin warning notification when quota hits 90.
    """
    used  = info.get('hitsToday', 0)
    limit = info.get('hitsLimit', 100)
    cache.set(CACHE_KEY_HITS_USED,  used,  timeout=HITS_COUNTER_TTL)
    cache.set(CACHE_KEY_HITS_LIMIT, limit, timeout=HITS_COUNTER_TTL)

    # Fire admin quota warning once per day when threshold is crossed
    if used >= QUOTA_WARN_THRESHOLD and not cache.get(CACHE_KEY_QUOTA_WARNED):
        cache.set(CACHE_KEY_QUOTA_WARNED, 1, timeout=HITS_COUNTER_TTL)
        try:
            from apps.notifications.tasks import notify_admin_quota_warning
            notify_admin_quota_warning.delay(used, limit)
        except Exception as exc:
            logger.error('Failed to queue quota warning notification: %s', exc)

    return used, limit


def get_hits_status() -> dict:
    """Return {'used': N, 'limit': N, 'remaining': N}."""
    used  = cache.get(CACHE_KEY_HITS_USED,  0)
    limit = cache.get(CACHE_KEY_HITS_LIMIT, 100)
    return {'used': used, 'limit': limit, 'remaining': max(0, limit - used)}


def _budget_ok() -> bool:
    return get_hits_status()['remaining'] > CIRCUIT_BREAKER_RESERVE


# ── Dynamic poll-interval calculation ─────────────────────────────────────────

def get_poll_interval(live_match_count: int = 1) -> int:
    """
    Return how many seconds to wait before the next live-score API poll.

    `live_match_count` is how many matches are currently IP — each one
    consumes one API call per poll, so with 2 live matches every poll
    costs 2 calls and the interval should be doubled accordingly.

    The base intervals below are calibrated for 1 live match.
    For 2 matches we scale up proportionally so the total call rate stays
    the same regardless of how many matches are running.

    With 2 matches × 4 h each and a base interval of 5 min (300 s):
        2 matches × (240 min / 5 min) = 96 calls — within the 100 limit.
    """
    remaining = get_hits_status()['remaining']

    # Base interval for 1 live match
    if remaining > 80:
        base = 180    # 3 min
    elif remaining > 50:
        base = 300    # 5 min  ← normal operating point
    elif remaining > 25:
        base = 480    # 8 min
    elif remaining > 10:
        base = 900    # 15 min
    else:
        base = 1800   # 30 min (emergency)

    # Scale up linearly with the number of concurrent matches so the total
    # calls-per-hour stays constant.
    count = max(live_match_count, 1)
    return base * count


# ── API calls ─────────────────────────────────────────────────────────────────

def get_series_info(tournament_id=None) -> list:
    """
    Fetch all matches in a tournament series (1 API call, cached 1 h).
    Returns list of match dicts or [] on failure / budget exhausted / paused.
    """
    if _is_paused():
        logger.info('get_series_info skipped — API is paused by admin.')
        return []

    if tournament_id is None:
        from apps.core.models import SiteSettings
        tournament_id = SiteSettings.get().tournament_id or getattr(settings, 'CRICKET_TOURNAMENT_ID', '')

    cached = cache.get(CACHE_KEY_SERIES)
    if cached is not None:
        return cached

    if not _budget_ok():
        logger.warning('series_info skipped — API budget at circuit-breaker threshold.')
        return []

    url = (
        f'https://api.cricapi.com/v1/series_info'
        f'?apikey={_api_key()}&id={tournament_id}'
    )
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read().decode())
    except Exception as exc:
        logger.error('series_info request failed: %s', exc)
        return []

    if 'info' in data:
        used, limit = _sync_hits(data['info'])
        logger.info('series_info called — hits today: %d/%d', used, limit)

    if 'data' not in data:
        logger.warning('series_info empty response: status=%s', data.get('status'))
        return []

    matches = []
    for match in data['data'].get('matchList', []):
        try:
            if 'Tbc' in match.get('teams', []):
                continue

            teams = match['teams']
            team_info = match.get('teamInfo', [])

            # Guard against teamInfo with fewer than 2 entries
            if len(team_info) >= 2:
                if team_info[0]['name'] == teams[0]:
                    t1_info, t2_info = team_info[0], team_info[1]
                else:
                    t1_info, t2_info = team_info[1], team_info[0]
            else:
                t1_info = {'name': teams[0], 'shortname': '', 'img': ''}
                t2_info = {'name': teams[1], 'shortname': '', 'img': ''}

            comma_count = match['name'].count(',')
            description = match['name'].split(',')[comma_count * -1 if comma_count else 0].strip()
            venue        = match.get('venue', '').split(',')[-1].strip()

            matches.append({
                'match_id':    match['id'],
                'Team1':       teams[0],
                'Team2':       teams[1],
                'Team1Info':   t1_info,
                'Team2Info':   t2_info,
                'Description': description,
                'venue':       venue,
                'datetime':    match['dateTimeGMT'],
                'tournament':  tournament_id,
            })
        except Exception as exc:
            logger.error('Error parsing match from series_info: %s — %s', match, exc)

    cache.set(CACHE_KEY_SERIES, matches, timeout=SERIES_TTL)
    return matches


def get_match_info(match_id: str) -> dict:
    """
    Get live/final data for a specific match.

    Returns a dict:
        {
            'winner':      str,   # team name | 'TBD' | 'IP' | 'No Winner' | 'ERR'
            'scores':      list,  # [{"r": 185, "w": 6, "o": 20.0, "inning": "CSK Inning 1"}, ...]
            'status_text': str,   # e.g. "CSK won by 6 wickets" or "" if not available
        }

    Cache TTLs:
        live (IP)    → MATCH_LIVE_TTL (60 s)
        completed    → MATCH_COMPLETED_TTL (24 h)
        not started  → 5 min
    """
    err = {'winner': 'ERR', 'scores': [], 'status_text': ''}

    if _is_paused():
        logger.info('get_match_info skipped for %s — API is paused by admin.', match_id)
        return {'winner': 'IP', 'scores': [], 'status_text': ''}

    if not match_id or len(str(match_id)) < 5:
        return err

    cache_key = f'{CACHE_KEY_MATCH_PFX}{match_id}'
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    if not _budget_ok():
        logger.warning('match_info skipped for %s — circuit breaker open.', match_id)
        return {'winner': 'IP', 'scores': [], 'status_text': ''}  # assume still running

    url = (
        f'https://api.cricapi.com/v1/match_info'
        f'?apikey={_api_key()}&id={match_id}'
    )
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read().decode())
    except Exception as exc:
        logger.error('match_info request failed for %s: %s', match_id, exc)
        return err

    if 'info' in data:
        used, limit = _sync_hits(data['info'])
        logger.info(
            'match_info %s called — hits today: %d/%d (remaining: %d)',
            match_id, used, limit, limit - used
        )

    if data.get('status') != 'success':
        logger.warning('match_info non-success for %s: %s', match_id, data.get('status'))
        return {'winner': 'TBD', 'scores': [], 'status_text': ''}

    match_data  = data.get('data', {})
    scores      = match_data.get('score', [])
    status_text = match_data.get('status', '')

    if not match_data.get('matchStarted'):
        result = {'winner': 'TBD', 'scores': scores, 'status_text': status_text}
        ttl    = 300
    elif not match_data.get('matchEnded'):
        result = {'winner': 'IP', 'scores': scores, 'status_text': status_text}
        ttl    = MATCH_LIVE_TTL
    else:
        winner = match_data.get('matchWinner', '')
        result = {
            'winner':      winner if winner else 'No Winner',
            'scores':      scores,
            'status_text': status_text,
        }
        ttl = MATCH_COMPLETED_TTL

    cache.set(cache_key, result, timeout=ttl)
    return result
