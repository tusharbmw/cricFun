from django.db import models


class SiteSettings(models.Model):
    """
    Singleton table (always exactly one row) for runtime-configurable settings.
    Use SiteSettings.get() everywhere instead of direct DB queries.
    """
    pick_window_days = models.PositiveSmallIntegerField(
        default=5,
        help_text='How many days before a match opens for picks.',
    )
    tournament_id = models.CharField(
        max_length=100,
        blank=True,
        default='',
        help_text='CricAPI tournament/series ID (replaces CRIC_TOURNAMENT_ID env var).',
    )
    cricket_api_paused = models.BooleanField(
        default=False,
        help_text='Pause all CricAPI calls (live score polling + schedule fetch).',
    )
    football_api_paused = models.BooleanField(
        default=False,
        help_text='Pause all football-data.org calls (score sync + schedule fetch).',
    )
    notifications_paused = models.BooleanField(
        default=False,
        help_text='Silence all push and in-app notifications. Safe to enable during deployments or testing.',
    )
    odds_sync_paused = models.BooleanField(
        default=False,
        help_text='Pause automatic odds sync from The Odds API (runs every 6 hours).',
    )

    class Meta:
        verbose_name = 'Site Settings'
        verbose_name_plural = 'Site Settings'

    def __str__(self):
        return 'Site Settings'

    def save(self, *args, **kwargs):
        # Enforce singleton — always reuse pk=1
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
