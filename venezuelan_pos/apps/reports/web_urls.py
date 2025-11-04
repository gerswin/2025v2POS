from django.urls import path
from . import web_views

app_name = 'reports'

urlpatterns = [
    # Dashboard
    path('', web_views.dashboard, name='dashboard'),
    path('analytics/', web_views.analytics_dashboard, name='analytics_dashboard'),
    
    # Sales Reports
    path('sales-reports/', web_views.sales_reports_list, name='sales_reports_list'),
    path('sales-reports/create/', web_views.sales_report_create, name='sales_report_create'),
    path('sales-reports/<uuid:report_id>/', web_views.sales_report_detail, name='sales_report_detail'),
    
    # Occupancy Analysis
    path('occupancy-analysis/', web_views.occupancy_analysis_list, name='occupancy_analysis_list'),
    path('occupancy-analysis/create/', web_views.occupancy_analysis_create, name='occupancy_analysis_create'),
    path('occupancy-analysis/<uuid:analysis_id>/', web_views.occupancy_analysis_detail, name='occupancy_analysis_detail'),
    
    # Heat Maps
    path('heat-maps/', web_views.heat_map_generator, name='heat_map_generator'),
    
    # Custom Report Builder
    path('custom-reports/', web_views.custom_report_builder, name='custom_report_builder'),
    
    # Report Schedules
    path('schedules/', web_views.report_schedules_list, name='report_schedules_list'),
    path('schedules/create/', web_views.report_schedule_create, name='report_schedule_create'),
    path('schedules/<uuid:schedule_id>/', web_views.report_schedule_detail, name='report_schedule_detail'),
    path('schedules/<uuid:schedule_id>/edit/', web_views.report_schedule_edit, name='report_schedule_edit'),
    path('schedules/<uuid:schedule_id>/execute/', web_views.report_schedule_execute, name='report_schedule_execute'),
    path('schedules/<uuid:schedule_id>/toggle-status/', web_views.report_schedule_toggle_status, name='report_schedule_toggle_status'),
    
    # AJAX endpoints
    path('ajax/zone-performance/', web_views.ajax_zone_performance, name='ajax_zone_performance'),
    path('ajax/heat-map-data/', web_views.ajax_heat_map_data, name='ajax_heat_map_data'),
    path('ajax/sales-trends/', web_views.ajax_sales_trends, name='ajax_sales_trends'),
    path('ajax/real-time-metrics/', web_views.ajax_real_time_metrics, name='ajax_real_time_metrics'),
]