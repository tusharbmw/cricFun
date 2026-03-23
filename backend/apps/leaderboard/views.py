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
            'user_id':      u.id,
            'username':     u.username,
            'display_name': u.first_name or u.username,
            'won':          0,
            'lost':         0,
            'skipped':      0,
            'matches_won':  0,
            'matches_lost': 0,
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


def _build_ranked_list(scores):
    """Sort scores dict into a ranked list (rank 1 = highest total)."""
    ranked = sorted(scores.values(), key=lambda x: x['total'], reverse=True)
    for i, entry in enumerate(ranked, 1):
        entry['rank'] = i
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

    # Detect rank-1 change before saving (compare against previous snapshot)
    prev_leader = None
    try:
        prev = (LeaderboardSnapshot.objects
                .filter(match__datetime__lt=match.datetime)
                .latest('match__datetime'))
        if prev.rankings:
            prev_leader = prev.rankings[0]['username']
    except LeaderboardSnapshot.DoesNotExist:
        pass

    LeaderboardSnapshot.objects.update_or_create(
        match=match,
        defaults={'rankings': snapshot_data},
    )

    # Refresh Redis cache
    cache.set(CACHE_KEY_LEADERBOARD, ranked, timeout=CACHE_TTL)
    logger.info('take_snapshot: saved snapshot + cache refreshed for match %s', match_id)

    # Fire rank-change notification if #1 changed
    new_leader = ranked[0]['username'] if ranked else None
    if new_leader and new_leader != prev_leader:
        from apps.notifications.tasks import notify_rank_change
        notify_rank_change.delay(new_leader, match_id, prev_leader)
        logger.info(
            'take_snapshot: rank-1 changed %s → %s, notifications queued',
            prev_leader, new_leader,
        )


def get_cached_leaderboard():
    """Return ranked leaderboard list from Redis. Recompute + cache on miss."""
    ranked = cache.get(CACHE_KEY_LEADERBOARD)
    if ranked is None:
        ranked = _build_ranked_list(calculate_scores())
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
