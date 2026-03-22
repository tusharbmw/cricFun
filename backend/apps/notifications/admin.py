from django.contrib import admin

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display  = ['user', 'type', 'message', 'is_read', 'created_at']
    list_filter   = ['type', 'is_read']
    search_fields = ['user__username', 'message']
    ordering      = ['-created_at']
    readonly_fields = ['user', 'type', 'message', 'meta', 'created_at']
