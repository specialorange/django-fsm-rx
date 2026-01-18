"""
Backwards compatibility shim for django-fsm-log models.

This module provides a StateLog model that uses the EXISTING django_fsm_log_statelog
table, preserving all historical data from django-fsm-log installations.

Users migrating from django-fsm-log do NOT need to migrate their data - this shim
reads directly from the original table.

If you want to migrate to the new FSMTransitionLog table (optional), see the
migration guide in the documentation.
"""

from __future__ import annotations

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.timezone import now


class StateLog(models.Model):
    """
    Backwards-compatible StateLog model that uses the original django_fsm_log table.

    This model maintains the exact same schema as django-fsm-log's StateLog,
    allowing existing data to be read without migration.

    Field mappings to FSMTransitionLog:
    - state -> target_state
    - transition -> transition_name
    - source_state -> source_state
    - timestamp -> timestamp
    - by -> by
    - description -> description
    - content_type -> content_type
    - object_id -> object_id
    """

    timestamp = models.DateTimeField(default=now)
    by = models.ForeignKey(
        getattr(settings, "AUTH_USER_MODEL", "auth.User"),
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )
    source_state = models.CharField(
        max_length=255,
        db_index=True,
        null=True,
        blank=True,
        default=None,
    )
    state = models.CharField(
        "Target state",
        max_length=255,
        db_index=True,
    )
    transition = models.CharField(max_length=255)

    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
    )
    object_id = models.PositiveIntegerField(db_index=True)
    content_object = GenericForeignKey("content_type", "object_id")

    description = models.TextField(blank=True, null=True)

    class Meta:
        # Use the original django_fsm_log table
        app_label = "django_fsm_log"
        db_table = "django_fsm_log_statelog"
        managed = False  # Don't create/alter this table
        get_latest_by = "timestamp"
        ordering = ["-timestamp"]

    def __str__(self) -> str:
        return f"{self.timestamp} - {self.content_object} - {self.transition}"

    # Property aliases to match FSMTransitionLog field names
    @property
    def target_state(self) -> str:
        """Alias for 'state' to match FSMTransitionLog API."""
        return self.state

    @property
    def transition_name(self) -> str:
        """Alias for 'transition' to match FSMTransitionLog API."""
        return self.transition


__all__ = ["StateLog"]
