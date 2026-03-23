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
    api_paused = models.BooleanField(
        default=False,
        help_text='Pause all CricAPI calls (live score polling + schedule fetch). Use when API has issues.',
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
