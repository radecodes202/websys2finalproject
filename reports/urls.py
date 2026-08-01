from django.urls import path
from .views import SalesReportView

app_name = 'reports'

urlpatterns = [
    path('sales/', SalesReportView.as_view(), name='sales-report'),
]
