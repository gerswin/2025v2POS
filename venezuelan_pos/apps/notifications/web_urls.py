"""
Web URL configuration for notifications.
"""

from django.urls import path
from . import web_views

app_name = 'notifications'

urlpatterns = [
    # Dashboard
    path('', web_views.notification_dashboard, name='dashboard'),
    
    # Templates
    path('templates/', web_views.template_list, name='template_list'),
    path('templates/create/', web_views.template_create, name='template_create'),
    path('templates/<uuid:template_id>/', web_views.template_detail, name='template_detail'),
    path('templates/<uuid:template_id>/edit/', web_views.template_edit, name='template_edit'),
    path('templates/<uuid:template_id>/test/', web_views.template_test, name='template_test'),
    
    # Logs
    path('logs/', web_views.log_list, name='log_list'),
    path('logs/<uuid:log_id>/', web_views.log_detail, name='log_detail'),
    path('logs/<uuid:log_id>/retry/', web_views.log_retry, name='log_retry'),
    
    # Send notifications
    path('send/', web_views.send_notification, name='send'),
    
    # Preferences
    path('preferences/', web_views.preference_list, name='preference_list'),
    path('preferences/<uuid:preference_id>/edit/', web_views.preference_edit, name='preference_edit'),
    
    # Analytics
    path('analytics/', web_views.analytics, name='analytics'),
]