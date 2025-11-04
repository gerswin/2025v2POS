"""
Performance monitoring middleware for Venezuelan POS System.
"""

import time
import logging
import structlog
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin
from django.db import connection
from django.core.cache import cache

# Get structured logger
logger = structlog.get_logger('venezuelan_pos.performance')
security_logger = structlog.get_logger('venezuelan_pos.security')


class PerformanceMonitoringMiddleware(MiddlewareMixin):
    """
    Middleware to monitor request performance and log metrics.
    """
    
    def process_request(self, request):
        """Start timing the request."""
        request._performance_start_time = time.time()
        request._performance_queries_start = len(connection.queries)
        return None
    
    def process_response(self, request, response):
        """Log performance metrics for the request."""
        if not hasattr(request, '_performance_start_time'):
            return response
        
        # Calculate timing
        duration = time.time() - request._performance_start_time
        query_count = len(connection.queries) - request._performance_queries_start
        
        # Get tenant info if available
        tenant_id = getattr(request, 'tenant_id', None)
        user_id = request.user.id if request.user.is_authenticated else None
        
        # Log performance metrics
        logger.info(
            "request_completed",
            method=request.method,
            path=request.path,
            status_code=response.status_code,
            duration_ms=round(duration * 1000, 2),
            query_count=query_count,
            tenant_id=str(tenant_id) if tenant_id else None,
            user_id=user_id,
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            remote_addr=self._get_client_ip(request),
        )
        
        # Log slow requests
        slow_threshold = getattr(settings, 'PERFORMANCE_MONITORING', {}).get('SLOW_QUERY_THRESHOLD', 0.5)
        if duration > slow_threshold:
            logger.warning(
                "slow_request_detected",
                method=request.method,
                path=request.path,
                duration_ms=round(duration * 1000, 2),
                query_count=query_count,
                tenant_id=str(tenant_id) if tenant_id else None,
                user_id=user_id,
            )
        
        # Log excessive database queries
        if query_count > 10:
            logger.warning(
                "excessive_queries_detected",
                method=request.method,
                path=request.path,
                query_count=query_count,
                duration_ms=round(duration * 1000, 2),
                tenant_id=str(tenant_id) if tenant_id else None,
            )
        
        return response
    
    def _get_client_ip(self, request):
        """Get the client IP address from the request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class SecurityMonitoringMiddleware(MiddlewareMixin):
    """
    Middleware to monitor security events and suspicious activities.
    """
    
    def process_request(self, request):
        """Monitor for suspicious request patterns."""
        # Log authentication attempts
        if request.path.startswith('/auth/'):
            security_logger.info(
                "auth_attempt",
                path=request.path,
                method=request.method,
                remote_addr=self._get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
            )
        
        # Monitor for potential attacks
        self._check_suspicious_patterns(request)
        
        return None
    
    def process_response(self, request, response):
        """Log security-relevant responses."""
        # Log failed authentication attempts
        if (request.path.startswith('/auth/') and 
            response.status_code in [401, 403]):
            security_logger.warning(
                "auth_failure",
                path=request.path,
                status_code=response.status_code,
                remote_addr=self._get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
            )
        
        # Log admin access
        if (request.path.startswith('/admin/') and 
            response.status_code == 200 and 
            request.user.is_authenticated):
            security_logger.info(
                "admin_access",
                path=request.path,
                user_id=request.user.id,
                username=request.user.username,
                remote_addr=self._get_client_ip(request),
            )
        
        return response
    
    def _check_suspicious_patterns(self, request):
        """Check for suspicious request patterns."""
        # Check for SQL injection attempts
        suspicious_params = ['union', 'select', 'drop', 'delete', 'insert', 'update']
        query_string = request.META.get('QUERY_STRING', '').lower()
        
        for param in suspicious_params:
            if param in query_string:
                security_logger.warning(
                    "suspicious_sql_pattern",
                    pattern=param,
                    query_string=query_string,
                    path=request.path,
                    remote_addr=self._get_client_ip(request),
                )
                break
        
        # Check for XSS attempts
        if '<script' in query_string or 'javascript:' in query_string:
            security_logger.warning(
                "suspicious_xss_pattern",
                query_string=query_string,
                path=request.path,
                remote_addr=self._get_client_ip(request),
            )
    
    def _get_client_ip(self, request):
        """Get the client IP address from the request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class CacheMonitoringMiddleware(MiddlewareMixin):
    """
    Middleware to monitor cache performance and hit rates.
    """
    
    def process_request(self, request):
        """Initialize cache monitoring for the request."""
        request._cache_hits = 0
        request._cache_misses = 0
        return None
    
    def process_response(self, request, response):
        """Log cache performance metrics."""
        if hasattr(request, '_cache_hits') and hasattr(request, '_cache_misses'):
            total_cache_ops = request._cache_hits + request._cache_misses
            hit_rate = (request._cache_hits / total_cache_ops * 100) if total_cache_ops > 0 else 0
            
            if total_cache_ops > 0:
                logger.info(
                    "cache_performance",
                    path=request.path,
                    cache_hits=request._cache_hits,
                    cache_misses=request._cache_misses,
                    hit_rate_percent=round(hit_rate, 2),
                )
        
        return response