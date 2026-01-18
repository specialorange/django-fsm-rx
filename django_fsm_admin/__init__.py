"""
Backwards compatibility shim for django-fsm-admin.

This module re-exports admin integration classes from django_fsm_rx.admin,
allowing existing projects to continue using `from django_fsm_admin import ...` imports.

IMPORTANT: You do NOT need to add 'django_fsm_admin' to INSTALLED_APPS.
Just add 'django_fsm_rx' to INSTALLED_APPS and it will work.

For new projects, we recommend using `from django_fsm_rx.admin import ...` directly.

Example:
    # Both of these work:
    from django_fsm_admin.mixins import FSMTransitionMixin  # backwards compatible
    from django_fsm_rx.admin import FSMAdminMixin  # recommended for new code

Migration Guide:
    Before (django-fsm-admin):
        from django_fsm_admin.mixins import FSMTransitionMixin

        class MyModelAdmin(FSMTransitionMixin, admin.ModelAdmin):
            fsm_field = ['status']

    After (django-fsm-rx):
        from django_fsm_rx.admin import FSMAdminMixin

        class MyModelAdmin(FSMAdminMixin, admin.ModelAdmin):
            fsm_fields = ['status']  # Note: 'fsm_fields' (plural) is the attribute name
"""

from __future__ import annotations

import warnings

from django_fsm_rx.admin import FSMAdminMixin
from django_fsm_rx.admin import FSMObjectTransitions
from django_fsm_rx.admin import FSMTransitionLogInline
from django_fsm_rx.admin import FSMTransitionMixin

# Backwards compatibility alias
FSMTransitionInline = FSMTransitionLogInline

warnings.warn(
    "Importing from 'django_fsm_admin' is deprecated. "
    "Please update your imports to use 'django_fsm_rx.admin' instead. "
    "FSMTransitionMixin has been renamed to FSMAdminMixin.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    "FSMTransitionMixin",
    "FSMAdminMixin",
    "FSMObjectTransitions",
    "FSMTransitionInline",
    "FSMTransitionLogInline",
]
