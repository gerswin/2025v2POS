"""
Database optimization utilities and services.
Provides centralized access to optimized queries and performance monitoring.
"""

from django.db import models, connection
from django.core.cache import cache
from django.conf import settings
import logging
import time
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class QueryOptimizer:
    """
    Centralized query optimization service.
    Provides optimized querysets for common use cases.
    """
    
    @staticmethod
    def get_events_with_zones_and_pricing(tenant=None):
        """Get events with zones, seats, and pricing data optimized."""
        from venezuelan_pos.apps.events.models import Event
        from venezuelan_pos.apps.zones.models import Zone, Seat
        from venezuelan_pos.apps.pricing.models import PriceStage
        
        queryset = Event.objects.select_related(
            'tenant',
            'venue'
        ).prefetch_related(
            models.Prefetch(
                'zones',
                queryset=Zone.objects.filter(status='active').select_related('tenant')
            ),
            models.Prefetch(
                'zones__seats',
                queryset=Seat.objects.filter(status='available').select_related('zone')
            ),
            models.Prefetch(
                'zones__price_stages',
                queryset=PriceStage.objects.filter(is_active=True).select_related('zone')
            ),
            'zones__row_pricing'
        )
        
        if tenant:
            queryset = queryset.filter(tenant=tenant)
        
        return queryset.filter(status='active')
    
    @staticmethod
    def get_transactions_with_complete_data(tenant=None, event=None):
        """Get transactions with all related data optimized."""
        from venezuelan_pos.apps.sales.models import Transaction, TransactionItem
        from venezuelan_pos.apps.payments.models import Payment
        
        queryset = Transaction.objects.select_related(
            'tenant',
            'event',
            'event__venue',
            'customer'
        ).prefetch_related(
            models.Prefetch(
                'items',
                queryset=TransactionItem.objects.select_related(
                    'zone',
                    'seat',
                    'seat__zone'
                ).order_by('created_at')
            ),
            models.Prefetch(
                'payments',
                queryset=Payment.objects.select_related('payment_method').order_by('-created_at')
            ),
            'reserved_tickets'
        )
        
        if tenant:
            queryset = queryset.filter(tenant=tenant)
        if event:
            queryset = queryset.filter(event=event)
        
        return queryset
    
    @staticmethod
    def get_zones_with_availability(event, zone_type=None):
        """Get zones with seat availability data optimized."""
        from venezuelan_pos.apps.zones.models import Zone, Seat
        from venezuelan_pos.apps.pricing.models import PriceStage
        
        queryset = Zone.objects.select_related(
            'tenant',
            'event'
        ).prefetch_related(
            models.Prefetch(
                'seats',
                queryset=Seat.objects.select_related('zone').order_by(
                    'row_number', 'seat_number'
                )
            ),
            models.Prefetch(
                'price_stages',
                queryset=PriceStage.objects.filter(is_active=True).order_by('stage_order')
            )
        ).filter(event=event, status='active')
        
        if zone_type:
            queryset = queryset.filter(zone_type=zone_type)
        
        return queryset
    
    @staticmethod
    def get_customers_with_transactions(tenant=None):
        """Get customers with their transaction history optimized."""
        from venezuelan_pos.apps.customers.models import Customer
        from venezuelan_pos.apps.sales.models import Transaction
        
        queryset = Customer.objects.select_related(
            'tenant',
            'preferences'
        ).prefetch_related(
            models.Prefetch(
                'transactions',
                queryset=Transaction.objects.filter(status='completed').select_related(
                    'event'
                ).order_by('-created_at')
            )
        )
        
        if tenant:
            queryset = queryset.filter(tenant=tenant)
        
        return queryset.filter(is_active=True)
    
    @staticmethod
    def get_price_stages_with_sales_data(event=None, zone=None):
        """Get price stages with sales tracking data optimized."""
        from venezuelan_pos.apps.pricing.models import PriceStage, StageSales, StageTransition
        
        queryset = PriceStage.objects.select_related(
            'tenant',
            'event',
            'zone'
        ).prefetch_related(
            models.Prefetch(
                'stage_sales',
                queryset=StageSales.objects.order_by('-sales_date')
            ),
            models.Prefetch(
                'transitions_from',
                queryset=StageTransition.objects.select_related('stage_to').order_by('-transition_at')
            )
        )
        
        if event:
            queryset = queryset.filter(event=event)
        if zone:
            queryset = queryset.filter(zone=zone)
        
        return queryset.filter(is_active=True)


class QueryPerformanceMonitor:
    """
    Query performance monitoring and optimization suggestions.
    """
    
    def __init__(self):
        self.query_log = []
        self.slow_query_threshold = getattr(settings, 'SLOW_QUERY_THRESHOLD', 0.1)  # 100ms
    
    @contextmanager
    def monitor_queries(self, operation_name="Unknown"):
        """Context manager to monitor query performance."""
        initial_queries = len(connection.queries)
        start_time = time.time()
        
        try:
            yield
        finally:
            end_time = time.time()
            execution_time = end_time - start_time
            query_count = len(connection.queries) - initial_queries
            
            # Log performance data
            performance_data = {
                'operation': operation_name,
                'execution_time': execution_time,
                'query_count': query_count,
                'queries': connection.queries[initial_queries:] if settings.DEBUG else []
            }
            
            self.query_log.append(performance_data)
            
            # Log slow operations
            if execution_time > self.slow_query_threshold:
                logger.warning(
                    f"Slow operation detected: {operation_name} took {execution_time:.3f}s "
                    f"with {query_count} queries"
                )
            
            # Log N+1 query problems
            if query_count > 10:
                logger.warning(
                    f"Potential N+1 query problem: {operation_name} executed {query_count} queries"
                )
    
    def get_performance_summary(self):
        """Get performance summary for recent operations."""
        if not self.query_log:
            return {}
        
        total_operations = len(self.query_log)
        total_time = sum(op['execution_time'] for op in self.query_log)
        total_queries = sum(op['query_count'] for op in self.query_log)
        slow_operations = [op for op in self.query_log if op['execution_time'] > self.slow_query_threshold]
        
        return {
            'total_operations': total_operations,
            'total_execution_time': total_time,
            'average_execution_time': total_time / total_operations,
            'total_queries': total_queries,
            'average_queries_per_operation': total_queries / total_operations,
            'slow_operations_count': len(slow_operations),
            'slow_operations_percentage': (len(slow_operations) / total_operations) * 100,
        }
    
    def clear_log(self):
        """Clear the performance log."""
        self.query_log.clear()


class DatabaseIndexAnalyzer:
    """
    Analyze database usage and suggest index optimizations.
    """
    
    @staticmethod
    def analyze_missing_indexes():
        """Analyze queries for missing indexes (PostgreSQL specific)."""
        if not settings.DEBUG:
            return []
        
        # This would analyze pg_stat_user_tables and pg_stat_user_indexes
        # For now, return common patterns that should have indexes
        suggestions = []
        
        # Check for common tenant-aware query patterns
        common_patterns = [
            "Consider adding indexes on (tenant_id, status) for frequently filtered models",
            "Consider adding indexes on (tenant_id, created_at) for date-based queries",
            "Consider adding indexes on foreign key fields used in joins",
            "Consider adding partial indexes for active/inactive status filtering",
        ]
        
        return common_patterns
    
    @staticmethod
    def get_index_usage_stats():
        """Get index usage statistics (PostgreSQL specific)."""
        if connection.vendor != 'postgresql':
            return {}
        
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    schemaname,
                    tablename,
                    indexname,
                    idx_tup_read,
                    idx_tup_fetch
                FROM pg_stat_user_indexes 
                ORDER BY idx_tup_read DESC
                LIMIT 20;
            """)
            
            results = cursor.fetchall()
            return [
                {
                    'schema': row[0],
                    'table': row[1],
                    'index': row[2],
                    'tuples_read': row[3],
                    'tuples_fetched': row[4]
                }
                for row in results
            ]


class CacheOptimizer:
    """
    Cache optimization utilities for database queries.
    """
    
    @staticmethod
    def cache_expensive_query(cache_key, query_func, timeout=300):
        """Cache the result of an expensive query."""
        result = cache.get(cache_key)
        if result is None:
            result = query_func()
            cache.set(cache_key, result, timeout)
        return result
    
    @staticmethod
    def invalidate_related_caches(model_name, instance_id=None):
        """Invalidate caches related to a model instance."""
        cache_patterns = [
            f"{model_name}_list",
            f"{model_name}_detail_{instance_id}" if instance_id else None,
            f"tenant_{model_name}",
        ]
        
        for pattern in cache_patterns:
            if pattern:
                cache.delete(pattern)
    
    @staticmethod
    def warm_cache_for_tenant(tenant):
        """Pre-warm cache with commonly accessed data for a tenant."""
        # This would pre-load frequently accessed data
        cache_keys = [
            f"tenant_{tenant.id}_active_events",
            f"tenant_{tenant.id}_zones_with_availability",
            f"tenant_{tenant.id}_price_stages",
        ]
        
        # Implementation would depend on specific caching strategy
        return cache_keys


# Global instances
query_monitor = QueryPerformanceMonitor()
query_optimizer = QueryOptimizer()
cache_optimizer = CacheOptimizer()
index_analyzer = DatabaseIndexAnalyzer()