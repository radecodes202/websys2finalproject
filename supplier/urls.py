from django.urls import path
from . import views

app_name = 'supplier'

urlpatterns = [
    path('', views.SupplierListView.as_view(), name='supplier-list'),
    path('create/', views.SupplierCreateView.as_view(), name='supplier-create'),
    path('<int:pk>/update/', views.SupplierUpdateView.as_view(), name='supplier-update'),
    path('<int:pk>/delete/', views.SupplierDeleteView.as_view(), name='supplier-delete'),
]