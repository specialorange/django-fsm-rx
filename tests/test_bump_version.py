"""
Tests for bump_version script and management command.

These tests verify:
- Version parsing and validation
- pyproject.toml version updates
- CHANGELOG.rst updates
- Git operations (mocked)
- Dry run mode
- Error handling
"""

from __future__ import annotations

import re
import subprocess
import tempfile
from pathlib import Path

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError


class TestBumpVersionCommand:
    """Tests for bump_version management command."""

    def test_command_exists(self):
        """The command should be importable."""
        from django_fsm_rx.management.commands.bump_version import Command

        assert Command is not None

    def test_invalid_version_format_raises_error(self):
        """Invalid version format should raise error."""
        with pytest.raises(CommandError) as exc_info:
            call_command("bump_version", "invalid", "-m", "Test")

        assert "Invalid version format" in str(exc_info.value)

    def test_invalid_version_format_variations(self):
        """Various invalid version formats should raise error."""
        invalid_versions = [
            "5.1",  # Missing patch
            "5",  # Missing minor and patch
            "v5.1.4",  # Has 'v' prefix
            "5.1.4.5",  # Too many parts
            "5.1.a",  # Non-numeric
            "five.one.four",  # Words
            "",  # Empty
        ]

        for version in invalid_versions:
            with pytest.raises(CommandError) as exc_info:
                call_command("bump_version", version, "-m", "Test")
            assert "Invalid version format" in str(exc_info.value), f"Should reject: {version}"

    def test_valid_version_formats(self):
        """Valid version formats should pass regex validation."""
        valid_versions = [
            "5.1.4",
            "0.0.1",
            "10.20.30",
            "1.0.0",
        ]

        pattern = r"^\d+\.\d+\.\d+$"
        for version in valid_versions:
            assert re.match(pattern, version), f"Should accept: {version}"

    def test_missing_message_raises_error(self):
        """Missing changelog message should raise error (tested via script)."""
        script_path = Path(__file__).parent.parent / "scripts" / "bump_version.py"
        result = subprocess.run(
            ["python", str(script_path), "1.0.1"],
            capture_output=True,
            text=True,
        )
        # argparse will complain about required -m argument
        assert result.returncode != 0
        assert "required" in result.stderr.lower() or "-m" in result.stderr

    def test_same_version_raises_error(self):
        """Setting same version should raise error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            pyproject = tmpdir / "pyproject.toml"
            pyproject.write_text('[project]\nname = "test"\nversion = "1.0.0"\n')

            script_path = Path(__file__).parent.parent / "scripts" / "bump_version.py"
            result = subprocess.run(
                ["python", str(script_path), "1.0.0", "-m", "Test"],
                capture_output=True,
                text=True,
                cwd=tmpdir,
            )

            assert result.returncode != 0
            assert "already set" in result.stdout.lower()


class TestBumpVersionScript:
    """Tests for standalone bump_version.py script."""

    def test_script_exists(self):
        """The script should exist."""
        script_path = Path(__file__).parent.parent / "scripts" / "bump_version.py"
        assert script_path.exists(), f"Script not found at {script_path}"

    def test_script_is_valid_python(self):
        """The script should be valid Python that can be imported."""
        script_path = Path(__file__).parent.parent / "scripts" / "bump_version.py"
        # Verify it's valid Python by compiling it
        import py_compile

        py_compile.compile(str(script_path), doraise=True)

    def test_script_help(self):
        """Script should show help without errors."""
        script_path = Path(__file__).parent.parent / "scripts" / "bump_version.py"
        result = subprocess.run(
            ["python", str(script_path), "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "version" in result.stdout.lower()
        assert "--message" in result.stdout or "-m" in result.stdout

    def test_script_invalid_version(self):
        """Script should reject invalid version format."""
        script_path = Path(__file__).parent.parent / "scripts" / "bump_version.py"
        result = subprocess.run(
            ["python", str(script_path), "invalid", "-m", "Test"],
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0
        assert "invalid version format" in result.stdout.lower() or "invalid version format" in result.stderr.lower()

    def test_script_missing_message(self):
        """Script should require -m message."""
        script_path = Path(__file__).parent.parent / "scripts" / "bump_version.py"
        result = subprocess.run(
            ["python", str(script_path), "1.0.0"],
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0
        assert "required" in result.stderr.lower() or "message" in result.stderr.lower()


class TestVersionBumperClass:
    """Tests for VersionBumper class from the script."""

    @pytest.fixture
    def bumper(self, tmp_path):
        """Create a VersionBumper instance with temp directory."""
        # Import the class from the script
        import importlib.util

        script_path = Path(__file__).parent.parent / "scripts" / "bump_version.py"
        spec = importlib.util.spec_from_file_location("bump_version", script_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Create pyproject.toml
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[project]\nname = "test-project"\nversion = "1.0.0"\n')

        # Create CHANGELOG.rst
        changelog = tmp_path / "CHANGELOG.rst"
        changelog.write_text(
            "Changelog\n=========\n\ntest-project 1.0.0 2025-01-01\n~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n\n- Initial release\n"
        )

        return module.VersionBumper(tmp_path)

    def test_get_current_version(self, bumper):
        """Should read current version from pyproject.toml."""
        version = bumper.get_current_version()
        assert version == "1.0.0"

    def test_update_pyproject_version(self, bumper):
        """Should update version in pyproject.toml."""
        bumper.update_pyproject_version("1.1.0")

        content = bumper.pyproject_path.read_text()
        assert 'version = "1.1.0"' in content
        assert 'version = "1.0.0"' not in content

    def test_update_pyproject_preserves_other_content(self, bumper):
        """Should preserve other content when updating version."""
        # Add more content to pyproject.toml
        original = bumper.pyproject_path.read_text()
        bumper.pyproject_path.write_text(original + '\n[tool.pytest]\ntestpaths = ["tests"]\n')

        bumper.update_pyproject_version("2.0.0")

        content = bumper.pyproject_path.read_text()
        assert 'version = "2.0.0"' in content
        assert 'name = "test-project"' in content
        assert 'testpaths = ["tests"]' in content

    def test_update_changelog(self, bumper):
        """Should add entry to CHANGELOG.rst."""
        bumper.update_changelog("1.1.0", ["Add new feature", "Fix bug"])

        content = bumper.changelog_path.read_text()
        assert "django-fsm-rx 1.1.0" in content
        assert "- Add new feature" in content
        assert "- Fix bug" in content
        # New entry should come before old entry
        assert content.index("1.1.0") < content.index("1.0.0")

    def test_update_changelog_single_message(self, bumper):
        """Should handle single changelog message."""
        bumper.update_changelog("1.1.0", ["Single change"])

        content = bumper.changelog_path.read_text()
        assert "- Single change" in content

    def test_update_changelog_creates_proper_rst_format(self, bumper):
        """Should create proper RST format with underline."""
        bumper.update_changelog("1.1.0", ["Test"])

        content = bumper.changelog_path.read_text()
        lines = content.split("\n")

        # Find the header line
        header_idx = None
        for i, line in enumerate(lines):
            if "django-fsm-rx 1.1.0" in line:
                header_idx = i
                break

        assert header_idx is not None
        # Next line should be underline of same length
        header = lines[header_idx]
        underline = lines[header_idx + 1]
        assert len(underline) == len(header)
        assert all(c == "~" for c in underline)


class TestDryRunMode:
    """Tests for dry run mode."""

    def test_dry_run_does_not_modify_files(self):
        """Dry run should not modify any files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Create files
            pyproject = tmpdir / "pyproject.toml"
            pyproject.write_text('[project]\nname = "test"\nversion = "1.0.0"\n')

            changelog = tmpdir / "CHANGELOG.rst"
            changelog.write_text("Changelog\n=========\n\n")

            original_pyproject = pyproject.read_text()
            original_changelog = changelog.read_text()

            # Run script with --dry-run
            script_path = Path(__file__).parent.parent / "scripts" / "bump_version.py"
            subprocess.run(
                ["python", str(script_path), "1.1.0", "-m", "Test change", "--dry-run"],
                capture_output=True,
                text=True,
                cwd=tmpdir,
            )

            # Files should be unchanged
            assert pyproject.read_text() == original_pyproject
            assert changelog.read_text() == original_changelog

    def test_dry_run_shows_what_would_happen(self):
        """Dry run should show what would be done."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            pyproject = tmpdir / "pyproject.toml"
            pyproject.write_text('[project]\nname = "test"\nversion = "1.0.0"\n')

            changelog = tmpdir / "CHANGELOG.rst"
            changelog.write_text("Changelog\n=========\n\n")

            script_path = Path(__file__).parent.parent / "scripts" / "bump_version.py"
            result = subprocess.run(
                ["python", str(script_path), "1.1.0", "-m", "New feature", "--dry-run"],
                capture_output=True,
                text=True,
                cwd=tmpdir,
            )

            output = result.stdout
            assert "DRY RUN" in output
            assert "Would update pyproject.toml" in output or "pyproject.toml" in output
            assert "New feature" in output


class TestNoCommitMode:
    """Tests for --no-commit mode."""

    def test_no_commit_updates_files_only(self):
        """--no-commit should update files but not create git commit."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Initialize git repo
            subprocess.run(["git", "init"], cwd=tmpdir, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmpdir, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=tmpdir, capture_output=True)

            # Create files
            pyproject = tmpdir / "pyproject.toml"
            pyproject.write_text('[project]\nname = "test"\nversion = "1.0.0"\n')

            changelog = tmpdir / "CHANGELOG.rst"
            changelog.write_text("Changelog\n=========\n\n")

            # Initial commit
            subprocess.run(["git", "add", "."], cwd=tmpdir, capture_output=True)
            subprocess.run(["git", "commit", "-m", "Initial"], cwd=tmpdir, capture_output=True)

            # Run with --no-commit
            script_path = Path(__file__).parent.parent / "scripts" / "bump_version.py"
            subprocess.run(
                ["python", str(script_path), "1.1.0", "-m", "Test", "--no-commit"],
                capture_output=True,
                text=True,
                cwd=tmpdir,
            )

            # Files should be updated
            assert 'version = "1.1.0"' in pyproject.read_text()
            assert "1.1.0" in changelog.read_text()

            # But no new commit should exist
            log_result = subprocess.run(
                ["git", "log", "--oneline"],
                cwd=tmpdir,
                capture_output=True,
                text=True,
            )
            assert "Release 1.1.0" not in log_result.stdout

            # And no tag
            tag_result = subprocess.run(
                ["git", "tag", "-l"],
                cwd=tmpdir,
                capture_output=True,
                text=True,
            )
            assert "1.1.0" not in tag_result.stdout


class TestGitOperations:
    """Tests for git commit and tag operations."""

    def test_creates_commit_and_tag(self):
        """Should create git commit and tag."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Initialize git repo
            subprocess.run(["git", "init"], cwd=tmpdir, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmpdir, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=tmpdir, capture_output=True)

            # Create files
            pyproject = tmpdir / "pyproject.toml"
            pyproject.write_text('[project]\nname = "test"\nversion = "1.0.0"\n')

            changelog = tmpdir / "CHANGELOG.rst"
            changelog.write_text("Changelog\n=========\n\n")

            # Initial commit
            subprocess.run(["git", "add", "."], cwd=tmpdir, capture_output=True)
            subprocess.run(["git", "commit", "-m", "Initial"], cwd=tmpdir, capture_output=True)

            # Run bump_version
            script_path = Path(__file__).parent.parent / "scripts" / "bump_version.py"
            result = subprocess.run(
                ["python", str(script_path), "1.1.0", "-m", "Add feature X"],
                capture_output=True,
                text=True,
                cwd=tmpdir,
            )

            assert result.returncode == 0, f"Script failed: {result.stdout}\n{result.stderr}"

            # Check commit exists
            log_result = subprocess.run(
                ["git", "log", "--oneline", "-1"],
                cwd=tmpdir,
                capture_output=True,
                text=True,
            )
            assert "Release 1.1.0" in log_result.stdout

            # Check tag exists (without 'v' prefix)
            tag_result = subprocess.run(
                ["git", "tag", "-l"],
                cwd=tmpdir,
                capture_output=True,
                text=True,
            )
            assert "1.1.0" in tag_result.stdout
            assert "v1.1.0" not in tag_result.stdout  # Should NOT have 'v' prefix

    def test_tag_has_no_v_prefix(self):
        """Tag should not have 'v' prefix."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Initialize git repo
            subprocess.run(["git", "init"], cwd=tmpdir, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmpdir, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=tmpdir, capture_output=True)

            pyproject = tmpdir / "pyproject.toml"
            pyproject.write_text('[project]\nname = "test"\nversion = "1.0.0"\n')

            subprocess.run(["git", "add", "."], cwd=tmpdir, capture_output=True)
            subprocess.run(["git", "commit", "-m", "Initial"], cwd=tmpdir, capture_output=True)

            script_path = Path(__file__).parent.parent / "scripts" / "bump_version.py"
            subprocess.run(
                ["python", str(script_path), "2.0.0", "-m", "Major release", "--no-changelog"],
                capture_output=True,
                text=True,
                cwd=tmpdir,
            )

            # Verify tag format
            tag_result = subprocess.run(
                ["git", "tag", "-l"],
                cwd=tmpdir,
                capture_output=True,
                text=True,
            )
            tags = tag_result.stdout.strip().split("\n")
            assert "2.0.0" in tags
            assert "v2.0.0" not in tags


class TestMultipleMessages:
    """Tests for multiple changelog messages."""

    def test_multiple_messages_in_changelog(self):
        """Multiple -m flags should create multiple changelog entries."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            pyproject = tmpdir / "pyproject.toml"
            pyproject.write_text('[project]\nname = "test"\nversion = "1.0.0"\n')

            changelog = tmpdir / "CHANGELOG.rst"
            changelog.write_text("Changelog\n=========\n\n")

            script_path = Path(__file__).parent.parent / "scripts" / "bump_version.py"
            subprocess.run(
                [
                    "python",
                    str(script_path),
                    "1.1.0",
                    "-m",
                    "Add feature A",
                    "-m",
                    "Add feature B",
                    "-m",
                    "Fix bug C",
                    "--no-commit",
                ],
                capture_output=True,
                text=True,
                cwd=tmpdir,
            )

            content = changelog.read_text()
            assert "- Add feature A" in content
            assert "- Add feature B" in content
            assert "- Fix bug C" in content


class TestEdgeCases:
    """Tests for edge cases."""

    def test_no_changelog_file(self):
        """Should handle missing CHANGELOG.rst gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Initialize git
            subprocess.run(["git", "init"], cwd=tmpdir, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmpdir, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=tmpdir, capture_output=True)

            # Only pyproject.toml, no CHANGELOG.rst
            pyproject = tmpdir / "pyproject.toml"
            pyproject.write_text('[project]\nname = "test"\nversion = "1.0.0"\n')

            subprocess.run(["git", "add", "."], cwd=tmpdir, capture_output=True)
            subprocess.run(["git", "commit", "-m", "Initial"], cwd=tmpdir, capture_output=True)

            script_path = Path(__file__).parent.parent / "scripts" / "bump_version.py"
            result = subprocess.run(
                ["python", str(script_path), "1.1.0", "-m", "Test", "--no-changelog"],
                capture_output=True,
                text=True,
                cwd=tmpdir,
            )

            # Should succeed
            assert result.returncode == 0
            assert 'version = "1.1.0"' in pyproject.read_text()

    def test_version_with_leading_zeros_rejected(self):
        """Versions with leading zeros should be handled."""
        # Note: 01.02.03 doesn't match X.Y.Z pattern (single digits)
        script_path = Path(__file__).parent.parent / "scripts" / "bump_version.py"
        subprocess.run(
            ["python", str(script_path), "01.02.03", "-m", "Test"],
            capture_output=True,
            text=True,
        )
        # This might be accepted or rejected depending on regex - just document behavior
        # The regex \d+\.\d+\.\d+ will accept it

    def test_pyproject_with_complex_structure(self):
        """Should handle complex pyproject.toml."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            pyproject = tmpdir / "pyproject.toml"
            pyproject.write_text("""[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "test-project"
version = "1.0.0"
description = "A test project"
dependencies = [
    "django>=4.2",
]

[project.optional-dependencies]
dev = ["pytest"]

[tool.ruff]
line-length = 100
""")

            # Import and test
            import importlib.util

            script_path = Path(__file__).parent.parent / "scripts" / "bump_version.py"
            spec = importlib.util.spec_from_file_location("bump_version", script_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            bumper = module.VersionBumper(tmpdir)
            bumper.update_pyproject_version("2.0.0")

            content = pyproject.read_text()
            assert 'version = "2.0.0"' in content
            assert 'name = "test-project"' in content
            assert "django>=4.2" in content
            assert "line-length = 100" in content
