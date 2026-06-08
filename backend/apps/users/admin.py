from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

from .models import TournamentEnrollment, UserProfile


class TournamentEnrollmentInline(admin.TabularInline):
    model = TournamentEnrollment
    extra = 1
    fields = ('tournament',)
    verbose_name = 'Tournament enrollment'
    verbose_name_plural = 'Tournament enrollments'


class UserAdmin(BaseUserAdmin):
    inlines = (TournamentEnrollmentInline,)
    list_display = ('username', 'email', 'first_name', 'enrolled_in', 'date_joined', 'is_staff')
    list_filter = ('is_staff', 'is_active')

    @admin.display(description='Enrolled in')
    def enrolled_in(self, obj):
        names = list(
            TournamentEnrollment.objects
            .filter(user=obj)
            .values_list('tournament__name', flat=True)
        )
        return ', '.join(names) if names else '—'


admin.site.unregister(User)
admin.site.register(User, UserAdmin)
