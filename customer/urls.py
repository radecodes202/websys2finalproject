from django.urls import path
from . import views

app_name = 'customer'

urlpatterns = [
    path('', views.CustomerListView.as_view(), name='customer-list'),
    path('create/', views.CustomerCreateView.as_view(), name='customer-create'),
    path('<int:pk>/update/', views.CustomerUpdateView.as_view(), name='customer-update'),
    path('<int:pk>/delete/', views.CustomerDeleteView.as_view(), name='customer-delete'),
]