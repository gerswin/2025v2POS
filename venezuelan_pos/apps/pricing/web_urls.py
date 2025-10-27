"""
URL configuration for pricing web interface.
"""

from django.urls import path
from . import web_views

app_name = 'pricing'

urlpatterns = [
    # Dashboard
    path('', web_views.pricing_dashboard, name='dashboard'),
    
    # Price Stages
    path('events/<uuid:event_id>/stages/', web_views.price_stage_list, name='price_stage_list'),
    path('events/<uuid:event_id>/stages/create/', web_views.price_stage_create, name='price_stage_create'),
    path('stages/<uuid:stage_id>/edit/', web_views.price_stage_edit, name='price_stage_edit'),
    path('stages/<uuid:stage_id>/delete/', web_views.price_stage_delete, name='price_stage_delete'),
    
    # Row Pricing
    path('zones/<uuid:zone_id>/row-pricing/', web_views.row_pricing_list, name='row_pricing_list'),
    path('zones/<uuid:zone_id>/row-pricing/create/', web_views.row_pricing_create, name='row_pricing_create'),
    path('zones/<uuid:zone_id>/row-pricing/bulk-create/', web_views.bulk_row_pricing_create, name='bulk_row_pricing_create'),
    path('row-pricing/<uuid:row_pricing_id>/edit/', web_views.row_pricing_edit, name='row_pricing_edit'),
    path('row-pricing/<uuid:row_pricing_id>/delete/', web_views.row_pricing_delete, name='row_pricing_delete'),
    
    # Price Calculation
    path('calculate/', web_views.price_calculation_interface, name='price_calculation'),
    
    # Price History
    path('history/', web_views.price_history_list, name='price_history'),
    
    # AJAX Endpoints
    path('ajax/zones/', web_views.ajax_get_zones, name='ajax_get_zones'),
    path('ajax/calculate/', web_views.ajax_calculate_price, name='ajax_calculate_price'),
]