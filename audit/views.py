"""
Audit Log viewer views.

Provides an Admin/Manager-only paginated audit-log viewer with filters
(user, action, date range, content type/module, severity), search, a detail
view, and CSV export of filtered results.
"""
import csv

from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponse
from django.views.generic import DetailView, ListView, View

from accounts.mixins import RoleRequiredMixin

from .models import AuditLog


class AuditLogListView(RoleRequiredMixin, ListView):
    """Paginated audit-log list with filters and search."""

    model = AuditLog
    template_name = 'audit/auditlog_list.html'
    context_object_name = 'audit_logs'
    paginate_by = 25
    allowed_roles = ['admin', 'manager']

    def get_queryset(self):
        qs = AuditLog.objects.select_related('user', 'content_type').all()

        # ---- Filters from query params -------------------------------- #
        user_id = self.request.GET.get('user')
        if user_id:
            qs = qs.filter(user_id=user_id)

        action = self.request.GET.get('action')
        if action:
            qs = qs.filter(action=action)

        severity = self.request.GET.get('severity')
        if severity:
            qs = qs.filter(severity=severity)

        content_type_id = self.request.GET.get('content_type')
        if content_type_id:
            qs = qs.filter(content_type_id=content_type_id)

        date_from = self.request.GET.get('date_from')
        if date_from:
            qs = qs.filter(timestamp__date__gte=date_from)

        date_to = self.request.GET.get('date_to')
        if date_to:
            qs = qs.filter(timestamp__date__lte=date_to)

        search = self.request.GET.get('search')
        if search:
            qs = qs.filter(
                models_Q_object(search)
            )

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Pass filter choices to the template for the filter sidebar.
        context['action_choices'] = AuditLog.ACTION_CHOICES
        context['severity_choices'] = AuditLog.SEVERITY_CHOICES
        context['user_choices'] = (
            AuditLog.objects.exclude(user=None)
            .select_related('user')
            .values_list('user_id', 'user__username')
            .distinct()
            .order_by('user__username')
        )
        # Content types that appear in the audit log (query distinct IDs
        # from AuditLog directly since the FK uses related_name='+').
        ct_ids = AuditLog.objects.exclude(content_type=None).values_list('content_type_id', flat=True).distinct()
        context['content_type_choices'] = (
            ContentType.objects.filter(id__in=ct_ids).values_list('id', 'app_label', 'model')
        )
        # Preserve current query params for pagination links.
        context['query_params'] = self.request.GET.urlencode()
        return context


def models_Q_object(search):
    """Build a Q object for searching object_repr and description."""
    from django.db.models import Q
    return Q(object_repr__icontains=search) | Q(description__icontains=search)


class AuditLogDetailView(RoleRequiredMixin, DetailView):
    """Detail view for a single audit-log entry (shows formatted diff)."""

    model = AuditLog
    template_name = 'audit/auditlog_detail.html'
    context_object_name = 'audit_log'
    allowed_roles = ['admin', 'manager']


class AuditLogExportView(RoleRequiredMixin, View):
    """Export filtered audit-log entries to CSV."""

    allowed_roles = ['admin', 'manager']

    def get(self, request, *args, **kwargs):
        # Reuse the same filtering logic as the list view.
        list_view = AuditLogListView()
        list_view.request = request
        list_view.kwargs = {}
        list_view.args = ()
        queryset = list_view.get_queryset()

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="audit_log_export.csv"'

        writer = csv.writer(response)
        writer.writerow([
            'Timestamp', 'User', 'Action', 'Severity',
            'Module', 'Model', 'Object ID', 'Object Repr',
            'Description', 'IP Address', 'User Agent', 'Changes',
        ])

        for entry in queryset:
            writer.writerow([
                entry.timestamp.isoformat(),
                entry.username_snapshot or '',
                entry.get_action_display(),
                entry.get_severity_display(),
                entry.module_name,
                entry.model_name,
                entry.object_id or '',
                entry.object_repr,
                entry.description,
                entry.ip_address or '',
                entry.user_agent,
                _changes_to_csv(entry.changes),
            ])

        return response


def _changes_to_csv(changes):
    """Flatten the changes dict into a compact string for CSV."""
    if not changes:
        return ''
    parts = []
    for field, values in changes.items():
        if isinstance(values, dict) and ('old' in values or 'new' in values):
            parts.append(f'{field}: {values.get("old")} -> {values.get("new")}')
        else:
            parts.append(f'{field}: {values}')
    return '; '.join(parts)