from django.contrib import admin

from .models import LeaderboardSnapshot


@admin.register(LeaderboardSnapshot)
class LeaderboardSnapshotAdmin(admin.ModelAdmin):
    list_display    = ['match', 'taken_at']
    readonly_fields = ['match', 'taken_at', 'rankings']
    ordering        = ['match__datetime']
