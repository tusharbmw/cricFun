"""
Management command to backfill LeaderboardSnapshot for all completed matches
that don't already have one. Safe to re-run; use --force to regenerate all.

Usage:
    python manage.py backfill_snapshots
    python manage.py backfill_snapshots --force
"""
from django.core.management.base import BaseCommand
from django.db.models import Q

from teams.models import Match


class Command(BaseCommand):
    help = 'Backfill LeaderboardSnapshot for completed matches without one.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Re-generate snapshots even for matches that already have one.',
        )

    def handle(self, *args, **options):
        from apps.leaderboard.models import LeaderboardSnapshot
        from apps.leaderboard.views import (
            CACHE_KEY_LEADERBOARD, CACHE_TTL,
            _build_ranked_list, calculate_scores, get_cached_leaderboard,
        )
        from django.core.cache import cache

        completed = list(
            Match.objects.filter(
                Q(result='team1') | Q(result='team2') | Q(result='NR')
            ).order_by('datetime')
        )

        if not options['force']:
            existing_ids = set(
                LeaderboardSnapshot.objects.values_list('match_id', flat=True)
            )
            to_fill = [m for m in completed if m.id not in existing_ids]
        else:
            to_fill = completed

        total = len(to_fill)
        if total == 0:
            self.stdout.write('Nothing to backfill — all snapshots already exist.')
            return

        self.stdout.write(f'Backfilling {total} match snapshot(s)...')

        for i, match in enumerate(to_fill, 1):
            scores = calculate_scores(upto_match_id=match.id)
            ranked = _build_ranked_list(scores)
            snapshot_data = [
                {k: e[k] for k in (
                    'rank', 'username', 'user_id', 'total',
                    'won', 'lost', 'skipped', 'matches_won', 'matches_lost'
                )}
                for e in ranked
            ]
            LeaderboardSnapshot.objects.update_or_create(
                match=match,
                defaults={'rankings': snapshot_data},
            )
            self.stdout.write(f'  [{i}/{total}] {match}')

        # Refresh Redis cache with the final (current) state
        final = _build_ranked_list(calculate_scores())
        cache.set(CACHE_KEY_LEADERBOARD, final, timeout=CACHE_TTL)

        self.stdout.write(self.style.SUCCESS(
            f'Done. {total} snapshot(s) created/updated. Redis cache refreshed.'
        ))
