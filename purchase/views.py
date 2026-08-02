"""Views for the purchase-order management workflow.

Covers the full lifecycle of a purchase order:
  * list  — browse / filter / search purchase orders
  * create — PO header + inline line items
  * update — edit a pending PO (header + lines)
  * detail  — inspect a PO, its receipts and remaining quantities
  * cancel  — move a pending PO to "cancelled"
  * receive — the goods-receiving screen (matches received qty to ordered qty)

All views require one of the purchasing roles
(``admin``, ``manager``, ``inventory_staff``).
"""
from decimal import Decimal

from django.contrib import messages
from django.db import transaction
from django.db.models import DecimalField, F, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from accounts.mixins import RoleRequiredMixin
from audit.models import AuditLog
from product.models import PurchaseOrder
from supplier.models import Supplier

from .forms import PurchaseOrderForm, PurchaseOrderItemFormSet, StockReceiptForm

# Roles permitted to manage purchase orders.
PURCHASING_ROLES = ['admin', 'manager', 'inventory_staff']

# Roles that can approve or reject purchase orders.
PO_APPROVER_ROLES = ['admin', 'manager']


class PurchaseOrderListView(RoleRequiredMixin, ListView):
    model = PurchaseOrder
    template_name = 'purchase/purchase_order_list.html'
    context_object_name = 'purchase_orders'
    paginate_by = 10
    allowed_roles = PURCHASING_ROLES

    def get_queryset(self):
        queryset = PurchaseOrder.objects.select_related('supplier').all()

        # Annotate the line-total so the list can show cost without an N+1.
        queryset = queryset.annotate(
            po_total=Sum(
                F('items__quantity_ordered') * F('items__unit_cost'),
                output_field=DecimalField(max_digits=12, decimal_places=2),
            )
        )

        search = self.request.GET.get('search', '').strip()
        status = self.request.GET.get('status')
        supplier = self.request.GET.get('supplier')

        if search:
            queryset = queryset.filter(supplier__name__icontains=search)
        if status and status in dict(PurchaseOrder.STATUS_CHOICES):
            queryset = queryset.filter(status=status)
        if supplier:
            queryset = queryset.filter(supplier_id=supplier)

        return queryset.order_by('-order_date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['suppliers'] = Supplier.objects.all()
        context['statuses'] = PurchaseOrder.STATUS_CHOICES
        context['search'] = self.request.GET.get('search', '')
        context['selected_status'] = self.request.GET.get('status', '')
        context['selected_supplier'] = self.request.GET.get('supplier', '')
        return context


class PurchaseOrderCreateView(RoleRequiredMixin, CreateView):
    model = PurchaseOrder
    template_name = 'purchase/purchase_order_form.html'
    form_class = PurchaseOrderForm
    success_url = reverse_lazy('purchase:purchase-order-list')
    allowed_roles = PURCHASING_ROLES

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['view_type'] = 'Create'
        context.setdefault(
            'item_formset',
            PurchaseOrderItemFormSet(self.request.POST or None, prefix='items'),
        )
        po = getattr(self, 'object', None)
        context['total_cost'] = po.total_cost if po else Decimal('0.00')
        return context

    def post(self, request, *args, **kwargs):
        self.object = None
        form = self.get_form()
        item_formset = PurchaseOrderItemFormSet(request.POST, prefix='items')
        if form.is_valid() and item_formset.is_valid():
            return self.form_valid(form, item_formset)
        return self.form_invalid(form, item_formset)

    @transaction.atomic
    def form_valid(self, form, item_formset):
        form.instance.created_by = self.request.user
        self.object = form.save()
        item_formset.instance = self.object
        item_formset.save()
        messages.success(self.request, f'Purchase order PO-{self.object.pk} created.')
        return redirect(self.get_success_url())

    def form_invalid(self, form, item_formset):
        return self.render_to_response(
            self.get_context_data(form=form, item_formset=item_formset)
        )


class PurchaseOrderUpdateView(RoleRequiredMixin, UpdateView):
    model = PurchaseOrder
    template_name = 'purchase/purchase_order_form.html'
    form_class = PurchaseOrderForm
    success_url = reverse_lazy('purchase:purchase-order-list')
    allowed_roles = PURCHASING_ROLES
    pk_url_kwarg = 'pk'

    def get_queryset(self):
        return PurchaseOrder.objects.select_related('supplier')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['view_type'] = 'Update'
        context.setdefault(
            'item_formset',
            PurchaseOrderItemFormSet(
                self.request.POST or None,
                instance=self.object,
                prefix='items',
            ),
        )
        context['total_cost'] = self.object.total_cost
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        # Only pending POs are editable — once goods move the lines are locked.
        if self.object.status != PurchaseOrder.STATUS_PENDING:
            messages.error(
                request,
                f'PO-{self.object.pk} can only be edited while pending '
                f'(current status: {self.object.get_status_display()}).',
            )
            return redirect('purchase:purchase-order-detail', self.object.pk)

        form = self.get_form()
        item_formset = PurchaseOrderItemFormSet(
            request.POST, instance=self.object, prefix='items'
        )
        if form.is_valid() and item_formset.is_valid():
            return self.form_valid(form, item_formset)
        return self.form_invalid(form, item_formset)

    @transaction.atomic
    def form_valid(self, form, item_formset):
        self.object = form.save()
        item_formset.save()
        messages.success(self.request, f'Purchase order PO-{self.object.pk} updated.')
        return redirect('purchase:purchase-order-detail', self.object.pk)

    def form_invalid(self, form, item_formset):
        return self.render_to_response(
            self.get_context_data(form=form, item_formset=item_formset)
        )


class PurchaseOrderDetailView(RoleRequiredMixin, DetailView):
    model = PurchaseOrder
    template_name = 'purchase/purchase_order_detail.html'
    context_object_name = 'po'
    allowed_roles = PURCHASING_ROLES

    def get_queryset(self):
        return PurchaseOrder.objects.select_related('supplier').prefetch_related(
            'items', 'stock_receipts'
        )


class PurchaseOrderApproveView(RoleRequiredMixin, View):
    """Manager or Admin approves a pending purchase order."""
    template_name = 'purchase/purchase_order_confirm_approve.html'
    allowed_roles = PO_APPROVER_ROLES

    def get(self, request, pk):
        po = get_object_or_404(PurchaseOrder, pk=pk)
        if po.status != PurchaseOrder.STATUS_PENDING:
            messages.error(
                request,
                f'PO-{po.pk} is not pending approval (status: {po.get_status_display()}).',
            )
            return redirect('purchase:purchase-order-detail', po.pk)
        return render(request, self.template_name, {'po': po})

    def post(self, request, pk):
        po = get_object_or_404(PurchaseOrder, pk=pk)
        if po.status != PurchaseOrder.STATUS_PENDING:
            messages.error(
                request,
                f'PO-{po.pk} is not pending approval (status: {po.get_status_display()}).',
            )
            return redirect('purchase:purchase-order-detail', po.pk)
        log_activity(
            user=request.user,
            action=AuditLog.ACTION_UPDATE,
            instance=po,
            description=f'Purchase Order PO-{po.pk} was approved by {request.user.username}.',
            changes={'status': {'old': po.status, 'new': po.status}},
            severity=AuditLog.SEVERITY_INFO,
        )
        messages.success(request, f'PO-{po.pk} has been approved.')
        return redirect('purchase:purchase-order-detail', po.pk)


class PurchaseOrderRejectView(RoleRequiredMixin, View):
    """Manager or Admin rejects a pending purchase order."""
    template_name = 'purchase/purchase_order_confirm_reject.html'
    allowed_roles = PO_APPROVER_ROLES

    def get(self, request, pk):
        po = get_object_or_404(PurchaseOrder, pk=pk)
        if po.status != PurchaseOrder.STATUS_PENDING:
            messages.error(
                request,
                f'PO-{po.pk} is not pending approval (status: {po.get_status_display()}).',
            )
            return redirect('purchase:purchase-order-detail', po.pk)
        return render(request, self.template_name, {'po': po})

    def post(self, request, pk):
        po = get_object_or_404(PurchaseOrder, pk=pk)
        if po.status != PurchaseOrder.STATUS_PENDING:
            messages.error(
                request,
                f'PO-{po.pk} is not pending approval (status: {po.get_status_display()}).',
            )
            return redirect('purchase:purchase-order-detail', po.pk)
        po.cancel(cancelled_by=request.user)
        messages.success(request, f'PO-{po.pk} has been rejected and cancelled.')
        return redirect('purchase:purchase-order-list')


class PurchaseOrderCancelView(RoleRequiredMixin, View):
    """Confirm + perform cancellation of a pending purchase order."""
    template_name = 'purchase/purchase_order_confirm_cancel.html'
    allowed_roles = PURCHASING_ROLES

    def get(self, request, pk):
        po = get_object_or_404(PurchaseOrder, pk=pk)
        if not po.can_cancel():
            messages.error(
                request,
                f'PO-{po.pk} cannot be cancelled (current status: '
                f'{po.get_status_display()}).',
            )
            return redirect('purchase:purchase-order-detail', po.pk)
        return render(request, self.template_name, {'po': po})

    def post(self, request, pk):
        po = get_object_or_404(PurchaseOrder, pk=pk)
        if not po.can_cancel():
            messages.error(
                request,
                f'PO-{po.pk} cannot be cancelled (current status: '
                f'{po.get_status_display()}).',
            )
            return redirect('purchase:purchase-order-detail', po.pk)
        po.cancel(cancelled_by=request.user)
        messages.success(request, f'PO-{po.pk} has been cancelled.')
        return redirect('purchase:purchase-order-list')


class StockReceiptView(RoleRequiredMixin, View):
    """The goods-receiving screen.

    GET  renders a form with one input per ordered line (capped at the
         remaining quantity for that line).
    POST validates, persists a ``StockReceipt`` + ``StockReceiptItem`` rows
         and applies them (stock up, movements recorded, PO status updated).
    """
    template_name = 'purchase/stock_receipt_form.html'
    allowed_roles = PURCHASING_ROLES

    def get_queryset(self):
        return PurchaseOrder.objects.select_related('supplier').prefetch_related(
            'items', 'stock_receipts'
        )

    def get(self, request, pk):
        po = get_object_or_404(self.get_queryset(), pk=pk)
        if not po.can_be_received():
            messages.error(
                request,
                f'PO-{po.pk} cannot be received (current status: '
                f'{po.get_status_display()}).',
            )
            return redirect('purchase:purchase-order-detail', po.pk)
        form = StockReceiptForm(po=po)
        return render(request, self.template_name, {'po': po, 'form': form})

    def post(self, request, pk):
        po = get_object_or_404(self.get_queryset(), pk=pk)
        if not po.can_be_received():
            messages.error(
                request,
                f'PO-{po.pk} cannot be received (current status: '
                f'{po.get_status_display()}).',
            )
            return redirect('purchase:purchase-order-detail', po.pk)
        form = StockReceiptForm(request.POST, po=po)
        if form.is_valid():
            stock_receipt = form.save(received_by=request.user)
            for item in stock_receipt.items.all():
                item.purchase_order_item.product.create_alerts()
            messages.success(request, f'Stock receipt recorded for PO-{po.pk}.')
            return redirect('purchase:purchase-order-detail', po.pk)
        return render(request, self.template_name, {'po': po, 'form': form})
