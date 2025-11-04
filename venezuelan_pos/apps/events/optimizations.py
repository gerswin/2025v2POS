"""
Optimized managers and querysets for event models.
"""

from django.db import models
from django.db.models import Prefetch, Q, F, Count, Sum, Avg
from django.core.cache import cache
from django.utils import timezone


class OptimizedEventManager(models.Manager):
    """Optimized manager for Event model."""
    
    def get_with_complete_data(self):
        """Get events with all related data optimized."""
        return self.select_related(
            'tenant',
            'venue'
        ).prefetch_related(
            Prefetch(
                'zones',
                queryset=models.QuerySet().select_related('tenant').annotate(
                    seat_count=Count('seats'),
                    available_seats=Count('seats', filter=Q(seats__status='available'))
                )
            ),
            Prefetch(
                'zones__price_stages',
                queryset=models.QuerySet().filter(is_active=True).order_by('stage_order')
            ),
            'zones__row_pricing'
        ).annotate(
            total_capacity=Sum('zones__capacity'),
            zone_count=Count('zones', distinct=True),
            transaction_count=Count('transactions', distinct=True)
        )
    
    def get_active_with_availability(self, tenant=None):
        """Get active events with seat availability data."""
        queryset = self.filter(status='active').select_related(
            'tenant',
            'venue'
        ).prefetch_related(
            Prefetch(
                'zones',
                queryset=models.QuerySet().annotate(
                    available_seats=Count('seats', filter=Q(seats__status='available')),
                    sold_seats=Count('seats', filter=Q(seats__status='sold')),
                    reserved_seats=Count('seats', filter=Q(seats__status='reserved'))
                )
            )
        ).annotate(
            total_available=Sum('zones__seats__id', filter=Q(zones__seats__status='available')),
            total_sold=Sum('zones__seats__id', filter=Q(zones__seats__status='sold')),
            occupancy_rate=F('total_sold') * 100.0 / F('zones__capacity')
        )
        
        if tenant:
            queryset = queryset.filter(tenant=tenant)
        
        return queryset.order_by('start_date')
    
    def get_upcoming_events(self, tenant=None, days_ahead=30):
        """Get upcoming events within specified days."""
        from datetime import timedelta
        
        end_date = timezone.now() + timedelta(days=days_ahead)
        
        queryset = self.filter(
            start_date__gte=timezone.now(),
            start_date__lte=end_date,
            status__in=['active', 'draft']
        ).select_related('tenant', 'venue').annotate(
            days_until_event=F('start_date') - timezone.now()
        )
        
        if tenant:
            queryset = queryset.filter(tenant=tenant)
        
        return queryset.order_by('start_date')
    
    def get_events_with_sales_data(self, tenant=None):
        """Get events with sales performance data."""
        queryset = self.select_related('tenant', 'venue').annotate(
            total_revenue=Sum('transactions__total_amount', filter=Q(transactions__status='completed')),
            total_tickets_sold=Count('transactions__items', filter=Q(transactions__status='completed')),
            transaction_count=Count('transactions', filter=Q(transactions__status='completed')),
            average_ticket_price=Avg('transactions__total_amount', filter=Q(transactions__status='completed'))
        )
        
        if tenant:
            queryset = queryset.filter(tenant=tenant)
        
        return queryset.order_by('-total_revenue')
    
    def search_events(self, query, tenant=None):
        """Search events by name, description, or venue."""
        queryset = self.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query) |
            Q(venue__name__icontains=query)
        ).select_related('tenant', 'venue')
        
        if tenant:
            queryset = queryset.filter(tenant=tenant)
        
        return queryset.order_by('-start_date')


class OptimizedVenueManager(models.Manager):
    """Optimized manager for Venue model."""
    
    def get_with_event_stats(self, tenant=None):
        """Get venues with event statistics."""
        queryset = self.select_related('tenant').annotate(
            total_events=Count('events'),
            active_events=Count('events', filter=Q(events__status='active')),
            upcoming_events=Count('events', filter=Q(
                events__start_date__gte=timezone.now(),
                events__status='active'
            ))
        )
        
        if tenant:
            queryset = queryset.filter(tenant=tenant)
        
        return queryset.order_by('name')
    
    def get_popular_venues(self, tenant=None, limit=10):
        """Get most popular venues by event count."""
        queryset = self.annotate(
            event_count=Count('events'),
            total_revenue=Sum('events__transactions__total_amount', 
                            filter=Q(events__transactions__status='completed'))
        ).filter(event_count__gt=0)
        
        if tenant:
            queryset = queryset.filter(tenant=tenant)
        
        return queryset.order_by('-event_count')[:limit]


class EventQueryOptimizer:
    """Utility class for optimizing event-related queries."""
    
    @staticmethod
    def get_event_dashboard_data(event):
        """Get optimized data for event dashboard."""
        cache_key = f'event_dashboard_{event.id}'
        data = cache.get(cache_key)
        
        if data is None:
            # Get zones with availability
            zones_data = event.zones.annotate(
                total_seats=Count('seats'),
                available_seats=Count('seats', filter=Q(seats__status='available')),
                sold_seats=Count('seats', filter=Q(seats__status='sold')),
                reserved_seats=Count('seats', filter=Q(seats__status='reserved'))
            ).values(
                'id', 'name', 'zone_type', 'capacity',
                'total_seats', 'available_seats', 'sold_seats', 'reserved_seats'
            )
            
            # Get sales summary
            sales_summary = event.transactions.filter(
                status='completed'
            ).aggregate(
                total_revenue=Sum('total_amount'),
                total_transactions=Count('id'),
                total_tickets=Count('items__id'),
                average_transaction=Avg('total_amount')
            )
            
            # Get current price stages
            current_stages = event.zones.prefetch_related(
                Prefetch(
                    'price_stages',
                    queryset=models.QuerySet().filter(
                        is_active=True,
                        start_date__lte=timezone.now(),
                        end_date__gte=timezone.now()
                    ).order_by('stage_order')
                )
            ).values(
                'id', 'name', 'price_stages__name', 'price_stages__modifier_value'
            )
            
            data = {
                'zones': list(zones_data),
                'sales_summary': sales_summary,
                'current_stages': list(current_stages),
                'last_updated': timezone.now().isoformat(),
            }
            
            # Cache for 2 minutes (frequent updates needed)
            cache.set(cache_key, data, 120)
        
        return data
    
    @staticmethod
    def get_event_seat_map_data(event):
        """Get optimized seat map data for an event."""
        cache_key = f'event_seat_map_{event.id}'
        data = cache.get(cache_key)
        
        if data is None:
            zones_with_seats = event.zones.filter(
                zone_type='numbered'
            ).prefetch_related(
                Prefetch(
                    'seats',
                    queryset=models.QuerySet().select_related('zone').order_by(
                        'row_number', 'seat_number'
                    )
                ),
                Prefetch(
                    'tables',
                    queryset=models.QuerySet().prefetch_related('seats')
                )
            ).values(
                'id', 'name', 'rows', 'seats_per_row',
                'seats__id', 'seats__row_number', 'seats__seat_number', 'seats__status'
            )
            
            data = {
                'zones': list(zones_with_seats),
                'last_updated': timezone.now().isoformat(),
            }
            
            # Cache for 30 seconds (needs frequent updates during sales)
            cache.set(cache_key, data, 30)
        
        return data
    
    @staticmethod
    def get_event_pricing_data(event):
        """Get optimized pricing data for an event."""
        cache_key = f'event_pricing_{event.id}'
        data = cache.get(cache_key)
        
        if data is None:
            # Get current active price stages
            price_stages = event.zones.prefetch_related(
                Prefetch(
                    'price_stages',
                    queryset=models.QuerySet().filter(is_active=True).annotate(
                        tickets_sold=Count('stage_sales__tickets_sold'),
                        remaining_quantity=F('quantity_limit') - F('tickets_sold')
                    ).order_by('stage_order')
                )
            )
            
            # Get row pricing
            row_pricing = event.zones.prefetch_related('row_pricing')
            
            data = {
                'price_stages': [
                    {
                        'zone_id': str(zone.id),
                        'zone_name': zone.name,
                        'stages': [
                            {
                                'id': str(stage.id),
                                'name': stage.name,
                                'modifier_value': float(stage.modifier_value),
                                'start_date': stage.start_date.isoformat(),
                                'end_date': stage.end_date.isoformat(),
                                'quantity_limit': stage.quantity_limit,
                                'remaining_quantity': stage.remaining_quantity,
                            }
                            for stage in zone.price_stages.all()
                        ]
                    }
                    for zone in price_stages
                ],
                'row_pricing': [
                    {
                        'zone_id': str(zone.id),
                        'zone_name': zone.name,
                        'rows': [
                            {
                                'row_number': rp.row_number,
                                'price_modifier': float(rp.price_modifier),
                            }
                            for rp in zone.row_pricing.all()
                        ]
                    }
                    for zone in row_pricing
                ],
                'last_updated': timezone.now().isoformat(),
            }
            
            # Cache for 1 minute
            cache.set(cache_key, data, 60)
        
        return data
    
    @staticmethod
    def invalidate_event_cache(event_id):
        """Invalidate all cached data for an event."""
        cache_keys = [
            f'event_dashboard_{event_id}',
            f'event_seat_map_{event_id}',
            f'event_pricing_{event_id}',
        ]
        
        cache.delete_many(cache_keys)
    
    @staticmethod
    def get_events_by_date_range(tenant, start_date, end_date):
        """Get events within a date range with optimized queries."""
        from venezuelan_pos.apps.events.models import Event
        
        return Event.objects.filter(
            tenant=tenant,
            start_date__gte=start_date,
            start_date__lte=end_date
        ).select_related('tenant', 'venue').prefetch_related(
            'zones'
        ).annotate(
            zone_count=Count('zones'),
            total_capacity=Sum('zones__capacity'),
            sales_count=Count('transactions', filter=Q(transactions__status='completed'))
        ).order_by('start_date')
    
    @staticmethod
    def get_event_performance_metrics(event):
        """Get comprehensive performance metrics for an event."""
        cache_key = f'event_metrics_{event.id}'
        metrics = cache.get(cache_key)
        
        if metrics is None:
            # Sales metrics
            sales_data = event.transactions.filter(status='completed').aggregate(
                total_revenue=Sum('total_amount'),
                total_transactions=Count('id'),
                total_tickets=Count('items__id'),
                average_transaction_value=Avg('total_amount'),
                first_sale=models.Min('completed_at'),
                last_sale=models.Max('completed_at')
            )
            
            # Capacity metrics
            capacity_data = event.zones.aggregate(
                total_capacity=Sum('capacity'),
                total_seats=Count('seats'),
                sold_seats=Count('seats', filter=Q(seats__status='sold')),
                available_seats=Count('seats', filter=Q(seats__status='available'))
            )
            
            # Calculate occupancy rate
            occupancy_rate = 0
            if capacity_data['total_seats'] and capacity_data['sold_seats']:
                occupancy_rate = (capacity_data['sold_seats'] / capacity_data['total_seats']) * 100
            
            metrics = {
                'sales': sales_data,
                'capacity': capacity_data,
                'occupancy_rate': round(occupancy_rate, 2),
                'last_updated': timezone.now().isoformat(),
            }
            
            # Cache for 5 minutes
            cache.set(cache_key, metrics, 300)
        
        return metrics