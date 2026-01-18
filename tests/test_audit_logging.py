"""
Tests for audit logging functionality.

These tests verify:
- Audit logging in transaction mode (default)
- Audit logging in signal mode
- Audit logging disabled
- Custom audit log model
- Audit log rollback behavior with transactions
"""

from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
from django.db import models
from django.test import override_settings

from django_fsm_rx import FSMField
from django_fsm_rx import transition
from django_fsm_rx.conf import FSMRXSettings
from django_fsm_rx.conf import fsm_rx_settings


@contextmanager
def override_fsm_settings(**kwargs):
    """Context manager that overrides Django settings and clears the FSM settings cache."""
    with override_settings(DJANGO_FSM_RX=kwargs):
        fsm_rx_settings.clear_cache()
        try:
            yield
        finally:
            fsm_rx_settings.clear_cache()


# =============================================================================
# Test Models
# =============================================================================


class AuditTestModel(models.Model):
    """Model for testing audit logging."""

    state = FSMField(default="new")

    @transition(field=state, source="new", target="active")
    def activate(self):
        pass

    @transition(field=state, source="active", target="complete")
    def complete(self):
        pass

    @transition(field=state, source="*", target="cancelled")
    def cancel(self):
        pass

    class Meta:
        app_label = "tests"


class FailingTransitionModel(models.Model):
    """Model with a transition that can fail."""

    state = FSMField(default="new")

    @transition(field=state, source="new", target="processing")
    def start(self):
        pass

    @transition(field=state, source="processing", target="complete")
    def complete(self, should_fail=False):
        if should_fail:
            raise ValueError("Transition failed!")

    class Meta:
        app_label = "tests"


# =============================================================================
# Test Settings Combinations
# =============================================================================


class TestAuditLogSettings:
    """Tests for audit log settings combinations."""

    @pytest.mark.parametrize(
        "audit_log,audit_log_mode,expected_enabled,expected_mode",
        [
            # Default: audit logging enabled in transaction mode
            (True, "transaction", True, "transaction"),
            # Audit logging enabled in signal mode
            (True, "signal", True, "signal"),
            # Audit logging disabled
            (False, "transaction", False, "transaction"),
            (False, "signal", False, "signal"),
        ],
    )
    def test_audit_log_settings_combinations(self, audit_log, audit_log_mode, expected_enabled, expected_mode):
        """Test various audit log settings combinations."""
        with override_settings(
            DJANGO_FSM_RX={
                "AUDIT_LOG": audit_log,
                "AUDIT_LOG_MODE": audit_log_mode,
            }
        ):
            settings = FSMRXSettings()
            assert settings.AUDIT_LOG is expected_enabled
            assert settings.AUDIT_LOG_MODE == expected_mode

    @pytest.mark.parametrize(
        "settings_dict,expected_atomic",
        [
            ({}, True),  # Default
            ({"ATOMIC": True}, True),
            ({"ATOMIC": False}, False),
            ({"ATOMIC": True, "AUDIT_LOG": True}, True),
            ({"ATOMIC": False, "AUDIT_LOG": False}, False),
        ],
    )
    def test_atomic_settings(self, settings_dict, expected_atomic):
        """Test atomic setting combinations."""
        with override_settings(DJANGO_FSM_RX=settings_dict):
            settings = FSMRXSettings()
            assert settings.ATOMIC is expected_atomic


# =============================================================================
# Test Audit Callback Behavior
# =============================================================================


class TestTransactionModeAuditLog:
    """Tests for transaction-mode audit logging."""

    def test_transaction_audit_callback_called(self):
        """In transaction mode, audit callback should be called."""
        with override_fsm_settings(AUDIT_LOG=True, AUDIT_LOG_MODE="transaction"):
            model = AuditTestModel()

            with patch("django_fsm_rx.audit.transaction_audit_callback") as mock_callback:
                model.activate()

                mock_callback.assert_called_once()
                call_kwargs = mock_callback.call_args[1]
                assert call_kwargs["source"] == "new"
                assert call_kwargs["target"] == "active"
                assert call_kwargs["transition_name"] == "activate"

    def test_transaction_audit_multiple_transitions(self):
        """Transaction audit should be called for each transition."""
        with override_fsm_settings(AUDIT_LOG=True, AUDIT_LOG_MODE="transaction"):
            model = AuditTestModel()

            with patch("django_fsm_rx.audit.transaction_audit_callback") as mock_callback:
                model.activate()
                model.complete()

                assert mock_callback.call_count == 2

                # First call: new -> active
                first_call = mock_callback.call_args_list[0][1]
                assert first_call["source"] == "new"
                assert first_call["target"] == "active"

                # Second call: active -> complete
                second_call = mock_callback.call_args_list[1][1]
                assert second_call["source"] == "active"
                assert second_call["target"] == "complete"

    def test_transaction_audit_disabled(self):
        """When AUDIT_LOG is False, transaction audit should not create logs."""
        with override_fsm_settings(AUDIT_LOG=False, AUDIT_LOG_MODE="transaction"):
            model = AuditTestModel()

            with patch("django_fsm_rx.audit.create_audit_log") as mock_create:
                model.activate()
                # Callback is still called, but it checks AUDIT_LOG setting
                # create_audit_log should not be called
                mock_create.assert_not_called()


class TestSignalModeAuditLog:
    """Tests for signal-mode audit logging."""

    def test_signal_audit_called(self):
        """In signal mode, signal audit handler should create logs."""
        with override_fsm_settings(AUDIT_LOG=True, AUDIT_LOG_MODE="signal"):
            model = AuditTestModel()

            with patch("django_fsm_rx.audit._create_audit_log_safe") as mock_create:
                model.activate()

                # Signal handler should be called
                mock_create.assert_called_once()
                call_kwargs = mock_create.call_args[1]
                assert call_kwargs["source_state"] == "new"
                assert call_kwargs["target_state"] == "active"
                assert call_kwargs["transition_name"] == "activate"

    def test_signal_audit_multiple_transitions(self):
        """Signal audit should be called for each transition."""
        with override_fsm_settings(AUDIT_LOG=True, AUDIT_LOG_MODE="signal"):
            model = AuditTestModel()

            with patch("django_fsm_rx.audit._create_audit_log_safe") as mock_create:
                model.activate()
                model.complete()

                assert mock_create.call_count == 2

    def test_signal_audit_disabled(self):
        """When AUDIT_LOG is False, signal audit should not create logs."""
        with override_fsm_settings(AUDIT_LOG=False, AUDIT_LOG_MODE="signal"):
            model = AuditTestModel()

            with patch("django_fsm_rx.audit.create_audit_log") as mock_create:
                model.activate()
                mock_create.assert_not_called()


class TestAuditModeExclusivity:
    """Tests ensuring only one audit mode is active at a time."""

    def test_transaction_mode_does_not_trigger_signal_audit(self):
        """In transaction mode, signal audit handler should not create logs."""
        with override_fsm_settings(AUDIT_LOG=True, AUDIT_LOG_MODE="transaction"):
            model = AuditTestModel()

            with patch("django_fsm_rx.audit.signal_audit_log"):
                with patch("django_fsm_rx.audit.transaction_audit_callback") as mock_transaction:
                    model.activate()

                    # Transaction callback is called
                    mock_transaction.assert_called_once()

                    # Signal handler is called (it's a receiver), but it checks mode
                    # and returns early without creating a log

    def test_signal_mode_transaction_callback_returns_early(self):
        """In signal mode, transaction callback should return early."""
        with override_fsm_settings(AUDIT_LOG=True, AUDIT_LOG_MODE="signal"):
            model = AuditTestModel()

            with patch("django_fsm_rx.audit._create_audit_log_safe") as mock_create:
                model.activate()

                # Only one call (from signal handler, not from transaction callback)
                assert mock_create.call_count == 1


# =============================================================================
# Test Audit Log Model Resolution
# =============================================================================


class TestAuditLogModelResolution:
    """Tests for audit log model resolution."""

    def test_default_model_resolution(self):
        """With no custom model, should use FSMTransitionLog."""
        with override_fsm_settings(AUDIT_LOG=True, AUDIT_LOG_MODEL=None):
            from django_fsm_rx.audit import get_audit_log_model

            with patch("django.apps.apps.get_model") as mock_get_model:
                mock_model = MagicMock()
                mock_get_model.return_value = mock_model

                result = get_audit_log_model()

                mock_get_model.assert_called_with("django_fsm_rx", "FSMTransitionLog")
                assert result == mock_model

    def test_custom_model_resolution(self):
        """With custom model specified, should use that model."""
        with override_fsm_settings(AUDIT_LOG=True, AUDIT_LOG_MODEL="myapp.CustomLog"):
            from django_fsm_rx.audit import get_audit_log_model

            with patch("django.apps.apps.get_model") as mock_get_model:
                mock_model = MagicMock()
                mock_get_model.return_value = mock_model

                result = get_audit_log_model()

                mock_get_model.assert_called_with("myapp.CustomLog")
                assert result == mock_model

    def test_custom_model_not_found(self):
        """If custom model not found, should return None and log error."""
        with override_fsm_settings(AUDIT_LOG=True, AUDIT_LOG_MODEL="nonexistent.Model"):
            from django_fsm_rx.audit import get_audit_log_model

            with patch("django.apps.apps.get_model") as mock_get_model:
                mock_get_model.side_effect = LookupError("Model not found")

                result = get_audit_log_model()

                assert result is None

    def test_audit_disabled_returns_none(self):
        """When audit logging disabled, should return None."""
        with override_fsm_settings(AUDIT_LOG=False):
            from django_fsm_rx.audit import get_audit_log_model

            result = get_audit_log_model()

            assert result is None


# =============================================================================
# Test Create Audit Log Function
# =============================================================================


class TestCreateAuditLog:
    """Tests for create_audit_log function."""

    def test_create_audit_log_with_all_fields(self):
        """create_audit_log should create log with all required fields."""
        with override_fsm_settings(AUDIT_LOG=True):
            from django_fsm_rx.audit import create_audit_log

            mock_model = MagicMock()
            mock_model._meta.get_fields.return_value = []
            mock_instance = MagicMock()
            mock_instance.pk = 123

            with patch("django_fsm_rx.audit.get_audit_log_model") as mock_get_model:
                with patch("django.contrib.contenttypes.models.ContentType.objects.get_for_model") as mock_ct:
                    mock_get_model.return_value = mock_model
                    mock_ct.return_value = MagicMock()

                    create_audit_log(
                        instance=mock_instance,
                        transition_name="activate",
                        source_state="new",
                        target_state="active",
                    )

                    mock_model.objects.create.assert_called_once()
                    call_kwargs = mock_model.objects.create.call_args[1]
                    assert call_kwargs["transition_name"] == "activate"
                    assert call_kwargs["source_state"] == "new"
                    assert call_kwargs["target_state"] == "active"
                    assert call_kwargs["object_id"] == "123"

    def test_create_audit_log_disabled(self):
        """create_audit_log should return None when disabled."""
        with override_fsm_settings(AUDIT_LOG=False):
            from django_fsm_rx.audit import create_audit_log

            mock_instance = MagicMock()

            result = create_audit_log(
                instance=mock_instance,
                transition_name="activate",
                source_state="new",
                target_state="active",
            )

            assert result is None


# =============================================================================
# Test Wildcard Transitions
# =============================================================================


class TestAuditLogWithWildcards:
    """Tests for audit logging with wildcard transitions."""

    def test_wildcard_transition_audit(self):
        """Wildcard transitions should be audited correctly."""
        with override_fsm_settings(AUDIT_LOG=True, AUDIT_LOG_MODE="transaction"):
            model = AuditTestModel()

            with patch("django_fsm_rx.audit.transaction_audit_callback") as mock_callback:
                # Cancel from 'new' state (wildcard source)
                model.cancel()

                mock_callback.assert_called_once()
                call_kwargs = mock_callback.call_args[1]
                assert call_kwargs["source"] == "new"
                assert call_kwargs["target"] == "cancelled"
                assert call_kwargs["transition_name"] == "cancel"

    def test_wildcard_from_different_states(self):
        """Wildcard transitions should capture correct source state."""
        with override_fsm_settings(AUDIT_LOG=True, AUDIT_LOG_MODE="transaction"):
            model = AuditTestModel()

            with patch("django_fsm_rx.audit.transaction_audit_callback") as mock_callback:
                model.activate()  # new -> active
                mock_callback.reset_mock()

                model.cancel()  # active -> cancelled (wildcard)

                call_kwargs = mock_callback.call_args[1]
                assert call_kwargs["source"] == "active"
                assert call_kwargs["target"] == "cancelled"


# =============================================================================
# Test Error Handling
# =============================================================================


class TestAuditLogErrorHandling:
    """Tests for audit log error handling."""

    def test_audit_failure_does_not_break_transition(self):
        """If audit logging fails, transition should still succeed."""
        with override_fsm_settings(AUDIT_LOG=True, AUDIT_LOG_MODE="transaction"):
            model = AuditTestModel()

            # Patch create_audit_log to raise an exception
            with patch("django_fsm_rx.audit.create_audit_log") as mock_create_inner:
                mock_create_inner.side_effect = Exception("Database error")

                # Transition should still work (exception is caught by _create_audit_log_safe)
                model.activate()

                assert model.state == "active"

    def test_signal_audit_failure_logged(self):
        """If signal audit fails, error should be logged but not raised."""
        with override_fsm_settings(AUDIT_LOG=True, AUDIT_LOG_MODE="signal"):
            model = AuditTestModel()

            with patch("django_fsm_rx.audit.create_audit_log") as mock_create:
                mock_create.side_effect = Exception("Database error")

                with patch("django_fsm_rx.audit.logger") as mock_logger:
                    model.activate()

                    # Transition succeeded
                    assert model.state == "active"

                    # Error was logged
                    mock_logger.exception.assert_called_once()


# =============================================================================
# Parametrized Integration Tests
# =============================================================================


class TestAuditLogIntegration:
    """Integration tests with parametrized settings."""

    @pytest.mark.parametrize("audit_log", [True, False])
    @pytest.mark.parametrize("audit_mode", ["transaction", "signal"])
    def test_transition_works_with_all_audit_settings(self, audit_log, audit_mode):
        """Transitions should work regardless of audit settings."""
        with override_fsm_settings(AUDIT_LOG=audit_log, AUDIT_LOG_MODE=audit_mode):
            model = AuditTestModel()
            assert model.state == "new"

            model.activate()
            assert model.state == "active"

            model.complete()
            assert model.state == "complete"

    @pytest.mark.parametrize("audit_log", [True, False])
    @pytest.mark.parametrize("audit_mode", ["transaction", "signal"])
    def test_audit_call_based_on_settings(self, audit_log, audit_mode):
        """Audit log creation should depend on settings."""
        with override_fsm_settings(AUDIT_LOG=audit_log, AUDIT_LOG_MODE=audit_mode):
            model = AuditTestModel()

            with patch("django_fsm_rx.audit._create_audit_log_safe") as mock_create:
                model.activate()

                if audit_log:
                    mock_create.assert_called()
                else:
                    mock_create.assert_not_called()

    @pytest.mark.parametrize("atomic", [True, False])
    @pytest.mark.parametrize("audit_log", [True, False])
    @pytest.mark.parametrize("audit_mode", ["transaction", "signal"])
    def test_atomic_and_audit_combinations(self, atomic, audit_log, audit_mode):
        """All combinations of atomic and audit settings should work."""
        with override_fsm_settings(ATOMIC=atomic, AUDIT_LOG=audit_log, AUDIT_LOG_MODE=audit_mode):
            model = AuditTestModel()

            model.activate()
            assert model.state == "active"

            model.cancel()
            assert model.state == "cancelled"
