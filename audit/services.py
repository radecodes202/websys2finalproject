"""
Audit-trail logging service.

This module provides a single reusable entry point — :func:`log_activity` —
that both signal handlers and view/business logic call to write an
:class:`audit.models.AuditLog` entry consistently.

Key guarantees
--------------
* **Never breaks the main transaction.**  Every logging call is wrapped in a
  ``try/except``.  If the audit write fails (e.g. serialization error), the
  failure is reported to Python's standard ``logging`` instead of propagating.
* **Safe serialization.**  Field values are converted to JSON-safe primitives
  before being stored in the ``changes`` JSONField.  Dates, decimals, and
  foreign keys are handled explicitly (FKs are stored as ``"id - str(obj)"``).
* **Append-only.**  The function always creates a *new* ``AuditLog`` row; it
  never updates an existing one.
* **Context-aware.**  When ``request`` is not supplied, the function falls back
  to the thread-local context populated by :class:`audit.middleware.AuditMiddleware`
  so that signal handlers (which have no request object) still capture the
  user / IP / user-agent.
"""
import logging
from datetime import date, datetime, time
from decimal import Decimal

from django.contrib.contenttypes.models import ContentType
from django.db import models

from .current import get_current_ip, get_current_request, get_current_user, get_current_user_agent
from .models import AuditLog

logger = logging.getLogger('audit')

# Fields that are never interesting in a diff and would only add noise.
_EXCLUDED_FIELD_NAMES = {
    'created_at', 'updated_at', 'last_login', 'date_joined',
    'password', 'date_requested',
}


# --------------------------------------------------------------------------- #
# Serialization helpers
# --------------------------------------------------------------------------- #
def _serialize_value(value):
    """
    Convert a Python/Django field value into a JSON-safe primitive.

    * ``None`` → ``None``
    * Dates / datetimes / times → ISO-format strings
    * ``Decimal`` → ``str`` (preserves precision, avoids float rounding)
    * Django model instances (FKs) → ``"id - str(obj)"``
    * QuerySets / iterables → list of serialized items
    * Everything else → returned as-is (Django's JSONField will attempt
      serialisation and fall back to ``str`` via the DjangoJSONEncoder).
    """
    if value is None:
        return None

    # Django model instance (FK / one-to-one) — store "id - str(obj)".
    if isinstance(value, models.Model):
        return f'{value.pk} - {value}'

    # Date / time types.
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, time):
        return value.isoformat()

    # Decimal — preserve exact representation as a string.
    if isinstance(value, Decimal):
        return str(value)

    # Iterables (but not strings/bytes which are fine as-is).
    if isinstance(value, (list, tuple, set)):
        return [_serialize_value(v) for v in value]

    # Django QuerySet.
    if hasattr(value, 'all') and callable(getattr(value, 'all', None)):
        try:
            return [_serialize_value(v) for v in value.all()]
        except Exception:  # noqa: BLE001
            return str(value)

    return value


def _field_value_for_audit(instance, field_name):
    """
    Return a JSON-safe value for ``field_name`` on ``instance``.

    Handles forward relations (FK / one-to-one) by reading the cached
    attribute rather than triggering a fresh DB query when possible.
    """
    # Try the concrete field first (handles FKs by returning the related pk).
    try:
        field = instance._meta.get_field(field_name)
    except Exception:  # noqa: BLE001
        # Not a model field (e.g. a property) — read the attribute directly.
        return _serialize_value(getattr(instance, field_name, None))

    # Foreign key / one-to-one — Django stores the related pk in
    # ``<field_name>_id``.  Prefer the related object if it is cached.
    if isinstance(field, (models.ForeignKey, models.OneToOneField)):
        related = getattr(instance, field_name, None)
        if related is not None:
            return _serialize_value(related)
        # Fall back to the raw pk column.
        pk = getattr(instance, f'{field_name}_id', None)
        return pk

    # Many-to-many — only meaningful if the instance already has a pk.
    if isinstance(field, models.ManyToManyField):
        if instance.pk is None:
            return []
        try:
            return [_serialize_value(v) for v in getattr(instance, field_name).all()]
        except Exception:  # noqa: BLE001
            return []

    # Plain field.
    return _serialize_value(getattr(instance, field_name, None))


def model_diff(old_instance, new_instance, excluded=None):
    """
    Compute a field-level before/after diff between two model instances.

    Returns a dict keyed by field name whose values are
    ``{"old": <value>, "new": <value>}``.  Only fields that actually changed
    are included.

    Parameters
    ----------
    old_instance : Model | None
        The instance before the change.  ``None`` means the record is new
        (a CREATE) — every field is reported with ``old=None``.
    new_instance : Model
        The instance after the change.
    excluded : set, optional
        Field names to skip.  Defaults to :data:`_EXCLUDED_FIELD_NAMES`.
    """
    if excluded is None:
        excluded = _EXCLUDED_FIELD_NAMES

    diff = {}
    for field in new_instance._meta.get_fields():
        # Skip reverse relations and auto-created m2m-through fields.
        if not getattr(field, 'concrete', False):
            continue
        name = field.name
        if name in excluded:
            continue
        # Skip many-to-many on CREATE (no pk yet) — handled per-field above.
        if isinstance(field, models.ManyToManyField) and new_instance.pk is None:
            continue

        old_val = _field_value_for_audit(old_instance, name) if old_instance is not None else None
        new_val = _field_value_for_audit(new_instance, name)

        if old_val != new_val:
            diff[name] = {'old': old_val, 'new': new_val}
    return diff


def instance_snapshot(instance, excluded=None):
    """
    Return a JSON-safe snapshot of all concrete fields on ``instance``.

    Used to capture the *before* state of an object that is about to be
    deleted (so the full record is preserved in the audit log).
    """
    if excluded is None:
        excluded = _EXCLUDED_FIELD_NAMES

    snapshot = {}
    for field in instance._meta.get_fields():
        if not getattr(field, 'concrete', False):
            continue
        name = field.name
        if name in excluded:
            continue
        if isinstance(field, models.ManyToManyField):
            if instance.pk is None:
                snapshot[name] = []
            else:
                try:
                    snapshot[name] = [_serialize_value(v) for v in getattr(instance, name).all()]
                except Exception:  # noqa: BLE001
                    snapshot[name] = []
        else:
            snapshot[name] = _field_value_for_audit(instance, name)
    return snapshot


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #
def log_activity(
    user=None,
    action=AuditLog.ACTION_OTHER,
    instance=None,
    description='',
    changes=None,
    severity=AuditLog.SEVERITY_INFO,
    request=None,
    content_type=None,
    object_id=None,
    object_repr=None,
    ip_address=None,
    user_agent=None,
):
    """
    Write a single :class:`AuditLog` entry.

    This is the **only** function that should create ``AuditLog`` rows.  It
    centralises context resolution (user / IP / user-agent), serialisation,
    and error isolation.

    Parameters
    ----------
    user : User, optional
        The actor.  If ``None``, falls back to the thread-local current user.
    action : str
        One of ``AuditLog.ACTION_*``.
    instance : Model, optional
        The affected record.  When supplied, ``content_type``, ``object_id``,
        and ``object_repr`` are derived automatically.
    description : str
        Human-readable summary.
    changes : dict, optional
        Structured before/after diff (see :func:`model_diff`).
    severity : str
        One of ``AuditLog.SEVERITY_*``.
    request : HttpRequest, optional
        If supplied, the user / IP / user-agent are read from it.  Otherwise
        the thread-local context is used.
    content_type / object_id / object_repr : optional
        Override the values derived from ``instance`` (useful for auth events
        that have no model instance).
    ip_address / user_agent : optional
        Override the values derived from the request / thread-local context.

    Returns
    -------
    AuditLog | None
        The created entry, or ``None`` if the write failed (the failure is
        logged to Python's ``logging`` instead of being raised).
    """
    try:
        # ---- Resolve context ------------------------------------------- #
        req = request or get_current_request()

        if user is None:
            if req is not None and getattr(req, 'user', None) is not None:
                u = req.user
                user = u if getattr(u, 'is_authenticated', False) else None
            else:
                user = get_current_user()

        if ip_address is None:
            if req is not None:
                ip_address = req.META.get('REMOTE_ADDR')
            if ip_address is None:
                ip_address = get_current_ip()

        if user_agent is None:
            if req is not None:
                user_agent = req.META.get('HTTP_USER_AGENT', '')
            else:
                user_agent = get_current_user_agent()

        # ---- Derive generic-relation fields from the instance --------- #
        if instance is not None:
            if content_type is None:
                content_type = ContentType.objects.get_for_model(instance)
            if object_id is None:
                object_id = str(instance.pk) if instance.pk is not None else None
            if object_repr is None:
                object_repr = str(instance)[:255]

        # ---- Username snapshot ---------------------------------------- #
        username_snapshot = ''
        if user is not None:
            username_snapshot = getattr(user, 'username', '') or ''

        # ---- Create the entry (append-only) --------------------------- #
        entry = AuditLog(
            user=user,
            username_snapshot=username_snapshot,
            action=action,
            content_type=content_type,
            object_id=object_id,
            object_repr=object_repr or '',
            changes=changes,
            description=description or '',
            ip_address=ip_address,
            user_agent=user_agent or '',
            severity=severity,
        )
        entry.save(force_insert=True)
        return entry

    except Exception as exc:  # noqa: BLE001
        # Logging must never break the main transaction.
        logger.exception('Failed to write audit log: %s', exc)
        return None