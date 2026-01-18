"""
Migration utilities for users transitioning from other django-fsm packages.

This module provides helpers, validators, and utilities to assist with
migrating from:
- django-fsm (original package)
- django-fsm-2 (maintained fork)
- django-fsm-admin (admin integration)
- django-fsm-log (transition logging)

Migration Guide Summary:
------------------------

1. django-fsm / django-fsm-2 -> django_fsm_rx:
   - Change imports: `from django_fsm import ...` -> `from django_fsm_rx import ...`
   - All core APIs are compatible (FSMField, transition, can_proceed, etc.)
   - Protected fields work the same way
   - Conditions and permissions work the same way

2. django-fsm-admin -> django_fsm_rx:
   - Change import: `from django_fsm_admin.mixins import FSMTransitionMixin`
              to: `from django_fsm_rx.admin import FSMAdminMixin`
   - FSMTransitionMixin is aliased to FSMAdminMixin for backwards compatibility
   - Admin templates are included in django_fsm_rx

3. django-fsm-log -> django_fsm_rx:
   - Built-in audit logging (FSMTransitionLog model)
   - StateLog is aliased to FSMTransitionLog
   - fsm_log_by and fsm_log_description decorators available from django_fsm_rx.log
   - No need for separate INSTALLED_APPS entry

Example Migration:
------------------

Before (multiple packages):
    >>> from django_fsm import FSMField, transition, can_proceed
    >>> from django_fsm_admin.mixins import FSMTransitionMixin
    >>> from django_fsm_log.models import StateLog
    >>> from django_fsm_log.decorators import fsm_log_by

After (single package):
    >>> from django_fsm_rx import FSMField, transition, can_proceed
    >>> from django_fsm_rx.admin import FSMAdminMixin  # or FSMTransitionMixin
    >>> from django_fsm_rx import FSMTransitionLog  # or StateLog from django_fsm_log.models
    >>> from django_fsm_rx.log import fsm_log_by
"""

from __future__ import annotations

import re
import warnings
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any
from typing import TypedDict

if TYPE_CHECKING:
    from django.db.models import Model

__all__ = [
    "check_migration_status",
    "MigrationReport",
    "scan_imports_in_file",
    "scan_imports_in_directory",
    "get_import_replacements",
    "validate_model_fsm_compatibility",
    "IMPORT_MAPPINGS",
]


class ImportMapping(TypedDict):
    """Mapping from old import to new import."""

    old_module: str
    old_name: str
    new_module: str
    new_name: str
    notes: str


# Comprehensive mapping of old imports to new imports
IMPORT_MAPPINGS: list[ImportMapping] = [
    # Core django-fsm / django-fsm-2 imports
    {
        "old_module": "django_fsm",
        "old_name": "FSMField",
        "new_module": "django_fsm_rx",
        "new_name": "FSMField",
        "notes": "Direct replacement, API identical",
    },
    {
        "old_module": "django_fsm",
        "old_name": "FSMIntegerField",
        "new_module": "django_fsm_rx",
        "new_name": "FSMIntegerField",
        "notes": "Direct replacement, API identical",
    },
    {
        "old_module": "django_fsm",
        "old_name": "FSMKeyField",
        "new_module": "django_fsm_rx",
        "new_name": "FSMKeyField",
        "notes": "Direct replacement, API identical",
    },
    {
        "old_module": "django_fsm",
        "old_name": "transition",
        "new_module": "django_fsm_rx",
        "new_name": "transition",
        "notes": "Direct replacement. New features: on_success, on_commit, atomic callbacks",
    },
    {
        "old_module": "django_fsm",
        "old_name": "can_proceed",
        "new_module": "django_fsm_rx",
        "new_name": "can_proceed",
        "notes": "Direct replacement, API identical",
    },
    {
        "old_module": "django_fsm",
        "old_name": "has_transition_perm",
        "new_module": "django_fsm_rx",
        "new_name": "has_transition_perm",
        "notes": "Direct replacement, API identical",
    },
    {
        "old_module": "django_fsm",
        "old_name": "TransitionNotAllowed",
        "new_module": "django_fsm_rx",
        "new_name": "TransitionNotAllowed",
        "notes": "Direct replacement, API identical",
    },
    {
        "old_module": "django_fsm",
        "old_name": "ConcurrentTransition",
        "new_module": "django_fsm_rx",
        "new_name": "ConcurrentTransition",
        "notes": "Direct replacement, API identical",
    },
    {
        "old_module": "django_fsm",
        "old_name": "ConcurrentTransitionMixin",
        "new_module": "django_fsm_rx",
        "new_name": "ConcurrentTransitionMixin",
        "notes": "Direct replacement, API identical",
    },
    {
        "old_module": "django_fsm",
        "old_name": "FSMFieldMixin",
        "new_module": "django_fsm_rx",
        "new_name": "FSMFieldMixin",
        "notes": "Direct replacement, API identical",
    },
    {
        "old_module": "django_fsm",
        "old_name": "RETURN_VALUE",
        "new_module": "django_fsm_rx",
        "new_name": "RETURN_VALUE",
        "notes": "Direct replacement, API identical",
    },
    {
        "old_module": "django_fsm",
        "old_name": "GET_STATE",
        "new_module": "django_fsm_rx",
        "new_name": "GET_STATE",
        "notes": "Direct replacement, API identical",
    },
    # django-fsm-2 specific
    {
        "old_module": "django_fsm_2",
        "old_name": "FSMField",
        "new_module": "django_fsm_rx",
        "new_name": "FSMField",
        "notes": "Direct replacement, API identical",
    },
    {
        "old_module": "django_fsm_2",
        "old_name": "FSMIntegerField",
        "new_module": "django_fsm_rx",
        "new_name": "FSMIntegerField",
        "notes": "Direct replacement, API identical",
    },
    {
        "old_module": "django_fsm_2",
        "old_name": "FSMKeyField",
        "new_module": "django_fsm_rx",
        "new_name": "FSMKeyField",
        "notes": "Direct replacement, API identical",
    },
    {
        "old_module": "django_fsm_2",
        "old_name": "transition",
        "new_module": "django_fsm_rx",
        "new_name": "transition",
        "notes": "Direct replacement. New features: on_success, on_commit, atomic callbacks",
    },
    {
        "old_module": "django_fsm_2",
        "old_name": "can_proceed",
        "new_module": "django_fsm_rx",
        "new_name": "can_proceed",
        "notes": "Direct replacement, API identical",
    },
    {
        "old_module": "django_fsm_2",
        "old_name": "has_transition_perm",
        "new_module": "django_fsm_rx",
        "new_name": "has_transition_perm",
        "notes": "Direct replacement, API identical",
    },
    {
        "old_module": "django_fsm_2",
        "old_name": "TransitionNotAllowed",
        "new_module": "django_fsm_rx",
        "new_name": "TransitionNotAllowed",
        "notes": "Direct replacement, API identical",
    },
    {
        "old_module": "django_fsm_2",
        "old_name": "ConcurrentTransition",
        "new_module": "django_fsm_rx",
        "new_name": "ConcurrentTransition",
        "notes": "Direct replacement, API identical",
    },
    {
        "old_module": "django_fsm_2",
        "old_name": "ConcurrentTransitionMixin",
        "new_module": "django_fsm_rx",
        "new_name": "ConcurrentTransitionMixin",
        "notes": "Direct replacement, API identical",
    },
    # django-fsm-admin
    {
        "old_module": "django_fsm_admin.mixins",
        "old_name": "FSMTransitionMixin",
        "new_module": "django_fsm_rx.admin",
        "new_name": "FSMAdminMixin",
        "notes": "FSMTransitionMixin is aliased to FSMAdminMixin for compatibility",
    },
    {
        "old_module": "django_fsm_admin",
        "old_name": "FSMTransitionMixin",
        "new_module": "django_fsm_rx.admin",
        "new_name": "FSMAdminMixin",
        "notes": "FSMTransitionMixin is aliased to FSMAdminMixin for compatibility",
    },
    # django-fsm-log
    {
        "old_module": "django_fsm_log.models",
        "old_name": "StateLog",
        "new_module": "django_fsm_rx",
        "new_name": "FSMTransitionLog",
        "notes": "StateLog aliased to FSMTransitionLog. Can still use from django_fsm_log.models",
    },
    {
        "old_module": "django_fsm_log.decorators",
        "old_name": "fsm_log_by",
        "new_module": "django_fsm_rx.log",
        "new_name": "fsm_log_by",
        "notes": "Direct replacement, API identical",
    },
    {
        "old_module": "django_fsm_log.decorators",
        "old_name": "fsm_log_description",
        "new_module": "django_fsm_rx.log",
        "new_name": "fsm_log_description",
        "notes": "Direct replacement, API identical",
    },
    {
        "old_module": "django_fsm_log",
        "old_name": "fsm_log_by",
        "new_module": "django_fsm_rx.log",
        "new_name": "fsm_log_by",
        "notes": "Direct replacement, API identical",
    },
    {
        "old_module": "django_fsm_log",
        "old_name": "fsm_log_description",
        "new_module": "django_fsm_rx.log",
        "new_name": "fsm_log_description",
        "notes": "Direct replacement, API identical",
    },
    # Signal imports
    {
        "old_module": "django_fsm.signals",
        "old_name": "pre_transition",
        "new_module": "django_fsm_rx.signals",
        "new_name": "pre_transition",
        "notes": "Direct replacement, API identical",
    },
    {
        "old_module": "django_fsm.signals",
        "old_name": "post_transition",
        "new_module": "django_fsm_rx.signals",
        "new_name": "post_transition",
        "notes": "Direct replacement, API identical",
    },
    {
        "old_module": "django_fsm_2.signals",
        "old_name": "pre_transition",
        "new_module": "django_fsm_rx.signals",
        "new_name": "pre_transition",
        "notes": "Direct replacement, API identical",
    },
    {
        "old_module": "django_fsm_2.signals",
        "old_name": "post_transition",
        "new_module": "django_fsm_rx.signals",
        "new_name": "post_transition",
        "notes": "Direct replacement, API identical",
    },
]


class MigrationReport:
    """
    Report of migration status and required changes.

    Attributes:
        deprecated_imports: List of deprecated import statements found.
        suggested_changes: Dictionary mapping old imports to suggested replacements.
        files_affected: List of file paths that need updating.
        warnings: List of warning messages.
        is_fully_migrated: Boolean indicating if migration is complete.
    """

    def __init__(self) -> None:
        self.deprecated_imports: list[dict[str, Any]] = []
        self.suggested_changes: dict[str, str] = {}
        self.files_affected: list[str] = []
        self.warnings: list[str] = []
        self.is_fully_migrated: bool = True

    def add_deprecated_import(
        self,
        file_path: str,
        line_number: int,
        old_import: str,
        new_import: str,
        notes: str = "",
    ) -> None:
        """Add a deprecated import finding to the report."""
        self.deprecated_imports.append(
            {
                "file": file_path,
                "line": line_number,
                "old": old_import,
                "new": new_import,
                "notes": notes,
            }
        )
        self.suggested_changes[old_import] = new_import
        if file_path not in self.files_affected:
            self.files_affected.append(file_path)
        self.is_fully_migrated = False

    def add_warning(self, message: str) -> None:
        """Add a warning message to the report."""
        self.warnings.append(message)

    def __str__(self) -> str:
        """Generate a human-readable report."""
        lines = ["=" * 60, "Django FSM-RX Migration Report", "=" * 60, ""]

        if self.is_fully_migrated:
            lines.append("No deprecated imports found. Migration complete!")
            return "\n".join(lines)

        lines.append(f"Files affected: {len(self.files_affected)}")
        lines.append(f"Deprecated imports found: {len(self.deprecated_imports)}")
        lines.append("")

        if self.deprecated_imports:
            lines.append("Deprecated Imports:")
            lines.append("-" * 40)
            for item in self.deprecated_imports:
                lines.append(f"  {item['file']}:{item['line']}")
                lines.append(f"    OLD: {item['old']}")
                lines.append(f"    NEW: {item['new']}")
                if item["notes"]:
                    lines.append(f"    NOTE: {item['notes']}")
                lines.append("")

        if self.warnings:
            lines.append("Warnings:")
            lines.append("-" * 40)
            for warning in self.warnings:
                lines.append(f"  - {warning}")

        return "\n".join(lines)


def get_import_replacements() -> dict[str, str]:
    """
    Get a dictionary mapping old import statements to new ones.

    Returns:
        Dictionary mapping old import patterns to new import statements.

    Example:
        >>> replacements = get_import_replacements()
        >>> print(replacements['from django_fsm import FSMField'])
        'from django_fsm_rx import FSMField'
    """
    replacements = {}
    for mapping in IMPORT_MAPPINGS:
        old = f"from {mapping['old_module']} import {mapping['old_name']}"
        new = f"from {mapping['new_module']} import {mapping['new_name']}"
        replacements[old] = new
    return replacements


def scan_imports_in_file(file_path: str | Path, report: MigrationReport | None = None) -> MigrationReport:
    """
    Scan a Python file for deprecated django-fsm imports.

    Args:
        file_path: Path to the Python file to scan.
        report: Optional existing report to add findings to.

    Returns:
        MigrationReport with findings from the file.

    Example:
        >>> report = scan_imports_in_file('myapp/models.py')
        >>> print(report)
    """
    if report is None:
        report = MigrationReport()

    file_path = Path(file_path)
    if not file_path.exists():
        report.add_warning(f"File not found: {file_path}")
        return report

    if not file_path.suffix == ".py":
        return report

    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        report.add_warning(f"Could not read {file_path}: {e}")
        return report

    lines = content.split("\n")

    # Build regex patterns for each deprecated module
    deprecated_patterns = {
        "django_fsm": r"from\s+django_fsm\s+import\s+",
        "django_fsm_2": r"from\s+django_fsm_2\s+import\s+",
        "django_fsm.signals": r"from\s+django_fsm\.signals\s+import\s+",
        "django_fsm_2.signals": r"from\s+django_fsm_2\.signals\s+import\s+",
        "django_fsm_admin": r"from\s+django_fsm_admin(?:\.mixins)?\s+import\s+",
        "django_fsm_log": r"from\s+django_fsm_log(?:\.(?:models|decorators))?\s+import\s+",
    }

    for line_num, line in enumerate(lines, start=1):
        stripped = line.strip()

        # Skip comments and empty lines
        if not stripped or stripped.startswith("#"):
            continue

        for module_key, pattern in deprecated_patterns.items():
            if re.match(pattern, stripped):
                # Find matching import mapping
                for mapping in IMPORT_MAPPINGS:
                    if mapping["old_module"].startswith(module_key.replace(".", r"\.")):
                        if mapping["old_name"] in stripped:
                            old_import = f"from {mapping['old_module']} import {mapping['old_name']}"
                            new_import = f"from {mapping['new_module']} import {mapping['new_name']}"
                            report.add_deprecated_import(
                                str(file_path),
                                line_num,
                                old_import,
                                new_import,
                                mapping["notes"],
                            )
                            break

    return report


def scan_imports_in_directory(
    directory: str | Path,
    exclude_patterns: list[str] | None = None,
    report: MigrationReport | None = None,
) -> MigrationReport:
    """
    Scan a directory recursively for deprecated django-fsm imports.

    Args:
        directory: Path to the directory to scan.
        exclude_patterns: List of patterns to exclude (e.g., ['migrations', '__pycache__']).
        report: Optional existing report to add findings to.

    Returns:
        MigrationReport with findings from all files.

    Example:
        >>> report = scan_imports_in_directory('myproject/', exclude_patterns=['migrations'])
        >>> print(report)
    """
    if report is None:
        report = MigrationReport()

    if exclude_patterns is None:
        exclude_patterns = ["migrations", "__pycache__", ".git", "venv", "env", ".venv"]

    directory = Path(directory)
    if not directory.exists():
        report.add_warning(f"Directory not found: {directory}")
        return report

    for file_path in directory.rglob("*.py"):
        # Check if any exclude pattern is in the path
        if any(pattern in str(file_path) for pattern in exclude_patterns):
            continue
        scan_imports_in_file(file_path, report)

    return report


def check_migration_status() -> MigrationReport:
    """
    Check current migration status by scanning for deprecated imports.

    This function tries to find the project root and scan all Python files.
    It's designed to be called from a Django management command or interactively.

    Returns:
        MigrationReport with migration status.

    Example:
        >>> from django_fsm_rx.migration import check_migration_status
        >>> report = check_migration_status()
        >>> print(report)
    """
    report = MigrationReport()

    # Try to find project root from Django settings
    try:
        from django.conf import settings

        if hasattr(settings, "BASE_DIR"):
            base_dir = Path(settings.BASE_DIR)
            return scan_imports_in_directory(base_dir, report=report)
    except Exception:
        pass

    # Fallback to current directory
    return scan_imports_in_directory(Path.cwd(), report=report)


def validate_model_fsm_compatibility(model_class: type[Model]) -> list[str]:
    """
    Validate that a model's FSM setup is compatible with django_fsm_rx.

    This function checks for common migration issues:
    - FSM fields are properly configured
    - Transitions are properly decorated
    - Protected fields are handled correctly

    Args:
        model_class: The Django model class to validate.

    Returns:
        List of warning messages (empty if no issues).

    Example:
        >>> from myapp.models import Order
        >>> warnings = validate_model_fsm_compatibility(Order)
        >>> for warning in warnings:
        ...     print(warning)
    """
    from django_fsm_rx import FSMFieldMixin

    validation_warnings: list[str] = []

    # Check for FSM fields
    fsm_fields = []
    for field in model_class._meta.get_fields():
        if isinstance(field, FSMFieldMixin):
            fsm_fields.append(field)

    if not fsm_fields:
        validation_warnings.append(f"Model {model_class.__name__} has no FSM fields defined")
        return validation_warnings

    # Check each FSM field
    for field in fsm_fields:
        field_name = field.name

        # Check for transitions
        if model_class not in field.transitions or not field.transitions[model_class]:
            validation_warnings.append(f"FSM field '{field_name}' has no transitions defined")
            continue

        # Check transition methods
        for method_name, method in field.transitions[model_class].items():
            if not hasattr(method, "_django_fsm_rx"):
                validation_warnings.append(
                    f"Transition method '{method_name}' missing _django_fsm_rx metadata. "
                    "Ensure @transition decorator is applied correctly."
                )

    # Check for FSMModelMixin if protected fields exist
    has_protected = any(getattr(f, "protected", False) for f in fsm_fields)
    if has_protected:
        from django_fsm_rx import FSMModelMixin

        if not issubclass(model_class, FSMModelMixin):
            validation_warnings.append(
                f"Model {model_class.__name__} has protected FSM field(s) but does not "
                "inherit from FSMModelMixin. Consider adding FSMModelMixin to enable "
                "refresh_from_db() support for protected fields."
            )

    return validation_warnings


def show_migration_warnings() -> None:
    """
    Display migration warnings to help users update their imports.

    This function checks for deprecated import patterns and shows
    helpful messages guiding users to the new import locations.
    Intended to be called during Django's ready() phase.
    """
    import sys

    # Check for deprecated imports in sys.modules
    deprecated_modules = {
        "django_fsm": "django_fsm_rx",
        "django_fsm_2": "django_fsm_rx",
        "django_fsm_admin": "django_fsm_rx.admin",
    }

    for old_module, new_module in deprecated_modules.items():
        if old_module in sys.modules:
            warnings.warn(
                f"Detected import from deprecated module '{old_module}'. "
                f"Please update to use '{new_module}' instead.",
                DeprecationWarning,
                stacklevel=1,
            )


# Migration helper functions for common patterns


def migrate_fsm_log_to_fsm_transition_log(
    model_class: type[Model],
    state_field: str = "state",
    batch_size: int = 1000,
    dry_run: bool = True,
) -> dict[str, Any]:
    """
    Migrate existing StateLog entries to FSMTransitionLog format.

    This function helps migrate data from django-fsm-log's StateLog table
    to django-fsm-rx's FSMTransitionLog table.

    Note: This is only needed if you have existing StateLog data and want
    to migrate to a separate FSMTransitionLog table. If you're using the
    StateLog alias (which points to FSMTransitionLog), no data migration
    is needed.

    Args:
        model_class: The model class to migrate logs for.
        state_field: The name of the FSM field (default: 'state').
        batch_size: Number of records to process at a time.
        dry_run: If True, only report what would be migrated.

    Returns:
        Dictionary with migration statistics.

    Example:
        >>> from myapp.models import Order
        >>> stats = migrate_fsm_log_to_fsm_transition_log(Order, dry_run=False)
        >>> print(f"Migrated {stats['migrated']} entries")
    """
    from django.contrib.contenttypes.models import ContentType

    from django_fsm_rx import FSMTransitionLog

    stats = {
        "total": 0,
        "migrated": 0,
        "skipped": 0,
        "errors": [],
    }

    content_type = ContentType.objects.get_for_model(model_class)

    # Check if old StateLog table exists
    try:
        from django.db import connection

        with connection.cursor() as cursor:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='django_fsm_log_statelog'")
            if not cursor.fetchone():
                stats["errors"].append("Old StateLog table not found")
                return stats
    except Exception:
        # Non-SQLite database, try direct query
        pass

    try:
        # Try to access old StateLog entries
        # This assumes the old django_fsm_log is still installed
        from django_fsm_log.models import StateLog

        old_logs = StateLog.objects.filter(content_type=content_type).order_by("id")
        stats["total"] = old_logs.count()

        if dry_run:
            stats["migrated"] = stats["total"]
            stats["skipped"] = 0
            return stats

        # Batch process
        for i in range(0, stats["total"], batch_size):
            batch = old_logs[i : i + batch_size]
            for log in batch:
                # Check if already migrated
                exists = FSMTransitionLog.objects.filter(
                    content_type=content_type,
                    object_id=log.object_id,
                    timestamp=log.timestamp,
                    transition_name=log.transition,
                ).exists()

                if exists:
                    stats["skipped"] += 1
                    continue

                # Create new log entry
                FSMTransitionLog.objects.create(
                    content_type=content_type,
                    object_id=log.object_id,
                    transition_name=log.transition,
                    source_state=log.source_state,
                    target_state=log.state,
                    timestamp=log.timestamp,
                    by=log.by,
                    description=getattr(log, "description", ""),
                )
                stats["migrated"] += 1

    except ImportError:
        stats["errors"].append("django_fsm_log not installed, cannot migrate old logs")
    except Exception as e:
        stats["errors"].append(str(e))

    return stats


# Convenience function for running migration check from management command
def run_migration_check_command() -> int:
    """
    Run migration check and print report to stdout.

    Returns:
        Exit code (0 if fully migrated, 1 if migration needed).

    This is designed to be used in a management command:

        # myapp/management/commands/check_fsm_migration.py
        from django.core.management.base import BaseCommand
        from django_fsm_rx.migration import run_migration_check_command

        class Command(BaseCommand):
            help = 'Check for deprecated django-fsm imports'

            def handle(self, *args, **options):
                exit_code = run_migration_check_command()
                if exit_code:
                    self.stdout.write(self.style.WARNING('Migration needed'))
                else:
                    self.stdout.write(self.style.SUCCESS('Migration complete'))
    """
    report = check_migration_status()
    print(str(report))
    return 0 if report.is_fully_migrated else 1
