import django.db.models.deletion
from django.db import migrations, models


def create_tournaments_and_backfill(apps, schema_editor):
    Tournament = apps.get_model('teams', 'Tournament')
    Match = apps.get_model('teams', 'Match')

    # Create one Tournament record per unique existing string value
    tournament_map = {}
    for name in Match.objects.values_list('tournament_str', flat=True).distinct():
        if name:
            t, _ = Tournament.objects.get_or_create(
                name=name,
                defaults={'sport': 'cricket', 'season': ''},
            )
            tournament_map[name] = t.pk

    # Backfill the FK on every match
    for match in Match.objects.all():
        pk = tournament_map.get(match.tournament_str)
        if pk:
            match.tournament_id = pk
            match.save(update_fields=['tournament_id'])


def reverse_backfill(apps, schema_editor):
    Match = apps.get_model('teams', 'Match')
    Tournament = apps.get_model('teams', 'Tournament')
    for match in Match.objects.select_related('tournament').all():
        if match.tournament_id:
            try:
                t = Tournament.objects.get(pk=match.tournament_id)
                match.tournament_str = t.name
                match.save(update_fields=['tournament_str'])
            except Tournament.DoesNotExist:
                pass


class Migration(migrations.Migration):

    dependencies = [
        ('teams', '0011_backfill_playoff'),
    ]

    operations = [
        # ── 1. Create Tournament model ──────────────────────────────────────
        migrations.CreateModel(
            name='Tournament',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('sport', models.CharField(
                    choices=[('cricket', 'Cricket'), ('soccer', 'Soccer')],
                    default='cricket',
                    max_length=20,
                )),
                ('season', models.CharField(blank=True, default='', max_length=50)),
                ('external_id', models.CharField(blank=True, max_length=20, null=True)),
                ('is_active', models.BooleanField(default=False)),
                ('state', models.CharField(blank=True, max_length=100, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={'ordering': ['name']},
        ),

        # ── 2. Rename old CharField so we can read it during data migration ─
        migrations.RenameField(
            model_name='match',
            old_name='tournament',
            new_name='tournament_str',
        ),

        # ── 3. Add new FK (nullable so existing rows don't violate constraints)
        migrations.AddField(
            model_name='match',
            name='tournament',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='matches',
                to='teams.tournament',
            ),
        ),

        # ── 4. Data migration: create Tournament rows + backfill FK ─────────
        migrations.RunPython(create_tournaments_and_backfill, reverse_code=reverse_backfill),

        # ── 5. Make FK non-nullable now that all rows are filled ─────────────
        migrations.AlterField(
            model_name='match',
            name='tournament',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='matches',
                to='teams.tournament',
            ),
        ),

        # ── 6. Drop the old string column ────────────────────────────────────
        migrations.RemoveField(
            model_name='match',
            name='tournament_str',
        ),

        # ── 7. Add new Match fields ──────────────────────────────────────────
        migrations.AddField(
            model_name='match',
            name='home_score',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='match',
            name='away_score',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='match',
            name='duration',
            field=models.CharField(
                blank=True,
                choices=[
                    ('REGULAR', 'Regular'),
                    ('EXTRA_TIME', 'Extra Time'),
                    ('PENALTY_SHOOTOUT', 'Penalty Shootout'),
                ],
                max_length=20,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='match',
            name='odds',
            field=models.JSONField(blank=True, null=True),
        ),

        # ── 8. Add draw to Match.Result choices (no schema change, just metadata)
        migrations.AlterField(
            model_name='match',
            name='result',
            field=models.CharField(
                choices=[
                    ('NR', 'No Result'),
                    ('team1', 'Team 1 Won'),
                    ('team2', 'Team 2 Won'),
                    ('draw', 'Draw'),
                    ('IP', 'In Progress'),
                    ('TBD', 'TBD'),
                    ('TOSS', 'Toss'),
                    ('DLD', 'Delayed'),
                ],
                db_index=True,
                default='TBD',
                max_length=10,
            ),
        ),

        # ── 9. Add Selection.draw field ──────────────────────────────────────
        migrations.AddField(
            model_name='selection',
            name='draw',
            field=models.BooleanField(default=False),
        ),

        # ── 10. Allow Selection.selection to be blank (draw picks have no team)
        migrations.AlterField(
            model_name='selection',
            name='selection',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to='teams.team',
            ),
        ),
    ]
