"""Forms for the purchase-order management workflow.

The PO header (supplier + expected delivery date) is handled by a regular
``ModelForm``.  Line items are edited via an ``inlineformset_factory`` so a
single create/update screen manages both the head and its lines in one POST.

The receiving screen is a *dynamic* ``forms.Form`` — one integer field is
generated per PO line, each capped at the line's remaining quantity, so the
user can never record more goods than were ordered.
"""
from django import forms
from django.core.exceptions import ValidationError
from django.db import transaction
from django.forms import inlineformset_factory

from product.models import (
    Product,
    PurchaseOrder,
    PurchaseOrderItem,
    StockReceipt,
    StockReceiptItem,
)


class PurchaseOrderForm(forms.ModelForm):
    """Header form for a purchase order (supplier + expected delivery date)."""

    class Meta:
        model = PurchaseOrder
        fields = ['supplier', 'expected_delivery_date']
        widgets = {
            'expected_delivery_date': forms.DateInput(attrs={'type': 'date'}),
        }


class PurchaseOrderItemForm(forms.ModelForm):
    """A single line on a purchase order.

    All three fields are marked ``required=False`` at the form level.  A line
    is only treated as "intended" when it has a positive quantity — this makes
    the inline formset robust to the extra blank rows that Django renders,
    regardless of whether the product ``<select>`` happens to render a blank
    first option.  Cross-form requirements (product present, unique product,
    no-empty-orderset) are enforced in :class:`BasePurchaseOrderItemFormSet`.
    """

    class Meta:
        model = PurchaseOrderItem
        fields = ['product', 'quantity_ordered', 'unit_cost']
        widgets = {
            'quantity_ordered': forms.NumberInput(attrs={'min': 1}),
            'unit_cost': forms.NumberInput(attrs={'step': '0.01', 'min': '0.00'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only active, purchasable products should be selectable.
        self.fields['product'].queryset = Product.objects.filter(is_active=True).order_by('name')
        # De-formalise validation to the formset level (see class docstring).
        self.fields['product'].required = False
        self.fields['quantity_ordered'].required = False
        self.fields['unit_cost'].required = False


class BasePurchaseOrderItemFormSet(forms.BaseInlineFormSet):
    """Inline formset for PO line items.

    A row counts as a *real* line only when it carries a positive quantity.
    This sidesteps the classic "extra blank forms trigger required errors"
    problem cleanly and predictably.
    """

    def clean(self):
        super().clean()
        seen_products = set()
        has_line = False
        for form in self.forms:
            if self.can_delete and form.cleaned_data.get('DELETE'):
                continue
            product = form.cleaned_data.get('product')
            qty = form.cleaned_data.get('quantity_ordered')
            cost = form.cleaned_data.get('unit_cost')
            # No quantity → blank extra row, ignore it entirely.
            if not qty:
                continue
            if qty < 1:
                form.add_error('quantity_ordered', 'Quantity ordered must be at least 1.')
                continue
            # Quantity present → this is an intended line; the rest is mandatory.
            if not product:
                form.add_error('product', 'Product is required for a line item.')
            elif product.pk in seen_products:
                form.add_error('product', 'This product is already on this purchase order.')
            else:
                seen_products.add(product.pk)
            if cost is None:
                form.add_error('unit_cost', 'Unit cost is required for a line item.')
            if product and product.pk not in seen_products and cost is not None:
                has_line = True
        if not has_line:
            raise ValidationError(
                'A purchase order must contain at least one line item.',
                code='too_few_forms',
            )


PurchaseOrderItemFormSet = inlineformset_factory(
    PurchaseOrder,
    PurchaseOrderItem,
    form=PurchaseOrderItemForm,
    formset=BasePurchaseOrderItemFormSet,
    extra=1,
    can_delete=True,
    fields=['product', 'quantity_ordered', 'unit_cost'],
)


class StockReceiptForm(forms.Form):
    """Dynamic receiving form.

    One ``IntegerField`` is created per PO line, capped at the line's
    *remaining* quantity, with a sensible initial value of "everything still
    outstanding".  The user can never receive more than was ordered.
    """

    def __init__(self, *args, po=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.po = po
        if po is not None:
            for item in po.items.select_related('product').all():
                remaining = item.remaining_quantity
                field_name = f'item_{item.pk}'
                self.fields[field_name] = forms.IntegerField(
                    min_value=0,
                    max_value=remaining,
                    initial=remaining,
                    required=False,
                    label=f'{item.product.name} ({item.product.sku})',
                    help_text=(
                        f'Ordered: {item.quantity_ordered} | '
                        f'Received: {item.received_quantity} | '
                        f'Remaining: {remaining}'
                    ),
                )
                # Stash the model instance so the view can map values back to it.
                self.fields[field_name].extra_item = item

    def clean(self):
        cleaned = super().clean()
        total_received = 0
        for name, value in cleaned.items():
            if name.startswith('item_') and value:
                total_received += value
        if total_received == 0:
            raise ValidationError('Please enter at least one received quantity.')
        return cleaned

    def save(self, received_by=None):
        """Create a ``StockReceipt`` + line items and apply them to stock."""
        receipt = None
        with transaction.atomic():
            receipt = StockReceipt.objects.create(
                purchase_order=self.po,
                received_by=received_by,
            )
            for name, value in self.cleaned_data.items():
                if not name.startswith('item_') or not value:
                    continue
                item = self.fields[name].extra_item
                StockReceiptItem.objects.create(
                    stock_receipt=receipt,
                    purchase_order_item=item,
                    quantity_received=value,
                )
            # ``receive()`` atomically updates stock, movements & PO status.
            receipt.receive()
        return receipt
