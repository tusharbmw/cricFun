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
    from apps.matches.oddsapi import CACHE_KEY_CREDITS_REMAINING, CACHE_KEY_CREDITS_USED, CACHE_KEY_LAST_SYNC

    api_hits            = get_hits_status()
    settings            = SiteSettings.get()
    cricket_api_paused  = settings.cricket_api_paused
    football_api_paused = settings.football_api_paused

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

    from django.core.cache import cache as _cache
    football_calls_today = _cache.get('football_api_calls_today', 0)
    notifications_paused = settings.notifications_paused

    # Odds API info
    odds_credits_remaining = cache.get(CACHE_KEY_CREDITS_REMAINING)  # None if never run
    odds_credits_used = cache.get(CACHE_KEY_CREDITS_USED)
    odds_last_sync_raw = cache.get(CACHE_KEY_LAST_SYNC)
    if odds_last_sync_raw:
        try:
            odds_last_sync = datetime.fromisoformat(odds_last_sync_raw)
        except ValueError:
            odds_last_sync = None
    else:
        odds_last_sync = None

    # Next odds sync: crontab(hour='0,6,12,18', minute=30) UTC
    sync_hours = [0, 6, 12, 18]
    next_odds_sync = None
    for h in sync_hours:
        candidate = now.replace(hour=h, minute=30, second=0, microsecond=0)
        if candidate <= now:
            candidate += timedelta(days=1) if h == 18 else timedelta()
            if candidate <= now:
                continue
        if next_odds_sync is None or candidate < next_odds_sync:
            next_odds_sync = candidate
    if next_odds_sync is None:
        next_odds_sync = now.replace(hour=0, minute=30, second=0, microsecond=0) + timedelta(days=1)
    next_odds_sync_in = max(0, int((next_odds_sync - now).total_seconds()))

    return {
        'api_hits':               api_hits,
        'cricket_api_paused':     cricket_api_paused,
        'football_api_paused':    football_api_paused,
        'football_calls_today':   football_calls_today,
        'notifications_paused':   notifications_paused,
        'next_live_check':        next_live_check,
        'next_live_check_in':     next_live_check_in,
        'next_fetch':             next_fetch,
        'next_fetch_in_h':        next_fetch_in // 3600,
        'next_fetch_in_m':        (next_fetch_in % 3600) // 60,
        'odds_sync_paused':       settings.odds_sync_paused,
        'odds_credits_remaining': odds_credits_remaining,
        'odds_credits_used':      odds_credits_used,
        'odds_last_sync':         odds_last_sync,
        'odds_monthly_limit':     500,
        'next_odds_sync':         next_odds_sync,
        'next_odds_sync_in_h':    next_odds_sync_in // 3600,
        'next_odds_sync_in_m':    (next_odds_sync_in % 3600) // 60,
    }


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    fields = ['tournament_id', 'pick_window_days', 'cricket_api_paused', 'football_api_paused', 'notifications_paused', 'odds_sync_paused']
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
            path(
                'toggle-notifications-pause/',
                self.admin_site.admin_view(self.toggle_notifications_pause_view),
                name='sitesettings_toggle_notifications_pause',
            ),
            path(
                'toggle-football-api-pause/',
                self.admin_site.admin_view(self.toggle_football_api_pause_view),
                name='sitesettings_toggle_football_api_pause',
            ),
            path(
                'fetch-soccer-matches/',
                self.admin_site.admin_view(self.fetch_soccer_matches_view),
                name='sitesettings_fetch_soccer_matches',
            ),
            path(
                'sync-odds/',
                self.admin_site.admin_view(self.sync_odds_view),
                name='sitesettings_sync_odds',
            ),
            path(
                'toggle-odds-sync-pause/',
                self.admin_site.admin_view(self.toggle_odds_sync_pause_view),
                name='sitesettings_toggle_odds_sync_pause',
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
            ).select_related('tournament').order_by('datetime')
        )
        existing_ids = set(LeaderboardSnapshot.objects.values_list('match_id', flat=True))
        to_fill = [m for m in completed if m.id not in existing_ids]

        for match in to_fill:
            tournament    = match.tournament
            scores        = calculate_scores(upto_match_id=match.id, tournament=tournament)
            ranked        = _build_ranked_list(scores, tournament=tournament)
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

        django_cache.delete(CACHE_KEY_LEADERBOARD)

        messages.success(
            request,
            f'Backfilled {len(to_fill)} snapshot(s). Cache cleared.'
        )
        return redirect(self._settings_change_url(request))

    # ------------------------------------------------------------------
    # Recalculate leaderboard: force-regenerate ALL snapshots + refresh cache
    # ------------------------------------------------------------------

    def recalculate_leaderboard_view(self, request):
        if request.method != 'POST':
            return redirect(self._settings_change_url(request))
        from apps.leaderboard.tasks import recalculate_leaderboard
        recalculate_leaderboard.delay()
        messages.success(
            request,
            'Leaderboard recalculation started in background. Refresh in a minute to see updated snapshots.'
        )
        return redirect(self._settings_change_url(request))

    # ------------------------------------------------------------------
    # Toggle CricAPI pause
    # ------------------------------------------------------------------

    def toggle_api_pause_view(self, request):
        if request.method != 'POST':
            return redirect(self._settings_change_url(request))
        settings = SiteSettings.get()
        settings.cricket_api_paused = not settings.cricket_api_paused
        settings.save()
        state = 'PAUSED' if settings.cricket_api_paused else 'RESUMED'
        messages.success(request, f'Cricket API calls {state}.')
        return redirect(self._settings_change_url(request))

    def fetch_soccer_matches_view(self, request):
        if request.method != 'POST':
            return redirect(self._settings_change_url(request))
        from apps.matches.tasks import fetch_football_matches
        result = fetch_football_matches()
        messages.success(request, f'Fetch soccer matches: {result}')
        return redirect(self._settings_change_url(request))

    def toggle_football_api_pause_view(self, request):
        if request.method != 'POST':
            return redirect(self._settings_change_url(request))
        settings = SiteSettings.get()
        settings.football_api_paused = not settings.football_api_paused
        settings.save()
        state = 'PAUSED' if settings.football_api_paused else 'RESUMED'
        messages.success(request, f'Football API calls {state}.')
        return redirect(self._settings_change_url(request))

    def toggle_notifications_pause_view(self, request):
        if request.method != 'POST':
            return redirect(self._settings_change_url(request))
        settings = SiteSettings.get()
        settings.notifications_paused = not settings.notifications_paused
        settings.save()
        state = 'PAUSED' if settings.notifications_paused else 'RESUMED'
        messages.success(request, f'Notifications {state}.')
        return redirect(self._settings_change_url(request))

    def sync_odds_view(self, request):
        if request.method != 'POST':
            return redirect(self._settings_change_url(request))
        from apps.matches.oddsapi import fetch_and_store_odds
        try:
            result = fetch_and_store_odds()
            messages.success(request, f'Odds sync complete — updated: {result["updated"]}, skipped: {result["skipped"]}')
        except Exception as exc:
            messages.error(request, f'Odds sync failed: {exc}')
        return redirect(self._settings_change_url(request))

    def toggle_odds_sync_pause_view(self, request):
        if request.method != 'POST':
            return redirect(self._settings_change_url(request))
        settings = SiteSettings.get()
        settings.odds_sync_paused = not settings.odds_sync_paused
        settings.save()
        state = 'PAUSED' if settings.odds_sync_paused else 'RESUMED'
        messages.success(request, f'Odds auto-sync {state}.')
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
