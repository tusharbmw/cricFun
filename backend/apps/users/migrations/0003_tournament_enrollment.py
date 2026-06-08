import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_backfill_userprofiles'),
        ('teams', '0012_tournament_match_updates'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Drop the approved field — replaced by TournamentEnrollment
        migrations.RemoveField(
            model_name='userprofile',
            name='approved',
        ),

        # Create the per-tournament enrollment join table
        migrations.CreateModel(
            name='TournamentEnrollment',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='tournament_enrollments',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('tournament', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='enrollments',
                    to='teams.tournament',
                )),
            ],
            options={
                'ordering': ['tournament__name', 'user__username'],
            },
        ),
        migrations.AlterUniqueTogether(
            name='tournamentenrollment',
            unique_together={('user', 'tournament')},
        ),
    ]
