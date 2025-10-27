from django.apps import AppConfig


class SalesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "venezuelan_pos.apps.sales"
    verbose_name = "Sales Engine"
    
    def ready(self):
        """Import signals when app is ready."""
        try:
            import venezuelan_pos.apps.sales.signals
        except ImportError:
            pass
