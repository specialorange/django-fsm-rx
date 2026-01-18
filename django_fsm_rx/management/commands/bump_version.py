"""
Management command to bump version and handle all release tasks.

This command:
1. Updates version in pyproject.toml
2. Adds a changelog entry
3. Commits the changes
4. Creates a git tag (without 'v' prefix)
5. Optionally pushes to remote

Usage:
    python manage.py bump_version 5.1.4 --message "Add new feature X"
    python manage.py bump_version 5.1.4 -m "Add new feature X" --push
    python manage.py bump_version 5.1.4 -m "Fix bug Y" -m "Add feature Z" --push
"""

from __future__ import annotations

import re
import subprocess
from datetime import date
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand
from django.core.management.base import CommandError


class Command(BaseCommand):
    """Management command to bump version and create release."""

    help = "Bump version, update changelog, commit, and tag"

    def add_arguments(self, parser: Any) -> None:
        """Add command-line arguments."""
        parser.add_argument(
            "version",
            type=str,
            help="New version number (e.g., 5.1.4)",
        )
        parser.add_argument(
            "-m",
            "--message",
            action="append",
            dest="messages",
            help="Changelog entry (can be used multiple times for multiple entries)",
        )
        parser.add_argument(
            "--push",
            action="store_true",
            help="Push commits and tags to origin after creating",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be done without making changes",
        )
        parser.add_argument(
            "--no-commit",
            action="store_true",
            help="Update files but don't commit or tag",
        )
        parser.add_argument(
            "--no-changelog",
            action="store_true",
            help="Skip changelog update",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        """Execute the command."""
        version = options["version"]
        messages = options["messages"] or []
        dry_run = options["dry_run"]
        push = options["push"]
        no_commit = options["no_commit"]
        no_changelog = options["no_changelog"]

        # Validate version format
        if not re.match(r"^\d+\.\d+\.\d+$", version):
            raise CommandError(f"Invalid version format: {version}. Expected format: X.Y.Z")

        # Find project root (where pyproject.toml is)
        project_root = self._find_project_root()
        if not project_root:
            raise CommandError("Could not find pyproject.toml. Run from project directory.")

        pyproject_path = project_root / "pyproject.toml"
        changelog_path = project_root / "CHANGELOG.rst"

        # Get current version
        current_version = self._get_current_version(pyproject_path)
        self.stdout.write(f"Current version: {current_version}")
        self.stdout.write(f"New version: {version}")

        if current_version == version:
            raise CommandError(f"Version {version} is already set in pyproject.toml")

        # Require changelog messages unless skipped
        if not no_changelog and not messages:
            raise CommandError("Please provide at least one changelog message with -m/--message")

        if dry_run:
            self.stdout.write(self.style.WARNING("\n=== DRY RUN ===\n"))

        # Step 1: Update pyproject.toml
        self.stdout.write(f"\n1. Updating pyproject.toml: {current_version} -> {version}")
        if not dry_run:
            self._update_pyproject_version(pyproject_path, current_version, version)
            self.stdout.write(self.style.SUCCESS("   ✓ pyproject.toml updated"))
        else:
            self.stdout.write("   Would update pyproject.toml")

        # Step 2: Update CHANGELOG.rst
        if not no_changelog:
            self.stdout.write(f"\n2. Adding changelog entry for {version}")
            if changelog_path.exists():
                if not dry_run:
                    self._update_changelog(changelog_path, version, messages)
                    self.stdout.write(self.style.SUCCESS("   ✓ CHANGELOG.rst updated"))
                else:
                    self.stdout.write("   Would add changelog entry:")
                    for msg in messages:
                        self.stdout.write(f"     - {msg}")
            else:
                self.stdout.write(self.style.WARNING("   CHANGELOG.rst not found, skipping"))
        else:
            self.stdout.write("\n2. Skipping changelog (--no-changelog)")

        if no_commit:
            self.stdout.write(self.style.SUCCESS(f"\nFiles updated for version {version}"))
            self.stdout.write("Skipping commit and tag (--no-commit)")
            return

        # Step 3: Git commit
        self.stdout.write("\n3. Creating git commit")
        if not dry_run:
            self._git_commit(project_root, version, messages)
            self.stdout.write(self.style.SUCCESS("   ✓ Committed changes"))
        else:
            self.stdout.write(f"   Would commit with message: 'Release {version}'")

        # Step 4: Create git tag (without 'v' prefix)
        self.stdout.write(f"\n4. Creating git tag: {version}")
        if not dry_run:
            self._git_tag(project_root, version, messages)
            self.stdout.write(self.style.SUCCESS(f"   ✓ Tag {version} created"))
        else:
            self.stdout.write(f"   Would create tag: {version}")

        # Step 5: Push (optional)
        if push:
            self.stdout.write("\n5. Pushing to origin")
            if not dry_run:
                self._git_push(project_root, version)
                self.stdout.write(self.style.SUCCESS("   ✓ Pushed commits and tag to origin"))
            else:
                self.stdout.write("   Would push commits and tag to origin")
        else:
            self.stdout.write("\n5. Skipping push (use --push to push automatically)")
            self.stdout.write("   To push manually:")
            self.stdout.write("     git push origin main")
            self.stdout.write(f"     git push origin {version}")

        self.stdout.write(self.style.SUCCESS(f"\n{'Would release' if dry_run else 'Released'} version {version}"))

    def _find_project_root(self) -> Path | None:
        """Find the project root directory containing pyproject.toml."""
        # Try current directory first
        cwd = Path.cwd()
        if (cwd / "pyproject.toml").exists():
            return cwd

        # Try to find via django settings
        try:
            from django.conf import settings

            if hasattr(settings, "BASE_DIR"):
                base = Path(settings.BASE_DIR)
                # Check BASE_DIR and parent (in case BASE_DIR is a subdirectory)
                for check_path in [base, base.parent]:
                    if (check_path / "pyproject.toml").exists():
                        return check_path
        except Exception:
            pass

        # Walk up from current directory
        current = cwd
        for _ in range(10):  # Max 10 levels up
            if (current / "pyproject.toml").exists():
                return current
            parent = current.parent
            if parent == current:
                break
            current = parent

        return None

    def _get_current_version(self, pyproject_path: Path) -> str:
        """Get current version from pyproject.toml."""
        content = pyproject_path.read_text()
        match = re.search(r'^version\s*=\s*"([^"]+)"', content, re.MULTILINE)
        if not match:
            raise CommandError("Could not find version in pyproject.toml")
        return match.group(1)

    def _update_pyproject_version(self, pyproject_path: Path, old_version: str, new_version: str) -> None:
        """Update version in pyproject.toml."""
        content = pyproject_path.read_text()
        new_content = re.sub(
            r'^(version\s*=\s*)"[^"]+"',
            f'\\1"{new_version}"',
            content,
            count=1,
            flags=re.MULTILINE,
        )
        pyproject_path.write_text(new_content)

    def _update_changelog(self, changelog_path: Path, version: str, messages: list[str]) -> None:
        """Add entry to CHANGELOG.rst."""
        content = changelog_path.read_text()
        today = date.today().strftime("%Y-%m-%d")

        # Build the new entry
        header = f"django-fsm-rx {version} {today}"
        underline = "~" * len(header)
        entries = "\n".join(f"- {msg}" for msg in messages)
        new_entry = f"{header}\n{underline}\n\n{entries}\n\n\n"

        # Insert after the main title
        # Look for the pattern: Changelog\n=========\n\n
        pattern = r"(Changelog\n=+\n\n)"
        if re.search(pattern, content):
            new_content = re.sub(pattern, f"\\1{new_entry}", content, count=1)
        else:
            # Fallback: prepend to file
            new_content = f"Changelog\n=========\n\n{new_entry}{content}"

        changelog_path.write_text(new_content)

    def _git_commit(self, project_root: Path, version: str, messages: list[str]) -> None:
        """Create git commit with version changes."""
        # Stage changes
        subprocess.run(
            ["git", "add", "pyproject.toml", "CHANGELOG.rst"],
            cwd=project_root,
            check=True,
            capture_output=True,
        )

        # Build commit message
        commit_msg = f"Release {version}\n\n"
        if messages:
            commit_msg += "\n".join(f"- {msg}" for msg in messages)
            commit_msg += "\n"

        # Commit
        subprocess.run(
            ["git", "commit", "-m", commit_msg],
            cwd=project_root,
            check=True,
            capture_output=True,
        )

    def _git_tag(self, project_root: Path, version: str, messages: list[str]) -> None:
        """Create git tag (without 'v' prefix)."""
        # Build tag message
        tag_msg = f"Release {version}"
        if messages:
            tag_msg += "\n\n" + "\n".join(f"- {msg}" for msg in messages)

        subprocess.run(
            ["git", "tag", "-a", version, "-m", tag_msg],
            cwd=project_root,
            check=True,
            capture_output=True,
        )

    def _git_push(self, project_root: Path, version: str) -> None:
        """Push commits and tag to origin."""
        # Push commits
        subprocess.run(
            ["git", "push", "origin", "main"],
            cwd=project_root,
            check=True,
            capture_output=True,
        )

        # Push tag
        subprocess.run(
            ["git", "push", "origin", version],
            cwd=project_root,
            check=True,
            capture_output=True,
        )
