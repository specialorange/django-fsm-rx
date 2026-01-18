"""
Backwards compatibility shim for django_fsm_admin.mixins.

This module provides the FSMTransitionMixin class that was the primary
export of django-fsm-admin.

Example:
    # Both of these work:
    from django_fsm_admin.mixins import FSMTransitionMixin  # backwards compatible
    from django_fsm_rx.admin import FSMAdminMixin  # recommended for new code
"""

from __future__ import annotations

import warnings

from django_fsm_rx.admin import FSMAdminMixin
from django_fsm_rx.admin import FSMObjectTransitions
from django_fsm_rx.admin import FSMTransitionMixin

warnings.warn(
    "Importing from 'django_fsm_admin.mixins' is deprecated. "
    "Please update your imports to use 'django_fsm_rx.admin' instead. "
    "FSMTransitionMixin has been renamed to FSMAdminMixin.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    "FSMTransitionMixin",
    "FSMAdminMixin",
    "FSMObjectTransitions",
]
