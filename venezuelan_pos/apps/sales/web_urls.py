"""
Web URL patterns for sales interface.
Provides web-based ticket sales interface for operators.
"""

from django.urls import path
from . import web_views

app_name = 'sales'

urlpatterns = [
    # Sales Dashboard
    path('', web_views.sales_dashboard, name='dashboard'),
    
    # Seat Selection Interface
    path('events/<uuid:event_id>/select-seats/', web_views.seat_selection, name='seat_selection'),
    path('events/<uuid:event_id>/zones/<uuid:zone_id>/seats/', web_views.zone_seat_map, name='zone_seat_map'),
    
    # Shopping Cart and Checkout
    path('cart/', web_views.shopping_cart, name='shopping_cart'),
    path('cart/add/', web_views.add_to_cart, name='add_to_cart'),
    path('cart/remove/', web_views.remove_from_cart, name='remove_from_cart'),
    path('cart/clear/', web_views.clear_cart, name='clear_cart'),
    
    # Seat Reservations (temporary holds)
    path('seats/reserve/', web_views.reserve_seats, name='reserve_seats'),
    path('seats/release/', web_views.release_seats, name='release_seats'),
    
    # Checkout Process
    path('checkout/', web_views.checkout, name='checkout'),
    path('checkout/customer/', web_views.checkout_customer, name='checkout_customer'),
    path('checkout/payment/', web_views.checkout_payment, name='checkout_payment'),
    path('checkout/confirm/', web_views.checkout_confirm, name='checkout_confirm'),
    
    # Transaction Management
    path('transactions/', web_views.transaction_list, name='transaction_list'),
    path('transactions/<uuid:transaction_id>/', web_views.transaction_detail, name='transaction_detail'),
    path('transactions/<uuid:transaction_id>/receipt/', web_views.transaction_receipt, name='transaction_receipt'),
    path('transactions/<uuid:transaction_id>/complete/', web_views.complete_transaction, name='complete_transaction'),
    
    # Reservations Management
    path('reservations/', web_views.reservation_list, name='reservation_list'),
    path('reservations/<uuid:reservation_id>/extend/', web_views.extend_reservation, name='extend_reservation'),
    path('reservations/<uuid:reservation_id>/cancel/', web_views.cancel_reservation, name='cancel_reservation'),
    
    # AJAX endpoints for real-time updates
    path('ajax/seat-availability/', web_views.ajax_seat_availability, name='ajax_seat_availability'),
    path('ajax/zone-availability/', web_views.ajax_zone_availability, name='ajax_zone_availability'),
    path('ajax/pricing-info/', web_views.ajax_pricing_info, name='ajax_pricing_info'),
    path('ajax/cart-update/', web_views.ajax_cart_update, name='ajax_cart_update'),
]