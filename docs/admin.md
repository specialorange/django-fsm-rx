# Admin Integration

## FSMCascadeWidget

When using hierarchical status codes, the standard dropdown becomes unwieldy with dozens of options. `FSMCascadeWidget` renders cascading dropdowns that filter based on selection.

![FSMCascadeWidget Example](images/cascade_widget_example.png)

*The cascade widget showing three linked dropdowns (Category → Type → Status) with status history below.*

### Basic Configuration

```python
from django.contrib import admin
from django_fsm_rx.admin import FSMAdminMixin

@admin.register(RepairOrder)
class RepairOrderAdmin(FSMAdminMixin, admin.ModelAdmin):
    list_display = ['id', 'customer_name', 'status']
    fsm_fields = ['status']

    # Configure cascade widget
    fsm_cascade_fields = {
        'status': {
            'levels': 3,           # Number of dropdown levels
            'separator': '-',      # Character separating levels
            'labels': ['Category', 'Type', 'Status'],  # Dropdown labels
        }
    }
```

### How It Works

Instead of one dropdown with all options:

```
[Select Status ▼]
  DRF-NEW-CRT - Draft - New - Created
  DRF-NEW-EDT - Draft - New - Edited
  SCH-REP-CRT - Scheduled - Repair - Created
  SCH-INS-CRT - Scheduled - Inspection - Created
  WRK-REP-PRG - Work - Repair - In Progress
  ... (20+ more options)
```

The cascade widget renders three linked dropdowns:

```
[Category ▼]     [Type ▼]        [Status ▼]
   DRF              NEW             CRT
   SCH              REP             EDT
   WRK              INS             PRG
   QC               MNT             HLD
   CMP                              DON
   CAN                              FAI
```

When you select "WRK" in Category, the Type dropdown filters to show only types available under WRK:

```
[Category ▼]     [Type ▼]        [Status ▼]
   WRK ✓           REP             PRG
                   INS             HLD
                   MNT
```

### Manual Widget Configuration

For more control, configure the widget directly:

```python
from django_fsm_rx.admin import FSMAdminMixin
from django_fsm_rx.widgets import FSMCascadeWidget

@admin.register(RepairOrder)
class RepairOrderAdmin(FSMAdminMixin, admin.ModelAdmin):
    fsm_fields = ['status']

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == 'status':
            # Get the object being edited (if any)
            obj = getattr(request, '_editing_obj', None)

            kwargs['widget'] = FSMCascadeWidget(
                levels=3,
                separator='-',
                labels=['Category', 'Type', 'Status'],
                choices=RepairOrder.STATUS_CHOICES,
                # Optionally filter to allowed transitions only
                allowed_targets=self._get_allowed_targets(obj) if obj else None,
            )
        return super().formfield_for_dbfield(db_field, request, **kwargs)

    def _get_allowed_targets(self, obj):
        """Get list of states this object can transition to."""
        transitions = obj.get_available_status_transitions()
        return [t.target for t in transitions]
```

### Widget Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `levels` | int | 2 | Number of dropdown levels |
| `separator` | str | `'-'` | Character separating levels in status code |
| `labels` | list | `['Level 1', ...]` | Labels for each dropdown |
| `choices` | list | `[]` | List of `(value, label)` tuples |
| `allowed_targets` | list | `None` | Filter to only these target states |

### Styling

The widget includes CSS for both light and dark modes. Customize by overriding in your admin CSS:

```css
/* Custom cascade widget styling */
.fsm-cascade-widget {
    display: flex;
    gap: 1rem;
}

.fsm-cascade-widget select {
    min-width: 150px;
}

.fsm-cascade-widget label {
    font-weight: bold;
    margin-bottom: 0.25rem;
}
```
