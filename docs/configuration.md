# Configuration

Django FSM RX works out of the box with sensible defaults. All settings are optional and can be customized via the `DJANGO_FSM_RX` dictionary in your Django settings.

## Settings Overview

```python
# settings.py
DJANGO_FSM_RX = {
    'ATOMIC': True,                    # Wrap transitions in database transactions
    'AUDIT_LOG': True,                 # Enable automatic audit logging
    'AUDIT_LOG_MODE': 'transaction',   # 'transaction' or 'signal'
    'AUDIT_LOG_MODEL': None,           # Custom audit log model (dotted path)
    'PROTECTED_FIELDS': False,         # Default for FSMField protected parameter
}
```

## Settings Reference

| Setting | Default | Description |
|---------|---------|-------------|
| `ATOMIC` | `True` | Wrap transitions in `transaction.atomic()`. Ensures state changes and related DB operations roll back together on failure. |
| `AUDIT_LOG` | `True` | Automatically log all state transitions to `FSMTransitionLog`. |
| `AUDIT_LOG_MODE` | `'transaction'` | How audit logs are created. See [Audit Log Modes](#audit-log-modes). |
| `AUDIT_LOG_MODEL` | `None` | Use a custom model for audit logs. See [Custom Audit Log Model](#custom-audit-log-model). |
| `PROTECTED_FIELDS` | `False` | Default value for `protected` parameter on `FSMField`. When `True`, direct field assignment raises an exception. |

## Audit Logging

By default, django-fsm-rx automatically logs all state transitions to the `FSMTransitionLog` model. This provides a complete audit trail of all state changes in your application.

### Audit Log Modes

#### Transaction Mode (Default, Recommended)

```python
DJANGO_FSM_RX = {
    'AUDIT_LOG_MODE': 'transaction',
}
```

In transaction mode, the audit log is created **inside** the atomic transaction block. This means:

- If the transition succeeds but later code fails, both the state change and the audit log roll back together
- Data consistency is guaranteed - you never have audit logs for transitions that didn't persist
- This is the safest option for most applications

#### Signal Mode

```python
DJANGO_FSM_RX = {
    'AUDIT_LOG_MODE': 'signal',
}
```

In signal mode, the audit log is created via the `post_transition` signal, **after** the transition completes. This means:

- Audit logs are created even if later code fails (outside the transition's atomic block)
- Useful when you want to log attempted transitions regardless of final outcome
- May result in audit logs for transitions that were rolled back

### Disabling Audit Logging

```python
DJANGO_FSM_RX = {
    'AUDIT_LOG': False,
}
```

### Custom Audit Log Model

If you need additional fields on your audit logs (e.g., user tracking, IP address, custom metadata), you can use your own model:

```python
# settings.py
DJANGO_FSM_RX = {
    'AUDIT_LOG_MODEL': 'myapp.TransitionLog',
}
```

Your custom model must have these required fields:

```python
# myapp/models.py
from django.db import models
from django.contrib.contenttypes.models import ContentType

class TransitionLog(models.Model):
    # Required fields (must match these names and types)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.TextField()
    transition_name = models.CharField(max_length=255)
    source_state = models.CharField(max_length=255)
    target_state = models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True)

    # Add your custom fields
    user = models.ForeignKey(
        'auth.User',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text="User who triggered the transition"
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    notes = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['-timestamp']),
        ]

    def __str__(self):
        return f"{self.content_type} #{self.object_id}: {self.source_state} → {self.target_state}"
```

## Atomic Transactions

By default, all transitions are wrapped in `transaction.atomic()`:

```python
DJANGO_FSM_RX = {
    'ATOMIC': True,  # Default
}
```

This ensures that:
- State changes and any database operations in the transition method are atomic
- If an exception is raised, everything rolls back
- `on_success` callbacks run inside the transaction (roll back together)
- `on_commit` callbacks run after the transaction commits

### Disabling Atomic Transactions

```python
DJANGO_FSM_RX = {
    'ATOMIC': False,  # Not recommended
}
```

**Warning**: Disabling atomic transactions may lead to inconsistent state if errors occur during transitions.

You can also control this per-transition:

```python
@transition(field=state, source='draft', target='published', atomic=False)
def publish(self):
    pass
```

## Protected Fields

The `PROTECTED_FIELDS` setting controls the default behavior for direct field assignment:

```python
# Default: allow direct assignment (for backwards compatibility)
DJANGO_FSM_RX = {
    'PROTECTED_FIELDS': False,
}

# Recommended for new projects: enforce transitions
DJANGO_FSM_RX = {
    'PROTECTED_FIELDS': True,
}
```

When `PROTECTED_FIELDS` is `True`:

```python
order = Order()
order.state = 'shipped'  # Raises AttributeError!
order.ship()  # Must use transitions
```

You can override per-field:

```python
class Order(models.Model):
    # Uses global default
    status = FSMField(default='pending')

    # Explicitly protected
    payment_state = FSMField(default='unpaid', protected=True)

    # Explicitly unprotected
    internal_state = FSMField(default='new', protected=False)
```

## Accessing Settings Programmatically

You can access the current settings in your code:

```python
from django_fsm_rx import fsm_rx_settings

if fsm_rx_settings.AUDIT_LOG:
    print("Audit logging is enabled")

print(f"Audit mode: {fsm_rx_settings.AUDIT_LOG_MODE}")
```

## Environment-Specific Configuration

A common pattern is to use different settings for different environments:

```python
# settings/base.py
DJANGO_FSM_RX = {
    'ATOMIC': True,
    'AUDIT_LOG': True,
    'AUDIT_LOG_MODE': 'transaction',
}

# settings/development.py
from .base import *

# Keep audit logging in dev for debugging
DJANGO_FSM_RX = {
    **DJANGO_FSM_RX,
    'AUDIT_LOG_MODE': 'signal',  # See all attempts, even failed ones
}

# settings/testing.py
from .base import *

# Disable audit logging in tests for speed
DJANGO_FSM_RX = {
    **DJANGO_FSM_RX,
    'AUDIT_LOG': False,
}

# settings/production.py
from .base import *

# Production uses defaults (transaction mode, audit enabled)
```
