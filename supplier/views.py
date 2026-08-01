from django.shortcuts import render
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from .models import Supplier

class SupplierListView(ListView):
    model = Supplier
    template_name = 'supplier/supplier_list.html'
    context_object_name = 'suppliers'
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset()
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(name__icontains=search_query)
        return queryset

class SupplierCreateView(CreateView):
    model = Supplier
    template_name = 'supplier/supplier_form.html'
    fields = ['name', 'contact_person', 'email', 'phone', 'address', 'city', 'postal_code', 'country', 'is_active']
    success_url = reverse_lazy('supplier:supplier-list')

class SupplierUpdateView(UpdateView):
    model = Supplier
    template_name = 'supplier/supplier_form.html'
    fields = ['name', 'contact_person', 'email', 'phone', 'address', 'city', 'postal_code', 'country', 'is_active']
    success_url = reverse_lazy('supplier:supplier-list')

class SupplierDeleteView(DeleteView):
    model = Supplier
    template_name = 'supplier/supplier_confirm_delete.html'
    success_url = reverse_lazy('supplier:supplier-list')