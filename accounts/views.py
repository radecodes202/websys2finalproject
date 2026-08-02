from django.db import models
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.signals import user_logged_in
from django.contrib.auth.views import (
    PasswordChangeView,
    PasswordChangeDoneView,
    PasswordResetView,
    PasswordResetDoneView,
    PasswordResetConfirmView,
    PasswordResetCompleteView,
)
from django.contrib import messages
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import ListView, TemplateView, UpdateView
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.utils import timezone
from django.contrib.auth import get_user_model
from product.models import Alert, Product, Sale, PurchaseOrder
from audit.services import log_activity
from audit.models import AuditLog
from .forms import CustomUserCreationForm, AdminUserCreationForm
from .mixins import RoleRequiredMixin

User = get_user_model()


@method_decorator(login_required, name='dispatch')
class HomeView(TemplateView):
    template_name = 'home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.localdate()
        user = self.request.user

        # Date-range filter
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        if date_from and date_to:
            try:
                date_from_obj = timezone.datetime.strptime(date_from, '%Y-%m-%d').date()
                date_to_obj = timezone.datetime.strptime(date_to, '%Y-%m-%d').date()
                sale_qs = Sale.objects.filter(date__date__gte=date_from_obj, date__date__lte=date_to_obj)
            except ValueError:
                sale_qs = Sale.objects.none()
        else:
            sale_qs = Sale.objects.filter(date__date=today)

        # Common KPIs
        context['product_count'] = Product.objects.count()
        context['low_stock_count'] = Product.objects.filter(quantity_in_stock__lte=models.F('reorder_level')).count()
        context['alerts_count'] = Alert.objects.filter(is_resolved=False).count()

        # Sales KPIs
        context['today_sales_count'] = sale_qs.count()
        context['date_from'] = date_from
        context['date_to'] = date_to

        # Today's Profit = sum((unit_price - cost_price) * quantity) for completed sales today
        from django.db.models import Sum, F, DecimalField, ExpressionWrapper
        profit_expr = ExpressionWrapper(
            F('items__unit_price') - F('items__product__cost_price'),
            output_field=DecimalField()
        )
        completed_sales_qs = sale_qs.filter(status=Sale.STATUS_COMPLETED)
        context['today_profit'] = completed_sales_qs.annotate(
            item_profit=profit_expr
        ).aggregate(
            total_profit=Sum('item_profit')
        )['total_profit'] or 0

        # Pending POs
        context['pending_po_count'] = PurchaseOrder.objects.filter(status=PurchaseOrder.STATUS_PENDING).count()

        # Chart data preparation
        from django.db.models import Sum, F, DecimalField, ExpressionWrapper
        from collections import defaultdict
        import json

        # Sales trend (last 7 days)
        sales_trend_labels = []
        sales_trend_data = []
        for i in range(6, -1, -1):
            d = today - timezone.timedelta(days=i)
            sales_trend_labels.append(d.strftime('%Y-%m-%d'))
            daily_total = Sale.objects.filter(date__date=d, status=Sale.STATUS_COMPLETED).aggregate(
                total=Sum('total')
            )['total'] or 0
            sales_trend_data.append(float(daily_total))

        # Top selling products
        top_products = SaleItem.objects.filter(sale__status=Sale.STATUS_COMPLETED).values('product__name').annotate(
            total_qty=Sum('quantity')
        ).order_by('-total_qty')[:5]
        top_products_labels = [item['product__name'] for item in top_products]
        top_products_data = [int(item['total_qty']) for item in top_products]

        # Sales by category
        category_sales = SaleItem.objects.filter(sale__status=Sale.STATUS_COMPLETED).values('product__category__name').annotate(
            total=Sum('subtotal')
        ).order_by('-total')[:5]
        category_labels = [item['product__category__name'] for item in category_sales]
        category_data = [float(item['total']) for item in category_sales]

        # Profit margin trend (last 7 days)
        profit_trend_labels = []
        profit_trend_data = []
        for i in range(6, -1, -1):
            d = today - timezone.timedelta(days=i)
            profit_trend_labels.append(d.strftime('%Y-%m-%d'))
            day_sales = Sale.objects.filter(date__date=d, status=Sale.STATUS_COMPLETED)
            profit = day_sales.annotate(
                item_profit=ExpressionWrapper(
                    F('items__unit_price') - F('items__product__cost_price'),
                    output_field=DecimalField()
                )
            ).aggregate(total_profit=Sum('item_profit'))['total_profit'] or 0
            revenue = day_sales.aggregate(total=Sum('total'))['total'] or 0
            margin = (profit / revenue * 100) if revenue > 0 else 0
            profit_trend_data.append(round(float(margin), 2))

        context.update({
            'sales_trend_labels': json.dumps(sales_trend_labels),
            'sales_trend_data': json.dumps(sales_trend_data),
            'top_products_labels': json.dumps(top_products_labels),
            'top_products_data': json.dumps(top_products_data),
            'category_labels': json.dumps(category_labels),
            'category_data': json.dumps(category_data),
            'profit_trend_labels': json.dumps(profit_trend_labels),
            'profit_trend_data': json.dumps(profit_trend_data),
        })

        # Role-specific KPIs
        if getattr(user, 'role', None) == 'cashier':
            context['my_today_sales_count'] = Sale.objects.filter(date__date=today, cashier=user).count()
        else:
            context['my_today_sales_count'] = None

        return context


class LoginView(View):
    template_name = 'accounts/login.html'

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('home')
        form = AuthenticationForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = AuthenticationForm(request, data=request.POST)
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request=request, username=username, password=password)

        if user is not None and user.is_approved:
            login(request, user)
            user_logged_in.send(sender=self.__class__, request=request, user=user)
            messages.success(request, f'Welcome back, {user.username}!')
            return redirect('home')

        if user is not None and not user.is_approved:
            messages.error(request, 'Your account is pending approval by an administrator.')
        else:
            messages.error(request, 'Invalid username or password.')
        return render(request, self.template_name, {'form': form})


class LogoutView(View):
    def get(self, request):
        logout(request)
        messages.info(request, 'You have been logged out.')
        return redirect('accounts:login')


class RegisterView(View):
    template_name = 'accounts/register.html'

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('home')
        form = CustomUserCreationForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_approved = False  # Requires admin approval
            user.save()
            messages.success(request, 'Your account has been created and is pending approval. You will be notified once approved.')
            return redirect('accounts:login')
        else:
            messages.error(request, 'Please correct the errors below.')
        return render(request, self.template_name, {'form': form})


class AdminRegisterView(RoleRequiredMixin, View):
    """Admin-only view to register new users, including other admins.

    Only users with the ``admin`` role can access this view.
    Users created here (including admins) are immediately approved
    and active, bypassing the pending-approval workflow.
    """
    template_name = 'accounts/admin_register.html'
    allowed_roles = ['admin']

    def get(self, request):
        form = AdminUserCreationForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = AdminUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=True)
            messages.success(request, f'User {user.username} has been registered and approved.')
            return redirect('accounts:user-management')
        else:
            messages.error(request, 'Please correct the errors below.')
        return render(request, self.template_name, {'form': form})


class UserManagementView(RoleRequiredMixin, View):
    """Admin/Manager page for managing users with full edit, deactivate, and delete.

    Edit policy:
      * Admin can edit any user.
      * Manager can only edit Cashier and Inventory Staff accounts.
      This restriction prevents Managers from escalating their own privileges.
    """
    template_name = 'accounts/user_management.html'
    allowed_roles = ['admin', 'manager']

    def get(self, request):
        status_filter = request.GET.get('status', 'all')
        users = User.objects.order_by('-date_joined')

        if status_filter == 'active':
            users = users.filter(is_active=True, is_approved=True)
        elif status_filter == 'pending':
            users = users.filter(is_approved=False)
        elif status_filter == 'inactive':
            users = users.filter(is_active=False)

        return render(request, self.template_name, {
            'users': users,
            'status_filter': status_filter,
        })

    def post(self, request):
        user_id = request.POST.get('user_id')
        action = request.POST.get('action')

        if not user_id:
            messages.error(request, 'No user was selected.')
            return redirect('accounts:user-management')

        user = get_object_or_404(User, id=user_id)

        if action == 'approve':
            if user == request.user:
                messages.error(request, 'You cannot approve your own account.')
            elif not self._is_admin(request.user):
                messages.error(request, 'Only admins can approve accounts.')
            else:
                user.is_approved = True
                user.save(update_fields=['is_approved'])
                log_activity(
                    user=request.user,
                    action=AuditLog.ACTION_UPDATE,
                    instance=user,
                    description=f'User {user.username} was approved.',
                    changes={'is_approved': {'old': False, 'new': True}},
                )
                messages.success(request, f'User {user.username} has been approved.')

        elif action == 'reject':
            if user == request.user:
                messages.error(request, 'You cannot reject your own account.')
            elif not self._is_admin(request.user):
                messages.error(request, 'Only admins can reject accounts.')
            else:
                username = user.username
                log_activity(
                    user=request.user,
                    action=AuditLog.ACTION_DELETE,
                    instance=user,
                    description=f'User {username} was rejected and removed.',
                )
                user.delete()
                messages.success(request, f'User {username} has been rejected and removed.')

        elif action == 'edit':
            if user == request.user:
                messages.error(request, 'You cannot edit your own account from here.')
            elif not self._can_edit(request.user, user):
                messages.error(request, 'Managers can only edit Cashier and Inventory Staff accounts.')
            else:
                user.username = request.POST.get('username', user.username)
                user.first_name = request.POST.get('first_name', user.first_name)
                user.last_name = request.POST.get('last_name', user.last_name)
                user.email = request.POST.get('email', user.email)
                if self._is_admin(request.user):
                    role = request.POST.get('role')
                    if role in dict(User.ROLE_CHOICES):
                        user.role = role
                is_active = request.POST.get('is_active')
                if is_active is not None:
                    user.is_active = is_active == 'true'
                user.save()
                log_activity(
                    user=request.user,
                    action=AuditLog.ACTION_UPDATE,
                    instance=user,
                    description=f'User {user.username} was updated.',
                )
                messages.success(request, f'User {user.username} has been updated.')

        elif action == 'toggle_active':
            if user == request.user:
                messages.error(request, 'You cannot change your own active status.')
            elif self._is_last_admin(user):
                messages.error(request, 'The last remaining admin account cannot be deactivated or deleted.')
            else:
                user.is_active = not user.is_active
                user.save(update_fields=['is_active'])
                status = 'activated' if user.is_active else 'deactivated'
                log_activity(
                    user=request.user,
                    action=AuditLog.ACTION_UPDATE,
                    instance=user,
                    description=f'User {user.username} was {status}.',
                    changes={'is_active': {'old': not user.is_active, 'new': user.is_active}},
                )
                messages.success(request, f'User {user.username} has been {status}.')

        elif action == 'delete':
            if user == request.user:
                messages.error(request, 'You cannot delete your own account.')
            elif not self._is_admin(request.user):
                messages.error(request, 'Only admins can delete accounts.')
            elif self._is_last_admin(user):
                messages.error(request, 'The last remaining admin account cannot be deleted.')
            elif self._has_history(user):
                messages.error(request, 'This user has historical activity and cannot be deleted — deactivate instead.')
            else:
                log_activity(
                    user=request.user,
                    action=AuditLog.ACTION_DELETE,
                    instance=user,
                    description=f'User {user.username} was permanently deleted.',
                )
                user.delete()
                messages.success(request, f'User has been permanently deleted.')
        else:
            messages.error(request, 'Unsupported action.')

        return redirect('accounts:user-management')

    def _is_admin(self, user):
        return getattr(user, 'role', None) == 'admin'

    def _is_last_admin(self, user):
        if self._is_admin(user):
            active_admins = User.objects.filter(role='admin', is_active=True).count()
            return active_admins <= 1
        return False

    def _can_edit(self, actor, target):
        """Check if actor can edit target.

        Admin can edit anyone. Manager can edit Cashier and Inventory Staff only.
        """
        if self._is_admin(actor):
            return True
        if self._is_admin(target):
            return False
        return target.role in ('cashier', 'inventory_staff')

    def _has_history(self, user):
        return (
            user.sales.exists()
            or user.created_purchase_orders.exists()
            or user.received_stock_receipts.exists()
            or user.audit_logs.exists()
            or getattr(user, 'activity_logs', None) is not None and user.activity_logs.exists()
        )


class CustomPasswordResetView(PasswordResetView):
    email_template_name = 'accounts/password_reset_email.html'
    template_name = 'accounts/password_reset.html'
    success_url = reverse_lazy('accounts:password_reset_done')


class CustomPasswordResetDoneView(PasswordResetDoneView):
    template_name = 'accounts/password_reset_done.html'


class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = 'accounts/password_reset_confirm.html'
    success_url = reverse_lazy('accounts:password_reset_complete')


class CustomPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = 'accounts/password_reset_complete.html'


class ProfileView(RoleRequiredMixin, UpdateView):
    """Allow a logged-in user to edit their own profile."""
    model = User
    template_name = 'accounts/profile_form.html'
    fields = ['first_name', 'last_name', 'email']
    success_url = reverse_lazy('home')

    def get_object(self, queryset=None):
        return self.request.user

    def form_valid(self, form):
        messages.success(self.request, 'Profile updated successfully.')
        return super().form_valid(form)


# Password change views using Django's built-in views
# We're just pointing to them, but we could customize if needed
