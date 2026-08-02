from django.urls import path
from . import views

app_name = 'product'

urlpatterns = [
    path('', views.ProductListView.as_view(), name='product-list'),
    path('<int:pk>/', views.ProductDetailView.as_view(), name='product-detail'),
    path('add/', views.ProductCreateView.as_view(), name='product-create'),
    path('<int:pk>/edit/', views.ProductUpdateView.as_view(), name='product-update'),
    path('<int:pk>/delete/', views.ProductDeleteView.as_view(), name='product-delete'),
    path('pos/', views.POSView.as_view(), name='pos'),
    path('receipt/<int:pk>/', views.receipt_view, name='receipt'),
    path('receipt/<int:pk>/print/', views.receipt_print_view, name='receipt_print'),
    path('alerts/', views.AlertListView.as_view(), name='alert-list'),
    path('alerts/<int:pk>/resolve/', views.AlertResolveView.as_view(), name='alert-resolve'),
    path('sales/<int:pk>/cancel/', views.SaleCancelView.as_view(), name='sale-cancel'),
    path('stock-adjustment/', views.StockAdjustmentView.as_view(), name='stock-adjustment'),
]
