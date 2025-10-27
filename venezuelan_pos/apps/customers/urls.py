from django.urls import path
from . import views

app_name = 'customers'

urlpatterns = [
    # Customer CRUD endpoints
    path('', views.CustomerListCreateView.as_view(), name='customer-list-create'),
    path('<uuid:pk>/', views.CustomerDetailView.as_view(), name='customer-detail'),
    
    # Customer preferences
    path('<uuid:customer_id>/preferences/', 
         views.CustomerPreferencesView.as_view(), 
         name='customer-preferences'),
    
    # Search and lookup endpoints
    path('search/', views.customer_search, name='customer-search'),
    path('lookup/', views.customer_lookup, name='customer-lookup'),
    path('quick-lookup/', views.customer_quick_lookup, name='customer-quick-lookup'),
    
    # Sales integration endpoints
    path('validate/', views.validate_customer_data, name='customer-validate'),
    path('find-or-create/', views.find_or_create_customer, name='customer-find-or-create'),
    path('<uuid:pk>/purchase-history/', views.customer_purchase_history, name='customer-purchase-history'),
    path('<uuid:pk>/sales-summary/', views.customer_sales_summary, name='customer-sales-summary'),
    
    # Statistics
    path('statistics/', views.customer_statistics, name='customer-statistics'),
]