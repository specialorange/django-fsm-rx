"""
Backwards compatibility shim for django_fsm_log.decorators.

This module provides the fsm_log_by and fsm_log_description decorators
that were part of django-fsm-log.

Example:
    # Both of these work:
    from django_fsm_log.decorators import fsm_log_by  # backwards compatible
    from django_fsm_rx.log import fsm_log_by  # recommended for new code
"""

from __future__ import annotations

import warnings

from django_fsm_rx.log import FSMLogDescriptor
from django_fsm_rx.log import fsm_log_by
from django_fsm_rx.log import fsm_log_description

warnings.warn(
    "Importing from 'django_fsm_log.decorators' is deprecated. "
    "Please update your imports to use 'django_fsm_rx.log' instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    "fsm_log_by",
    "fsm_log_description",
    "FSMLogDescriptor",
]
