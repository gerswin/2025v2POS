"""
Custom health checks for Venezuelan POS System.
"""

from django.core.cache import cache
from django.db import connection
from health_check.backends import BaseHealthCheckBackend
from health_check.exceptions import ServiceUnavailable, ServiceReturnedUnexpectedResult
import redis
import time
import structlog

logger = structlog.get_logger('venezuelan_pos.health')


class DatabasePerformanceHealthCheck(BaseHealthCheckBackend):
    """
    Health check that monitors database performance.
    """
    critical_service = True
    
    def check_status(self):
        """Check database performance and connectivity."""
        try:
            start_time = time.time()
            
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            
            duration = time.time() - start_time
            
            # Check if response time is acceptable (< 100ms)
            if duration > 0.1:
                logger.warning(
                    "database_slow_response",
                    duration_ms=duration * 1000,
                    threshold_ms=100,
                )
                raise ServiceReturnedUnexpectedResult(
                    f"Database response time too slow: {duration * 1000:.2f}ms"
                )
            
            logger.info(
                "database_health_check_passed",
                duration_ms=duration * 1000,
            )
            
        except Exception as e:
            logger.error(
                "database_health_check_failed",
                error=str(e),
            )
            raise ServiceUnavailable(f"Database health check failed: {str(e)}")
    
    def identifier(self):
        return self.__class__.__name__


class CachePerformanceHealthCheck(BaseHealthCheckBackend):
    """
    Health check that monitors cache performance.
    """
    critical_service = True
    
    def check_status(self):
        """Check cache performance and connectivity."""
        try:
            start_time = time.time()
            
            # Test cache write and read
            test_key = "health_check_test"
            test_value = "health_check_value"
            
            cache.set(test_key, test_value, timeout=60)
            retrieved_value = cache.get(test_key)
            
            duration = time.time() - start_time
            
            # Verify the value was stored and retrieved correctly
            if retrieved_value != test_value:
                raise ServiceReturnedUnexpectedResult(
                    f"Cache returned unexpected value: {retrieved_value}"
                )
            
            # Check if response time is acceptable (< 50ms)
            if duration > 0.05:
                logger.warning(
                    "cache_slow_response",
                    duration_ms=duration * 1000,
                    threshold_ms=50,
                )
                raise ServiceReturnedUnexpectedResult(
                    f"Cache response time too slow: {duration * 1000:.2f}ms"
                )
            
            # Clean up
            cache.delete(test_key)
            
            logger.info(
                "cache_health_check_passed",
                duration_ms=duration * 1000,
            )
            
        except Exception as e:
            logger.error(
                "cache_health_check_failed",
                error=str(e),
            )
            raise ServiceUnavailable(f"Cache health check failed: {str(e)}")
    
    def identifier(self):
        return self.__class__.__name__


class RedisConnectionHealthCheck(BaseHealthCheckBackend):
    """
    Health check for Redis connection and performance.
    """
    critical_service = True
    
    def check_status(self):
        """Check Redis connectivity and performance."""
        try:
            from django.conf import settings
            
            # Get Redis URL from cache configuration
            redis_url = settings.CACHES['default']['LOCATION']
            
            # Create Redis connection
            r = redis.Redis.from_url(redis_url)
            
            start_time = time.time()
            
            # Test Redis operations
            r.ping()
            r.set("health_check_redis", "ok", ex=60)
            result = r.get("health_check_redis")
            
            duration = time.time() - start_time
            
            if result != b"ok":
                raise ServiceReturnedUnexpectedResult(
                    f"Redis returned unexpected value: {result}"
                )
            
            # Check if response time is acceptable (< 10ms)
            if duration > 0.01:
                logger.warning(
                    "redis_slow_response",
                    duration_ms=duration * 1000,
                    threshold_ms=10,
                )
            
            # Clean up
            r.delete("health_check_redis")
            
            logger.info(
                "redis_health_check_passed",
                duration_ms=duration * 1000,
            )
            
        except Exception as e:
            logger.error(
                "redis_health_check_failed",
                error=str(e),
            )
            raise ServiceUnavailable(f"Redis health check failed: {str(e)}")
    
    def identifier(self):
        return self.__class__.__name__


class CeleryHealthCheck(BaseHealthCheckBackend):
    """
    Health check for Celery workers.
    """
    critical_service = False  # Non-critical for basic functionality
    
    def check_status(self):
        """Check Celery worker availability."""
        try:
            from celery import current_app
            
            start_time = time.time()
            
            # Check if workers are available
            inspect = current_app.control.inspect()
            stats = inspect.stats()
            
            duration = time.time() - start_time
            
            if not stats:
                logger.warning("no_celery_workers_available")
                raise ServiceReturnedUnexpectedResult("No Celery workers available")
            
            # Check worker health
            active_workers = len(stats)
            if active_workers < 1:
                raise ServiceReturnedUnexpectedResult(
                    f"Insufficient Celery workers: {active_workers}"
                )
            
            logger.info(
                "celery_health_check_passed",
                active_workers=active_workers,
                duration_ms=duration * 1000,
            )
            
        except Exception as e:
            logger.error(
                "celery_health_check_failed",
                error=str(e),
            )
            raise ServiceUnavailable(f"Celery health check failed: {str(e)}")
    
    def identifier(self):
        return self.__class__.__name__


class TenantDataIntegrityHealthCheck(BaseHealthCheckBackend):
    """
    Health check for tenant data integrity.
    """
    critical_service = True
    
    def check_status(self):
        """Check tenant data integrity."""
        try:
            from venezuelan_pos.apps.tenants.models import Tenant
            
            start_time = time.time()
            
            # Check if we have at least one active tenant
            active_tenants = Tenant.objects.filter(is_active=True).count()
            
            if active_tenants == 0:
                logger.warning("no_active_tenants")
                raise ServiceReturnedUnexpectedResult("No active tenants found")
            
            # Check for orphaned data (basic integrity check)
            from venezuelan_pos.apps.events.models import Event
            events_without_tenant = Event.objects.filter(tenant__isnull=True).count()
            
            if events_without_tenant > 0:
                logger.warning(
                    "orphaned_events_detected",
                    count=events_without_tenant,
                )
                raise ServiceReturnedUnexpectedResult(
                    f"Found {events_without_tenant} events without tenant"
                )
            
            duration = time.time() - start_time
            
            logger.info(
                "tenant_integrity_check_passed",
                active_tenants=active_tenants,
                duration_ms=duration * 1000,
            )
            
        except Exception as e:
            logger.error(
                "tenant_integrity_check_failed",
                error=str(e),
            )
            raise ServiceUnavailable(f"Tenant integrity check failed: {str(e)}")
    
    def identifier(self):
        return self.__class__.__name__


class FiscalSeriesIntegrityHealthCheck(BaseHealthCheckBackend):
    """
    Health check for fiscal series integrity.
    """
    critical_service = True
    
    def check_status(self):
        """Check fiscal series integrity."""
        try:
            from venezuelan_pos.apps.sales.models import Transaction
            from django.db.models import Count
            
            start_time = time.time()
            
            # Check for duplicate fiscal series
            duplicates = (
                Transaction.objects
                .values('fiscal_series')
                .annotate(count=Count('fiscal_series'))
                .filter(count__gt=1, fiscal_series__isnull=False)
            )
            
            duplicate_count = duplicates.count()
            if duplicate_count > 0:
                logger.error(
                    "duplicate_fiscal_series_detected",
                    duplicate_count=duplicate_count,
                )
                raise ServiceReturnedUnexpectedResult(
                    f"Found {duplicate_count} duplicate fiscal series"
                )
            
            duration = time.time() - start_time
            
            logger.info(
                "fiscal_integrity_check_passed",
                duration_ms=duration * 1000,
            )
            
        except Exception as e:
            logger.error(
                "fiscal_integrity_check_failed",
                error=str(e),
            )
            raise ServiceUnavailable(f"Fiscal integrity check failed: {str(e)}")
    
    def identifier(self):
        return self.__class__.__name__