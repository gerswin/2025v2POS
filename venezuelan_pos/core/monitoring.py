"""
Performance monitoring utilities for Venezuelan POS System.
"""

import time
import functools
import structlog
from typing import Dict, Any, Optional, Callable
from django.core.cache import cache
from django.db import connection
from django.conf import settings
from contextlib import contextmanager

# Prometheus metrics
try:
    from prometheus_client import Counter, Histogram, Gauge, Summary
    
    # Business metrics
    TICKET_SALES_COUNTER = Counter(
        'venezuelan_pos_ticket_sales_total',
        'Total number of tickets sold',
        ['event_id', 'zone_id', 'payment_method', 'tenant_id']
    )
    
    REVENUE_COUNTER = Counter(
        'venezuelan_pos_revenue_total',
        'Total revenue generated in USD',
        ['event_id', 'zone_id', 'payment_method', 'tenant_id']
    )
    
    PAYMENT_DURATION_HISTOGRAM = Histogram(
        'venezuelan_pos_payment_processing_duration_seconds',
        'Payment processing time',
        ['payment_method', 'success'],
        buckets=(.01, .025, .05, .075, .1, .25, .5, .75, 1.0, 2.5, 5.0, 7.5, 10.0, float("inf"))
    )
    
    STAGE_TRANSITIONS_COUNTER = Counter(
        'venezuelan_pos_stage_transitions_total',
        'Total number of pricing stage transitions',
        ['event_id', 'zone_id', 'trigger', 'tenant_id']
    )
    
    NOTIFICATION_DURATION_HISTOGRAM = Histogram(
        'venezuelan_pos_notification_delivery_duration_seconds',
        'Notification delivery time',
        ['channel', 'success'],
        buckets=(.1, .25, .5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, float("inf"))
    )
    
    DATABASE_QUERY_DURATION = Histogram(
        'venezuelan_pos_database_query_duration_seconds',
        'Database query execution time',
        ['operation', 'table'],
        buckets=(.001, .005, .01, .025, .05, .1, .25, .5, 1.0, 2.5, 5.0, float("inf"))
    )
    
    CACHE_OPERATIONS_COUNTER = Counter(
        'venezuelan_pos_cache_operations_total',
        'Total cache operations',
        ['operation', 'result']
    )
    
    FISCAL_SERIES_COUNTER = Counter(
        'venezuelan_pos_fiscal_series_generated_total',
        'Total fiscal series numbers generated',
        ['tenant_id']
    )
    
    ACTIVE_USERS_GAUGE = Gauge(
        'venezuelan_pos_active_users',
        'Number of currently active users',
        ['tenant_id']
    )
    
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

# Get structured logger
logger = structlog.get_logger('venezuelan_pos.performance')


class PerformanceMonitor:
    """
    Centralized performance monitoring service.
    """
    
    def __init__(self):
        self.metrics = {}
        self.enabled = getattr(settings, 'PERFORMANCE_MONITORING', {}).get('ENABLE_REQUEST_PROFILING', False)
    
    def track_metric(self, name: str, value: float, tags: Optional[Dict[str, Any]] = None):
        """Track a custom metric."""
        if not self.enabled:
            return
        
        logger.info(
            "custom_metric",
            metric_name=name,
            value=value,
            tags=tags or {},
        )
    
    def increment_counter(self, name: str, tags: Optional[Dict[str, Any]] = None):
        """Increment a counter metric."""
        if not self.enabled:
            return
        
        cache_key = f"metric_counter_{name}"
        current_value = cache.get(cache_key, 0)
        new_value = current_value + 1
        cache.set(cache_key, new_value, timeout=3600)  # 1 hour
        
        logger.info(
            "counter_metric",
            metric_name=name,
            value=new_value,
            tags=tags or {},
        )
    
    def track_database_performance(self, operation: str, table: str = None):
        """Track database operation performance."""
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                if not self.enabled:
                    return func(*args, **kwargs)
                
                start_queries = len(connection.queries)
                start_time = time.time()
                
                try:
                    result = func(*args, **kwargs)
                    success = True
                except Exception as e:
                    success = False
                    raise
                finally:
                    duration = time.time() - start_time
                    query_count = len(connection.queries) - start_queries
                    
                    # Track in Prometheus
                    BusinessMetrics.track_database_operation(
                        operation=operation or 'unknown',
                        table=table or 'unknown',
                        duration_seconds=duration
                    )
                    
                    logger.info(
                        "database_operation",
                        operation=operation,
                        table=table,
                        duration_ms=round(duration * 1000, 2),
                        query_count=query_count,
                        success=success,
                        function=func.__name__,
                    )
                
                return result
            return wrapper
        return decorator
    
    def track_cache_performance(self, operation: str, cache_key: str = None):
        """Track cache operation performance."""
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                if not self.enabled:
                    return func(*args, **kwargs)
                
                start_time = time.time()
                
                try:
                    result = func(*args, **kwargs)
                    success = True
                    hit = result is not None if operation == 'get' else True
                except Exception as e:
                    success = False
                    hit = False
                    raise
                finally:
                    duration = time.time() - start_time
                    
                    # Track in Prometheus
                    if operation == 'get':
                        BusinessMetrics.track_cache_operation(operation, hit)
                    
                    logger.info(
                        "cache_operation",
                        operation=operation,
                        cache_key=cache_key,
                        duration_ms=round(duration * 1000, 2),
                        success=success,
                        hit=hit if operation == 'get' else None,
                        function=func.__name__,
                    )
                
                return result
            return wrapper
        return decorator
    
    @contextmanager
    def measure_time(self, operation_name: str, tags: Optional[Dict[str, Any]] = None):
        """Context manager to measure operation time."""
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            self.track_metric(
                f"{operation_name}_duration_ms",
                round(duration * 1000, 2),
                tags
            )


# Global performance monitor instance
performance_monitor = PerformanceMonitor()


def track_performance(operation: str, **tags):
    """Decorator to track function performance."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with performance_monitor.measure_time(operation, tags):
                return func(*args, **kwargs)
        return wrapper
    return decorator


def track_database_queries(operation: str, table: str = None):
    """Decorator to track database query performance."""
    return performance_monitor.track_database_performance(operation, table)


def track_cache_operations(operation: str, cache_key: str = None):
    """Decorator to track cache operation performance."""
    return performance_monitor.track_cache_performance(operation, cache_key)


class BusinessMetrics:
    """
    Business-specific metrics tracking with Prometheus integration.
    """
    
    @staticmethod
    def track_ticket_sale(event_id: str, zone_id: str, amount: float, payment_method: str, tenant_id: str = None):
        """Track ticket sale metrics."""
        logger.info(
            "ticket_sale",
            event_id=event_id,
            zone_id=zone_id,
            amount=amount,
            payment_method=payment_method,
            tenant_id=tenant_id,
            metric_type="business",
        )
        
        # Prometheus metrics
        if PROMETHEUS_AVAILABLE:
            TICKET_SALES_COUNTER.labels(
                event_id=event_id,
                zone_id=zone_id,
                payment_method=payment_method,
                tenant_id=tenant_id or 'unknown'
            ).inc()
            
            REVENUE_COUNTER.labels(
                event_id=event_id,
                zone_id=zone_id,
                payment_method=payment_method,
                tenant_id=tenant_id or 'unknown'
            ).inc(amount)
        
        # Increment counters
        performance_monitor.increment_counter("tickets_sold", {
            "event_id": event_id,
            "zone_id": zone_id,
            "payment_method": payment_method,
            "tenant_id": tenant_id,
        })
        
        performance_monitor.track_metric("ticket_revenue", amount, {
            "event_id": event_id,
            "zone_id": zone_id,
            "payment_method": payment_method,
            "tenant_id": tenant_id,
        })
    
    @staticmethod
    def track_payment_processing(payment_method: str, amount: float, success: bool, duration_ms: float):
        """Track payment processing metrics."""
        logger.info(
            "payment_processing",
            payment_method=payment_method,
            amount=amount,
            success=success,
            duration_ms=duration_ms,
            metric_type="business",
        )
        
        # Prometheus metrics
        if PROMETHEUS_AVAILABLE:
            PAYMENT_DURATION_HISTOGRAM.labels(
                payment_method=payment_method,
                success=str(success)
            ).observe(duration_ms / 1000.0)  # Convert to seconds
        
        performance_monitor.increment_counter("payments_processed", {
            "payment_method": payment_method,
            "success": success,
        })
    
    @staticmethod
    def track_stage_transition(event_id: str, zone_id: str, from_stage: str, to_stage: str, trigger: str, tenant_id: str = None):
        """Track pricing stage transitions."""
        logger.info(
            "stage_transition",
            event_id=event_id,
            zone_id=zone_id,
            from_stage=from_stage,
            to_stage=to_stage,
            trigger=trigger,
            tenant_id=tenant_id,
            metric_type="business",
        )
        
        # Prometheus metrics
        if PROMETHEUS_AVAILABLE:
            STAGE_TRANSITIONS_COUNTER.labels(
                event_id=event_id,
                zone_id=zone_id,
                trigger=trigger,
                tenant_id=tenant_id or 'unknown'
            ).inc()
        
        performance_monitor.increment_counter("stage_transitions", {
            "event_id": event_id,
            "zone_id": zone_id,
            "trigger": trigger,
            "tenant_id": tenant_id,
        })
    
    @staticmethod
    def track_notification_delivery(channel: str, success: bool, duration_ms: float):
        """Track notification delivery metrics."""
        logger.info(
            "notification_delivery",
            channel=channel,
            success=success,
            duration_ms=duration_ms,
            metric_type="business",
        )
        
        # Prometheus metrics
        if PROMETHEUS_AVAILABLE:
            NOTIFICATION_DURATION_HISTOGRAM.labels(
                channel=channel,
                success=str(success)
            ).observe(duration_ms / 1000.0)  # Convert to seconds
        
        performance_monitor.increment_counter("notifications_sent", {
            "channel": channel,
            "success": success,
        })
    
    @staticmethod
    def track_fiscal_series_generation(tenant_id: str):
        """Track fiscal series generation."""
        logger.info(
            "fiscal_series_generated",
            tenant_id=tenant_id,
            metric_type="business",
        )
        
        # Prometheus metrics
        if PROMETHEUS_AVAILABLE:
            FISCAL_SERIES_COUNTER.labels(tenant_id=tenant_id).inc()
    
    @staticmethod
    def track_database_operation(operation: str, table: str, duration_seconds: float):
        """Track database operation metrics."""
        if PROMETHEUS_AVAILABLE:
            DATABASE_QUERY_DURATION.labels(
                operation=operation,
                table=table
            ).observe(duration_seconds)
    
    @staticmethod
    def track_cache_operation(operation: str, hit: bool):
        """Track cache operation metrics."""
        if PROMETHEUS_AVAILABLE:
            result = 'hit' if hit else 'miss'
            CACHE_OPERATIONS_COUNTER.labels(
                operation=operation,
                result=result
            ).inc()
    
    @staticmethod
    def update_active_users(tenant_id: str, count: int):
        """Update active users gauge."""
        if PROMETHEUS_AVAILABLE:
            ACTIVE_USERS_GAUGE.labels(tenant_id=tenant_id).set(count)


class SystemHealthMonitor:
    """
    System health monitoring utilities.
    """
    
    @staticmethod
    def check_database_health():
        """Check database connectivity and performance."""
        try:
            start_time = time.time()
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            duration = time.time() - start_time
            
            logger.info(
                "health_check",
                component="database",
                status="healthy",
                response_time_ms=round(duration * 1000, 2),
            )
            return True, duration
        except Exception as e:
            logger.error(
                "health_check",
                component="database",
                status="unhealthy",
                error=str(e),
            )
            return False, None
    
    @staticmethod
    def check_cache_health():
        """Check cache connectivity and performance."""
        try:
            start_time = time.time()
            cache.set("health_check", "ok", timeout=60)
            result = cache.get("health_check")
            duration = time.time() - start_time
            
            if result == "ok":
                logger.info(
                    "health_check",
                    component="cache",
                    status="healthy",
                    response_time_ms=round(duration * 1000, 2),
                )
                return True, duration
            else:
                logger.warning(
                    "health_check",
                    component="cache",
                    status="unhealthy",
                    error="Cache read/write failed",
                )
                return False, None
        except Exception as e:
            logger.error(
                "health_check",
                component="cache",
                status="unhealthy",
                error=str(e),
            )
            return False, None
    
    @staticmethod
    def check_celery_health():
        """Check Celery worker connectivity."""
        try:
            from celery import current_app
            start_time = time.time()
            
            # Check if workers are available
            inspect = current_app.control.inspect()
            stats = inspect.stats()
            duration = time.time() - start_time
            
            if stats:
                logger.info(
                    "health_check",
                    component="celery",
                    status="healthy",
                    worker_count=len(stats),
                    response_time_ms=round(duration * 1000, 2),
                )
                return True, duration
            else:
                logger.warning(
                    "health_check",
                    component="celery",
                    status="unhealthy",
                    error="No workers available",
                )
                return False, None
        except Exception as e:
            logger.error(
                "health_check",
                component="celery",
                status="unhealthy",
                error=str(e),
            )
            return False, None