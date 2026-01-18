"""
Backwards compatibility shim for django-fsm-log.

This module provides a StateLog model alias to FSMTransitionLog, allowing existing
projects to continue using `from django_fsm_log.models import StateLog` imports.

IMPORTANT: You do NOT need to add 'django_fsm_log' to INSTALLED_APPS.
Just add 'django_fsm_rx' to INSTALLED_APPS and run migrations.

For new projects, we recommend using `from django_fsm_rx import FSMTransitionLog` directly.

Example:
    # Both of these work (after adding 'django_fsm_rx' to INSTALLED_APPS):
    from django_fsm_log.models import StateLog  # backwards compatible
    from django_fsm_rx import FSMTransitionLog  # recommended for new code

Migration Guide:
    Before (django-fsm-log):
        from django_fsm_log.models import StateLog
        from django_fsm_log.decorators import fsm_log_by, fsm_log_description

        logs = StateLog.objects.for_instance(my_object)

    After (django-fsm-rx):
        from django_fsm_rx import FSMTransitionLog
        from django_fsm_rx.log import fsm_log_by, fsm_log_description

        logs = FSMTransitionLog.objects.filter(
            content_type=ContentType.objects.get_for_model(my_object),
            object_id=my_object.pk
        )
"""

from __future__ import annotations

import warnings

# Re-export decorators for convenience (django-fsm-log style imports)
from django_fsm_rx.log import FSMLogDescriptor
from django_fsm_rx.log import fsm_log_by
from django_fsm_rx.log import fsm_log_description

warnings.warn(
    "Importing from 'django_fsm_log' is deprecated. "
    "Please update your imports to use 'django_fsm_rx' and 'django_fsm_rx.log' instead. "
    "StateLog has been renamed to FSMTransitionLog.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    "fsm_log_by",
    "fsm_log_description",
    "FSMLogDescriptor",
]
