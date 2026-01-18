"""
Tests for django-fsm-rx settings configuration.

These tests verify:
- Default settings values
- Custom settings override defaults
- Settings cache clearing
- Invalid setting access raises error
"""

from __future__ import annotations

import pytest
from django.test import override_settings

from django_fsm_rx.conf import DEFAULTS
from django_fsm_rx.conf import FSMRXSettings
from django_fsm_rx.conf import fsm_rx_settings


class TestDefaultSettings:
    """Tests for default settings values."""

    def test_atomic_default_is_true(self):
        """Default ATOMIC should be True."""
        settings = FSMRXSettings()
        assert settings.ATOMIC is True

    def test_audit_log_default_is_true(self):
        """Default AUDIT_LOG should be True."""
        settings = FSMRXSettings()
        assert settings.AUDIT_LOG is True

    def test_audit_log_mode_default_is_transaction(self):
        """Default AUDIT_LOG_MODE should be 'transaction'."""
        settings = FSMRXSettings()
        assert settings.AUDIT_LOG_MODE == 'transaction'

    def test_audit_log_model_default_is_none(self):
        """Default AUDIT_LOG_MODEL should be None."""
        settings = FSMRXSettings()
        assert settings.AUDIT_LOG_MODEL is None

    def test_protected_fields_default_is_false(self):
        """Default PROTECTED_FIELDS should be False."""
        settings = FSMRXSettings()
        assert settings.PROTECTED_FIELDS is False

    def test_all_defaults_documented(self):
        """All DEFAULTS should be documented."""
        expected_keys = {'ATOMIC', 'AUDIT_LOG', 'AUDIT_LOG_MODE', 'AUDIT_LOG_MODEL', 'PROTECTED_FIELDS'}
        assert set(DEFAULTS.keys()) == expected_keys


class TestCustomSettings:
    """Tests for custom settings override."""

    @override_settings(DJANGO_FSM_RX={'ATOMIC': False})
    def test_atomic_can_be_overridden(self):
        """ATOMIC can be overridden via settings."""
        settings = FSMRXSettings()
        assert settings.ATOMIC is False

    @override_settings(DJANGO_FSM_RX={'AUDIT_LOG': False})
    def test_audit_log_can_be_overridden(self):
        """AUDIT_LOG can be overridden via settings."""
        settings = FSMRXSettings()
        assert settings.AUDIT_LOG is False

    @override_settings(DJANGO_FSM_RX={'AUDIT_LOG_MODE': 'signal'})
    def test_audit_log_mode_can_be_overridden(self):
        """AUDIT_LOG_MODE can be overridden via settings."""
        settings = FSMRXSettings()
        assert settings.AUDIT_LOG_MODE == 'signal'

    @override_settings(DJANGO_FSM_RX={'AUDIT_LOG_MODEL': 'myapp.CustomLog'})
    def test_audit_log_model_can_be_overridden(self):
        """AUDIT_LOG_MODEL can be overridden via settings."""
        settings = FSMRXSettings()
        assert settings.AUDIT_LOG_MODEL == 'myapp.CustomLog'

    @override_settings(DJANGO_FSM_RX={'PROTECTED_FIELDS': True})
    def test_protected_fields_can_be_overridden(self):
        """PROTECTED_FIELDS can be overridden via settings."""
        settings = FSMRXSettings()
        assert settings.PROTECTED_FIELDS is True

    @override_settings(DJANGO_FSM_RX={'ATOMIC': False, 'AUDIT_LOG': False})
    def test_multiple_settings_can_be_overridden(self):
        """Multiple settings can be overridden at once."""
        settings = FSMRXSettings()
        assert settings.ATOMIC is False
        assert settings.AUDIT_LOG is False
        # Others remain default
        assert settings.AUDIT_LOG_MODE == 'transaction'


class TestSettingsCache:
    """Tests for settings caching behavior."""

    def test_clear_cache_resets_cached_settings(self):
        """clear_cache should reset the cached settings."""
        settings = FSMRXSettings()
        # Access a setting to populate cache
        _ = settings.ATOMIC
        assert settings._cached_settings is not None

        # Clear cache
        settings.clear_cache()
        assert settings._cached_settings is None


class TestInvalidSettings:
    """Tests for invalid setting access."""

    def test_invalid_setting_raises_attribute_error(self):
        """Accessing invalid setting should raise AttributeError."""
        settings = FSMRXSettings()
        with pytest.raises(AttributeError, match="Invalid django-fsm-rx setting"):
            _ = settings.INVALID_SETTING

    def test_private_attribute_raises_attribute_error(self):
        """Accessing private attributes should raise AttributeError."""
        settings = FSMRXSettings()
        with pytest.raises(AttributeError):
            _ = settings._private


class TestSingletonInstance:
    """Tests for the singleton fsm_rx_settings instance."""

    def test_singleton_is_available(self):
        """fsm_rx_settings should be importable."""
        from django_fsm_rx import fsm_rx_settings as imported_settings
        assert imported_settings is not None

    def test_singleton_has_correct_type(self):
        """fsm_rx_settings should be an FSMRXSettings instance."""
        assert isinstance(fsm_rx_settings, FSMRXSettings)

    def test_singleton_works_with_defaults(self):
        """fsm_rx_settings should work with default values."""
        # Clear cache to ensure we get fresh values
        fsm_rx_settings.clear_cache()
        assert fsm_rx_settings.ATOMIC is True
        assert fsm_rx_settings.AUDIT_LOG is True
        assert fsm_rx_settings.AUDIT_LOG_MODE == 'transaction'
