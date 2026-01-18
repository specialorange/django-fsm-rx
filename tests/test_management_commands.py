"""
Tests for django_fsm_rx management commands.
"""

from __future__ import annotations

import tempfile
from io import StringIO
from pathlib import Path

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError


class TestCheckFSMMigrationCommand:
    """Tests for check_fsm_migration management command."""

    def test_command_exists(self):
        """The command should be importable."""
        from django_fsm_rx.management.commands.check_fsm_migration import Command

        assert Command is not None

    def test_command_runs_with_clean_directory(self):
        """Command should succeed with a directory containing no deprecated imports."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a clean Python file
            clean_file = Path(tmpdir) / "clean.py"
            clean_file.write_text("from django_fsm_rx import FSMField\n")

            out = StringIO()
            call_command("check_fsm_migration", path=tmpdir, stdout=out)
            output = out.getvalue()

            assert "No deprecated imports found" in output

    def test_command_finds_deprecated_imports(self):
        """Command should find deprecated imports."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a file with deprecated import
            deprecated_file = Path(tmpdir) / "models.py"
            deprecated_file.write_text("from django_fsm import FSMField, transition\n")

            out = StringIO()
            call_command("check_fsm_migration", path=tmpdir, stdout=out)
            output = out.getvalue()

            assert "Files affected: 1" in output
            assert "django_fsm" in output
            assert "django_fsm_rx" in output

    def test_command_verbose_output(self):
        """Command should provide verbose output when requested."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a file with deprecated import
            deprecated_file = Path(tmpdir) / "models.py"
            deprecated_file.write_text("from django_fsm import FSMField\n")

            out = StringIO()
            call_command("check_fsm_migration", path=tmpdir, verbose=True, stdout=out)
            output = out.getvalue()

            assert "Migration Guide" in output or "Migration Notes" in output

    def test_command_json_output(self):
        """Command should provide JSON output when requested."""
        import json

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a clean file
            clean_file = Path(tmpdir) / "clean.py"
            clean_file.write_text("from django_fsm_rx import FSMField\n")

            out = StringIO()
            call_command("check_fsm_migration", path=tmpdir, json=True, stdout=out)
            output = out.getvalue()

            # Should be valid JSON
            data = json.loads(output)
            assert "is_fully_migrated" in data
            assert data["is_fully_migrated"] is True

    def test_command_exclude_patterns(self):
        """Command should respect exclude patterns."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a deprecated file in migrations directory
            migrations_dir = Path(tmpdir) / "migrations"
            migrations_dir.mkdir()
            deprecated_file = migrations_dir / "0001_initial.py"
            deprecated_file.write_text("from django_fsm import FSMField\n")

            out = StringIO()
            call_command("check_fsm_migration", path=tmpdir, exclude="migrations", stdout=out)
            output = out.getvalue()

            # Should report no issues because migrations are excluded
            assert "No deprecated imports found" in output

    def test_command_invalid_path_raises_error(self):
        """Command should raise error for invalid path."""
        with pytest.raises(CommandError) as exc_info:
            call_command("check_fsm_migration", path="/nonexistent/path/12345")

        assert "does not exist" in str(exc_info.value)

    def test_command_handles_multiple_deprecated_packages(self):
        """Command should handle files with imports from multiple deprecated packages."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a file with multiple deprecated imports
            multi_file = Path(tmpdir) / "admin.py"
            multi_file.write_text(
                "from django_fsm import FSMField\n"
                "from django_fsm_admin.mixins import FSMTransitionMixin\n"
            )

            out = StringIO()
            call_command("check_fsm_migration", path=tmpdir, stdout=out)
            output = out.getvalue()

            assert "django_fsm" in output
            assert "FSMTransitionMixin" in output or "django_fsm_admin" in output


class TestGraphTransitionsCommand:
    """Tests for graph_transitions management command."""

    def test_command_exists(self):
        """The graph_transitions command should be importable."""
        from django_fsm_rx.management.commands.graph_transitions import Command

        assert Command is not None
