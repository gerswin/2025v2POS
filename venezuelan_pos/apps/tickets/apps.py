from django.apps import AppConfig


class TicketsConfig(AppConfig):
    """Configuration for the tickets app."""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'venezuelan_pos.apps.tickets'
    verbose_name = 'Digital Tickets'
    
    def ready(self):
        """Import signals when app is ready."""
        import venezuelan_pos.apps.tickets.signals