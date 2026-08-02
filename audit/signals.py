"""
Audit-trail signal handlers.

Wires ``pre_save`` / ``post_save`` / ``post_delete`` signals for every core
model so that CREATE / UPDATE / DELETE actions are captured automatically with
field-level diffs — no manual calls required in the CRUD views.

Models covered
--------------
* ``accounts.User``
* ``category.Category``
* ``product.Product``, ``PurchaseOrder``, ``StockReceipt``, ``StockMovement``,
  ``Sale``, ``Payment``
* ``supplier.Supplier``, ``SupplierPayment``
* ``customer.Customer``

How it works
------------
1. **``pre_save``** — if the instance already has a ``pk``, fetch the *old*
   row from the database and stash it on ``instance._audit_old`` so that
   ``post_save`` can compute a real field-level diff.  If there is no ``pk``
   yet, this is a CREATE.
2. **``post_save``** — CREATE → log with ``old=None`` for every field;
   UPDATE → log only the fields that changed via :func:`model_diff`.
3. **``post_delete``** — log a DELETE with a full snapshot of the row captured
   in ``pre_delete`` (so the data is preserved even after the row is gone).

All logging goes through :func:`audit.services.log_activity`, which isolates
errors so a logging failure never breaks the main transaction.
"""
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.db.models.signals import post_delete, post_save, pre_delete, pre_save
from django.dispatch import receiver

from .models import AuditLog
from .services import instance_snapshot, log_activity, model_diff

# --------------------------------------------------------------------------- #
# Registry of models to audit
# --------------------------------------------------------------------------- #
# Each entry maps a model (as "app_label.ModelName") to a human-readable label
# used in the audit description.  The actual model classes are resolved lazily
# via django.apps.apps.get_model to avoid circular imports at import time.
_AUDITED_MODELS = {
    'accounts.User': 'User',
    'category.Category': 'Category',
    'product.Product': 'Product',
    'product.PurchaseOrder': 'Purchase Order',
    'product.StockReceipt': 'Stock Receipt',
    'product.StockMovement': 'Stock Movement',
    'product.Sale': 'Sale',
    'product.Payment': 'Payment',
    'supplier.Supplier': 'Supplier',
    'supplier.SupplierPayment': 'Supplier Payment',
    'customer.Customer': 'Customer',
}

# Models whose CREATE should be logged with ACTION_PAYMENT instead of
# ACTION_CREATE, since they represent payment events.
_PAYMENT_MODELS = {
    'product.Payment',
    'supplier.SupplierPayment',
}


def _model_label(instance):
    """Return a human-readable label for the instance's model."""
    label = f'{instance._meta.app_label}.{instance._meta.object_name}'
    return _AUDITED_MODELS.get(label, instance._meta.object_name)


def _model_key(instance):
    """Return the 'app_label.ModelName' key for the instance."""
    return f'{instance._meta.app_label}.{instance._meta.object_name}'


# --------------------------------------------------------------------------- #
# pre_save — capture old state for UPDATE diffing
# --------------------------------------------------------------------------- #
@receiver(pre_save)
def _audit_pre_save(sender, instance, **kwargs):
    """Stash the pre-save row so post_save can compute a diff."""
    # Only process models in our registry.
    key = _model_key(instance)
    if key not in _AUDITED_MODELS:
        return

    if instance.pk is None:
        # New record — no old state.
        instance._audit_old = None
        instance._audit_is_create = True
    else:
        # Existing record — fetch the current DB state for diffing.
        try:
            old = sender.objects.filter(pk=instance.pk).first()
        except Exception:  # noqa: BLE001
            old = None
        instance._audit_old = old
        instance._audit_is_create = False


# --------------------------------------------------------------------------- #
# post_save — log CREATE / UPDATE
# --------------------------------------------------------------------------- #
@receiver(post_save)
def _audit_post_save(sender, instance, created, **kwargs):
    """Log a CREATE or UPDATE action with a field-level diff."""
    key = _model_key(instance)
    if key not in _AUDITED_MODELS:
        return

    model_label = _model_label(instance)

    if created:
        # ---- CREATE --------------------------------------------------- #
        changes = model_diff(None, instance)
        # Use ACTION_PAYMENT for payment models, ACTION_CREATE otherwise.
        if key in _PAYMENT_MODELS:
            action = AuditLog.ACTION_PAYMENT
            description = f'Recorded {model_label}: {instance}'
        else:
            action = AuditLog.ACTION_CREATE
            description = f'Created {model_label}: {instance}'
        log_activity(
            action=action,
            instance=instance,
            description=description,
            changes=changes,
            severity=AuditLog.SEVERITY_INFO,
        )
    else:
        # ---- UPDATE --------------------------------------------------- #
        old = getattr(instance, '_audit_old', None)
        changes = model_diff(old, instance)
        if not changes:
            # Nothing meaningful changed (e.g. only auto timestamps) — skip.
            return
        log_activity(
            action=AuditLog.ACTION_UPDATE,
            instance=instance,
            description=f'Updated {model_label}: {instance}',
            changes=changes,
            severity=AuditLog.SEVERITY_INFO,
        )


# --------------------------------------------------------------------------- #
# pre_delete — capture a full snapshot before the row is removed
# --------------------------------------------------------------------------- #
@receiver(pre_delete)
def _audit_pre_delete(sender, instance, **kwargs):
    """Stash a full snapshot so post_delete can log it."""
    key = _model_key(instance)
    if key not in _AUDITED_MODELS:
        return
    instance._audit_snapshot = instance_snapshot(instance)
    instance._audit_repr = str(instance)


# --------------------------------------------------------------------------- #
# post_delete — log DELETE
# --------------------------------------------------------------------------- #
@receiver(post_delete)
def _audit_post_delete(sender, instance, **kwargs):
    """Log a DELETE action with the pre-deletion snapshot."""
    key = _model_key(instance)
    if key not in _AUDITED_MODELS:
        return

    model_label = _model_label(instance)
    snapshot = getattr(instance, '_audit_snapshot', None)
    object_repr = getattr(instance, '_audit_repr', str(instance))

    log_activity(
        action=AuditLog.ACTION_DELETE,
        instance=instance,
        description=f'Deleted {model_label}: {object_repr}',
        changes=snapshot,
        severity=AuditLog.SEVERITY_WARNING,
        object_repr=object_repr,
    )


# --------------------------------------------------------------------------- #
# Auth signals — login / logout / failed login
# --------------------------------------------------------------------------- #
@receiver(user_logged_in)
def _audit_user_logged_in(sender, request, user, **kwargs):
    """Log a successful login."""
    log_activity(
        user=user,
        action=AuditLog.ACTION_LOGIN,
        instance=user,
        description=f'User "{user.username}" logged in.',
        severity=AuditLog.SEVERITY_INFO,
        request=request,
    )


@receiver(user_logged_out)
def _audit_user_logged_out(sender, request, user, **kwargs):
    """Log a logout."""
    # ``user`` may be None if the session was already anonymous.
    username = getattr(user, 'username', '') if user else ''
    log_activity(
        user=user,
        action=AuditLog.ACTION_LOGOUT,
        instance=user,
        object_repr=f'User: {username}' if username else 'User: (anonymous)',
        description=f'User "{username}" logged out.' if username else 'Anonymous session ended.',
        severity=AuditLog.SEVERITY_INFO,
        request=request,
    )


@receiver(user_login_failed)
def _audit_user_login_failed(sender, credentials, request, **kwargs):
    """Log a failed login attempt.

    The user object is not available on this signal (the credentials did not
    authenticate), so we record the attempted username from ``credentials``
    and mark the severity as ``WARNING``.
    """
    attempted_username = ''
    if isinstance(credentials, dict):
        attempted_username = credentials.get('username', '') or ''

    log_activity(
        user=None,
        action=AuditLog.ACTION_LOGIN_FAILED,
        instance=None,
        object_repr=f'Login attempt: {attempted_username}' if attempted_username else 'Login attempt',
        description=(
            f'Failed login attempt for username "{attempted_username}".'
            if attempted_username else 'Failed login attempt (no username).'
        ),
        severity=AuditLog.SEVERITY_WARNING,
        request=request,
    )
