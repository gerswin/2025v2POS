"""
Stage transition automation system with Redis caching.
Implements real-time stage monitoring, automatic transitions, and concurrent purchase handling.
"""

import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal
from datetime import datetime, timedelta

from django.core.cache import cache
from django.conf import settings
from django.utils import timezone
from django.db import transaction, models
from django.db.models import F, Q

import redis
from redis.exceptions import ConnectionError, TimeoutError

from .models import PriceStage, StageTransition, StageSales
from .services import HybridPricingService
from ..events.models import Event
from ..zones.models import Zone
from ..sales.models import TransactionItem

logger = logging.getLogger(__name__)


class StageTransitionAutomationService:
    """
    Real-time stage monitoring and automatic transition service.
    Handles Redis caching, concurrent purchase validation, and automated transitions.
    """
    
    # Cache key prefixes
    STAGE_STATUS_PREFIX = "stage_status"
    STAGE_LOCK_PREFIX = "stage_lock"
    TRANSITION_QUEUE_PREFIX = "transition_queue"
    STAGE_SALES_PREFIX = "stage_sales"
    CONCURRENT_PURCHASE_PREFIX = "concurrent_purchase"
    
    # Cache TTL settings (in seconds)
    STAGE_STATUS_TTL = 60  # 1 minute for real-time updates
    STAGE_LOCK_TTL = 30  # 30 seconds for transition locks
    TRANSITION_QUEUE_TTL = 300  # 5 minutes for transition queue
    STAGE_SALES_TTL = 120  # 2 minutes for sales tracking
    CONCURRENT_PURCHASE_TTL = 10  # 10 seconds for purchase locks
    
    def __init__(self):
        """Initialize the automation service."""
        self.cache = cache
        self._redis_client = None
        self.hybrid_service = HybridPricingService()
        
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
    
    def _acquire_lock(self, lock_key: str, timeout: int = None) -> bool:
        """Acquire a Redis lock for atomic operations."""
        if not self._redis_client:
            return True  # Fallback to no locking if Redis unavailable
        
        try:
            timeout = timeout or self.STAGE_LOCK_TTL
            return self._redis_client.set(lock_key, "locked", nx=True, ex=timeout)
        except (ConnectionError, TimeoutError) as e:
            logger.warning(f"Failed to acquire lock {lock_key}: {e}")
            return False
    
    def _release_lock(self, lock_key: str) -> bool:
        """Release a Redis lock."""
        if not self._redis_client:
            return True
        
        try:
            return bool(self._redis_client.delete(lock_key))
        except (ConnectionError, TimeoutError) as e:
            logger.warning(f"Failed to release lock {lock_key}: {e}")
            return False
    
    # Real-time Stage Status Caching
    
    def get_stage_status_cached(self, stage: PriceStage) -> Dict:
        """
        Get stage status from cache with real-time data.
        Falls back to database calculation if cache miss.
        """
        cache_key = self._get_cache_key(
            self.STAGE_STATUS_PREFIX, 
            str(stage.id)
        )
        
        cached_status = self._safe_cache_get(cache_key)
        if cached_status:
            return cached_status
        
        # Cache miss - calculate and cache
        return self._calculate_and_cache_stage_status(stage)
    
    def _calculate_and_cache_stage_status(self, stage: PriceStage) -> Dict:
        """
        Calculate stage status and cache it.
        Includes real-time quantity tracking and time calculations.
        """
        try:
            now = timezone.now()
            
            # Get real-time sold quantity
            sold_quantity = self._get_real_time_sold_quantity(stage)
            
            # Calculate time remaining
            time_remaining = self._calculate_time_remaining(stage, now)
            
            # Determine current status
            is_current = self._is_stage_current(stage, now, sold_quantity)
            should_transition, trigger_reason = self._should_stage_transition(
                stage, now, sold_quantity
            )
            
            status_data = {
                'stage_id': str(stage.id),
                'name': stage.name,
                'scope': stage.scope,
                'modifier_type': stage.modifier_type,
                'modifier_value': str(stage.modifier_value),
                'start_date': stage.start_date.isoformat(),
                'end_date': stage.end_date.isoformat(),
                'quantity_limit': stage.quantity_limit,
                'sold_quantity': sold_quantity,
                'remaining_quantity': max(0, (stage.quantity_limit or 0) - sold_quantity),
                'is_current': is_current,
                'is_upcoming': stage.is_upcoming,
                'is_past': stage.is_past,
                'should_transition': should_transition,
                'transition_trigger': trigger_reason,
                'auto_transition': stage.auto_transition,
                'time_remaining': time_remaining,
                'last_updated': now.isoformat(),
            }
            
            # Add next stage information
            next_stage = stage.get_next_stage()
            if next_stage:
                status_data['next_stage'] = {
                    'id': str(next_stage.id),
                    'name': next_stage.name,
                    'modifier_type': next_stage.modifier_type,
                    'modifier_value': str(next_stage.modifier_value),
                    'start_date': next_stage.start_date.isoformat(),
                }
            else:
                status_data['next_stage'] = None
            
            # Cache the status
            cache_key = self._get_cache_key(
                self.STAGE_STATUS_PREFIX, 
                str(stage.id)
            )
            self._safe_cache_set(cache_key, status_data, self.STAGE_STATUS_TTL)
            
            return status_data
            
        except Exception as e:
            logger.error(f"Failed to calculate stage status for {stage.id}: {e}")
            return {}
    
    def _get_real_time_sold_quantity(self, stage: PriceStage) -> int:
        """
        Get real-time sold quantity for a stage.
        Uses cached data when available, falls back to database.
        """
        cache_key = self._get_cache_key(
            self.STAGE_SALES_PREFIX,
            str(stage.id),
            str(stage.zone.id) if stage.zone else "event"
        )
        
        cached_quantity = self._safe_cache_get(cache_key)
        if cached_quantity is not None:
            return cached_quantity
        
        # Calculate from database
        quantity = stage.get_sold_quantity()
        
        # Cache for future use
        self._safe_cache_set(cache_key, quantity, self.STAGE_SALES_TTL)
        
        return quantity
    
    def _calculate_time_remaining(self, stage: PriceStage, now: datetime) -> Dict:
        """Calculate detailed time remaining information."""
        if now >= stage.end_date:
            return {
                'days': 0,
                'hours': 0,
                'minutes': 0,
                'seconds': 0,
                'total_seconds': 0,
                'expired': True
            }
        
        delta = stage.end_date - now
        total_seconds = int(delta.total_seconds())
        
        days = delta.days
        hours = delta.seconds // 3600
        minutes = (delta.seconds % 3600) // 60
        seconds = delta.seconds % 60
        
        return {
            'days': days,
            'hours': hours,
            'minutes': minutes,
            'seconds': seconds,
            'total_seconds': total_seconds,
            'expired': False
        }
    
    def _is_stage_current(self, stage: PriceStage, now: datetime, sold_quantity: int) -> bool:
        """Check if stage is currently active considering both date and quantity."""
        # Check date range
        if not (stage.start_date <= now <= stage.end_date):
            return False
        
        # Check quantity limit
        if stage.quantity_limit and sold_quantity >= stage.quantity_limit:
            return False
        
        return stage.is_active
    
    def _should_stage_transition(
        self, 
        stage: PriceStage, 
        now: datetime, 
        sold_quantity: int
    ) -> Tuple[bool, Optional[str]]:
        """Check if stage should transition and return reason."""
        if not stage.auto_transition:
            return False, None
        
        # Check date expiration
        if now > stage.end_date:
            return True, StageTransition.TriggerReason.DATE_EXPIRED
        
        # Check quantity limit
        if stage.quantity_limit and sold_quantity >= stage.quantity_limit:
            return True, StageTransition.TriggerReason.QUANTITY_REACHED
        
        return False, None
    
    # Automatic Transition Processing
    
    def process_automatic_transitions(self, event: Event, zone: Optional[Zone] = None) -> List[StageTransition]:
        """
        Process automatic transitions for an event or zone.
        Uses Redis locks to prevent concurrent transition processing.
        """
        lock_key = self._get_cache_key(
            self.STAGE_LOCK_PREFIX,
            "transition",
            str(event.id),
            str(zone.id) if zone else "event"
        )
        
        # Acquire lock to prevent concurrent processing
        if not self._acquire_lock(lock_key):
            logger.info(f"Transition already in progress for event {event.id}, zone {zone}")
            return []
        
        try:
            return self._process_transitions_locked(event, zone)
        finally:
            self._release_lock(lock_key)
    
    def _process_transitions_locked(self, event: Event, zone: Optional[Zone] = None) -> List[StageTransition]:
        """Process transitions while holding lock."""
        transitions = []
        
        # Get stages that might need transition
        stages_query = PriceStage.objects.filter(
            event=event,
            is_active=True,
            auto_transition=True
        )
        
        if zone:
            stages_query = stages_query.filter(
                zone=zone,
                scope=PriceStage.StageScope.ZONE_SPECIFIC
            )
        else:
            stages_query = stages_query.filter(
                zone__isnull=True,
                scope=PriceStage.StageScope.EVENT_WIDE
            )
        
        for stage in stages_query:
            transition = self._check_and_process_single_transition(stage)
            if transition:
                transitions.append(transition)
                # Invalidate stage status cache after transition
                self._invalidate_stage_status_cache(stage)
        
        return transitions
    
    def _check_and_process_single_transition(self, stage: PriceStage) -> Optional[StageTransition]:
        """Check and process a single stage transition."""
        now = timezone.now()
        sold_quantity = self._get_real_time_sold_quantity(stage)
        
        should_transition, trigger_reason = self._should_stage_transition(
            stage, now, sold_quantity
        )
        
        if not should_transition:
            return None
        
        # Process the transition
        return self._execute_stage_transition(stage, trigger_reason, sold_quantity)
    
    @transaction.atomic
    def _execute_stage_transition(
        self, 
        stage: PriceStage, 
        trigger_reason: str, 
        sold_quantity: int
    ) -> StageTransition:
        """
        Execute a stage transition atomically.
        Creates transition record and updates caches.
        """
        next_stage = stage.get_next_stage()
        
        # Create transition record
        stage_transition = StageTransition.objects.create(
            tenant=stage.tenant,
            event=stage.event,
            zone=stage.zone,
            stage_from=stage,
            stage_to=next_stage,
            trigger_reason=trigger_reason,
            sold_quantity=sold_quantity,
            metadata={
                'stage_from_name': stage.name,
                'stage_to_name': next_stage.name if next_stage else 'Final Stage',
                'quantity_limit': stage.quantity_limit,
                'end_date': stage.end_date.isoformat(),
                'scope': stage.scope,
                'transition_timestamp': timezone.now().isoformat(),
            }
        )
        
        # Update stage sales tracking
        StageSales.update_sales_for_stage(
            stage=stage,
            zone=stage.zone,
            tickets_count=0,  # Just update cumulative totals
            revenue_amount=Decimal('0.00')
        )
        
        # Invalidate related caches
        self._invalidate_transition_caches(stage, next_stage)
        
        logger.info(
            f"Stage transition executed: {stage.name} -> "
            f"{next_stage.name if next_stage else 'Final'} "
            f"(Reason: {trigger_reason}, Sold: {sold_quantity})"
        )
        
        return stage_transition
    
    # Concurrent Purchase Handling
    
    def validate_concurrent_purchase(
        self, 
        stage: PriceStage, 
        requested_quantity: int,
        purchase_session_id: str
    ) -> Tuple[bool, Dict]:
        """
        Validate a purchase request against current stage limits.
        Handles concurrent purchases during stage transitions.
        """
        lock_key = self._get_cache_key(
            self.CONCURRENT_PURCHASE_PREFIX,
            str(stage.id)
        )
        
        # Acquire short-term lock for purchase validation
        if not self._acquire_lock(lock_key, self.CONCURRENT_PURCHASE_TTL):
            return False, {
                'error': 'Purchase validation in progress, please retry',
                'retry_after': 2
            }
        
        try:
            return self._validate_purchase_locked(stage, requested_quantity, purchase_session_id)
        finally:
            self._release_lock(lock_key)
    
    def _validate_purchase_locked(
        self, 
        stage: PriceStage, 
        requested_quantity: int,
        purchase_session_id: str
    ) -> Tuple[bool, Dict]:
        """Validate purchase while holding lock."""
        now = timezone.now()
        
        # Get current stage status
        status = self.get_stage_status_cached(stage)
        
        # Check if stage is still current
        if not status.get('is_current', False):
            return False, {
                'error': 'Price stage is no longer active',
                'current_stage': status.get('next_stage'),
                'transition_reason': status.get('transition_trigger')
            }
        
        # Check quantity availability
        if stage.quantity_limit:
            current_sold = status.get('sold_quantity', 0)
            remaining = stage.quantity_limit - current_sold
            
            if requested_quantity > remaining:
                return False, {
                    'error': 'Insufficient quantity available in current stage',
                    'requested': requested_quantity,
                    'available': remaining,
                    'stage_limit': stage.quantity_limit
                }
        
        # Reserve the quantity temporarily
        self._reserve_stage_quantity(stage, requested_quantity, purchase_session_id)
        
        return True, {
            'stage_id': str(stage.id),
            'stage_name': stage.name,
            'reserved_quantity': requested_quantity,
            'session_id': purchase_session_id,
            'expires_at': (now + timedelta(minutes=5)).isoformat()
        }
    
    def _reserve_stage_quantity(
        self, 
        stage: PriceStage, 
        quantity: int, 
        session_id: str
    ) -> bool:
        """Temporarily reserve quantity for a purchase session."""
        reservation_key = self._get_cache_key(
            "stage_reservation",
            str(stage.id),
            session_id
        )
        
        reservation_data = {
            'stage_id': str(stage.id),
            'quantity': quantity,
            'session_id': session_id,
            'reserved_at': timezone.now().isoformat(),
            'expires_at': (timezone.now() + timedelta(minutes=5)).isoformat()
        }
        
        return self._safe_cache_set(
            reservation_key, 
            reservation_data, 
            300  # 5 minutes
        )
    
    def confirm_stage_purchase(
        self, 
        stage: PriceStage, 
        quantity: int, 
        session_id: str,
        revenue_amount: Optional[Decimal] = None
    ) -> bool:
        """
        Confirm a stage purchase and update tracking.
        Called when transaction is completed.
        """
        # Remove reservation
        reservation_key = self._get_cache_key(
            "stage_reservation",
            str(stage.id),
            session_id
        )
        self._safe_cache_delete(reservation_key)
        
        # Update stage sales tracking
        try:
            StageSales.update_sales_for_stage(
                stage=stage,
                zone=stage.zone,
                tickets_count=quantity,
                revenue_amount=revenue_amount
            )
            
            # Update cached sold quantity
            self._update_cached_sold_quantity(stage, quantity)
            
            # Check if this purchase triggers a transition
            self._check_post_purchase_transition(stage)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to confirm stage purchase: {e}")
            return False
    
    def _update_cached_sold_quantity(self, stage: PriceStage, additional_quantity: int):
        """Update cached sold quantity after a purchase."""
        cache_key = self._get_cache_key(
            self.STAGE_SALES_PREFIX,
            str(stage.id),
            str(stage.zone.id) if stage.zone else "event"
        )
        
        try:
            if self._redis_client:
                # Atomic increment
                self._redis_client.incrby(cache_key, additional_quantity)
                self._redis_client.expire(cache_key, self.STAGE_SALES_TTL)
            else:
                # Fallback: invalidate cache to force refresh
                self._safe_cache_delete(cache_key)
        except Exception as e:
            logger.warning(f"Failed to update cached sold quantity: {e}")
    
    def _check_post_purchase_transition(self, stage: PriceStage):
        """Check if a purchase triggers an automatic transition."""
        if not stage.auto_transition:
            return
        
        # Process transitions for this stage's scope
        if stage.scope == PriceStage.StageScope.ZONE_SPECIFIC:
            self.process_automatic_transitions(stage.event, stage.zone)
        else:
            self.process_automatic_transitions(stage.event)
    
    # Cache Management
    
    def _invalidate_stage_status_cache(self, stage: PriceStage):
        """Invalidate stage status cache."""
        cache_key = self._get_cache_key(self.STAGE_STATUS_PREFIX, str(stage.id))
        self._safe_cache_delete(cache_key)
    
    def _invalidate_transition_caches(self, from_stage: PriceStage, to_stage: Optional[PriceStage]):
        """Invalidate caches after a transition."""
        # Invalidate from stage
        self._invalidate_stage_status_cache(from_stage)
        
        # Invalidate to stage if exists
        if to_stage:
            self._invalidate_stage_status_cache(to_stage)
        
        # Invalidate sales cache
        sales_key = self._get_cache_key(
            self.STAGE_SALES_PREFIX,
            str(from_stage.id),
            str(from_stage.zone.id) if from_stage.zone else "event"
        )
        self._safe_cache_delete(sales_key)
    
    def invalidate_event_stage_caches(self, event: Event):
        """Invalidate all stage caches for an event."""
        for stage in event.price_stages.all():
            self._invalidate_stage_status_cache(stage)
    
    # Monitoring and Health Check
    
    def get_monitoring_overview(self, event: Event) -> Dict:
        """
        Get comprehensive monitoring overview for an event.
        Includes all stages, transitions, and real-time status.
        """
        overview = {
            'event_id': str(event.id),
            'event_name': event.name,
            'monitoring_timestamp': timezone.now().isoformat(),
            'event_wide_stages': [],
            'zone_specific_stages': {},
            'recent_transitions': [],
            'active_reservations': 0,
        }
        
        # Get event-wide stages
        event_stages = PriceStage.objects.filter(
            event=event,
            scope=PriceStage.StageScope.EVENT_WIDE,
            is_active=True
        ).order_by('stage_order')
        
        for stage in event_stages:
            stage_status = self.get_stage_status_cached(stage)
            overview['event_wide_stages'].append(stage_status)
        
        # Get zone-specific stages
        for zone in event.zones.all():
            zone_stages = PriceStage.objects.filter(
                event=event,
                zone=zone,
                scope=PriceStage.StageScope.ZONE_SPECIFIC,
                is_active=True
            ).order_by('stage_order')
            
            if zone_stages.exists():
                overview['zone_specific_stages'][zone.name] = [
                    self.get_stage_status_cached(stage)
                    for stage in zone_stages
                ]
        
        # Get recent transitions (last 24 hours)
        recent_transitions = StageTransition.objects.filter(
            event=event,
            transition_at__gte=timezone.now() - timedelta(hours=24)
        ).order_by('-transition_at')[:10]
        
        overview['recent_transitions'] = [
            {
                'id': str(trans.id),
                'from_stage': trans.stage_from.name,
                'to_stage': trans.stage_to.name if trans.stage_to else 'Final',
                'trigger_reason': trans.trigger_reason,
                'zone': trans.zone.name if trans.zone else 'Event-wide',
                'sold_quantity': trans.sold_quantity,
                'transition_at': trans.transition_at.isoformat(),
            }
            for trans in recent_transitions
        ]
        
        return overview
    
    def health_check(self) -> Dict[str, Any]:
        """Perform health check on the automation service."""
        try:
            start_time = timezone.now()
            
            # Test Redis operations
            test_key = "automation_health_check"
            test_data = {"timestamp": start_time.isoformat()}
            
            set_success = self._safe_cache_set(test_key, test_data, 60)
            get_success = self._safe_cache_get(test_key) == test_data
            delete_success = self._safe_cache_delete(test_key)
            
            # Test lock operations
            lock_key = "automation_health_lock"
            lock_acquired = self._acquire_lock(lock_key, 5)
            lock_released = self._release_lock(lock_key) if lock_acquired else False
            
            end_time = timezone.now()
            response_time = (end_time - start_time).total_seconds() * 1000
            
            return {
                'status': 'healthy' if all([set_success, get_success, delete_success]) else 'degraded',
                'response_time_ms': response_time,
                'redis_operations': {
                    'cache_set': set_success,
                    'cache_get': get_success,
                    'cache_delete': delete_success,
                    'lock_acquire': lock_acquired,
                    'lock_release': lock_released,
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


# Global automation service instance
stage_automation = StageTransitionAutomationService()