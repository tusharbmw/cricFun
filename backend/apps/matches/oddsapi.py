"""
The Odds API integration — fetches pre-match odds for soccer matches and
stores them in Match.odds as consensus values averaged across bookmakers.

Supported sport keys:
  soccer_fifa_world_cup  — FIFA World Cup 2026 (active)
  cricket_odi            — ODI internationals (active; no IPL T20)

Markets fetched:
  h2h      — win/draw/loss probabilities
  totals   — over/under expected total goals
  spreads  — handicap line (expected goal difference)

Stored in Match.odds:
{
  "team1": 1.41,           # consensus decimal odds for team1 win
  "draw": 4.5,             # consensus decimal odds for draw
  "team2": 8.9,            # consensus decimal odds for team2 win
  "total_line": 2.5,       # most common O/U goals line
  "over_odds": 2.10,       # consensus odds for over
  "under_odds": 1.70,      # consensus odds for under
  "spread_line": 1.5,      # expected goal difference (absolute)
  "spread_favored": "team1",  # which team is favored ("team1"/"team2")
  "updated_at": "2026-06-10T03:39Z"
}

Credits: 3 markets × 1 region × 4 runs/day × 30 days = 360 / 500 monthly limit.
"""
import json
import logging
import statistics
import urllib.request
import urllib.parse
from datetime import datetime, timezone, timedelta

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

BASE_URL = 'https://api.the-odds-api.com/v4'
REGION = 'eu'
MARKETS = 'h2h,totals,spreads'

CACHE_KEY_CREDITS_REMAINING = 'odds_api_credits_remaining'
CACHE_KEY_CREDITS_USED = 'odds_api_credits_used'
CACHE_KEY_LAST_SYNC = 'odds_api_last_sync'

# Map from our Tournament sport + known competition to The Odds API sport key
# Only soccer_fifa_world_cup is currently active for our use case
SPORT_KEY_MAP = {
    'soccer_fifa_world_cup': 'soccer_fifa_world_cup',
}


def _api_key():
    return getattr(settings, 'SPORTS_ODDS_API_KEY', '')


def _fetch(path, params):
    key = _api_key()
    if not key:
        raise ValueError('SPORTS_ODDS_API_KEY is not configured')
    params['apiKey'] = key
    url = f'{BASE_URL}{path}?{urllib.parse.urlencode(params)}'
    req = urllib.request.Request(url, headers={'Accept': 'application/json'})
    with urllib.request.urlopen(req, timeout=20) as resp:
        credits_remaining = resp.headers.get('x-requests-remaining')
        credits_used = resp.headers.get('x-requests-used')
        credits_last = resp.headers.get('x-requests-last')
        if credits_remaining is not None:
            cache.set(CACHE_KEY_CREDITS_REMAINING, int(credits_remaining), timeout=86400)
        if credits_used is not None:
            cache.set(CACHE_KEY_CREDITS_USED, int(credits_used), timeout=86400)
        logger.info(
            'Odds API call %s — last cost: %s, remaining: %s, used: %s',
            path, credits_last, credits_remaining, credits_used,
        )
        return json.loads(resp.read().decode())


# Odds API name → our DB Team.name (for known discrepancies)
_NAME_ALIASES = {
    'czech republic':       'czechia',
    'bosnia & herzegovina': 'bosnia-herzegovina',
    'cape verde':           'cape verde islands',
    'dr congo':             'congo dr',
    'usa':                  'united states',
}


def _normalize_name(name):
    n = name.lower().strip()
    return _NAME_ALIASES.get(n, n)


def _consensus_h2h(bookmakers, home_team, away_team):
    """Average decimal odds across bookmakers for h2h market."""
    home_prices, away_prices, draw_prices = [], [], []
    for bm in bookmakers:
        for market in bm.get('markets', []):
            if market['key'] != 'h2h':
                continue
            for outcome in market['outcomes']:
                n = _normalize_name(outcome['name'])
                p = outcome['price']
                if n == _normalize_name(home_team):
                    home_prices.append(p)
                elif n == _normalize_name(away_team):
                    away_prices.append(p)
                elif n == 'draw':
                    draw_prices.append(p)

    result = {}
    if home_prices:
        result['home'] = round(statistics.mean(home_prices), 3)
    if away_prices:
        result['away'] = round(statistics.mean(away_prices), 3)
    if draw_prices:
        result['draw'] = round(statistics.mean(draw_prices), 3)
    return result


def _consensus_dnb(bookmakers, home_team, away_team):
    """Average draw-no-bet decimal odds across bookmakers."""
    home_prices, away_prices = [], []
    for bm in bookmakers:
        for market in bm.get('markets', []):
            if market['key'] != 'draw_no_bet':
                continue
            for outcome in market['outcomes']:
                n = _normalize_name(outcome['name'])
                p = outcome['price']
                if n == _normalize_name(home_team):
                    home_prices.append(p)
                elif n == _normalize_name(away_team):
                    away_prices.append(p)

    result = {}
    if home_prices:
        result['home'] = round(statistics.mean(home_prices), 3)
    if away_prices:
        result['away'] = round(statistics.mean(away_prices), 3)
    return result


def _consensus_totals(bookmakers):
    """Find most common line value and average odds for that line."""
    line_data = {}  # line -> {'over': [], 'under': []}
    for bm in bookmakers:
        for market in bm.get('markets', []):
            if market['key'] != 'totals':
                continue
            for outcome in market['outcomes']:
                line = outcome.get('point')
                if line is None:
                    continue
                if line not in line_data:
                    line_data[line] = {'over': [], 'under': []}
                n = outcome['name'].lower()
                if n == 'over':
                    line_data[line]['over'].append(outcome['price'])
                elif n == 'under':
                    line_data[line]['under'].append(outcome['price'])

    if not line_data:
        return {}

    # Pick line with most data points
    best_line = max(line_data, key=lambda l: len(line_data[l]['over']) + len(line_data[l]['under']))
    d = line_data[best_line]
    result = {'total_line': best_line}
    if d['over']:
        result['over_odds'] = round(statistics.mean(d['over']), 3)
    if d['under']:
        result['under_odds'] = round(statistics.mean(d['under']), 3)
    return result


def _consensus_spread(bookmakers, home_team):
    """Find consensus handicap line to derive expected goal difference."""
    # Collect (home_point, home_price) pairs — home_point negative means home favored
    home_points = []
    for bm in bookmakers:
        for market in bm.get('markets', []):
            if market['key'] != 'spreads':
                continue
            for outcome in market['outcomes']:
                if _normalize_name(outcome['name']) == _normalize_name(home_team):
                    pt = outcome.get('point')
                    if pt is not None:
                        home_points.append(pt)

    if not home_points:
        return {}

    median_point = statistics.median(home_points)
    if median_point < 0:
        return {'spread_line': round(abs(median_point), 2), 'spread_favored': 'team1'}
    elif median_point > 0:
        return {'spread_line': round(abs(median_point), 2), 'spread_favored': 'team2'}
    else:
        return {'spread_line': 0.0, 'spread_favored': None}


def _match_event_to_db(event, team_name_map):
    """
    Find our Match for a given Odds API event by team name + date proximity.
    team_name_map: dict of normalized_name -> Team instance (all soccer teams).
    Returns (Match, home_is_team1) or (None, None).
    """
    from teams.models import Match

    home_norm = _normalize_name(event['home_team'])
    away_norm = _normalize_name(event['away_team'])

    home_team = team_name_map.get(home_norm)
    away_team = team_name_map.get(away_norm)

    if not home_team or not away_team:
        # Try partial match
        for norm, team in team_name_map.items():
            if not home_team and (home_norm in norm or norm in home_norm):
                home_team = team
            if not away_team and (away_norm in norm or norm in away_norm):
                away_team = team

    if not home_team or not away_team:
        logger.debug('Odds API: no team match for %s vs %s', event['home_team'], event['away_team'])
        return None, None

    event_dt = datetime.fromisoformat(event['commence_time'].replace('Z', '+00:00'))
    window_start = event_dt - timedelta(hours=12)
    window_end = event_dt + timedelta(hours=12)

    match = Match.objects.filter(
        result='TBD',
        datetime__gte=window_start,
        datetime__lte=window_end,
    ).filter(
        team1__in=[home_team, away_team],
        team2__in=[home_team, away_team],
    ).first()

    if not match:
        return None, None

    home_is_team1 = match.team1_id == home_team.id
    return match, home_is_team1


def fetch_and_store_odds():
    """
    Main entry point. Fetches odds for all active soccer tournaments,
    matches events to our Match objects, and writes to Match.odds.
    Returns a summary dict.
    """
    from teams.models import Match, Team, Tournament

    updated = 0
    skipped = 0
    errors = []

    # Build a name map for all soccer teams (for matching).
    # Use two flat ID queries to avoid DISTINCT over a table with JSONField (NCLOB on Oracle).
    soccer_matches = Match.objects.filter(tournament__sport='soccer')
    team_ids = set(soccer_matches.values_list('team1_id', flat=True)) | \
               set(soccer_matches.values_list('team2_id', flat=True))
    team_ids.discard(None)
    soccer_teams = Team.objects.filter(id__in=team_ids)
    team_name_map = {_normalize_name(t.name): t for t in soccer_teams}

    for sport_key in SPORT_KEY_MAP:
        try:
            events = _fetch(
                f'/sports/{sport_key}/odds',
                {'regions': REGION, 'markets': MARKETS, 'oddsFormat': 'decimal'},
            )
        except Exception as exc:
            logger.error('Odds API fetch failed for %s: %s', sport_key, exc)
            errors.append(str(exc))
            continue

        for event in events:
            match, home_is_team1 = _match_event_to_db(event, team_name_map)
            if not match:
                skipped += 1
                continue

            bookmakers = event.get('bookmakers', [])
            home_team_name = event['home_team']
            away_team_name = event['away_team']

            h2h = _consensus_h2h(bookmakers, home_team_name, away_team_name)
            dnb = _consensus_dnb(bookmakers, home_team_name, away_team_name)
            totals = _consensus_totals(bookmakers)
            spread = _consensus_spread(bookmakers, home_team_name)

            if not h2h:
                skipped += 1
                continue

            # Map home/away to team1/team2
            if home_is_team1:
                odds_data = {
                    'team1': h2h.get('home'),
                    'draw': h2h.get('draw'),
                    'team2': h2h.get('away'),
                    'team1_dnb': dnb.get('home'),
                    'team2_dnb': dnb.get('away'),
                }
            else:
                odds_data = {
                    'team1': h2h.get('away'),
                    'draw': h2h.get('home'),
                    'team2': h2h.get('away'),
                    'team1_dnb': dnb.get('away'),
                    'team2_dnb': dnb.get('home'),
                }
                # When home is team2, swap favored side too
                if spread.get('spread_favored') == 'team1':
                    spread['spread_favored'] = 'team2'
                elif spread.get('spread_favored') == 'team2':
                    spread['spread_favored'] = 'team1'

            odds_data.update(totals)
            odds_data.update(spread)
            odds_data['updated_at'] = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%MZ')

            # Remove None values
            odds_data = {k: v for k, v in odds_data.items() if v is not None}

            match.odds = odds_data
            match.save(update_fields=['odds'])
            updated += 1
            logger.debug('Odds updated for match %s (%s)', match.id, match.description)

    cache.set(CACHE_KEY_LAST_SYNC, datetime.now(timezone.utc).isoformat(), timeout=86400 * 7)
    logger.info('Odds sync complete: %d updated, %d skipped, %d errors', updated, skipped, len(errors))
    return {'updated': updated, 'skipped': skipped, 'errors': errors}
