from django.apps import AppConfig


class PurchaseConfig(AppConfig):
    """App config for the purchasing domain.

    Holds the views, forms and templates that drive the
    purchase-order management workflow (create / update / receive / cancel)
    plus the later supplier-payment monitoring UI.

    The underlying models themselves live in the ``product`` app alongside the
    other inventory-transaction models (Sale, StockMovement, …).
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'purchase'
    verbose_name = 'Purchasing'
