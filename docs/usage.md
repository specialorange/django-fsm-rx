# Usage Guide

## Basic Transitions

Add an FSMField to your model and use the `transition` decorator:

```python
from django_fsm_rx import FSMField, transition

class BlogPost(models.Model):
    state = FSMField(default='draft')

    @transition(field=state, source='draft', target='published')
    def publish(self):
        """This method may contain side effects."""
        pass
```

Call the transition method to change state:

```python
post = BlogPost()
post.publish()
post.save()  # State change is not persisted until save()
```

## Checking if Transition is Allowed

```python
from django_fsm_rx import can_proceed

if can_proceed(post.publish):
    post.publish()
    post.save()
```

## Conditions

Add conditions that must be met before a transition can occur:

```python
def is_business_hours(instance):
    return 9 <= datetime.now().hour < 17

@transition(field=state, source='draft', target='published', conditions=[is_business_hours])
def publish(self):
    pass
```

## Protected Fields

Prevent direct state assignment:

```python
class BlogPost(FSMModelMixin, models.Model):
    state = FSMField(default='draft', protected=True)

post = BlogPost()
post.state = 'published'  # Raises AttributeError
```

## Source State Options

```python
# From any state
@transition(field=state, source='*', target='cancelled')
def cancel(self):
    pass

# From any state except target
@transition(field=state, source='+', target='reset')
def reset(self):
    pass

# From multiple specific states
@transition(field=state, source=['draft', 'review'], target='published')
def publish(self):
    pass
```

## Dynamic Target State

```python
from django_fsm_rx import RETURN_VALUE, GET_STATE

@transition(field=state, source='review', target=RETURN_VALUE('published', 'rejected'))
def moderate(self, approved):
    return 'published' if approved else 'rejected'

@transition(
    field=state,
    source='review',
    target=GET_STATE(
        lambda self, approved: 'published' if approved else 'rejected',
        states=['published', 'rejected']
    )
)
def moderate(self, approved):
    pass
```

## Permissions

```python
@transition(field=state, source='draft', target='published', permission='blog.can_publish')
def publish(self):
    pass

@transition(
    field=state,
    source='*',
    target='deleted',
    permission=lambda instance, user: user.is_superuser
)
def delete(self):
    pass
```

Check permissions:

```python
from django_fsm_rx import has_transition_perm

if has_transition_perm(post.publish, user):
    post.publish()
    post.save()
```

## Error Handling

Specify a fallback state if transition raises an exception:

```python
@transition(field=state, source='processing', target='complete', on_error='failed')
def process(self):
    # If this raises, state becomes 'failed'
    do_risky_operation()
```

## Signals

```python
from django_fsm_rx.signals import pre_transition, post_transition

@receiver(pre_transition)
def on_pre_transition(sender, instance, name, source, target, **kwargs):
    print(f"{instance} transitioning from {source} to {target}")

@receiver(post_transition)
def on_post_transition(sender, instance, name, source, target, **kwargs):
    print(f"{instance} transitioned to {target}")
```

## Optimistic Locking

Prevent concurrent state changes:

```python
from django_fsm_rx import ConcurrentTransitionMixin

class BlogPost(ConcurrentTransitionMixin, models.Model):
    state = FSMField(default='draft')
```

## Integer States

```python
class OrderStatus:
    PENDING = 10
    PROCESSING = 20
    SHIPPED = 30

class Order(models.Model):
    status = FSMIntegerField(default=OrderStatus.PENDING)

    @transition(field=status, source=OrderStatus.PENDING, target=OrderStatus.PROCESSING)
    def process(self):
        pass
```

## Foreign Key States

```python
class OrderState(models.Model):
    id = models.CharField(primary_key=True, max_length=50)
    label = models.CharField(max_length=100)

class Order(models.Model):
    state = FSMKeyField(OrderState, default='pending', on_delete=models.PROTECT)
```

## Model Methods

```python
# Get all declared transitions
post.get_all_state_transitions()

# Get transitions available from current state
post.get_available_state_transitions()

# Get transitions available for a specific user
post.get_available_user_state_transitions(user)
```

## Database Migrations for FSM Fields

Understanding when Django migrations are required:

### Adding a New FSMField

When adding a new FSM field to a model, a migration **is required** (just like any new field):

```python
# Adding a new field - migration required
class Order(models.Model):
    status = FSMField(default='pending')  # New field
```

Run `python manage.py makemigrations` to create the migration.

### Converting an Existing CharField to FSMField

Converting from `CharField` to `FSMField` requires **no database schema changes** because `FSMField` inherits directly from `CharField`:

```python
# Before
status = models.CharField(max_length=50, default='pending')

# After - same database column, just Python-side FSM behavior added
status = FSMField(max_length=50, default='pending')
```

**However**, Django's migration system will detect the field class change and generate a migration. This migration is safe to run - it updates Django's internal state but makes no database changes (the column remains a VARCHAR).

You can either:
1. **Run the migration** (recommended) - It's a no-op at the database level
2. **Fake it** - `python manage.py migrate --fake` if you want to skip execution

### Converting Other Field Types

| Original Field | Target FSM Field | Migration Impact |
|----------------|------------------|------------------|
| `CharField` | `FSMField` | ✅ No schema change (same column type) |
| `IntegerField` | `FSMIntegerField` | ✅ No schema change (same column type) |
| `CharField` | `FSMIntegerField` | ⚠️ Schema change required (VARCHAR → INTEGER) |
| `IntegerField` | `FSMField` | ⚠️ Schema change required (INTEGER → VARCHAR) |
| `ForeignKey` | `FSMKeyField` | ✅ No schema change (same column type) |
| Any other type | Any FSM field | ⚠️ Check if base types match |

**Rule of thumb**: If the base Django field type matches, no schema migration is needed.

### The `protected` Parameter

The `protected=True` parameter is Python-only and has no database impact:

```python
# protected=False (default) - allows direct assignment for backward compatibility
status = FSMField(default='pending', protected=False)
instance.status = 'approved'  # Works

# protected=True - enforces transitions only
status = FSMField(default='pending', protected=True)
instance.status = 'approved'  # Raises AttributeError
```

Use `protected=False` when converting existing code that assigns directly to the field, then gradually migrate to using transitions.
