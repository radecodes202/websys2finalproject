from django.db import models
from django.utils.translation import gettext_lazy as _
from category.models import Category


class Product(models.Model):
    name = models.CharField(
        max_length=200,
        verbose_name=_('Name')
    )
    description = models.TextField(
        blank=True,
        verbose_name=_('Description')
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name='products',
        verbose_name=_('Category')
    )
    sku = models.CharField(
        max_length=50,
        unique=True,
        verbose_name=_('SKU')
    )
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name=_('Unit Price')
    )
    quantity_in_stock = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Quantity in Stock')
    )
    reorder_level = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Reorder Level')
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
        verbose_name = _('Product')
        verbose_name_plural = _('Products')
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def is_low_stock(self):
        return self.quantity_in_stock <= self.reorder_level