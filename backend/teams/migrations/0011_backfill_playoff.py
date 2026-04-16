from django.db import migrations


def backfill_playoff(apps, schema_editor):
    Match = apps.get_model('teams', 'Match')
    Match.objects.filter(match_points__gt=1).update(playoff=True)


class Migration(migrations.Migration):

    dependencies = [
        ('teams', '0010_add_playoff_to_match'),
    ]

    operations = [
        migrations.RunPython(backfill_playoff, migrations.RunPython.noop),
    ]
