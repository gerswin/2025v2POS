"""
Database query optimizations for pricing models.
Provides optimized managers and querysets with select_related and prefetch_related.
"""

from django.db import models
from django.db.models import Prefetch


class OptimizedPriceStageManager(models.Manager):
    """Optimized manager for PriceStage model."""
    
    def get_queryset(self):
        """Include basic relationships by default."""
        return super().get_queryset().select_related(
            'tenant',
            'event',
            'zone'
        )
    
    def with_transitions(self):
        """Include stage transitions."""
        return self.get_queryset().prefetch_related(
            Prefetch(
                'transitions_from',
                queryset=models.Q().select_related('stage_to').order_by('-transition_at')
            )
        )
    
    def with_sales_data(self):
        """Include sales tracking data."""
        return self.get_queryset().prefetch_related(
            Prefetch(
                'stage_sales',
                queryset=models.Q().order_by('-sales_date')
            )
        )
    
    def active_stages(self):
        """Get active price stages."""
        return self.get_queryset().filter(is_active=True)
    
    def current_stages(self):
        """Get currently active stages based on date."""
        from django.utils import timezone
        now = timezone.now()
        return self.get_queryset().filter(
            is_active=True,
            start_date__lte=now,
            end_date__gte=now
        )
    
    def event_wide_stages(self):
        """Get event-wide stages."""
        return self.get_queryset().filter(
            scope='event',
            zone__isnull=True
        )
    
    def zone_specific_stages(self):
        """Get zone-specific stages."""
        return self.get_queryset().filter(
            scope='zone',
            zone__isnull=False
        )
    
    def by_event(self, event):
        """Get stages by event."""
        return self.get_queryset().filter(event=event)
    
    def by_zone(self, zone):
        """Get stages by zone."""
        return self.get_queryset().filter(zone=zone)
    
    def ordered_stages(self):
        """Get stages ordered by stage order and start date."""
        return self.get_queryset().order_by('stage_order', 'start_date')


class OptimizedStageTransitionManager(models.Manager):
    """Optimized manager for StageTransition model."""
    
    def get_queryset(self):
        """Include basic relationships by default."""
        return super().get_queryset().select_related(
            'tenant',
            'event',
            'zone',
            'stage_from',
            'stage_to'
        )
    
    def by_event(self, event):
        """Get transitions by event."""
        return self.get_queryset().filter(event=event)
    
    def by_zone(self, zone):
        """Get transitions by zone."""
        return self.get_queryset().filter(zone=zone)
    
    def by_trigger_reason(self, reason):
        """Get transitions by trigger reason."""
        return self.get_queryset().filter(trigger_reason=reason)
    
    def recent_transitions(self, days=30):
        """Get recent transitions."""
        from django.utils import timezone
        from datetime import timedelta
        
        cutoff_date = timezone.now() - timedelta(days=days)
        return self.get_queryset().filter(transition_at__gte=cutoff_date)


class OptimizedStageSalesManager(models.Manager):
    """Optimized manager for StageSales model."""
    
    def get_queryset(self):
        """Include basic relationships by default."""
        return super().get_queryset().select_related(
            'tenant',
            'stage',
            'stage__event',
            'zone'
        )
    
    def by_stage(self, stage):
        """Get sales by stage."""
        return self.get_queryset().filter(stage=stage)
    
    def by_zone(self, zone):
        """Get sales by zone."""
        return self.get_queryset().filter(zone=zone)
    
    def by_date_range(self, start_date, end_date):
        """Get sales by date range."""
        return self.get_queryset().filter(
            sales_date__range=[start_date, end_date]
        )
    
    def recent_sales(self, days=30):
        """Get recent sales data."""
        from django.utils import timezone
        from datetime import timedelta
        
        cutoff_date = timezone.now().date() - timedelta(days=days)
        return self.get_queryset().filter(sales_date__gte=cutoff_date)


class OptimizedRowPricingManager(models.Manager):
    """Optimized manager for RowPricing model."""
    
    def get_queryset(self):
        """Include basic relationships by default."""
        return super().get_queryset().select_related(
            'tenant',
            'zone',
            'zone__event'
        )
    
    def active_pricing(self):
        """Get active row pricing."""
        return self.get_queryset().filter(is_active=True)
    
    def by_zone(self, zone):
        """Get row pricing by zone."""
        return self.get_queryset().filter(zone=zone)
    
    def by_row(self, zone, row_number):
        """Get pricing for specific row."""
        return self.get_queryset().filter(
            zone=zone,
            row_number=row_number
        )
    
    def ordered_by_row(self):
        """Get pricing ordered by row number."""
        return self.get_queryset().order_by('row_number')


class OptimizedPriceHistoryManager(models.Manager):
    """Optimized manager for PriceHistory model."""
    
    def get_queryset(self):
        """Include basic relationships by default."""
        return super().get_queryset().select_related(
            'tenant',
            'event',
            'zone',
            'price_stage',
            'row_pricing'
        )
    
    def by_event(self, event):
        """Get price history by event."""
        return self.get_queryset().filter(event=event)
    
    def by_zone(self, zone):
        """Get price history by zone."""
        return self.get_queryset().filter(zone=zone)
    
    def by_price_type(self, price_type):
        """Get price history by type."""
        return self.get_queryset().filter(price_type=price_type)
    
    def by_date_range(self, start_date, end_date):
        """Get price history by date range."""
        return self.get_queryset().filter(
            calculation_date__date__range=[start_date, end_date]
        )
    
    def recent_calculations(self, days=30):
        """Get recent price calculations."""
        from django.utils import timezone
        from datetime import timedelta
        
        cutoff_date = timezone.now() - timedelta(days=days)
        return self.get_queryset().filter(calculation_date__gte=cutoff_date)