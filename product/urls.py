from django.urls import path
from . import views

app_name = 'product'

urlpatterns = [
    path('', views.ProductListView.as_view(), name='product-list'),
    path('create/', views.ProductCreateView.as_view(), name='product-create'),
    path('pos/', views.POSView.as_view(), name='pos'),
    path('receipt/<int:pk>/', views.receipt_view, name='receipt'),
    path('sale/<int:pk>/receipt/', views.receipt_print_view, name='receipt_print'),
    path('<int:pk>/', views.ProductDetailView.as_view(), name='product-detail'),
    path('<int:pk>/update/', views.ProductUpdateView.as_view(), name='product-update'),
    path('<int:pk>/delete/', views.ProductDeleteView.as_view(), name='product-delete'),
    path('sale/<int:pk>/cancel/', views.SaleCancelView.as_view(), name='sale-cancel'),
    path('alerts/', views.AlertListView.as_view(), name='alert-list'),
    path('alerts/<int:pk>/resolve/', views.AlertResolveView.as_view(), name='alert-resolve'),
]
