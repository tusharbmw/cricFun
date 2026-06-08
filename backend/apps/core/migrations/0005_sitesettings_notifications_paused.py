from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_sitesettings_api_paused_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='sitesettings',
            name='notifications_paused',
            field=models.BooleanField(
                default=False,
                help_text='Silence all push and in-app notifications. Safe to enable during deployments or testing.',
            ),
        ),
    ]
