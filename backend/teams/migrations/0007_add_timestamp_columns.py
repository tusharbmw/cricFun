"""
Migration 0005 marked timestamp columns as state-only (assuming v1 had them).
After dropping and recreating tables from scratch, those columns are missing.
This migration adds them for real on both Oracle and SQLite.
"""
from django.db import migrations


def add_timestamp_columns(apps, schema_editor):
    vendor = schema_editor.connection.vendor
    if vendor == 'oracle':
        schema_editor.execute(
            "ALTER TABLE TEAMS_MATCH ADD ("
            "CREATED_AT TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, "
            "UPDATED_AT TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL)"
        )
        schema_editor.execute(
            "ALTER TABLE TEAMS_SELECTION ADD ("
            "CREATED_AT TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL, "
            "UPDATED_AT TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL)"
        )
    elif vendor == 'sqlite':
        schema_editor.execute(
            'ALTER TABLE "teams_match" ADD COLUMN "created_at" datetime NOT NULL DEFAULT CURRENT_TIMESTAMP'
        )
        schema_editor.execute(
            'ALTER TABLE "teams_match" ADD COLUMN "updated_at" datetime NOT NULL DEFAULT CURRENT_TIMESTAMP'
        )
        schema_editor.execute(
            'ALTER TABLE "teams_selection" ADD COLUMN "created_at" datetime NOT NULL DEFAULT CURRENT_TIMESTAMP'
        )
        schema_editor.execute(
            'ALTER TABLE "teams_selection" ADD COLUMN "updated_at" datetime NOT NULL DEFAULT CURRENT_TIMESTAMP'
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
