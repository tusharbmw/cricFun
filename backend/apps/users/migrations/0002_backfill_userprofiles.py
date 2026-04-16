"""
Create UserProfile rows for all existing users.
Existing users (already playing) are approved by default.
"""
from django.db import migrations


def create_profiles(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    UserProfile = apps.get_model('users', 'UserProfile')
    existing_ids = set(UserProfile.objects.values_list('user_id', flat=True))
    profiles = [
        UserProfile(user_id=u.pk, approved=True)
        for u in User.objects.filter(is_active=True)
        if u.pk not in existing_ids
    ]
    UserProfile.objects.bulk_create(profiles)


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_add_userprofile'),
    ]

    operations = [
        migrations.RunPython(create_profiles, migrations.RunPython.noop),
    ]
