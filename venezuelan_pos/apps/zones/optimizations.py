"""
Optimized managers and querysets for zone models.
"""

from django.db import models
from django.db.models import Prefetch, Q, F, Count, Sum, Case, When
from django.core.cache import cache
from django.utils import timezone


class OptimizedZoneManager(models.Manager):
    """Optimized manager for Zone model."""
    
    def get_with_availability(self):
        """Get zones with seat availability data."""
        return self.select_related(
            'tenant',
            'event',
            'event__venue'
        ).annotate(
            total_seats=Count('seats'),
            available_seats=Count('seats', filter=Q(seats__status='available')),
            sold_seats=Count('seats', filter=Q(seats__status='sold')),
            reserved_seats=Count('seats', filter=Q(seats__status='reserved')),
            occupancy_rate=Case(
                When(capacity=0, then=0),
                default=F('sold_seats') * 100.0 / F('capacity')
            )
        )
    
    def get_with_pricing(self):
        """Get zones with pricing information."""
        return self.select_related(
            'tenant',
            'event'
        ).prefetch_related(
            Prefetch(
                'price_stages',
                queryset=models.QuerySet().filter(is_active=True).order_by('stage_order')
            ),
            'row_pricing'
        )
    
    def get_numbered_zones_with_seats(self):
        """Get numbered zones with seat data."""
        return self.filter(zone_type='numbered').select_related(
            'tenant',
            'event'
        ).prefetch_related(
            Prefetch(
                'seats',
                queryset=models.QuerySet().order_by('row_number', 'seat_number')
            ),
            Prefetch(
                'tables',
                queryset=models.QuerySet().prefetch_related('seats')
            )
        ).annotate(
            seat_count=Count('seats'),
            available_count=Count('seats', filter=Q(seats__status='available'))
        )
    
    def get_general_zones_with_capacity(self):
        """Get general admission zones with capacity tracking."""
        return self.filter(zone_type='general').select_related(
            'tenant',
            'event'
        ).annotate(
            tickets_sold=Count('transaction_items', filter=Q(
                transaction_items__transaction__status='completed'
            )),
            remaining_capacity=F('capacity') - F('tickets_sold')
        )
    
    def get_zones_for_event(self, event):
        """Get all zones for an event with complete data."""
        return self.filter(event=event).select_related(
            'tenant'
        ).prefetch_related(
            Prefetch(
                'seats',
                queryset=models.QuerySet().order_by('row_number', 'seat_number')
            ),
            Prefetch(
                'price_stages',
                queryset=models.QuerySet().filter(is_active=True).order_by('stage_order')
            ),
            'row_pricing',
            'tables'
        ).annotate(
            available_seats=Count('seats', filter=Q(seats__status='available')),
            sold_seats=Count('seats', filter=Q(seats__status='sold'))
        )
    
    def search_zones(self, query, event=None):
        """Search zones by name or description."""
        queryset = self.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query)
        ).select_related('tenant', 'event')
        
        if event:
            queryset = queryset.filter(event=event)
        
        return queryset.order_by('name')


class OptimizedSeatManager(models.Manager):
    """Optimized manager for Seat model."""
    
    def get_with_zone_data(self):
        """Get seats with zone information."""
        return self.select_related(
            'zone',
            'zone__event',
            'zone__tenant'
        )
    
    def get_available_seats(self, zone=None):
        """Get available seats."""
        queryset = self.filter(status='available').select_related('zone')
        
        if zone:
            queryset = queryset.filter(zone=zone)
        
        return queryset.order_by('row_number', 'seat_number')
    
    def get_sold_seats(self, zone=None):
        """Get sold seats."""
        queryset = self.filter(status='sold').select_related('zone')
        
        if zone:
            queryset = queryset.filter(zone=zone)
        
        return queryset.order_by('row_number', 'seat_number')
    
    def get_reserved_seats(self, zone=None):
        """Get reserved seats."""
        queryset = self.filter(status='reserved').select_related('zone')
        
        if zone:
            queryset = queryset.filter(zone=zone)
        
        return queryset.order_by('row_number', 'seat_number')
    
    def get_seats_by_row(self, zone, row_number):
        """Get seats in a specific row."""
        return self.filter(
            zone=zone,
            row_number=row_number
        ).select_related('zone').order_by('seat_number')
    
    def get_seats_in_range(self, zone, start_row, end_row, start_seat=None, end_seat=None):
        """Get seats in a range of rows and optionally seat numbers."""
        queryset = self.filter(
            zone=zone,
            row_number__gte=start_row,
            row_number__lte=end_row
        )
        
        if start_seat is not None:
            queryset = queryset.filter(seat_number__gte=start_seat)
        
        if end_seat is not None:
            queryset = queryset.filter(seat_number__lte=end_seat)
        
        return queryset.select_related('zone').order_by('row_number', 'seat_number')


class OptimizedTableManager(models.Manager):
    """Optimized manager for Table model."""
    
    def get_with_seats(self):
        """Get tables with seat information."""
        return self.select_related(
            'zone',
            'zone__event',
            'zone__tenant'
        ).prefetch_related(
            Prefetch(
                'seats',
                queryset=models.QuerySet().order_by('row_number', 'seat_number')
            )
        ).annotate(
            seat_count=Count('seats'),
            available_seats=Count('seats', filter=Q(seats__status='available')),
            sold_seats=Count('seats', filter=Q(seats__status='sold'))
        )
    
    def get_available_tables(self, zone=None):
        """Get tables that are completely available."""
        queryset = self.annotate(
            total_seats=Count('seats'),
            available_seats=Count('seats', filter=Q(seats__status='available'))
        ).filter(
            total_seats=F('available_seats')  # All seats are available
        ).select_related('zone')
        
        if zone:
            queryset = queryset.filter(zone=zone)
        
        return queryset.order_by('name')
    
    def get_partially_sold_tables(self, zone=None):
        """Get tables that are partially sold."""
        queryset = self.annotate(
            total_seats=Count('seats'),
            available_seats=Count('seats', filter=Q(seats__status='available')),
            sold_seats=Count('seats', filter=Q(seats__status='sold'))
        ).filter(
            sold_seats__gt=0,
            available_seats__gt=0
        ).select_related('zone')
        
        if zone:
            queryset = queryset.filter(zone=zone)
        
        return queryset.order_by('name')


class ZoneQueryOptimizer:
    """Utility class for optimizing zone-related queries."""
    
    @staticmethod
    def get_zone_availability_summary(zone):
        """Get comprehensive availability summary for a zone."""
        cache_key = f'zone_availability_{zone.id}'
        summary = cache.get(cache_key)
        
        if summary is None:
            if zone.zone_type == 'numbered':
                # For numbered zones, count seats
                seat_data = zone.seats.aggregate(
                    total_seats=Count('id'),
                    available_seats=Count('id', filter=Q(status='available')),
                    sold_seats=Count('id', filter=Q(status='sold')),
                    reserved_seats=Count('id', filter=Q(status='reserved'))
                )
                
                # Get table data if applicable
                table_data = zone.tables.annotate(
                    table_seats=Count('seats'),
                    table_available=Count('seats', filter=Q(seats__status='available'))
                ).aggregate(
                    total_tables=Count('id'),
                    available_tables=Count('id', filter=Q(table_seats=F('table_available')))
                )
                
                summary = {
                    'zone_type': 'numbered',
                    'capacity': zone.capacity,
                    'seats': seat_data,
                    'tables': table_data,
                    'occupancy_rate': (seat_data['sold_seats'] / seat_data['total_seats'] * 100) if seat_data['total_seats'] > 0 else 0,
                }
            
            else:  # general admission
                # For general zones, count transaction items
                tickets_sold = zone.transaction_items.filter(
                    transaction__status='completed'
                ).count()
                
                summary = {
                    'zone_type': 'general',
                    'capacity': zone.capacity,
                    'tickets_sold': tickets_sold,
                    'remaining_capacity': zone.capacity - tickets_sold,
                    'occupancy_rate': (tickets_sold / zone.capacity * 100) if zone.capacity > 0 else 0,
                }
            
            summary['last_updated'] = timezone.now().isoformat()
            
            # Cache for 30 seconds (needs frequent updates during sales)
            cache.set(cache_key, summary, 30)
        
        return summary
    
    @staticmethod
    def get_zone_seat_map(zone):
        """Get optimized seat map data for a numbered zone."""
        if zone.zone_type != 'numbered':
            return None
        
        cache_key = f'zone_seat_map_{zone.id}'
        seat_map = cache.get(cache_key)
        
        if seat_map is None:
            # Get seats organized by row
            seats_by_row = {}
            seats = zone.seats.order_by('row_number', 'seat_number').values(
                'id', 'row_number', 'seat_number', 'status'
            )
            
            for seat in seats:
                row = seat['row_number']
                if row not in seats_by_row:
                    seats_by_row[row] = []
                seats_by_row[row].append({
                    'id': str(seat['id']),
                    'seat_number': seat['seat_number'],
                    'status': seat['status']
                })
            
            # Get tables if any
            tables = []
            if zone.tables.exists():
                tables_data = zone.tables.prefetch_related('seats').all()
                for table in tables_data:
                    table_seats = [
                        {
                            'id': str(seat.id),
                            'row_number': seat.row_number,
                            'seat_number': seat.seat_number,
                            'status': seat.status
                        }
                        for seat in table.seats.all()
                    ]
                    tables.append({
                        'id': str(table.id),
                        'name': table.name,
                        'seats': table_seats
                    })
            
            seat_map = {
                'zone_id': str(zone.id),
                'zone_name': zone.name,
                'rows': zone.rows,
                'seats_per_row': zone.seats_per_row,
                'seats_by_row': seats_by_row,
                'tables': tables,
                'last_updated': timezone.now().isoformat(),
            }
            
            # Cache for 15 seconds (frequent updates needed)
            cache.set(cache_key, seat_map, 15)
        
        return seat_map
    
    @staticmethod
    def get_zone_pricing_info(zone):
        """Get current pricing information for a zone."""
        cache_key = f'zone_pricing_{zone.id}'
        pricing_info = cache.get(cache_key)
        
        if pricing_info is None:
            # Get current active price stage
            current_stage = zone.price_stages.filter(
                is_active=True,
                start_date__lte=timezone.now(),
                end_date__gte=timezone.now()
            ).first()
            
            # Get row pricing
            row_pricing = list(zone.row_pricing.values(
                'row_number', 'price_modifier'
            ).order_by('row_number'))
            
            pricing_info = {
                'zone_id': str(zone.id),
                'base_price': float(zone.base_price),
                'current_stage': {
                    'id': str(current_stage.id),
                    'name': current_stage.name,
                    'modifier_type': current_stage.modifier_type,
                    'modifier_value': float(current_stage.modifier_value),
                    'start_date': current_stage.start_date.isoformat(),
                    'end_date': current_stage.end_date.isoformat(),
                } if current_stage else None,
                'row_pricing': row_pricing,
                'last_updated': timezone.now().isoformat(),
            }
            
            # Cache for 1 minute
            cache.set(cache_key, pricing_info, 60)
        
        return pricing_info
    
    @staticmethod
    def invalidate_zone_cache(zone_id):
        """Invalidate all cached data for a zone."""
        cache_keys = [
            f'zone_availability_{zone_id}',
            f'zone_seat_map_{zone_id}',
            f'zone_pricing_{zone_id}',
        ]
        
        cache.delete_many(cache_keys)
    
    @staticmethod
    def get_zones_performance_summary(event):
        """Get performance summary for all zones in an event."""
        cache_key = f'zones_performance_{event.id}'
        summary = cache.get(cache_key)
        
        if summary is None:
            zones_data = []
            
            for zone in event.zones.all():
                zone_summary = ZoneQueryOptimizer.get_zone_availability_summary(zone)
                
                # Add revenue data
                revenue_data = zone.transaction_items.filter(
                    transaction__status='completed'
                ).aggregate(
                    total_revenue=Sum('total_price'),
                    ticket_count=Count('id'),
                    average_price=models.Avg('total_price')
                )
                
                zone_summary.update({
                    'revenue': revenue_data,
                })
                
                zones_data.append(zone_summary)
            
            summary = {
                'event_id': str(event.id),
                'zones': zones_data,
                'last_updated': timezone.now().isoformat(),
            }
            
            # Cache for 2 minutes
            cache.set(cache_key, summary, 120)
        
        return summary