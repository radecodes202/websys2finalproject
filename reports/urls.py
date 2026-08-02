from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    path('sales/', views.SalesReportView.as_view(), name='sales-report'),
    path('sales-history/', views.SalesHistoryView.as_view(), name='sales-history'),
    path('sales/<int:pk>/', views.SaleDetailView.as_view(), name='sale-detail'),
    path('sales/<int:pk>/pdf/', views.SalePDFView.as_view(), name='sale-pdf'),
    path('sales/<int:pk>/excel/', views.SaleExcelView.as_view(), name='sale-excel'),
    path('inventory-valuation/', views.InventoryValuationView.as_view(), name='inventory-valuation'),
    path('inventory-valuation/pdf/', views.InventoryPDFView.as_view(), name='inventory-pdf'),
    path('inventory-valuation/excel/', views.InventoryExcelView.as_view(), name='inventory-excel'),
    path('stock-movement/', views.StockMovementView.as_view(), name='stock-movement'),
    path('supplier-payments/', views.SupplierPaymentOutstandingView.as_view(), name='supplier-payments'),
    path('profit-loss/', views.ProfitLossSummaryView.as_view(), name='profit-loss'),
]
