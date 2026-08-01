from decimal import Decimal
from django.db import models
from django.utils.translation import gettext_lazy as _


class Supplier(models.Model):
    outstanding_balance = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('Outstanding Balance')
    )

    name = models.CharField(
        max_length=200,
        verbose_name=_('Supplier Name')
    )
    contact_person = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Contact Person')
    )
    email = models.EmailField(
        blank=True,
        verbose_name=_('Email')
    )
    phone = models.CharField(
        max_length=20,
        blank=True,
        verbose_name=_('Phone Number')
    )
    address = models.TextField(
        blank=True,
        verbose_name=_('Address')
    )
    city = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('City')
    )
    postal_code = models.CharField(
        max_length=20,
        blank=True,
        verbose_name=_('Postal Code')
    )
    country = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Country')
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Is Active')
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created At')
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Updated At')
    )

    class Meta:
        verbose_name = _('Supplier')
        verbose_name_plural = _('Suppliers')
        ordering = ['name']

    def __str__(self):
        return self.name


class SupplierPayment(models.Model):
    STATUS_PAID = 'paid'
    STATUS_PARTIAL = 'partial'
    STATUS_PENDING = 'pending'

    STATUS_CHOICES = [
        (STATUS_PAID, 'Paid'),
        (STATUS_PARTIAL, 'Partial'),
        (STATUS_PENDING, 'Pending'),
    ]

    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.CASCADE,
        related_name='payments',
        verbose_name=_('Supplier')
    )
    purchase_order = models.ForeignKey(
        'product.PurchaseOrder',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='supplier_payments',
        verbose_name=_('Purchase Order')
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name=_('Amount')
    )
    date = models.DateField(
        auto_now_add=True,
        verbose_name=_('Date')
    )
    method = models.CharField(
        max_length=20,
        default='cash',
        verbose_name=_('Method')
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        verbose_name=_('Status')
    )

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f'{self.supplier.name} - {self.amount}'