"""
Migration 0007 created CREATED_AT/UPDATED_AT as TIMESTAMP WITH TIME ZONE.
Django's Oracle backend expects plain TIMESTAMP — the mismatch causes
oracledb decode_date errors when reading those rows.
This migration changes the type to plain TIMESTAMP on Oracle.
"""
from django.db import migrations


def fix_timestamp_types(apps, schema_editor):
    if schema_editor.connection.vendor != 'oracle':
        return
    for table in ('TEAMS_MATCH', 'TEAMS_SELECTION'):
        schema_editor.execute(
            f'ALTER TABLE {table} MODIFY ('
            f'CREATED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP, '
            f'UPDATED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP)'
        )


class Migration(migrations.Migration):

    dependencies = [
        ('teams', '0007_add_timestamp_columns'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[],
            database_operations=[
                migrations.RunPython(fix_timestamp_types, migrations.RunPython.noop),
            ],
        ),
    ]
