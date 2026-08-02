"""
Audit-trail middleware.

Captures the authenticated user, client IP address (X-Forwarded-For aware),
and user-agent for every request and stores them in thread-local storage so
that signal handlers and business logic can access them when writing
audit-log entries.

The middleware must come **after** ``AuthenticationMiddleware`` so that
``request.user`` is populated.
"""
from .current import set_context, clear_context


def _get_client_ip(request):
    """
    Return the client's IP address.

    Honours ``X-Forwarded-For`` (first hop) when present so that the real
    client IP is recorded behind a reverse proxy; falls back to
    ``REMOTE_ADDR``.
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        # X-Forwarded-For may contain a comma-separated list; the first
        # entry is the original client.
        ip = x_forwarded_for.split(',')[0].strip()
        if ip:
            return ip
    return request.META.get('REMOTE_ADDR')


class AuditMiddleware:
    """Populate thread-local request context for audit logging."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Determine the authenticated user (may be AnonymousUser).
        user = getattr(request, 'user', None)
        if user is not None and not getattr(user, 'is_authenticated', False):
            user = None

        ip_address = _get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')

        set_context(
            user=user,
            ip_address=ip_address,
            user_agent=user_agent,
            request=request,
        )

        try:
            response = self.get_response(request)
        finally:
            # Always clear the thread-local context to avoid leaking data
            # across requests handled by the same thread (e.g. in a
            # threaded server that reuses worker threads).
            clear_context()

        return response