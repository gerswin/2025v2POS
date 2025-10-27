from django.urls import path
from . import web_views

app_name = 'events'

urlpatterns = [
    # Dashboard
    path('', web_views.dashboard, name='dashboard'),
    
    # Venues
    path('venues/', web_views.venue_list, name='venue_list'),
    path('venues/create/', web_views.venue_create, name='venue_create'),
    path('venues/<uuid:venue_id>/', web_views.venue_detail, name='venue_detail'),
    path('venues/<uuid:venue_id>/edit/', web_views.venue_edit, name='venue_edit'),
    path('venues/<uuid:venue_id>/delete/', web_views.venue_delete, name='venue_delete'),
    
    # Events
    path('events/', web_views.event_list, name='event_list'),
    path('events/create/', web_views.event_create, name='event_create'),
    path('events/<uuid:event_id>/', web_views.event_detail, name='event_detail'),
    path('events/<uuid:event_id>/edit/', web_views.event_edit, name='event_edit'),
    path('events/<uuid:event_id>/delete/', web_views.event_delete, name='event_delete'),
    
    # Event Actions
    path('events/<uuid:event_id>/activate/', web_views.event_activate, name='event_activate'),
    path('events/<uuid:event_id>/deactivate/', web_views.event_deactivate, name='event_deactivate'),
    path('events/<uuid:event_id>/cancel/', web_views.event_cancel, name='event_cancel'),
    
    # Zone Management
    path('events/<uuid:event_id>/zones/', web_views.zone_list, name='zone_list'),
    path('zones/<uuid:zone_id>/seats/', web_views.seat_management, name='seat_management'),
]