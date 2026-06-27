from celery import shared_task


@shared_task
def recalculate_leaderboard():
    from django.db.models import Q
    from django.core.cache import cache

    from teams.models import Match
    from apps.leaderboard.models import LeaderboardSnapshot
    from apps.leaderboard.views import (
        CACHE_KEY_LEADERBOARD, _build_ranked_list, calculate_scores,
    )

    completed = list(
        Match.objects.filter(
            Q(result='team1') | Q(result='team2') | Q(result='draw') | Q(result='NR')
        ).select_related('tournament').order_by('datetime')
    )

    for match in completed:
        tournament = match.tournament
        scores = calculate_scores(upto_match_id=match.id, tournament=tournament)
        ranked = _build_ranked_list(scores, tournament=tournament)
        snapshot_data = [
            {k: e[k] for k in (
                'rank', 'username', 'user_id', 'total',
                'won', 'lost', 'skipped', 'matches_won', 'matches_lost'
            )}
            for e in ranked
        ]
        LeaderboardSnapshot.objects.update_or_create(
            match=match, defaults={'rankings': snapshot_data}
        )

    cache.delete(CACHE_KEY_LEADERBOARD)
    return f'Recalculated {len(completed)} snapshot(s). Cache cleared.'
