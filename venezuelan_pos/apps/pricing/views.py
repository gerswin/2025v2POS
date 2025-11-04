"""
Views for pricing configuration and calculation endpoints.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from django.db import transaction
from decimal import Decimal

from .models import PriceStage, RowPricing, PriceHistory, StageTransition
from .serializers import (
    PriceStageSerializer, RowPricingSerializer, PriceHistorySerializer,
    PriceCalculationRequestSerializer, PriceCalculationResponseSerializer,
    PriceBreakdownSerializer, BulkPriceCalculationSerializer,
    PriceStageListSerializer, RowPricingListSerializer
)
from .services import PricingCalculationService
from .stage_automation import stage_automation
# Removed TenantPermission import - using standard permissions
from venezuelan_pos.apps.events.models import Event
from venezuelan_pos.apps.zones.models import Zone, Seat


class PriceStageViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing price stages.
    Provides CRUD operations for time-based pricing periods.
    """
    
    serializer_class = PriceStageSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['event', 'is_active', 'stage_order']
    ordering = ['stage_order', 'start_date']
    
    def get_queryset(self):
        """Filter price stages by tenant."""
        return PriceStage.objects.filter(
            tenant=self.request.user.tenant
        ).select_related('event')
    
    def get_serializer_class(self):
        """Use simplified serializer for list actions."""
        if self.action == 'list':
            return PriceStageListSerializer
        return PriceStageSerializer
    
    def perform_create(self, serializer):
        """Set tenant when creating price stage."""
        serializer.save(tenant=self.request.user.tenant)
    
    @action(detail=False, methods=['get'])
    def current_stages(self, request):
        """Get currently active price stages."""
        now = timezone.now()
        current_stages = self.get_queryset().filter(
            is_active=True,
            start_date__lte=now,
            end_date__gte=now
        )
        
        serializer = PriceStageListSerializer(current_stages, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def duplicate(self, request, pk=None):
        """Duplicate a price stage with new dates."""
        stage = self.get_object()
        
        # Get new dates from request
        start_date = request.data.get('start_date')
        end_date = request.data.get('end_date')
        name = request.data.get('name', f"{stage.name} (Copy)")
        
        if not start_date or not end_date:
            return Response(
                {'error': 'start_date and end_date are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create duplicate
        new_stage = PriceStage.objects.create(
            tenant=stage.tenant,
            event=stage.event,
            name=name,
            description=stage.description,
            start_date=start_date,
            end_date=end_date,
            modifier_type=stage.modifier_type,
            modifier_value=stage.modifier_value,
            stage_order=stage.stage_order + 1,
            is_active=True,
            configuration=stage.configuration
        )
        
        serializer = PriceStageSerializer(new_stage)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class RowPricingViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing row pricing.
    Provides CRUD operations for row-specific price modifiers.
    """
    
    serializer_class = RowPricingSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['zone', 'is_active', 'row_number']
    ordering = ['row_number']
    
    def get_queryset(self):
        """Filter row pricing by tenant."""
        return RowPricing.objects.filter(
            tenant=self.request.user.tenant
        ).select_related('zone', 'zone__event')
    
    def get_serializer_class(self):
        """Use simplified serializer for list actions."""
        if self.action == 'list':
            return RowPricingListSerializer
        return RowPricingSerializer
    
    def perform_create(self, serializer):
        """Set tenant when creating row pricing."""
        serializer.save(tenant=self.request.user.tenant)
    
    @action(detail=False, methods=['post'])
    def bulk_create(self, request):
        """Create row pricing for multiple rows at once."""
        zone_id = request.data.get('zone_id')
        rows_data = request.data.get('rows', [])
        
        if not zone_id or not rows_data:
            return Response(
                {'error': 'zone_id and rows data are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            zone = Zone.objects.get(
                id=zone_id,
                tenant=request.user.tenant
            )
        except Zone.DoesNotExist:
            return Response(
                {'error': 'Zone not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if zone.zone_type != Zone.ZoneType.NUMBERED:
            return Response(
                {'error': 'Row pricing can only be applied to numbered zones'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        created_rows = []
        with transaction.atomic():
            for row_data in rows_data:
                row_number = row_data.get('row_number')
                percentage_markup = row_data.get('percentage_markup', 0)
                name = row_data.get('name', '')
                
                if not row_number:
                    continue
                
                # Skip if row pricing already exists
                if RowPricing.objects.filter(zone=zone, row_number=row_number).exists():
                    continue
                
                row_pricing = RowPricing.objects.create(
                    tenant=request.user.tenant,
                    zone=zone,
                    row_number=row_number,
                    percentage_markup=percentage_markup,
                    name=name,
                    is_active=True
                )
                created_rows.append(row_pricing)
        
        serializer = RowPricingSerializer(created_rows, many=True)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class PriceHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing price history.
    Provides read-only access to price calculation audit trail.
    """
    
    serializer_class = PriceHistorySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['event', 'zone', 'price_type', 'calculation_date']
    ordering = ['-calculation_date', '-created_at']
    
    def get_queryset(self):
        """Filter price history by tenant."""
        return PriceHistory.objects.filter(
            tenant=self.request.user.tenant
        ).select_related('event', 'zone', 'price_stage', 'row_pricing')


class PriceCalculationViewSet(viewsets.ViewSet):
    """
    ViewSet for price calculations.
    Provides endpoints for calculating prices with different parameters.
    """
    
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def calculate(self, request):
        """Calculate price for a specific seat or zone."""
        serializer = PriceCalculationRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        event = data['event']
        zone = data['zone']
        row_number = data.get('row_number')
        seat_number = data.get('seat_number')
        calculation_date = data.get('calculation_date', timezone.now())
        
        # Check tenant access
        if event.tenant != request.user.tenant:
            return Response(
                {'error': 'Access denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        service = PricingCalculationService()
        
        # Calculate price based on parameters
        if seat_number and row_number and zone.zone_type == Zone.ZoneType.NUMBERED:
            try:
                seat = zone.seats.get(row_number=row_number, seat_number=seat_number)
                final_price, calculation_details = service.calculate_seat_price(
                    seat, calculation_date, create_history=True
                )
            except Seat.DoesNotExist:
                return Response(
                    {'error': f'Seat {seat_number} not found in row {row_number}'},
                    status=status.HTTP_404_NOT_FOUND
                )
        else:
            final_price, calculation_details = service.calculate_zone_price(
                zone, row_number, calculation_date, create_history=True
            )
        
        response_serializer = PriceCalculationResponseSerializer(calculation_details)
        return Response(response_serializer.data)
    
    @action(detail=False, methods=['post'])
    def bulk_calculate(self, request):
        """Calculate prices for multiple seats/zones at once."""
        serializer = BulkPriceCalculationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        calculations = serializer.validated_data['calculations']
        service = PricingCalculationService()
        results = []
        
        for calc_data in calculations:
            event = calc_data['event']
            zone = calc_data['zone']
            
            # Check tenant access
            if event.tenant != request.user.tenant:
                results.append({
                    'error': 'Access denied',
                    'event_id': str(event.id),
                    'zone_id': str(zone.id)
                })
                continue
            
            row_number = calc_data.get('row_number')
            seat_number = calc_data.get('seat_number')
            calculation_date = calc_data.get('calculation_date', timezone.now())
            
            try:
                if seat_number and row_number and zone.zone_type == Zone.ZoneType.NUMBERED:
                    seat = zone.seats.get(row_number=row_number, seat_number=seat_number)
                    final_price, calculation_details = service.calculate_seat_price(
                        seat, calculation_date, create_history=False
                    )
                else:
                    final_price, calculation_details = service.calculate_zone_price(
                        zone, row_number, calculation_date, create_history=False
                    )
                
                calculation_details['event_id'] = str(event.id)
                calculation_details['zone_id'] = str(zone.id)
                results.append(calculation_details)
                
            except Seat.DoesNotExist:
                results.append({
                    'error': f'Seat {seat_number} not found in row {row_number}',
                    'event_id': str(event.id),
                    'zone_id': str(zone.id),
                    'row_number': row_number,
                    'seat_number': seat_number
                })
            except Exception as e:
                results.append({
                    'error': str(e),
                    'event_id': str(event.id),
                    'zone_id': str(zone.id)
                })
        
        return Response({'results': results})
    
    @action(detail=False, methods=['post'])
    def breakdown(self, request):
        """Get detailed price breakdown for analysis."""
        serializer = PriceBreakdownSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        breakdown = serializer.to_representation(serializer.validated_data)
        
        if not breakdown:
            return Response(
                {'error': 'Event or zone not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        return Response(breakdown)
    
    @action(detail=False, methods=['get'])
    def current_stages(self, request):
        """Get current price stages for all events."""
        event_id = request.query_params.get('event_id')
        
        if event_id:
            try:
                event = Event.objects.get(
                    id=event_id,
                    tenant=request.user.tenant
                )
                service = PricingCalculationService()
                current_stage = service.get_current_price_stage(event)
                
                if current_stage:
                    serializer = PriceStageSerializer(current_stage)
                    return Response(serializer.data)
                else:
                    return Response({'message': 'No current price stage'})
                    
            except Event.DoesNotExist:
                return Response(
                    {'error': 'Event not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        # Get all current stages
        now = timezone.now()
        current_stages = PriceStage.objects.filter(
            tenant=request.user.tenant,
            is_active=True,
            start_date__lte=now,
            end_date__gte=now
        ).select_related('event')
        
        serializer = PriceStageSerializer(current_stages, many=True)
        return Response(serializer.data)


class StageTransitionViewSet(viewsets.ViewSet):
    """
    ViewSet for stage transition automation and monitoring.
    Provides real-time stage status and transition management.
    """
    
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def stage_status(self, request):
        """Get real-time status for a specific stage."""
        stage_id = request.query_params.get('stage_id')
        
        if not stage_id:
            return Response(
                {'error': 'stage_id parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            stage = PriceStage.objects.get(
                id=stage_id,
                tenant=request.user.tenant
            )
        except PriceStage.DoesNotExist:
            return Response(
                {'error': 'Stage not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get real-time status from automation service
        stage_status = stage_automation.get_stage_status_cached(stage)
        
        return Response(stage_status)
    
    @action(detail=False, methods=['get'])
    def event_overview(self, request):
        """Get comprehensive stage overview for an event."""
        event_id = request.query_params.get('event_id')
        
        if not event_id:
            return Response(
                {'error': 'event_id parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            event = Event.objects.get(
                id=event_id,
                tenant=request.user.tenant
            )
        except Event.DoesNotExist:
            return Response(
                {'error': 'Event not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get monitoring overview
        overview = stage_automation.get_monitoring_overview(event)
        
        return Response(overview)
    
    @action(detail=False, methods=['post'])
    def process_transitions(self, request):
        """Manually trigger transition processing for an event."""
        event_id = request.data.get('event_id')
        zone_id = request.data.get('zone_id')
        
        if not event_id:
            return Response(
                {'error': 'event_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            event = Event.objects.get(
                id=event_id,
                tenant=request.user.tenant
            )
        except Event.DoesNotExist:
            return Response(
                {'error': 'Event not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        zone = None
        if zone_id:
            try:
                zone = Zone.objects.get(
                    id=zone_id,
                    event=event
                )
            except Zone.DoesNotExist:
                return Response(
                    {'error': 'Zone not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        # Process transitions
        transitions = stage_automation.process_automatic_transitions(event, zone)
        
        response_data = {
            'event_id': str(event.id),
            'zone_id': str(zone.id) if zone else None,
            'transitions_processed': len(transitions),
            'transitions': [
                {
                    'id': str(trans.id),
                    'from_stage': trans.stage_from.name,
                    'to_stage': trans.stage_to.name if trans.stage_to else 'Final',
                    'trigger_reason': trans.trigger_reason,
                    'sold_quantity': trans.sold_quantity,
                    'transition_at': trans.transition_at.isoformat(),
                }
                for trans in transitions
            ]
        }
        
        return Response(response_data)
    
    @action(detail=False, methods=['post'])
    def validate_purchase(self, request):
        """Validate a purchase request against current stage limits."""
        stage_id = request.data.get('stage_id')
        quantity = request.data.get('quantity', 1)
        session_id = request.data.get('session_id')
        
        if not all([stage_id, session_id]):
            return Response(
                {'error': 'stage_id and session_id are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            stage = PriceStage.objects.get(
                id=stage_id,
                tenant=request.user.tenant
            )
        except PriceStage.DoesNotExist:
            return Response(
                {'error': 'Stage not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Validate purchase
        is_valid, validation_result = stage_automation.validate_concurrent_purchase(
            stage, quantity, session_id
        )
        
        if is_valid:
            return Response({
                'valid': True,
                'reservation': validation_result
            })
        else:
            return Response({
                'valid': False,
                'error': validation_result
            }, status=status.HTTP_409_CONFLICT)
    
    @action(detail=False, methods=['post'])
    def confirm_purchase(self, request):
        """Confirm a stage purchase and update tracking."""
        stage_id = request.data.get('stage_id')
        quantity = request.data.get('quantity', 1)
        session_id = request.data.get('session_id')
        revenue_amount = request.data.get('revenue_amount')
        
        if not all([stage_id, session_id]):
            return Response(
                {'error': 'stage_id and session_id are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            stage = PriceStage.objects.get(
                id=stage_id,
                tenant=request.user.tenant
            )
        except PriceStage.DoesNotExist:
            return Response(
                {'error': 'Stage not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Convert revenue amount to Decimal if provided
        if revenue_amount:
            try:
                revenue_amount = Decimal(str(revenue_amount))
            except (ValueError, TypeError):
                return Response(
                    {'error': 'Invalid revenue_amount format'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Confirm purchase
        success = stage_automation.confirm_stage_purchase(
            stage, quantity, session_id, revenue_amount
        )
        
        if success:
            return Response({
                'confirmed': True,
                'stage_id': str(stage.id),
                'quantity': quantity,
                'session_id': session_id
            })
        else:
            return Response(
                {'error': 'Failed to confirm purchase'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def transition_history(self, request):
        """Get transition history for an event or zone."""
        event_id = request.query_params.get('event_id')
        zone_id = request.query_params.get('zone_id')
        days = int(request.query_params.get('days', 30))
        
        if not event_id:
            return Response(
                {'error': 'event_id parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            event = Event.objects.get(
                id=event_id,
                tenant=request.user.tenant
            )
        except Event.DoesNotExist:
            return Response(
                {'error': 'Event not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        zone = None
        if zone_id:
            try:
                zone = Zone.objects.get(
                    id=zone_id,
                    event=event
                )
            except Zone.DoesNotExist:
                return Response(
                    {'error': 'Zone not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        # Get transition history
        since_date = timezone.now() - timezone.timedelta(days=days)
        
        queryset = StageTransition.objects.filter(
            event=event,
            transition_at__gte=since_date
        ).order_by('-transition_at')
        
        if zone:
            queryset = queryset.filter(zone=zone)
        
        transitions = list(queryset[:50])  # Limit to 50 most recent
        
        response_data = {
            'event_id': str(event.id),
            'zone_id': str(zone.id) if zone else None,
            'days': days,
            'total_transitions': len(transitions),
            'transitions': [
                {
                    'id': str(trans.id),
                    'from_stage': {
                        'id': str(trans.stage_from.id),
                        'name': trans.stage_from.name,
                    },
                    'to_stage': {
                        'id': str(trans.stage_to.id),
                        'name': trans.stage_to.name,
                    } if trans.stage_to else None,
                    'trigger_reason': trans.trigger_reason,
                    'sold_quantity': trans.sold_quantity,
                    'zone': trans.zone.name if trans.zone else 'Event-wide',
                    'transition_at': trans.transition_at.isoformat(),
                    'metadata': trans.metadata,
                }
                for trans in transitions
            ]
        }
        
        return Response(response_data)
    
    @action(detail=False, methods=['get'])
    def health_check(self, request):
        """Health check for the stage automation system."""
        health_status = stage_automation.health_check()
        
        http_status = status.HTTP_200_OK
        if health_status.get('status') == 'error':
            http_status = status.HTTP_500_INTERNAL_SERVER_ERROR
        elif health_status.get('status') == 'degraded':
            http_status = status.HTTP_206_PARTIAL_CONTENT
        
        return Response(health_status, status=http_status)