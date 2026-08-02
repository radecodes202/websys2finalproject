from decimal import Decimal
from django.db.models import Sum, Q, F
from django.views import View
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.db import transaction
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404
from accounts.mixins import RoleRequiredMixin
from audit.models import AuditLog
from audit.services import log_activity
from .models import Supplier, SupplierPayment


class SupplierListView(RoleRequiredMixin, ListView):
    model = Supplier
    template_name = 'supplier/supplier_list.html'
    context_object_name = 'suppliers'
    paginate_by = 10
    allowed_roles = ['admin', 'manager', 'inventory_staff']

    def get_queryset(self):
        queryset = super().get_queryset()
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(name__icontains=search_query)
        return queryset


class SupplierCreateView(RoleRequiredMixin, CreateView):
    model = Supplier
    template_name = 'supplier/supplier_form.html'
    fields = ['name', 'contact_person', 'email', 'phone', 'address', 'city', 'postal_code', 'country', 'is_active']
    success_url = reverse_lazy('supplier:supplier-list')
    allowed_roles = ['admin', 'manager', 'inventory_staff']


class SupplierUpdateView(RoleRequiredMixin, UpdateView):
    model = Supplier
    template_name = 'supplier/supplier_form.html'
    fields = ['name', 'contact_person', 'email', 'phone', 'address', 'city', 'postal_code', 'country', 'is_active']
    success_url = reverse_lazy('supplier:supplier-list')
    allowed_roles = ['admin', 'manager', 'inventory_staff']


class SupplierDeleteView(RoleRequiredMixin, View):
    model = Supplier
    success_url = reverse_lazy('supplier:supplier-list')
    allowed_roles = ['admin', 'manager', 'inventory_staff']

    def post(self, request, pk):
        supplier = get_object_or_404(Supplier, pk=pk)
        supplier.delete()
        messages.success(request, f'Supplier "{supplier.name}" deleted successfully.')
        return redirect(self.success_url)


class SupplierPaymentListView(RoleRequiredMixin, ListView):
    model = SupplierPayment
    template_name = 'supplier/supplierpayment_list.html'
    context_object_name = 'payments'
    paginate_by = 10
    allowed_roles = ['admin', 'manager', 'inventory_staff']

    def get_queryset(self):
        queryset = SupplierPayment.objects.select_related('supplier').all()
        supplier_id = self.request.GET.get('supplier')
        if supplier_id:
            queryset = queryset.filter(supplier_id=supplier_id)
        return queryset.order_by('-date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['suppliers'] = Supplier.objects.all()
        context['selected_supplier'] = self.request.GET.get('supplier', '')
        return context


class SupplierPaymentCreateView(RoleRequiredMixin, CreateView):
    model = SupplierPayment
    template_name = 'supplier/supplierpayment_form.html'
    fields = ['supplier', 'purchase_order', 'amount', 'method', 'status']
    success_url = reverse_lazy('supplier:supplierpayment-list')
    allowed_roles = ['admin', 'manager', 'inventory_staff']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['view_type'] = 'Create'
        return context

    @transaction.atomic
    def form_valid(self, form):
        payment = form.save()
        supplier = payment.supplier
        supplier.outstanding_balance = (
            Supplier.objects.filter(pk=supplier.pk)
            .aggregate(
                total=Sum(
                    'payments__amount',
                    filter=Q(payments__status=SupplierPayment.STATUS_PAID),
                )
            )['total']
            or Decimal('0.00')
        )
        old_balance = supplier.outstanding_balance
        supplier.save(update_fields=['outstanding_balance'])
        log_activity(
            user=self.request.user,
            action=AuditLog.ACTION_UPDATE,
            instance=supplier,
            description=f'Recorded payment of {payment.amount} for supplier {supplier.name}.',
            changes={'outstanding_balance': {'old': old_balance, 'new': supplier.outstanding_balance}},
            severity=AuditLog.SEVERITY_INFO,
        )
        messages.success(self.request, 'Supplier payment recorded successfully.')
        return redirect(self.get_success_url())


class SupplierPaymentUpdateView(RoleRequiredMixin, UpdateView):
    model = SupplierPayment
    template_name = 'supplier/supplierpayment_form.html'
    fields = ['supplier', 'purchase_order', 'amount', 'method', 'status']
    success_url = reverse_lazy('supplier:supplierpayment-list')
    allowed_roles = ['admin', 'manager', 'inventory_staff']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['view_type'] = 'Update'
        return context

    @transaction.atomic
    def form_valid(self, form):
        payment = form.save()
        supplier = payment.supplier
        supplier.outstanding_balance = (
            Supplier.objects.filter(pk=supplier.pk)
            .aggregate(
                total=Sum(
                    'payments__amount',
                    filter=Q(payments__status=SupplierPayment.STATUS_PAID),
                )
            )['total']
            or Decimal('0.00')
        )
        old_balance = supplier.outstanding_balance
        supplier.save(update_fields=['outstanding_balance'])
        log_activity(
            user=self.request.user,
            action=AuditLog.ACTION_UPDATE,
            instance=supplier,
            description=f'Updated payment of {payment.amount} for supplier {supplier.name}.',
            changes={'outstanding_balance': {'old': old_balance, 'new': supplier.outstanding_balance}},
            severity=AuditLog.SEVERITY_INFO,
        )
        messages.success(self.request, 'Supplier payment updated successfully.')
        return redirect(self.get_success_url())


class SupplierPaymentDeleteView(RoleRequiredMixin, DeleteView):
    model = SupplierPayment
    template_name = 'supplier/supplierpayment_confirm_delete.html'
    success_url = reverse_lazy('supplier:supplierpayment-list')
    allowed_roles = ['admin', 'manager', 'inventory_staff']
