from decimal import Decimal

from django import forms
from django.contrib import messages
from django.db import models, transaction
from django.shortcuts import redirect, render, get_object_or_404
from django.views import View
from django.views.generic import DetailView, ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from accounts.mixins import RoleRequiredMixin
from category.models import Category
from supplier.models import Supplier
from audit.models import AuditLog
from audit.services import log_activity
from .models import Alert, Payment, Product, Sale, SaleItem, StockMovement


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            'name', 'description', 'category', 'sku', 'code', 'barcode', 'cost_price',
            'unit_of_measure', 'image', 'preferred_supplier', 'unit_price',
            'quantity_in_stock', 'reorder_level', 'is_active',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in ['code', 'barcode', 'cost_price', 'unit_of_measure', 'image', 'preferred_supplier']:
            self.fields[field_name].required = False


class AlertListView(RoleRequiredMixin, ListView):
    model = Alert
    template_name = 'product/alert_list.html'
    context_object_name = 'alerts'
    paginate_by = 20
    allowed_roles = ['admin', 'manager', 'inventory_staff']

    def get_queryset(self):
        queryset = Alert.objects.select_related('product').all()
        alert_type = self.request.GET.get('type')
        if alert_type in dict(Alert.TYPE_CHOICES):
            queryset = queryset.filter(type=alert_type)
        is_resolved = self.request.GET.get('resolved')
        if is_resolved == 'true':
            queryset = queryset.filter(is_resolved=True)
        elif is_resolved == 'false':
            queryset = queryset.filter(is_resolved=False)
        return queryset.order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['type_choices'] = Alert.TYPE_CHOICES
        context['selected_type'] = self.request.GET.get('type', '')
        context['selected_resolved'] = self.request.GET.get('resolved', '')
        return context


class AlertResolveView(RoleRequiredMixin, View):
    """Mark an alert as resolved."""
    allowed_roles = ['admin', 'manager', 'inventory_staff']

    def post(self, request, pk):
        alert = get_object_or_404(Alert, pk=pk)
        if not alert.is_resolved:
            alert.is_resolved = True
            alert.save(update_fields=['is_resolved'])
            log_activity(
                user=request.user,
                action=AuditLog.ACTION_UPDATE,
                instance=alert,
                description=f'Alert for {alert.product.name} ({alert.type}) marked as resolved.',
                changes={'is_resolved': {'old': False, 'new': True}},
                severity=AuditLog.SEVERITY_INFO,
            )
            messages.success(request, 'Alert marked as resolved.')
        else:
            messages.info(request, 'Alert is already resolved.')
        return redirect('product:alert-list')


class ProductListView(RoleRequiredMixin, ListView):
    model = Product
    template_name = 'product/product_list.html'
    context_object_name = 'products'
    paginate_by = 10
    allowed_roles = ['admin', 'manager', 'inventory_staff']

    def get_queryset(self):
        queryset = super().get_queryset()
        search_query = self.request.GET.get('search')
        category = self.request.GET.get('category')
        stock_status = self.request.GET.get('stock_status')
        supplier = self.request.GET.get('supplier')

        if search_query:
            queryset = queryset.filter(name__icontains=search_query)
        if category:
            queryset = queryset.filter(category_id=category)
        if supplier:
            queryset = queryset.filter(preferred_supplier_id=supplier)
        if stock_status == 'low':
            queryset = queryset.filter(quantity_in_stock__lte=models.F('reorder_level'))
        elif stock_status == 'in_stock':
            queryset = queryset.filter(quantity_in_stock__gt=models.F('reorder_level'))
        elif stock_status == 'out':
            queryset = queryset.filter(quantity_in_stock=0)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        context['suppliers'] = Supplier.objects.all()
        return context


class ProductDetailView(RoleRequiredMixin, DetailView):
    model = Product
    template_name = 'product/product_detail.html'
    context_object_name = 'product'
    allowed_roles = ['admin', 'manager', 'inventory_staff']


class ProductCreateView(RoleRequiredMixin, CreateView):
    model = Product
    template_name = 'product/product_form.html'
    form_class = ProductForm
    success_url = reverse_lazy('product:product-list')
    allowed_roles = ['admin', 'manager', 'inventory_staff']


class ProductUpdateView(RoleRequiredMixin, UpdateView):
    model = Product
    template_name = 'product/product_form.html'
    form_class = ProductForm
    success_url = reverse_lazy('product:product-list')
    allowed_roles = ['admin', 'manager', 'inventory_staff']


class ProductDeleteView(RoleRequiredMixin, DeleteView):
    model = Product
    template_name = 'product/product_confirm_delete.html'
    success_url = reverse_lazy('product:product-list')
    allowed_roles = ['admin', 'manager', 'inventory_staff']


class POSView(RoleRequiredMixin, View):
    template_name = 'product/pos.html'
    allowed_roles = ['admin', 'manager', 'cashier']

    def get(self, request):
        cart = request.session.get('pos_cart', [])
        cart_items = []
        total = Decimal('0.00')
        for entry in cart:
            product = get_object_or_404(Product, pk=entry['product_id'])
            quantity = int(entry['quantity'])
            subtotal = product.unit_price * quantity
            total += subtotal
            cart_items.append({
                'product': product,
                'quantity': quantity,
                'subtotal': subtotal,
            })

        products = Product.objects.filter(is_active=True).order_by('name')
        return render(request, self.template_name, {
            'products': products,
            'cart_items': cart_items,
            'cart_total': total,
        })

    def post(self, request):
        action = request.POST.get('action')

        if action == 'add_to_cart':
            product_id = request.POST.get('product_id')
            quantity = int(request.POST.get('quantity', 1) or 1)
            if product_id:
                cart = list(request.session.get('pos_cart', []))
                existing = next((item for item in cart if item['product_id'] == int(product_id)), None)
                if existing:
                    existing['quantity'] += quantity
                else:
                    cart.append({'product_id': int(product_id), 'quantity': quantity})
                request.session['pos_cart'] = cart
            messages.success(request, 'Item added to cart.')
            return redirect('product:pos')

        if action == 'checkout':
            cart = list(request.session.get('pos_cart', []))
            if not cart:
                messages.error(request, 'Your cart is empty.')
                return redirect('product:pos')

            subtotal = Decimal('0.00')
            sale_items = []
            for entry in cart:
                product = get_object_or_404(Product, pk=entry['product_id'])
                quantity = int(entry['quantity'])
                line_total = product.unit_price * quantity
                subtotal += line_total
                sale_items.append((product, quantity, line_total))

            discount = Decimal(request.POST.get('discount', '0.00') or '0.00')
            total = subtotal - discount
            sale = Sale.objects.create(
                cashier=request.user,
                payment_method=request.POST.get('payment_method', 'cash'),
                subtotal=subtotal,
                tax=Decimal('0.00'),
                discount=discount,
                total=total,
                status='pending',
            )

            for product, quantity, line_total in sale_items:
                SaleItem.objects.create(
                    sale=sale,
                    product=product,
                    quantity=quantity,
                    unit_price=product.unit_price,
                    subtotal=line_total,
                )

            amount_tendered = Decimal(request.POST.get('amount_tendered', total) or total)
            Payment.objects.create(
                sale=sale,
                amount=amount_tendered,
                method=sale.payment_method,
                reference_number='POS-{}'.format(sale.pk),
                change_given=max(Decimal('0.00'), amount_tendered - total),
            )

            try:
                sale.complete_checkout()
            except ValueError as exc:
                messages.error(request, str(exc))
                return redirect('product:pos')

            request.session['pos_cart'] = []
            messages.success(request, 'Checkout completed successfully.')
            return redirect('product:receipt', sale.pk)

        messages.error(request, 'Unsupported action.')
        return redirect('product:pos')


class SaleCancelView(RoleRequiredMixin, View):
    """Manager or Admin cancels a completed sale and restores stock."""
    template_name = 'product/sale_confirm_cancel.html'
    allowed_roles = ['admin', 'manager']

    def get(self, request, pk):
        sale = get_object_or_404(Sale, pk=pk)
        if sale.status != Sale.STATUS_COMPLETED:
            messages.error(request, f'Sale #{sale.pk} cannot be cancelled (status: {sale.get_status_display()}).')
            return redirect('product:product-list')
        return render(request, self.template_name, {'sale': sale})

    @transaction.atomic
    def post(self, request, pk):
        sale = get_object_or_404(Sale, pk=pk)
        if sale.status != Sale.STATUS_COMPLETED:
            messages.error(request, f'Sale #{sale.pk} cannot be cancelled (status: {sale.get_status_display()}).')
            return redirect('product:product-list')

        for item in sale.items.all():
            product = item.product
            old_stock = product.quantity_in_stock
            product.quantity_in_stock += item.quantity
            product.save(update_fields=['quantity_in_stock'])
            product.create_alerts()
            StockMovement.objects.create(
                product=product,
                type='return',
                quantity_change=item.quantity,
                resulting_stock_level=product.quantity_in_stock,
                reference=f'SaleCancel-{sale.pk}',
            )
            log_activity(
                action=AuditLog.ACTION_STOCK_ADJUSTMENT,
                instance=product,
                description=(
                    f'Restored {item.quantity} units of {product.name} '
                    f'due to Sale #{sale.pk} cancellation.'
                ),
                changes={
                    'quantity_in_stock': {
                        'old': old_stock,
                        'new': product.quantity_in_stock,
                    },
                    'source': f'SaleCancel-{sale.pk}',
                },
                severity=AuditLog.SEVERITY_WARNING,
            )

        old_status = sale.status
        sale.status = Sale.STATUS_CANCELLED
        sale.save(update_fields=['status'])
        log_activity(
            action=AuditLog.ACTION_STATUS_CHANGE,
            instance=sale,
            description=(
                f'Sale #{sale.pk} was cancelled — status changed '
                f'from "{old_status}" to "{Sale.STATUS_CANCELLED}".'
            ),
            changes={'status': {'old': old_status, 'new': Sale.STATUS_CANCELLED}},
            severity=AuditLog.SEVERITY_WARNING,
        )

        messages.success(request, f'Sale #{sale.pk} has been cancelled and stock restored.')
        return redirect('product:product-list')


def receipt_view(request, pk):
    sale = get_object_or_404(Sale, pk=pk)
    return render(request, 'product/receipt.html', {'sale': sale})


def receipt_print_view(request, pk):
    sale = get_object_or_404(Sale, pk=pk)
    return render(request, 'product/receipt_print.html', {'sale': sale})
