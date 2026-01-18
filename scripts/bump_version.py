#!/usr/bin/env python3
"""
Standalone script to bump version and handle all release tasks.

This script:
1. Updates version in pyproject.toml
2. Adds a changelog entry
3. Commits the changes
4. Creates a git tag (without 'v' prefix)
5. Optionally pushes to remote

Usage:
    python scripts/bump_version.py 5.1.4 -m "Add new feature X"
    python scripts/bump_version.py 5.1.4 -m "Add new feature X" --push
    python scripts/bump_version.py 5.1.4 -m "Fix bug Y" -m "Add feature Z" --push
    python scripts/bump_version.py 5.1.4 --dry-run -m "Test release"

Can also be run via uv:
    uv run scripts/bump_version.py 5.1.4 -m "Add new feature"
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from datetime import date
from pathlib import Path


class VersionBumper:
    """Handle version bumping and release tasks."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.pyproject_path = project_root / "pyproject.toml"
        self.changelog_path = project_root / "CHANGELOG.rst"

    def get_current_version(self) -> str:
        """Get current version from pyproject.toml."""
        content = self.pyproject_path.read_text()
        match = re.search(r'^version\s*=\s*"([^"]+)"', content, re.MULTILINE)
        if not match:
            raise ValueError("Could not find version in pyproject.toml")
        return match.group(1)

    def update_pyproject_version(self, new_version: str) -> None:
        """Update version in pyproject.toml."""
        content = self.pyproject_path.read_text()
        new_content = re.sub(
            r'^(version\s*=\s*)"[^"]+"',
            f'\\1"{new_version}"',
            content,
            count=1,
            flags=re.MULTILINE,
        )
        self.pyproject_path.write_text(new_content)

    def update_changelog(self, version: str, messages: list[str]) -> None:
        """Add entry to CHANGELOG.rst."""
        if not self.changelog_path.exists():
            print("  Warning: CHANGELOG.rst not found, skipping")
            return

        content = self.changelog_path.read_text()
        today = date.today().strftime("%Y-%m-%d")

        # Build the new entry
        header = f"django-fsm-rx {version} {today}"
        underline = "~" * len(header)
        entries = "\n".join(f"- {msg}" for msg in messages)
        new_entry = f"{header}\n{underline}\n\n{entries}\n\n\n"

        # Insert after the main title
        pattern = r"(Changelog\n=+\n\n)"
        if re.search(pattern, content):
            new_content = re.sub(pattern, f"\\1{new_entry}", content, count=1)
        else:
            new_content = f"Changelog\n=========\n\n{new_entry}{content}"

        self.changelog_path.write_text(new_content)

    def git_commit(self, version: str, messages: list[str]) -> None:
        """Create git commit with version changes."""
        # Stage changes
        files_to_add = ["pyproject.toml"]
        if self.changelog_path.exists():
            files_to_add.append("CHANGELOG.rst")

        subprocess.run(
            ["git", "add"] + files_to_add,
            cwd=self.project_root,
            check=True,
            capture_output=True,
        )

        # Build commit message
        commit_msg = f"Release {version}\n\n"
        if messages:
            commit_msg += "\n".join(f"- {msg}" for msg in messages)
            commit_msg += "\n"

        subprocess.run(
            ["git", "commit", "-m", commit_msg],
            cwd=self.project_root,
            check=True,
            capture_output=True,
        )

    def git_tag(self, version: str, messages: list[str]) -> None:
        """Create git tag (without 'v' prefix)."""
        tag_msg = f"Release {version}"
        if messages:
            tag_msg += "\n\n" + "\n".join(f"- {msg}" for msg in messages)

        subprocess.run(
            ["git", "tag", "-a", version, "-m", tag_msg],
            cwd=self.project_root,
            check=True,
            capture_output=True,
        )

    def git_push(self, version: str, branch: str = "main") -> None:
        """Push commits and tag to origin."""
        subprocess.run(
            ["git", "push", "origin", branch],
            cwd=self.project_root,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "push", "origin", version],
            cwd=self.project_root,
            check=True,
            capture_output=True,
        )


def find_project_root() -> Path | None:
    """Find the project root directory containing pyproject.toml."""
    # IMPORTANT: Check current working directory FIRST
    # This allows running from a temp directory with its own pyproject.toml
    cwd = Path.cwd()
    if (cwd / "pyproject.toml").exists():
        return cwd

    # Walk up from cwd
    current = cwd
    for _ in range(10):
        if (current / "pyproject.toml").exists():
            return current
        parent = current.parent
        if parent == current:
            break
        current = parent

    # Fallback: check parent of scripts directory (where script lives)
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    if (project_root / "pyproject.toml").exists():
        return project_root

    return None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Bump version, update changelog, commit, and tag",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s 5.1.4 -m "Add new feature"
  %(prog)s 5.1.4 -m "Fix bug" -m "Add feature" --push
  %(prog)s 5.1.4 -m "Test" --dry-run
        """,
    )
    parser.add_argument("version", help="New version number (e.g., 5.1.4)")
    parser.add_argument(
        "-m",
        "--message",
        action="append",
        dest="messages",
        required=True,
        help="Changelog entry (can be used multiple times)",
    )
    parser.add_argument(
        "--push",
        action="store_true",
        help="Push commits and tags to origin",
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
    parser.add_argument(
        "--branch",
        default="main",
        help="Branch to push (default: main)",
    )

    args = parser.parse_args()

    # Validate version format
    if not re.match(r"^\d+\.\d+\.\d+$", args.version):
        print(f"Error: Invalid version format: {args.version}. Expected: X.Y.Z")
        return 1

    # Find project root
    project_root = find_project_root()
    if not project_root:
        print("Error: Could not find pyproject.toml")
        return 1

    bumper = VersionBumper(project_root)

    # Get current version
    try:
        current_version = bumper.get_current_version()
    except ValueError as e:
        print(f"Error: {e}")
        return 1

    print(f"Project root: {project_root}")
    print(f"Current version: {current_version}")
    print(f"New version: {args.version}")

    if current_version == args.version:
        print(f"Error: Version {args.version} is already set")
        return 1

    if args.dry_run:
        print("\n=== DRY RUN ===\n")

    # Step 1: Update pyproject.toml
    print(f"\n1. Updating pyproject.toml: {current_version} -> {args.version}")
    if not args.dry_run:
        bumper.update_pyproject_version(args.version)
        print("   ✓ pyproject.toml updated")
    else:
        print("   Would update pyproject.toml")

    # Step 2: Update CHANGELOG.rst
    if not args.no_changelog:
        print(f"\n2. Adding changelog entry for {args.version}")
        if not args.dry_run:
            bumper.update_changelog(args.version, args.messages)
            print("   ✓ CHANGELOG.rst updated")
        else:
            print("   Would add changelog entry:")
            for msg in args.messages:
                print(f"     - {msg}")
    else:
        print("\n2. Skipping changelog (--no-changelog)")

    if args.no_commit:
        print(f"\n✓ Files updated for version {args.version}")
        print("Skipping commit and tag (--no-commit)")
        return 0

    # Step 3: Git commit
    print("\n3. Creating git commit")
    if not args.dry_run:
        bumper.git_commit(args.version, args.messages)
        print("   ✓ Committed changes")
    else:
        print(f"   Would commit with message: 'Release {args.version}'")

    # Step 4: Create git tag
    print(f"\n4. Creating git tag: {args.version}")
    if not args.dry_run:
        bumper.git_tag(args.version, args.messages)
        print(f"   ✓ Tag {args.version} created")
    else:
        print(f"   Would create tag: {args.version}")

    # Step 5: Push
    if args.push:
        print("\n5. Pushing to origin")
        if not args.dry_run:
            bumper.git_push(args.version, args.branch)
            print("   ✓ Pushed commits and tag to origin")
        else:
            print("   Would push commits and tag to origin")
    else:
        print("\n5. Skipping push (use --push to push automatically)")
        print("   To push manually:")
        print(f"     git push origin {args.branch}")
        print(f"     git push origin {args.version}")

    print(f"\n{'Would release' if args.dry_run else '✓ Released'} version {args.version}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
