from django.contrib import admin
from .models import Customer


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('name', 'contact_person', 'email', 'phone', 'city', 'is_active')
    list_filter = ('is_active', 'country', 'created_at')
    search_fields = ('name', 'contact_person', 'email', 'phone', 'city')
    readonly_fields = ('created_at', 'updated_at')
    list_editable = ('is_active',)