from django.urls import path
from .views import SalesReportView, SalesHistoryView, SaleDetailView

app_name = 'reports'

urlpatterns = [
    path('sales/', SalesReportView.as_view(), name='sales-report'),
    path('sales/history/', SalesHistoryView.as_view(), name='sales-history'),
    path('sale/<int:pk>/', SaleDetailView.as_view(), name='sale-detail'),
]
