from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_sitesettings_notifications_paused'),
    ]

    operations = [
        migrations.RenameField(
            model_name='sitesettings',
            old_name='api_paused',
            new_name='cricket_api_paused',
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='football_api_paused',
            field=models.BooleanField(
                default=False,
                help_text='Pause all football-data.org calls (score sync + schedule fetch).',
            ),
        ),
    ]
