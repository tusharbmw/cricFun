from django import forms
from django.contrib import admin, messages
from django.contrib.auth.models import User
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import path, reverse

from .models import Notification, PushSubscription


# ── Send notification form ─────────────────────────────────────────────────

class SendNotificationForm(forms.Form):
    RECIPIENT_CHOICES = [
        ('all',       'All active users'),
        ('push_only', 'Users with push notifications enabled'),
        ('specific',  'Specific users'),
    ]
    recipients = forms.ChoiceField(
        choices=RECIPIENT_CHOICES,
        widget=forms.RadioSelect,
        initial='all',
    )
    users = forms.ModelMultipleChoiceField(
        queryset=User.objects.filter(is_active=True).order_by('username'),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text='Only used when "Specific users" is selected.',
    )
    title = forms.CharField(max_length=100)
    message = forms.CharField(max_length=255, widget=forms.Textarea(attrs={'rows': 3}))
    url = forms.CharField(
        max_length=200,
        initial='/',
        required=False,
        help_text='URL to open when notification is clicked (e.g. /standings). Leave blank for home.',
    )

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('recipients') == 'specific' and not cleaned.get('users'):
            raise forms.ValidationError('Please select at least one user.')
        return cleaned


# ── PushSubscription admin ─────────────────────────────────────────────────

@admin.register(PushSubscription)
class PushSubscriptionAdmin(admin.ModelAdmin):
    list_display    = ['user', 'user_email', 'created_at']
    list_filter     = ['created_at']
    search_fields   = ['user__username', 'user__email']
    ordering        = ['-created_at']
    readonly_fields = ['user', 'endpoint', 'p256dh', 'auth', 'created_at']

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'Email'
    user_email.admin_order_field = 'user__email'


# ── Notification admin ─────────────────────────────────────────────────────

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display         = ['user', 'type', 'message', 'is_read', 'created_at']
    list_filter          = ['type', 'is_read']
    search_fields        = ['user__username', 'message']
    ordering             = ['-created_at']
    readonly_fields      = ['user', 'type', 'message', 'meta', 'created_at']
    change_list_template = 'admin/notifications/notification/change_list.html'

    def get_urls(self):
        urls = super().get_urls()
        extra = [
            path('send/', self.admin_site.admin_view(self.send_notification_view), name='notification_send'),
        ]
        return extra + urls

    def send_notification_view(self, request):
        from .tasks import send_custom_notification

        if request.method == 'POST':
            form = SendNotificationForm(request.POST)
            if form.is_valid():
                recipients = form.cleaned_data['recipients']
                title      = form.cleaned_data['title']
                message    = form.cleaned_data['message']
                url        = form.cleaned_data.get('url') or '/'

                if recipients == 'all':
                    user_ids = list(User.objects.filter(is_active=True).values_list('id', flat=True))
                elif recipients == 'push_only':
                    user_ids = list(
                        PushSubscription.objects.values_list('user_id', flat=True).distinct()
                    )
                else:
                    user_ids = [u.id for u in form.cleaned_data['users']]

                send_custom_notification.delay(title, message, url, user_ids)
                messages.success(request, f'Notification queued for {len(user_ids)} user(s).')
                return HttpResponseRedirect(reverse('admin:notification_send'))
        else:
            form = SendNotificationForm()

        push_count   = PushSubscription.objects.values('user').distinct().count()
        active_count = User.objects.filter(is_active=True).count()

        context = {
            **self.admin_site.each_context(request),
            'title':        'Send Notification',
            'form':         form,
            'push_count':   push_count,
            'active_count': active_count,
            'opts':         self.model._meta,
        }
        return render(request, 'admin/notifications/notification/send_notification.html', context)
