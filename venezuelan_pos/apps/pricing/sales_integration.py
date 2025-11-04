"""
Integration service between pricing stage automation and sales process.
Handles stage validation during purchases and automatic stage updates.
"""

import logging
from typing import Dict, List, Optional, Tuple
from decimal import Decimal
from django.utils import timezone
from django.db import transaction

from .stage_automation import stage_automation
from .models import PriceStage, StageSales
from .services import HybridPricingService
from ..sales.models import Transaction, TransactionItem
from ..zones.models import Zone, Seat

logger = logging.getLogger(__name__)


class StagePricingIntegrationService:
    """
    Service for integrating stage pricing with the sales process.
    Handles validation, price calculation, and stage updates during purchases.
    """
    
    def __init__(self):
        self.hybrid_service = HybridPricingService()
    
    def validate_purchase_with_stages(
        self,
        event,
        items_data: List[Dict],
        session_id: str
    ) -> Tuple[bool, Dict]:
        """
        Validate a purchase request against current pricing stages.
        
        Args:
            event: Event being purchased for
            items_data: List of items to purchase (zone, seat, quantity)
            session_id: Unique session ID for this purchase
            
        Returns:
            Tuple of (is_valid, validation_result)
        """
        try:
            validation_results = {
                'valid': True,
                'stage_validations': [],
                'total_reservations': 0,
                'errors': []
            }
            
            # Group items by zone to validate stage limits
            zone_quantities = {}
            for item_data in items_data:
                zone_id = item_data.get('zone_id')
                quantity = item_data.get('quantity', 1)
                
                if zone_id not in zone_quantities:
                    zone_quantities[zone_id] = 0
                zone_quantities[zone_id] += quantity
            
            # Validate each zone's stage limits
            for zone_id, total_quantity in zone_quantities.items():
                try:
                    zone = Zone.objects.get(id=zone_id, event=event)
                    
                    # Get current stage for this zone
                    current_stage = self.hybrid_service.get_current_stage(
                        event, zone, timezone.now()
                    )
                    
                    if not current_stage:
                        # No active stage - use event-wide stage
                        current_stage = self.hybrid_service.get_current_stage(
                            event, None, timezone.now()
                        )
                    
                    if current_stage:
                        # Validate against stage limits
                        is_valid, stage_result = stage_automation.validate_concurrent_purchase(
                            current_stage, total_quantity, f"{session_id}_{zone_id}"
                        )
                        
                        if is_valid:
                            validation_results['stage_validations'].append({
                                'zone_id': str(zone_id),
                                'zone_name': zone.name,
                                'stage_id': str(current_stage.id),
                                'stage_name': current_stage.name,
                                'quantity': total_quantity,
                                'reservation': stage_result
                            })
                            validation_results['total_reservations'] += total_quantity
                        else:
                            validation_results['valid'] = False
                            validation_results['errors'].append({
                                'zone_id': str(zone_id),
                                'zone_name': zone.name,
                                'error': stage_result.get('error'),
                                'details': stage_result
                            })
                    
                except Zone.DoesNotExist:
                    validation_results['valid'] = False
                    validation_results['errors'].append({
                        'zone_id': str(zone_id),
                        'error': 'Zone not found'
                    })
            
            return validation_results['valid'], validation_results
            
        except Exception as e:
            logger.error(f"Stage validation failed: {e}")
            return False, {
                'valid': False,
                'error': 'Stage validation failed',
                'details': str(e)
            }
    
    def calculate_stage_prices(
        self,
        event,
        items_data: List[Dict],
        calculation_date: Optional[timezone.datetime] = None
    ) -> Dict:
        """
        Calculate prices for items using current pricing stages.
        
        Args:
            event: Event for price calculation
            items_data: List of items with zone/seat information
            calculation_date: Date for price calculation (defaults to now)
            
        Returns:
            Dictionary with price calculations for each item
        """
        if calculation_date is None:
            calculation_date = timezone.now()
        
        from ..pricing.services import PricingCalculationService
        pricing_service = PricingCalculationService()
        
        results = {
            'calculation_date': calculation_date.isoformat(),
            'items': [],
            'total_amount': Decimal('0.00'),
            'stage_info': {}
        }
        
        for i, item_data in enumerate(items_data):
            try:
                zone_id = item_data.get('zone_id')
                seat_id = item_data.get('seat_id')
                row_number = item_data.get('row_number')
                seat_number = item_data.get('seat_number')
                quantity = item_data.get('quantity', 1)
                
                zone = Zone.objects.get(id=zone_id, event=event)
                
                # Calculate price based on seat or zone
                if seat_id:
                    seat = Seat.objects.get(id=seat_id, zone=zone)
                    final_price, calculation_details = pricing_service.calculate_seat_price(
                        seat, calculation_date, create_history=False
                    )
                elif row_number and seat_number:
                    seat = zone.seats.get(row_number=row_number, seat_number=seat_number)
                    final_price, calculation_details = pricing_service.calculate_seat_price(
                        seat, calculation_date, create_history=False
                    )
                else:
                    # General admission or zone pricing
                    final_price, calculation_details = pricing_service.calculate_zone_price(
                        zone, row_number, calculation_date, create_history=False
                    )
                
                # Calculate item total
                item_total = final_price * quantity
                
                item_result = {
                    'index': i,
                    'zone_id': str(zone_id),
                    'zone_name': zone.name,
                    'quantity': quantity,
                    'unit_price': str(final_price),
                    'total_price': str(item_total),
                    'calculation_details': calculation_details
                }
                
                if seat_id or (row_number and seat_number):
                    item_result.update({
                        'seat_id': str(seat_id) if seat_id else None,
                        'row_number': row_number,
                        'seat_number': seat_number,
                        'seat_label': seat.seat_label if 'seat' in locals() else None
                    })
                
                results['items'].append(item_result)
                results['total_amount'] += item_total
                
                # Track stage information
                if calculation_details.get('stages'):
                    for stage_info in calculation_details['stages']:
                        stage_name = stage_info.get('stage_name')
                        if stage_name not in results['stage_info']:
                            results['stage_info'][stage_name] = {
                                'stage_name': stage_name,
                                'modifier_type': stage_info.get('stage_modifier_type'),
                                'modifier_value': stage_info.get('stage_modifier_value'),
                                'items_count': 0,
                                'total_quantity': 0
                            }
                        
                        results['stage_info'][stage_name]['items_count'] += 1
                        results['stage_info'][stage_name]['total_quantity'] += quantity
                
            except Exception as e:
                logger.error(f"Price calculation failed for item {i}: {e}")
                results['items'].append({
                    'index': i,
                    'error': str(e),
                    'item_data': item_data
                })
        
        # Convert total to string for JSON serialization
        results['total_amount'] = str(results['total_amount'])
        
        return results
    
    def confirm_stage_purchases(
        self,
        transaction: Transaction,
        session_id: str
    ) -> bool:
        """
        Confirm stage purchases after transaction completion.
        Updates stage sales tracking and triggers transitions if needed.
        
        Args:
            transaction: Completed transaction
            session_id: Session ID used for reservations
            
        Returns:
            True if confirmation successful
        """
        try:
            with transaction.atomic():
                # Group items by zone and stage
                zone_stage_quantities = {}
                
                for item in transaction.items.all():
                    zone = item.zone
                    
                    # Get the stage that was active when transaction was created
                    current_stage = self.hybrid_service.get_current_stage(
                        transaction.event, zone, transaction.created_at
                    )
                    
                    if not current_stage:
                        # Try event-wide stage
                        current_stage = self.hybrid_service.get_current_stage(
                            transaction.event, None, transaction.created_at
                        )
                    
                    if current_stage:
                        stage_key = (current_stage.id, zone.id if zone else None)
                        
                        if stage_key not in zone_stage_quantities:
                            zone_stage_quantities[stage_key] = {
                                'stage': current_stage,
                                'zone': zone,
                                'quantity': 0,
                                'revenue': Decimal('0.00')
                            }
                        
                        zone_stage_quantities[stage_key]['quantity'] += item.quantity
                        zone_stage_quantities[stage_key]['revenue'] += item.total_price
                
                # Confirm purchases for each stage
                for stage_data in zone_stage_quantities.values():
                    stage = stage_data['stage']
                    zone = stage_data['zone']
                    quantity = stage_data['quantity']
                    revenue = stage_data['revenue']
                    
                    # Confirm the purchase
                    success = stage_automation.confirm_stage_purchase(
                        stage, quantity, f"{session_id}_{zone.id if zone else 'event'}", revenue
                    )
                    
                    if not success:
                        logger.warning(
                            f"Failed to confirm stage purchase for stage {stage.id}, "
                            f"transaction {transaction.id}"
                        )
                
                return True
                
        except Exception as e:
            logger.error(f"Failed to confirm stage purchases for transaction {transaction.id}: {e}")
            return False
    
    def get_current_stage_pricing(self, event, zone: Optional[Zone] = None) -> Dict:
        """
        Get current stage pricing information for display.
        
        Args:
            event: Event to get pricing for
            zone: Optional zone for zone-specific pricing
            
        Returns:
            Dictionary with current stage pricing information
        """
        try:
            current_stage = self.hybrid_service.get_current_stage(event, zone)
            
            if not current_stage:
                return {
                    'has_active_stage': False,
                    'message': 'No active pricing stage'
                }
            
            # Get stage status from automation service
            stage_status = stage_automation.get_stage_status_cached(current_stage)
            
            return {
                'has_active_stage': True,
                'stage': {
                    'id': str(current_stage.id),
                    'name': current_stage.name,
                    'description': current_stage.description,
                    'modifier_type': current_stage.modifier_type,
                    'modifier_value': str(current_stage.modifier_value),
                    'scope': current_stage.scope,
                },
                'status': stage_status,
                'zone_id': str(zone.id) if zone else None,
                'zone_name': zone.name if zone else None,
            }
            
        except Exception as e:
            logger.error(f"Failed to get current stage pricing: {e}")
            return {
                'has_active_stage': False,
                'error': str(e)
            }
    
    def handle_stage_transition_during_purchase(
        self,
        event,
        zone: Optional[Zone] = None
    ) -> Dict:
        """
        Handle stage transitions that occur during active purchase sessions.
        
        Args:
            event: Event to check transitions for
            zone: Optional zone for zone-specific transitions
            
        Returns:
            Dictionary with transition information
        """
        try:
            # Process any pending transitions
            transitions = stage_automation.process_automatic_transitions(event, zone)
            
            if not transitions:
                return {
                    'transitions_occurred': False,
                    'message': 'No transitions processed'
                }
            
            # Get new current stage after transitions
            new_current_stage = self.hybrid_service.get_current_stage(event, zone)
            
            result = {
                'transitions_occurred': True,
                'transitions_count': len(transitions),
                'transitions': [
                    {
                        'from_stage': trans.stage_from.name,
                        'to_stage': trans.stage_to.name if trans.stage_to else 'Final',
                        'trigger_reason': trans.trigger_reason,
                        'sold_quantity': trans.sold_quantity,
                    }
                    for trans in transitions
                ],
                'new_current_stage': None
            }
            
            if new_current_stage:
                result['new_current_stage'] = {
                    'id': str(new_current_stage.id),
                    'name': new_current_stage.name,
                    'modifier_type': new_current_stage.modifier_type,
                    'modifier_value': str(new_current_stage.modifier_value),
                }
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to handle stage transition during purchase: {e}")
            return {
                'transitions_occurred': False,
                'error': str(e)
            }


# Global integration service instance
stage_pricing_integration = StagePricingIntegrationService()