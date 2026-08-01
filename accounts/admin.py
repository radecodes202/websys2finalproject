from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group
from .models import User

# Unregister the default Group model if not used
admin.site.unregister(Group)

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'role', 'is_approved', 'date_joined', 'is_staff')
    list_filter = ('is_approved', 'role', 'is_staff', 'is_superuser')
    search_fields = ('username', 'email')
    ordering = ('username',)
    filter_horizontal = ()

    # For adding a user via admin
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'role', 'password1', 'password2')
        }),
    )
    # For editing existing user
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email')}),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'role', 'is_approved', 'groups', 'user_permissions')
        }),
        ('Important dates', {'fields': ('last_login', 'date_joined', 'date_requested')}),
    )
