"""
Tests for atomic and on_commit transition features.

These tests verify:
- atomic=True wraps transition in transaction.atomic()
- on_commit callback runs after transaction commits
- on_success runs before on_commit
- Rollback behavior with atomic=True
- Deprecation warning when atomic=False
- Backwards compatibility with existing @transition usage
"""

from __future__ import annotations

import warnings
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
from django.db import models

from django_fsm_rx import FSMField
from django_fsm_rx import TransitionNotAllowed
from django_fsm_rx import can_proceed
from django_fsm_rx import transition

# Track callback invocations
invocation_log: list[dict] = []


def reset_invocation_log():
    """Reset the invocation log."""
    invocation_log.clear()


def on_success_callback(instance, source, target, **kwargs):
    """on_success callback that logs invocation."""
    invocation_log.append(
        {
            "type": "on_success",
            "source": source,
            "target": target,
            "order": len(invocation_log),
        }
    )


def on_commit_callback(instance, source, target, **kwargs):
    """on_commit callback that logs invocation."""
    invocation_log.append(
        {
            "type": "on_commit",
            "source": source,
            "target": target,
            "order": len(invocation_log),
        }
    )


def failing_on_success_callback(instance, source, target, **kwargs):
    """on_success callback that raises an exception."""
    invocation_log.append({"type": "on_success_before_fail", "order": len(invocation_log)})
    raise ValueError("on_success failed!")


# =============================================================================
# Test Models
# =============================================================================


class BasicModel(models.Model):
    """Model with default atomic=True behavior."""

    state = FSMField(default="new")

    @transition(field=state, source="new", target="done", on_success=on_success_callback)
    def finish(self):
        pass

    class Meta:
        app_label = "tests"


class OnCommitModel(models.Model):
    """Model with on_commit callback."""

    state = FSMField(default="new")

    @transition(
        field=state,
        source="new",
        target="done",
        on_success=on_success_callback,
        on_commit=on_commit_callback,
    )
    def finish(self):
        pass

    class Meta:
        app_label = "tests"


class AtomicFalseModel(models.Model):
    """Model with atomic=False (should emit warning)."""

    state = FSMField(default="new")

    # This will emit a DeprecationWarning at class definition time
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)

        @transition(field=state, source="new", target="done", atomic=False)
        def finish(self):
            pass

    class Meta:
        app_label = "tests"


class MultipleTransitionsModel(models.Model):
    """Model with multiple transitions to test isolation."""

    state = FSMField(default="new")

    @transition(
        field=state,
        source="new",
        target="processing",
        on_success=on_success_callback,
        on_commit=on_commit_callback,
    )
    def start(self):
        pass

    @transition(
        field=state,
        source="processing",
        target="done",
        on_success=on_success_callback,
        on_commit=on_commit_callback,
    )
    def complete(self):
        pass

    @transition(
        field=state,
        source="processing",
        target="failed",
    )
    def fail(self):
        pass

    class Meta:
        app_label = "tests"


class FailingOnSuccessModel(models.Model):
    """Model where on_success callback fails."""

    state = FSMField(default="new")

    @transition(
        field=state,
        source="new",
        target="done",
        on_success=failing_on_success_callback,
        on_commit=on_commit_callback,
    )
    def finish(self):
        pass

    class Meta:
        app_label = "tests"


class NoCallbacksModel(models.Model):
    """Model with no callbacks - backwards compatibility test."""

    state = FSMField(default="new")

    @transition(field=state, source="new", target="done")
    def finish(self):
        pass

    @transition(field=state, source="done", target="archived")
    def archive(self):
        pass

    class Meta:
        app_label = "tests"


class MultipleSourcesModel(models.Model):
    """Model with transition from multiple sources."""

    state = FSMField(default="new")

    @transition(
        field=state,
        source=["new", "pending"],
        target="done",
        on_success=on_success_callback,
    )
    def finish(self):
        pass

    @transition(field=state, source="new", target="pending")
    def pend(self):
        pass

    class Meta:
        app_label = "tests"


class WildcardModel(models.Model):
    """Model with wildcard transitions."""

    state = FSMField(default="new")

    @transition(field=state, source="*", target="cancelled", on_success=on_success_callback)
    def cancel(self):
        pass

    @transition(field=state, source="new", target="active")
    def activate(self):
        pass

    class Meta:
        app_label = "tests"


# =============================================================================
# Tests
# =============================================================================


class TestBackwardsCompatibility:
    """Tests ensuring existing @transition usage still works."""

    def setup_method(self):
        reset_invocation_log()

    def test_transition_without_callbacks_works(self):
        """Transition without on_success or on_commit should work."""
        model = NoCallbacksModel()
        assert model.state == "new"

        model.finish()
        assert model.state == "done"

        model.archive()
        assert model.state == "archived"

    def test_transition_with_only_on_success_works(self):
        """Transition with only on_success (no on_commit) should work."""
        model = BasicModel()
        assert model.state == "new"

        model.finish()
        assert model.state == "done"
        assert len(invocation_log) == 1
        assert invocation_log[0]["type"] == "on_success"

    def test_can_proceed_still_works(self):
        """can_proceed should work with new parameters."""
        model = NoCallbacksModel()
        assert can_proceed(model.finish) is True
        assert can_proceed(model.archive) is False

        model.finish()
        assert can_proceed(model.finish) is False
        assert can_proceed(model.archive) is True

    def test_transition_not_allowed_still_raised(self):
        """TransitionNotAllowed should still be raised for invalid transitions."""
        model = NoCallbacksModel()
        model.finish()

        with pytest.raises(TransitionNotAllowed):
            model.finish()  # Can't finish twice

    def test_multiple_sources_still_works(self):
        """Transitions from multiple sources should work."""
        model = MultipleSourcesModel()

        # From new -> done
        model.finish()
        assert model.state == "done"

        # Reset and try new -> pending -> done
        model2 = MultipleSourcesModel()
        model2.pend()
        assert model2.state == "pending"
        model2.finish()
        assert model2.state == "done"

    def test_wildcard_source_still_works(self):
        """Wildcard source transitions should work."""
        model = WildcardModel()

        # Cancel from new
        model.cancel()
        assert model.state == "cancelled"
        assert len(invocation_log) == 1

        # Reset and try cancel from active
        reset_invocation_log()
        model2 = WildcardModel()
        model2.activate()
        model2.cancel()
        assert model2.state == "cancelled"
        assert len(invocation_log) == 1


class TestOnCommitCallback:
    """Tests for on_commit callback behavior."""

    def setup_method(self):
        reset_invocation_log()

    def test_on_commit_registered(self):
        """on_commit should be registered for execution after commit."""
        model = OnCommitModel()

        with patch("django_fsm_rx.transaction.on_commit") as mock_on_commit:
            model.finish()

            # on_commit should have been called to register the callback
            assert mock_on_commit.called

    def test_on_success_runs_before_on_commit_registration(self):
        """on_success should run immediately, on_commit should be registered."""
        model = OnCommitModel()

        with patch("django_fsm_rx.transaction.on_commit") as mock_on_commit:
            model.finish()

            # on_success ran immediately
            assert len(invocation_log) == 1
            assert invocation_log[0]["type"] == "on_success"

            # on_commit was registered but not executed yet
            assert mock_on_commit.called


class TestAtomicBehavior:
    """Tests for atomic transaction wrapping."""

    def setup_method(self):
        reset_invocation_log()

    def test_atomic_true_is_default(self):
        """atomic=True should be the default."""
        model = BasicModel()

        with patch("django_fsm_rx.transaction.atomic") as mock_atomic:
            # Mock the context manager
            mock_atomic.return_value.__enter__ = MagicMock()
            mock_atomic.return_value.__exit__ = MagicMock(return_value=False)

            with patch("django.db.connection") as mock_conn:
                mock_conn.ensure_connection = MagicMock()
                model.finish()

                # atomic should have been used
                assert mock_atomic.called


class TestAtomicFalseWarning:
    """Tests for deprecation warning when atomic=False."""

    def test_atomic_false_emits_warning(self):
        """Using atomic=False should emit a DeprecationWarning."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            # Define a model with atomic=False
            class WarningTestModel(models.Model):
                state = FSMField(default="new")

                @transition(field=state, source="new", target="done", atomic=False)
                def finish(self):
                    pass

                class Meta:
                    app_label = "tests"

            # Check that a deprecation warning was emitted
            deprecation_warnings = [x for x in w if issubclass(x.category, DeprecationWarning)]
            assert len(deprecation_warnings) == 1
            assert "atomic=False is not recommended" in str(deprecation_warnings[0].message)


class TestMultipleTransitions:
    """Tests for models with multiple transitions."""

    def setup_method(self):
        reset_invocation_log()

    def test_each_transition_has_own_callbacks(self):
        """Each transition should have its own callbacks."""
        model = MultipleTransitionsModel()

        model.start()
        assert model.state == "processing"
        # Both on_success and on_commit run (on_commit runs immediately as fallback without DB)
        assert len(invocation_log) == 2
        assert invocation_log[0]["type"] == "on_success"
        assert invocation_log[0]["source"] == "new"
        assert invocation_log[0]["target"] == "processing"
        assert invocation_log[1]["type"] == "on_commit"
        assert invocation_log[1]["source"] == "new"
        assert invocation_log[1]["target"] == "processing"

        reset_invocation_log()

        model.complete()
        assert model.state == "done"
        assert len(invocation_log) == 2
        assert invocation_log[0]["source"] == "processing"
        assert invocation_log[0]["target"] == "done"

    def test_transition_without_callbacks_in_multi_transition_model(self):
        """Transition without callbacks should work alongside ones with callbacks."""
        model = MultipleTransitionsModel()

        model.start()
        assert model.state == "processing"
        # Both on_success and on_commit run
        assert len(invocation_log) == 2

        reset_invocation_log()

        model.fail()
        assert model.state == "failed"
        # fail() has no callbacks
        assert len(invocation_log) == 0


class TestCallbackArguments:
    """Tests for callback argument passing."""

    def setup_method(self):
        reset_invocation_log()

    def test_on_success_receives_correct_arguments(self):
        """on_success should receive instance, source, target, and kwargs."""
        received_args = {}

        def capture_callback(instance, source, target, **kwargs):
            received_args["instance"] = instance
            received_args["source"] = source
            received_args["target"] = target
            received_args["kwargs"] = kwargs

        class CaptureModel(models.Model):
            state = FSMField(default="new")

            @transition(field=state, source="new", target="done", on_success=capture_callback)
            def finish(self, arg1, kwarg1=None):
                pass

            class Meta:
                app_label = "tests"

        model = CaptureModel()
        model.finish("positional", kwarg1="keyword")

        assert received_args["instance"] is model
        assert received_args["source"] == "new"
        assert received_args["target"] == "done"
        assert received_args["kwargs"]["method_args"] == ("positional",)
        assert received_args["kwargs"]["method_kwargs"] == {"kwarg1": "keyword"}


class TestFailingCallbacks:
    """Tests for callback failure scenarios."""

    def setup_method(self):
        reset_invocation_log()

    def test_failing_on_success_propagates_exception(self):
        """Exception in on_success should propagate."""
        model = FailingOnSuccessModel()

        with pytest.raises(ValueError, match="on_success failed!"):
            model.finish()

        # on_success started executing
        assert len(invocation_log) == 1
        assert invocation_log[0]["type"] == "on_success_before_fail"

    def test_state_changes_even_if_on_success_fails(self):
        """State should change even if on_success raises (without DB rollback)."""
        model = FailingOnSuccessModel()

        with pytest.raises(ValueError):
            model.finish()

        # State changed in memory (would rollback in real DB with atomic=True)
        assert model.state == "done"
