from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('teams', '0012_tournament_match_updates'),
    ]

    operations = [
        migrations.AlterField(
            model_name='tournament',
            name='external_id',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
    ]
