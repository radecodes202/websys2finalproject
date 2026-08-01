from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from accounts.mixins import RoleRequiredMixin
from .models import Customer


class CustomerListView(RoleRequiredMixin, ListView):
    model = Customer
    template_name = 'customer/customer_list.html'
    context_object_name = 'customers'
    paginate_by = 10
    allowed_roles = ['admin', 'manager', 'cashier']

    def get_queryset(self):
        queryset = super().get_queryset()
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(name__icontains=search_query)
        return queryset


class CustomerCreateView(RoleRequiredMixin, CreateView):
    model = Customer
    template_name = 'customer/customer_form.html'
    fields = ['name', 'contact_person', 'email', 'phone', 'address', 'city', 'postal_code', 'country', 'is_active']
    success_url = reverse_lazy('customer:customer-list')
    allowed_roles = ['admin', 'manager', 'cashier']


class CustomerUpdateView(RoleRequiredMixin, UpdateView):
    model = Customer
    template_name = 'customer/customer_form.html'
    fields = ['name', 'contact_person', 'email', 'phone', 'address', 'city', 'postal_code', 'country', 'is_active']
    success_url = reverse_lazy('customer:customer-list')
    allowed_roles = ['admin', 'manager', 'cashier']


class CustomerDeleteView(RoleRequiredMixin, DeleteView):
    model = Customer
    template_name = 'customer/customer_confirm_delete.html'
    success_url = reverse_lazy('customer:customer-list')
    allowed_roles = ['admin', 'manager', 'cashier']
