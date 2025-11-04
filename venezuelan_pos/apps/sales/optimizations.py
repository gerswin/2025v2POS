"""
Database query optimizations for sales models.
Provides optimized managers and querysets with select_related and prefetch_related.
"""

from django.db import models
from django.db.models import Prefetch


class OptimizedTransactionManager(models.Manager):
    """Optimized manager for Transaction model."""
    
    def get_queryset(self):
        """Include basic relationships by default."""
        return super().get_queryset().select_related(
            'tenant',
            'event',
            'event__venue',
            'customer'
        )
    
    def with_items(self):
        """Include transaction items with seats and zones."""
        return self.get_queryset().prefetch_related(
            Prefetch(
                'items',
                queryset=models.Q().select_related(
                    'zone',
                    'seat',
                    'seat__zone'
                ).order_by('created_at')
            )
        )
    
    def with_payments(self):
        """Include payment information."""
        return self.get_queryset().prefetch_related(
            Prefetch(
                'payments',
                queryset=models.Q().select_related('payment_method').order_by('-created_at')
            )
        )
    
    def with_reservations(self):
        """Include reserved tickets."""
        return self.get_queryset().prefetch_related(
            Prefetch(
                'reserved_tickets',
                queryset=models.Q(status='active').select_related('seat', 'zone')
            )
        )
    
    def with_complete_data(self):
        """Include all related data for detailed views."""
        return self.get_queryset().prefetch_related(
            Prefetch(
                'items',
                queryset=models.Q().select_related(
                    'zone',
                    'seat',
                    'seat__zone'
                )
            ),
            Prefetch(
                'payments',
                queryset=models.Q().select_related('payment_method')
            ),
            'reserved_tickets'
        )
    
    def completed_transactions(self):
        """Get completed transactions."""
        return self.get_queryset().filter(status='completed')
    
    def pending_transactions(self):
        """Get pending transactions."""
        return self.get_queryset().filter(status='pending')
    
    def reserved_transactions(self):
        """Get transactions with reservations."""
        return self.get_queryset().filter(status='reserved')
    
    def by_event(self, event):
        """Get transactions by event."""
        return self.get_queryset().filter(event=event)
    
    def by_customer(self, customer):
        """Get transactions by customer."""
        return self.get_queryset().filter(customer=customer)
    
    def by_date_range(self, start_date, end_date):
        """Get transactions by date range."""
        return self.get_queryset().filter(
            created_at__date__range=[start_date, end_date]
        )


class OptimizedTransactionItemManager(models.Manager):
    """Optimized manager for TransactionItem model."""
    
    def get_queryset(self):
        """Include basic relationships by default."""
        return super().get_queryset().select_related(
            'tenant',
            'transaction',
            'transaction__event',
            'transaction__customer',
            'zone',
            'seat'
        )
    
    def with_pricing_data(self):
        """Include pricing-related data."""
        return self.get_queryset().select_related(
            'zone__event',
            'seat__zone'
        ).prefetch_related(
            'zone__price_stages',
            'zone__row_pricing'
        )
    
    def numbered_seat_items(self):
        """Get items for numbered seats."""
        return self.get_queryset().filter(
            item_type='numbered_seat',
            seat__isnull=False
        )
    
    def general_admission_items(self):
        """Get general admission items."""
        return self.get_queryset().filter(item_type='general_admission')
    
    def by_zone(self, zone):
        """Get items by zone."""
        return self.get_queryset().filter(zone=zone)
    
    def by_transaction(self, transaction):
        """Get items by transaction."""
        return self.get_queryset().filter(transaction=transaction)


class OptimizedReservedTicketManager(models.Manager):
    """Optimized manager for ReservedTicket model."""
    
    def get_queryset(self):
        """Include basic relationships by default."""
        return super().get_queryset().select_related(
            'tenant',
            'transaction',
            'transaction__event',
            'transaction__customer',
            'zone',
            'seat'
        )
    
    def active_reservations(self):
        """Get active reservations."""
        return self.get_queryset().filter(status='active')
    
    def expired_reservations(self):
        """Get expired reservations."""
        from django.utils import timezone
        return self.get_queryset().filter(
            status='active',
            reserved_until__lt=timezone.now()
        )
    
    def by_transaction(self, transaction):
        """Get reservations by transaction."""
        return self.get_queryset().filter(transaction=transaction)
    
    def by_zone(self, zone):
        """Get reservations by zone."""
        return self.get_queryset().filter(zone=zone)


class OptimizedOfflineBlockManager(models.Manager):
    """Optimized manager for OfflineBlock model."""
    
    def get_queryset(self):
        """Include tenant relationship by default."""
        return super().get_queryset().select_related('tenant')
    
    def active_blocks(self):
        """Get active blocks."""
        from django.utils import timezone
        return self.get_queryset().filter(
            status='active',
            expires_at__gt=timezone.now()
        )
    
    def expired_blocks(self):
        """Get expired blocks."""
        from django.utils import timezone
        return self.get_queryset().filter(
            status='active',
            expires_at__lte=timezone.now()
        )
    
    def by_assigned_to(self, assigned_to):
        """Get blocks by assignment."""
        return self.get_queryset().filter(assigned_to=assigned_to)


class OptimizedFiscalSeriesCounterManager(models.Manager):
    """Optimized manager for FiscalSeriesCounter model."""
    
    def get_queryset(self):
        """Include tenant and event relationships by default."""
        return super().get_queryset().select_related(
            'tenant',
            'event'
        )
    
    def by_tenant(self, tenant):
        """Get counters by tenant."""
        return self.get_queryset().filter(tenant=tenant)
    
    def by_event(self, event):
        """Get counters by event."""
        return self.get_queryset().filter(event=event)
    
    def global_counters(self):
        """Get global counters (no event specified)."""
        return self.get_queryset().filter(event__isnull=True)