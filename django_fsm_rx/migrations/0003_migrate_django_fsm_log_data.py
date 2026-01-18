# Generated migration to copy data from django_fsm_log to django_fsm_rx
from __future__ import annotations

from django.db import migrations


def migrate_statelog_data(apps, schema_editor):
    """
    Copy data from django_fsm_log_statelog to django_fsm_rx_fsmtransitionlog.

    This migration is safe to run multiple times - it only copies records
    that don't already exist in the new table (based on timestamp + object_id + transition).
    """
    connection = schema_editor.connection

    # Check if old table exists using Django's introspection (database-agnostic)
    table_names = connection.introspection.table_names()

    if "django_fsm_log_statelog" not in table_names:
        # Old table doesn't exist, nothing to migrate
        return

    with connection.cursor() as cursor:
        # Check if there's any data to migrate
        cursor.execute("SELECT COUNT(*) FROM django_fsm_log_statelog")
        count = cursor.fetchone()[0]

        if count == 0:
            return

        # Determine database backend for type casting
        vendor = connection.vendor

        if vendor == "postgresql":
            # PostgreSQL: use ::text for casting
            object_id_cast = "object_id::text"
        else:
            # SQLite, MySQL, etc: CAST function
            object_id_cast = "CAST(object_id AS TEXT)"

        # Migrate data - use INSERT ... SELECT with conflict handling
        # We use a subquery to avoid duplicates based on key fields
        cursor.execute(f"""
            INSERT INTO django_fsm_rx_fsmtransitionlog
                (content_type_id, object_id, transition_name, source_state, target_state, timestamp, by_id, description)
            SELECT
                content_type_id,
                {object_id_cast},
                transition,
                COALESCE(source_state, ''),
                state,
                timestamp,
                by_id,
                COALESCE(description, '')
            FROM django_fsm_log_statelog old
            WHERE NOT EXISTS (
                SELECT 1 FROM django_fsm_rx_fsmtransitionlog new
                WHERE new.content_type_id = old.content_type_id
                AND new.object_id = {object_id_cast}
                AND new.timestamp = old.timestamp
                AND new.transition_name = old.transition
            )
        """)

        migrated = cursor.rowcount
        if migrated > 0:
            print(f"  Migrated {migrated} records from django_fsm_log_statelog to django_fsm_rx_fsmtransitionlog")


def reverse_migration(apps, schema_editor):
    """
    Reverse migration is a no-op.

    We don't delete the migrated data because:
    1. New transitions may have been logged to the new table
    2. Users may have deleted the old table
    3. Data loss is worse than having duplicate data
    """
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("django_fsm_rx", "0002_fsmtransitionlog_by_fsmtransitionlog_description"),
    ]

    operations = [
        migrations.RunPython(migrate_statelog_data, reverse_migration),
    ]
