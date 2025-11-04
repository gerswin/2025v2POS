"""
Serializers for pricing models and API endpoints.
"""

from rest_framework import serializers
from django.utils import timezone
from decimal import Decimal

from .models import PriceStage, RowPricing, PriceHistory, StageTransition
from .services import PricingCalculationService
from venezuelan_pos.apps.events.models import Event
from venezuelan_pos.apps.zones.models import Zone, Seat


class PriceStageSerializer(serializers.ModelSerializer):
    """Serializer for PriceStage model."""
    
    is_current = serializers.ReadOnlyField()
    is_upcoming = serializers.ReadOnlyField()
    is_past = serializers.ReadOnlyField()
    
    class Meta:
        model = PriceStage
        fields = [
            'id', 'event', 'zone', 'name', 'description', 'start_date', 'end_date',
            'quantity_limit', 'modifier_type', 'modifier_value', 'scope', 
            'stage_order', 'is_active', 'auto_transition', 'configuration',
            'is_current', 'is_upcoming', 'is_past', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate(self, data):
        """Validate price stage data."""
        # Check date range
        if data.get('start_date') and data.get('end_date'):
            if data['start_date'] >= data['end_date']:
                raise serializers.ValidationError({
                    'end_date': 'End date must be after start date'
                })
        
        # Check for overlapping stages
        event = data.get('event')
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        if event and start_date and end_date:
            overlapping_stages = PriceStage.objects.filter(
                event=event,
                is_active=True
            )
            
            # Exclude current instance if updating
            if self.instance:
                overlapping_stages = overlapping_stages.exclude(pk=self.instance.pk)
            
            for stage in overlapping_stages:
                if stage.start_date and stage.end_date:
                    if (start_date < stage.end_date and end_date > stage.start_date):
                        raise serializers.ValidationError({
                            'start_date': f'Date range overlaps with "{stage.name}" stage',
                            'end_date': f'Date range overlaps with "{stage.name}" stage'
                        })
        
        return data


class RowPricingSerializer(serializers.ModelSerializer):
    """Serializer for RowPricing model."""
    
    class Meta:
        model = RowPricing
        fields = [
            'id', 'zone', 'row_number', 'percentage_markup', 'name',
            'description', 'is_active', 'configuration', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate(self, data):
        """Validate row pricing data."""
        zone = data.get('zone')
        row_number = data.get('row_number')
        
        if zone and zone.zone_type != Zone.ZoneType.NUMBERED:
            raise serializers.ValidationError({
                'zone': 'Row pricing can only be applied to numbered zones'
            })
        
        if zone and zone.rows and row_number and row_number > zone.rows:
            raise serializers.ValidationError({
                'row_number': f'Row number cannot exceed zone rows ({zone.rows})'
            })
        
        return data


class PriceHistorySerializer(serializers.ModelSerializer):
    """Serializer for PriceHistory model."""
    
    event_name = serializers.CharField(source='event.name', read_only=True)
    zone_name = serializers.CharField(source='zone.name', read_only=True)
    price_stage_name = serializers.CharField(source='price_stage.name', read_only=True)
    
    class Meta:
        model = PriceHistory
        fields = [
            'id', 'event', 'event_name', 'zone', 'zone_name', 'price_stage',
            'price_stage_name', 'row_pricing', 'price_type', 'base_price',
            'markup_percentage', 'markup_amount', 'final_price',
            'calculation_date', 'row_number', 'seat_number',
            'calculation_details', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class PriceCalculationRequestSerializer(serializers.Serializer):
    """Serializer for price calculation requests."""
    
    event_id = serializers.UUIDField()
    zone_id = serializers.UUIDField()
    row_number = serializers.IntegerField(required=False, min_value=1)
    seat_number = serializers.IntegerField(required=False, min_value=1)
    calculation_date = serializers.DateTimeField(required=False)
    
    def validate(self, data):
        """Validate price calculation request."""
        try:
            event = Event.objects.get(id=data['event_id'])
            zone = Zone.objects.get(id=data['zone_id'], event=event)
        except Event.DoesNotExist:
            raise serializers.ValidationError({'event_id': 'Event not found'})
        except Zone.DoesNotExist:
            raise serializers.ValidationError({'zone_id': 'Zone not found'})
        
        # Validate row and seat numbers for numbered zones
        if zone.zone_type == Zone.ZoneType.NUMBERED:
            row_number = data.get('row_number')
            seat_number = data.get('seat_number')
            
            if row_number and zone.rows and row_number > zone.rows:
                raise serializers.ValidationError({
                    'row_number': f'Row number cannot exceed zone rows ({zone.rows})'
                })
            
            if seat_number and row_number:
                try:
                    seat = zone.seats.get(row_number=row_number, seat_number=seat_number)
                except Seat.DoesNotExist:
                    raise serializers.ValidationError({
                        'seat_number': f'Seat {seat_number} not found in row {row_number}'
                    })
        
        data['event'] = event
        data['zone'] = zone
        return data


class PriceCalculationResponseSerializer(serializers.Serializer):
    """Serializer for price calculation responses."""
    
    final_price = serializers.DecimalField(max_digits=10, decimal_places=2)
    base_price = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_markup_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    zone_name = serializers.CharField()
    zone_type = serializers.CharField()
    calculation_date = serializers.CharField()
    seat_label = serializers.CharField(required=False)
    row_number = serializers.IntegerField(required=False)
    
    # Price stage information
    stages = serializers.ListField(
        child=serializers.DictField(),
        required=False
    )
    
    # Row pricing information
    row_pricing = serializers.DictField(required=False)
    
    # Seat modifier information
    seat_modifier = serializers.DictField(required=False)


class PriceBreakdownSerializer(serializers.Serializer):
    """Serializer for detailed price breakdown."""
    
    event_id = serializers.UUIDField()
    zone_id = serializers.UUIDField()
    row_number = serializers.IntegerField(required=False)
    seat_number = serializers.IntegerField(required=False)
    calculation_date = serializers.DateTimeField(required=False)
    
    def to_representation(self, instance):
        """Convert price breakdown to response format."""
        service = PricingCalculationService()
        
        event_id = instance.get('event_id')
        zone_id = instance.get('zone_id')
        row_number = instance.get('row_number')
        seat_number = instance.get('seat_number')
        calculation_date = instance.get('calculation_date', timezone.now())
        
        try:
            event = Event.objects.get(id=event_id)
            zone = Zone.objects.get(id=zone_id, event=event)
        except (Event.DoesNotExist, Zone.DoesNotExist):
            return {}
        
        breakdown = service.get_price_breakdown(
            event=event,
            zone=zone,
            row_number=row_number,
            seat_number=seat_number,
            calculation_date=calculation_date
        )
        
        return breakdown


class BulkPriceCalculationSerializer(serializers.Serializer):
    """Serializer for bulk price calculations."""
    
    calculations = serializers.ListField(
        child=PriceCalculationRequestSerializer(),
        min_length=1,
        max_length=100  # Limit bulk operations
    )
    
    def validate_calculations(self, value):
        """Validate bulk calculation requests."""
        # Check for duplicate requests
        seen = set()
        for calc in value:
            key = (
                calc.get('event_id'),
                calc.get('zone_id'),
                calc.get('row_number'),
                calc.get('seat_number')
            )
            if key in seen:
                raise serializers.ValidationError(
                    'Duplicate calculation requests are not allowed'
                )
            seen.add(key)
        
        return value


class PriceStageListSerializer(serializers.ModelSerializer):
    """Simplified serializer for price stage lists."""
    
    is_current = serializers.ReadOnlyField()
    
    class Meta:
        model = PriceStage
        fields = [
            'id', 'name', 'start_date', 'end_date', 'modifier_type', 'modifier_value',
            'stage_order', 'is_active', 'is_current'
        ]


class RowPricingListSerializer(serializers.ModelSerializer):
    """Simplified serializer for row pricing lists."""
    
    class Meta:
        model = RowPricing
        fields = [
            'id', 'row_number', 'percentage_markup', 'name', 'is_active'
        ]


class StageTransitionSerializer(serializers.ModelSerializer):
    """Serializer for StageTransition model."""
    
    event_name = serializers.CharField(source='event.name', read_only=True)
    zone_name = serializers.CharField(source='zone.name', read_only=True)
    stage_from_name = serializers.CharField(source='stage_from.name', read_only=True)
    stage_to_name = serializers.CharField(source='stage_to.name', read_only=True)
    
    class Meta:
        model = StageTransition
        fields = [
            'id', 'event', 'event_name', 'zone', 'zone_name',
            'stage_from', 'stage_from_name', 'stage_to', 'stage_to_name',
            'trigger_reason', 'sold_quantity', 'transition_at',
            'metadata', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class StageStatusSerializer(serializers.Serializer):
    """Serializer for real-time stage status."""
    
    stage_id = serializers.UUIDField()
    name = serializers.CharField()
    scope = serializers.CharField()
    modifier_type = serializers.CharField()
    modifier_value = serializers.DecimalField(max_digits=10, decimal_places=2)
    start_date = serializers.DateTimeField()
    end_date = serializers.DateTimeField()
    quantity_limit = serializers.IntegerField(allow_null=True)
    sold_quantity = serializers.IntegerField()
    remaining_quantity = serializers.IntegerField()
    is_current = serializers.BooleanField()
    is_upcoming = serializers.BooleanField()
    is_past = serializers.BooleanField()
    should_transition = serializers.BooleanField()
    transition_trigger = serializers.CharField(allow_null=True)
    auto_transition = serializers.BooleanField()
    time_remaining = serializers.DictField()
    last_updated = serializers.DateTimeField()
    next_stage = serializers.DictField(allow_null=True)


class PurchaseValidationRequestSerializer(serializers.Serializer):
    """Serializer for purchase validation requests."""
    
    stage_id = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1, max_value=100)
    session_id = serializers.CharField(max_length=255)
    
    def validate_stage_id(self, value):
        """Validate that stage exists and is active."""
        try:
            stage = PriceStage.objects.get(id=value, is_active=True)
            return value
        except PriceStage.DoesNotExist:
            raise serializers.ValidationError('Stage not found or inactive')


class PurchaseConfirmationSerializer(serializers.Serializer):
    """Serializer for purchase confirmation."""
    
    stage_id = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1)
    session_id = serializers.CharField(max_length=255)
    revenue_amount = serializers.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        required=False,
        allow_null=True
    )


class EventStageOverviewSerializer(serializers.Serializer):
    """Serializer for event stage monitoring overview."""
    
    event_id = serializers.UUIDField()
    event_name = serializers.CharField()
    monitoring_timestamp = serializers.DateTimeField()
    event_wide_stages = serializers.ListField(
        child=StageStatusSerializer()
    )
    zone_specific_stages = serializers.DictField(
        child=serializers.ListField(child=StageStatusSerializer())
    )
    recent_transitions = serializers.ListField(
        child=serializers.DictField()
    )
    active_reservations = serializers.IntegerField()


class TransitionProcessingRequestSerializer(serializers.Serializer):
    """Serializer for manual transition processing requests."""
    
    event_id = serializers.UUIDField()
    zone_id = serializers.UUIDField(required=False, allow_null=True)
    
    def validate_event_id(self, value):
        """Validate that event exists."""
        try:
            Event.objects.get(id=value)
            return value
        except Event.DoesNotExist:
            raise serializers.ValidationError('Event not found')
    
    def validate(self, data):
        """Validate zone belongs to event if provided."""
        event_id = data.get('event_id')
        zone_id = data.get('zone_id')
        
        if zone_id and event_id:
            try:
                Zone.objects.get(id=zone_id, event_id=event_id)
            except Zone.DoesNotExist:
                raise serializers.ValidationError({
                    'zone_id': 'Zone not found in the specified event'
                })
        
        return data