from django.apps import AppConfig


class ReportsConfig(AppConfig):
    """Configuration for the reports app."""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'venezuelan_pos.apps.reports'
    verbose_name = 'Reports and Analytics'
    
    def ready(self):
        """Import signals when app is ready."""
        # Import any signals here if needed in the future
        pass