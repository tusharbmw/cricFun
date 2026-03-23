"""
Migration 0005 marked timestamp columns as state-only (assuming v1 had them).
After dropping and recreating tables from scratch, those columns are missing.
This migration adds them for real on both Oracle and SQLite.
"""
from django.db import migrations


def _existing_columns(connection, table):
    with connection.cursor() as cursor:
        return {col.name for col in connection.introspection.get_table_description(cursor, table)}


def add_timestamp_columns(apps, schema_editor):
    conn = schema_editor.connection
    vendor = conn.vendor

    for table in ('teams_match', 'teams_selection'):
        existing = _existing_columns(conn, table)
        if vendor == 'oracle':
            tbl = table.upper()
            cols = []
            if 'created_at' not in existing:
                cols.append('CREATED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL')
            if 'updated_at' not in existing:
                cols.append('UPDATED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL')
            if cols:
                schema_editor.execute(f'ALTER TABLE {tbl} ADD ({", ".join(cols)})')
        elif vendor == 'sqlite':
            if 'created_at' not in existing:
                schema_editor.execute(
                    f'ALTER TABLE "{table}" ADD COLUMN "created_at" datetime NOT NULL DEFAULT CURRENT_TIMESTAMP'
                )
            if 'updated_at' not in existing:
                schema_editor.execute(
                    f'ALTER TABLE "{table}" ADD COLUMN "updated_at" datetime NOT NULL DEFAULT CURRENT_TIMESTAMP'
                )


def remove_timestamp_columns(apps, schema_editor):
    vendor = schema_editor.connection.vendor
    if vendor == 'oracle':
        schema_editor.execute("ALTER TABLE TEAMS_MATCH DROP (CREATED_AT, UPDATED_AT)")
        schema_editor.execute("ALTER TABLE TEAMS_SELECTION DROP (CREATED_AT, UPDATED_AT)")
    elif vendor == 'sqlite':
        # SQLite < 3.35 does not support DROP COLUMN; skip reverse
        pass


class Migration(migrations.Migration):

    dependencies = [
        ('teams', '0006_alter_match_description_alter_match_tournament_and_more'),
    ]

    operations = [
        # State already updated by 0005 — only the DB columns are missing.
        migrations.SeparateDatabaseAndState(
            state_operations=[],
            database_operations=[
                migrations.RunPython(add_timestamp_columns, remove_timestamp_columns),
            ],
        ),
    ]
