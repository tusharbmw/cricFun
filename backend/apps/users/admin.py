from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

from .models import UserProfile


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'
    fields = ('approved',)


class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)
    list_display = ('username', 'email', 'first_name', 'is_approved', 'date_joined', 'is_staff')
    list_filter = ('userprofile__approved', 'is_staff', 'is_active')
    actions = ('approve_users', 'unapprove_users')

    @admin.display(boolean=True, description='Approved')
    def is_approved(self, obj):
        try:
            return obj.userprofile.approved
        except UserProfile.DoesNotExist:
            return False

    @admin.action(description='Approve selected users')
    def approve_users(self, request, queryset):
        for user in queryset:
            UserProfile.objects.update_or_create(user=user, defaults={'approved': True})
        self.message_user(request, f'{queryset.count()} user(s) approved.')

    @admin.action(description='Revoke approval for selected users')
    def unapprove_users(self, request, queryset):
        for user in queryset:
            UserProfile.objects.update_or_create(user=user, defaults={'approved': False})
        self.message_user(request, f'{queryset.count()} user(s) unapproved.')


admin.site.unregister(User)
admin.site.register(User, UserAdmin)
