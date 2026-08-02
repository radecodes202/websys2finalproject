"""Admin registration for the purchase-order / stock-receipt models.

The models themselves live in the ``product`` app (alongside the other
inventory-transaction models), but their admin surface is grouped here so the
whole purchasing workflow is configurable from one place.
"""
from django.contrib import admin

from product.models import (
    PurchaseOrder,
    PurchaseOrderItem,
    StockReceipt,
    StockReceiptItem,
    StockMovement,
)


class PurchaseOrderItemInline(admin.TabularInline):
    model = PurchaseOrderItem
    extra = 1
    fields = ('product', 'quantity_ordered', 'unit_cost')
    autocomplete_fields = ['product']


class StockReceiptItemInline(admin.TabularInline):
    model = StockReceiptItem
    extra = 0
    fields = ('purchase_order_item', 'quantity_received')
    autocomplete_fields = ['purchase_order_item']


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'supplier',
        'order_date',
        'expected_delivery_date',
        'status',
        'total_cost',
        'created_by',
    )
    list_filter = ('status', 'supplier', 'order_date')
    search_fields = ('supplier__name',)
    inlines = [PurchaseOrderItemInline]
    readonly_fields = ('created_by',)

    @admin.display(description='Total', ordering='items__unit_cost')
    def total_cost(self, obj):
        return obj.total_cost


@admin.register(StockReceipt)
class StockReceiptAdmin(admin.ModelAdmin):
    list_display = ('id', 'purchase_order', 'received_date', 'received_by')
    list_filter = ('received_date', 'received_by')
    inlines = [StockReceiptItemInline]


@admin.register(PurchaseOrderItem)
class PurchaseOrderItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'purchase_order', 'product', 'quantity_ordered', 'unit_cost', 'total_cost')
    list_filter = ('purchase_order', 'product')
    search_fields = ('product__name', 'purchase_order__id')
    autocomplete_fields = ['product']

    @admin.display(description='Line Total')
    def total_cost(self, obj):
        return obj.total_cost


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ('product', 'type', 'quantity_change', 'resulting_stock_level', 'timestamp', 'reference')
    list_filter = ('type', 'timestamp')
    search_fields = ('product__name', 'reference')
    readonly_fields = ('product', 'type', 'quantity_change', 'resulting_stock_level', 'reference', 'timestamp')
