from django.db import models
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.views import PasswordChangeView, PasswordChangeDoneView
from django.contrib import messages
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import ListView, TemplateView
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.utils import timezone
from django.contrib.auth import get_user_model
from product.models import Alert, Product, Sale
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
        if form.is_valid():
            user = form.get_user()
            if user.is_approved:
                login(request, user)
                messages.success(request, f'Welcome back, {user.username}!')
                return redirect('home')
            else:
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
            return redirect('accounts:pending_users')
        else:
            messages.error(request, 'Please correct the errors below.')
        return render(request, self.template_name, {'form': form})


class PendingUserListView(RoleRequiredMixin, ListView):
    """Admin-only view to review and approve pending user registrations."""
    model = User
    template_name = 'accounts/pending_users.html'
    context_object_name = 'pending_users'
    allowed_roles = ['admin']

    def get_queryset(self):
        return User.objects.filter(is_approved=False)

    def post(self, request):
        user_id = request.POST.get('user_id')
        if user_id:
            user = get_object_or_404(User, id=user_id)
            user.is_approved = True
            user.save()
            messages.success(request, f'User {user.username} has been approved.')
        return redirect('accounts:pending_users')


# Password change views using Django's built-in views
# We're just pointing to them, but we could customize if needed
