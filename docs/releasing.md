# Releasing New Versions

This guide covers how to release new versions of django-fsm-rx.

## Quick Release

Use the `bump_version` script to handle all release tasks in one command:

```bash
python scripts/bump_version.py 5.1.4 -m "Add new feature" --push
```

This will:
1. Update version in `pyproject.toml`
2. Add changelog entry to `CHANGELOG.rst`
3. Create git commit
4. Create git tag (e.g., `5.1.4` - no 'v' prefix)
5. Push to origin (with `--push` flag)

## Usage

### Basic Release

```bash
# Preview what will happen (no changes made)
python scripts/bump_version.py 5.1.4 -m "Add new feature" --dry-run

# Create release locally (review before pushing)
python scripts/bump_version.py 5.1.4 -m "Add new feature"

# Create and push release
python scripts/bump_version.py 5.1.4 -m "Add new feature" --push
```

### Multiple Changelog Entries

Use multiple `-m` flags for multiple changelog entries:

```bash
python scripts/bump_version.py 5.1.4 \
    -m "Add migration utilities" \
    -m "Add check_fsm_migration management command" \
    -m "Fix bug in admin integration"
```

### Options

| Option | Description |
|--------|-------------|
| `-m "message"` | Changelog entry (required, can use multiple times) |
| `--push` | Push commits and tag to origin after creating |
| `--dry-run` | Show what would be done without making changes |
| `--no-commit` | Update files but don't commit or tag |
| `--no-changelog` | Skip changelog update |
| `--branch` | Branch to push (default: main) |

## Alternative: Django Management Command

If you have Django configured, you can also use the management command:

```bash
python manage.py bump_version 5.1.4 -m "Add new feature"
python manage.py bump_version 5.1.4 -m "Add new feature" --push
```

## Manual Release Process

If you prefer to release manually:

### 1. Update pyproject.toml

```toml
[project]
version = "5.1.4"  # Update this
```

### 2. Update CHANGELOG.rst

Add entry at the top (after the header):

```rst
django-fsm-rx 5.1.4 2025-01-18
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Add new feature
- Fix bug
```

### 3. Commit Changes

```bash
git add pyproject.toml CHANGELOG.rst
git commit -m "Release 5.1.4"
```

### 4. Create Tag

```bash
git tag -a 5.1.4 -m "Release 5.1.4"
```

Note: Tags do NOT use a 'v' prefix (use `5.1.4`, not `v5.1.4`).

### 5. Push

```bash
git push origin main
git push origin 5.1.4
```

## Version Numbering

This project follows [Semantic Versioning](https://semver.org/):

- **MAJOR** (X.0.0): Breaking changes
- **MINOR** (0.X.0): New features, backwards compatible
- **PATCH** (0.0.X): Bug fixes, backwards compatible

## Publishing to PyPI

After pushing the tag, the GitHub Actions workflow will automatically:
1. Build the package
2. Publish to PyPI

To publish manually:

```bash
uv build
uv publish
```

## Checklist

Before releasing:

- [ ] All tests pass (`uv run pytest`)
- [ ] Documentation is updated
- [ ] CHANGELOG has entry for new version
- [ ] Version number follows semver
