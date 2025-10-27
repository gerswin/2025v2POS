"""
URL patterns for cached sales operations.
High-performance endpoints for ticket validation and availability checking.
"""

from django.urls import path
from .cache_views import (
    TicketValidationAPIView,
    SeatAvailabilityAPIView,
    ZoneAvailabilityAPIView,
    EventAvailabilityAPIView,
    CacheManagementAPIView,
    bulk_seat_availability,
    cache_stats,
)

app_name = 'sales_cache'

urlpatterns = [
    # Ticket validation
    path(
        'tickets/<str:fiscal_series>/validate/',
        TicketValidationAPIView.as_view(),
        name='ticket-validation'
    ),
    
    # Seat availability
    path(
        'seats/<str:seat_id>/availability/',
        SeatAvailabilityAPIView.as_view(),
        name='seat-availability'
    ),
    path(
        'seats/bulk-availability/',
        bulk_seat_availability,
        name='bulk-seat-availability'
    ),
    
    # Zone availability
    path(
        'zones/<str:zone_id>/availability/',
        ZoneAvailabilityAPIView.as_view(),
        name='zone-availability'
    ),
    
    # Event availability
    path(
        'events/<str:event_id>/availability/',
        EventAvailabilityAPIView.as_view(),
        name='event-availability'
    ),
    
    # Cache management
    path(
        'manage/',
        CacheManagementAPIView.as_view(),
        name='cache-management'
    ),
    path(
        'stats/',
        cache_stats,
        name='cache-stats'
    ),
]