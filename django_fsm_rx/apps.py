from __future__ import annotations

from django.apps import AppConfig


class DjangoFsmRxConfig(AppConfig):
    """Django application configuration for django-fsm-rx."""

    name = "django_fsm_rx"
    verbose_name = "Django FSM RX"
    default_auto_field = "django.db.models.BigAutoField"
