from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from accounts.mixins import RoleRequiredMixin
from .models import Supplier


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


class SupplierDeleteView(RoleRequiredMixin, DeleteView):
    model = Supplier
    template_name = 'supplier/supplier_confirm_delete.html'
    success_url = reverse_lazy('supplier:supplier-list')
    allowed_roles = ['admin', 'manager', 'inventory_staff']
