"""
URL configuration for payment processing web interface.
"""

from django.urls import path
from . import web_views

app_name = 'payments'

urlpatterns = [
    # Dashboard
    path('', web_views.payment_dashboard, name='dashboard'),
    
    # Payment Methods
    path('methods/', web_views.payment_method_list, name='payment_method_list'),
    path('methods/create/', web_views.payment_method_create, name='payment_method_create'),
    path('methods/<uuid:pk>/edit/', web_views.payment_method_edit, name='payment_method_edit'),
    
    # Payment Plans
    path('plans/', web_views.payment_plan_list, name='payment_plan_list'),
    path('plans/create/<uuid:transaction_id>/', web_views.payment_plan_create, name='payment_plan_create'),
    path('plans/<uuid:pk>/', web_views.payment_plan_detail, name='payment_plan_detail'),
    path('plans/<uuid:pk>/extend-expiry/', web_views.extend_payment_plan_expiry, name='extend_payment_plan_expiry'),
    path('plans/<uuid:pk>/cancel/', web_views.cancel_payment_plan, name='cancel_payment_plan'),

    # Payments
    path('payments/', web_views.payment_list, name='payment_list'),
    path('payments/<uuid:pk>/', web_views.payment_detail, name='payment_detail'),
    path('payments/create/<uuid:transaction_id>/', web_views.create_payment, name='create_payment'),
    path('payments/<uuid:pk>/process/', web_views.process_payment, name='process_payment'),
    
    # Reconciliation
    path('reconciliation/', web_views.reconciliation_list, name='reconciliation_list'),
    path('reconciliation/create/', web_views.reconciliation_create, name='reconciliation_create'),
    path('reconciliation/<uuid:pk>/', web_views.reconciliation_detail, name='reconciliation_detail'),
    
    # Fiscal Audit
    path('fiscal-audit/', web_views.fiscal_audit, name='fiscal_audit'),
    
    # AJAX endpoints
    path('ajax/calculate-fee/', web_views.ajax_calculate_fee, name='ajax_calculate_fee'),
    
    # Actions
    path('cleanup-expired/', web_views.cleanup_expired, name='cleanup_expired'),
]
