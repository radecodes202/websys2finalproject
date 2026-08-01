from django.shortcuts import render
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from .models import Product

class ProductListView(ListView):
    model = Product
    template_name = 'product/product_list.html'
    context_object_name = 'products'
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset()
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(name__icontains=search_query)
        return queryset

class ProductCreateView(CreateView):
    model = Product
    template_name = 'product/product_form.html'
    fields = ['name', 'description', 'category', 'sku', 'unit_price', 'quantity_in_stock', 'reorder_level', 'is_active']
    success_url = reverse_lazy('product:product-list')

class ProductUpdateView(UpdateView):
    model = Product
    template_name = 'product/product_form.html'
    fields = ['name', 'description', 'category', 'sku', 'unit_price', 'quantity_in_stock', 'reorder_level', 'is_active']
    success_url = reverse_lazy('product:product-list')

class ProductDeleteView(DeleteView):
    model = Product
    template_name = 'product/product_confirm_delete.html'
    success_url = reverse_lazy('product:product-list')