"""
URL patterns for sales operations.
Includes both regular sales endpoints and cached operations.
"""

from django.urls import path, include
from . import views

app_name = 'sales'

urlpatterns = [
    # Include cache URLs for high-performance operations
    path('', include('venezuelan_pos.apps.sales.cache_urls')),
    
    # Transaction endpoints
    path(
        'transactions/',
        views.TransactionListCreateAPIView.as_view(),
        name='transaction-list-create'
    ),
    path(
        'transactions/<uuid:id>/',
        views.TransactionDetailAPIView.as_view(),
        name='transaction-detail'
    ),
    path(
        'transactions/fiscal/<str:fiscal_series>/',
        views.get_transaction_by_fiscal_series,
        name='transaction-by-fiscal-series'
    ),
    path(
        'transactions/complete/',
        views.TransactionCompletionAPIView.as_view(),
        name='transaction-complete'
    ),
    
    # Seat selection and reservation endpoints
    path(
        'seats/select/',
        views.SeatSelectionAPIView.as_view(),
        name='seat-selection'
    ),
    path(
        'seats/reserve/',
        views.SeatReservationAPIView.as_view(),
        name='seat-reservation'
    ),
    
    # Reserved tickets
    path(
        'reservations/',
        views.ReservedTicketListAPIView.as_view(),
        name='reserved-tickets'
    ),
    
    # Pricing information
    path(
        'pricing/',
        views.get_pricing_information,
        name='pricing-information'
    ),
]