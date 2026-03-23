from django.contrib import admin

from .models import Notification, PushSubscription


@admin.register(PushSubscription)
class PushSubscriptionAdmin(admin.ModelAdmin):
    list_display  = ['user', 'created_at']
    list_filter   = ['user']
    ordering      = ['-created_at']
    readonly_fields = ['user', 'endpoint', 'p256dh', 'auth', 'created_at']


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display  = ['user', 'type', 'message', 'is_read', 'created_at']
    list_filter   = ['type', 'is_read']
    search_fields = ['user__username', 'message']
    ordering      = ['-created_at']
    readonly_fields = ['user', 'type', 'message', 'meta', 'created_at']
