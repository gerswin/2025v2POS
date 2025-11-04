"""
Sales transaction API views.
Implements ticket purchase API with idempotency, seat selection, and transaction validation.
"""

from decimal import Decimal
from typing import Dict, Any
from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db import transaction
from django.utils import timezone
from django.core.cache import cache
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes

from .models import Transaction, TransactionItem, ReservedTicket
from .serializers import (
    TransactionCreateSerializer,
    TransactionSerializer,
    TransactionListSerializer,
    SeatSelectionSerializer,
    SeatReservationSerializer,
    TransactionCompletionSerializer,
    ReservedTicketSerializer
)
from .cache import sales_cache
from ..tenants.middleware import TenantRequiredMixin
from ..zones.models import Zone, Seat
from ..pricing.services import PricingCalculationService
from ..pricing.sales_integration import stage_pricing_integration
from ..pricing.stage_automation import stage_automation


class TransactionListCreateAPIView(TenantRequiredMixin, generics.ListCreateAPIView):
    """
    API view for listing and creating transactions.
    
    GET: List transactions for the current tenant
    POST: Create a new transaction with idempotency support
    """
    
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return TransactionCreateSerializer
        return TransactionListSerializer
    
    def get_queryset(self):
        """Get transactions for current tenant."""
        queryset = Transaction.objects.filter(tenant=self.request.tenant)
        
        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by event
        event_id = self.request.query_params.get('event_id')
        if event_id:
            queryset = queryset.filter(event_id=event_id)
        
        # Filter by customer
        customer_id = self.request.query_params.get('customer_id')
        if customer_id:
            queryset = queryset.filter(customer_id=customer_id)
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(created_at__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__lte=end_date)
        
        return queryset.select_related('event', 'customer').order_by('-created_at')
    
    @extend_schema(
        summary="Create new transaction",
        description="Create a new ticket purchase transaction with idempotency support",
        request=TransactionCreateSerializer,
        responses={
            201: TransactionSerializer,
            400: "Validation errors",
            409: "Idempotency key conflict"
        },
        examples=[
            OpenApiExample(
                "Numbered seat purchase",
                value={
                    "event_id": "123e4567-e89b-12d3-a456-426614174000",
                    "customer_id": "123e4567-e89b-12d3-a456-426614174001",
                    "items": [
                        {
                            "zone_id": "123e4567-e89b-12d3-a456-426614174002",
                            "seat_id": "123e4567-e89b-12d3-a456-426614174003",
                            "quantity": 1
                        }
                    ],
                    "transaction_type": "online",
                    "currency": "USD",
                    "idempotency_key": "unique-key-12345"
                }
            ),
            OpenApiExample(
                "General admission purchase",
                value={
                    "event_id": "123e4567-e89b-12d3-a456-426614174000",
                    "customer_id": "123e4567-e89b-12d3-a456-426614174001",
                    "items": [
                        {
                            "zone_id": "123e4567-e89b-12d3-a456-426614174002",
                            "quantity": 2
                        }
                    ],
                    "transaction_type": "online",
                    "currency": "USD",
                    "idempotency_key": "unique-key-12346"
                }
            )
        ]
    )
    def post(self, request, *args, **kwargs):
        """Create a new transaction with idempotency."""
        return super().post(request, *args, **kwargs)
    
    def perform_create(self, serializer):
        """Set tenant when creating transaction."""
        # Tenant is set in the serializer's create method
        pass


class TransactionDetailAPIView(TenantRequiredMixin, generics.RetrieveUpdateAPIView):
    """
    API view for retrieving and updating transaction details.
    
    GET: Get transaction details
    PATCH: Update transaction (limited fields)
    """
    
    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'id'
    
    def get_queryset(self):
        """Get transactions for current tenant."""
        return Transaction.objects.filter(tenant=self.request.tenant).select_related(
            'event', 'customer'
        ).prefetch_related('items__zone', 'items__seat')
    
    @extend_schema(
        summary="Get transaction details",
        description="Retrieve detailed information about a specific transaction",
        responses={
            200: TransactionSerializer,
            404: "Transaction not found"
        }
    )
    def get(self, request, *args, **kwargs):
        """Get transaction details."""
        return super().get(request, *args, **kwargs)


class SeatSelectionAPIView(TenantRequiredMixin, APIView):
    """
    API view for seat selection and availability checking.
    Provides real-time seat availability and pricing information.
    """
    
    permission_classes = [permissions.IsAuthenticated]
    
    @extend_schema(
        summary="Check seat availability and pricing",
        description="Check availability and get pricing for specific seats or general admission",
        request=SeatSelectionSerializer,
        responses={
            200: {
                "type": "object",
                "properties": {
                    "zone": {"type": "object"},
                    "availability": {"type": "object"},
                    "pricing": {"type": "object"},
                    "seats": {"type": "array"}
                }
            },
            400: "Validation errors"
        },
        examples=[
            OpenApiExample(
                "Check numbered seats",
                value={
                    "zone_id": "123e4567-e89b-12d3-a456-426614174000",
                    "seat_ids": [
                        "123e4567-e89b-12d3-a456-426614174001",
                        "123e4567-e89b-12d3-a456-426614174002"
                    ]
                }
            ),
            OpenApiExample(
                "Check general admission",
                value={
                    "zone_id": "123e4567-e89b-12d3-a456-426614174000",
                    "quantity": 3
                }
            )
        ]
    )
    def post(self, request):
        """Check seat availability and pricing."""
        serializer = SeatSelectionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        zone = serializer.validated_data['zone']
        pricing_service = PricingCalculationService()
        
        # Get current stage pricing information
        current_stage_info = stage_pricing_integration.get_current_stage_pricing(
            zone.event, zone
        )
        
        response_data = {
            'zone': {
                'id': str(zone.id),
                'name': zone.name,
                'zone_type': zone.zone_type,
                'base_price': str(zone.base_price),
                'capacity': zone.capacity,
                'available_capacity': zone.available_capacity,
                'is_sold_out': zone.is_sold_out
            },
            'availability': {},
            'pricing': {},
            'seats': [],
            'current_stage': current_stage_info
        }
        
        if zone.zone_type == Zone.ZoneType.NUMBERED:
            # Handle numbered seats
            seats = serializer.validated_data.get('seats', [])
            total_price = Decimal('0.00')
            
            for seat in seats:
                # Check cached availability first
                cached_availability = sales_cache.get_seat_availability(str(seat.id))
                if not cached_availability:
                    # Cache miss - rebuild from database
                    sales_cache.cache_seat_availability(seat)
                    cached_availability = sales_cache.get_seat_availability(str(seat.id))
                
                # Calculate pricing
                seat_price, pricing_details = pricing_service.calculate_seat_price(seat)
                total_price += seat_price
                
                seat_data = {
                    'id': str(seat.id),
                    'row_number': seat.row_number,
                    'seat_number': seat.seat_number,
                    'seat_label': seat.seat_label,
                    'status': seat.status,
                    'is_available': seat.is_available,
                    'price': str(seat_price),
                    'pricing_details': pricing_details,
                    'cached_data': cached_availability,
                    'stage_info': {
                        'current_stage': pricing_details.get('stages', [{}])[0] if pricing_details.get('stages') else None,
                        'stage_pricing_applied': bool(pricing_details.get('stages'))
                    }
                }
                response_data['seats'].append(seat_data)
            
            response_data['pricing'] = {
                'total_price': str(total_price),
                'currency': 'USD',
                'seat_count': len(seats)
            }
            
            response_data['availability'] = {
                'all_available': all(seat.is_available for seat in seats),
                'unavailable_seats': [
                    seat.seat_label for seat in seats if not seat.is_available
                ]
            }
        
        else:
            # Handle general admission
            quantity = serializer.validated_data.get('quantity', 1)
            
            # Check cached zone availability
            cached_zone_data = sales_cache.get_zone_seat_availability(str(zone.id))
            if not cached_zone_data:
                cached_zone_data = sales_cache.rebuild_zone_availability_cache(zone)
            
            # Calculate pricing
            zone_price, pricing_details = pricing_service.calculate_zone_price(zone)
            total_price = zone_price * quantity
            
            response_data['pricing'] = {
                'unit_price': str(zone_price),
                'quantity': quantity,
                'total_price': str(total_price),
                'currency': 'USD',
                'pricing_details': pricing_details,
                'stage_info': {
                    'current_stage': pricing_details.get('stages', [{}])[0] if pricing_details.get('stages') else None,
                    'stage_pricing_applied': bool(pricing_details.get('stages'))
                }
            }
            
            response_data['availability'] = {
                'available': quantity <= zone.available_capacity,
                'requested_quantity': quantity,
                'available_capacity': zone.available_capacity,
                'cached_data': cached_zone_data
            }
        
        return Response(response_data, status=status.HTTP_200_OK)


class SeatReservationAPIView(TenantRequiredMixin, APIView):
    """
    API view for creating temporary seat reservations.
    Holds seats for a specified time period during checkout process.
    """
    
    permission_classes = [permissions.IsAuthenticated]
    
    @extend_schema(
        summary="Create seat reservation",
        description="Create temporary seat reservations for checkout process",
        request=SeatReservationSerializer,
        responses={
            201: {
                "type": "object",
                "properties": {
                    "transaction_id": {"type": "string", "format": "uuid"},
                    "reservations": {"type": "array"},
                    "reserved_until": {"type": "string", "format": "date-time"},
                    "reservation_minutes": {"type": "integer"}
                }
            },
            400: "Validation errors",
            409: "Seats not available"
        },
        examples=[
            OpenApiExample(
                "Reserve numbered seats",
                value={
                    "zone_id": "123e4567-e89b-12d3-a456-426614174000",
                    "seat_ids": [
                        "123e4567-e89b-12d3-a456-426614174001",
                        "123e4567-e89b-12d3-a456-426614174002"
                    ],
                    "reservation_minutes": 15,
                    "customer_id": "123e4567-e89b-12d3-a456-426614174003"
                }
            ),
            OpenApiExample(
                "Reserve general admission",
                value={
                    "zone_id": "123e4567-e89b-12d3-a456-426614174000",
                    "quantity": 2,
                    "reservation_minutes": 10,
                    "customer_id": "123e4567-e89b-12d3-a456-426614174003"
                }
            )
        ]
    )
    def post(self, request):
        """Create seat reservations."""
        serializer = SeatReservationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            reservation_data = serializer.save()
            
            # Format response
            response_data = {
                'transaction_id': reservation_data['transaction_id'],
                'reserved_until': reservation_data['reserved_until'].isoformat(),
                'reservation_minutes': serializer.validated_data['reservation_minutes'],
                'reservations': []
            }
            
            for reservation in reservation_data['reservations']:
                reservation_info = {
                    'id': str(reservation.id),
                    'zone_id': str(reservation.zone.id),
                    'zone_name': reservation.zone.name,
                    'quantity': reservation.quantity,
                    'status': reservation.status
                }
                
                if reservation.seat:
                    reservation_info.update({
                        'seat_id': str(reservation.seat.id),
                        'seat_label': reservation.seat.seat_label,
                        'row_number': reservation.seat.row_number,
                        'seat_number': reservation.seat.seat_number
                    })
                
                response_data['reservations'].append(reservation_info)
            
            return Response(response_data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response(
                {'error': f'Failed to create reservations: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )


class TransactionCompletionAPIView(TenantRequiredMixin, APIView):
    """
    API view for completing transactions and generating fiscal series.
    Called when payment is fully completed to finalize the transaction.
    """
    
    permission_classes = [permissions.IsAuthenticated]
    
    @extend_schema(
        summary="Complete transaction",
        description="Complete transaction and generate fiscal series number",
        request=TransactionCompletionSerializer,
        responses={
            200: TransactionSerializer,
            400: "Validation errors",
            404: "Transaction not found"
        },
        examples=[
            OpenApiExample(
                "Complete transaction",
                value={
                    "transaction_id": "123e4567-e89b-12d3-a456-426614174000"
                }
            )
        ]
    )
    def post(self, request):
        """Complete a transaction."""
        serializer = TransactionCompletionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            completed_transaction = serializer.save()
            
            # Return completed transaction details
            response_serializer = TransactionSerializer(completed_transaction)
            return Response(response_serializer.data, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {'error': f'Failed to complete transaction: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )


class ReservedTicketListAPIView(TenantRequiredMixin, generics.ListAPIView):
    """
    API view for listing reserved tickets.
    Shows active reservations and their expiration status.
    """
    
    serializer_class = ReservedTicketSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Get reserved tickets for current tenant."""
        queryset = ReservedTicket.objects.filter(tenant=self.request.tenant)
        
        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by active reservations
        active_only = self.request.query_params.get('active_only')
        if active_only and active_only.lower() == 'true':
            queryset = queryset.filter(
                status=ReservedTicket.Status.ACTIVE,
                reserved_until__gt=timezone.now()
            )
        
        # Filter by zone
        zone_id = self.request.query_params.get('zone_id')
        if zone_id:
            queryset = queryset.filter(zone_id=zone_id)
        
        # Filter by customer
        customer_id = self.request.query_params.get('customer_id')
        if customer_id:
            queryset = queryset.filter(transaction__customer_id=customer_id)
        
        return queryset.select_related(
            'transaction', 'zone', 'seat'
        ).order_by('-created_at')
    
    @extend_schema(
        summary="List reserved tickets",
        description="Get list of reserved tickets with filtering options",
        parameters=[
            OpenApiParameter(
                name='status',
                type=OpenApiTypes.STR,
                description='Filter by reservation status'
            ),
            OpenApiParameter(
                name='active_only',
                type=OpenApiTypes.BOOL,
                description='Show only active reservations'
            ),
            OpenApiParameter(
                name='zone_id',
                type=OpenApiTypes.UUID,
                description='Filter by zone ID'
            ),
            OpenApiParameter(
                name='customer_id',
                type=OpenApiTypes.UUID,
                description='Filter by customer ID'
            )
        ],
        responses={200: ReservedTicketSerializer(many=True)}
    )
    def get(self, request, *args, **kwargs):
        """List reserved tickets."""
        return super().get(request, *args, **kwargs)


@extend_schema(
    summary="Get transaction by fiscal series",
    description="Retrieve transaction details using fiscal series number",
    parameters=[
        OpenApiParameter(
            name='fiscal_series',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.PATH,
            description='Fiscal series number'
        )
    ],
    responses={
        200: TransactionSerializer,
        404: "Transaction not found"
    }
)
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_transaction_by_fiscal_series(request, fiscal_series):
    """Get transaction by fiscal series number."""
    try:
        # Check cache first
        cached_ticket = sales_cache.get_ticket_status(fiscal_series)
        if cached_ticket:
            transaction_id = cached_ticket.get('transaction_id')
            if transaction_id:
                try:
                    transaction_obj = Transaction.objects.get(
                        id=transaction_id,
                        tenant=request.tenant
                    )
                    serializer = TransactionSerializer(transaction_obj)
                    return Response(serializer.data)
                except Transaction.DoesNotExist:
                    pass
        
        # Fallback to database query
        transaction_obj = get_object_or_404(
            Transaction,
            fiscal_series=fiscal_series,
            tenant=request.tenant
        )
        
        serializer = TransactionSerializer(transaction_obj)
        return Response(serializer.data)
        
    except Exception as e:
        return Response(
            {'error': f'Failed to retrieve transaction: {str(e)}'},
            status=status.HTTP_400_BAD_REQUEST
        )


@extend_schema(
    summary="Check stage transitions during purchase",
    description="Check for stage transitions that may affect current purchase session",
    parameters=[
        OpenApiParameter(
            name='event_id',
            type=OpenApiTypes.UUID,
            description='Event ID to check transitions for'
        ),
        OpenApiParameter(
            name='zone_id',
            type=OpenApiTypes.UUID,
            description='Zone ID to check transitions for (optional)'
        )
    ],
    responses={
        200: {
            "type": "object",
            "properties": {
                "transitions_occurred": {"type": "boolean"},
                "transitions": {"type": "array"},
                "new_current_stage": {"type": "object"},
                "pricing_updates": {"type": "object"}
            }
        },
        400: "Invalid parameters",
        404: "Event not found"
    }
)
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def check_stage_transitions(request):
    """Check for stage transitions during active purchase sessions."""
    from ..events.models import Event
    
    event_id = request.query_params.get('event_id')
    zone_id = request.query_params.get('zone_id')
    
    if not event_id:
        return Response(
            {'error': 'event_id parameter is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        event = Event.objects.get(id=event_id, tenant=request.tenant)
        zone = None
        
        if zone_id:
            zone = Zone.objects.get(id=zone_id, event=event, tenant=request.tenant)
        
        # Check for transitions
        transition_result = stage_pricing_integration.handle_stage_transition_during_purchase(
            event, zone
        )
        
        # Get updated pricing if transitions occurred
        pricing_updates = {}
        if transition_result.get('transitions_occurred'):
            if zone:
                pricing_updates = stage_pricing_integration.get_current_stage_pricing(event, zone)
            else:
                # Get pricing for all zones in the event
                pricing_updates = {}
                for event_zone in event.zones.all():
                    pricing_updates[str(event_zone.id)] = stage_pricing_integration.get_current_stage_pricing(
                        event, event_zone
                    )
        
        response_data = {
            **transition_result,
            'pricing_updates': pricing_updates,
            'event_id': str(event.id),
            'zone_id': str(zone.id) if zone else None,
            'check_timestamp': timezone.now().isoformat()
        }
        
        return Response(response_data, status=status.HTTP_200_OK)
        
    except Event.DoesNotExist:
        return Response(
            {'error': 'Event not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Zone.DoesNotExist:
        return Response(
            {'error': 'Zone not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {'error': f'Failed to check stage transitions: {str(e)}'},
            status=status.HTTP_400_BAD_REQUEST
        )


@extend_schema(
    summary="Get pricing information",
    description="Get current pricing for zones, rows, or specific seats with stage information",
    parameters=[
        OpenApiParameter(
            name='zone_id',
            type=OpenApiTypes.UUID,
            description='Zone ID for pricing calculation'
        ),
        OpenApiParameter(
            name='row_number',
            type=OpenApiTypes.INT,
            description='Row number (for numbered zones)'
        ),
        OpenApiParameter(
            name='seat_number',
            type=OpenApiTypes.INT,
            description='Seat number (for specific seat pricing)'
        )
    ],
    responses={
        200: {
            "type": "object",
            "properties": {
                "zone": {"type": "object"},
                "pricing": {"type": "object"},
                "current_stage": {"type": "object"},
                "row_pricing": {"type": "object"},
                "stage_status": {"type": "object"}
            }
        },
        400: "Invalid parameters",
        404: "Zone not found"
    }
)
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_pricing_information(request):
    """Get current pricing information for zones, rows, or seats."""
    zone_id = request.query_params.get('zone_id')
    row_number = request.query_params.get('row_number')
    seat_number = request.query_params.get('seat_number')
    
    if not zone_id:
        return Response(
            {'error': 'zone_id parameter is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        zone = Zone.objects.get(id=zone_id, tenant=request.tenant)
        pricing_service = PricingCalculationService()
        
        # Convert string parameters to integers
        row_num = int(row_number) if row_number else None
        seat_num = int(seat_number) if seat_number else None
        
        if seat_num and row_num and zone.zone_type == Zone.ZoneType.NUMBERED:
            # Get specific seat pricing
            try:
                seat = zone.seats.get(row_number=row_num, seat_number=seat_num)
                final_price, pricing_details = pricing_service.calculate_seat_price(seat)
                
                # Get current stage information
                current_stage_info = stage_pricing_integration.get_current_stage_pricing(
                    zone.event, zone
                )
                
                response_data = {
                    'zone': {
                        'id': str(zone.id),
                        'name': zone.name,
                        'zone_type': zone.zone_type,
                        'base_price': str(zone.base_price)
                    },
                    'seat': {
                        'id': str(seat.id),
                        'row_number': seat.row_number,
                        'seat_number': seat.seat_number,
                        'seat_label': seat.seat_label,
                        'price_modifier': str(seat.price_modifier)
                    },
                    'pricing': pricing_details,
                    'final_price': str(final_price),
                    'current_stage': current_stage_info,
                    'stage_status': current_stage_info.get('status', {}) if current_stage_info.get('has_active_stage') else None
                }
                
            except Seat.DoesNotExist:
                return Response(
                    {'error': f'Seat {row_num}-{seat_num} not found in zone'},
                    status=status.HTTP_404_NOT_FOUND
                )
        else:
            # Get zone or row pricing
            final_price, pricing_details = pricing_service.calculate_zone_price(
                zone, row_num
            )
            
            # Get current stage information
            current_stage_info = stage_pricing_integration.get_current_stage_pricing(
                zone.event, zone
            )
            
            response_data = {
                'zone': {
                    'id': str(zone.id),
                    'name': zone.name,
                    'zone_type': zone.zone_type,
                    'base_price': str(zone.base_price)
                },
                'pricing': pricing_details,
                'final_price': str(final_price),
                'current_stage': current_stage_info,
                'stage_status': current_stage_info.get('status', {}) if current_stage_info.get('has_active_stage') else None
            }
            
            if row_num:
                response_data['row_number'] = row_num
        
        return Response(response_data)
        
    except Zone.DoesNotExist:
        return Response(
            {'error': 'Zone not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except ValueError as e:
        return Response(
            {'error': f'Invalid parameter: {str(e)}'},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return Response(
            {'error': f'Failed to get pricing information: {str(e)}'},
            status=status.HTTP_400_BAD_REQUEST
        )
