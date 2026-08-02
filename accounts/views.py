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
from django.views.generic import ListView, TemplateView
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.utils import timezone
from django.contrib.auth import get_user_model
from product.models import Alert, Product, Sale
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

        context['product_count'] = Product.objects.count()
        context['today_sales_count'] = Sale.objects.filter(date__date=today).count()
        context['low_stock_count'] = Product.objects.filter(quantity_in_stock__lte=models.F('reorder_level')).count()
        context['alerts_count'] = Alert.objects.filter(is_resolved=False).count()
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
    """Admin/Manager page for managing users with full edit, deactivate, and delete."""
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


# Password change views using Django's built-in views
# We're just pointing to them, but we could customize if needed
