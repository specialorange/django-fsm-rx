"""
Management command to check for deprecated django-fsm imports.

This command scans your project for deprecated imports from:
- django_fsm
- django_fsm_2
- django_fsm_admin
- django_fsm_log

And provides guidance on migrating to django_fsm_rx.

Usage:
    python manage.py check_fsm_migration
    python manage.py check_fsm_migration --path /path/to/scan
    python manage.py check_fsm_migration --exclude migrations,tests
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand
from django.core.management.base import CommandError

from django_fsm_rx.migration import MigrationReport
from django_fsm_rx.migration import scan_imports_in_directory


class Command(BaseCommand):
    """Management command to check for deprecated django-fsm imports."""

    help = "Check for deprecated django-fsm imports and provide migration guidance"

    def add_arguments(self, parser: Any) -> None:
        """Add command-line arguments."""
        parser.add_argument(
            "--path",
            type=str,
            default=None,
            help="Path to scan (default: BASE_DIR from settings)",
        )
        parser.add_argument(
            "--exclude",
            type=str,
            default="migrations,__pycache__,.git,venv,env,.venv",
            help="Comma-separated list of patterns to exclude (default: migrations,__pycache__,.git,venv,env,.venv)",
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Show detailed output including all deprecated imports",
        )
        parser.add_argument(
            "--json",
            action="store_true",
            help="Output results as JSON",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        """Execute the command."""
        # Determine path to scan
        path = options["path"]
        if path is None:
            if hasattr(settings, "BASE_DIR"):
                path = str(settings.BASE_DIR)
            else:
                raise CommandError(
                    "Could not determine project root. "
                    "Please provide --path or ensure BASE_DIR is set in settings."
                )

        path_obj = Path(path)
        if not path_obj.exists():
            raise CommandError(f"Path does not exist: {path}")

        # Parse exclude patterns
        exclude_patterns = [p.strip() for p in options["exclude"].split(",") if p.strip()]

        # Scan for deprecated imports
        if not options["json"]:
            self.stdout.write(f"Scanning {path_obj} for deprecated django-fsm imports...")
        report = scan_imports_in_directory(path_obj, exclude_patterns=exclude_patterns)

        # Output results
        if options["json"]:
            self._output_json(report)
        elif options["verbose"]:
            self._output_verbose(report)
        else:
            self._output_summary(report)

    def _output_summary(self, report: MigrationReport) -> None:
        """Output a summary of the migration status."""
        if report.is_fully_migrated:
            self.stdout.write(
                self.style.SUCCESS("No deprecated imports found. Your code is ready for django_fsm_rx!")
            )
            return

        self.stdout.write("")
        self.stdout.write(self.style.WARNING("=" * 60))
        self.stdout.write(self.style.WARNING("Django FSM-RX Migration Check"))
        self.stdout.write(self.style.WARNING("=" * 60))
        self.stdout.write("")
        self.stdout.write(f"Files affected: {len(report.files_affected)}")
        self.stdout.write(f"Deprecated imports found: {len(report.deprecated_imports)}")
        self.stdout.write("")

        # Group by file
        by_file: dict[str, list[dict]] = {}
        for item in report.deprecated_imports:
            file_path = item["file"]
            if file_path not in by_file:
                by_file[file_path] = []
            by_file[file_path].append(item)

        for file_path, imports in by_file.items():
            self.stdout.write(self.style.WARNING(f"\n{file_path}:"))
            for imp in imports:
                self.stdout.write(f"  Line {imp['line']}:")
                self.stdout.write(self.style.ERROR(f"    - {imp['old']}"))
                self.stdout.write(self.style.SUCCESS(f"    + {imp['new']}"))

        self.stdout.write("")
        self.stdout.write(self.style.NOTICE("To fix these imports, update your code as shown above."))
        self.stdout.write(
            self.style.NOTICE("See https://github.com/specialorange/django-fsm-rx for migration guide.")
        )

        if report.warnings:
            self.stdout.write("")
            self.stdout.write(self.style.WARNING("Warnings:"))
            for warning in report.warnings:
                self.stdout.write(f"  - {warning}")

    def _output_verbose(self, report: MigrationReport) -> None:
        """Output detailed migration information."""
        self._output_summary(report)

        if not report.is_fully_migrated and report.deprecated_imports:
            self.stdout.write("")
            self.stdout.write(self.style.NOTICE("=" * 60))
            self.stdout.write(self.style.NOTICE("Migration Notes"))
            self.stdout.write(self.style.NOTICE("=" * 60))

            # Collect unique notes
            notes_seen = set()
            for item in report.deprecated_imports:
                if item["notes"] and item["notes"] not in notes_seen:
                    notes_seen.add(item["notes"])
                    self.stdout.write(f"  - {item['notes']}")

            self.stdout.write("")
            self.stdout.write(self.style.NOTICE("Quick Migration Guide:"))
            self.stdout.write("  1. Replace 'django_fsm' with 'django_fsm_rx' in imports")
            self.stdout.write("  2. Replace 'django_fsm_2' with 'django_fsm_rx' in imports")
            self.stdout.write("  3. Replace 'django_fsm_admin' with 'django_fsm_rx.admin' in imports")
            self.stdout.write("  4. Replace 'django_fsm_log' with 'django_fsm_rx.log' in imports")
            self.stdout.write("  5. Update INSTALLED_APPS: only 'django_fsm_rx' is needed")

    def _output_json(self, report: MigrationReport) -> None:
        """Output results as JSON."""
        import json

        data = {
            "is_fully_migrated": report.is_fully_migrated,
            "files_affected": report.files_affected,
            "deprecated_imports": report.deprecated_imports,
            "warnings": report.warnings,
            "suggested_changes": report.suggested_changes,
        }
        self.stdout.write(json.dumps(data, indent=2))
