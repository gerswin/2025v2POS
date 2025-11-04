"""
URL configuration for Fiscal Compliance web interface.
"""

from django.urls import path
from . import web_views

app_name = 'fiscal'

urlpatterns = [
    # Dashboard
    path('', web_views.fiscal_dashboard, name='fiscal_dashboard'),
    
    # Fiscal Series
    path('series/', web_views.fiscal_series_list, name='fiscal_series_list'),
    path('series/<uuid:series_id>/', web_views.fiscal_series_detail, name='fiscal_series_detail'),
    path('series/<uuid:series_id>/void/', web_views.void_fiscal_series, name='void_fiscal_series'),
    
    # Fiscal Reports
    path('reports/', web_views.fiscal_reports_list, name='fiscal_reports_list'),
    path('reports/generate/', web_views.generate_fiscal_report, name='generate_fiscal_report'),
    path('reports/<uuid:report_id>/', web_views.fiscal_report_detail, name='fiscal_report_detail'),
    
    # Tax Configurations
    path('taxes/', web_views.tax_configurations_list, name='tax_configurations_list'),
    path('taxes/create/', web_views.tax_configuration_create, name='tax_configuration_create'),
    path('taxes/<uuid:config_id>/', web_views.tax_configuration_detail, name='tax_configuration_detail'),
    path('taxes/<uuid:config_id>/edit/', web_views.tax_configuration_edit, name='tax_configuration_edit'),
    
    # Tax Calculator
    path('calculator/', web_views.tax_calculator, name='tax_calculator'),
    
    # Fiscal Day Management
    path('close-day/', web_views.close_fiscal_day, name='close_fiscal_day'),
    
    # Audit Trail
    path('audit/', web_views.audit_trail, name='audit_trail'),
    
    # API endpoints for AJAX
    path('api/status/', web_views.fiscal_status_api, name='fiscal_status_api'),
]