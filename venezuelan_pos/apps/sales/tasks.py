"""
Celery tasks for sales operations.
Handles asynchronous processing of non-critical operations.
"""

import logging
from celery import shared_task
from django.utils import timezone
from decimal import Decimal

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def process_transaction_completion(self, transaction_id):
    """
    Process transaction completion asynchronously.
    Handles notifications and non-critical operations.
    """
    try:
        from .models import Transaction
        from ..notifications.services import NotificationService
        from ..tickets.services import TicketGenerationService
        
        # Get transaction
        transaction_obj = Transaction.objects.select_related(
            'event', 'customer', 'tenant'
        ).get(id=transaction_id)
        
        logger.info(f"Processing completion for transaction {transaction_obj.fiscal_series}")
        
        # Generate digital tickets
        try:
            TicketGenerationService.generate_transaction_tickets(transaction_obj)
            logger.info(f"Digital tickets generated for transaction {transaction_obj.fiscal_series}")
        except Exception as e:
            logger.error(f"Failed to generate tickets for transaction {transaction_obj.fiscal_series}: {e}")
        
        # Send purchase confirmation email
        try:
            NotificationService.send_purchase_confirmation(transaction_obj)
            logger.info(f"Purchase confirmation sent for transaction {transaction_obj.fiscal_series}")
        except Exception as e:
            logger.error(f"Failed to send purchase confirmation for transaction {transaction_obj.fiscal_series}: {e}")
        
        # Send ticket delivery notification
        try:
            NotificationService.send_ticket_delivery(transaction_obj)
            logger.info(f"Ticket delivery notification sent for transaction {transaction_obj.fiscal_series}")
        except Exception as e:
            logger.error(f"Failed to send ticket delivery for transaction {transaction_obj.fiscal_series}: {e}")
        
        # Update transaction status to indicate completion processing is done
        transaction_obj.processing_completed_at = timezone.now()
        transaction_obj.save(update_fields=['processing_completed_at'])
        
        logger.info(f"Transaction completion processing finished for {transaction_obj.fiscal_series}")
        
    except Exception as e:
        logger.error(f"Error processing transaction completion {transaction_id}: {e}")
        # Retry with exponential backoff
        raise self.retry(countdown=60 * (2 ** self.request.retries))


@shared_task(bind=True, max_retries=2)
def update_sales_statistics(self, transaction_id):
    """
    Update sales statistics and analytics data.
    """
    try:
        from .models import Transaction
        from ..reports.services import AnalyticsService
        
        transaction_obj = Transaction.objects.select_related('event').get(id=transaction_id)
        
        # Update event statistics
        AnalyticsService.update_event_statistics(transaction_obj.event)
        
        # Update zone occupancy
        for item in transaction_obj.items.all():
            if item.zone:
                AnalyticsService.update_zone_occupancy(item.zone)
        
        logger.info(f"Statistics updated for transaction {transaction_obj.fiscal_series}")
        
    except Exception as e:
        logger.error(f"Error updating statistics for transaction {transaction_id}: {e}")
        raise self.retry(countdown=30 * (2 ** self.request.retries))


@shared_task
def cleanup_expired_reservations():
    """
    Clean up expired seat reservations.
    """
    try:
        from .models import ReservedTicket
        
        expired_count = ReservedTicket.objects.filter(
            status=ReservedTicket.Status.ACTIVE,
            reserved_until__lt=timezone.now()
        ).update(status=ReservedTicket.Status.EXPIRED)
        
        if expired_count > 0:
            logger.info(f"Cleaned up {expired_count} expired reservations")
        
    except Exception as e:
        logger.error(f"Error cleaning up expired reservations: {e}")


@shared_task
def cleanup_expired_cart_locks():
    """
    Clean up expired cart item locks.
    Runs every 5 minutes to free up locked items.
    """
    try:
        from .cart_lock_service import CartLockService
        
        expired_count = CartLockService.cleanup_expired_locks()
        
        if expired_count > 0:
            logger.info(f"Cleaned up {expired_count} expired cart locks")
        
        return expired_count
        
    except Exception as e:
        logger.error(f"Error cleaning up expired cart locks: {e}")
        return 0


@shared_task
def warm_pricing_cache(event_id):
    """
    Pre-warm pricing calculations cache for an event.
    """
    try:
        from ..events.models import Event
        from ..pricing.services import PricingCalculationService
        
        event = Event.objects.get(id=event_id)
        pricing_service = PricingCalculationService()
        
        # Pre-calculate pricing for all zones
        for zone in event.zones.filter(status='active'):
            pricing_service.calculate_zone_price(zone)
        
        logger.info(f"Pricing cache warmed for event {event.name}")
        
    except Exception as e:
        logger.error(f"Error warming pricing cache for event {event_id}: {e}")