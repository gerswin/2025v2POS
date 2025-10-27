"""
Pricing calculation service with base + stage + row logic.
Implements the dynamic pricing engine for the Venezuelan POS system.
"""

from decimal import Decimal
from typing import Dict, Optional, Tuple
from django.utils import timezone
from django.db import transaction

from .models import PriceStage, RowPricing, PriceHistory
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
        current_stage = self.get_current_price_stage(event, calculation_date)
        stage_markup_amount = Decimal('0.00')
        price_after_stage = base_price
        
        if current_stage:
            stage_markup_amount = current_stage.calculate_markup_amount(base_price)
            price_after_stage = current_stage.calculate_final_price(base_price)
            
            calculation_details['stages'].append({
                'stage_name': current_stage.name,
                'stage_markup_percentage': current_stage.percentage_markup,
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
                    markup_percentage=current_stage.percentage_markup,
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
        current_stage = self.get_current_price_stage(event, calculation_date)
        stage_markup_amount = Decimal('0.00')
        price_after_stage = base_price
        
        if current_stage:
            stage_markup_amount = current_stage.calculate_markup_amount(base_price)
            price_after_stage = current_stage.calculate_final_price(base_price)
            
            calculation_details['stages'].append({
                'stage_name': current_stage.name,
                'stage_markup_percentage': current_stage.percentage_markup,
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
                    markup_percentage=current_stage.percentage_markup,
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
        calculation_date: Optional[timezone.datetime] = None
    ) -> Optional[PriceStage]:
        """
        Get the current active price stage for an event at a specific date.
        
        Args:
            event: The event to get price stage for
            calculation_date: Date to check (defaults to now)
            
        Returns:
            Current PriceStage or None if no active stage
        """
        if calculation_date is None:
            calculation_date = timezone.now()
        
        return PriceStage.objects.filter(
            event=event,
            is_active=True,
            start_date__lte=calculation_date,
            end_date__gte=calculation_date
        ).first()
    
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
        # Convert Decimal values to strings for JSON serialization
        if calculation_details:
            serializable_details = {}
            for key, value in calculation_details.items():
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
                else:
                    serializable_details[key] = value
        else:
            serializable_details = {}
        
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