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
