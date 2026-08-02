"""
Thread-local storage for the current request context.

This module provides a lightweight, dependency-free alternative to
``django-crum`` / ``django-cuser``.  The :class:`AuditMiddleware` stores the
authenticated user, IP address, and user-agent for the *current* request into a
``threading.local`` so that signal handlers (which run outside the view layer)
can access them when writing audit-log entries.

Usage from signal handlers or business logic::

    from audit.current import get_current_user, get_current_ip

    user = get_current_user()      # User instance or None
    ip = get_current_ip()          # str or None
    ua = get_current_user_agent()  # str or ''
"""
import threading

_local = threading.local()


def _get(attr, default=None):
    return getattr(_local, attr, default)


def get_current_user():
    """Return the authenticated user for the current request, or ``None``."""
    return _get('user', None)


def get_current_ip():
    """Return the client IP address for the current request, or ``None``."""
    return _get('ip_address', None)


def get_current_user_agent():
    """Return the user-agent string for the current request, or ``''``."""
    return _get('user_agent', '')


def get_current_request():
    """Return the current HttpRequest object, or ``None`` (outside a request)."""
    return _get('request', None)


def set_context(user=None, ip_address=None, user_agent='', request=None):
    """Populate the thread-local context (called by middleware)."""
    _local.user = user
    _local.ip_address = ip_address
    _local.user_agent = user_agent or ''
    _local.request = request


def clear_context():
    """Clear the thread-local context (called after the response is sent)."""
    for attr in ('user', 'ip_address', 'user_agent', 'request'):
        if hasattr(_local, attr):
            delattr(_local, attr)