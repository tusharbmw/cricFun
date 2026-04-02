import logging

from django.contrib.auth.models import User
from django.core.cache import cache
from django.db.models import Q
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from teams.models import Match, Selection

logger = logging.getLogger(__name__)

MAX_SKIPPED_ALLOWED = 5
DISQUALIFICATION_SCORE = -999

CACHE_KEY_LEADERBOARD = 'leaderboard:ranked'
CACHE_TTL = 86400  # 24 hours


# ---------------------------------------------------------------------------
# Core scoring logic
# ---------------------------------------------------------------------------

def calculate_scores(upto_match_id=None):
    """
    Compute scores for all active users.

    Args:
        upto_match_id: If given, only count matches with datetime <= that match's
                       datetime. Used by backfill to reconstruct historical states.
                       Default None = use all completed matches.

    Returns dict: {username: {user_id, username, won, lost, skipped,
                               matches_won, matches_lost}}
    """
    scores = {}
    for u in User.objects.filter(is_active=True):
        scores[u.username] = {
            'user_id':       u.id,
            'username':      u.username,
            'display_name':  u.first_name or u.username,
            'won':           0,
            'lost':          0,
            'skipped':       0,
            'matches_won':   0,
            'matches_lost':  0,
            'powerups_used': 0,
        }

    matches_qs = Match.objects.filter(
        Q(result='team1') | Q(result='team2')
    ).prefetch_related('selection_set__user', 'selection_set__selection')

    if upto_match_id is not None:
        try:
            cutoff = Match.objects.get(pk=upto_match_id)
            matches_qs = matches_qs.filter(datetime__lte=cutoff.datetime)
        except Match.DoesNotExist:
            pass  # fall through — compute full scores

    for mr in matches_qs:
        sel1    = []
        sel2    = []
        no_neg  = []

        for s in mr.selection_set.all():
            if s.selection == mr.team1:
                sel1.append(s.user.username)
            elif s.selection == mr.team2:
                sel2.append(s.user.username)
            if s.no_negative:
                no_neg.append(s.user.username)
            if s.hidden or s.fake or s.no_negative:
                if s.user.username in scores:
                    scores[s.user.username]['powerups_used'] += 1

        pickers = set(sel1 + sel2)
        for username in scores:
            if username not in pickers:
                scores[username]['skipped'] += 1

        if mr.result == 'team1':
            for u in sel1:
                if u in scores:
                    scores[u]['won']         += len(sel2) * mr.match_points
                    scores[u]['matches_won'] += 1
            for u in sel2:
                if u in scores:
                    if u not in no_neg:
                        scores[u]['lost']         += len(sel1) * mr.match_points
                    scores[u]['matches_lost'] += 1
        else:  # team2 won
            for u in sel2:
                if u in scores:
                    scores[u]['won']         += len(sel1) * mr.match_points
                    scores[u]['matches_won'] += 1
            for u in sel1:
                if u in scores:
                    if u not in no_neg:
                        scores[u]['lost']         += len(sel2) * mr.match_points
                    scores[u]['matches_lost'] += 1

    for username, data in scores.items():
        total = data['won'] - data['lost']
        if data['skipped'] > MAX_SKIPPED_ALLOWED:
            total = DISQUALIFICATION_SCORE
        data['total'] = total

    return scores


def _tie_key(entry):
    """The 4-tuple used to detect ties after primary sort."""
    return (entry['total'], entry['skipped'], entry['won'],
            entry['matches_won'], entry['powerups_used'])


def _head_to_head(username_a, username_b):
    """
    Return (a_wins, b_wins) from completed matches where A and B picked
    opposite sides.  Single query — safe to call only for 2-player ties.
    """
    from django.db.models import Q as _Q
    sels = (
        Selection.objects
        .filter(
            user__username__in=[username_a, username_b],
            match__result__in=['team1', 'team2'],
        )
        .select_related('match__team1', 'match__team2', 'selection', 'user')
    )
    by_match = {}
    for s in sels:
        by_match.setdefault(s.match_id, {})[s.user.username] = s

    a_wins = b_wins = 0
    for picks in by_match.values():
        if username_a not in picks or username_b not in picks:
            continue
        sa, sb = picks[username_a], picks[username_b]
        if sa.selection_id == sb.selection_id:
            continue  # same side — not a direct clash
        winner = sa.match.team1 if sa.match.result == 'team1' else sa.match.team2
        if sa.selection == winner:
            a_wins += 1
        else:
            b_wins += 1
    return a_wins, b_wins


def _build_ranked_list(scores):
    """
    Sort scores into a ranked list applying the full tiebreaker chain:
      Primary : highest total
      TB1     : fewest skipped
      TB2     : most points won (gross)
      TB3     : most matches won
      TB4     : fewest powerplays used
      TB5     : head-to-head (2-player ties only; 3+ keep TB1-4 order, sequential ranks)
      TB6     : joint winners (shared rank) — only when 2-player H2H is exactly equal
    """
    ranked = sorted(
        scores.values(),
        key=lambda x: (
            -x['total'],
             x['skipped'],
            -x['won'],
            -x['matches_won'],
             x['powerups_used'],
        ),
    )

    # shared_rank_indices: positions that share the rank of their predecessor
    # Only set for 2-player groups where H2H is exactly equal.
    # 3+ player groups keep sequential ranks (TB1-4 order stands).
    shared_rank_indices = set()

    i = 0
    while i < len(ranked):
        j = i + 1
        while j < len(ranked) and _tie_key(ranked[j]) == _tie_key(ranked[i]):
            j += 1
        if j - i == 2:
            a, b = ranked[i], ranked[i + 1]
            a_wins, b_wins = _head_to_head(a['username'], b['username'])
            if b_wins > a_wins:
                ranked[i], ranked[i + 1] = ranked[i + 1], ranked[i]
            if a_wins == b_wins:
                shared_rank_indices.add(i + 1)
        i = j

    # Assign ranks — competition / 1224 style
    # rank = 1-indexed position, so two players at rank 1 make the next rank 3.
    for i, entry in enumerate(ranked):
        if i == 0:
            entry['rank'] = 1
        elif i in shared_rank_indices:
            entry['rank'] = ranked[i - 1]['rank']
        else:
            entry['rank'] = i + 1

    return ranked


# ---------------------------------------------------------------------------
# Snapshot + cache helpers  (called from Celery tasks, not web requests)
# ---------------------------------------------------------------------------

def take_snapshot(match_id):
    """
    Compute the current full leaderboard, persist it as a LeaderboardSnapshot
    for the given match, refresh Redis cache, and fire rank-change notifications
    if the #1 player changed.

    Safe to call multiple times for the same match (update_or_create).
    """
    from apps.leaderboard.models import LeaderboardSnapshot

    try:
        match = Match.objects.get(pk=match_id)
    except Match.DoesNotExist:
        logger.error('take_snapshot: match %s not found', match_id)
        return

    scores = calculate_scores()
    ranked = _build_ranked_list(scores)

    snapshot_data = [
        {k: e[k] for k in (
            'rank', 'username', 'user_id', 'total',
            'won', 'lost', 'skipped', 'matches_won', 'matches_lost'
        )}
        for e in ranked
    ]

    # Detect rank-1 change by comparing against the previous match's snapshot.
    # Must be done before update_or_create so we get the true "before" state.
    prev_leader = None
    try:
        prev = (LeaderboardSnapshot.objects
                .filter(match__datetime__lt=match.datetime)
                .latest('match__datetime'))
        if prev.rankings:
            prev_leader = prev.rankings[0]['username']
    except LeaderboardSnapshot.DoesNotExist:
        pass

    _, created = LeaderboardSnapshot.objects.update_or_create(
        match=match,
        defaults={'rankings': snapshot_data},
    )

    # Refresh Redis cache (include streaks so live leaderboard is consistent)
    streaks = compute_streaks()
    ranked_with_streaks = [{**e, 'streak': streaks.get(e['username'], [])} for e in ranked]
    cache.set(CACHE_KEY_LEADERBOARD, ranked_with_streaks, timeout=CACHE_TTL)
    logger.info('take_snapshot: saved snapshot + cache refreshed for match %s', match_id)

    # Fire rank-change notification only on the FIRST snapshot for this match.
    # update_or_create returns created=False on retries/re-runs, preventing
    # duplicate notifications when take_snapshot is called multiple times for
    # the same match (e.g. admin re-runs backfill or Celery retries).
    new_leader = ranked[0]['username'] if ranked else None
    if created and new_leader and new_leader != prev_leader:
        from apps.notifications.tasks import notify_rank_change
        notify_rank_change.delay(new_leader, match_id, prev_leader)
        logger.info(
            'take_snapshot: rank-1 changed %s → %s, notifications queued',
            prev_leader, new_leader,
        )


def compute_streaks():
    """
    Return {username: ['W','L','S','N', ...]} for each active user.
    Each entry represents one of their last 5 completed matches (oldest → newest).
      W = picked the winner
      L = picked the loser
      S = skipped (no pick placed)
      N = no result / rain
    Cancelled matches are excluded — they don't count toward the 5.
    """
    recent_matches = list(
        Match.objects.filter(
            Q(result='team1') | Q(result='team2') | Q(result='NR')
        ).order_by('-datetime')[:5]
    )
    if not recent_matches:
        return {}

    # winner team pk per match (None = NR)
    winner_map = {}
    for m in recent_matches:
        if m.result == 'team1':
            winner_map[m.id] = m.team1_id
        elif m.result == 'team2':
            winner_map[m.id] = m.team2_id
        else:
            winner_map[m.id] = None

    # picks indexed by (match_id, username) → selected team pk
    picks = {}
    for s in (
        Selection.objects
        .filter(match__in=recent_matches)
        .select_related('user')
        .values('match_id', 'user__username', 'selection_id')
    ):
        picks[(s['match_id'], s['user__username'])] = s['selection_id']

    usernames = list(User.objects.filter(is_active=True).values_list('username', flat=True))

    streaks = {}
    for username in usernames:
        streak = []
        # recent_matches is desc (newest first) — matches display order
        for m in recent_matches:
            winner_team_id = winner_map[m.id]
            if winner_team_id is None:
                streak.append('N')
            else:
                pick = picks.get((m.id, username))
                if pick is None:
                    streak.append('S')
                elif pick == winner_team_id:
                    streak.append('W')
                else:
                    streak.append('L')
        streaks[username] = streak

    return streaks


def get_cached_leaderboard():
    """Return ranked leaderboard list from Redis. Recompute + cache on miss."""
    ranked = cache.get(CACHE_KEY_LEADERBOARD)
    if ranked is None:
        ranked = _build_ranked_list(calculate_scores())
        streaks = compute_streaks()
        for entry in ranked:
            entry['streak'] = streaks.get(entry['username'], [])
        cache.set(CACHE_KEY_LEADERBOARD, ranked, timeout=CACHE_TTL)
    return ranked


# ---------------------------------------------------------------------------
# Helper for history labels
# ---------------------------------------------------------------------------

def _abbreviate(team_name: str) -> str:
    """'Chennai Super Kings' → 'CSK'  |  'Mumbai' → 'MUM'"""
    words = team_name.split()
    if len(words) == 1:
        return team_name[:3].upper()
    return ''.join(w[0] for w in words).upper()


# ---------------------------------------------------------------------------
# API views
# ---------------------------------------------------------------------------

class LeaderboardView(APIView):
    """GET /api/v1/leaderboard/  → global leaderboard sorted by total score."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(get_cached_leaderboard())


class MyRankView(APIView):
    """GET /api/v1/leaderboard/me/  → current user's rank and stats."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        ranked = get_cached_leaderboard()
        for entry in ranked:
            if entry['username'] == request.user.username:
                return Response(entry)
        return Response({'error': 'User not found in leaderboard.'}, status=404)


class LeaderboardHistoryView(APIView):
    """
    GET /api/v1/leaderboard/history/
    Returns all snapshots ordered by match datetime, shaped for a line chart.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.leaderboard.models import LeaderboardSnapshot

        snapshots = (
            LeaderboardSnapshot.objects
            .select_related('match__team1', 'match__team2')
            .order_by('match__datetime')
        )

        result = []
        for i, snap in enumerate(snapshots, 1):
            m  = snap.match
            t1 = m.team1.name if m.team1 else '?'
            t2 = m.team2.name if m.team2 else '?'
            result.append({
                'match_id':     m.id,
                'match_number': i,
                'label':        f'M{i}: {_abbreviate(t1)} vs {_abbreviate(t2)}',
                'full_label':   f'{m.description or "Match"}: {t1} vs {t2}',
                'taken_at':     snap.taken_at.isoformat(),
                'rankings':     snap.rankings,
            })

        return Response(result)
