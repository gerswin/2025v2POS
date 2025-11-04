"""
URL configuration for ticket web views.
"""

from django.urls import path
from . import web_views

app_name = 'tickets'

urlpatterns = [
    # Dashboard and main views
    path('', web_views.TicketDashboardView.as_view(), name='dashboard'),
    path('ticket/<uuid:pk>/', web_views.TicketDetailView.as_view(), name='ticket_detail'),
    
    # Validation interface
    path('validate/', web_views.validate_ticket_view, name='validate_ticket'),
    path('validation-dashboard/', web_views.ValidationDashboardView.as_view(), name='validation_dashboard'),
    
    # Template management
    path('templates/', web_views.TicketTemplateListView.as_view(), name='template_list'),
    path('templates/<uuid:pk>/', web_views.TicketTemplateDetailView.as_view(), name='template_detail'),
    path('templates/create/', web_views.TicketTemplateCreateView.as_view(), name='template_create'),
    path('templates/<uuid:pk>/edit/', web_views.TicketTemplateUpdateView.as_view(), name='template_edit'),
    
    # Ticket actions
    path('ticket/<uuid:ticket_id>/regenerate-qr/', web_views.regenerate_qr_code, name='regenerate_qr_code'),
    path('ticket/<uuid:ticket_id>/download-pdf/', web_views.download_ticket_pdf, name='download_pdf'),
    path('ticket/<uuid:ticket_id>/resend/', web_views.resend_ticket, name='resend_ticket'),
    
    # Analytics and reporting
    path('analytics/', web_views.ticket_analytics, name='analytics'),
    
    # AJAX endpoints
    path('ajax/validate/', web_views.ajax_validate_ticket, name='ajax_validate'),
]