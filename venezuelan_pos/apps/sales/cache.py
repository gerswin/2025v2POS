"""
Redis-based caching service for sales operations.
Provides real-time ticket status caching, seat availability caching,
and cache invalidation for ticket purchases and payments.
"""

import json
import logging
from typing import Dict, List, Optional, Any, Union
from decimal import Decimal
from datetime import datetime, timedelta

from django.core.cache import cache
from django.conf import settings
from django.utils import timezone
from django.db import transaction

import redis
from redis.exceptions import ConnectionError, TimeoutError

from .models import Transaction, TransactionItem, ReservedTicket
from ..zones.models import Zone, Seat
from ..events.models import Event

logger = logging.getLogger(__name__)


class SalesCacheService:
    """
    Redis-based caching service for sales operations.
    Handles ticket validation cache, seat availability, and cache invalidation.
    """
    
    # Cache key prefixes
    TICKET_STATUS_PREFIX = "ticket_status"
    SEAT_AVAILABILITY_PREFIX = "seat_availability"
    ZONE_AVAILABILITY_PREFIX = "zone_availability"
    EVENT_AVAILABILITY_PREFIX = "event_availability"
    TRANSACTION_PREFIX = "transaction"
    RESERVED_TICKETS_PREFIX = "reserved_tickets"
    
    # Cache TTL settings (in seconds)
    TICKET_STATUS_TTL = 300  # 5 minutes
    SEAT_AVAILABILITY_TTL = 60  # 1 minute
    ZONE_AVAILABILITY_TTL = 120  # 2 minutes
    EVENT_AVAILABILITY_TTL = 180  # 3 minutes
    TRANSACTION_TTL = 1800  # 30 minutes
    RESERVED_TICKETS_TTL = 3600  # 1 hour
    
    def __init__(self):
        """Initialize the cache service."""
        self.cache = cache
        self._redis_client = None
        
        # Try to get direct Redis client for advanced operations
        try:
            if hasattr(cache, '_cache') and hasattr(cache._cache, '_client'):
                self._redis_client = cache._cache._client.get_client()
        except Exception as e:
            logger.warning(f"Could not get Redis client: {e}")
    
    def _get_cache_key(self, prefix: str, *args) -> str:
        """Generate cache key with prefix and arguments."""
        key_parts = [prefix] + [str(arg) for arg in args]
        return ":".join(key_parts)
    
    def _safe_cache_get(self, key: str, default=None) -> Any:
        """Safely get value from cache with fallback."""
        try:
            return self.cache.get(key, default)
        except (ConnectionError, TimeoutError) as e:
            logger.warning(f"Cache get failed for key {key}: {e}")
            return default
    
    def _safe_cache_set(self, key: str, value: Any, timeout: int = None) -> bool:
        """Safely set value in cache with fallback."""
        try:
            self.cache.set(key, value, timeout)
            return True
        except (ConnectionError, TimeoutError) as e:
            logger.warning(f"Cache set failed for key {key}: {e}")
            return False
    
    def _safe_cache_delete(self, key: str) -> bool:
        """Safely delete value from cache."""
        try:
            self.cache.delete(key)
            return True
        except (ConnectionError, TimeoutError) as e:
            logger.warning(f"Cache delete failed for key {key}: {e}")
            return False
    
    def _safe_cache_delete_pattern(self, pattern: str) -> bool:
        """Safely delete keys matching pattern."""
        try:
            if self._redis_client:
                keys = self._redis_client.keys(f"*{pattern}*")
                if keys:
                    self._redis_client.delete(*keys)
                return True
            else:
                # Fallback: we can't delete by pattern without Redis client
                logger.warning(f"Cannot delete pattern {pattern} without Redis client")
                return False
        except (ConnectionError, TimeoutError) as e:
            logger.warning(f"Cache pattern delete failed for pattern {pattern}: {e}")
            return False
    
    # Ticket Status Caching
    
    def get_ticket_status(self, fiscal_series: str) -> Optional[Dict]:
        """
        Get ticket status from cache.
        Returns ticket validation data or None if not cached.
        """
        key = self._get_cache_key(self.TICKET_STATUS_PREFIX, fiscal_series)
        return self._safe_cache_get(key)
    
    def set_ticket_status(self, fiscal_series: str, ticket_data: Dict) -> bool:
        """
        Cache ticket status with TTL.
        Stores ticket validation data for quick access.
        """
        key = self._get_cache_key(self.TICKET_STATUS_PREFIX, fiscal_series)
        return self._safe_cache_set(key, ticket_data, self.TICKET_STATUS_TTL)
    
    def invalidate_ticket_status(self, fiscal_series: str) -> bool:
        """Invalidate cached ticket status."""
        key = self._get_cache_key(self.TICKET_STATUS_PREFIX, fiscal_series)
        return self._safe_cache_delete(key)
    
    def cache_transaction_tickets(self, transaction: Transaction) -> bool:
        """
        Cache all tickets from a completed transaction.
        Called when transaction is completed to enable fast validation.
        """
        if not transaction.is_completed or not transaction.fiscal_series:
            return False
        
        try:
            # Prepare ticket data for caching
            ticket_data = {
                'transaction_id': str(transaction.id),
                'fiscal_series': transaction.fiscal_series,
                'event_id': str(transaction.event.id),
                'event_name': transaction.event.name,
                'customer_id': str(transaction.customer.id),
                'customer_name': transaction.customer.full_name,
                'total_amount': str(transaction.total_amount),
                'currency': transaction.currency,
                'completed_at': transaction.completed_at.isoformat(),
                'status': transaction.status,
                'items': []
            }
            
            # Add transaction items
            for item in transaction.items.all():
                item_data = {
                    'id': str(item.id),
                    'zone_id': str(item.zone.id),
                    'zone_name': item.zone.name,
                    'item_type': item.item_type,
                    'quantity': item.quantity,
                    'unit_price': str(item.unit_price),
                    'total_price': str(item.total_price),
                }
                
                if item.seat:
                    item_data.update({
                        'seat_id': str(item.seat.id),
                        'row_number': item.seat.row_number,
                        'seat_number': item.seat.seat_number,
                        'seat_label': item.seat.seat_label,
                    })
                
                ticket_data['items'].append(item_data)
            
            # Cache the ticket data
            return self.set_ticket_status(transaction.fiscal_series, ticket_data)
            
        except Exception as e:
            logger.error(f"Failed to cache transaction tickets for {transaction.fiscal_series}: {e}")
            return False
    
    # Seat Availability Caching
    
    def get_seat_availability(self, seat_id: str) -> Optional[Dict]:
        """Get seat availability status from cache."""
        key = self._get_cache_key(self.SEAT_AVAILABILITY_PREFIX, seat_id)
        return self._safe_cache_get(key)
    
    def set_seat_availability(self, seat_id: str, availability_data: Dict) -> bool:
        """Cache seat availability status."""
        key = self._get_cache_key(self.SEAT_AVAILABILITY_PREFIX, seat_id)
        return self._safe_cache_set(key, availability_data, self.SEAT_AVAILABILITY_TTL)
    
    def invalidate_seat_availability(self, seat_id: str) -> bool:
        """Invalidate cached seat availability."""
        key = self._get_cache_key(self.SEAT_AVAILABILITY_PREFIX, seat_id)
        return self._safe_cache_delete(key)
    
    def cache_seat_availability(self, seat: Seat) -> bool:
        """
        Cache seat availability data.
        Includes status, pricing, and reservation information.
        """
        try:
            availability_data = {
                'seat_id': str(seat.id),
                'zone_id': str(seat.zone.id),
                'row_number': seat.row_number,
                'seat_number': seat.seat_number,
                'seat_label': seat.seat_label,
                'status': seat.status,
                'is_available': seat.is_available,
                'calculated_price': str(seat.calculated_price),
                'price_modifier': str(seat.price_modifier),
                'updated_at': timezone.now().isoformat(),
            }
            
            # Check for active reservations
            active_reservations = ReservedTicket.objects.filter(
                seat=seat,
                status=ReservedTicket.Status.ACTIVE,
                reserved_until__gt=timezone.now()
            ).first()
            
            if active_reservations:
                availability_data.update({
                    'reserved_until': active_reservations.reserved_until.isoformat(),
                    'reservation_id': str(active_reservations.id),
                })
            
            return self.set_seat_availability(str(seat.id), availability_data)
            
        except Exception as e:
            logger.error(f"Failed to cache seat availability for seat {seat.id}: {e}")
            return False
    
    def get_zone_seat_availability(self, zone_id: str) -> Optional[Dict]:
        """Get all seat availability for a zone from cache."""
        key = self._get_cache_key(self.ZONE_AVAILABILITY_PREFIX, zone_id)
        cached_data = self._safe_cache_get(key)
        
        if cached_data:
            return cached_data
        
        # Cache miss - rebuild from database
        try:
            zone = Zone.objects.get(id=zone_id)
            return self.rebuild_zone_availability_cache(zone)
        except Zone.DoesNotExist:
            return None
    
    def rebuild_zone_availability_cache(self, zone: Zone) -> Dict:
        """
        Rebuild zone availability cache from database.
        Called on cache miss to ensure data consistency.
        """
        try:
            zone_data = {
                'zone_id': str(zone.id),
                'zone_name': zone.name,
                'zone_type': zone.zone_type,
                'capacity': zone.capacity,
                'available_capacity': zone.available_capacity,
                'sold_capacity': zone.sold_capacity,
                'is_sold_out': zone.is_sold_out,
                'base_price': str(zone.base_price),
                'updated_at': timezone.now().isoformat(),
                'seats': {}
            }
            
            if zone.zone_type == Zone.ZoneType.NUMBERED:
                # Cache individual seat data
                for seat in zone.seats.all():
                    seat_key = f"{seat.row_number}_{seat.seat_number}"
                    zone_data['seats'][seat_key] = {
                        'seat_id': str(seat.id),
                        'row_number': seat.row_number,
                        'seat_number': seat.seat_number,
                        'status': seat.status,
                        'is_available': seat.is_available,
                        'calculated_price': str(seat.calculated_price),
                    }
                    
                    # Also cache individual seat
                    self.cache_seat_availability(seat)
            
            # Cache zone data
            key = self._get_cache_key(self.ZONE_AVAILABILITY_PREFIX, str(zone.id))
            self._safe_cache_set(key, zone_data, self.ZONE_AVAILABILITY_TTL)
            
            return zone_data
            
        except Exception as e:
            logger.error(f"Failed to rebuild zone availability cache for zone {zone.id}: {e}")
            return {}
    
    # Event Availability Caching
    
    def get_event_availability(self, event_id: str) -> Optional[Dict]:
        """Get event availability summary from cache."""
        key = self._get_cache_key(self.EVENT_AVAILABILITY_PREFIX, event_id)
        return self._safe_cache_get(key)
    
    def rebuild_event_availability_cache(self, event: Event) -> Dict:
        """
        Rebuild event availability cache from database.
        Provides summary of all zones and overall availability.
        """
        try:
            event_data = {
                'event_id': str(event.id),
                'event_name': event.name,
                'event_status': event.status,
                'start_date': event.start_date.isoformat() if event.start_date else None,
                'total_capacity': 0,
                'available_capacity': 0,
                'sold_capacity': 0,
                'updated_at': timezone.now().isoformat(),
                'zones': {}
            }
            
            # Aggregate zone data
            for zone in event.zones.filter(status=Zone.Status.ACTIVE):
                zone_data = {
                    'zone_id': str(zone.id),
                    'zone_name': zone.name,
                    'zone_type': zone.zone_type,
                    'capacity': zone.capacity,
                    'available_capacity': zone.available_capacity,
                    'sold_capacity': zone.sold_capacity,
                    'is_sold_out': zone.is_sold_out,
                    'base_price': str(zone.base_price),
                }
                
                event_data['zones'][str(zone.id)] = zone_data
                event_data['total_capacity'] += zone.capacity
                event_data['available_capacity'] += zone.available_capacity
                event_data['sold_capacity'] += zone.sold_capacity
            
            # Cache event data
            key = self._get_cache_key(self.EVENT_AVAILABILITY_PREFIX, str(event.id))
            self._safe_cache_set(key, event_data, self.EVENT_AVAILABILITY_TTL)
            
            return event_data
            
        except Exception as e:
            logger.error(f"Failed to rebuild event availability cache for event {event.id}: {e}")
            return {}
    
    # Transaction Caching
    
    def get_transaction_cache(self, transaction_id: str) -> Optional[Dict]:
        """Get transaction data from cache."""
        key = self._get_cache_key(self.TRANSACTION_PREFIX, transaction_id)
        return self._safe_cache_get(key)
    
    def cache_transaction(self, transaction: Transaction) -> bool:
        """Cache transaction data for quick access."""
        try:
            transaction_data = {
                'id': str(transaction.id),
                'fiscal_series': transaction.fiscal_series,
                'event_id': str(transaction.event.id),
                'customer_id': str(transaction.customer.id),
                'status': transaction.status,
                'total_amount': str(transaction.total_amount),
                'currency': transaction.currency,
                'created_at': transaction.created_at.isoformat(),
                'completed_at': transaction.completed_at.isoformat() if transaction.completed_at else None,
                'updated_at': transaction.updated_at.isoformat(),
            }
            
            key = self._get_cache_key(self.TRANSACTION_PREFIX, str(transaction.id))
            return self._safe_cache_set(key, transaction_data, self.TRANSACTION_TTL)
            
        except Exception as e:
            logger.error(f"Failed to cache transaction {transaction.id}: {e}")
            return False
    
    # Cache Invalidation Methods
    
    def invalidate_seat_caches(self, seat: Seat) -> bool:
        """
        Invalidate all caches related to a seat.
        Called when seat status changes.
        """
        success = True
        
        # Invalidate individual seat cache
        success &= self.invalidate_seat_availability(str(seat.id))
        
        # Invalidate zone cache
        zone_key = self._get_cache_key(self.ZONE_AVAILABILITY_PREFIX, str(seat.zone.id))
        success &= self._safe_cache_delete(zone_key)
        
        # Invalidate event cache
        event_key = self._get_cache_key(self.EVENT_AVAILABILITY_PREFIX, str(seat.zone.event.id))
        success &= self._safe_cache_delete(event_key)
        
        return success
    
    def invalidate_zone_caches(self, zone: Zone) -> bool:
        """
        Invalidate all caches related to a zone.
        Called when zone configuration changes.
        """
        success = True
        
        # Invalidate zone cache
        zone_key = self._get_cache_key(self.ZONE_AVAILABILITY_PREFIX, str(zone.id))
        success &= self._safe_cache_delete(zone_key)
        
        # Invalidate event cache
        event_key = self._get_cache_key(self.EVENT_AVAILABILITY_PREFIX, str(zone.event.id))
        success &= self._safe_cache_delete(event_key)
        
        # Invalidate all seat caches in this zone
        if zone.zone_type == Zone.ZoneType.NUMBERED:
            for seat in zone.seats.all():
                success &= self.invalidate_seat_availability(str(seat.id))
        
        return success
    
    def invalidate_event_caches(self, event: Event) -> bool:
        """
        Invalidate all caches related to an event.
        Called when event configuration changes.
        """
        success = True
        
        # Invalidate event cache
        event_key = self._get_cache_key(self.EVENT_AVAILABILITY_PREFIX, str(event.id))
        success &= self._safe_cache_delete(event_key)
        
        # Invalidate all zone caches
        for zone in event.zones.all():
            success &= self.invalidate_zone_caches(zone)
        
        return success
    
    def invalidate_transaction_caches(self, transaction: Transaction) -> bool:
        """
        Invalidate all caches related to a transaction.
        Called when transaction status changes or payment is processed.
        """
        success = True
        
        # Invalidate transaction cache
        transaction_key = self._get_cache_key(self.TRANSACTION_PREFIX, str(transaction.id))
        success &= self._safe_cache_delete(transaction_key)
        
        # Invalidate ticket status cache if fiscal series exists
        if transaction.fiscal_series:
            success &= self.invalidate_ticket_status(transaction.fiscal_series)
        
        # Invalidate seat caches for all items
        for item in transaction.items.all():
            if item.seat:
                success &= self.invalidate_seat_caches(item.seat)
            else:
                # For general admission, invalidate zone cache
                success &= self.invalidate_zone_caches(item.zone)
        
        return success
    
    # Batch Operations
    
    def warm_event_caches(self, event: Event) -> bool:
        """
        Warm up all caches for an event.
        Useful for pre-loading popular events.
        """
        try:
            # Warm event availability cache
            self.rebuild_event_availability_cache(event)
            
            # Warm zone caches
            for zone in event.zones.filter(status=Zone.Status.ACTIVE):
                self.rebuild_zone_availability_cache(zone)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to warm caches for event {event.id}: {e}")
            return False
    
    def clear_all_caches(self) -> bool:
        """
        Clear all sales-related caches.
        Use with caution - will force database queries until caches rebuild.
        """
        try:
            patterns = [
                self.TICKET_STATUS_PREFIX,
                self.SEAT_AVAILABILITY_PREFIX,
                self.ZONE_AVAILABILITY_PREFIX,
                self.EVENT_AVAILABILITY_PREFIX,
                self.TRANSACTION_PREFIX,
                self.RESERVED_TICKETS_PREFIX,
            ]
            
            success = True
            for pattern in patterns:
                success &= self._safe_cache_delete_pattern(pattern)
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to clear all caches: {e}")
            return False
    
    # Health Check
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform cache health check.
        Returns status and performance metrics.
        """
        try:
            start_time = timezone.now()
            
            # Test basic cache operations
            test_key = "health_check_test"
            test_value = {"timestamp": start_time.isoformat()}
            
            # Test set
            set_success = self._safe_cache_set(test_key, test_value, 60)
            
            # Test get
            retrieved_value = self._safe_cache_get(test_key)
            get_success = retrieved_value == test_value
            
            # Test delete
            delete_success = self._safe_cache_delete(test_key)
            
            end_time = timezone.now()
            response_time = (end_time - start_time).total_seconds() * 1000  # ms
            
            return {
                'status': 'healthy' if (set_success and get_success and delete_success) else 'unhealthy',
                'response_time_ms': response_time,
                'operations': {
                    'set': set_success,
                    'get': get_success,
                    'delete': delete_success,
                },
                'redis_client_available': self._redis_client is not None,
                'timestamp': timezone.now().isoformat(),
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': timezone.now().isoformat(),
            }


# Global cache service instance
sales_cache = SalesCacheService()