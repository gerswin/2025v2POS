from django.urls import path
from . import web_views

app_name = 'customers_web'

urlpatterns = [
    # Dashboard
    path('', web_views.customer_dashboard, name='dashboard'),
    
    # Customer management
    path('customers/', web_views.customer_list, name='customer_list'),
    path('customers/create/', web_views.customer_create, name='customer_create'),
    path('customers/<uuid:pk>/', web_views.customer_detail, name='customer_detail'),
    path('customers/<uuid:pk>/edit/', web_views.customer_edit, name='customer_edit'),
    path('customers/<uuid:pk>/toggle-active/', web_views.customer_toggle_active, name='customer_toggle_active'),
    
    # Customer preferences
    path('customers/<uuid:pk>/preferences/', web_views.customer_preferences, name='customer_preferences'),
    
    # Search and lookup
    path('search/', web_views.customer_search, name='customer_search'),
    path('lookup/', web_views.customer_lookup, name='customer_lookup'),
    
    # AJAX endpoints
    path('ajax/quick-add/', web_views.customer_quick_add, name='customer_quick_add'),
    path('ajax/quick-lookup/', web_views.customer_quick_lookup, name='customer_quick_lookup'),
]