"""
Django signals for automatic cache invalidation.
Handles cache invalidation when models are saved, updated, or deleted.
"""

import logging
from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver

from .models import Transaction, TransactionItem, ReservedTicket
from .cache_utils import invalidate_related_caches
from .cache import sales_cache

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Transaction)
def transaction_post_save(sender, instance, created, **kwargs):
    """
    Handle transaction save events.
    Invalidate related caches and cache completed transactions.
    """
    try:
        # Always invalidate transaction caches
        invalidate_related_caches(instance)
        
        # Cache completed transactions for ticket validation
        if instance.is_completed and instance.fiscal_series:
            sales_cache.cache_transaction_tickets(instance)
            
        # Cache transaction data
        sales_cache.cache_transaction(instance)
        
    except Exception as e:
        logger.error(f"Error in transaction post_save signal: {e}")


@receiver(post_delete, sender=Transaction)
def transaction_post_delete(sender, instance, **kwargs):
    """Handle transaction deletion."""
    try:
        invalidate_related_caches(instance)
    except Exception as e:
        logger.error(f"Error in transaction post_delete signal: {e}")


@receiver(post_save, sender=TransactionItem)
def transaction_item_post_save(sender, instance, created, **kwargs):
    """Handle transaction item save events."""
    try:
        invalidate_related_caches(instance)
    except Exception as e:
        logger.error(f"Error in transaction_item post_save signal: {e}")


@receiver(post_delete, sender=TransactionItem)
def transaction_item_post_delete(sender, instance, **kwargs):
    """Handle transaction item deletion."""
    try:
        invalidate_related_caches(instance)
    except Exception as e:
        logger.error(f"Error in transaction_item post_delete signal: {e}")


@receiver(post_save, sender=ReservedTicket)
def reserved_ticket_post_save(sender, instance, created, **kwargs):
    """Handle reserved ticket save events."""
    try:
        invalidate_related_caches(instance)
    except Exception as e:
        logger.error(f"Error in reserved_ticket post_save signal: {e}")


@receiver(post_delete, sender=ReservedTicket)
def reserved_ticket_post_delete(sender, instance, **kwargs):
    """Handle reserved ticket deletion."""
    try:
        invalidate_related_caches(instance)
    except Exception as e:
        logger.error(f"Error in reserved_ticket post_delete signal: {e}")


# Import and register signals for related models
from ..zones.models import Seat, Zone
from ..events.models import Event


@receiver(post_save, sender=Seat)
def seat_post_save(sender, instance, created, **kwargs):
    """Handle seat save events."""
    try:
        invalidate_related_caches(instance)
        
        # Cache seat availability for quick access
        sales_cache.cache_seat_availability(instance)
        
    except Exception as e:
        logger.error(f"Error in seat post_save signal: {e}")


@receiver(post_delete, sender=Seat)
def seat_post_delete(sender, instance, **kwargs):
    """Handle seat deletion."""
    try:
        invalidate_related_caches(instance)
    except Exception as e:
        logger.error(f"Error in seat post_delete signal: {e}")


@receiver(post_save, sender=Zone)
def zone_post_save(sender, instance, created, **kwargs):
    """Handle zone save events."""
    try:
        invalidate_related_caches(instance)
    except Exception as e:
        logger.error(f"Error in zone post_save signal: {e}")


@receiver(post_delete, sender=Zone)
def zone_post_delete(sender, instance, **kwargs):
    """Handle zone deletion."""
    try:
        invalidate_related_caches(instance)
    except Exception as e:
        logger.error(f"Error in zone post_delete signal: {e}")


@receiver(post_save, sender=Event)
def event_post_save(sender, instance, created, **kwargs):
    """Handle event save events."""
    try:
        invalidate_related_caches(instance)
    except Exception as e:
        logger.error(f"Error in event post_save signal: {e}")


@receiver(post_delete, sender=Event)
def event_post_delete(sender, instance, **kwargs):
    """Handle event deletion."""
    try:
        invalidate_related_caches(instance)
    except Exception as e:
        logger.error(f"Error in event post_delete signal: {e}")