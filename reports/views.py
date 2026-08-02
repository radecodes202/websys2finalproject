from django.core.paginator import Paginator
from django.db.models import Q, Sum, Count, F
from django.views.generic import TemplateView, DetailView
from django.urls import reverse_lazy
from accounts.mixins import RoleRequiredMixin
from accounts.models import User
from product.models import Sale, SaleItem


class SalesReportView(RoleRequiredMixin, TemplateView):
    template_name = 'reports/sales_report.html'
    allowed_roles = ['admin', 'manager']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['sales'] = Sale.objects.select_related('cashier').prefetch_related('items').all()
        return context


class SalesHistoryView(RoleRequiredMixin, TemplateView):
    template_name = 'reports/sales_history.html'
    allowed_roles = ['admin', 'manager', 'cashier']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        request = self.request
        base_qs = Sale.objects.select_related('cashier').prefetch_related('items', 'payments')
        if request.user.role == 'cashier':
            base_qs = base_qs.filter(cashier=request.user)

        search = request.GET.get('search', '').strip()
        date_from = request.GET.get('date_from', '').strip()
        date_to = request.GET.get('date_to', '').strip()
        cashier_id = request.GET.get('cashier', '').strip()
        payment_method = request.GET.get('payment_method', '').strip()
        status = request.GET.get('status', '').strip()

        if search:
            base_qs = base_qs.filter(
                Q(pk__icontains=search) |
                Q(customer__name__icontains=search)
            )
        if date_from:
            base_qs = base_qs.filter(date__date__gte=date_from)
        if date_to:
            base_qs = base_qs.filter(date__date__lte=date_to)
        if cashier_id and request.user.role in ('admin', 'manager'):
            base_qs = base_qs.filter(cashier_id=cashier_id)
        if payment_method:
            base_qs = base_qs.filter(payment_method=payment_method)
        if status:
            base_qs = base_qs.filter(status=status)

        page_size = request.GET.get('page_size', 20)
        paginator = Paginator(base_qs.order_by('-date'), page_size)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        payment_methods = Sale.objects.values_list('payment_method', flat=True).distinct().order_by('payment_method')
        statuses = [choice[0] for choice in Sale.STATUS_CHOICES]
        users = User.objects.filter(is_active=True).order_by('username')

        context.update({
            'page_obj': page_obj,
            'payment_methods': payment_methods,
            'statuses': statuses,
            'users': users,
            'request_get': request.GET,
        })
        return context


class SaleDetailView(RoleRequiredMixin, DetailView):
    model = Sale
    template_name = 'reports/sale_detail.html'
    context_object_name = 'sale'
    allowed_roles = ['admin', 'manager', 'cashier']

    def get_queryset(self):
        qs = Sale.objects.select_related('cashier').prefetch_related('items', 'payments')
        if self.request.user.role == 'cashier':
            return qs.filter(cashier=self.request.user)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['print_url'] = reverse_lazy('product:receipt_print', kwargs={'pk': self.object.pk})
        return context
