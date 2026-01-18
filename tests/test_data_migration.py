"""
Tests for the django_fsm_log data migration.

These tests verify that:
1. The migration correctly copies data from the old table to the new one
2. The migration is idempotent (safe to run multiple times)
3. The migration handles missing old table gracefully
"""

from __future__ import annotations

import pytest
from django.contrib.contenttypes.models import ContentType
from django.db import connection
from django.utils import timezone

from django_fsm_rx import FSMTransitionLog


def migrate_statelog_data_for_test(connection):
    """
    Copy data from django_fsm_log_statelog to django_fsm_rx_fsmtransitionlog.

    This is a test-friendly version of the migration function.
    """
    # Check if old table exists using Django's introspection (database-agnostic)
    table_names = connection.introspection.table_names()

    if "django_fsm_log_statelog" not in table_names:
        # Old table doesn't exist, nothing to migrate
        return 0

    with connection.cursor() as cursor:
        # Check if there's any data to migrate
        cursor.execute("SELECT COUNT(*) FROM django_fsm_log_statelog")
        count = cursor.fetchone()[0]

        if count == 0:
            return 0

        # SQLite: CAST function
        object_id_cast = "CAST(object_id AS TEXT)"

        # Migrate data
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

        return cursor.rowcount


@pytest.fixture
def create_old_statelog_table():
    """Create the old django_fsm_log_statelog table for testing."""
    with connection.cursor() as cursor:
        # Create old table structure matching django-fsm-log's StateLog
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS django_fsm_log_statelog (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME NOT NULL,
                by_id INTEGER,
                source_state VARCHAR(255),
                state VARCHAR(255) NOT NULL,
                transition VARCHAR(255) NOT NULL,
                content_type_id INTEGER NOT NULL,
                object_id INTEGER NOT NULL,
                description TEXT
            )
        """)
    yield
    # Clean up
    with connection.cursor() as cursor:
        cursor.execute("DROP TABLE IF EXISTS django_fsm_log_statelog")


@pytest.fixture
def sample_content_type(db):
    """Get a sample content type for testing."""
    return ContentType.objects.get_for_model(FSMTransitionLog)


@pytest.mark.django_db(transaction=True)
class TestDataMigration:
    """Tests for the data migration from django_fsm_log to django_fsm_rx."""

    def test_migration_copies_data(self, create_old_statelog_table, sample_content_type):
        """Data should be copied from old table to new table."""
        # Insert test data into old table
        now = timezone.now()
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO django_fsm_log_statelog
                    (timestamp, source_state, state, transition, content_type_id, object_id, description)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [now, "draft", "published", "publish", sample_content_type.id, 123, "Test transition"],
            )

        # Run the migration function
        migrated = migrate_statelog_data_for_test(connection)
        assert migrated == 1

        # Verify data was copied
        log = FSMTransitionLog.objects.get(object_id="123", transition_name="publish")
        assert log.source_state == "draft"
        assert log.target_state == "published"
        assert log.description == "Test transition"
        assert log.content_type == sample_content_type

    def test_migration_is_idempotent(self, create_old_statelog_table, sample_content_type):
        """Running migration multiple times should not create duplicates."""
        now = timezone.now()
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO django_fsm_log_statelog
                    (timestamp, source_state, state, transition, content_type_id, object_id, description)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [now, "new", "done", "finish", sample_content_type.id, 456, ""],
            )

        # Run migration twice
        migrate_statelog_data_for_test(connection)
        migrated = migrate_statelog_data_for_test(connection)

        # Second run should migrate 0 (already exists)
        assert migrated == 0

        # Should only have one record
        count = FSMTransitionLog.objects.filter(object_id="456", transition_name="finish").count()
        assert count == 1

    def test_migration_handles_null_source_state(self, create_old_statelog_table, sample_content_type):
        """Migration should handle NULL source_state gracefully."""
        now = timezone.now()
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO django_fsm_log_statelog
                    (timestamp, source_state, state, transition, content_type_id, object_id, description)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [now, None, "active", "activate", sample_content_type.id, 789, None],
            )

        migrate_statelog_data_for_test(connection)

        log = FSMTransitionLog.objects.get(object_id="789", transition_name="activate")
        assert log.source_state == ""  # NULL becomes empty string
        assert log.description == ""  # NULL becomes empty string

    def test_migration_handles_missing_table(self, db):
        """Migration should handle missing old table gracefully."""
        # Ensure old table doesn't exist
        with connection.cursor() as cursor:
            cursor.execute("DROP TABLE IF EXISTS django_fsm_log_statelog")

        # Should not raise an error, returns 0
        migrated = migrate_statelog_data_for_test(connection)
        assert migrated == 0

    def test_migration_preserves_old_table(self, create_old_statelog_table, sample_content_type):
        """Migration should NOT delete data from old table."""
        now = timezone.now()
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO django_fsm_log_statelog
                    (timestamp, source_state, state, transition, content_type_id, object_id, description)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [now, "start", "end", "complete", sample_content_type.id, 999, "Keep me"],
            )

        migrate_statelog_data_for_test(connection)

        # Old table should still have the data
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM django_fsm_log_statelog WHERE object_id = 999")
            count = cursor.fetchone()[0]
            assert count == 1, "Old table data should be preserved"


@pytest.mark.django_db
class TestStateLogAlias:
    """Tests for the StateLog compatibility alias."""

    def test_statelog_is_alias_to_fsmtransitionlog(self):
        """StateLog should be an alias to FSMTransitionLog."""
        from django_fsm_log.models import StateLog

        assert StateLog is FSMTransitionLog

    def test_statelog_can_create_records(self, db):
        """StateLog should be able to create records (same as FSMTransitionLog)."""
        from django_fsm_log.models import StateLog

        ct = ContentType.objects.get_for_model(FSMTransitionLog)
        log = StateLog.objects.create(
            content_type=ct,
            object_id="test-123",
            transition_name="test_transition",
            source_state="start",
            target_state="end",
        )

        assert log.pk is not None
        assert log.transition_name == "test_transition"
        assert log.target_state == "end"

    def test_statelog_queries_new_table(self, db):
        """StateLog queries should use the new FSMTransitionLog table."""
        from django_fsm_log.models import StateLog

        ct = ContentType.objects.get_for_model(FSMTransitionLog)

        # Create via FSMTransitionLog
        FSMTransitionLog.objects.create(
            content_type=ct,
            object_id="alias-test",
            transition_name="via_fsmtransitionlog",
            source_state="a",
            target_state="b",
        )

        # Query via StateLog
        log = StateLog.objects.get(object_id="alias-test")
        assert log.transition_name == "via_fsmtransitionlog"
