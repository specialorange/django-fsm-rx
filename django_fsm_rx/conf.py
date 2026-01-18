"""
Django FSM RX configuration.

This module provides package-level configuration via Django settings.

Settings:
    DJANGO_FSM_RX = {
        'ATOMIC': True,                    # Default for atomic parameter on @transition
        'AUDIT_LOG': True,                 # Enable automatic audit logging
        'AUDIT_LOG_MODE': 'transaction',   # 'transaction' (in atomic block) or 'signal' (via post_transition)
        'AUDIT_LOG_MODEL': None,           # Custom audit log model (dotted path)
        'PROTECTED_FIELDS': False,         # Default for protected parameter on FSMField
    }

Example:
    # settings.py - Disable audit logging
    DJANGO_FSM_RX = {
        'AUDIT_LOG': False,
    }

    # settings.py - Use signal-based audit logging (decoupled, but may not roll back)
    DJANGO_FSM_RX = {
        'AUDIT_LOG_MODE': 'signal',
    }

    # settings.py - Use custom audit log model
    DJANGO_FSM_RX = {
        'AUDIT_LOG_MODEL': 'myapp.TransitionLog',  # Your custom model
    }
"""

from __future__ import annotations

from typing import Any

from django.conf import settings

DEFAULTS = {
    # Transaction behavior
    'ATOMIC': True,

    # Audit logging
    'AUDIT_LOG': True,              # Enable automatic audit logging
    'AUDIT_LOG_MODE': 'transaction',  # 'transaction' (default, rolls back together) or 'signal' (decoupled)
    'AUDIT_LOG_MODEL': None,        # Custom audit log model (e.g., 'myapp.TransitionLog')

    # Field defaults
    'PROTECTED_FIELDS': False,
}


class FSMRXSettings:
    """
    Settings object for django-fsm-rx.

    Reads from Django settings.DJANGO_FSM_RX dict, falling back to defaults.

    Usage:
        from django_fsm_rx.conf import fsm_rx_settings

        if fsm_rx_settings.AUDIT_LOG_ENABLED:
            # do audit logging
    """

    def __init__(self) -> None:
        self._cached_settings: dict[str, Any] | None = None

    @property
    def _settings(self) -> dict[str, Any]:
        if self._cached_settings is None:
            user_settings = getattr(settings, 'DJANGO_FSM_RX', {})
            self._cached_settings = {**DEFAULTS, **user_settings}
        return self._cached_settings

    def __getattr__(self, name: str) -> Any:
        if name.startswith('_'):
            raise AttributeError(name)

        if name not in DEFAULTS:
            raise AttributeError(f"Invalid django-fsm-rx setting: {name}")

        return self._settings[name]

    def clear_cache(self) -> None:
        """Clear cached settings. Useful for testing."""
        self._cached_settings = None


# Singleton instance
fsm_rx_settings = FSMRXSettings()
