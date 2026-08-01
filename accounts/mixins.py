from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin


class RoleRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    Mixin that requires the user to be logged in AND have one of the
    allowed roles.

    Set ``allowed_roles`` to a list of role strings, e.g.::

        class ProductListView(RoleRequiredMixin, ListView):
            allowed_roles = ['admin', 'manager', 'inventory_staff']

    Behaviour:
      * Anonymous user  → redirect to ``settings.LOGIN_URL``.
      * Authenticated user with a permitted role → view is allowed.
      * Authenticated user with a non-permitted role → 403 Forbidden.
    """
    allowed_roles = []

    def test_func(self):
        return self.request.user.role in self.allowed_roles
