from django.contrib import admin

from .models import Team, Match, Selection


# ---------------------------------------------------------------------------
# Team
# ---------------------------------------------------------------------------

@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display  = ['name', 'location', 'description']
    search_fields = ['name']


# ---------------------------------------------------------------------------
# Selection inline (shown inside Match)
# ---------------------------------------------------------------------------

class SelectionInline(admin.TabularInline):
    model = Selection
    extra = 0
    fields = ['user', 'selection', 'hidden', 'fake', 'no_negative']
    readonly_fields = ['user', 'selection']


# ---------------------------------------------------------------------------
# Match — main admin with management panel
# ---------------------------------------------------------------------------

@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display    = ['__str__', 'result', 'datetime', 'match_points', 'venue', 'tournament']
    list_filter     = ['result', 'tournament']
    search_fields   = ['description', 'team1__name', 'team2__name']
    readonly_fields = ['created_at', 'updated_at']
    inlines         = [SelectionInline]

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        # When admin manually sets a final result, trigger the same pipeline
        # that update_live_scores triggers: pick processing + leaderboard snapshot.
        if change and 'result' in form.changed_data and obj.result in ('team1', 'team2', 'NR'):
            from apps.matches.tasks import finalize_match_results
            finalize_match_results.delay(obj.id)


# ---------------------------------------------------------------------------
# Selection standalone list
# ---------------------------------------------------------------------------

@admin.register(Selection)
class SelectionAdmin(admin.ModelAdmin):
    list_display    = ['user', 'match', 'selection', 'hidden', 'fake', 'no_negative', 'created_at']
    list_filter     = ['hidden', 'fake', 'no_negative', 'match__result']
    search_fields   = ['user__username', 'match__description']
    readonly_fields = ['created_at', 'updated_at']
