from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model

User = get_user_model()

# Roles that a regular user can self-select during registration.
# 'admin' is deliberately excluded — only existing admins
# can register new admins via the admin-only registration view.
SELF_REGISTER_ROLE_CHOICES = [
    ('manager', 'Manager'),
    ('cashier', 'Cashier'),
    ('inventory_staff', 'Inventory Staff'),
]


class CustomUserCreationForm(UserCreationForm):
    """Form used by anonymous visitors to self-register.

    The ``role`` field is restricted to non-admin choices so that
    no one can grant themselves admin privileges.
    """
    email = forms.EmailField(required=True, label='Email')
    role = forms.ChoiceField(
        choices=SELF_REGISTER_ROLE_CHOICES,
        initial='cashier',
        label='Role',
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'role', 'password1', 'password2')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.role = self.cleaned_data['role']
        if commit:
            user.save()
        return user


class AdminUserCreationForm(UserCreationForm):
    """Form used by admins to register new users (including admins).

    All roles — including ``admin`` — are available here so that an
    existing admin can onboard other admins.
    """
    email = forms.EmailField(required=True, label='Email')
    role = forms.ChoiceField(
        choices=User.ROLE_CHOICES,
        initial='cashier',
        label='Role',
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'role', 'password1', 'password2')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.role = self.cleaned_data['role']
        # Users created by an admin are immediately approved.
        user.is_approved = True
        if commit:
            user.save()
        return user
