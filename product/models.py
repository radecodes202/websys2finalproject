from datetime import timedelta
from decimal import Decimal
from django.conf import settings
from django.db import models, transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from category.models import Category
from customer.models import Customer
from supplier.models import Supplier

# Audit-trail logging (imported lazily-safe: log_activity isolates errors
# so a logging failure never breaks the business transaction).
from audit.services import log_activity
from audit.models import AuditLog


class Product(models.Model):
    expiration_date = models.DateField(
        blank=True,
        null=True,
        verbose_name=_('Expiration Date')
    )

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
    code = models.CharField(
        max_length=50,
        unique=True,
        blank=True,
        null=True,
        verbose_name=_('Code')
    )
    barcode = models.CharField(
        max_length=50,
        unique=True,
        blank=True,
        null=True,
        verbose_name=_('Barcode')
    )
    cost_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('Cost Price')
    )
    unit_of_measure = models.CharField(
        max_length=50,
        default='pcs',
        verbose_name=_('Unit of Measure')
    )
    image = models.ImageField(
        upload_to='products/',
        blank=True,
        null=True,
        verbose_name=_('Image')
    )
    preferred_supplier = models.ForeignKey(
        Supplier,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='preferred_products',
        verbose_name=_('Preferred Supplier')
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

    def create_alerts(self):
        alerts = []

        if self.quantity_in_stock <= self.reorder_level:
            alerts.append({
                'type': 'low_stock',
                'message': f'{self.name} is below its reorder level.',
            })

        if self.expiration_date:
            remaining_days = (self.expiration_date - timezone.now().date()).days
            if remaining_days <= 7:
                alerts.append({
                    'type': 'expiring',
                    'message': f'{self.name} expires in {remaining_days} day(s).',
                })

        for alert_data in alerts:
            Alert.objects.get_or_create(
                product=self,
                type=alert_data['type'],
                defaults={'message': alert_data['message']},
            )


class Alert(models.Model):
    TYPE_LOW_STOCK = 'low_stock'
    TYPE_EXPIRING = 'expiring'
    TYPE_EXPIRED = 'expired'

    TYPE_CHOICES = [
        (TYPE_LOW_STOCK, 'Low Stock'),
        (TYPE_EXPIRING, 'Expiring'),
        (TYPE_EXPIRED, 'Expired'),
    ]

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='alerts',
        verbose_name=_('Product')
    )
    type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        verbose_name=_('Type')
    )
    message = models.TextField(
        verbose_name=_('Message')
    )
    is_resolved = models.BooleanField(
        default=False,
        verbose_name=_('Resolved')
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created At')
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.product.name} - {self.type}'


class PurchaseOrder(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_PARTIAL = 'partial'
    STATUS_RECEIVED = 'received'
    STATUS_CANCELLED = 'cancelled'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_PARTIAL, 'Partially Received'),
        (STATUS_RECEIVED, 'Received'),
        (STATUS_CANCELLED, 'Cancelled'),
    ]

    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.PROTECT,
        related_name='purchase_orders',
        verbose_name=_('Supplier')
    )
    order_date = models.DateField(
        auto_now_add=True,
        verbose_name=_('Order Date')
    )
    expected_delivery_date = models.DateField(
        verbose_name=_('Expected Delivery Date')
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        verbose_name=_('Status')
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_purchase_orders',
        verbose_name=_('Created By')
    )

    class Meta:
        ordering = ['-order_date']

    def __str__(self):
        return f'PO-{self.pk} ({self.supplier.name})'

    @property
    def total_cost(self):
        """Sum of every line item (quantity ordered x unit cost)."""
        return sum((item.total_cost for item in self.items.all()), Decimal('0.00'))

    @property
    def total_items(self):
        """Number of line items on this purchase order."""
        return self.items.count()

    def can_cancel(self):
        """A purchase order may only be cancelled before any goods are received."""
        return self.status == self.STATUS_PENDING

    def can_be_received(self):
        """Goods may be received into a pending or partially-received PO."""
        return self.status in (self.STATUS_PENDING, self.STATUS_PARTIAL)

    def cancel(self, cancelled_by=None):
        """Transition the PO to ``cancelled`` and log the status change.

        Only ``pending`` orders can be cancelled — once goods have been
        (partially) received the inventory has already moved, so cancellation
        is refused to avoid leaving the stock ledger inconsistent.
        """
        if not self.can_cancel():
            raise ValueError('Only purchase orders in "pending" status can be cancelled.')
        old_status = self.status
        self.status = self.STATUS_CANCELLED
        self.save(update_fields=['status'])
        log_activity(
            user=cancelled_by,
            action=AuditLog.ACTION_STATUS_CHANGE,
            instance=self,
            description=(
                f'Purchase Order PO-{self.pk} was cancelled '
                f'(status changed from "{old_status}" to "{self.STATUS_CANCELLED}").'
            ),
            changes={'status': {'old': old_status, 'new': self.STATUS_CANCELLED}},
            severity=AuditLog.SEVERITY_WARNING,
        )


class PurchaseOrderItem(models.Model):
    purchase_order = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name=_('Purchase Order')
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name='purchase_order_items',
        verbose_name=_('Product')
    )
    quantity_ordered = models.PositiveIntegerField(
        verbose_name=_('Quantity Ordered')
    )
    unit_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('Unit Cost')
    )

    class Meta:
        verbose_name = _('Purchase Order Item')
        verbose_name_plural = _('Purchase Order Items')

    def __str__(self):
        return f'{self.product.name} x {self.quantity_ordered}'

    @property
    def total_cost(self):
        """Line total = ordered quantity x unit cost."""
        return self.quantity_ordered * self.unit_cost

    @property
    def received_quantity(self):
        """Quantity already received for this line across all receipts."""
        return sum((r.quantity_received for r in self.receipts.all()), 0)

    @property
    def remaining_quantity(self):
        """Quantity still outstanding before this line is fully received."""
        return max(self.quantity_ordered - self.received_quantity, 0)

    @property
    def is_fully_received(self):
        """True once the received quantity meets or exceeds the ordered quantity."""
        return self.received_quantity >= self.quantity_ordered


class StockReceipt(models.Model):
    purchase_order = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.CASCADE,
        related_name='stock_receipts',
        verbose_name=_('Purchase Order')
    )
    received_date = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Received Date')
    )
    received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='received_stock_receipts',
        verbose_name=_('Received By')
    )

    class Meta:
        ordering = ['-received_date']

    def __str__(self):
        return f'Stock Receipt {self.pk}'

    def receive(self):
        with transaction.atomic():
            total_ordered = 0
            total_received = 0
            for item in self.items.all():
                quantity_received = item.quantity_received
                if quantity_received < 0:
                    raise ValueError('Received quantity cannot be negative.')

                purchase_order_item = item.purchase_order_item
                total_ordered += purchase_order_item.quantity_ordered
                total_received += quantity_received

                product = purchase_order_item.product
                old_stock = product.quantity_in_stock
                product.quantity_in_stock += quantity_received
                product.save(update_fields=['quantity_in_stock'])
                product.create_alerts()

                StockMovement.objects.create(
                    product=product,
                    type='purchase',
                    quantity_change=quantity_received,
                    resulting_stock_level=product.quantity_in_stock,
                    reference=f'StockReceipt-{self.pk}',
                )

                log_activity(
                    action=AuditLog.ACTION_STOCK_ADJUSTMENT,
                    instance=product,
                    description=(
                        f'Added {quantity_received} units to {product.name} '
                        f'due to Stock Receipt #{self.pk} (PO-{self.purchase_order_id}).'
                    ),
                    changes={
                        'quantity_in_stock': {
                            'old': old_stock,
                            'new': product.quantity_in_stock,
                        },
                        'source': f'StockReceipt-{self.pk}',
                    },
                    severity=AuditLog.SEVERITY_INFO,
                )

            # Status is derived from the *whole* purchase order (ordered vs
            # received across every receipt), not just this receipt, so that
            # partial deliveries spread across multiple receipts are accounted
            # for correctly.
            po = self.purchase_order
            po_total_ordered = sum((i.quantity_ordered for i in po.items.all()), 0)
            po_total_received = sum((i.received_quantity for i in po.items.all()), 0)

            if po_total_ordered == 0:
                new_status = PurchaseOrder.STATUS_PENDING
            elif po_total_received < po_total_ordered:
                new_status = PurchaseOrder.STATUS_PARTIAL
            else:
                new_status = PurchaseOrder.STATUS_RECEIVED

            old_status = self.purchase_order.status
            self.purchase_order.status = new_status
            self.purchase_order.save(update_fields=['status'])

            if old_status != new_status:
                log_activity(
                    action=AuditLog.ACTION_STATUS_CHANGE,
                    instance=self.purchase_order,
                    description=(
                        f'Purchase Order PO-{self.purchase_order_id} status changed '
                        f'from "{old_status}" to "{new_status}" via Stock Receipt #{self.pk}.'
                    ),
                    changes={
                        'status': {'old': old_status, 'new': new_status},
                    },
                    severity=AuditLog.SEVERITY_INFO,
                )


class StockReceiptItem(models.Model):
    stock_receipt = models.ForeignKey(
        StockReceipt,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name=_('Stock Receipt')
    )
    purchase_order_item = models.ForeignKey(
        PurchaseOrderItem,
        on_delete=models.PROTECT,
        related_name='receipts',
        verbose_name=_('Purchase Order Item')
    )
    quantity_received = models.PositiveIntegerField(
        verbose_name=_('Quantity Received')
    )

    class Meta:
        verbose_name = _('Stock Receipt Item')
        verbose_name_plural = _('Stock Receipt Items')

    def __str__(self):
        return f'{self.purchase_order_item.product.name} x {self.quantity_received}'


class StockMovement(models.Model):
    MOVEMENT_TYPE_PURCHASE = 'purchase'
    MOVEMENT_TYPE_SALE = 'sale'
    MOVEMENT_TYPE_ADJUSTMENT = 'adjustment'
    MOVEMENT_TYPE_RETURN = 'return'

    MOVEMENT_TYPE_CHOICES = [
        (MOVEMENT_TYPE_PURCHASE, 'Purchase'),
        (MOVEMENT_TYPE_SALE, 'Sale'),
        (MOVEMENT_TYPE_ADJUSTMENT, 'Adjustment'),
        (MOVEMENT_TYPE_RETURN, 'Return'),
    ]

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='stock_movements',
        verbose_name=_('Product')
    )
    type = models.CharField(
        max_length=20,
        choices=MOVEMENT_TYPE_CHOICES,
        default=MOVEMENT_TYPE_PURCHASE,
        verbose_name=_('Type')
    )
    quantity_change = models.IntegerField(
        verbose_name=_('Quantity Change')
    )
    resulting_stock_level = models.PositiveIntegerField(
        verbose_name=_('Resulting Stock Level')
    )
    reference = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Reference')
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Timestamp')
    )

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f'{self.product.name} {self.type}'


class Sale(models.Model):
    STATUS_COMPLETED = 'completed'
    STATUS_PENDING = 'pending'
    STATUS_CANCELLED = 'cancelled'

    STATUS_CHOICES = [
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_PENDING, 'Pending'),
        (STATUS_CANCELLED, 'Cancelled'),
    ]

    date = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Date')
    )
    cashier = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sales',
        verbose_name=_('Cashier')
    )
    customer = models.ForeignKey(
        Customer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sales',
        verbose_name=_('Customer')
    )
    payment_method = models.CharField(
        max_length=20,
        default='cash',
        verbose_name=_('Payment Method')
    )
    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('Subtotal')
    )
    tax = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('Tax')
    )
    discount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('Discount')
    )
    total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('Total')
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        verbose_name=_('Status')
    )

    class Meta:
        ordering = ['-date']

    def complete_checkout(self):
        with transaction.atomic():
            for item in self.items.all():
                if item.quantity > item.product.quantity_in_stock:
                    raise ValueError(f'Insufficient stock for {item.product.name}.')

            for item in self.items.all():
                old_stock = item.product.quantity_in_stock
                item.product.quantity_in_stock -= item.quantity
                item.product.save(update_fields=['quantity_in_stock'])
                item.product.create_alerts()
                StockMovement.objects.create(
                    product=item.product,
                    type='sale',
                    quantity_change=-item.quantity,
                    resulting_stock_level=item.product.quantity_in_stock,
                    reference=f'Sale-{self.pk}',
                )

                log_activity(
                    action=AuditLog.ACTION_STOCK_ADJUSTMENT,
                    instance=item.product,
                    description=(
                        f'Deducted {item.quantity} units of {item.product.name} '
                        f'due to Sale #{self.pk}.'
                    ),
                    changes={
                        'quantity_in_stock': {
                            'old': old_stock,
                            'new': item.product.quantity_in_stock,
                        },
                        'source': f'Sale-{self.pk}',
                    },
                    severity=AuditLog.SEVERITY_INFO,
                )

            old_status = self.status
            self.status = self.STATUS_COMPLETED
            self.save(update_fields=['status'])

            log_activity(
                action=AuditLog.ACTION_STATUS_CHANGE,
                instance=self,
                description=(
                    f'Sale #{self.pk} checkout completed — status changed '
                    f'from "{old_status}" to "{self.STATUS_COMPLETED}".'
                ),
                changes={
                    'status': {'old': old_status, 'new': self.STATUS_COMPLETED},
                },
                severity=AuditLog.SEVERITY_INFO,
            )

    def __str__(self):
        return f'Sale {self.pk}'


class SaleItem(models.Model):
    sale = models.ForeignKey(
        Sale,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name=_('Sale')
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name='sale_items',
        verbose_name=_('Product')
    )
    quantity = models.PositiveIntegerField(
        verbose_name=_('Quantity')
    )
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name=_('Unit Price')
    )
    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name=_('Subtotal')
    )

    class Meta:
        verbose_name = _('Sale Item')
        verbose_name_plural = _('Sale Items')

    def __str__(self):
        return f'{self.product.name} x {self.quantity}'


class Payment(models.Model):
    METHOD_CASH = 'cash'
    METHOD_CARD = 'card'
    METHOD_GCASH = 'gcash'

    METHOD_CHOICES = [
        (METHOD_CASH, 'Cash'),
        (METHOD_CARD, 'Card'),
        (METHOD_GCASH, 'GCash'),
    ]

    sale = models.ForeignKey(
        Sale,
        on_delete=models.CASCADE,
        related_name='payments',
        verbose_name=_('Sale')
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name=_('Amount')
    )
    method = models.CharField(
        max_length=20,
        choices=METHOD_CHOICES,
        default=METHOD_CASH,
        verbose_name=_('Method')
    )
    reference_number = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_('Reference Number')
    )
    change_given = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('Change Given')
    )

    class Meta:
        ordering = ['-sale__date']

    def __str__(self):
        return f'Payment {self.pk} for Sale {self.sale_id}'