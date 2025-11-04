"""
Serializers for sales transaction endpoints.
Handles ticket purchase API with idempotency, seat selection, and transaction validation.
"""

from decimal import Decimal
from typing import Dict, List, Optional
from rest_framework import serializers
from django.db import transaction
from django.utils import timezone
from django.core.cache import cache
from django.conf import settings

from .models import Transaction, TransactionItem, ReservedTicket, FiscalSeriesCounter
from .cache import sales_cache
from ..events.models import Event
from ..zones.models import Zone, Seat
from ..customers.models import Customer
from ..pricing.services import PricingCalculationService
from ..pricing.sales_integration import stage_pricing_integration
from ..pricing.stage_automation import stage_automation


class TransactionItemCreateSerializer(serializers.Serializer):
    """Serializer for creating transaction items."""
    
    zone_id = serializers.UUIDField(help_text="Zone ID for the ticket")
    seat_id = serializers.UUIDField(
        required=False,
        allow_null=True,
        help_text="Seat ID for numbered zones (required for numbered zones)"
    )
    quantity = serializers.IntegerField(
        default=1,
        min_value=1,
        help_text="Number of tickets (for general admission only)"
    )
    
    def validate(self, data):
        """Validate transaction item data."""
        zone_id = data.get('zone_id')
        seat_id = data.get('seat_id')
        quantity = data.get('quantity', 1)
        
        # Validate zone exists
        try:
            zone = Zone.objects.get(id=zone_id)
            data['zone'] = zone
        except Zone.DoesNotExist:
            raise serializers.ValidationError({
                'zone_id': 'Zone not found'
            })
        
        # Validate seat requirements for numbered zones
        if zone.zone_type == Zone.ZoneType.NUMBERED:
            if not seat_id:
                raise serializers.ValidationError({
                    'seat_id': 'Seat ID is required for numbered zones'
                })
            
            if quantity != 1:
                raise serializers.ValidationError({
                    'quantity': 'Quantity must be 1 for numbered seat tickets'
                })
            
            # Validate seat exists and belongs to zone
            try:
                seat = Seat.objects.get(id=seat_id, zone=zone)
                data['seat'] = seat
                
                # Check seat availability
                if not seat.is_available:
                    raise serializers.ValidationError({
                        'seat_id': f'Seat {seat.seat_label} is not available'
                    })
                    
            except Seat.DoesNotExist:
                raise serializers.ValidationError({
                    'seat_id': 'Seat not found or does not belong to the specified zone'
                })
        
        # Validate general admission
        elif zone.zone_type == Zone.ZoneType.GENERAL:
            if seat_id:
                raise serializers.ValidationError({
                    'seat_id': 'Seat ID should not be provided for general admission zones'
                })
            
            # Check zone capacity
            if quantity > zone.available_capacity:
                raise serializers.ValidationError({
                    'quantity': f'Only {zone.available_capacity} tickets available in zone {zone.name}'
                })
        
        return data


class TransactionCreateSerializer(serializers.Serializer):
    """Serializer for creating new transactions with idempotency."""
    
    event_id = serializers.UUIDField(help_text="Event ID for the transaction")
    customer_id = serializers.UUIDField(help_text="Customer ID for the transaction")
    items = TransactionItemCreateSerializer(many=True, help_text="List of transaction items")
    transaction_type = serializers.ChoiceField(
        choices=Transaction.TransactionType.choices,
        default=Transaction.TransactionType.ONLINE,
        help_text="Type of transaction"
    )
    currency = serializers.CharField(
        default='USD',
        max_length=3,
        help_text="Transaction currency"
    )
    notes = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Additional transaction notes"
    )
    
    # Idempotency key for preventing duplicate transactions
    idempotency_key = serializers.CharField(
        max_length=255,
        help_text="Unique key to prevent duplicate transactions"
    )
    
    def validate(self, data):
        """Validate transaction creation data."""
        event_id = data.get('event_id')
        customer_id = data.get('customer_id')
        items = data.get('items', [])
        idempotency_key = data.get('idempotency_key')
        
        if not items:
            raise serializers.ValidationError({
                'items': 'At least one transaction item is required'
            })
        
        # Validate event exists and is active
        try:
            event = Event.objects.get(id=event_id)
            if event.status != Event.Status.ACTIVE:
                raise serializers.ValidationError({
                    'event_id': 'Event is not active for ticket sales'
                })
            data['event'] = event
        except Event.DoesNotExist:
            raise serializers.ValidationError({
                'event_id': 'Event not found'
            })
        
        # Validate customer exists
        try:
            customer = Customer.objects.get(id=customer_id)
            data['customer'] = customer
        except Customer.DoesNotExist:
            raise serializers.ValidationError({
                'customer_id': 'Customer not found'
            })
        
        # Validate all items belong to the same event
        for item_data in items:
            zone = item_data['zone']
            if zone.event != event:
                raise serializers.ValidationError({
                    'items': f'Zone {zone.name} does not belong to the specified event'
                })
        
        # Check idempotency key uniqueness using Redis
        cache_key = f"transaction_idempotency:{idempotency_key}"
        existing_transaction_id = cache.get(cache_key)
        if existing_transaction_id:
            raise serializers.ValidationError({
                'idempotency_key': 'Transaction with this idempotency key already exists'
            })
        
        # Validate purchase against current pricing stages
        is_valid, validation_result = stage_pricing_integration.validate_purchase_with_stages(
            event, items, idempotency_key
        )
        
        if not is_valid:
            raise serializers.ValidationError({
                'stage_validation': validation_result.get('errors', ['Stage validation failed'])
            })
        
        # Store stage validation result for use in create method
        data['_stage_validation'] = validation_result
        
        return data
    
    def create(self, validated_data):
        """Create transaction with items and handle seat reservations."""
        event = validated_data['event']
        customer = validated_data['customer']
        items_data = validated_data.pop('items')
        idempotency_key = validated_data.pop('idempotency_key')
        stage_validation = validated_data.pop('_stage_validation', {})
        
        # Use Redis lock to prevent race conditions
        lock_key = f"transaction_lock:{idempotency_key}"
        
        with transaction.atomic():
            # Double-check idempotency key
            cache_key = f"transaction_idempotency:{idempotency_key}"
            existing_transaction_id = cache.get(cache_key)
            if existing_transaction_id:
                try:
                    return Transaction.objects.get(id=existing_transaction_id)
                except Transaction.DoesNotExist:
                    # Cache is stale, continue with creation
                    pass
            
            # Create transaction
            transaction_obj = Transaction.objects.create(
                tenant=event.tenant,
                event=event,
                customer=customer,
                status=Transaction.Status.PENDING,
                **validated_data
            )
            
            # Create transaction items and calculate pricing
            pricing_service = PricingCalculationService()
            total_amount = Decimal('0.00')
            
            for item_data in items_data:
                zone = item_data['zone']
                seat = item_data.get('seat')
                quantity = item_data.get('quantity', 1)
                
                # Calculate pricing
                if seat:
                    # Numbered seat pricing
                    unit_price, pricing_details = pricing_service.calculate_seat_price(seat)
                    item_type = TransactionItem.ItemType.NUMBERED_SEAT
                    
                    # Reserve the seat
                    seat.status = Seat.Status.RESERVED
                    seat.save(update_fields=['status'])
                    
                    # Invalidate seat cache
                    sales_cache.invalidate_seat_caches(seat)
                    
                else:
                    # General admission pricing
                    unit_price, pricing_details = pricing_service.calculate_zone_price(zone)
                    item_type = TransactionItem.ItemType.GENERAL_ADMISSION
                
                # Create transaction item
                item = TransactionItem.objects.create(
                    tenant=event.tenant,
                    transaction=transaction_obj,
                    zone=zone,
                    seat=seat,
                    item_type=item_type,
                    quantity=quantity,
                    unit_price=unit_price,
                    description=f"{zone.name}" + (f" - {seat.seat_label}" if seat else ""),
                    metadata={'pricing_details': pricing_details}
                )
                
                total_amount += item.total_price
            
            # Update transaction total
            transaction_obj.total_amount = total_amount
            transaction_obj.subtotal_amount = sum(
                item.subtotal_price for item in transaction_obj.items.all()
            )
            transaction_obj.tax_amount = sum(
                item.tax_amount for item in transaction_obj.items.all()
            )
            transaction_obj.save(update_fields=['total_amount', 'subtotal_amount', 'tax_amount'])
            
            # Cache transaction for idempotency (expires in 1 hour)
            cache.set(cache_key, str(transaction_obj.id), 3600)
            
            # Cache transaction data
            sales_cache.cache_transaction(transaction_obj)
            
            # Confirm stage purchases after successful transaction creation
            if stage_validation:
                stage_pricing_integration.confirm_stage_purchases(
                    transaction_obj, idempotency_key
                )
            
            return transaction_obj


class TransactionItemSerializer(serializers.ModelSerializer):
    """Serializer for transaction items."""
    
    zone_name = serializers.CharField(source='zone.name', read_only=True)
    seat_label = serializers.CharField(source='seat.seat_label', read_only=True)
    
    class Meta:
        model = TransactionItem
        fields = [
            'id', 'zone', 'zone_name', 'seat', 'seat_label', 'item_type',
            'quantity', 'unit_price', 'subtotal_price', 'tax_rate', 'tax_amount',
            'total_price', 'description', 'metadata', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class TransactionSerializer(serializers.ModelSerializer):
    """Serializer for transaction details."""
    
    event_name = serializers.CharField(source='event.name', read_only=True)
    customer_name = serializers.CharField(source='customer.full_name', read_only=True)
    items = TransactionItemSerializer(many=True, read_only=True)
    ticket_count = serializers.ReadOnlyField()
    is_completed = serializers.ReadOnlyField()
    is_pending = serializers.ReadOnlyField()
    is_reserved = serializers.ReadOnlyField()
    can_be_completed = serializers.ReadOnlyField()
    
    class Meta:
        model = Transaction
        fields = [
            'id', 'event', 'event_name', 'customer', 'customer_name',
            'fiscal_series', 'transaction_type', 'subtotal_amount', 'tax_amount',
            'total_amount', 'currency', 'exchange_rate', 'status',
            'created_at', 'completed_at', 'updated_at', 'offline_block_id',
            'sync_status', 'notes', 'metadata', 'items', 'ticket_count',
            'is_completed', 'is_pending', 'is_reserved', 'can_be_completed'
        ]
        read_only_fields = [
            'id', 'fiscal_series', 'created_at', 'completed_at', 'updated_at'
        ]


class TransactionListSerializer(serializers.ModelSerializer):
    """Simplified serializer for transaction lists."""
    
    event_name = serializers.CharField(source='event.name', read_only=True)
    customer_name = serializers.CharField(source='customer.full_name', read_only=True)
    ticket_count = serializers.ReadOnlyField()
    
    class Meta:
        model = Transaction
        fields = [
            'id', 'event', 'event_name', 'customer', 'customer_name',
            'fiscal_series', 'transaction_type', 'total_amount', 'currency',
            'status', 'created_at', 'completed_at', 'ticket_count'
        ]
        read_only_fields = ['id', 'created_at', 'completed_at']


class SeatSelectionSerializer(serializers.Serializer):
    """Serializer for seat selection and availability checking."""
    
    zone_id = serializers.UUIDField(help_text="Zone ID to check seats for")
    seat_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        help_text="List of seat IDs to check (for numbered zones)"
    )
    quantity = serializers.IntegerField(
        required=False,
        min_value=1,
        help_text="Number of tickets needed (for general zones)"
    )
    
    def validate(self, data):
        """Validate seat selection request."""
        zone_id = data.get('zone_id')
        seat_ids = data.get('seat_ids')
        quantity = data.get('quantity')
        
        try:
            zone = Zone.objects.get(id=zone_id)
            data['zone'] = zone
        except Zone.DoesNotExist:
            raise serializers.ValidationError({
                'zone_id': 'Zone not found'
            })
        
        if zone.zone_type == Zone.ZoneType.NUMBERED:
            if not seat_ids:
                raise serializers.ValidationError({
                    'seat_ids': 'Seat IDs are required for numbered zones'
                })
            
            # Validate all seats exist and belong to zone
            seats = Seat.objects.filter(id__in=seat_ids, zone=zone)
            if seats.count() != len(seat_ids):
                raise serializers.ValidationError({
                    'seat_ids': 'Some seats do not exist or do not belong to the zone'
                })
            
            data['seats'] = list(seats)
            
        elif zone.zone_type == Zone.ZoneType.GENERAL:
            if not quantity:
                raise serializers.ValidationError({
                    'quantity': 'Quantity is required for general admission zones'
                })
            
            if quantity > zone.available_capacity:
                raise serializers.ValidationError({
                    'quantity': f'Only {zone.available_capacity} tickets available'
                })
        
        return data


class SeatReservationSerializer(serializers.Serializer):
    """Serializer for creating seat reservations."""
    
    zone_id = serializers.UUIDField(help_text="Zone ID for reservation")
    seat_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        help_text="List of seat IDs to reserve (for numbered zones)"
    )
    quantity = serializers.IntegerField(
        required=False,
        min_value=1,
        help_text="Number of tickets to reserve (for general zones)"
    )
    reservation_minutes = serializers.IntegerField(
        default=15,
        min_value=1,
        max_value=60,
        help_text="Minutes to hold the reservation (1-60)"
    )
    customer_id = serializers.UUIDField(help_text="Customer ID for the reservation")
    
    def validate(self, data):
        """Validate reservation request."""
        zone_id = data.get('zone_id')
        seat_ids = data.get('seat_ids')
        quantity = data.get('quantity')
        customer_id = data.get('customer_id')
        
        # Validate zone
        try:
            zone = Zone.objects.get(id=zone_id)
            data['zone'] = zone
        except Zone.DoesNotExist:
            raise serializers.ValidationError({
                'zone_id': 'Zone not found'
            })
        
        # Validate customer
        try:
            customer = Customer.objects.get(id=customer_id)
            data['customer'] = customer
        except Customer.DoesNotExist:
            raise serializers.ValidationError({
                'customer_id': 'Customer not found'
            })
        
        # Validate based on zone type
        if zone.zone_type == Zone.ZoneType.NUMBERED:
            if not seat_ids:
                raise serializers.ValidationError({
                    'seat_ids': 'Seat IDs are required for numbered zones'
                })
            
            # Check seat availability
            seats = Seat.objects.filter(id__in=seat_ids, zone=zone)
            if seats.count() != len(seat_ids):
                raise serializers.ValidationError({
                    'seat_ids': 'Some seats do not exist or do not belong to the zone'
                })
            
            unavailable_seats = [
                seat for seat in seats if not seat.is_available
            ]
            if unavailable_seats:
                seat_labels = [seat.seat_label for seat in unavailable_seats]
                raise serializers.ValidationError({
                    'seat_ids': f'Seats not available: {", ".join(seat_labels)}'
                })
            
            data['seats'] = list(seats)
            
        elif zone.zone_type == Zone.ZoneType.GENERAL:
            if not quantity:
                raise serializers.ValidationError({
                    'quantity': 'Quantity is required for general admission zones'
                })
            
            if quantity > zone.available_capacity:
                raise serializers.ValidationError({
                    'quantity': f'Only {zone.available_capacity} tickets available'
                })
        
        return data
    
    def create(self, validated_data):
        """Create seat reservations."""
        zone = validated_data['zone']
        customer = validated_data['customer']
        reservation_minutes = validated_data['reservation_minutes']
        reserved_until = timezone.now() + timezone.timedelta(minutes=reservation_minutes)
        
        # Create a temporary transaction for the reservation
        temp_transaction = Transaction.objects.create(
            tenant=zone.tenant,
            event=zone.event,
            customer=customer,
            status=Transaction.Status.RESERVED,
            transaction_type=Transaction.TransactionType.PARTIAL_PAYMENT
        )
        
        reservations = []
        
        with transaction.atomic():
            if zone.zone_type == Zone.ZoneType.NUMBERED:
                # Reserve specific seats
                seats = validated_data['seats']
                for seat in seats:
                    # Update seat status
                    seat.status = Seat.Status.RESERVED
                    seat.save(update_fields=['status'])
                    
                    # Create reservation record
                    reservation = ReservedTicket.objects.create(
                        tenant=zone.tenant,
                        transaction=temp_transaction,
                        seat=seat,
                        zone=zone,
                        quantity=1,
                        reserved_until=reserved_until
                    )
                    reservations.append(reservation)
                    
                    # Invalidate seat cache
                    sales_cache.invalidate_seat_caches(seat)
            
            else:
                # Reserve general admission capacity
                quantity = validated_data['quantity']
                reservation = ReservedTicket.objects.create(
                    tenant=zone.tenant,
                    transaction=temp_transaction,
                    zone=zone,
                    quantity=quantity,
                    reserved_until=reserved_until
                )
                reservations.append(reservation)
                
                # Invalidate zone cache
                sales_cache.invalidate_zone_caches(zone)
        
        return {
            'transaction_id': temp_transaction.id,
            'reservations': reservations,
            'reserved_until': reserved_until
        }


class TransactionCompletionSerializer(serializers.Serializer):
    """Serializer for completing transactions and generating fiscal series."""
    
    transaction_id = serializers.UUIDField(help_text="Transaction ID to complete")
    
    def validate_transaction_id(self, value):
        """Validate transaction exists and can be completed."""
        try:
            transaction_obj = Transaction.objects.get(id=value)
            if not transaction_obj.can_be_completed():
                raise serializers.ValidationError(
                    f"Transaction cannot be completed. Current status: {transaction_obj.status}"
                )
            return transaction_obj
        except Transaction.DoesNotExist:
            raise serializers.ValidationError("Transaction not found")
    
    def save(self):
        """Complete the transaction and generate fiscal series."""
        transaction_obj = self.validated_data['transaction_id']
        
        with transaction.atomic():
            # Complete the transaction (generates fiscal series)
            completed_transaction = transaction_obj.complete()
            
            # Cache completed transaction tickets for validation
            sales_cache.cache_transaction_tickets(completed_transaction)
            
            # Invalidate related caches
            sales_cache.invalidate_transaction_caches(completed_transaction)
            
            return completed_transaction


class ReservedTicketSerializer(serializers.ModelSerializer):
    """Serializer for reserved tickets."""
    
    zone_name = serializers.CharField(source='zone.name', read_only=True)
    seat_label = serializers.CharField(source='seat.seat_label', read_only=True)
    is_active = serializers.ReadOnlyField()
    is_expired = serializers.ReadOnlyField()
    
    class Meta:
        model = ReservedTicket
        fields = [
            'id', 'transaction', 'seat', 'seat_label', 'zone', 'zone_name',
            'quantity', 'reserved_until', 'status', 'is_active', 'is_expired',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']