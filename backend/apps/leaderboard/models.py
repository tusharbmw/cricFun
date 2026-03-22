from django.db import models

from teams.models import Match


class LeaderboardSnapshot(models.Model):
    """
    Stores the full ranked leaderboard state after each completed match.
    Enables historical rank-progression graphs and avoids on-the-fly recalculation.
    """
    match    = models.OneToOneField(
        Match,
        on_delete=models.CASCADE,
        related_name='leaderboard_snapshot',
    )
    taken_at = models.DateTimeField(auto_now_add=True)
    # rankings: ordered list (rank 1 first) of
    # {rank, username, user_id, total, won, lost, skipped, matches_won, matches_lost}
    rankings = models.JSONField()

    class Meta:
        ordering = ['match__datetime']

    def __str__(self):
        return f'Snapshot after {self.match} ({self.taken_at:%Y-%m-%d})'
