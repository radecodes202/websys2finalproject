from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
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


class CategoryDeleteView(RoleRequiredMixin, DeleteView):
    model = Category
    template_name = 'category/category_confirm_delete.html'
    success_url = reverse_lazy('category:category-list')
    allowed_roles = ['admin', 'manager', 'inventory_staff']
