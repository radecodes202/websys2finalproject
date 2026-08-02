"""
Audit Trail models.

This module defines the :class:`AuditLog` model — an append-only record of
every meaningful state-changing action that occurs in the application.

Design goals
------------
* **Who** – the authenticated user (or ``None`` for system/anonymous actions).
* **What** – the action type (create, update, delete, login, …) and a
  human-readable description.
* **To which record** – a generic relation via ``ContentType`` + ``object_id``,
  plus a denormalised ``object_repr`` string so the log remains readable even
  after the target row is deleted.
* **When** – ``timestamp`` (auto, indexed).
* **From where** – ``ip_address`` and ``user_agent`` captured by middleware.
* **What changed** – ``changes`` JSONField holding a structured before/after
  diff, e.g. ``{"stock_quantity": {"old": 50, "new": 45}}``.

The model is **append-only**: ``save()`` refuses updates and ``delete()``
refuses removal from the application layer, protecting the audit trail from
tampering.
"""
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.translation import gettext_lazy as _


class AppendOnlyQuerySet(models.QuerySet):
    """QuerySet that blocks bulk deletion of audit-log entries."""

    def delete(self):
        raise PermissionError(
            'AuditLog entries are append-only and cannot be deleted.'
        )


class AppendOnlyManager(models.Manager):
    """Manager that blocks bulk deletion of audit-log entries."""

    def get_queryset(self):
        return AppendOnlyQuerySet(self.model, using=self._db)

    def delete(self):
        """Prevent bulk deletion via the manager."""
        raise PermissionError(
            'AuditLog entries are append-only and cannot be deleted.'
        )


class AuditLog(models.Model):
    """An immutable, append-only audit-trail entry."""

    # Use the append-only manager that blocks bulk deletion.
    objects = AppendOnlyManager()

    # ------------------------------------------------------------------ #
    # Action choices
    # ------------------------------------------------------------------ #
    ACTION_CREATE = 'CREATE'
    ACTION_UPDATE = 'UPDATE'
    ACTION_DELETE = 'DELETE'
    ACTION_LOGIN = 'LOGIN'
    ACTION_LOGOUT = 'LOGOUT'
    ACTION_LOGIN_FAILED = 'LOGIN_FAILED'
    ACTION_STATUS_CHANGE = 'STATUS_CHANGE'
    ACTION_STOCK_ADJUSTMENT = 'STOCK_ADJUSTMENT'
    ACTION_PAYMENT = 'PAYMENT'
    ACTION_OTHER = 'OTHER'

    ACTION_CHOICES = [
        (ACTION_CREATE, _('Create')),
        (ACTION_UPDATE, _('Update')),
        (ACTION_DELETE, _('Delete')),
        (ACTION_LOGIN, _('Login')),
        (ACTION_LOGOUT, _('Logout')),
        (ACTION_LOGIN_FAILED, _('Failed Login')),
        (ACTION_STATUS_CHANGE, _('Status Change')),
        (ACTION_STOCK_ADJUSTMENT, _('Stock Adjustment')),
        (ACTION_PAYMENT, _('Payment')),
        (ACTION_OTHER, _('Other')),
    ]

    # ------------------------------------------------------------------ #
    # Severity choices
    # ------------------------------------------------------------------ #
    SEVERITY_INFO = 'INFO'
    SEVERITY_WARNING = 'WARNING'
    SEVERITY_CRITICAL = 'CRITICAL'

    SEVERITY_CHOICES = [
        (SEVERITY_INFO, _('Info')),
        (SEVERITY_WARNING, _('Warning')),
        (SEVERITY_CRITICAL, _('Critical')),
    ]

    # ------------------------------------------------------------------ #
    # Fields
    # ------------------------------------------------------------------ #
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
        verbose_name=_('User'),
    )
    username_snapshot = models.CharField(
        max_length=150,
        blank=True,
        default='',
        verbose_name=_('Username Snapshot'),
        help_text=_('Username stored as text in case the user account is later deleted.'),
    )
    action = models.CharField(
        max_length=20,
        choices=ACTION_CHOICES,
        db_index=True,
        verbose_name=_('Action'),
    )
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
        verbose_name=_('Content Type'),
    )
    object_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        db_index=True,
        verbose_name=_('Object ID'),
    )
    object_repr = models.CharField(
        max_length=255,
        blank=True,
        default='',
        verbose_name=_('Object Representation'),
        help_text=_('Human-readable string of the affected object, e.g. "Product: Sony WH-1000XM5".'),
    )
    changes = models.JSONField(
        null=True,
        blank=True,
        default=dict,
        verbose_name=_('Changes'),
        help_text=_('Structured before/after diff, e.g. {"stock_quantity": {"old": 50, "new": 45}}.'),
    )
    description = models.TextField(
        blank=True,
        default='',
        verbose_name=_('Description'),
        help_text=_('Short human-readable summary of the action.'),
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name=_('IP Address'),
    )
    user_agent = models.CharField(
        max_length=512,
        blank=True,
        default='',
        verbose_name=_('User Agent'),
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name=_('Timestamp'),
    )
    severity = models.CharField(
        max_length=10,
        choices=SEVERITY_CHOICES,
        default=SEVERITY_INFO,
        verbose_name=_('Severity'),
    )

    class Meta:
        ordering = ['-timestamp']
        verbose_name = _('Audit Log')
        verbose_name_plural = _('Audit Logs')
        indexes = [
            models.Index(fields=['user'], name='audit_log_user_idx'),
            models.Index(fields=['action'], name='audit_log_action_idx'),
            models.Index(fields=['content_type'], name='audit_log_ct_idx'),
            models.Index(fields=['timestamp'], name='audit_log_ts_idx'),
        ]

    def __str__(self):
        return f'{self.username_snapshot or "System"} | {self.get_action_display()} | {self.object_repr}'

    # ------------------------------------------------------------------ #
    # Append-only enforcement
    # ------------------------------------------------------------------ #
    def save(self, *args, **kwargs):
        """Allow inserts only — existing rows may never be modified."""
        if self.pk is not None:
            raise PermissionError(
                'AuditLog entries are append-only and cannot be modified.'
            )
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Prevent deletion of audit-log entries from the application layer."""
        raise PermissionError(
            'AuditLog entries are append-only and cannot be deleted.'
        )

    # ------------------------------------------------------------------ #
    # Convenience helpers
    # ------------------------------------------------------------------ #
    @property
    def module_name(self):
        """Return the app label of the affected content type, if available."""
        if self.content_type:
            return self.content_type.app_label
        return ''

    @property
    def model_name(self):
        """Return the model name of the affected content type, if available."""
        if self.content_type:
            return self.content_type.model
        return ''

    @property
    def formatted_changes(self):
        """
        Return the ``changes`` dict as a list of ``(field, old, new)`` tuples
        suitable for rendering in a template table. Returns an empty list when
        there are no recorded changes.
        """
        changes = self.changes or {}
        rows = []
        for field, values in changes.items():
            if isinstance(values, dict) and ('old' in values or 'new' in values):
                rows.append((field, values.get('old'), values.get('new')))
            else:
                # Non-diff value (e.g. a plain marker) — show as-is.
                rows.append((field, None, values))
        return rows