from django.conf import settings
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _
from django.utils import timezone


class User(AbstractUser):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('manager', 'Manager'),
        ('cashier', 'Cashier'),
        ('inventory_staff', 'Inventory Staff'),
    ]

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='cashier',
        verbose_name=_('Role')
    )
    is_approved = models.BooleanField(
        default=False,
        verbose_name=_('Approved'),
        help_text=_('Designates whether this user account has been approved by an administrator.')
    )
    date_requested = models.DateTimeField(
        default=timezone.now,
        verbose_name=_('Date Requested'),
        help_text=_('Date and time the user registered.')
    )

    class Meta:
        verbose_name = _('User')
        verbose_name_plural = _('Users')

    def __str__(self):
        return self.username

    def save(self, *args, **kwargs):
        # For new users, if not staff/superuser, set is_approved=False (default)
        # For staff/superusers, auto-approve
        if not self.pk:
            if self.is_staff or self.is_superuser:
                self.is_approved = True
                # If superuser, set role to admin
                if self.is_superuser:
                    self.role = 'admin'
        super().save(*args, **kwargs)

    @property
    def is_admin(self):
        return self.role == 'admin'

    @property
    def is_manager(self):
        return self.role == 'manager'

    @property
    def is_cashier(self):
        return self.role == 'cashier'

    @property
    def is_inventory_staff(self):
        return self.role == 'inventory_staff'


class ActivityLog(models.Model):
    ACTION_CREATE = 'create'
    ACTION_UPDATE = 'update'
    ACTION_DELETE = 'delete'
    ACTION_LOGIN = 'login'
    ACTION_LOGOUT = 'logout'

    ACTION_CHOICES = [
        (ACTION_CREATE, 'Create'),
        (ACTION_UPDATE, 'Update'),
        (ACTION_DELETE, 'Delete'),
        (ACTION_LOGIN, 'Login'),
        (ACTION_LOGOUT, 'Logout'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='activity_logs',
        verbose_name=_('User')
    )
    action = models.CharField(
        max_length=20,
        choices=ACTION_CHOICES,
        verbose_name=_('Action')
    )
    model_name = models.CharField(
        max_length=100,
        verbose_name=_('Model')
    )
    object_id = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name=_('Object ID')
    )
    before_snapshot = models.JSONField(
        null=True,
        blank=True,
        verbose_name=_('Before Snapshot')
    )
    after_snapshot = models.JSONField(
        null=True,
        blank=True,
        verbose_name=_('After Snapshot')
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Timestamp')
    )

    class Meta:
        ordering = ['-timestamp']
        verbose_name = _('Activity Log')
        verbose_name_plural = _('Activity Logs')

    def __str__(self):
        return f'{self.user or "System"} - {self.action} - {self.model_name}'
