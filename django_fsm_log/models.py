"""
Backwards compatibility shim for django-fsm-log models.

Provides StateLog as an alias to FSMTransitionLog.
"""

from __future__ import annotations

from django_fsm_rx import FSMTransitionLog

# Alias for backwards compatibility with django-fsm-log
StateLog = FSMTransitionLog

__all__ = ["StateLog"]
