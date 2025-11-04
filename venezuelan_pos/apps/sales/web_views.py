"""
Web views for sales interface.
Provides interactive ticket sales interface with real-time seat selection and shopping cart.
"""

import json
import logging
from decimal import Decimal, InvalidOperation
from datetime import datetime, timedelta
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count, Sum
from django.utils import timezone
from django.utils.translation import gettext as _
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods, require_POST
from django.views.decorators.csrf import csrf_exempt
from django.core.cache import cache
from django.db import transaction

from .models import Transaction, TransactionItem, ReservedTicket
from .serializers import TransactionCreateSerializer, SeatReservationSerializer
from .cache import sales_cache
from ..events.models import Event, EventConfiguration
from ..zones.models import Zone, Seat
from ..customers.models import Customer
from ..pricing.services import PricingCalculationService
from ..pricing.sales_integration import stage_pricing_integration
from venezuelan_pos.apps.payments.models import PaymentMethod, PaymentPlan
from venezuelan_pos.apps.payments.services import PaymentPlanService

logger = logging.getLogger(__name__)


def serialize_pricing_details(pricing_details: dict) -> dict:
    """
    Convert Decimal values to strings for JSON serialization.
    Recursively handles nested dictionaries and lists.
    """
    if not pricing_details:
        return {}
    
    serializable_details = {}
    for key, value in pricing_details.items():
        if isinstance(value, Decimal):
            serializable_details[key] = str(value)
        elif isinstance(value, dict):
            # Recursively handle nested dictionaries
            serializable_details[key] = serialize_pricing_details(value)
        elif isinstance(value, list):
            # Handle lists that might contain Decimals or nested structures
            serializable_list = []
            for item in value:
                if isinstance(item, Decimal):
                    serializable_list.append(str(item))
                elif isinstance(item, dict):
                    serializable_list.append(serialize_pricing_details(item))
                else:
                    serializable_list.append(item)
            serializable_details[key] = serializable_list
        elif hasattr(value, '__dict__'):
            # Handle objects that might have Decimal attributes
            serializable_details[key] = str(value)
        else:
            serializable_details[key] = value
    
    return serializable_details


def clean_cart_data(cart: dict) -> dict:
    """
    Clean cart data to ensure no Decimal values that could cause JSON serialization errors.
    """
    if not cart:
        return {}
    
    cleaned_cart = {}
    for key, item in cart.items():
        if isinstance(item, dict):
            cleaned_item = {}
            for item_key, item_value in item.items():
                if isinstance(item_value, Decimal):
                    cleaned_item[item_key] = str(item_value)
                elif isinstance(item_value, dict):
                    cleaned_item[item_key] = serialize_pricing_details(item_value)
                else:
                    cleaned_item[item_key] = item_value
            cleaned_cart[key] = cleaned_item
        else:
            cleaned_cart[key] = item
    
    return cleaned_cart


def get_clean_cart(request):
    """
    Get shopping cart from session and ensure it's clean of Decimal values.
    """
    cart = request.session.get('shopping_cart', {})
    cleaned_cart = clean_cart_data(cart)
    
    # Update session if cart was cleaned
    if cleaned_cart != cart:
        request.session['shopping_cart'] = cleaned_cart
        request.session.modified = True
    
    return cleaned_cart


@login_required
def sales_dashboard(request):
    """Sales dashboard with real-time statistics and transaction monitoring."""
    
    # Filter by tenant
    if request.user.is_admin_user:
        transactions = Transaction.objects.all()
        events = Event.objects.all()
        reservations = ReservedTicket.objects.all()
    else:
        transactions = Transaction.objects.filter(tenant=request.user.tenant)
        events = Event.objects.filter(tenant=request.user.tenant)
        reservations = ReservedTicket.objects.filter(tenant=request.user.tenant)
    
    # Today's statistics
    today = timezone.now().date()
    today_start = timezone.make_aware(datetime.combine(today, datetime.min.time()))
    today_end = timezone.make_aware(datetime.combine(today, datetime.max.time()))
    
    today_transactions = transactions.filter(created_at__range=[today_start, today_end])
    
    today_revenue = today_transactions.filter(
        status=Transaction.Status.COMPLETED
    ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
    
    stats = {
        'today_sales': today_transactions.filter(status=Transaction.Status.COMPLETED).count(),
        'today_revenue': str(today_revenue),
        'pending_transactions': transactions.filter(status=Transaction.Status.PENDING).count(),
        'active_reservations': reservations.filter(
            status=ReservedTicket.Status.ACTIVE,
            reserved_until__gt=timezone.now()
        ).count(),
        'active_events': events.filter(status=Event.Status.ACTIVE).count(),
    }
    
    # Recent transactions
    recent_transactions = transactions.select_related(
        'event', 'customer'
    ).order_by('-created_at')[:10]
    
    # Active events for quick access
    active_events = events.filter(
        status=Event.Status.ACTIVE,
        start_date__gt=timezone.now()
    ).select_related('venue').order_by('start_date')[:5]
    
    # Expiring reservations
    expiring_reservations = reservations.filter(
        status=ReservedTicket.Status.ACTIVE,
        reserved_until__lt=timezone.now() + timedelta(hours=1)
    ).select_related('transaction__customer', 'zone').order_by('reserved_until')[:5]
    
    context = {
        'stats': stats,
        'recent_transactions': recent_transactions,
        'active_events': active_events,
        'expiring_reservations': expiring_reservations,
        'today': today,
    }
    
    return render(request, 'sales/dashboard.html', context)


@login_required
def seat_selection(request, event_id):
    """Interactive seat selection interface for an event."""
    
    if request.user.is_admin_user:
        event = get_object_or_404(Event.objects.select_related('venue'), id=event_id)
    else:
        event = get_object_or_404(
            Event.objects.select_related('venue'), 
            id=event_id, 
            tenant=request.user.tenant
        )
    
    if not event.is_sales_active:
        messages.error(request, 'Las ventas para este evento no están activas.')
        return redirect('sales_web:dashboard')
    
    # Get zones with availability information
    zones = event.zones.filter(status=Zone.Status.ACTIVE).order_by('display_order', 'name')
    
    # Add availability information and stage pricing to zones
    for zone in zones:
        if zone.zone_type == Zone.ZoneType.NUMBERED:
            zone.available_seats = zone.seats.filter(status=Seat.Status.AVAILABLE).count()
            zone.total_seats = zone.seats.count()
        else:
            # For general zones, calculate based on sold tickets
            zone.available_seats = zone.available_capacity
            zone.total_seats = zone.capacity
        
        zone.occupancy_percentage = (
            (zone.total_seats - zone.available_seats) / zone.total_seats * 100
            if zone.total_seats > 0 else 0
        )
        
        # Add current stage information
        stage_info = stage_pricing_integration.get_current_stage_pricing(event, zone)
        if stage_info.get('has_active_stage'):
            zone.current_stage = stage_info.get('stage')
            zone.stage_status = stage_info.get('status')
        else:
            zone.current_stage = None
            zone.stage_status = None
    
    # Get current cart from session
    cart = request.session.get('shopping_cart', {})
    cart_items = []
    cart_total = Decimal('0.00')
    
    for item_key, item_data in cart.items():
        cart_total += Decimal(str(item_data.get('total_price', '0.00')))
        cart_items.append(item_data)
    
    context = {
        'event': event,
        'zones': zones,
        'cart_items': cart_items,
        'cart_total': str(cart_total),
        'cart_count': len(cart_items),
    }

    # Render response and add headers to disable back/forward cache
    response = render(request, 'sales/seat_selection.html', context)
    response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'

    return response


@login_required
def zone_seat_map(request, event_id, zone_id):
    """Detailed seat map for a specific zone - OPTIMIZED VERSION."""
    import time
    start_time = time.time()
    
    if request.user.is_admin_user:
        event = get_object_or_404(Event, id=event_id)
        zone = get_object_or_404(Zone, id=zone_id, event=event)
    else:
        event = get_object_or_404(Event, id=event_id, tenant=request.user.tenant)
        zone = get_object_or_404(Zone, id=zone_id, event=event, tenant=request.user.tenant)
    
    if zone.zone_type == Zone.ZoneType.NUMBERED:
        # Initialize pricing service once
        pricing_service = PricingCalculationService()
        
        # Calculate zone price once (this is the same for all seats in the zone)
        zone_price, pricing_details = pricing_service.calculate_zone_price(zone)
        
        # Get shopping cart items once and ensure they're clean
        shopping_cart = get_clean_cart(request)
        
        # Get all seats with optimized query
        seats = zone.seats.select_related('zone').order_by('row_number', 'seat_number')
        
        # Get zone availability data from cache (includes all seats)
        zone_availability = sales_cache.get_zone_seat_availability(str(zone_id))
        cached_seats = zone_availability.get('seats', {}) if zone_availability else {}
        
        # Organize seats by row with optimized processing
        seats_by_row = {}
        for seat in seats:
            if seat.row_number not in seats_by_row:
                seats_by_row[seat.row_number] = []
            
            # Use cached status if available, otherwise use database status
            seat_key = f"{seat.row_number}_{seat.seat_number}"
            cached_seat_data = cached_seats.get(seat_key, {})
            seat.cached_status = cached_seat_data.get('status', seat.status)
            seat.is_in_cart = str(seat.id) in shopping_cart
            
            # Use zone price for all seats (optimization: avoid per-seat calculation)
            # In most cases, seats in the same zone have the same base price
            seat.dynamic_price = str(zone_price)
            
            seats_by_row[seat.row_number].append(seat)
        
        context = {
            'event': event,
            'zone': zone,
            'seats_by_row': seats_by_row,
            'zone_price': str(zone_price),
            'pricing_details': serialize_pricing_details(pricing_details),
        }
        
        # Log performance metrics
        end_time = time.time()
        processing_time = end_time - start_time
        logger.info(f"zone_seat_map optimized processing time: {processing_time:.3f}s for zone {zone_id} with {len(seats)} seats")
        
        return render(request, 'sales/zone_seat_map.html', context)
    
    else:
        # General admission zone
        pricing_service = PricingCalculationService()
        zone_price, pricing_details = pricing_service.calculate_zone_price(zone)
        
        # Calculate sold tickets
        sold_count = zone.capacity - zone.available_capacity
        
        # Determine current quantity reserved in the cart for this zone
        cart = get_clean_cart(request)
        cart_item_key = f"general_{zone.id}"
        cart_quantity = 0
        if cart_item_key in cart:
            try:
                cart_quantity = int(cart[cart_item_key].get('quantity', 0))
            except (TypeError, ValueError):
                cart_quantity = 0
        
        effective_available_capacity = max(zone.available_capacity - cart_quantity, 0)
        occupancy_percentage = (
            (sold_count / zone.capacity * 100) if zone.capacity else 0
        )
        zone.occupancy_percentage = occupancy_percentage
        
        context = {
            'event': event,
            'zone': zone,
            'zone_price': str(zone_price),
            'pricing_details': serialize_pricing_details(pricing_details),
            'available_capacity': zone.available_capacity,
            'effective_available_capacity': effective_available_capacity,
            'cart_quantity': cart_quantity,
            'occupancy_percentage': occupancy_percentage,
            'sold_count': sold_count,
        }
        
        return render(request, 'sales/general_admission.html', context)


@login_required
def shopping_cart(request):
    """Shopping cart management interface."""
    
    # Get cart and ensure it's clean of Decimal values
    cart = get_clean_cart(request)
    cart_items = []
    cart_total = Decimal('0.00')
    
    # Process cart items and add detailed information
    for item_key, item_data in cart.items():
        try:
            if item_data.get('seat_id'):
                seat = Seat.objects.select_related('zone', 'zone__event').get(
                    id=item_data['seat_id']
                )
                item_data['seat'] = seat
                item_data['zone'] = seat.zone
                item_data['event'] = seat.zone.event
            elif item_data.get('zone_id'):
                zone = Zone.objects.select_related('event').get(
                    id=item_data['zone_id']
                )
                item_data['zone'] = zone
                item_data['event'] = zone.event
            
            cart_total += Decimal(str(item_data.get('total_price', '0.00')))
            cart_items.append(item_data)
            
        except (Seat.DoesNotExist, Zone.DoesNotExist):
            # Remove invalid items from cart
            continue
    
    # Update session with cleaned cart
    cleaned_cart = {
        item['item_key']: item for item in cart_items
    }
    request.session['shopping_cart'] = cleaned_cart
    
    context = {
        'cart_items': cart_items,
        'cart_total': str(cart_total),
        'cart_count': len(cart_items),
    }
    
    return render(request, 'sales/shopping_cart.html', context)


@login_required
@require_POST
def add_to_cart(request):
    """Add items to shopping cart via AJAX."""
    
    try:
        data = json.loads(request.body)
        zone_id = data.get('zone_id')
        seat_ids = data.get('seat_ids', [])
        quantity = int(data.get('quantity', 1))
        
        if not zone_id:
            return JsonResponse({'error': 'Zone ID is required'}, status=400)
        
        # Get zone and validate
        if request.user.is_admin_user:
            zone = get_object_or_404(Zone, id=zone_id)
        else:
            zone = get_object_or_404(Zone, id=zone_id, tenant=request.user.tenant)
        
        cart = request.session.get('shopping_cart', {})
        pricing_service = PricingCalculationService()
        
        # OPTIMIZATION: Lock items before adding to cart
        from .cart_lock_service import CartLockService
        
        # Prepare items for locking
        items_to_lock = []
        
        if zone.zone_type == Zone.ZoneType.NUMBERED and seat_ids:
            for seat_id in seat_ids:
                items_to_lock.append({
                    'zone_id': str(zone.id),
                    'seat_id': str(seat_id),
                    'quantity': 1
                })
        elif zone.zone_type == Zone.ZoneType.GENERAL:
            items_to_lock.append({
                'zone_id': str(zone.id),
                'quantity': quantity
            })
        
        # Lock items first
        session_key = request.session.session_key
        if not session_key:
            request.session.create()
            session_key = request.session.session_key
        
        lock_success, created_locks, lock_errors = CartLockService.lock_items(
            session_key=session_key,
            user=request.user,
            items_data=items_to_lock
        )
        
        if not lock_success:
            return JsonResponse({
                'success': False,
                'error': 'Failed to lock items',
                'details': lock_errors
            }, status=409)
        
        if zone.zone_type == Zone.ZoneType.NUMBERED and seat_ids:
            # Add numbered seats
            for seat_id in seat_ids:
                seat = get_object_or_404(Seat, id=seat_id, zone=zone)
                
                # Check availability
                if not seat.is_available:
                    return JsonResponse({
                        'error': f'Seat {seat.seat_label} is not available'
                    }, status=409)
                
                # Calculate pricing
                seat_price, pricing_details = pricing_service.calculate_seat_price(seat)
                
                item_key = f"seat_{seat.id}"
                cart[item_key] = {
                    'item_key': item_key,
                    'type': 'numbered_seat',
                    'zone_id': str(zone.id),
                    'zone_name': zone.name,
                    'seat_id': str(seat.id),
                    'seat_label': seat.seat_label,
                    'quantity': 1,
                    'unit_price': str(seat_price),
                    'total_price': str(seat_price),
                    'pricing_details': serialize_pricing_details(pricing_details),
                    'added_at': timezone.now().isoformat(),
                }
        
        elif zone.zone_type == Zone.ZoneType.GENERAL:
            # Add general admission tickets
            if quantity > zone.available_capacity:
                return JsonResponse({
                    'error': f'Only {zone.available_capacity} tickets available'
                }, status=409)
            
            # Calculate pricing
            zone_price, pricing_details = pricing_service.calculate_zone_price(zone)
            total_price = zone_price * quantity
            
            item_key = f"general_{zone.id}"
            if item_key in cart:
                # Update existing item
                existing_qty = cart[item_key]['quantity']
                new_qty = existing_qty + quantity
                
                if new_qty > zone.available_capacity:
                    return JsonResponse({
                        'error': f'Cannot add {quantity} more tickets. Only {zone.available_capacity - existing_qty} available'
                    }, status=409)
                
                cart[item_key]['quantity'] = new_qty
                cart[item_key]['total_price'] = str(zone_price * new_qty)
            else:
                cart[item_key] = {
                    'item_key': item_key,
                    'type': 'general_admission',
                    'zone_id': str(zone.id),
                    'zone_name': zone.name,
                    'quantity': quantity,
                    'unit_price': str(zone_price),
                    'total_price': str(total_price),
                    'pricing_details': serialize_pricing_details(pricing_details),
                    'added_at': timezone.now().isoformat(),
                }
        
        # Save updated cart
        request.session['shopping_cart'] = cart
        request.session.modified = True
        
        # Calculate cart totals
        cart_total = sum(Decimal(str(item['total_price'])) for item in cart.values())
        cart_count = len(cart)
        
        return JsonResponse({
            'success': True,
            'message': 'Items added to cart successfully',
            'cart_total': str(cart_total),
            'cart_count': cart_count,
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_POST
def remove_from_cart(request):
    """Remove items from shopping cart via AJAX."""
    
    try:
        data = json.loads(request.body)
        item_key = data.get('item_key')
        
        if not item_key:
            return JsonResponse({'error': 'Item key is required'}, status=400)
        
        cart = request.session.get('shopping_cart', {})
        
        if item_key in cart:
            del cart[item_key]
            request.session['shopping_cart'] = cart
            request.session.modified = True
        
        # Calculate cart totals
        cart_total = sum(Decimal(str(item['total_price'])) for item in cart.values())
        cart_count = len(cart)
        
        return JsonResponse({
            'success': True,
            'message': 'Item removed from cart',
            'cart_total': str(cart_total),
            'cart_count': cart_count,
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_POST
def clear_cart(request):
    """Clear all items from shopping cart."""
    
    request.session['shopping_cart'] = {}
    request.session.modified = True
    
    return JsonResponse({
        'success': True,
        'message': 'Cart cleared successfully',
        'cart_total': '0.00',
        'cart_count': 0,
    })


@login_required
def transaction_status(request, transaction_id):
    """Check transaction processing status via AJAX."""
    
    try:
        if request.user.is_admin_user:
            transaction_obj = get_object_or_404(Transaction, id=transaction_id)
        else:
            transaction_obj = get_object_or_404(
                Transaction, 
                id=transaction_id, 
                tenant=request.user.tenant
            )
        
        # Check processing status
        is_processing_complete = transaction_obj.processing_completed_at is not None
        
        response_data = {
            'success': True,
            'transaction_id': str(transaction_obj.id),
            'fiscal_series': transaction_obj.fiscal_series,
            'status': transaction_obj.status,
            'processing_complete': is_processing_complete,
            'completed_at': transaction_obj.completed_at.isoformat() if transaction_obj.completed_at else None,
            'processing_completed_at': transaction_obj.processing_completed_at.isoformat() if transaction_obj.processing_completed_at else None,
        }
        
        return JsonResponse(response_data)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=404)


@require_POST
@login_required
def reserve_seats(request):
    """
    Create temporary reservations for selected seats to prevent conflicts.
    Reservations expire after 10 minutes if not completed.
    """
    try:
        data = json.loads(request.body)
        seat_ids = data.get('seat_ids', [])
        zone_id = data.get('zone_id')
        
        if not seat_ids and not zone_id:
            return JsonResponse({'success': False, 'error': 'No seats or zone specified'})
        
        # Get or create a temporary transaction for reservations
        session_key = request.session.session_key
        if not session_key:
            request.session.create()
            session_key = request.session.session_key
        
        # Create temporary transaction for this session if it doesn't exist
        temp_transaction, created = Transaction.objects.get_or_create(
            tenant=request.user.tenant,
            fiscal_series=f"TEMP_{session_key}",
            defaults={
                'status': Transaction.Status.PENDING,
                'total_price': Decimal('0.00'),
                'payment_method': Transaction.PaymentMethod.CASH,
                'notes': 'Temporary transaction for seat reservations'
            }
        )
        
        reserved_seats = []
        reservation_time = timezone.now() + timezone.timedelta(minutes=10)  # 10 minute hold
        
        if seat_ids:
            # Reserve specific seats (numbered zones)
            for seat_id in seat_ids:
                try:
                    seat = Seat.objects.select_for_update().get(
                        id=seat_id,
                        status=Seat.Status.AVAILABLE
                    )
                    
                    # Check if seat is already reserved by someone else
                    existing_reservation = ReservedTicket.objects.filter(
                        seat=seat,
                        status=ReservedTicket.Status.ACTIVE,
                        reserved_until__gt=timezone.now()
                    ).exclude(transaction=temp_transaction).first()
                    
                    if existing_reservation:
                        return JsonResponse({
                            'success': False, 
                            'error': f'Seat {seat.seat_label} is already reserved by another operator'
                        })
                    
                    # Create or update reservation
                    reservation, created = ReservedTicket.objects.update_or_create(
                        transaction=temp_transaction,
                        seat=seat,
                        zone=seat.zone,
                        defaults={
                            'reserved_until': reservation_time,
                            'status': ReservedTicket.Status.ACTIVE,
                            'quantity': 1
                        }
                    )
                    
                    reserved_seats.append({
                        'seat_id': str(seat.id),
                        'seat_label': seat.seat_label,
                        'reserved_until': reservation_time.isoformat()
                    })
                    
                except Seat.DoesNotExist:
                    return JsonResponse({
                        'success': False, 
                        'error': f'Seat {seat_id} not found or not available'
                    })
        
        elif zone_id:
            # Reserve general admission tickets
            try:
                zone = Zone.objects.get(id=zone_id)
                quantity = data.get('quantity', 1)
                
                # Check zone availability
                if zone.available_capacity < quantity:
                    return JsonResponse({
                        'success': False, 
                        'error': f'Only {zone.available_capacity} tickets available in {zone.name}'
                    })
                
                # Create or update reservation
                reservation, created = ReservedTicket.objects.update_or_create(
                    transaction=temp_transaction,
                    zone=zone,
                    seat=None,  # General admission
                    defaults={
                        'reserved_until': reservation_time,
                        'status': ReservedTicket.Status.ACTIVE,
                        'quantity': quantity
                    }
                )
                
                reserved_seats.append({
                    'zone_id': str(zone.id),
                    'zone_name': zone.name,
                    'quantity': quantity,
                    'reserved_until': reservation_time.isoformat()
                })
                
            except Zone.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Zone not found'})
        
        # Update cache to reflect reservations
        for seat_info in reserved_seats:
            if 'seat_id' in seat_info:
                sales_cache.invalidate_seat_availability(seat_info['seat_id'])
            else:
                sales_cache.invalidate_zone_availability(zone_id)
        
        return JsonResponse({
            'success': True,
            'reserved_seats': reserved_seats,
            'expires_at': reservation_time.isoformat(),
            'message': f'Reserved {len(reserved_seats)} seat(s) for 10 minutes'
        })
        
    except Exception as e:
        logger.error(f"Error reserving seats: {e}")
        return JsonResponse({'success': False, 'error': 'Failed to reserve seats'})


@require_POST
@login_required
def release_seats(request):
    """Release temporary seat reservations."""
    try:
        data = json.loads(request.body)
        seat_ids = data.get('seat_ids', [])
        zone_id = data.get('zone_id')
        
        session_key = request.session.session_key
        if not session_key:
            return JsonResponse({'success': True, 'message': 'No reservations to release'})
        
        # Find temporary transaction for this session
        try:
            temp_transaction = Transaction.objects.get(
                tenant=request.user.tenant,
                fiscal_series=f"TEMP_{session_key}"
            )
        except Transaction.DoesNotExist:
            return JsonResponse({'success': True, 'message': 'No reservations found'})
        
        released_count = 0
        
        if seat_ids:
            # Release specific seats
            for seat_id in seat_ids:
                released = ReservedTicket.objects.filter(
                    transaction=temp_transaction,
                    seat_id=seat_id,
                    status=ReservedTicket.Status.ACTIVE
                ).update(status=ReservedTicket.Status.CANCELLED)
                released_count += released
                
                # Update cache
                sales_cache.invalidate_seat_availability(seat_id)
        
        elif zone_id:
            # Release zone reservations
            released = ReservedTicket.objects.filter(
                transaction=temp_transaction,
                zone_id=zone_id,
                status=ReservedTicket.Status.ACTIVE
            ).update(status=ReservedTicket.Status.CANCELLED)
            released_count += released
            
            # Update cache
            sales_cache.invalidate_zone_availability(zone_id)
        
        else:
            # Release all reservations for this session
            released = ReservedTicket.objects.filter(
                transaction=temp_transaction,
                status=ReservedTicket.Status.ACTIVE
            ).update(status=ReservedTicket.Status.CANCELLED)
            released_count += released
        
        return JsonResponse({
            'success': True,
            'released_count': released_count,
            'message': f'Released {released_count} reservation(s)'
        })
        
    except Exception as e:
        logger.error(f"Error releasing seats: {e}")
        return JsonResponse({'success': False, 'error': 'Failed to release seats'})


@login_required
def checkout(request):
    """Checkout process step 1 - Review cart and select customer."""
    
    cart = request.session.get('shopping_cart', {})
    
    if not cart:
        messages.error(request, 'Your cart is empty.')
        return redirect('sales_web:dashboard')
    
    # Process cart items
    cart_items = []
    cart_total = Decimal('0.00')
    event = None
    
    for item_key, item_data in cart.items():
        try:
            if item_data.get('seat_id'):
                seat = Seat.objects.select_related('zone', 'zone__event').get(
                    id=item_data['seat_id']
                )
                item_data['seat'] = seat
                item_data['zone'] = seat.zone
                item_data['event'] = seat.zone.event
                event = seat.zone.event
            elif item_data.get('zone_id'):
                zone = Zone.objects.select_related('event').get(
                    id=item_data['zone_id']
                )
                item_data['zone'] = zone
                item_data['event'] = zone.event
                event = zone.event
            
            cart_total += Decimal(str(item_data.get('total_price', '0.00')))
            cart_items.append(item_data)
            
        except (Seat.DoesNotExist, Zone.DoesNotExist):
            continue
    
    # Get recent customers for quick selection
    if request.user.is_admin_user:
        recent_customers = Customer.objects.all()
    else:
        recent_customers = Customer.objects.filter(tenant=request.user.tenant)
    
    recent_customers = recent_customers.order_by('-updated_at')[:10]
    
    context = {
        'cart_items': cart_items,
        'cart_total': str(cart_total),
        'cart_count': len(cart_items),
        'event': event,
        'recent_customers': recent_customers,
    }
    
    return render(request, 'sales/checkout.html', context)


@login_required
def checkout_customer(request):
    """Checkout step 2 - Customer information."""
    
    cart = request.session.get('shopping_cart', {})
    if not cart:
        messages.error(request, 'Your cart is empty.')
        return redirect('sales_web:dashboard')
    
    if request.method == 'POST':
        # Handle customer selection or creation
        customer_id = request.POST.get('customer_id')
        
        if customer_id:
            # Existing customer selected
            if request.user.is_admin_user:
                customer = get_object_or_404(Customer, id=customer_id)
            else:
                customer = get_object_or_404(Customer, id=customer_id, tenant=request.user.tenant)
        else:
            # Create new customer
            customer_data = {
                'name': request.POST.get('name'),
                'surname': request.POST.get('surname'),
                'phone': request.POST.get('phone'),
                'email': request.POST.get('email'),
                'identification': request.POST.get('identification'),
            }
            
            customer = Customer.objects.create(
                tenant=request.user.tenant,
                **customer_data
            )
        
        # Store customer in session
        request.session['checkout_customer_id'] = str(customer.id)
        request.session.modified = True
        
        return redirect('sales_web:checkout_payment')
    
    return render(request, 'sales/checkout_customer.html')


@login_required
def checkout_payment(request):
    """Checkout step 3 - Payment method selection."""
    
    cart = request.session.get('shopping_cart', {})
    customer_id = request.session.get('checkout_customer_id')
    
    if not cart or not customer_id:
        messages.error(request, 'Invalid checkout session.')
        return redirect('sales_web:checkout')

    payment_pref = request.session.get('checkout_payment', {'option': 'full'})
    partial_payment_selected = payment_pref.get('option') == 'partial'
    
    # Get customer
    if request.user.is_admin_user:
        customer = get_object_or_404(Customer, id=customer_id)
    else:
        customer = get_object_or_404(Customer, id=customer_id, tenant=request.user.tenant)
    
    # Calculate subtotal
    cart_subtotal = sum(Decimal(str(item['total_price'])) for item in cart.values())

    # Identify event from cart items
    event = None
    for item_data in cart.values():
        if item_data.get('seat_id'):
            seat = Seat.objects.select_related('zone__event').filter(id=item_data['seat_id']).first()
            if seat:
                event = seat.zone.event
                break
        elif item_data.get('zone_id'):
            zone = Zone.objects.select_related('event').filter(id=item_data['zone_id']).first()
            if zone:
                event = zone.event
                break

    # Calculate taxes using fiscal service
    tax_amount = Decimal('0.00')
    if event:
        from venezuelan_pos.apps.fiscal.services import TaxCalculationService
        try:
            tax_amount, tax_details, tax_breakdown = TaxCalculationService.calculate_taxes(
                base_amount=cart_subtotal,
                tenant=request.user.tenant,
                event=event,
                user=request.user
            )
        except Exception:
            # If tax calculation fails, continue without taxes
            pass

    # Calculate total including taxes
    cart_total = cart_subtotal + tax_amount
    cart_total_display = cart_total.quantize(Decimal('0.01'))

    event_config = EventConfiguration.objects.filter(event=event).first() if event else None

    tenant = event.tenant if event else getattr(request.user, 'tenant', None)
    payment_methods_query = PaymentMethod.objects.filter(
        tenant=tenant,
        is_active=True
    )

    # Filter payment methods based on event configuration
    if event_config:
        enabled_types = []
        if event_config.cash_enabled:
            enabled_types.append('cash')
        if event_config.credit_card_enabled:
            enabled_types.append('credit_card')
        if event_config.debit_card_enabled:
            enabled_types.append('debit_card')
        if event_config.bank_transfer_enabled:
            enabled_types.append('bank_transfer')
        if event_config.mobile_payment_enabled:
            enabled_types.extend(['pago_movil', 'zelle', 'paypal'])

        if enabled_types:
            payment_methods_query = payment_methods_query.filter(method_type__in=enabled_types)
        else:
            # If no payment methods enabled, return empty queryset
            payment_methods_query = PaymentMethod.objects.none()

    payment_methods = payment_methods_query.order_by('sort_order', 'name') if tenant else PaymentMethod.objects.none()
    has_payment_methods = payment_methods.exists()
    partial_payment_methods = payment_methods.filter(allows_partial=True)

    partial_payments_available = bool(
        event_config and event_config.partial_payments_enabled and partial_payment_methods.exists()
    )

    if payment_pref.get('option') == 'partial' and not partial_payments_available:
        payment_pref = {'option': 'full'}
        partial_payment_selected = False

    if not has_payment_methods:
        payment_pref = {'option': 'full'}
        partial_payment_selected = False

    partial_payment_selected = payment_pref.get('option') == 'partial'

    min_down_payment = Decimal('0.00')
    if partial_payments_available and event_config.min_down_payment_percentage:
        min_down_payment = (cart_total * (Decimal(str(event_config.min_down_payment_percentage)) / Decimal('100')))
        min_down_payment = min_down_payment.quantize(Decimal('0.01'))

    payment_pref = request.session.get('checkout_payment', {})

    context = {
        'customer': customer,
        'cart_subtotal': str(cart_subtotal.quantize(Decimal('0.01'))),
        'tax_amount': str(tax_amount.quantize(Decimal('0.01'))),
        'cart_total': str(cart_total_display),
        'cart_total_decimal': str(cart_total_display),
        'cart_count': len(cart),
        'payment_methods': payment_methods,
        'partial_payment_methods': partial_payment_methods,
        'partial_payments_available': partial_payments_available,
        'has_payment_methods': has_payment_methods,
        'event_config': event_config,
        'min_down_payment': min_down_payment,
        'max_installments': getattr(event_config, 'max_installments', None),
        'payment_pref': payment_pref,
    }
    
    return render(request, 'sales/checkout_payment.html', context)


@require_POST
@login_required
def checkout_payment_option(request):
    """Persist payment choice (full vs partial) in the session during checkout."""
    cart = request.session.get('shopping_cart', {})
    if not cart:
        return JsonResponse({'success': False, 'error': 'Cart is empty'}, status=400)

    try:
        payload = json.loads(request.body.decode('utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({'success': False, 'error': 'Invalid payload'}, status=400)

    option = payload.get('option')
    if option not in {'full', 'partial'}:
        return JsonResponse({'success': False, 'error': 'Invalid payment option'}, status=400)

    # Determine event context
    event = None
    for item_data in cart.values():
        if item_data.get('seat_id'):
            seat = Seat.objects.select_related('zone__event').filter(id=item_data['seat_id']).first()
            if seat:
                event = seat.zone.event
                break
        elif item_data.get('zone_id'):
            zone = Zone.objects.select_related('event').filter(id=item_data['zone_id']).first()
            if zone:
                event = zone.event
                break

    event_config = EventConfiguration.objects.filter(event=event).first() if event else None
    tenant = event.tenant if event else getattr(request.user, 'tenant', None)
    if not tenant:
        return JsonResponse({'success': False, 'error': 'Tenant context not available'}, status=400)

    payment_methods = PaymentMethod.objects.filter(
        tenant=tenant,
        is_active=True
    ).order_by('sort_order', 'name')

    stored_data = {'option': option}

    if option == 'full':
        payment_method_id = payload.get('payment_method_id')
        if not payment_method_id:
            return JsonResponse({'success': False, 'error': 'Select a payment method'}, status=400)
        payment_method = payment_methods.filter(id=payment_method_id).first()
        if not payment_method:
            return JsonResponse({'success': False, 'error': 'Payment method not available'}, status=400)
        stored_data['payment_method_id'] = str(payment_method.id)
    else:
        if not (event_config and event_config.partial_payments_enabled):
            return JsonResponse({'success': False, 'error': 'Partial payments are not enabled for this event'}, status=400)

        plan_type = payload.get('plan_type') or PaymentPlan.PlanType.FLEXIBLE
        if plan_type not in dict(PaymentPlan.PlanType.choices):
            return JsonResponse({'success': False, 'error': 'Invalid plan type'}, status=400)

        if plan_type == PaymentPlan.PlanType.INSTALLMENT and not event_config.installment_plans_enabled:
            return JsonResponse({'success': False, 'error': 'Installment plans are not enabled for this event'}, status=400)
        if plan_type == PaymentPlan.PlanType.FLEXIBLE and not event_config.flexible_payments_enabled:
            return JsonResponse({'success': False, 'error': 'Flexible plans are not enabled for this event'}, status=400)

        installment_count = payload.get('installment_count')
        if plan_type == PaymentPlan.PlanType.INSTALLMENT:
            if installment_count is None:
                return JsonResponse({'success': False, 'error': 'Installment count is required'}, status=400)
            try:
                installment_count = int(installment_count)
            except (TypeError, ValueError):
                return JsonResponse({'success': False, 'error': 'Installment count must be numeric'}, status=400)
            max_installments = event_config.max_installments or 1
            if installment_count < 1 or installment_count > max_installments:
                return JsonResponse({'success': False, 'error': f'Installments must be between 1 and {max_installments}'}, status=400)
        else:
            installment_count = None

        # Get initial payment amount from user
        initial_payment_amount = payload.get('initial_payment_amount') or '0'
        try:
            initial_payment_amount = Decimal(str(initial_payment_amount))
        except (TypeError, InvalidOperation):
            return JsonResponse({'success': False, 'error': 'Invalid initial payment amount'}, status=400)
        if initial_payment_amount < 0:
            return JsonResponse({'success': False, 'error': 'Initial payment cannot be negative'}, status=400)

        # Calculate cart total with taxes for validation
        cart_subtotal = sum(Decimal(str(item['total_price'])) for item in cart.values())
        tax_amount = Decimal('0.00')
        if event:
            from venezuelan_pos.apps.fiscal.services import TaxCalculationService
            try:
                tax_amount, tax_details, tax_breakdown = TaxCalculationService.calculate_taxes(
                    base_amount=cart_subtotal,
                    tenant=tenant,
                    event=event,
                    user=request.user
                )
            except Exception:
                pass

        cart_total = cart_subtotal + tax_amount

        # Minimum down payment enforcement for all partial payment plans
        if event_config.min_down_payment_percentage:
            min_required = cart_total * (Decimal(str(event_config.min_down_payment_percentage)) / Decimal('100'))
            min_required = min_required.quantize(Decimal('0.01'))
            if initial_payment_amount < min_required:
                return JsonResponse({
                    'success': False,
                    'error': _('Initial payment must be at least $%(amount)s') % {'amount': f'{min_required:.2f}'}
                }, status=400)

        payment_method_id = payload.get('payment_method_id')
        partial_method_qs = payment_methods.filter(allows_partial=True)
        if payment_method_id:
            payment_method = partial_method_qs.filter(id=payment_method_id).first()
        else:
            payment_method = partial_method_qs.first()
        if not payment_method:
            return JsonResponse({'success': False, 'error': 'No payment method available for partial payments'}, status=400)

        stored_data.update({
            'plan_type': plan_type,
            'installment_count': installment_count,
            'initial_payment_amount': str(initial_payment_amount),
            'payment_method_id': str(payment_method.id),
        })

    request.session['checkout_payment'] = stored_data
    request.session.modified = True

    return JsonResponse({'success': True})
@login_required
def checkout_confirm(request):
    """Checkout step 4 - Confirm and complete transaction - OPTIMIZED VERSION."""
    import time
    import logging

    logger = logging.getLogger(__name__)
    start_time = time.time()

    cart = request.session.get('shopping_cart', {})
    customer_id = request.session.get('checkout_customer_id')
    payment_pref = request.session.get('checkout_payment', {})
    partial_payment_selected = payment_pref.get('option') == 'partial'

    if not cart or not customer_id:
        messages.error(request, 'Invalid checkout session.')
        return redirect('sales_web:checkout')
    
    if request.method == 'POST':
        try:
            # OPTIMIZATION: Batch database queries
            seat_ids = [item['seat_id'] for item in cart.values() if item.get('seat_id')]
            zone_ids = [item['zone_id'] for item in cart.values() if item.get('zone_id')]
            
            # Single query for all seats
            seats_dict = {}
            if seat_ids:
                seats = Seat.objects.select_related('zone', 'zone__event').filter(id__in=seat_ids)
                seats_dict = {str(seat.id): seat for seat in seats}
            
            # Single query for all zones
            zones_dict = {}
            if zone_ids:
                zones = Zone.objects.select_related('event').filter(id__in=zone_ids)
                zones_dict = {str(zone.id): zone for zone in zones}
            
            # Get customer once
            if request.user.is_admin_user:
                customer = get_object_or_404(Customer, id=customer_id)
            else:
                customer = get_object_or_404(Customer, id=customer_id, tenant=request.user.tenant)
            
            # OPTIMIZATION: Shorter atomic transaction - only critical operations
            with transaction.atomic():
                # Prepare transaction data
                event = None
                items_data = []
                
                for item_key, item_data in cart.items():
                    if item_data.get('seat_id'):
                        seat = seats_dict.get(item_data['seat_id'])
                        if not seat:
                            raise ValueError(f"Seat {item_data['seat_id']} not found")
                        
                        zone = seat.zone
                        event = zone.event
                        
                        # Validate seat availability
                        if seat.status != Seat.Status.AVAILABLE:
                            raise ValueError(f"Seat {seat.seat_label} is no longer available")
                        
                        items_data.append({
                            'zone': zone,
                            'seat': seat,
                            'quantity': 1,
                            'unit_price': Decimal(str(item_data['unit_price'])),
                        })
                    elif item_data.get('zone_id'):
                        zone = zones_dict.get(item_data['zone_id'])
                        if not zone:
                            raise ValueError(f"Zone {item_data['zone_id']} not found")
                        
                        event = zone.event
                        
                        # Validate zone availability
                        if zone.available_capacity < item_data['quantity']:
                            raise ValueError(f"Zone {zone.name} doesn't have enough capacity")
                        
                        items_data.append({
                            'zone': zone,
                            'quantity': item_data['quantity'],
                            'unit_price': Decimal(str(item_data['unit_price'])),
                        })
                
                # Create transaction (critical operations only)
                transaction_obj = Transaction.objects.create_transaction_fast(
                    tenant=request.user.tenant,
                    event=event,
                    customer=customer,
                    items_data=items_data,
                    transaction_type=Transaction.TransactionType.ONLINE,
                )

                payment_plan = None
                if partial_payment_selected:
                    payment_method_id = payment_pref.get('payment_method_id')
                    payment_method = PaymentMethod.objects.filter(
                        tenant=transaction_obj.tenant,
                        id=payment_method_id,
                        is_active=True
                    ).first()
                    if not payment_method:
                        raise ValueError('Selected payment method is not available.')

                    plan_type = payment_pref.get('plan_type', PaymentPlan.PlanType.FLEXIBLE)
                    initial_amount = payment_pref.get('initial_payment_amount', '0')
                    try:
                        initial_amount = Decimal(str(initial_amount))
                    except (TypeError, InvalidOperation):
                        raise ValueError('Invalid initial payment amount provided.')
                    if initial_amount <= 0:
                        initial_amount = None

                    if plan_type == PaymentPlan.PlanType.INSTALLMENT:
                        installment_count = payment_pref.get('installment_count')
                        try:
                            installment_count = int(installment_count)
                        except (TypeError, ValueError):
                            raise ValueError('Invalid installment count provided.')

                        payment_plan = PaymentPlanService.create_installment_plan(
                            transaction_obj=transaction_obj,
                            installment_count=installment_count,
                            expires_at=None,
                            notes=payment_pref.get('notes', ''),
                            initial_payment_amount=initial_amount,
                            initial_payment_method=payment_method
                        )
                    else:
                        payment_plan = PaymentPlanService.create_flexible_plan(
                            transaction_obj=transaction_obj,
                            expires_at=None,
                            notes=payment_pref.get('notes', ''),
                            initial_payment_amount=initial_amount,
                            initial_payment_method=payment_method
                        )

                    completed_transaction = transaction_obj  # transaction remains reserved
                else:
                    completed_transaction = Transaction.objects.complete_transaction_fast(transaction_obj)

                    # Update seat statuses immediately (critical for availability)
                    if seat_ids:
                        Seat.objects.filter(id__in=seat_ids).update(status=Seat.Status.SOLD)

                # Invalidate caches to reflect seat availability changes
                from .cache import sales_cache

                for zone_id in zone_ids:
                    zone = zones_dict.get(zone_id)
                    if zone:
                        sales_cache.invalidate_zone_caches(zone)

                if seat_ids:
                    for seat_id in seat_ids:
                        sales_cache.invalidate_seat_availability(seat_id)
            
            # OPTIMIZATION: Clear session immediately after transaction
            request.session['shopping_cart'] = {}
            if 'checkout_customer_id' in request.session:
                del request.session['checkout_customer_id']
            request.session.pop('checkout_payment', None)
            request.session.modified = True
            
            # OPTIMIZATION: Process non-critical operations asynchronously
            if not partial_payment_selected:
                from .tasks import process_transaction_completion, update_sales_statistics
                process_transaction_completion.delay(str(completed_transaction.id))
                update_sales_statistics.delay(str(completed_transaction.id))
            
            # Log performance
            processing_time = time.time() - start_time
            if partial_payment_selected:
                logger.info(f"Checkout partial plan created in {processing_time:.3f}s for transaction {completed_transaction.id}")
            else:
                logger.info(f"Checkout completion time: {processing_time:.3f}s for transaction {completed_transaction.fiscal_series}")
            
            success_message = (
                _('Payment plan created successfully. Seats are reserved until the customer completes the schedule.')
                if partial_payment_selected else
                _('Transaction completed successfully! Fiscal series: %(series)s') % {'series': completed_transaction.fiscal_series}
            )
            
            response_payload = {
                'success': True,
                'message': success_message,
                'transaction_id': str(completed_transaction.id),
                'processing_time': f"{processing_time:.2f}s",
                'redirect_url': reverse('sales_web:transaction_detail', kwargs={'transaction_id': completed_transaction.id})
            }
            if not partial_payment_selected:
                response_payload['fiscal_series'] = completed_transaction.fiscal_series
            else:
                response_payload['payment_plan_id'] = str(payment_plan.id) if payment_plan else None
            
            # Return immediate response
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', ''):
                return JsonResponse(response_payload)
            else:
                messages.success(request, success_message)
                return redirect('sales_web:transaction_detail', transaction_id=completed_transaction.id)
                
        except Exception as e:
            # Detailed error logging with full traceback
            import traceback
            import sys

            exc_type, exc_value, exc_traceback = sys.exc_info()
            tb_lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
            tb_text = ''.join(tb_lines)

            logger.error(f"Checkout error: {e}")
            logger.error(f"Exception type: {type(e).__name__}")
            logger.error(f"Full traceback:\n{tb_text}")

            # Log additional context
            logger.error(f"Cart items count: {len(cart)}")
            logger.error(f"User: {request.user.username if request.user.is_authenticated else 'Anonymous'}")
            logger.error(f"Customer ID: {customer_id}")

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', ''):
                return JsonResponse({
                    'success': False,
                    'message': f'Error completing transaction: {str(e)}',
                    'redirect_url': reverse('sales_web:checkout')
                }, status=400)
            else:
                messages.error(request, f'Error completing transaction: {str(e)}')
                return redirect('sales_web:checkout')
    
    # GET request - show confirmation page
    if request.user.is_admin_user:
        customer = get_object_or_404(Customer, id=customer_id)
    else:
        customer = get_object_or_404(Customer, id=customer_id, tenant=request.user.tenant)
    
    cart_items = []
    cart_subtotal = Decimal('0.00')
    event = None
    
    # Process cart items and calculate subtotal
    for item_key, item_data in cart.items():
        cart_subtotal += Decimal(str(item_data.get('total_price', '0.00')))
        cart_items.append(item_data)
        
        # Get event from first item for tax calculation
        if not event:
            if item_data.get('seat_id'):
                try:
                    seat = Seat.objects.select_related('zone__event').get(id=item_data['seat_id'])
                    event = seat.zone.event
                except Seat.DoesNotExist:
                    pass
            elif item_data.get('zone_id'):
                try:
                    zone = Zone.objects.select_related('event').get(id=item_data['zone_id'])
                    event = zone.event
                except Zone.DoesNotExist:
                    pass
    
    # Calculate taxes using fiscal service
    tax_amount = Decimal('0.00')
    tax_details = []
    
    if event:
        from venezuelan_pos.apps.fiscal.services import TaxCalculationService
        try:
            tax_amount, tax_details, _tax_history = TaxCalculationService.calculate_taxes(
                base_amount=cart_subtotal,
                tenant=request.user.tenant,
                event=event,
                user=request.user
            )
        except Exception as e:
            # Log error but don't break checkout
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Tax calculation error in checkout: {e}")
    
    # Calculate final total
    cart_total = cart_subtotal + tax_amount
    
    partial_preview = None
    min_required_display = None
    if partial_payment_selected:
        initial_amount = payment_pref.get('initial_payment_amount', '0')
        try:
            initial_amount = Decimal(str(initial_amount)).quantize(Decimal('0.01'))
        except (TypeError, InvalidOperation):
            initial_amount = Decimal('0.00')
        payment_method_name = None
        method_id = payment_pref.get('payment_method_id')
        tenant_lookup = event.tenant if event else getattr(request.user, 'tenant', None)
        if method_id and tenant_lookup:
            method = PaymentMethod.objects.filter(tenant=tenant_lookup, id=method_id).first()
            if method:
                payment_method_name = method.name

        if event:
            event_config = EventConfiguration.objects.filter(event=event).first()
            if event_config and event_config.min_down_payment_percentage:
                min_required = (cart_total * (Decimal(str(event_config.min_down_payment_percentage)) / Decimal('100'))).quantize(Decimal('0.01'))
                min_required_display = str(min_required)

        remaining_balance = cart_total - initial_amount if initial_amount is not None else cart_total
        partial_preview = {
            'plan_type': payment_pref.get('plan_type', PaymentPlan.PlanType.FLEXIBLE),
            'installment_count': payment_pref.get('installment_count'),
            'initial_payment_amount': str(initial_amount),
            'payment_method_name': payment_method_name,
            'remaining_balance': str(remaining_balance.quantize(Decimal('0.01'))),
        }

    context = {
        'customer': customer,
        'cart_items': cart_items,
        'cart_subtotal': str(cart_subtotal),
        'tax_amount': str(tax_amount),
        'tax_details': tax_details,
        'cart_total': str(cart_total),
        'cart_count': len(cart_items),
        'event': event,
        'payment_pref': payment_pref,
        'partial_payment_selected': partial_payment_selected,
        'partial_payment_preview': partial_preview,
        'min_down_payment_required': min_required_display,
    }
    
    return render(request, 'sales/checkout_confirm.html', context)


@login_required
def transaction_list(request):
    """List all transactions with filtering and search."""
    
    # Filter by tenant
    if request.user.is_admin_user:
        transactions = Transaction.objects.all()
    else:
        transactions = Transaction.objects.filter(tenant=request.user.tenant)
    
    transactions = transactions.select_related('event', 'customer').order_by('-created_at')
    
    # Filters
    search = request.GET.get('search', '')
    status = request.GET.get('status', '')
    event_id = request.GET.get('event', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    if search:
        transactions = transactions.filter(
            Q(fiscal_series__icontains=search) |
            Q(customer__name__icontains=search) |
            Q(customer__surname__icontains=search) |
            Q(customer__email__icontains=search) |
            Q(event__name__icontains=search)
        )
    
    if status:
        transactions = transactions.filter(status=status)
    
    if event_id:
        transactions = transactions.filter(event_id=event_id)
    
    if date_from:
        transactions = transactions.filter(created_at__gte=date_from)
    
    if date_to:
        transactions = transactions.filter(created_at__lte=date_to)
    
    # Pagination
    paginator = Paginator(transactions, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Events for filter
    if request.user.is_admin_user:
        events_for_filter = Event.objects.filter(status=Event.Status.ACTIVE).order_by('name')
    else:
        events_for_filter = Event.objects.filter(
            tenant=request.user.tenant,
            status=Event.Status.ACTIVE
        ).order_by('name')
    
    context = {
        'transactions': page_obj,
        'events_for_filter': events_for_filter,
        'total_transactions': paginator.count,
        'is_paginated': page_obj.has_other_pages(),
        'page_obj': page_obj,
    }
    
    return render(request, 'sales/transaction_list.html', context)


@login_required
def transaction_detail(request, transaction_id):
    """Detailed view of a specific transaction."""
    
    if request.user.is_admin_user:
        transaction_obj = get_object_or_404(
            Transaction.objects.select_related('event', 'customer').prefetch_related(
                'items__zone', 'items__seat'
            ),
            id=transaction_id
        )
    else:
        transaction_obj = get_object_or_404(
            Transaction.objects.select_related('event', 'customer').prefetch_related(
                'items__zone', 'items__seat'
            ),
            id=transaction_id,
            tenant=request.user.tenant
        )
    
    event_config = EventConfiguration.objects.filter(event=transaction_obj.event).first()
    can_create_plan = (
        transaction_obj.status == Transaction.Status.PENDING and
        not hasattr(transaction_obj, 'payment_plan') and
        event_config and event_config.partial_payments_enabled
    )
    min_down_payment = None
    if event_config and event_config.min_down_payment_percentage:
        min_down_payment = (transaction_obj.total_amount * (
            Decimal(str(event_config.min_down_payment_percentage)) / Decimal('100')
        )).quantize(Decimal('0.01'))
    
    context = {
        'transaction': transaction_obj,
        'event_config': event_config,
        'can_create_payment_plan': can_create_plan,
        'min_down_payment': min_down_payment,
        'payment_plan': getattr(transaction_obj, 'payment_plan', None),
    }
    
    return render(request, 'sales/transaction_detail.html', context)


@login_required
def transaction_receipt(request, transaction_id):
    """Generate printable receipt for a transaction."""
    
    if request.user.is_admin_user:
        transaction_obj = get_object_or_404(
            Transaction.objects.select_related('event', 'customer').prefetch_related(
                'items__zone', 'items__seat'
            ),
            id=transaction_id
        )
    else:
        transaction_obj = get_object_or_404(
            Transaction.objects.select_related('event', 'customer').prefetch_related(
                'items__zone', 'items__seat'
            ),
            id=transaction_id,
            tenant=request.user.tenant
        )
    
    context = {
        'transaction': transaction_obj,
        'print_mode': True,
    }
    
    return render(request, 'sales/transaction_receipt.html', context)


@login_required
@require_POST
def complete_transaction(request, transaction_id):
    """Complete a pending transaction."""
    
    if request.user.is_admin_user:
        transaction_obj = get_object_or_404(Transaction, id=transaction_id)
    else:
        transaction_obj = get_object_or_404(
            Transaction, 
            id=transaction_id, 
            tenant=request.user.tenant
        )
    
    try:
        if transaction_obj.can_be_completed():
            completed_transaction = Transaction.objects.complete_transaction(transaction_obj)
            messages.success(
                request,
                f'Transaction completed! Fiscal series: {completed_transaction.fiscal_series}'
            )
        else:
            messages.error(request, 'Transaction cannot be completed in current status.')
    except Exception as e:
        messages.error(request, f'Error completing transaction: {str(e)}')
    
    return redirect('sales_web:transaction_detail', transaction_id=transaction_id)


@login_required
def reservation_list(request):
    """List active reservations."""
    
    if request.user.is_admin_user:
        reservations = ReservedTicket.objects.all()
    else:
        reservations = ReservedTicket.objects.filter(tenant=request.user.tenant)
    
    reservations = reservations.select_related(
        'transaction__customer', 'zone', 'seat'
    ).order_by('reserved_until')
    
    # Filter active reservations by default
    status_filter = request.GET.get('status', 'active')
    if status_filter == 'active':
        reservations = reservations.filter(
            status=ReservedTicket.Status.ACTIVE,
            reserved_until__gt=timezone.now()
        )
    elif status_filter:
        reservations = reservations.filter(status=status_filter)
    
    context = {
        'reservations': reservations,
        'status_filter': status_filter,
    }
    
    return render(request, 'sales/reservation_list.html', context)


@login_required
@require_POST
def extend_reservation(request, reservation_id):
    """Extend reservation time."""
    
    if request.user.is_admin_user:
        reservation = get_object_or_404(ReservedTicket, id=reservation_id)
    else:
        reservation = get_object_or_404(
            ReservedTicket, 
            id=reservation_id, 
            tenant=request.user.tenant
        )
    
    if reservation.is_active:
        # Extend by 30 minutes
        reservation.reserved_until += timedelta(minutes=30)
        reservation.save()
        messages.success(request, 'Reservation extended by 30 minutes.')
    else:
        messages.error(request, 'Cannot extend expired or inactive reservation.')
    
    return redirect('sales_web:reservation_list')


@login_required
@require_POST
def cancel_reservation(request, reservation_id):
    """Cancel a reservation."""
    
    if request.user.is_admin_user:
        reservation = get_object_or_404(ReservedTicket, id=reservation_id)
    else:
        reservation = get_object_or_404(
            ReservedTicket, 
            id=reservation_id, 
            tenant=request.user.tenant
        )
    
    try:
        reservation.cancel()
        messages.success(request, 'Reservation cancelled successfully.')
    except Exception as e:
        messages.error(request, f'Error cancelling reservation: {str(e)}')
    
    return redirect('sales_web:reservation_list')


# AJAX Views for real-time updates

@login_required
def ajax_seat_availability(request):
    """Get real-time seat availability via AJAX."""
    
    seat_ids = request.GET.getlist('seat_ids[]')
    
    if not seat_ids:
        return JsonResponse({'error': 'No seat IDs provided'}, status=400)
    
    availability_data = {}
    
    for seat_id in seat_ids:
        try:
            # Check cache first
            cached_data = sales_cache.get_seat_availability(seat_id)
            if cached_data:
                availability_data[seat_id] = cached_data
            else:
                # Fallback to database
                if request.user.is_admin_user:
                    seat = Seat.objects.get(id=seat_id)
                else:
                    seat = Seat.objects.get(id=seat_id, tenant=request.user.tenant)
                
                availability_data[seat_id] = {
                    'status': seat.status,
                    'is_available': seat.is_available,
                    'last_updated': timezone.now().isoformat(),
                }
        except Seat.DoesNotExist:
            availability_data[seat_id] = {
                'status': 'not_found',
                'is_available': False,
                'last_updated': timezone.now().isoformat(),
            }
    
    return JsonResponse({
        'success': True,
        'availability': availability_data,
    })


@login_required
def ajax_zone_availability(request):
    """Get real-time zone availability via AJAX."""
    
    zone_id = request.GET.get('zone_id')
    
    if not zone_id:
        return JsonResponse({'error': 'Zone ID is required'}, status=400)
    
    try:
        if request.user.is_admin_user:
            zone = Zone.objects.get(id=zone_id)
        else:
            zone = Zone.objects.get(id=zone_id, tenant=request.user.tenant)
        
        def _to_int(value, default=0):
            try:
                return int(value)
            except (TypeError, ValueError):
                try:
                    return int(float(value))
                except (TypeError, ValueError):
                    return default
        
        cart = get_clean_cart(request)
        cart_quantity = 0
        for item in cart.values():
            if str(item.get('zone_id')) == str(zone_id):
                cart_quantity += _to_int(item.get('quantity', 0), 0)
        
        now_iso = timezone.now().isoformat()
        
        # Check cache first
        cached_data = sales_cache.get_zone_seat_availability(zone_id)
        if cached_data:
            availability_data = cached_data.copy()
            
            available_seats = cached_data.get('available_seats')
            if available_seats is None:
                available_seats = cached_data.get('available_capacity')
            if available_seats is None and zone.zone_type == Zone.ZoneType.NUMBERED:
                seats_snapshot = cached_data.get('seats') or {}
                available_seats = sum(
                    1 for seat in seats_snapshot.values()
                    if seat.get('status') == Seat.Status.AVAILABLE
                )
            
            available_seats = _to_int(available_seats, 0)
            
            total_seats = cached_data.get('total_seats') or cached_data.get('capacity')
            if total_seats is None and zone.zone_type == Zone.ZoneType.NUMBERED:
                total_seats = zone.seats.count()
            total_seats = _to_int(total_seats, zone.capacity)
            
            sold_seats = cached_data.get('sold_seats') or cached_data.get('sold_capacity')
            if sold_seats is None:
                sold_seats = max(total_seats - available_seats, 0)
            sold_seats = _to_int(sold_seats, 0)
            
            effective_available = max(available_seats - cart_quantity, 0)
            occupancy_percentage = (
                (sold_seats / total_seats * 100)
                if total_seats else 0
            )
            
            availability_data.update({
                'available_seats': available_seats,
                'available_capacity': available_seats,
                'total_seats': total_seats,
                'total_capacity': total_seats,
                'sold_seats': sold_seats,
                'sold_capacity': sold_seats,
                'effective_available_seats': effective_available,
                'cart_quantity': cart_quantity,
                'occupancy_percentage': occupancy_percentage,
                'is_sold_out': available_seats <= 0,
                'last_updated': now_iso,
            })
            
            return JsonResponse({
                'success': True,
                'zone_id': zone_id,
                'availability': availability_data,
            })
        
        # Fallback to database calculation
        if zone.zone_type == Zone.ZoneType.NUMBERED:
            available_seats = zone.seats.filter(status=Seat.Status.AVAILABLE).count()
            total_seats = zone.seats.count()
        else:
            available_seats = zone.available_capacity
            total_seats = zone.capacity
        
        available_seats = _to_int(available_seats, 0)
        total_seats = _to_int(total_seats, 0)
        sold_seats = max(total_seats - available_seats, 0)
        effective_available = max(available_seats - cart_quantity, 0)
        occupancy_percentage = (
            (sold_seats / total_seats * 100)
            if total_seats > 0 else 0
        )
        
        availability_data = {
            'available_seats': available_seats,
            'total_seats': total_seats,
            'sold_seats': sold_seats,
            'available_capacity': available_seats,
            'total_capacity': total_seats,
            'sold_capacity': sold_seats,
            'effective_available_seats': effective_available,
            'cart_quantity': cart_quantity,
            'occupancy_percentage': occupancy_percentage,
            'is_sold_out': available_seats == 0,
            'last_updated': now_iso,
        }
        
        return JsonResponse({
            'success': True,
            'zone_id': zone_id,
            'availability': availability_data,
        })
        
    except Zone.DoesNotExist:
        return JsonResponse({'error': 'Zone not found'}, status=404)


@login_required
def ajax_pricing_info(request):
    """Get current pricing information via AJAX."""
    
    zone_id = request.GET.get('zone_id')
    seat_id = request.GET.get('seat_id')
    
    if not zone_id:
        return JsonResponse({'error': 'Zone ID is required'}, status=400)
    
    try:
        if request.user.is_admin_user:
            zone = Zone.objects.get(id=zone_id)
        else:
            zone = Zone.objects.get(id=zone_id, tenant=request.user.tenant)
        
        pricing_service = PricingCalculationService()
        
        if seat_id:
            # Get specific seat pricing
            seat = Seat.objects.get(id=seat_id, zone=zone)
            final_price, pricing_details = pricing_service.calculate_seat_price(seat)
        else:
            # Get zone pricing
            final_price, pricing_details = pricing_service.calculate_zone_price(zone)
        
        return JsonResponse({
            'success': True,
            'zone_id': zone_id,
            'seat_id': seat_id,
            'final_price': str(final_price),
            'pricing_details': serialize_pricing_details(pricing_details),
        })
        
    except (Zone.DoesNotExist, Seat.DoesNotExist) as e:
        return JsonResponse({'error': str(e)}, status=404)


@login_required
def ajax_cart_update(request):
    """Get current cart status via AJAX."""
    
    cart = request.session.get('shopping_cart', {})
    cart_total = sum(Decimal(str(item['total_price'])) for item in cart.values())
    cart_count = len(cart)
    
    return JsonResponse({
        'success': True,
        'cart_total': str(cart_total),
        'cart_count': cart_count,
        'cart_items': list(cart.values()),
    })
