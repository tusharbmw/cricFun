from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('teams', '0013_tournament_external_id_length'),
    ]

    operations = [
        migrations.AddField(
            model_name='selection',
            name='fake_selection',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='fake_selections',
                to='teams.team',
            ),
        ),
        migrations.AddField(
            model_name='selection',
            name='fake_draw',
            field=models.BooleanField(default=False),
        ),
    ]
