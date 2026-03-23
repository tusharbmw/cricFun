from datetime import datetime, timezone, timedelta

from django.contrib import admin, messages
from django.core.cache import cache
from django.db import transaction
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import path

from .models import SiteSettings


def _get_panel_context():
    """Build the context dict injected into the SiteSettings admin views."""
    from apps.core.cricapi import get_hits_status
    from apps.matches.tasks import CACHE_KEY_NEXT_CHECK

    api_hits   = get_hits_status()
    api_paused = SiteSettings.get().api_paused

    now = datetime.now(timezone.utc)

    # Next live-score API call — stored in Redis by update_live_scores
    next_check_ts = cache.get(CACHE_KEY_NEXT_CHECK)
    if next_check_ts:
        next_live_check = datetime.fromtimestamp(next_check_ts, tz=timezone.utc)
        next_live_check_in = max(0, int(next_check_ts - now.timestamp()))
    else:
        next_live_check = None
        next_live_check_in = None  # no live matches → gate not set

    # Next fetch_upcoming_matches: crontab(hour=6, minute=0) UTC
    next_fetch = now.replace(hour=6, minute=0, second=0, microsecond=0)
    if next_fetch <= now:
        next_fetch += timedelta(days=1)
    next_fetch_in = int((next_fetch - now).total_seconds())

    return {
        'api_hits': api_hits,
        'api_paused': api_paused,
        'next_live_check': next_live_check,
        'next_live_check_in': next_live_check_in,
        'next_fetch': next_fetch,
        'next_fetch_in_h': next_fetch_in // 3600,
        'next_fetch_in_m': (next_fetch_in % 3600) // 60,
    }


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    fields = ['tournament_id', 'pick_window_days', 'api_paused']
    change_form_template = 'admin/core/sitesettings/change_form.html'

    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        """Skip the list page — go straight to the singleton change form."""
        obj = SiteSettings.get()
        return redirect(f'{request.path}{obj.pk}/change/')

    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = extra_context or {}
        extra_context.update(_get_panel_context())
        return super().change_view(request, object_id, form_url, extra_context)

    # ------------------------------------------------------------------
    # Custom admin URLs for management actions
    # ------------------------------------------------------------------

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                'fill-matches/',
                self.admin_site.admin_view(self.fill_matches_view),
                name='sitesettings_fill_matches',
            ),
            path(
                'status-check/',
                self.admin_site.admin_view(self.status_check_view),
                name='sitesettings_status_check',
            ),
            path(
                'reset-season/',
                self.admin_site.admin_view(self.reset_season_view),
                name='sitesettings_reset_season',
            ),
            path(
                'backfill-snapshots/',
                self.admin_site.admin_view(self.backfill_snapshots_view),
                name='sitesettings_backfill_snapshots',
            ),
            path(
                'recalculate-leaderboard/',
                self.admin_site.admin_view(self.recalculate_leaderboard_view),
                name='sitesettings_recalculate_leaderboard',
            ),
            path(
                'toggle-api-pause/',
                self.admin_site.admin_view(self.toggle_api_pause_view),
                name='sitesettings_toggle_api_pause',
            ),
        ]
        return custom + urls

    def _settings_change_url(self, request):
        """Return the URL of the singleton change page."""
        base = request.path.rstrip('/').rsplit('/', 1)[0]
        return f'{base}/1/change/'

    # ------------------------------------------------------------------
    # Fetch upcoming matches from CricAPI
    # ------------------------------------------------------------------

    def fill_matches_view(self, request):
        if request.method != 'POST':
            return redirect(self._settings_change_url(request))
        from apps.matches.tasks import fetch_upcoming_matches
        from apps.core.cricapi import CACHE_KEY_SERIES
        cache.delete(CACHE_KEY_SERIES)
        result = fetch_upcoming_matches()
        messages.success(request, f'Fetch upcoming matches: {result}')
        return redirect(self._settings_change_url(request))

    # ------------------------------------------------------------------
    # Force match status check (TBD→IP + live score poll)
    # ------------------------------------------------------------------

    def status_check_view(self, request):
        if request.method != 'POST':
            return redirect(self._settings_change_url(request))
        from apps.matches.tasks import update_match_statuses, update_live_scores, CACHE_KEY_NEXT_CHECK
        from apps.core.cricapi import CACHE_KEY_MATCH_PFX
        from teams.models import Match
        from django.db.models import Q
        live_ids = Match.objects.filter(Q(result='IP') | Q(result='TBD')).values_list('match_id', flat=True)
        cache.delete_many([f'{CACHE_KEY_MATCH_PFX}{mid}' for mid in live_ids])
        cache.delete(CACHE_KEY_NEXT_CHECK)
        r1 = update_match_statuses()
        r2 = update_live_scores()
        messages.success(request, f'Status check — {r1} | {r2}')
        return redirect(self._settings_change_url(request))

    # ------------------------------------------------------------------
    # Reset season: delete all matches + selections, keep user accounts
    # ------------------------------------------------------------------

    def backfill_snapshots_view(self, request):
        if request.method != 'POST':
            return redirect(self._settings_change_url(request))
        from django.db.models import Q
        from teams.models import Match
        from apps.leaderboard.models import LeaderboardSnapshot
        from apps.leaderboard.views import (
            CACHE_KEY_LEADERBOARD, CACHE_TTL, _build_ranked_list, calculate_scores,
        )
        from django.core.cache import cache as django_cache

        completed = list(
            Match.objects.filter(
                Q(result='team1') | Q(result='team2') | Q(result='NR')
            ).order_by('datetime')
        )
        existing_ids = set(LeaderboardSnapshot.objects.values_list('match_id', flat=True))
        to_fill = [m for m in completed if m.id not in existing_ids]

        for match in to_fill:
            scores        = calculate_scores(upto_match_id=match.id)
            ranked        = _build_ranked_list(scores)
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

        # Refresh Redis cache
        final = _build_ranked_list(calculate_scores())
        django_cache.set(CACHE_KEY_LEADERBOARD, final, timeout=CACHE_TTL)

        messages.success(
            request,
            f'Backfilled {len(to_fill)} snapshot(s). Redis cache refreshed.'
        )
        return redirect(self._settings_change_url(request))

    # ------------------------------------------------------------------
    # Recalculate leaderboard: force-regenerate ALL snapshots + refresh cache
    # ------------------------------------------------------------------

    def recalculate_leaderboard_view(self, request):
        if request.method != 'POST':
            return redirect(self._settings_change_url(request))
        from django.db.models import Q
        from teams.models import Match
        from apps.leaderboard.models import LeaderboardSnapshot
        from apps.leaderboard.views import (
            CACHE_KEY_LEADERBOARD, CACHE_TTL, _build_ranked_list, calculate_scores,
        )
        from django.core.cache import cache as django_cache

        completed = list(
            Match.objects.filter(
                Q(result='team1') | Q(result='team2') | Q(result='NR')
            ).order_by('datetime')
        )

        # Force-regenerate every snapshot regardless of whether it exists
        for match in completed:
            scores        = calculate_scores(upto_match_id=match.id)
            ranked        = _build_ranked_list(scores)
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

        # Refresh Redis cache with the full current standings
        final = _build_ranked_list(calculate_scores())
        django_cache.set(CACHE_KEY_LEADERBOARD, final, timeout=CACHE_TTL)

        messages.success(
            request,
            f'Recalculated {len(completed)} snapshot(s) from scratch. Redis cache refreshed.'
        )
        return redirect(self._settings_change_url(request))

    # ------------------------------------------------------------------
    # Toggle CricAPI pause
    # ------------------------------------------------------------------

    def toggle_api_pause_view(self, request):
        if request.method != 'POST':
            return redirect(self._settings_change_url(request))
        settings = SiteSettings.get()
        settings.api_paused = not settings.api_paused
        settings.save()
        state = 'PAUSED' if settings.api_paused else 'RESUMED'
        messages.success(request, f'CricAPI calls {state}.')
        return redirect(self._settings_change_url(request))

    # ------------------------------------------------------------------
    # Reset season: delete all matches + selections, keep user accounts
    # ------------------------------------------------------------------

    def reset_season_view(self, request):
        from teams.models import Match, Selection
        if request.method == 'POST' and request.POST.get('confirm') == 'yes':
            with transaction.atomic():
                sel_count   = Selection.objects.count()
                match_count = Match.objects.count()
                Selection.objects.all().delete()
                Match.objects.all().delete()
            messages.success(
                request,
                f'Season reset: {match_count} matches and {sel_count} selections deleted. '
                f'User accounts preserved.',
            )
            return redirect(self._settings_change_url(request))

        context = {
            **self.admin_site.each_context(request),
            'title':           'Reset Season — Confirmation Required',
            'match_count':     Match.objects.count(),
            'selection_count': Selection.objects.count(),
            'opts':            self.model._meta,
        }
        return TemplateResponse(
            request,
            'admin/core/sitesettings/reset_season_confirm.html',
            context,
        )
