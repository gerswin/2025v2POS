"""
Core app configuration for database optimizations and utilities.
"""

from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'venezuelan_pos.core'
    verbose_name = 'Core Utilities'
    
    def ready(self):
        """Initialize core utilities when Django starts."""
        # Import signal handlers and optimizations
        pass