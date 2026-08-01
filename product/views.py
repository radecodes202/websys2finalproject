from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from accounts.mixins import RoleRequiredMixin
from .models import Product


class ProductListView(RoleRequiredMixin, ListView):
    model = Product
    template_name = 'product/product_list.html'
    context_object_name = 'products'
    paginate_by = 10
    allowed_roles = ['admin', 'manager', 'inventory_staff']

    def get_queryset(self):
        queryset = super().get_queryset()
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(name__icontains=search_query)
        return queryset


class ProductCreateView(RoleRequiredMixin, CreateView):
    model = Product
    template_name = 'product/product_form.html'
    fields = ['name', 'description', 'category', 'sku', 'unit_price', 'quantity_in_stock', 'reorder_level', 'is_active']
    success_url = reverse_lazy('product:product-list')
    allowed_roles = ['admin', 'manager', 'inventory_staff']


class ProductUpdateView(RoleRequiredMixin, UpdateView):
    model = Product
    template_name = 'product/product_form.html'
    fields = ['name', 'description', 'category', 'sku', 'unit_price', 'quantity_in_stock', 'reorder_level', 'is_active']
    success_url = reverse_lazy('product:product-list')
    allowed_roles = ['admin', 'manager', 'inventory_staff']


class ProductDeleteView(RoleRequiredMixin, DeleteView):
    model = Product
    template_name = 'product/product_confirm_delete.html'
    success_url = reverse_lazy('product:product-list')
    allowed_roles = ['admin', 'manager', 'inventory_staff']
