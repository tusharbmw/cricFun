from django.contrib import admin

from .models import Match, Selection, Team, Tournament


# ---------------------------------------------------------------------------
# Tournament enrollment inline (shown on Tournament page)
# ---------------------------------------------------------------------------

class TournamentEnrollmentInline(admin.TabularInline):
    from apps.users.models import TournamentEnrollment
    model = TournamentEnrollment
    extra = 1
    fields = ('user',)
    verbose_name = 'Enrolled user'
    verbose_name_plural = 'Enrolled users'


# ---------------------------------------------------------------------------
# Tournament
# ---------------------------------------------------------------------------

@admin.register(Tournament)
class TournamentAdmin(admin.ModelAdmin):
    list_display    = ['name', 'sport', 'season', 'state', 'is_active', 'external_id']
    list_filter     = ['sport', 'is_active']
    list_editable   = ['is_active']
    search_fields   = ['name', 'external_id']
    readonly_fields = ['state', 'created_at', 'updated_at']
    inlines         = [TournamentEnrollmentInline]
    fieldsets = (
        (None, {'fields': ('name', 'sport', 'season', 'external_id', 'is_active')}),
        ('Auto-managed', {
            'fields': ('state', 'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )


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
    fields = ['user', 'selection', 'draw', 'hidden', 'fake', 'no_negative']
    readonly_fields = ['user', 'selection']


# ---------------------------------------------------------------------------
# Match
# ---------------------------------------------------------------------------

@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display    = ['__str__', 'result', 'tournament', 'datetime', 'match_points', 'venue', 'match_id']
    list_filter     = ['result', 'tournament']
    search_fields   = ['description', 'team1__name', 'team2__name']
    readonly_fields = ['created_at', 'updated_at']
    inlines         = [SelectionInline]

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if change and 'result' in form.changed_data and obj.result in ('team1', 'team2', 'NR', 'draw'):
            from apps.matches.tasks import finalize_match_results
            finalize_match_results.delay(obj.id)


# ---------------------------------------------------------------------------
# Selection standalone list
# ---------------------------------------------------------------------------

@admin.register(Selection)
class SelectionAdmin(admin.ModelAdmin):
    list_display    = ['user', 'match', 'selection', 'draw', 'hidden', 'fake', 'no_negative', 'created_at']
    list_filter     = ['hidden', 'fake', 'no_negative', 'draw', 'match__result']
    search_fields   = ['user__username', 'match__description']
    readonly_fields = ['created_at', 'updated_at']
