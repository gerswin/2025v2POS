"""
Pricing calculation service with base + stage + row logic.
Implements the dynamic pricing engine for the Venezuelan POS system.
"""

from decimal import Decimal
from typing import Dict, Optional, Tuple
from django.utils import timezone
from django.db import transaction

from .models import PriceStage, RowPricing, PriceHistory, StageTransition, StageSales
from venezuelan_pos.apps.events.models import Event
from venezuelan_pos.apps.zones.models import Zone, Seat


class PricingCalculationService:
    """
    Service for calculating dynamic prices with base + stage + row logic.
    Handles all pricing calculations and maintains audit history.
    """
    
    def __init__(self):
        self.calculation_details = {}
    
    def calculate_seat_price(
        self,
        seat: Seat,
        calculation_date: Optional[timezone.datetime] = None,
        create_history: bool = True
    ) -> Tuple[Decimal, Dict]:
        """
        Calculate the final price for a specific seat.
        
        Args:
            seat: The seat to calculate price for
            calculation_date: Date to use for price stage calculation (defaults to now)
            create_history: Whether to create price history records
            
        Returns:
            Tuple of (final_price, calculation_details)
        """
        if calculation_date is None:
            calculation_date = timezone.now()
        
        zone = seat.zone
        event = zone.event
        
        # Start with zone base price
        base_price = zone.base_price
        calculation_details = {
            'base_price': base_price,
            'zone_name': zone.name,
            'seat_label': seat.seat_label,
            'calculation_date': calculation_date.isoformat(),
            'stages': []
        }
        
        # Apply price stage markup
        current_stage = self.get_current_price_stage(event, zone, calculation_date)
        stage_markup_amount = Decimal('0.00')
        price_after_stage = base_price
        
        if current_stage:
            stage_markup_amount = current_stage.calculate_modifier_amount(base_price)
            price_after_stage = current_stage.calculate_final_price(base_price)
            
            calculation_details['stages'].append({
                'stage_name': current_stage.name,
                'stage_modifier_type': current_stage.modifier_type,
                'stage_modifier_value': current_stage.modifier_value,
                'stage_markup_amount': stage_markup_amount,
                'price_after_stage': price_after_stage
            })
            
            if create_history:
                self._create_price_history(
                    event=event,
                    zone=zone,
                    price_stage=current_stage,
                    price_type=PriceHistory.PriceType.STAGE_MARKUP,
                    base_price=base_price,
                    markup_percentage=current_stage.modifier_value if current_stage.modifier_type == 'percentage' else Decimal('0.00'),
                    markup_amount=stage_markup_amount,
                    final_price=price_after_stage,
                    calculation_date=calculation_date,
                    row_number=seat.row_number,
                    seat_number=seat.seat_number,
                    calculation_details=calculation_details
                )
        
        # Apply row pricing markup
        row_pricing = self.get_row_pricing(zone, seat.row_number)
        row_markup_amount = Decimal('0.00')
        price_after_row = price_after_stage
        
        if row_pricing:
            row_markup_amount = row_pricing.calculate_markup_amount(price_after_stage)
            price_after_row = row_pricing.calculate_final_price(price_after_stage)
            
            calculation_details['row_pricing'] = {
                'row_number': seat.row_number,
                'row_markup_percentage': row_pricing.percentage_markup,
                'row_markup_amount': row_markup_amount,
                'price_after_row': price_after_row
            }
            
            if create_history:
                self._create_price_history(
                    event=event,
                    zone=zone,
                    row_pricing=row_pricing,
                    price_type=PriceHistory.PriceType.ROW_MARKUP,
                    base_price=price_after_stage,
                    markup_percentage=row_pricing.percentage_markup,
                    markup_amount=row_markup_amount,
                    final_price=price_after_row,
                    calculation_date=calculation_date,
                    row_number=seat.row_number,
                    seat_number=seat.seat_number,
                    calculation_details=calculation_details
                )
        
        # Apply individual seat price modifier if any
        seat_modifier_amount = Decimal('0.00')
        final_price = price_after_row
        
        if seat.price_modifier != 0:
            seat_modifier_amount = price_after_row * (seat.price_modifier / 100)
            final_price = price_after_row + seat_modifier_amount
            
            calculation_details['seat_modifier'] = {
                'seat_modifier_percentage': seat.price_modifier,
                'seat_modifier_amount': seat_modifier_amount,
                'final_price': final_price
            }
        
        calculation_details['final_price'] = final_price
        calculation_details['total_markup_amount'] = (
            stage_markup_amount + row_markup_amount + seat_modifier_amount
        )
        
        # Create final price history record
        if create_history:
            self._create_price_history(
                event=event,
                zone=zone,
                price_stage=current_stage,
                row_pricing=row_pricing,
                price_type=PriceHistory.PriceType.FINAL_CALCULATED,
                base_price=base_price,
                markup_percentage=Decimal('0.00'),  # Total markup is sum of individual markups
                markup_amount=calculation_details['total_markup_amount'],
                final_price=final_price,
                calculation_date=calculation_date,
                row_number=seat.row_number,
                seat_number=seat.seat_number,
                calculation_details=calculation_details
            )
        
        return final_price, calculation_details
    
    def calculate_zone_price(
        self,
        zone: Zone,
        row_number: Optional[int] = None,
        calculation_date: Optional[timezone.datetime] = None,
        create_history: bool = True
    ) -> Tuple[Decimal, Dict]:
        """
        Calculate price for a zone (general admission) or specific row in zone.
        
        Args:
            zone: The zone to calculate price for
            row_number: Specific row number (for numbered zones)
            calculation_date: Date to use for price stage calculation
            create_history: Whether to create price history records
            
        Returns:
            Tuple of (final_price, calculation_details)
        """
        if calculation_date is None:
            calculation_date = timezone.now()
        
        event = zone.event
        base_price = zone.base_price
        
        calculation_details = {
            'base_price': base_price,
            'zone_name': zone.name,
            'zone_type': zone.zone_type,
            'calculation_date': calculation_date.isoformat(),
            'stages': []
        }
        
        if row_number:
            calculation_details['row_number'] = row_number
        
        # Apply price stage markup
        current_stage = self.get_current_price_stage(event, zone, calculation_date)
        stage_markup_amount = Decimal('0.00')
        price_after_stage = base_price
        
        if current_stage:
            stage_markup_amount = current_stage.calculate_modifier_amount(base_price)
            price_after_stage = current_stage.calculate_final_price(base_price)
            
            calculation_details['stages'].append({
                'stage_name': current_stage.name,
                'stage_modifier_type': current_stage.modifier_type,
                'stage_modifier_value': current_stage.modifier_value,
                'stage_markup_amount': stage_markup_amount,
                'price_after_stage': price_after_stage
            })
        
        # Apply row pricing if specified and zone is numbered
        row_markup_amount = Decimal('0.00')
        final_price = price_after_stage
        
        if row_number and zone.zone_type == Zone.ZoneType.NUMBERED:
            row_pricing = self.get_row_pricing(zone, row_number)
            if row_pricing:
                row_markup_amount = row_pricing.calculate_markup_amount(price_after_stage)
                final_price = row_pricing.calculate_final_price(price_after_stage)
                
                calculation_details['row_pricing'] = {
                    'row_number': row_number,
                    'row_markup_percentage': row_pricing.percentage_markup,
                    'row_markup_amount': row_markup_amount,
                    'price_after_row': final_price
                }
        
        calculation_details['final_price'] = final_price
        calculation_details['total_markup_amount'] = stage_markup_amount + row_markup_amount
        
        # Create price history records if requested
        if create_history:
            if current_stage:
                self._create_price_history(
                    event=event,
                    zone=zone,
                    price_stage=current_stage,
                    price_type=PriceHistory.PriceType.STAGE_MARKUP,
                    base_price=base_price,
                    markup_percentage=current_stage.modifier_value,
                    markup_amount=stage_markup_amount,
                    final_price=price_after_stage,
                    calculation_date=calculation_date,
                    row_number=row_number,
                    calculation_details=calculation_details
                )
            
            if row_number and row_markup_amount > 0:
                row_pricing = self.get_row_pricing(zone, row_number)
                if row_pricing:
                    self._create_price_history(
                        event=event,
                        zone=zone,
                        row_pricing=row_pricing,
                        price_type=PriceHistory.PriceType.ROW_MARKUP,
                        base_price=price_after_stage,
                        markup_percentage=row_pricing.percentage_markup,
                        markup_amount=row_markup_amount,
                        final_price=final_price,
                        calculation_date=calculation_date,
                        row_number=row_number,
                        calculation_details=calculation_details
                    )
            
            # Final calculated price
            self._create_price_history(
                event=event,
                zone=zone,
                price_stage=current_stage,
                row_pricing=self.get_row_pricing(zone, row_number) if row_number else None,
                price_type=PriceHistory.PriceType.FINAL_CALCULATED,
                base_price=base_price,
                markup_percentage=Decimal('0.00'),
                markup_amount=calculation_details['total_markup_amount'],
                final_price=final_price,
                calculation_date=calculation_date,
                row_number=row_number,
                calculation_details=calculation_details
            )
        
        return final_price, calculation_details
    
    def get_current_price_stage(
        self,
        event: Event,
        zone: Optional[Zone] = None,
        calculation_date: Optional[timezone.datetime] = None
    ) -> Optional[PriceStage]:
        """
        Get the current active price stage for an event at a specific date.
        Now supports hybrid pricing with zone-specific stages.
        
        Args:
            event: The event to get price stage for
            zone: Specific zone for zone-specific stages
            calculation_date: Date to check (defaults to now)
            
        Returns:
            Current PriceStage or None if no active stage
        """
        if calculation_date is None:
            calculation_date = timezone.now()
        
        # Use hybrid pricing service for better stage resolution
        hybrid_service = HybridPricingService()
        return hybrid_service.get_current_stage(event, zone, calculation_date)
    
    def get_row_pricing(self, zone: Zone, row_number: int) -> Optional[RowPricing]:
        """
        Get row pricing configuration for a specific row in a zone.
        
        Args:
            zone: The zone to get row pricing for
            row_number: The row number
            
        Returns:
            RowPricing instance or None if no specific pricing
        """
        if zone.zone_type != Zone.ZoneType.NUMBERED:
            return None
        
        return RowPricing.objects.filter(
            zone=zone,
            row_number=row_number,
            is_active=True
        ).first()
    
    def get_price_breakdown(
        self,
        event: Event,
        zone: Zone,
        row_number: Optional[int] = None,
        seat_number: Optional[int] = None,
        calculation_date: Optional[timezone.datetime] = None
    ) -> Dict:
        """
        Get detailed price breakdown for analysis and display.
        
        Args:
            event: The event
            zone: The zone
            row_number: Row number (for numbered zones)
            seat_number: Seat number (for specific seat pricing)
            calculation_date: Date for calculation
            
        Returns:
            Detailed price breakdown dictionary
        """
        if calculation_date is None:
            calculation_date = timezone.now()
        
        if seat_number and row_number and zone.zone_type == Zone.ZoneType.NUMBERED:
            # Get specific seat pricing
            try:
                seat = zone.seats.get(row_number=row_number, seat_number=seat_number)
                final_price, details = self.calculate_seat_price(
                    seat, calculation_date, create_history=False
                )
                return details
            except zone.seats.model.DoesNotExist:
                pass
        
        # Get zone/row pricing
        final_price, details = self.calculate_zone_price(
            zone, row_number, calculation_date, create_history=False
        )
        return details
    
    def _convert_decimals_to_strings(self, data):
        """
        Recursively convert all Decimal values to strings for JSON serialization.
        Handles nested dictionaries, lists, and other data structures.

        Args:
            data: Data structure to convert (can be dict, list, Decimal, or other types)

        Returns:
            Converted data structure with all Decimals as strings
        """
        if isinstance(data, Decimal):
            return str(data)
        elif isinstance(data, dict):
            return {key: self._convert_decimals_to_strings(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [self._convert_decimals_to_strings(item) for item in data]
        elif isinstance(data, tuple):
            return tuple(self._convert_decimals_to_strings(item) for item in data)
        else:
            return data

    @transaction.atomic
    def _create_price_history(
        self,
        event: Event,
        zone: Zone,
        price_type: str,
        base_price: Decimal,
        markup_percentage: Decimal,
        markup_amount: Decimal,
        final_price: Decimal,
        calculation_date: timezone.datetime,
        price_stage: Optional[PriceStage] = None,
        row_pricing: Optional[RowPricing] = None,
        row_number: Optional[int] = None,
        seat_number: Optional[int] = None,
        calculation_details: Optional[Dict] = None
    ) -> PriceHistory:
        """
        Create a price history record for audit purposes.
        """
        # Convert all Decimal values to strings for JSON serialization
        serializable_details = self._convert_decimals_to_strings(calculation_details) if calculation_details else {}

        return PriceHistory.objects.create(
            tenant=event.tenant,
            event=event,
            zone=zone,
            price_stage=price_stage,
            row_pricing=row_pricing,
            price_type=price_type,
            base_price=base_price,
            markup_percentage=markup_percentage,
            markup_amount=markup_amount,
            final_price=final_price,
            calculation_date=calculation_date,
            row_number=row_number,
            seat_number=seat_number,
            calculation_details=serializable_details
        )


# Convenience functions for easy access
def calculate_seat_price(seat: Seat, calculation_date: Optional[timezone.datetime] = None) -> Tuple[Decimal, Dict]:
    """Calculate price for a specific seat."""
    service = PricingCalculationService()
    return service.calculate_seat_price(seat, calculation_date)


def calculate_zone_price(
    zone: Zone,
    row_number: Optional[int] = None,
    calculation_date: Optional[timezone.datetime] = None
) -> Tuple[Decimal, Dict]:
    """Calculate price for a zone or specific row."""
    service = PricingCalculationService()
    return service.calculate_zone_price(zone, row_number, calculation_date)


def get_current_price_stage(event: Event, calculation_date: Optional[timezone.datetime] = None) -> Optional[PriceStage]:
    """Get current price stage for an event."""
    service = PricingCalculationService()
    return service.get_current_price_stage(event, calculation_date)


def get_price_breakdown(
    event: Event,
    zone: Zone,
    row_number: Optional[int] = None,
    seat_number: Optional[int] = None,
    calculation_date: Optional[timezone.datetime] = None
) -> Dict:
    """Get detailed price breakdown."""
    service = PricingCalculationService()
    return service.get_price_breakdown(event, zone, row_number, seat_number, calculation_date)


class HybridPricingService:
    """
    Service for managing hybrid pricing stages with automatic transitions.
    Handles date and quantity-based stage transitions with real-time monitoring.
    """
    
    def __init__(self):
        pass
    
    def get_current_stage(
        self,
        event: Event,
        zone: Optional[Zone] = None,
        calculation_date: Optional[timezone.datetime] = None
    ) -> Optional[PriceStage]:
        """
        Get the current active price stage for an event or zone.
        Considers both date ranges and quantity limits for hybrid pricing.
        
        Args:
            event: The event to get stage for
            zone: Specific zone (for zone-specific stages)
            calculation_date: Date to check (defaults to now)
            
        Returns:
            Current active PriceStage or None
        """
        if calculation_date is None:
            calculation_date = timezone.now()
        
        # Determine scope and build query
        if zone:
            # Look for zone-specific stages first, then fall back to event-wide
            stage = PriceStage.objects.filter(
                event=event,
                zone=zone,
                scope=PriceStage.StageScope.ZONE_SPECIFIC,
                is_active=True,
                start_date__lte=calculation_date,
                end_date__gte=calculation_date
            ).order_by('stage_order').first()
            
            if stage and stage.is_current:
                return stage
        
        # Look for event-wide stages
        stage = PriceStage.objects.filter(
            event=event,
            zone__isnull=True,
            scope=PriceStage.StageScope.EVENT_WIDE,
            is_active=True,
            start_date__lte=calculation_date,
            end_date__gte=calculation_date
        ).order_by('stage_order').first()
        
        if stage and stage.is_current:
            return stage
        
        return None
    
    def check_and_process_transitions(
        self,
        event: Event,
        zone: Optional[Zone] = None
    ) -> list[StageTransition]:
        """
        Check for and process any pending stage transitions.
        
        Args:
            event: Event to check transitions for
            zone: Specific zone (for zone-specific stages)
            
        Returns:
            List of transitions that were processed
        """
        transitions = []
        
        # Get stages that might need transition
        stages_query = PriceStage.objects.filter(
            event=event,
            is_active=True,
            auto_transition=True
        )
        
        if zone:
            # Check zone-specific stages
            stages_query = stages_query.filter(
                zone=zone,
                scope=PriceStage.StageScope.ZONE_SPECIFIC
            )
        else:
            # Check event-wide stages
            stages_query = stages_query.filter(
                zone__isnull=True,
                scope=PriceStage.StageScope.EVENT_WIDE
            )
        
        for stage in stages_query:
            should_transition, reason = stage.should_transition()
            
            if should_transition:
                transition = self._process_stage_transition(stage, reason)
                if transition:
                    transitions.append(transition)
        
        return transitions
    
    @transaction.atomic
    def _process_stage_transition(
        self,
        stage: PriceStage,
        reason: str
    ) -> Optional[StageTransition]:
        """
        Process a single stage transition.
        
        Args:
            stage: Stage to transition from
            reason: Reason for transition
            
        Returns:
            Created StageTransition or None if no transition needed
        """
        next_stage = stage.get_next_stage()
        sold_quantity = stage.get_sold_quantity()
        
        # Create transition record
        transition = StageTransition.objects.create(
            tenant=stage.tenant,
            event=stage.event,
            zone=stage.zone,
            stage_from=stage,
            stage_to=next_stage,
            trigger_reason=reason,
            sold_quantity=sold_quantity,
            metadata={
                'stage_from_name': stage.name,
                'stage_to_name': next_stage.name if next_stage else 'Final Stage',
                'quantity_limit': stage.quantity_limit,
                'end_date': stage.end_date.isoformat(),
                'scope': stage.scope
            }
        )
        
        # Update stage sales if needed
        StageSales.update_sales_for_stage(
            stage=stage,
            zone=stage.zone,
            tickets_count=0,  # Just update cumulative totals
            revenue_amount=Decimal('0.00')
        )
        
        return transition
    
    def get_stage_status(
        self,
        stage: PriceStage,
        calculation_date: Optional[timezone.datetime] = None
    ) -> Dict:
        """
        Get comprehensive status information for a pricing stage.
        
        Args:
            stage: Stage to get status for
            calculation_date: Date for calculations
            
        Returns:
            Dictionary with stage status information
        """
        if calculation_date is None:
            calculation_date = timezone.now()
        
        sold_quantity = stage.get_sold_quantity()
        
        status = {
            'id': str(stage.id),
            'name': stage.name,
            'scope': stage.scope,
            'modifier_type': stage.modifier_type,
            'modifier_value': stage.modifier_value,
            'start_date': stage.start_date.isoformat(),
            'end_date': stage.end_date.isoformat(),
            'is_current': stage.is_current,
            'is_upcoming': stage.is_upcoming,
            'is_past': stage.is_past,
            'days_remaining': stage.days_remaining,
            'hours_remaining': stage.hours_remaining,
            'sold_quantity': sold_quantity,
            'auto_transition': stage.auto_transition
        }
        
        # Add quantity-related information
        if stage.quantity_limit:
            status.update({
                'quantity_limit': stage.quantity_limit,
                'remaining_quantity': stage.remaining_quantity,
                'quantity_percentage_sold': (sold_quantity / stage.quantity_limit * 100) if stage.quantity_limit > 0 else 0
            })
        else:
            status.update({
                'quantity_limit': None,
                'remaining_quantity': None,
                'quantity_percentage_sold': None
            })
        
        # Add next stage information
        next_stage = stage.get_next_stage()
        if next_stage:
            status['next_stage'] = {
                'name': next_stage.name,
                'modifier_type': next_stage.modifier_type,
                'modifier_value': next_stage.modifier_value,
                'start_date': next_stage.start_date.isoformat()
            }
        else:
            status['next_stage'] = None
        
        # Add transition trigger information
        should_transition, trigger_reason = stage.should_transition()
        status.update({
            'should_transition': should_transition,
            'transition_trigger': trigger_reason
        })
        
        return status
    
    def get_event_stage_overview(
        self,
        event: Event,
        calculation_date: Optional[timezone.datetime] = None
    ) -> Dict:
        """
        Get overview of all pricing stages for an event.
        
        Args:
            event: Event to get overview for
            calculation_date: Date for calculations
            
        Returns:
            Dictionary with event stage overview
        """
        if calculation_date is None:
            calculation_date = timezone.now()
        
        # Get event-wide stages
        event_stages = PriceStage.objects.filter(
            event=event,
            scope=PriceStage.StageScope.EVENT_WIDE,
            is_active=True
        ).order_by('stage_order')
        
        # Get zone-specific stages grouped by zone
        zone_stages = {}
        for zone in event.zones.all():
            zone_stage_list = PriceStage.objects.filter(
                event=event,
                zone=zone,
                scope=PriceStage.StageScope.ZONE_SPECIFIC,
                is_active=True
            ).order_by('stage_order')
            
            if zone_stage_list.exists():
                zone_stages[zone.name] = [
                    self.get_stage_status(stage, calculation_date)
                    for stage in zone_stage_list
                ]
        
        # Get current active stages
        current_event_stage = self.get_current_stage(event, None, calculation_date)
        current_zone_stages = {}
        for zone in event.zones.all():
            current_zone_stage = self.get_current_stage(event, zone, calculation_date)
            if current_zone_stage:
                current_zone_stages[zone.name] = self.get_stage_status(
                    current_zone_stage, calculation_date
                )
        
        return {
            'event_name': event.name,
            'calculation_date': calculation_date.isoformat(),
            'event_wide_stages': [
                self.get_stage_status(stage, calculation_date)
                for stage in event_stages
            ],
            'zone_specific_stages': zone_stages,
            'current_event_stage': (
                self.get_stage_status(current_event_stage, calculation_date)
                if current_event_stage else None
            ),
            'current_zone_stages': current_zone_stages
        }
    
    def record_ticket_sale(
        self,
        stage: PriceStage,
        zone: Optional[Zone] = None,
        tickets_count: int = 1,
        revenue_amount: Optional[Decimal] = None
    ) -> StageSales:
        """
        Record a ticket sale for stage tracking and transition monitoring.
        
        Args:
            stage: Stage the sale occurred in
            zone: Zone of the sale (for zone-specific tracking)
            tickets_count: Number of tickets sold
            revenue_amount: Revenue generated from the sale
            
        Returns:
            Updated StageSales record
        """
        # Update stage sales tracking
        sales_record = StageSales.update_sales_for_stage(
            stage=stage,
            zone=zone,
            tickets_count=tickets_count,
            revenue_amount=revenue_amount
        )
        
        # Check if this sale triggers a transition
        should_transition, reason = stage.should_transition()
        if should_transition and stage.auto_transition:
            self._process_stage_transition(stage, reason)
        
        return sales_record


class StageTransitionMonitoringService:
    """
    Service for monitoring and managing stage transitions.
    Provides real-time monitoring and automated transition processing.
    """
    
    def __init__(self):
        self.hybrid_service = HybridPricingService()
    
    def monitor_all_active_events(self) -> Dict:
        """
        Monitor all active events for pending transitions.
        
        Returns:
            Dictionary with monitoring results
        """
        from venezuelan_pos.apps.events.models import Event
        
        results = {
            'events_checked': 0,
            'transitions_processed': 0,
            'events_with_transitions': [],
            'errors': []
        }
        
        # Get all active events
        active_events = Event.objects.filter(
            status=Event.Status.ACTIVE,
            start_date__gt=timezone.now()  # Only future events
        )
        
        for event in active_events:
            try:
                results['events_checked'] += 1
                
                # Check event-wide transitions
                event_transitions = self.hybrid_service.check_and_process_transitions(event)
                
                # Check zone-specific transitions
                zone_transitions = []
                for zone in event.zones.all():
                    zone_trans = self.hybrid_service.check_and_process_transitions(event, zone)
                    zone_transitions.extend(zone_trans)
                
                all_transitions = event_transitions + zone_transitions
                
                if all_transitions:
                    results['transitions_processed'] += len(all_transitions)
                    results['events_with_transitions'].append({
                        'event_name': event.name,
                        'event_id': str(event.id),
                        'transitions': [
                            {
                                'from_stage': trans.stage_from.name,
                                'to_stage': trans.stage_to.name if trans.stage_to else 'Final',
                                'reason': trans.trigger_reason,
                                'zone': trans.zone.name if trans.zone else 'Event-wide'
                            }
                            for trans in all_transitions
                        ]
                    })
                
            except Exception as e:
                results['errors'].append({
                    'event_name': event.name,
                    'event_id': str(event.id),
                    'error': str(e)
                })
        
        return results
    
    def get_transition_history(
        self,
        event: Event,
        zone: Optional[Zone] = None,
        days: int = 30
    ) -> list[StageTransition]:
        """
        Get transition history for an event or zone.
        
        Args:
            event: Event to get history for
            zone: Specific zone (optional)
            days: Number of days to look back
            
        Returns:
            List of StageTransition records
        """
        since_date = timezone.now() - timezone.timedelta(days=days)
        
        queryset = StageTransition.objects.filter(
            event=event,
            transition_at__gte=since_date
        ).order_by('-transition_at')
        
        if zone:
            queryset = queryset.filter(zone=zone)
        
        return list(queryset)


# Convenience functions for hybrid pricing
def get_current_hybrid_stage(
    event: Event,
    zone: Optional[Zone] = None,
    calculation_date: Optional[timezone.datetime] = None
) -> Optional[PriceStage]:
    """Get current hybrid pricing stage."""
    service = HybridPricingService()
    return service.get_current_stage(event, zone, calculation_date)


def get_stage_status(
    stage: PriceStage,
    calculation_date: Optional[timezone.datetime] = None
) -> Dict:
    """Get comprehensive stage status."""
    service = HybridPricingService()
    return service.get_stage_status(stage, calculation_date)


def record_stage_sale(
    stage: PriceStage,
    zone: Optional[Zone] = None,
    tickets_count: int = 1,
    revenue_amount: Optional[Decimal] = None
) -> StageSales:
    """Record a ticket sale for stage tracking."""
    service = HybridPricingService()
    return service.record_ticket_sale(stage, zone, tickets_count, revenue_amount)


def monitor_stage_transitions() -> Dict:
    """Monitor all events for pending transitions."""
    service = StageTransitionMonitoringService()
    return service.monitor_all_active_events()