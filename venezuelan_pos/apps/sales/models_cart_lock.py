"""
Cart item locking models for preventing overselling.
"""

import uuid
from datetime import timedelta
from decimal import Decimal
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from venezuelan_pos.apps.tenants.models import TenantAwareModel
from venezuelan_pos.apps.zones.models import Zone, Seat
from venezuelan_pos.apps.tenants.models import User


class CartItemLock(TenantAwareModel):
    """
    Temporary lock on cart items to prevent overselling.
    Items are locked for 15 minutes when added to cart.
    """
    
    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        EXPIRED = 'expired', 'Expired'
        RELEASED = 'released', 'Released'
        CONVERTED = 'converted', 'Converted to Sale'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Session identification
    session_key = models.CharField(
        max_length=40,
        help_text="Django session key for anonymous users"
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="User if authenticated"
    )
    
    # Locked item
    zone = models.ForeignKey(
        Zone,
        on_delete=models.CASCADE,
        related_name='cart_locks',
        help_text="Zone containing the locked item"
    )
    seat = models.ForeignKey(
        Seat,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='cart_locks',
        help_text="Specific seat (for numbered zones only)"
    )
    quantity = models.PositiveIntegerField(
        default=1,
        help_text="Number of tickets locked (for general admission)"
    )
    
    # Temporal control
    locked_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the lock was created"
    )
    expires_at = models.DateTimeField(
        help_text="When the lock expires"
    )
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.ACTIVE,
        help_text="Current lock status"
    )
    
    # Pricing snapshot
    price_at_lock = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Price when item was locked"
    )
    
    # Additional metadata
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional lock metadata"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'cart_item_locks'
        verbose_name = 'Cart Item Lock'
        verbose_name_plural = 'Cart Item Locks'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', 'status', 'expires_at']),
            models.Index(fields=['session_key', 'status']),
            models.Index(fields=['user', 'status']),
            models.Index(fields=['zone', 'status']),
            models.Index(fields=['seat', 'status']),
        ]
        constraints = [
            # Ensure quantity is positive
            models.CheckConstraint(
                check=models.Q(quantity__gt=0),
                name='cart_lock_positive_quantity'
            ),
        ]
    
    def __str__(self):
        if self.seat:
            return f"Lock: {self.seat.seat_label} until {self.expires_at}"
        return f"Lock: {self.zone.name} (x{self.quantity}) until {self.expires_at}"
    
    def clean(self):
        """Validate lock data."""
        super().clean()
        
        # Validate seat-zone relationship
        if self.seat and self.seat.zone != self.zone:
            raise ValidationError({
                'seat': 'Seat must belong to the specified zone'
            })
        
        # Validate quantity for general admission
        if not self.seat and self.quantity <= 0:
            raise ValidationError({
                'quantity': 'Quantity must be positive for general admission'
            })
        
        # Validate quantity for numbered seats
        if self.seat and self.quantity != 1:
            raise ValidationError({
                'quantity': 'Quantity must be 1 for numbered seats'
            })
    
    @property
    def is_expired(self):
        """Check if lock has expired."""
        return timezone.now() > self.expires_at
    
    @property
    def time_remaining(self):
        """Get remaining time before expiration."""
        if self.is_expired:
            return timedelta(0)
        return self.expires_at - timezone.now()
    
    @property
    def item_key(self):
        """Generate unique key for this locked item."""
        if self.seat:
            return f"seat_{self.seat.id}"
        return f"general_{self.zone.id}"
    
    def extend_lock(self, minutes=15):
        """Extend lock expiration time."""
        if self.status == self.Status.ACTIVE:
            self.expires_at = timezone.now() + timedelta(minutes=minutes)
            self.save(update_fields=['expires_at', 'updated_at'])
            return True
        return False
    
    def release(self):
        """Release the lock manually."""
        if self.status == self.Status.ACTIVE:
            self.status = self.Status.RELEASED
            self.save(update_fields=['status', 'updated_at'])
            return True
        return False
    
    def convert_to_sale(self):
        """Mark lock as converted to sale."""
        if self.status == self.Status.ACTIVE:
            self.status = self.Status.CONVERTED
            self.save(update_fields=['status', 'updated_at'])
            return True
        return False


class CartItemLockManager(models.Manager):
    """Manager for CartItemLock with business logic."""
    
    def create_lock(self, session_key, user, zone, seat=None, quantity=1, 
                   price=None, duration_minutes=15):
        """Create a new cart item lock."""
        
        # Calculate expiration time
        expires_at = timezone.now() + timedelta(minutes=duration_minutes)
        
        # Get price if not provided
        if price is None:
            from ..pricing.services import PricingCalculationService
            pricing_service = PricingCalculationService()
            
            if seat:
                price, _ = pricing_service.calculate_seat_price(seat)
            else:
                price, _ = pricing_service.calculate_zone_price(zone)
        
        # Create lock
        lock = self.create(
            tenant=zone.tenant,
            session_key=session_key,
            user=user,
            zone=zone,
            seat=seat,
            quantity=quantity,
            expires_at=expires_at,
            price_at_lock=price,
            status=CartItemLock.Status.ACTIVE
        )
        
        return lock
    
    def get_active_locks(self, session_key=None, user=None, zone=None):
        """Get active locks for session, user, or zone."""
        queryset = self.filter(
            status=CartItemLock.Status.ACTIVE,
            expires_at__gt=timezone.now()
        )
        
        if session_key:
            queryset = queryset.filter(session_key=session_key)
        
        if user:
            queryset = queryset.filter(user=user)
        
        if zone:
            queryset = queryset.filter(zone=zone)
        
        return queryset
    
    def cleanup_expired_locks(self):
        """Mark expired locks as expired."""
        expired_count = self.filter(
            status=CartItemLock.Status.ACTIVE,
            expires_at__lte=timezone.now()
        ).update(
            status=CartItemLock.Status.EXPIRED,
            updated_at=timezone.now()
        )
        
        return expired_count
    
    def release_session_locks(self, session_key, item_keys=None):
        """Release locks for a specific session."""
        queryset = self.filter(
            session_key=session_key,
            status=CartItemLock.Status.ACTIVE
        )
        
        if item_keys:
            # Filter by specific items
            seat_ids = []
            zone_ids = []
            
            for key in item_keys:
                if key.startswith('seat_'):
                    seat_ids.append(key.replace('seat_', ''))
                elif key.startswith('general_'):
                    zone_ids.append(key.replace('general_', ''))
            
            if seat_ids or zone_ids:
                from django.db.models import Q
                filter_q = Q()
                
                if seat_ids:
                    filter_q |= Q(seat_id__in=seat_ids)
                
                if zone_ids:
                    filter_q |= Q(zone_id__in=zone_ids, seat__isnull=True)
                
                queryset = queryset.filter(filter_q)
        
        released_count = queryset.update(
            status=CartItemLock.Status.RELEASED,
            updated_at=timezone.now()
        )
        
        return released_count


# Add manager to model
CartItemLock.add_to_class('objects', CartItemLockManager())