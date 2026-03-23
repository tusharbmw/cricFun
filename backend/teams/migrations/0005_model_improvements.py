"""
Model improvements:
- Add created_at, updated_at timestamps to Match and Selection
- Add Meta ordering, unique_together for Selection
- Fix null/blank usage (string "True" -> bool True)
- Add db_index to Match.result and Match.datetime
- Add unique constraint to Match.match_id
- Rename ForeignKey related_names (team1/team2 -> home_matches/away_matches)
"""

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('teams', '0004_rename_tournaments_match_tournament_match_match_id_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Add timestamps to Match (columns already exist in Oracle — state-only)
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name='match',
                    name='created_at',
                    field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
                    preserve_default=False,
                ),
                migrations.AddField(
                    model_name='match',
                    name='updated_at',
                    field=models.DateTimeField(auto_now=True),
                ),
            ],
            database_operations=[],
        ),
        # Add timestamps to Selection (columns already exist in Oracle — state-only)
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name='selection',
                    name='created_at',
                    field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
                    preserve_default=False,
                ),
                migrations.AddField(
                    model_name='selection',
                    name='updated_at',
                    field=models.DateTimeField(auto_now=True),
                ),
            ],
            database_operations=[],
        ),
        # Fix null/blank on Team fields (string "True" -> bool True was a Python bug;
        # Oracle already has these as nullable, so skip DB ALTER — state-only update)
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AlterField(
                    model_name='team',
                    name='description',
                    field=models.TextField(blank=True, null=True),
                ),
                migrations.AlterField(
                    model_name='team',
                    name='location',
                    field=models.CharField(blank=True, max_length=40, null=True),
                ),
                migrations.AlterField(
                    model_name='team',
                    name='logo',
                    field=models.ImageField(blank=True, null=True, upload_to=''),
                ),
                migrations.AlterField(
                    model_name='team',
                    name='logo_url',
                    field=models.CharField(blank=True, max_length=100, null=True),
                ),
            ],
            database_operations=[],
        ),
        # Fix Match ForeignKey related_names — related_name is Python-only, null stays the same;
        # Oracle rejects ALTER when nullability doesn't change, so skip DB operation.
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AlterField(
                    model_name='match',
                    name='team1',
                    field=models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='home_matches',
                        to='teams.team',
                    ),
                ),
                migrations.AlterField(
                    model_name='match',
                    name='team2',
                    field=models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='away_matches',
                        to='teams.team',
                    ),
                ),
            ],
            database_operations=[],
        ),
        # Add db_index to Match.result and Match.datetime
        migrations.AlterField(
            model_name='match',
            name='result',
            field=models.CharField(
                choices=[
                    ('NR', 'No Result'), ('team1', 'Team 1 Won'), ('team2', 'Team 2 Won'),
                    ('IP', 'In Progress'), ('TBD', 'TBD'), ('TOSS', 'Toss'), ('DLD', 'Delayed'),
                ],
                db_index=True,
                default='TBD',
                max_length=10,
            ),
        ),
        migrations.AlterField(
            model_name='match',
            name='datetime',
            field=models.DateTimeField(db_index=True),
        ),
        # Fix Match.match_id unique constraint — column already exists as nullable,
        # so only apply the unique constraint in the DB (state update handles the rest).
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AlterField(
                    model_name='match',
                    name='match_id',
                    field=models.CharField(blank=True, max_length=50, null=True, unique=True),
                ),
            ],
            database_operations=[
                migrations.RunSQL(
                    sql='CREATE UNIQUE INDEX teams_match_match_id_ux ON teams_match (match_id)',
                    reverse_sql='DROP INDEX teams_match_match_id_ux',
                ),
            ],
        ),
        # Fix Selection ForeignKeys (remove null on user, cascade deletes)
        migrations.AlterField(
            model_name='selection',
            name='user',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name='selection',
            name='match',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                to='teams.match',
            ),
        ),
        # Add unique_together for Selection (one pick per user per match)
        migrations.AlterUniqueTogether(
            name='selection',
            unique_together={('user', 'match')},
        ),
        # Meta ordering
        migrations.AlterModelOptions(
            name='team',
            options={'ordering': ['name']},
        ),
        migrations.AlterModelOptions(
            name='match',
            options={'ordering': ['datetime']},
        ),
        migrations.AlterModelOptions(
            name='selection',
            options={'ordering': ['-created_at']},
        ),
    ]
