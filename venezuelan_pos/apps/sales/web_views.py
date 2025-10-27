"""
Web views for sales interface.
Provides interactive ticket sales interface with real-time seat selection and shopping cart.
"""

import json
import logging
from decimal import Decimal
from datetime import datetime, timedelta
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count, Sum
from django.utils import timezone
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods, require_POST
from django.views.decorators.csrf import csrf_exempt
from django.core.cache import cache
from django.db import transaction

from .models import Transaction, TransactionItem, ReservedTicket
from .serializers import TransactionCreateSerializer, SeatReservationSerializer
from .cache import sales_cache
from ..events.models import Event
from ..zones.models import Zone, Seat
from ..customers.models import Customer
from ..pricing.services import PricingCalculationService

logger = logging.getLogger(__name__)


def serialize_pricing_details(pricing_details: dict) -> dict:
    """
    Convert Decimal values to strings for JSON serialization.
    """
    if not pricing_details:
        return {}
    
    serializable_details = {}
    for key, value in pricing_details.items():
        if isinstance(value, Decimal):
            serializable_details[key] = str(value)
        elif isinstance(value, dict):
            # Handle nested dictionaries
            nested_dict = {}
            for nested_key, nested_value in value.items():
                if isinstance(nested_value, Decimal):
                    nested_dict[nested_key] = str(nested_value)
                else:
                    nested_dict[nested_key] = nested_value
            serializable_details[key] = nested_dict
        elif isinstance(value, list):
            # Handle lists that might contain Decimals
            serializable_list = []
            for item in value:
                if isinstance(item, Decimal):
                    serializable_list.append(str(item))
                elif isinstance(item, dict):
                    serializable_list.append(serialize_pricing_details(item))
                else:
                    serializable_list.append(item)
            serializable_details[key] = serializable_list
        else:
            serializable_details[key] = value
    
    return serializable_details


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
    
    stats = {
        'today_sales': today_transactions.filter(status=Transaction.Status.COMPLETED).count(),
        'today_revenue': today_transactions.filter(
            status=Transaction.Status.COMPLETED
        ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00'),
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
    
    # Add availability information to zones
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
        'cart_total': cart_total,
        'cart_count': len(cart_items),
    }
    
    return render(request, 'sales/seat_selection.html', context)


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
        
        # Get shopping cart items once
        shopping_cart = request.session.get('shopping_cart', {})
        
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
            seat.dynamic_price = zone_price
            
            seats_by_row[seat.row_number].append(seat)
        
        context = {
            'event': event,
            'zone': zone,
            'seats_by_row': seats_by_row,
            'zone_price': zone_price,
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
        
        context = {
            'event': event,
            'zone': zone,
            'zone_price': zone_price,
            'pricing_details': serialize_pricing_details(pricing_details),
            'available_capacity': zone.available_capacity,
        }
        
        return render(request, 'sales/general_admission.html', context)


@login_required
def shopping_cart(request):
    """Shopping cart management interface."""
    
    cart = request.session.get('shopping_cart', {})
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
        'cart_total': cart_total,
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
        'cart_total': cart_total,
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
    
    # Get customer
    if request.user.is_admin_user:
        customer = get_object_or_404(Customer, id=customer_id)
    else:
        customer = get_object_or_404(Customer, id=customer_id, tenant=request.user.tenant)
    
    # Calculate totals
    cart_total = sum(Decimal(str(item['total_price'])) for item in cart.values())
    
    context = {
        'customer': customer,
        'cart_total': cart_total,
        'cart_count': len(cart),
    }
    
    return render(request, 'sales/checkout_payment.html', context)


@login_required
def checkout_confirm(request):
    """Checkout step 4 - Confirm and complete transaction."""
    
    cart = request.session.get('shopping_cart', {})
    customer_id = request.session.get('checkout_customer_id')
    
    if not cart or not customer_id:
        messages.error(request, 'Invalid checkout session.')
        return redirect('sales_web:checkout')
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Get customer
                if request.user.is_admin_user:
                    customer = get_object_or_404(Customer, id=customer_id)
                else:
                    customer = get_object_or_404(Customer, id=customer_id, tenant=request.user.tenant)
                
                # Create transaction
                event = None
                items_data = []
                
                for item_key, item_data in cart.items():
                    if item_data.get('seat_id'):
                        seat = Seat.objects.select_related('zone').get(id=item_data['seat_id'])
                        zone = seat.zone
                        event = zone.event
                        
                        items_data.append({
                            'zone': zone,
                            'seat': seat,
                            'quantity': 1,
                            'unit_price': Decimal(str(item_data['unit_price'])),
                        })
                    elif item_data.get('zone_id'):
                        zone = Zone.objects.select_related('event').get(id=item_data['zone_id'])
                        event = zone.event
                        
                        items_data.append({
                            'zone': zone,
                            'quantity': item_data['quantity'],
                            'unit_price': Decimal(str(item_data['unit_price'])),
                        })
                
                # Create transaction using the manager
                transaction_obj = Transaction.objects.create_transaction(
                    tenant=request.user.tenant,
                    event=event,
                    customer=customer,
                    items_data=items_data,
                    transaction_type=Transaction.TransactionType.ONLINE,
                )
                
                # Complete transaction immediately for full payment
                completed_transaction = Transaction.objects.complete_transaction(transaction_obj)
                
                # Clear cart and checkout session
                request.session['shopping_cart'] = {}
                if 'checkout_customer_id' in request.session:
                    del request.session['checkout_customer_id']
                request.session.modified = True
                
                messages.success(
                    request, 
                    f'Transaction completed successfully! Fiscal series: {completed_transaction.fiscal_series}'
                )
                
                return redirect('sales_web:transaction_detail', transaction_id=completed_transaction.id)
                
        except Exception as e:
            messages.error(request, f'Error completing transaction: {str(e)}')
            return redirect('sales_web:checkout')
    
    # GET request - show confirmation page
    if request.user.is_admin_user:
        customer = get_object_or_404(Customer, id=customer_id)
    else:
        customer = get_object_or_404(Customer, id=customer_id, tenant=request.user.tenant)
    
    cart_items = []
    cart_total = Decimal('0.00')
    
    for item_key, item_data in cart.items():
        cart_total += Decimal(str(item_data.get('total_price', '0.00')))
        cart_items.append(item_data)
    
    context = {
        'customer': customer,
        'cart_items': cart_items,
        'cart_total': cart_total,
        'cart_count': len(cart_items),
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
    
    context = {
        'transaction': transaction_obj,
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
        
        # Check cache first
        cached_data = sales_cache.get_zone_seat_availability(zone_id)
        if cached_data:
            return JsonResponse({
                'success': True,
                'zone_id': zone_id,
                'availability': cached_data,
            })
        
        # Fallback to database calculation
        if zone.zone_type == Zone.ZoneType.NUMBERED:
            available_seats = zone.seats.filter(status=Seat.Status.AVAILABLE).count()
            total_seats = zone.seats.count()
        else:
            available_seats = zone.available_capacity
            total_seats = zone.capacity
        
        availability_data = {
            'available_seats': available_seats,
            'total_seats': total_seats,
            'occupancy_percentage': (
                (total_seats - available_seats) / total_seats * 100
                if total_seats > 0 else 0
            ),
            'is_sold_out': available_seats == 0,
            'last_updated': timezone.now().isoformat(),
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