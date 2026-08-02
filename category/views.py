from django.views import View
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404
from accounts.mixins import RoleRequiredMixin
from .models import Category


class CategoryListView(RoleRequiredMixin, ListView):
    model = Category
    template_name = 'category/category_list.html'
    context_object_name = 'categories'
    paginate_by = 10
    allowed_roles = ['admin', 'manager', 'inventory_staff']

    def get_queryset(self):
        queryset = super().get_queryset()
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(name__icontains=search_query)
        return queryset


class CategoryCreateView(RoleRequiredMixin, CreateView):
    model = Category
    template_name = 'category/category_form.html'
    fields = ['name', 'description']
    success_url = reverse_lazy('category:category-list')
    allowed_roles = ['admin', 'manager', 'inventory_staff']


class CategoryUpdateView(RoleRequiredMixin, UpdateView):
    model = Category
    template_name = 'category/category_form.html'
    fields = ['name', 'description']
    success_url = reverse_lazy('category:category-list')
    allowed_roles = ['admin', 'manager', 'inventory_staff']


class CategoryDeleteView(RoleRequiredMixin, View):
    model = Category
    success_url = reverse_lazy('category:category-list')
    allowed_roles = ['admin', 'manager', 'inventory_staff']

    def post(self, request, pk):
        category = get_object_or_404(Category, pk=pk)
        category.delete()
        messages.success(request, f'Category "{category.name}" deleted successfully.')
        return redirect(self.success_url)
