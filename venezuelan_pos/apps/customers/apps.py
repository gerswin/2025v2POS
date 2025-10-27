from django.apps import AppConfig


class CustomersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'venezuelan_pos.apps.customers'
    verbose_name = 'Customer Management'