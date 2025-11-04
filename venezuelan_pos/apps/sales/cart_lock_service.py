"""
Cart item locking service for preventing overselling.
"""

import logging
from datetime import timedelta
from typing import List, Dict, Optional, Tuple
from decimal import Decimal
from django.utils import timezone
from django.db import transaction
from django.core.cache import cache
from django.conf import settings

from .models_cart_lock import CartItemLock
from ..zones.models import Zone, Seat
from ..tenants.models import User

logger = logging.getLogger(__name__)


class CartLockService:
    """Service for managing cart item locks to prevent overselling."""
    
    # Configuration
    DEFAULT_LOCK_DURATION_MINUTES = getattr(settings, 'CART_LOCK_DURATION_MINUTES', 15)
    MAX_LOCKS_PER_SESSION = getattr(settings, 'MAX_LOCKS_PER_SESSION', 50)
    LOCK_WARNING_MINUTES = getattr(settings, 'CART_LOCK_WARNING_MINUTES', 2)
    
    @classmethod
    def lock_items(cls, session_key: str, user: Optional[User], items_data: List[Dict]) -> Tuple[bool, List[CartItemLock], List[str]]:
        """
        Lock items when adding to cart.
        
        Args:
            session_key: Django session key
            user: Authenticated user (optional)
            items_data: List of items to lock [{'zone_id': str, 'seat_id': str, 'quantity': int}]
        
        Returns:
            Tuple of (success, created_locks, error_messages)
        """
        
        created_locks = []
        error_messages = []
        
        try:
            with transaction.atomic():
                # Check session lock limit
                existing_locks_count = CartItemLock.objects.get_active_locks(
                    session_key=session_key
                ).count()
                
                if existing_locks_count + len(items_data) > cls.MAX_LOCKS_PER_SESSION:
                    error_messages.append(
                        f"Maximum {cls.MAX_LOCKS_PER_SESSION} items can be locked per session"
                    )
                    return False, [], error_messages
                
                for item_data in items_data:
                    zone_id = item_data.get('zone_id')
                    seat_id = item_data.get('seat_id')
                    quantity = item_data.get('quantity', 1)
                    
                    if not zone_id:
                        error_messages.append("Zone ID is required")
                        continue
                    
                    try:
                        # Get zone
                        zone = Zone.objects.get(id=zone_id)
                        
                        # Get seat if specified
                        seat = None
                        if seat_id:
                            seat = Seat.objects.get(id=seat_id, zone=zone)
                            quantity = 1  # Force quantity to 1 for numbered seats
                        
                        # Check if item is already locked
                        existing_lock = CartItemLock.objects.get_active_locks(
                            session_key=session_key
                        ).filter(
                            zone=zone,
                            seat=seat
                        ).first()
                        
                        if existing_lock:
                            # Extend existing lock
                            existing_lock.extend_lock(cls.DEFAULT_LOCK_DURATION_MINUTES)
                            created_locks.append(existing_lock)
                            logger.info(f"Extended lock for {existing_lock.item_key}")
                            continue
                        
                        # Check availability before locking
                        if seat:
                            # Check seat availability
                            if seat.status != Seat.Status.AVAILABLE:
                                error_messages.append(f"Seat {seat.seat_label} is not available")
                                continue
                            
                            # Check if seat is already locked by another session
                            conflicting_lock = CartItemLock.objects.get_active_locks(
                                zone=zone
                            ).filter(seat=seat).exclude(session_key=session_key).first()
                            
                            if conflicting_lock:
                                error_messages.append(f"Seat {seat.seat_label} is locked by another user")
                                continue
                        
                        else:
                            # Check zone availability for general admission
                            available_capacity = zone.available_capacity
                            
                            if available_capacity < quantity:
                                error_messages.append(
                                    f"Only {available_capacity} tickets available in {zone.name}"
                                )
                                continue
                        
                        # Create lock
                        lock = CartItemLock.objects.create_lock(
                            session_key=session_key,
                            user=user,
                            zone=zone,
                            seat=seat,
                            quantity=quantity,
                            duration_minutes=cls.DEFAULT_LOCK_DURATION_MINUTES
                        )
                        
                        created_locks.append(lock)
                        logger.info(f"Created lock for {lock.item_key} (expires: {lock.expires_at})")
                        
                    except (Zone.DoesNotExist, Seat.DoesNotExist) as e:
                        error_messages.append(f"Item not found: {str(e)}")
                        continue
                    
                    except Exception as e:
                        error_messages.append(f"Error locking item: {str(e)}")
                        logger.error(f"Error creating lock: {e}")
                        continue
                
                # Invalidate cache for affected zones
                cls._invalidate_zone_caches([lock.zone for lock in created_locks])
                
                success = len(created_locks) > 0
                return success, created_locks, error_messages
                
        except Exception as e:
            logger.error(f"Error in lock_items: {e}")
            error_messages.append(f"Failed to lock items: {str(e)}")
            return False, [], error_messages
    
    @classmethod
    def release_locks(cls, session_key: str, item_keys: Optional[List[str]] = None) -> Tuple[bool, int]:
        """
        Release locks for a session.
        
        Args:
            session_key: Django session key
            item_keys: Specific item keys to release (optional, releases all if None)
        
        Returns:
            Tuple of (success, released_count)
        """
        
        try:
            released_count = CartItemLock.objects.release_session_locks(
                session_key=session_key,
                item_keys=item_keys
            )
            
            if released_count > 0:
                # Invalidate cache for affected zones
                affected_zones = Zone.objects.filter(
                    cart_locks__session_key=session_key,
                    cart_locks__status=CartItemLock.Status.RELEASED
                ).distinct()
                
                cls._invalidate_zone_caches(affected_zones)
                
                logger.info(f"Released {released_count} locks for session {session_key}")
            
            return True, released_count
            
        except Exception as e:
            logger.error(f"Error releasing locks: {e}")
            return False, 0
    
    @classmethod
    def extend_locks(cls, session_key: str, minutes: int = None) -> Tuple[bool, int]:
        """
        Extend locks for a session.
        
        Args:
            session_key: Django session key
            minutes: Minutes to extend (default: DEFAULT_LOCK_DURATION_MINUTES)
        
        Returns:
            Tuple of (success, extended_count)
        """
        
        if minutes is None:
            minutes = cls.DEFAULT_LOCK_DURATION_MINUTES
        
        try:
            active_locks = CartItemLock.objects.get_active_locks(session_key=session_key)
            extended_count = 0
            
            for lock in active_locks:
                if lock.extend_lock(minutes):
                    extended_count += 1
            
            if extended_count > 0:
                logger.info(f"Extended {extended_count} locks for session {session_key}")
            
            return True, extended_count
            
        except Exception as e:
            logger.error(f"Error extending locks: {e}")
            return False, 0
    
    @classmethod
    def get_session_locks(cls, session_key: str) -> List[CartItemLock]:
        """Get active locks for a session."""
        
        return list(CartItemLock.objects.get_active_locks(session_key=session_key))
    
    @classmethod
    def convert_locks_to_sale(cls, session_key: str) -> Tuple[bool, int]:
        """
        Convert active locks to sales (called during checkout).
        
        Args:
            session_key: Django session key
        
        Returns:
            Tuple of (success, converted_count)
        """
        
        try:
            active_locks = CartItemLock.objects.get_active_locks(session_key=session_key)
            converted_count = 0
            
            for lock in active_locks:
                if lock.convert_to_sale():
                    converted_count += 1
            
            if converted_count > 0:
                logger.info(f"Converted {converted_count} locks to sales for session {session_key}")
            
            return True, converted_count
            
        except Exception as e:
            logger.error(f"Error converting locks to sales: {e}")
            return False, 0
    
    @classmethod
    def cleanup_expired_locks(cls) -> int:
        """
        Cleanup expired locks (called by Celery task).
        
        Returns:
            Number of expired locks cleaned up
        """
        
        try:
            expired_count = CartItemLock.objects.cleanup_expired_locks()
            
            if expired_count > 0:
                logger.info(f"Cleaned up {expired_count} expired locks")
                
                # Invalidate cache for affected zones
                affected_zones = Zone.objects.filter(
                    cart_locks__status=CartItemLock.Status.EXPIRED,
                    cart_locks__updated_at__gte=timezone.now() - timedelta(minutes=1)
                ).distinct()
                
                cls._invalidate_zone_caches(affected_zones)
            
            return expired_count
            
        except Exception as e:
            logger.error(f"Error cleaning up expired locks: {e}")
            return 0
    
    @classmethod
    def get_lock_status(cls, session_key: str) -> Dict:
        """
        Get lock status for a session.
        
        Returns:
            Dictionary with lock information
        """
        
        try:
            active_locks = CartItemLock.objects.get_active_locks(session_key=session_key)
            
            locks_data = []
            for lock in active_locks:
                locks_data.append({
                    'item_key': lock.item_key,
                    'zone_name': lock.zone.name,
                    'seat_label': lock.seat.seat_label if lock.seat else None,
                    'quantity': lock.quantity,
                    'expires_at': lock.expires_at.isoformat(),
                    'time_remaining_seconds': int(lock.time_remaining.total_seconds()),
                    'price': str(lock.price_at_lock),
                })
            
            return {
                'success': True,
                'session_key': session_key,
                'active_locks_count': len(locks_data),
                'locks': locks_data,
                'max_locks_per_session': cls.MAX_LOCKS_PER_SESSION,
                'default_duration_minutes': cls.DEFAULT_LOCK_DURATION_MINUTES,
            }
            
        except Exception as e:
            logger.error(f"Error getting lock status: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    @classmethod
    def _invalidate_zone_caches(cls, zones):
        """Invalidate cache for affected zones."""
        
        try:
            from .cache import sales_cache
            
            for zone in zones:
                sales_cache.invalidate_zone_caches(zone)
                
        except Exception as e:
            logger.error(f"Error invalidating zone caches: {e}")
    
    @classmethod
    def get_zone_locked_capacity(cls, zone: Zone) -> int:
        """Get the number of locked items for a zone."""
        
        if zone.zone_type == Zone.ZoneType.NUMBERED:
            return CartItemLock.objects.get_active_locks(zone=zone).filter(
                seat__isnull=False
            ).count()
        else:
            from django.db.models import Sum
            return CartItemLock.objects.get_active_locks(zone=zone).filter(
                seat__isnull=True
            ).aggregate(
                total=Sum('quantity')
            )['total'] or 0