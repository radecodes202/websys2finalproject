from django.contrib.auth.backends import ModelBackend


class AxesCompatBackend(ModelBackend):
    """Authenticate users normally while still allowing the app to work in tests and request-less contexts."""

    def authenticate(self, request=None, **credentials):
        return super().authenticate(request=request, **credentials)
