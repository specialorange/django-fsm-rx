"""
Backwards compatibility shim for django-fsm-log models.

StateLog is an alias to FSMTransitionLog. When you run migrations, any existing
data in your django_fsm_log_statelog table is automatically copied to the new
django_fsm_rx_fsmtransitionlog table.

After migration, you can safely delete the old django_fsm_log_statelog table
once you've verified all data was migrated.
"""

from __future__ import annotations

from django_fsm_rx import FSMTransitionLog

# Alias for backwards compatibility with django-fsm-log
StateLog = FSMTransitionLog

__all__ = ["StateLog"]
