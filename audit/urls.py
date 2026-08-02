"""
URL configuration for the audit app.
"""
from django.urls import path
from . import views

app_name = 'audit'

urlpatterns = [
    path('', views.AuditLogListView.as_view(), name='audit-log-list'),
    path('<int:pk>/', views.AuditLogDetailView.as_view(), name='audit-log-detail'),
    path('export/', views.AuditLogExportView.as_view(), name='audit-log-export'),
]