from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0002_add_tournament_id"),
    ]

    operations = [
        migrations.RenameField(
            model_name="sitesettings",
            old_name="bet_window_days",
            new_name="pick_window_days",
        ),
    ]
