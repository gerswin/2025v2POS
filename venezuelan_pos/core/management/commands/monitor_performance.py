"""
Management command for continuous performance monitoring.
"""

import time
import threading
import structlog
from django.core.management.base import BaseCommand
from django.core.cache import cache
from django.db import connection
from django.conf import settings
from venezuelan_pos.core.monitoring import SystemHealthMonitor, BusinessMetrics
from venezuelan_pos.apps.tenants.models import Tenant, User
from venezuelan_pos.apps.sales.models import Transaction

logger = structlog.get_logger('venezuelan_pos.performance')


class Command(BaseCommand):
    help = 'Run continuous performance monitoring for the Venezuelan POS system'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--interval',
            type=int,
            default=60,
            help='Monitoring interval in seconds (default: 60)'
        )
        parser.add_argument(
            '--duration',
            type=int,
            default=0,
            help='Total monitoring duration in seconds (0 = infinite)'
        )
        parser.add_argument(
            '--metrics-only',
            action='store_true',
            help='Only collect metrics, do not perform health checks'
        )
    
    def handle(self, *args, **options):
        self.interval = options['interval']
        self.duration = options['duration']
        self.metrics_only = options['metrics_only']
        self.running = True
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Starting performance monitoring (interval: {self.interval}s, '
                f'duration: {"infinite" if self.duration == 0 else f"{self.duration}s"})'
            )
        )
        
        # Set up signal handlers for graceful shutdown
        import signal
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        start_time = time.time()
        
        try:
            while self.running:
                # Check if duration limit reached
                if self.duration > 0 and (time.time() - start_time) >= self.duration:
                    break
                
                # Collect metrics
                self.collect_system_metrics()
                
                if not self.metrics_only:
                    # Perform health checks
                    self.perform_health_checks()
                
                # Collect business metrics
                self.collect_business_metrics()
                
                # Wait for next interval
                time.sleep(self.interval)
                
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('Monitoring interrupted by user'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Monitoring error: {str(e)}'))
            logger.error('monitoring_error', error=str(e))
        finally:
            self.stdout.write(self.style.SUCCESS('Performance monitoring stopped'))
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        self.running = False
        self.stdout.write(self.style.WARNING('Received shutdown signal, stopping monitoring...'))
    
    def collect_system_metrics(self):
        """Collect system-level performance metrics."""
        try:
            # Database connection pool metrics
            db_connections = len(connection.queries)
            
            # Cache performance
            cache_info = self._get_cache_info()
            
            # Memory usage (if psutil is available)
            memory_info = self._get_memory_info()
            
            logger.info(
                'system_metrics',
                db_connections=db_connections,
                cache_info=cache_info,
                memory_info=memory_info,
                timestamp=time.time(),
            )
            
        except Exception as e:
            logger.error('system_metrics_error', error=str(e))
    
    def perform_health_checks(self):
        """Perform comprehensive health checks."""
        try:
            # Database health
            db_healthy, db_duration = SystemHealthMonitor.check_database_health()
            
            # Cache health
            cache_healthy, cache_duration = SystemHealthMonitor.check_cache_health()
            
            # Celery health
            celery_healthy, celery_duration = SystemHealthMonitor.check_celery_health()
            
            # Overall system health
            overall_healthy = db_healthy and cache_healthy
            
            logger.info(
                'health_check_results',
                database_healthy=db_healthy,
                database_duration_ms=db_duration * 1000 if db_duration else None,
                cache_healthy=cache_healthy,
                cache_duration_ms=cache_duration * 1000 if cache_duration else None,
                celery_healthy=celery_healthy,
                celery_duration_ms=celery_duration * 1000 if celery_duration else None,
                overall_healthy=overall_healthy,
                timestamp=time.time(),
            )
            
        except Exception as e:
            logger.error('health_check_error', error=str(e))
    
    def collect_business_metrics(self):
        """Collect business-specific metrics."""
        try:
            # Active tenants
            active_tenants = Tenant.objects.filter(is_active=True).count()
            
            # Active users (logged in within last 24 hours)
            from django.utils import timezone
            from datetime import timedelta
            
            recent_login_threshold = timezone.now() - timedelta(hours=24)
            active_users = User.objects.filter(
                last_login__gte=recent_login_threshold
            ).count()
            
            # Recent transactions (last hour)
            recent_transaction_threshold = timezone.now() - timedelta(hours=1)
            recent_transactions = Transaction.objects.filter(
                created_at__gte=recent_transaction_threshold
            ).count()
            
            # Update Prometheus gauges
            for tenant in Tenant.objects.filter(is_active=True):
                tenant_users = User.objects.filter(
                    tenant=tenant,
                    last_login__gte=recent_login_threshold
                ).count()
                BusinessMetrics.update_active_users(str(tenant.id), tenant_users)
            
            logger.info(
                'business_metrics',
                active_tenants=active_tenants,
                active_users=active_users,
                recent_transactions=recent_transactions,
                timestamp=time.time(),
            )
            
        except Exception as e:
            logger.error('business_metrics_error', error=str(e))
    
    def _get_cache_info(self):
        """Get cache performance information."""
        try:
            # Test cache performance
            start_time = time.time()
            cache.set('monitor_test', 'test_value', timeout=60)
            cache.get('monitor_test')
            cache.delete('monitor_test')
            cache_duration = time.time() - start_time
            
            return {
                'response_time_ms': round(cache_duration * 1000, 2),
                'status': 'healthy' if cache_duration < 0.1 else 'slow'
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def _get_memory_info(self):
        """Get memory usage information."""
        try:
            import psutil
            process = psutil.Process()
            memory_info = process.memory_info()
            
            return {
                'rss_mb': round(memory_info.rss / 1024 / 1024, 2),
                'vms_mb': round(memory_info.vms / 1024 / 1024, 2),
                'percent': round(process.memory_percent(), 2)
            }
        except ImportError:
            return {'status': 'psutil_not_available'}
        except Exception as e:
            return {'status': 'error', 'error': str(e)}