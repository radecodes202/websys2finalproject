"""URL configuration for the purchasing app."""
from django.urls import path

from . import views

app_name = 'purchase'

urlpatterns = [
    path('', views.PurchaseOrderListView.as_view(), name='purchase-order-list'),
    path('create/', views.PurchaseOrderCreateView.as_view(), name='purchase-order-create'),
    path('<int:pk>/', views.PurchaseOrderDetailView.as_view(), name='purchase-order-detail'),
    path('<int:pk>/update/', views.PurchaseOrderUpdateView.as_view(), name='purchase-order-update'),
    path('<int:pk>/cancel/', views.PurchaseOrderCancelView.as_view(), name='purchase-order-cancel'),
    path('<int:pk>/receive/', views.StockReceiptView.as_view(), name='purchase-order-receive'),
]
