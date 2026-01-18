# Migration Guide

This guide covers migrating to django-fsm-rx from other FSM packages.

django-fsm-rx provides full backwards compatibility with django-fsm, django-fsm-2, django-fsm-admin, and django-fsm-log. Your existing code will work with deprecation warnings guiding you to update imports.

## Quick Migration Check

### Management Command

Run the built-in migration check command to find deprecated imports in your project:

```bash
python manage.py check_fsm_migration
```

This scans your codebase and shows exactly what imports need updating:

```
Files affected: 3
Deprecated imports found: 5

myapp/models.py:
  Line 1:
    - from django_fsm import FSMField, transition
    + from django_fsm_rx import FSMField, transition

myapp/admin.py:
  Line 2:
    - from django_fsm_admin.mixins import FSMTransitionMixin
    + from django_fsm_rx.admin import FSMAdminMixin
```

### Command Options

| Option | Description |
|--------|-------------|
| `--path /path/to/scan` | Scan a specific directory (default: BASE_DIR) |
| `--exclude migrations,tests` | Comma-separated patterns to exclude |
| `--verbose` | Show detailed migration notes |
| `--json` | Output as JSON for CI/automation |

### JSON Output for CI

For CI integration, use JSON output:

```bash
python manage.py check_fsm_migration --json > migration_report.json
```

Example JSON output:

```json
{
  "is_fully_migrated": false,
  "files_affected": ["myapp/models.py", "myapp/admin.py"],
  "deprecated_imports": [
    {
      "file": "myapp/models.py",
      "line": 1,
      "old": "from django_fsm import FSMField",
      "new": "from django_fsm_rx import FSMField",
      "notes": "Direct replacement, API identical"
    }
  ],
  "warnings": [],
  "suggested_changes": {
    "from django_fsm import FSMField": "from django_fsm_rx import FSMField"
  }
}
```

## From django-fsm-2

[django-fsm-2](https://github.com/django-commons/django-fsm-2) is a maintained fork of django-fsm under Django Commons. Migration is straightforward since django-fsm-rx maintains API compatibility.

### Step 1: Install the new package

```bash
pip uninstall django-fsm-2
pip install django-fsm-rx
```

### Step 2: Update INSTALLED_APPS

```python
# settings.py
INSTALLED_APPS = [
    ...,
    'django_fsm_rx',
    ...,
]
```

### Step 3: Run migrations

```bash
python manage.py migrate django_fsm_rx
```

This creates the `FSMTransitionLog` table for audit logging.

### Step 4: Update imports (recommended)

Your existing imports will continue to work with a deprecation warning:

```python
# Old (still works, shows deprecation warning)
from django_fsm_2 import FSMField, transition

# New (recommended)
from django_fsm_rx import FSMField, transition
```

### API Compatibility

All core APIs from django-fsm-2 are fully compatible:

| Feature | Status | Notes |
|---------|--------|-------|
| `FSMField`, `FSMIntegerField`, `FSMKeyField` | Identical | |
| `@transition` decorator | Compatible | New optional params: `on_success`, `on_commit`, `atomic` |
| `can_proceed()`, `has_transition_perm()` | Identical | |
| `ConcurrentTransitionMixin`, `FSMModelMixin` | Identical | |
| `RETURN_VALUE`, `GET_STATE` | Identical | |
| `pre_transition`, `post_transition` signals | Identical | |
| Wildcard sources (`*`, `+`) | Identical | |
| Prefix wildcards (`WRK-*`) | **New** | Matches `WRK-REP-PRG`, `WRK-INS-PRG`, etc. |

### New Features

django-fsm-rx adds these optional features:

- **Automatic audit logging** - All transitions logged to `FSMTransitionLog`
- **`on_success` callback** - Runs inside transaction, rolls back together
- **`on_commit` callback** - Runs after commit (for emails, external APIs)
- **`atomic=True` default** - Transitions wrapped in `transaction.atomic()`

### Opting out of new defaults

To get behavior identical to django-fsm-2:

```python
# settings.py
DJANGO_FSM_RX = {
    'AUDIT_LOG': False,  # Disable audit logging
    'ATOMIC': False,     # Disable transaction wrapping (not recommended)
}
```

## From django-fsm

[django-fsm](https://github.com/viewflow/django-fsm) is the original FSM package by Mikhail Podgurskiy (now archived).

```bash
pip uninstall django-fsm
pip install django-fsm-rx
```

Follow the same steps as "From django-fsm-2" above. Your `from django_fsm import ...` imports will also continue to work with a deprecation warning.

## From django-fsm-log

[django-fsm-log](https://github.com/jazzband/django-fsm-log) provides transition logging for django-fsm. django-fsm-rx includes built-in audit logging that can replace django-fsm-log.

### Your Data is Preserved

```{important}
**Your existing transition logs are safe!** The `StateLog` compatibility shim reads directly from your existing `django_fsm_log_statelog` table. No data migration is required.
```

### Step 1: Install django-fsm-rx

```bash
pip uninstall django-fsm-log
pip install django-fsm-rx
```

### Step 2: Update INSTALLED_APPS

```python
# settings.py
INSTALLED_APPS = [
    ...,
    'django_fsm_rx',  # This is all you need
    # 'django_fsm_log',  # Remove - no longer needed
    ...,
]
```

```{note}
You do **NOT** need to add `django_fsm_log` to INSTALLED_APPS. The compatibility shim is built into django-fsm-rx - just add `django_fsm_rx` and your existing `from django_fsm_log.models import StateLog` imports will continue to work automatically.
```

### Step 3: Run migrations

```bash
python manage.py migrate django_fsm_rx
```

This creates the new `FSMTransitionLog` table for future transitions. Your existing data in `django_fsm_log_statelog` remains untouched.

### Step 4: That's it!

Your existing code using `StateLog` will continue to work:

```python
# This still works - reads from your existing django_fsm_log_statelog table
from django_fsm_log.models import StateLog

# Query your existing logs
logs = StateLog.objects.filter(content_type__model='order')
for log in logs:
    print(f"{log.transition}: {log.source_state} -> {log.state}")
```

The `StateLog` model provides property aliases for the new field names:

```python
# Both work:
log.state          # Original field name
log.target_state   # Alias matching FSMTransitionLog API

log.transition       # Original field name
log.transition_name  # Alias matching FSMTransitionLog API
```

### New Transitions

New transitions are logged to `FSMTransitionLog` (the new table) by default. If you want to query both old and new logs, you can:

```python
from django_fsm_log.models import StateLog  # Old logs
from django_fsm_rx import FSMTransitionLog  # New logs

# Query old logs
old_logs = StateLog.objects.filter(...)

# Query new logs
new_logs = FSMTransitionLog.objects.filter(...)
```

### Optional: Migrate Data to New Table

If you want to consolidate all logs into the new `FSMTransitionLog` table, you can optionally migrate the data:

```python
# One-time migration script (run in Django shell or as a management command)
from django.db import connection

with connection.cursor() as cursor:
    # Check if old table exists and has data
    cursor.execute("""
        SELECT COUNT(*) FROM django_fsm_log_statelog
    """)
    count = cursor.fetchone()[0]

    if count == 0:
        print("No data to migrate")
    else:
        # Migrate data to new table
        cursor.execute("""
            INSERT INTO django_fsm_rx_fsmtransitionlog
                (content_type_id, object_id, transition_name, source_state, target_state, timestamp, by_id, description)
            SELECT
                content_type_id,
                object_id::text,
                transition,
                COALESCE(source_state, ''),
                state,
                timestamp,
                by_id,
                COALESCE(description, '')
            FROM django_fsm_log_statelog
        """)
        print(f"Migrated {cursor.rowcount} records to FSMTransitionLog")
```

After migrating and verifying the data:

```python
# Verify migration
from django_fsm_rx import FSMTransitionLog
print(f"New table has {FSMTransitionLog.objects.count()} records")
```

```{warning}
**Do not delete the old table until you have verified the migration.** The old `django_fsm_log_statelog` table contains your historical data. Only delete it after confirming all records were migrated successfully.
```

To delete the old table after verification (optional):

```sql
-- Only run after verifying migration!
DROP TABLE django_fsm_log_statelog;
```

### Field Mapping

| django-fsm-log `StateLog` | django-fsm-rx `FSMTransitionLog` |
|---------------------------|----------------------------------|
| `content_type` | `content_type` |
| `object_id` (PositiveIntegerField) | `object_id` (TextField) |
| `transition` | `transition_name` |
| `source_state` | `source_state` |
| `state` | `target_state` |
| `timestamp` | `timestamp` |
| `by` | `by` |
| `description` | `description` |

### Decorators

The `@fsm_log_by` and `@fsm_log_description` decorators are available for compatibility:

```python
from django_fsm_rx.log import fsm_log_by, fsm_log_description

@fsm_log_by
@fsm_log_description
@transition(field=state, source='draft', target='published')
def publish(self, by=None, description=None):
    pass
```

However, with audit logging enabled (default), you may not need these decorators - transitions are automatically logged.

### Differences from django-fsm-log

| Feature | django-fsm-log | django-fsm-rx |
|---------|----------------|---------------|
| Model name | `StateLog` | `FSMTransitionLog` (with `StateLog` shim) |
| Table | `django_fsm_log_statelog` | `django_fsm_rx_fsmtransitionlog` |
| StateLog shim | N/A | Reads from original table (no migration needed) |
| Requires INSTALLED_APPS | Yes | No (for shim), Yes (for new model) |
| Automatic logging | Via signal | Via `AUDIT_LOG` setting (default: True) |
| Log modes | Signal only | `transaction` (default) or `signal` |

## From django-fsm-admin / django-fsm-2-admin

[django-fsm-admin](https://github.com/gadventures/django-fsm-admin) and [django-fsm-2-admin](https://github.com/coral-li/django-fsm-2-admin) provide Django admin integration for django-fsm and django-fsm-2 respectively. django-fsm-rx includes built-in admin support.

### Step 1: Install django-fsm-rx

```bash
pip uninstall django-fsm-admin  # or django-fsm-2-admin
pip install django-fsm-rx
```

### Step 2: Update admin imports

```python
# Old (django-fsm-admin or django-fsm-2-admin)
from fsm_admin.mixins import FSMTransitionMixin

# New
from django_fsm_rx.admin import FSMAdminMixin
# Or use the compatibility alias:
from django_fsm_rx.admin import FSMTransitionMixin  # Alias for FSMAdminMixin
```

### Step 3: Update admin classes

```python
from django.contrib import admin
from django_fsm_rx.admin import FSMAdminMixin

@admin.register(BlogPost)
class BlogPostAdmin(FSMAdminMixin, admin.ModelAdmin):
    fsm_fields = ['state']  # List your FSM fields
    list_display = ['title', 'state']
```

### Admin Features

django-fsm-rx's admin integration provides:

- **Transition buttons** - Execute transitions from the change form
- **Custom labels** - Use `custom={'label': 'Publish'}` on transitions
- **Form support** - Transitions with forms via `custom={'form': MyForm}`
- **Visibility control** - Hide transitions with `custom={'admin': False}`
- **FSM_ADMIN_FORCE_PERMIT** - Require explicit `custom={'admin': True}`

See the [Admin Integration](admin.md) guide for full documentation.

## Compatibility Shims

django-fsm-rx provides backwards compatibility shims for seamless migration:

| Import Path | Status | Notes |
|-------------|--------|-------|
| `from django_fsm import ...` | Works with deprecation warning | Shim for django-fsm |
| `from django_fsm_2 import ...` | Works with deprecation warning | Shim for django-fsm-2 |
| `from django_fsm_log.models import StateLog` | Works (alias to FSMTransitionLog) | Shim for django-fsm-log |
| `from django_fsm_rx.admin import FSMTransitionMixin` | Works (alias to FSMAdminMixin) | Shim for django-fsm-admin |

These shims allow gradual migration - update imports at your own pace.

**Note:** The shims for `django_fsm` and `django_fsm_2` are full package shims included in the django-fsm-rx distribution. The `django_fsm_log` shim provides `StateLog` as an alias. The `FSMTransitionMixin` alias is for django-fsm-admin/django-fsm-2-admin compatibility (these were separate packages, not part of django-fsm-2 core).

## Programmatic Migration Utilities

For automated migration, CI integration, or custom tooling, use the migration utilities programmatically:

### Scanning for Deprecated Imports

```python
from django_fsm_rx.migration import (
    scan_imports_in_file,
    scan_imports_in_directory,
    MigrationReport,
)

# Scan a single file
report = scan_imports_in_file('myapp/models.py')

# Scan a directory (recursive)
report = scan_imports_in_directory(
    '/path/to/project',
    exclude_patterns=['migrations', '__pycache__', 'venv']
)

# Check results
if report.is_fully_migrated:
    print("No deprecated imports found!")
else:
    print(f"Files to update: {len(report.files_affected)}")
    for item in report.deprecated_imports:
        print(f"  {item['file']}:{item['line']}")
        print(f"    OLD: {item['old']}")
        print(f"    NEW: {item['new']}")
        if item['notes']:
            print(f"    NOTE: {item['notes']}")
```

### Model Validation

Validate that a model's FSM configuration is compatible:

```python
from django_fsm_rx.migration import validate_model_fsm_compatibility
from myapp.models import Order

warnings = validate_model_fsm_compatibility(Order)
for warning in warnings:
    print(f"Warning: {warning}")
```

This checks for:
- FSM fields are properly configured
- Transitions have the correct decorator metadata
- Protected fields have `FSMModelMixin` if needed

### Import Mappings

Get all import replacements as a dictionary:

```python
from django_fsm_rx.migration import get_import_replacements, IMPORT_MAPPINGS

# Get simple old->new mapping
replacements = get_import_replacements()
print(replacements['from django_fsm import FSMField'])
# Output: 'from django_fsm_rx import FSMField'

# Access detailed mappings with notes
for mapping in IMPORT_MAPPINGS:
    print(f"{mapping['old_module']}.{mapping['old_name']}")
    print(f"  -> {mapping['new_module']}.{mapping['new_name']}")
    print(f"  Note: {mapping['notes']}")
```

### Check Migration Status from Django Settings

```python
from django_fsm_rx.migration import check_migration_status

# Automatically finds BASE_DIR from Django settings
report = check_migration_status()
print(report)  # Human-readable report
```

### Using in CI/CD

Create a custom management command or script:

```python
# scripts/check_migration.py
import sys
from django_fsm_rx.migration import run_migration_check_command

if __name__ == '__main__':
    # Returns 0 if fully migrated, 1 if migration needed
    sys.exit(run_migration_check_command())
```

Or use the management command in CI:

```yaml
# .github/workflows/test.yml
- name: Check FSM migration
  run: python manage.py check_fsm_migration --json
```

## Complete Import Reference

### Core FSM (django-fsm / django-fsm-2)

| Old Import | New Import |
|------------|------------|
| `from django_fsm import FSMField` | `from django_fsm_rx import FSMField` |
| `from django_fsm import FSMIntegerField` | `from django_fsm_rx import FSMIntegerField` |
| `from django_fsm import FSMKeyField` | `from django_fsm_rx import FSMKeyField` |
| `from django_fsm import transition` | `from django_fsm_rx import transition` |
| `from django_fsm import can_proceed` | `from django_fsm_rx import can_proceed` |
| `from django_fsm import has_transition_perm` | `from django_fsm_rx import has_transition_perm` |
| `from django_fsm import TransitionNotAllowed` | `from django_fsm_rx import TransitionNotAllowed` |
| `from django_fsm import ConcurrentTransition` | `from django_fsm_rx import ConcurrentTransition` |
| `from django_fsm import ConcurrentTransitionMixin` | `from django_fsm_rx import ConcurrentTransitionMixin` |
| `from django_fsm import FSMModelMixin` | `from django_fsm_rx import FSMModelMixin` |
| `from django_fsm import RETURN_VALUE` | `from django_fsm_rx import RETURN_VALUE` |
| `from django_fsm import GET_STATE` | `from django_fsm_rx import GET_STATE` |
| `from django_fsm.signals import pre_transition` | `from django_fsm_rx.signals import pre_transition` |
| `from django_fsm.signals import post_transition` | `from django_fsm_rx.signals import post_transition` |

### Admin (django-fsm-admin)

| Old Import | New Import |
|------------|------------|
| `from django_fsm_admin.mixins import FSMTransitionMixin` | `from django_fsm_rx.admin import FSMAdminMixin` |
| `from django_fsm_admin import FSMTransitionMixin` | `from django_fsm_rx.admin import FSMAdminMixin` |

### Logging (django-fsm-log)

| Old Import | New Import |
|------------|------------|
| `from django_fsm_log.models import StateLog` | `from django_fsm_rx import FSMTransitionLog` |
| `from django_fsm_log.decorators import fsm_log_by` | `from django_fsm_rx.log import fsm_log_by` |
| `from django_fsm_log.decorators import fsm_log_description` | `from django_fsm_rx.log import fsm_log_description` |
| `from django_fsm_log import fsm_log_by` | `from django_fsm_rx.log import fsm_log_by` |
