from django.apps import AppConfig


class AuditConfig(AppConfig):
    name = 'audit'
    verbose_name = 'Audit Trail'

    def ready(self):
        # Import signal handlers so they are registered when the app is loaded.
        from . import signals  # noqa: F401