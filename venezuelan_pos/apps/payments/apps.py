from django.apps import AppConfig


class PaymentsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'venezuelan_pos.apps.payments'
    verbose_name = 'Payment Processing'
    
    def ready(self):
        """Import signals when app is ready."""
        try:
            import venezuelan_pos.apps.payments.signals  # noqa
        except ImportError:
            pass