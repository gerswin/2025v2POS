"""
Cache utilities and decorators for sales operations.
Provides decorators and helper functions for caching with fallback to database.
"""

import functools
import logging
from typing import Callable, Any, Optional, Dict
from django.core.cache import cache
from django.db import models
from django.utils import timezone

from .cache import sales_cache

logger = logging.getLogger(__name__)


def cache_with_fallback(cache_key_func: Callable, ttl: int = 300, fallback_func: Optional[Callable] = None):
    """
    Decorator that caches function results with database fallback.
    
    Args:
        cache_key_func: Function to generate cache key from function args
        ttl: Time to live in seconds
        fallback_func: Optional fallback function if cache and main function fail
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            try:
                cache_key = cache_key_func(*args, **kwargs)
            except Exception as e:
                logger.warning(f"Failed to generate cache key: {e}")
                return func(*args, **kwargs)
            
            # Try to get from cache
            cached_result = sales_cache._safe_cache_get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Cache miss - execute function
            try:
                result = func(*args, **kwargs)
                
                # Cache the result
                sales_cache._safe_cache_set(cache_key, result, ttl)
                
                return result
                
            except Exception as e:
                logger.error(f"Function execution failed: {e}")
                
                # Try fallback function if provided
                if fallback_func:
                    try:
                        return fallback_func(*args, **kwargs)
                    except Exception as fallback_error:
                        logger.error(f"Fallback function failed: {fallback_error}")
                
                # Re-raise original exception
                raise e
        
        return wrapper
    return decorator


def invalidate_related_caches(model_instance: models.Model):
    """
    Invalidate caches related to a model instance.
    Called from model signals to maintain cache consistency.
    """
    from .models import Transaction, TransactionItem, ReservedTicket
    from ..zones.models import Seat, Zone
    from ..events.models import Event
    
    try:
        if isinstance(model_instance, Seat):
            sales_cache.invalidate_seat_caches(model_instance)
            
        elif isinstance(model_instance, Zone):
            sales_cache.invalidate_zone_caches(model_instance)
            
        elif isinstance(model_instance, Event):
            sales_cache.invalidate_event_caches(model_instance)
            
        elif isinstance(model_instance, Transaction):
            sales_cache.invalidate_transaction_caches(model_instance)
            
        elif isinstance(model_instance, TransactionItem):
            if model_instance.transaction:
                sales_cache.invalidate_transaction_caches(model_instance.transaction)
            
        elif isinstance(model_instance, ReservedTicket):
            if model_instance.seat:
                sales_cache.invalidate_seat_caches(model_instance.seat)
            if model_instance.zone:
                sales_cache.invalidate_zone_caches(model_instance.zone)
                
    except Exception as e:
        logger.error(f"Failed to invalidate caches for {model_instance}: {e}")


def get_seat_availability_cached(seat_id: str) -> Optional[Dict]:
    """
    Get seat availability with cache fallback to database.
    """
    # Try cache first
    cached_data = sales_cache.get_seat_availability(seat_id)
    if cached_data:
        return cached_data
    
    # Fallback to database
    try:
        from ..zones.models import Seat
        seat = Seat.objects.select_related('zone').get(id=seat_id)
        
        # Cache the result
        sales_cache.cache_seat_availability(seat)
        
        # Return fresh cache data
        return sales_cache.get_seat_availability(seat_id)
        
    except Seat.DoesNotExist:
        return None
    except Exception as e:
        logger.error(f"Failed to get seat availability for {seat_id}: {e}")
        return None


def get_zone_availability_cached(zone_id: str) -> Optional[Dict]:
    """
    Get zone availability with cache fallback to database.
    """
    return sales_cache.get_zone_seat_availability(zone_id)


def get_event_availability_cached(event_id: str) -> Optional[Dict]:
    """
    Get event availability with cache fallback to database.
    """
    # Try cache first
    cached_data = sales_cache.get_event_availability(event_id)
    if cached_data:
        return cached_data
    
    # Fallback to database
    try:
        from ..events.models import Event
        event = Event.objects.prefetch_related('zones__seats').get(id=event_id)
        
        # Rebuild cache
        return sales_cache.rebuild_event_availability_cache(event)
        
    except Event.DoesNotExist:
        return None
    except Exception as e:
        logger.error(f"Failed to get event availability for {event_id}: {e}")
        return None


def get_ticket_status_cached(fiscal_series: str) -> Optional[Dict]:
    """
    Get ticket status with cache fallback to database.
    """
    # Try cache first
    cached_data = sales_cache.get_ticket_status(fiscal_series)
    if cached_data:
        return cached_data
    
    # Fallback to database
    try:
        from .models import Transaction
        transaction = Transaction.objects.select_related(
            'event', 'customer'
        ).prefetch_related(
            'items__zone', 'items__seat'
        ).get(
            fiscal_series=fiscal_series,
            status=Transaction.Status.COMPLETED
        )
        
        # Cache the transaction tickets
        sales_cache.cache_transaction_tickets(transaction)
        
        # Return fresh cache data
        return sales_cache.get_ticket_status(fiscal_series)
        
    except Transaction.DoesNotExist:
        return None
    except Exception as e:
        logger.error(f"Failed to get ticket status for {fiscal_series}: {e}")
        return None