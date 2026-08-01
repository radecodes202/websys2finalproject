from django.views.generic import TemplateView
from accounts.mixins import RoleRequiredMixin
from product.models import Sale


class SalesReportView(RoleRequiredMixin, TemplateView):
    template_name = 'reports/sales_report.html'
    allowed_roles = ['admin', 'manager']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['sales'] = Sale.objects.select_related('cashier').prefetch_related('items').all()
        return context
