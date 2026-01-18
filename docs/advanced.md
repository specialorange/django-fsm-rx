# Advanced Features

## Hierarchical Status Codes

Django FSM RX provides first-class support for hierarchical (multi-level) status codes. This is useful when your workflow has categories, subcategories, and granular states that follow a consistent pattern.

### Why Hierarchical Status Codes?

Traditional flat status fields work well for simple workflows:

```
draft → review → published → archived
```

But real-world applications often need more granularity:

```
DRF-NEW-CRT    (Draft / New / Created)
DRF-NEW-EDT    (Draft / New / Edited)
REV-PND-WAT    (Review / Pending / Waiting)
REV-APR-DON    (Review / Approved / Done)
PUB-ACT-LIV    (Published / Active / Live)
```

Benefits of hierarchical codes:
- **Logical grouping** - Related states share prefixes (`REV-*` = all review states)
- **Granular tracking** - Know exactly where something is in the process
- **Flexible transitions** - Move between any state in a category with one transition
- **Reporting** - Easily query/filter by category (`status LIKE 'REV-%'`)

### Designing Your Status Codes

A common pattern is `CATEGORY-TYPE-STATUS` with 3-character codes:

```python
class Job(models.Model):
    """
    Status code format: AAA-BBB-CCC

    Categories (Level 1):
        DRF = Draft
        SCH = Scheduled
        WRK = Work in Progress
        QC  = Quality Control
        CMP = Complete
        CAN = Cancelled

    Types (Level 2):
        NEW = New
        REP = Repair
        INS = Inspection
        MNT = Maintenance

    Statuses (Level 3):
        CRT = Created
        PRG = In Progress
        HLD = On Hold
        DON = Done
        FAI = Failed
    """

    STATUS_CHOICES = [
        ('DRF-NEW-CRT', 'Draft - New - Created'),
        ('DRF-NEW-EDT', 'Draft - New - Edited'),
        ('SCH-REP-CRT', 'Scheduled - Repair - Created'),
        ('SCH-INS-CRT', 'Scheduled - Inspection - Created'),
        ('WRK-REP-PRG', 'Work - Repair - In Progress'),
        ('WRK-REP-HLD', 'Work - Repair - On Hold'),
        ('WRK-INS-PRG', 'Work - Inspection - In Progress'),
        ('QC-REP-PRG', 'QC - Repair - In Progress'),
        ('QC-REP-FAI', 'QC - Repair - Failed'),
        ('CMP-REP-DON', 'Complete - Repair - Done'),
        ('CMP-INS-DON', 'Complete - Inspection - Done'),
        ('CAN-ANY-CAN', 'Cancelled'),
    ]

    status = FSMField(default='DRF-NEW-CRT', choices=STATUS_CHOICES)
```

### Category Wildcards (Prefix Matching)

Use prefix wildcards to match any state starting with a pattern:

```python
from django_fsm_rx import FSMField, transition

class Job(models.Model):
    status = FSMField(default='DRF-NEW-CRT', choices=STATUS_CHOICES)

    # Match any status starting with "WRK-" (all Work in Progress states)
    @transition(field=status, source='WRK-*', target='CMP-STD-DON')
    def complete(self):
        """Complete any work in progress."""
        pass

    # Match any status starting with "WRK-REP-" (Work + Repair category)
    @transition(field=status, source='WRK-REP-*', target='QC-REP-PRG')
    def send_to_qc(self):
        """Send repair work to quality control."""
        pass

    # Match multiple category prefixes
    @transition(field=status, source=['SCH-*', 'DRF-*'], target='WRK-REP-PRG')
    def start_repair(self):
        """Start repair work from scheduled or draft status."""
        pass

    # Combine specific states with wildcards
    @transition(
        field=status,
        source=['WRK-*', 'QC-REP-FAI'],  # Any work state OR failed QC
        target='WRK-REP-HLD'
    )
    def put_on_hold(self):
        """Put job on hold."""
        pass
```

### Supported Source Patterns

| Pattern | Description | Example Match |
|---------|-------------|---------------|
| `'*'` | Any state | All states |
| `'+'` | Any state except target | All except target state |
| `'WRK-*'` | Prefix wildcard | `WRK-REP-PRG`, `WRK-INS-HLD` |
| `'WRK-REP-*'` | Multi-level prefix | `WRK-REP-PRG`, `WRK-REP-HLD` |
| `['A', 'B']` | Specific states | Only `A` or `B` |
| `['WRK-*', 'QC-*']` | Multiple wildcards | Any WRK or QC state |

### Complete Workflow Example

```python
from django.db import models
from django_fsm_rx import FSMField, FSMModelMixin, transition

class RepairOrder(FSMModelMixin, models.Model):
    """
    Repair order with hierarchical status tracking.

    Workflow:
    1. Created as draft (DRF-NEW-CRT)
    2. Scheduled for work (SCH-REP-CRT or SCH-INS-CRT)
    3. Work begins (WRK-*-PRG)
    4. Work can be paused (WRK-*-HLD) or completed
    5. QC review (QC-*-PRG)
    6. Complete (CMP-*-DON) or back to work if QC fails
    """

    STATUS_CHOICES = [
        # Draft states
        ('DRF-NEW-CRT', 'Draft - New - Created'),
        ('DRF-NEW-EDT', 'Draft - New - Edited'),

        # Scheduled states
        ('SCH-REP-CRT', 'Scheduled - Repair - Created'),
        ('SCH-INS-CRT', 'Scheduled - Inspection - Created'),
        ('SCH-MNT-CRT', 'Scheduled - Maintenance - Created'),

        # Work in progress states
        ('WRK-REP-PRG', 'Work - Repair - In Progress'),
        ('WRK-REP-HLD', 'Work - Repair - On Hold'),
        ('WRK-INS-PRG', 'Work - Inspection - In Progress'),
        ('WRK-INS-HLD', 'Work - Inspection - On Hold'),
        ('WRK-MNT-PRG', 'Work - Maintenance - In Progress'),

        # QC states
        ('QC-REP-PRG', 'QC - Repair - Review'),
        ('QC-REP-FAI', 'QC - Repair - Failed'),
        ('QC-INS-PRG', 'QC - Inspection - Review'),
        ('QC-MNT-PRG', 'QC - Maintenance - Review'),

        # Complete states
        ('CMP-REP-DON', 'Complete - Repair - Done'),
        ('CMP-INS-DON', 'Complete - Inspection - Done'),
        ('CMP-MNT-DON', 'Complete - Maintenance - Done'),

        # Cancelled
        ('CAN-ANY-CAN', 'Cancelled'),
    ]

    status = FSMField(default='DRF-NEW-CRT', choices=STATUS_CHOICES, protected=True)
    customer_name = models.CharField(max_length=200)
    vehicle_info = models.CharField(max_length=200)

    # === Draft Phase ===

    @transition(field=status, source='DRF-NEW-CRT', target='DRF-NEW-EDT')
    def edit_draft(self):
        """Mark draft as edited."""
        pass

    @transition(field=status, source='DRF-*', target='SCH-REP-CRT')
    def schedule_repair(self):
        """Schedule as a repair job."""
        pass

    @transition(field=status, source='DRF-*', target='SCH-INS-CRT')
    def schedule_inspection(self):
        """Schedule as an inspection job."""
        pass

    @transition(field=status, source='DRF-*', target='SCH-MNT-CRT')
    def schedule_maintenance(self):
        """Schedule as a maintenance job."""
        pass

    # === Work Phase ===

    @transition(field=status, source='SCH-REP-*', target='WRK-REP-PRG')
    def start_repair(self):
        """Begin repair work."""
        pass

    @transition(field=status, source='SCH-INS-*', target='WRK-INS-PRG')
    def start_inspection(self):
        """Begin inspection work."""
        pass

    @transition(field=status, source='SCH-MNT-*', target='WRK-MNT-PRG')
    def start_maintenance(self):
        """Begin maintenance work."""
        pass

    @transition(field=status, source='WRK-REP-PRG', target='WRK-REP-HLD')
    def pause_repair(self):
        """Pause repair work (waiting for parts, etc.)."""
        pass

    @transition(field=status, source='WRK-REP-HLD', target='WRK-REP-PRG')
    def resume_repair(self):
        """Resume paused repair work."""
        pass

    # === QC Phase ===

    @transition(field=status, source='WRK-REP-PRG', target='QC-REP-PRG')
    def submit_repair_for_qc(self):
        """Submit repair for quality control."""
        pass

    @transition(field=status, source='WRK-INS-PRG', target='QC-INS-PRG')
    def submit_inspection_for_qc(self):
        """Submit inspection for quality control."""
        pass

    @transition(field=status, source='QC-REP-PRG', target='QC-REP-FAI')
    def fail_repair_qc(self):
        """Mark repair as failed QC."""
        pass

    @transition(field=status, source='QC-REP-FAI', target='WRK-REP-PRG')
    def rework_repair(self):
        """Send back to repair after failed QC."""
        pass

    # === Completion ===

    @transition(field=status, source='QC-REP-PRG', target='CMP-REP-DON')
    def complete_repair(self):
        """Mark repair as complete."""
        pass

    @transition(field=status, source='QC-INS-PRG', target='CMP-INS-DON')
    def complete_inspection(self):
        """Mark inspection as complete."""
        pass

    @transition(field=status, source='QC-MNT-PRG', target='CMP-MNT-DON')
    def complete_maintenance(self):
        """Mark maintenance as complete."""
        pass

    # === Universal Transitions ===

    @transition(field=status, source=['DRF-*', 'SCH-*'], target='CAN-ANY-CAN')
    def cancel(self):
        """Cancel job (only from draft or scheduled states)."""
        pass

    @transition(field=status, source='WRK-*', target='CAN-ANY-CAN',
                conditions=[lambda self: self.has_manager_approval])
    def cancel_in_progress(self):
        """Cancel in-progress job (requires manager approval)."""
        pass
```

### Use Cases

**Automotive/Repair Shops:**
```
WRK-ENG-DIA  (Work - Engine - Diagnostics)
WRK-ENG-REP  (Work - Engine - Repair)
WRK-BRK-INS  (Work - Brakes - Inspection)
WRK-BRK-REP  (Work - Brakes - Repair)
```

**Order Processing:**
```
ORD-NEW-RCV  (Order - New - Received)
ORD-NEW-CNF  (Order - New - Confirmed)
SHP-PCK-PRG  (Shipping - Packing - In Progress)
SHP-TRN-OUT  (Shipping - Transit - Out for Delivery)
DLV-CMP-SIG  (Delivered - Complete - Signed)
```

**Content Management:**
```
DRF-ART-WRT  (Draft - Article - Writing)
DRF-ART-EDT  (Draft - Article - Editing)
REV-LEG-PND  (Review - Legal - Pending)
REV-EDI-PND  (Review - Editorial - Pending)
PUB-WEB-LIV  (Published - Web - Live)
PUB-PRT-QUE  (Published - Print - Queued)
```

**IT Ticketing:**
```
NEW-BUG-TRI  (New - Bug - Triage)
NEW-FEA-TRI  (New - Feature - Triage)
WRK-BUG-DEV  (Work - Bug - Development)
WRK-BUG-TST  (Work - Bug - Testing)
RES-BUG-FIX  (Resolved - Bug - Fixed)
RES-BUG-WNT  (Resolved - Bug - Won't Fix)
```

## Transition Callbacks

The `@transition` decorator supports callbacks and transaction control for executing code after state changes.

### Quick Start (Recommended)

For best results, combine `on_success` for DB operations and `on_commit` for external side effects:

```python
def example_create_audit_log(instance, source, target, **kwargs):
    """DB operation - will roll back if something fails (atomic is on by default)."""
    AuditLog.objects.create(
        content_object=instance,
        from_state=source,
        to_state=target,
    )

def example_send_notifications(instance, source, target, **kwargs):
    """External side effect - only runs after DB commit."""
    from django.core.mail import send_mail
    send_mail(
        subject="Your post is live!",
        message=f"Your post '{instance.title}' has been published.",
        from_email="noreply@example.com",
        recipient_list=[instance.author.email],
    )

@transition(
    field=status,
    source='draft',
    target='published',
    on_success=example_create_audit_log,
    on_commit=example_send_notifications,
    # atomic=True is the default - all-or-nothing guarantee
)
def publish(self):
    self.published_at = timezone.now()
    self.save()
```

This ensures:
- Audit log and state change are atomic (both succeed or both roll back)
- Notifications only send after the database commits
- No partial failures or orphaned records

### Parameter Reference

| Parameter | Default | When it runs | Rolls back on failure? | Example |
|-----------|---------|-------------|------------------------|---------|
| `on_success` | `None` | Immediately after transition | Yes (with `atomic`) | `AuditLog.objects.create(...)` |
| `on_commit` | `None` | After transaction commits | N/A (never runs on rollback) | `send_email(...)`, `task.delay()` |
| `atomic` | `True` | Wraps entire transition | Yes | All-or-nothing guarantee |

**Note:** As of v5.1.0, `atomic` defaults to `True`. Using `atomic=False` will emit a deprecation warning.

### on_success - Immediate Callbacks

Use `on_success` for operations that should run immediately after the transition:

```python
def log_completion(instance, source, target, **kwargs):
    """Runs immediately after transition."""
    AuditLog.objects.create(
        job=instance,
        from_status=source,
        to_status=target,
    )

@transition(
    field=status,
    source='WRK-*',
    target='CMP-STD-DON',
    on_success=log_completion
)
def complete(self):
    self.completed_at = timezone.now()
```

**Important:** Without `atomic=True`, the `on_success` callback runs but there's no automatic rollback - each `save()` commits independently.

### on_commit - Post-Commit Callbacks

Use `on_commit` for external side effects that should only happen after the database transaction commits:

```python
def send_notifications(instance, source, target, **kwargs):
    """Runs after commit - safe for external side effects."""
    send_email(instance.customer.email, "Your job is complete!")
    notify_slack(f"Job {instance.id} completed")

@transition(
    field=status,
    source='WRK-*',
    target='CMP-STD-DON',
    on_commit=send_notifications
)
def complete(self):
    self.completed_at = timezone.now()
```

### atomic - Transaction Wrapping (Default)

By default (`atomic=True`), the entire transition is wrapped in a database transaction for all-or-nothing behavior:

```python
@transition(
    field=status,
    source='WRK-*',
    target='CMP-STD-DON',
    on_success=log_completion,
    on_commit=send_notifications,
    # atomic=True is the default
)
def complete(self):
    self.completed_at = timezone.now()
    self.save()  # Part of the atomic transaction
```

With `atomic=True` (default):
- If the transition method raises an exception, all DB changes roll back
- If `on_success` raises an exception, all DB changes roll back
- `on_commit` only runs after the atomic block commits successfully

To disable atomic behavior (not recommended), use `atomic=False`. This will emit a deprecation warning.

### Complete Example

```python
def example_log_and_update(instance, source, target, **kwargs):
    """In-transaction: audit log + related model updates."""
    AuditLog.objects.create(job=instance, from_status=source, to_status=target)
    instance.work_order.status = 'complete'
    instance.work_order.save()

def example_notify_externally(instance, source, target, **kwargs):
    """Post-commit: external notifications."""
    from django.core.mail import send_mail
    send_mail("Job complete", f"Job {instance.id} completed", "noreply@example.com", [instance.customer.email])

@transition(
    field=status,
    source='WRK-*',
    target='CMP-STD-DON',
    on_success=example_log_and_update,
    on_commit=example_notify_externally,
    # atomic=True is the default
)
def complete(self):
    self.completed_at = timezone.now()
    self.save()
```

**Timeline (with default `atomic=True`):**
```
1. transaction.atomic() begins
2. complete() called, state changes in memory
3. self.save() persists job (pending commit)
4. on_success runs: AuditLog created, work_order saved (pending commit)
5. atomic block ends, transaction commits
6. on_commit runs: email sent
```

If anything fails in steps 2-4, the transaction rolls back and `on_commit` never runs.

### Why atomic Matters

**With `atomic=False` (not recommended)** - partial failures are possible:

```python
@transition(field=status, source='draft', target='published', on_success=example_create_audit_log, atomic=False)
def publish(self):
    self.published_at = timezone.now()

# Usage:
post.publish()          # State changes, on_success runs, AuditLog.save() commits
post.title = "Updated"
post.save()             # FAILS - database error!

# Result: AuditLog exists, but post is still in 'draft' state in DB
# The state changed in memory but was never saved
```

**With `atomic=True` (default)** - all-or-nothing:

```python
@transition(field=status, source='draft', target='published', on_success=example_create_audit_log)
def publish(self):
    self.published_at = timezone.now()
    self.save()  # Include save() in the transition

# Usage:
post.publish()  # Everything in one transaction

# If anything fails: no AuditLog, no state change, nothing saved
# If everything succeeds: AuditLog + state change + post saved atomically
```

### Callback Signature

Both callbacks receive the same arguments:
- `instance` - The model instance
- `source` - The state before transition
- `target` - The state after transition
- `method_args` - Positional arguments passed to the transition method
- `method_kwargs` - Keyword arguments passed to the transition method

## Graph Visualization

Generate a visual representation of your state machine:

```bash
# Output as DOT format
python manage.py graph_transitions myapp.BlogPost > states.dot

# Output as PNG
python manage.py graph_transitions -o states.png myapp.BlogPost
```

Requires the `graphviz` package:

```bash
pip install django-fsm-rx[graphviz]
```
