"""
Read-only Django Admin registration for AuditLog.

Even superusers cannot add, change, or delete audit-log entries through the
admin UI — ``has_add_permission``, ``has_change_permission``, and
``has_delete_permission`` all return ``False``.
"""
from django.contrib import admin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """Read-only admin view for audit-log entries."""

    list_display = (
        'timestamp', 'username_snapshot', 'action', 'severity',
        'content_type', 'object_id', 'object_repr', 'ip_address',
    )
    list_filter = (
        'action', 'severity', 'content_type', 'timestamp',
    )
    search_fields = (
        'username_snapshot', 'object_repr', 'description', 'ip_address',
    )
    date_hierarchy = 'timestamp'
    ordering = ('-timestamp',)
    readonly_fields = (
        'user', 'username_snapshot', 'action', 'content_type', 'object_id',
        'object_repr', 'changes', 'description', 'ip_address', 'user_agent',
        'timestamp', 'severity',
    )
    # No raw_id_fields / autocomplete — everything is read-only.

    # ------------------------------------------------------------------ #
    # Read-only enforcement — no add / change / delete via admin
    # ------------------------------------------------------------------ #
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    # ------------------------------------------------------------------ #
    # Remove the "Save" / "Delete" buttons from the change page
    # ------------------------------------------------------------------ #
    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = extra_context or {}
        extra_context['show_save'] = False
        extra_context['show_save_and_continue'] = False
        extra_context['show_delete'] = False
        return super().change_view(request, object_id, form_url, extra_context)