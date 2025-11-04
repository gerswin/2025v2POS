"""
Management command to run performance benchmarks.
"""

import time
import statistics
from django.core.management.base import BaseCommand
from django.db import transaction
from django.core.cache import cache
from django.test import RequestFactory
from venezuelan_pos.core.monitoring import SystemHealthMonitor, performance_monitor
from venezuelan_pos.apps.tenants.models import Tenant, User
from venezuelan_pos.apps.events.models import Event
from venezuelan_pos.apps.zones.models import Zone
from venezuelan_pos.apps.sales.models import Transaction


class Command(BaseCommand):
    help = 'Run performance benchmarks for the Venezuelan POS system'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--iterations',
            type=int,
            default=100,
            help='Number of iterations for each benchmark'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Enable verbose output'
        )
    
    def handle(self, *args, **options):
        self.iterations = options['iterations']
        self.verbose = options['verbose']
        
        self.stdout.write(
            self.style.SUCCESS(f'Starting performance benchmarks with {self.iterations} iterations...')
        )
        
        # Run benchmarks
        results = {}
        results['database'] = self.benchmark_database_operations()
        results['cache'] = self.benchmark_cache_operations()
        results['api'] = self.benchmark_api_endpoints()
        results['health'] = self.benchmark_health_checks()
        
        # Display results
        self.display_results(results)
    
    def benchmark_database_operations(self):
        """Benchmark database operations."""
        self.stdout.write('Benchmarking database operations...')
        
        results = {}
        
        # Test simple queries
        times = []
        for _ in range(self.iterations):
            start_time = time.time()
            list(Tenant.objects.all()[:10])
            times.append(time.time() - start_time)
        
        results['simple_query'] = {
            'avg_ms': statistics.mean(times) * 1000,
            'p95_ms': statistics.quantiles(times, n=20)[18] * 1000,
            'p99_ms': statistics.quantiles(times, n=100)[98] * 1000,
        }
        
        # Test complex queries with joins
        times = []
        for _ in range(self.iterations):
            start_time = time.time()
            list(Event.objects.select_related('tenant').prefetch_related('zones')[:10])
            times.append(time.time() - start_time)
        
        results['complex_query'] = {
            'avg_ms': statistics.mean(times) * 1000,
            'p95_ms': statistics.quantiles(times, n=20)[18] * 1000,
            'p99_ms': statistics.quantiles(times, n=100)[98] * 1000,
        }
        
        # Test write operations
        times = []
        tenant = Tenant.objects.first()
        if tenant:
            # Create a venue for testing
            from venezuelan_pos.apps.events.models import Venue
            venue, created = Venue.objects.get_or_create(
                tenant=tenant,
                name='Benchmark Venue',
                defaults={
                    'address': 'Test Address',
                    'capacity': 1000,
                }
            )
            
            for i in range(min(self.iterations, 10)):  # Limit writes to 10
                start_time = time.time()
                with transaction.atomic():
                    event = Event.objects.create(
                        tenant=tenant,
                        venue=venue,
                        name=f'Benchmark Event {i}',
                        event_type='general_admission',
                        start_date='2025-12-01 20:00:00+00:00',
                        end_date='2025-12-01 23:00:00+00:00',
                        status='draft'
                    )
                    event.delete()  # Clean up immediately
                times.append(time.time() - start_time)
            
            # Clean up venue if we created it
            if created:
                venue.delete()
            
            results['write_operation'] = {
                'avg_ms': statistics.mean(times) * 1000,
                'p95_ms': statistics.quantiles(times, n=20)[18] * 1000 if len(times) >= 20 else max(times) * 1000,
                'p99_ms': statistics.quantiles(times, n=100)[98] * 1000 if len(times) >= 100 else max(times) * 1000,
            }
        
        return results
    
    def benchmark_cache_operations(self):
        """Benchmark cache operations."""
        self.stdout.write('Benchmarking cache operations...')
        
        results = {}
        
        # Test cache writes
        times = []
        for i in range(self.iterations):
            start_time = time.time()
            cache.set(f'benchmark_key_{i}', f'benchmark_value_{i}', timeout=300)
            times.append(time.time() - start_time)
        
        results['cache_write'] = {
            'avg_ms': statistics.mean(times) * 1000,
            'p95_ms': statistics.quantiles(times, n=20)[18] * 1000,
            'p99_ms': statistics.quantiles(times, n=100)[98] * 1000,
        }
        
        # Test cache reads (hits)
        times = []
        for i in range(self.iterations):
            start_time = time.time()
            cache.get(f'benchmark_key_{i % 50}')  # Some hits, some misses
            times.append(time.time() - start_time)
        
        results['cache_read'] = {
            'avg_ms': statistics.mean(times) * 1000,
            'p95_ms': statistics.quantiles(times, n=20)[18] * 1000,
            'p99_ms': statistics.quantiles(times, n=100)[98] * 1000,
        }
        
        # Clean up cache keys
        for i in range(self.iterations):
            cache.delete(f'benchmark_key_{i}')
        
        return results
    
    def benchmark_api_endpoints(self):
        """Benchmark API endpoint response times."""
        self.stdout.write('Benchmarking API endpoints...')
        
        results = {}
        factory = RequestFactory()
        
        # Test health check endpoint
        times = []
        for _ in range(self.iterations):
            start_time = time.time()
            request = factory.get('/health/')
            # Simulate health check logic
            SystemHealthMonitor.check_database_health()
            times.append(time.time() - start_time)
        
        results['health_check'] = {
            'avg_ms': statistics.mean(times) * 1000,
            'p95_ms': statistics.quantiles(times, n=20)[18] * 1000,
            'p99_ms': statistics.quantiles(times, n=100)[98] * 1000,
        }
        
        return results
    
    def benchmark_health_checks(self):
        """Benchmark system health checks."""
        self.stdout.write('Benchmarking health checks...')
        
        results = {}
        
        # Database health check
        times = []
        for _ in range(self.iterations):
            start_time = time.time()
            SystemHealthMonitor.check_database_health()
            times.append(time.time() - start_time)
        
        results['database_health'] = {
            'avg_ms': statistics.mean(times) * 1000,
            'p95_ms': statistics.quantiles(times, n=20)[18] * 1000,
            'p99_ms': statistics.quantiles(times, n=100)[98] * 1000,
        }
        
        # Cache health check
        times = []
        for _ in range(self.iterations):
            start_time = time.time()
            SystemHealthMonitor.check_cache_health()
            times.append(time.time() - start_time)
        
        results['cache_health'] = {
            'avg_ms': statistics.mean(times) * 1000,
            'p95_ms': statistics.quantiles(times, n=20)[18] * 1000,
            'p99_ms': statistics.quantiles(times, n=100)[98] * 1000,
        }
        
        return results
    
    def display_results(self, results):
        """Display benchmark results."""
        self.stdout.write(self.style.SUCCESS('\n=== PERFORMANCE BENCHMARK RESULTS ===\n'))
        
        for category, tests in results.items():
            self.stdout.write(self.style.WARNING(f'{category.upper()} BENCHMARKS:'))
            
            for test_name, metrics in tests.items():
                self.stdout.write(f'  {test_name}:')
                self.stdout.write(f'    Average: {metrics["avg_ms"]:.2f}ms')
                self.stdout.write(f'    P95: {metrics["p95_ms"]:.2f}ms')
                self.stdout.write(f'    P99: {metrics["p99_ms"]:.2f}ms')
                
                # Performance warnings
                if metrics['avg_ms'] > 100:
                    self.stdout.write(
                        self.style.ERROR(f'    ⚠️  WARNING: Average response time exceeds 100ms')
                    )
                elif metrics['avg_ms'] > 50:
                    self.stdout.write(
                        self.style.WARNING(f'    ⚠️  CAUTION: Average response time exceeds 50ms')
                    )
                else:
                    self.stdout.write(
                        self.style.SUCCESS(f'    ✅ Good performance')
                    )
            
            self.stdout.write('')
        
        # Overall assessment
        self.stdout.write(self.style.SUCCESS('=== PERFORMANCE ASSESSMENT ==='))
        
        # Check if any critical thresholds are exceeded
        critical_issues = []
        warnings = []
        
        for category, tests in results.items():
            for test_name, metrics in tests.items():
                if metrics['avg_ms'] > 200:
                    critical_issues.append(f'{category}.{test_name}: {metrics["avg_ms"]:.2f}ms')
                elif metrics['avg_ms'] > 100:
                    warnings.append(f'{category}.{test_name}: {metrics["avg_ms"]:.2f}ms')
        
        if critical_issues:
            self.stdout.write(self.style.ERROR('CRITICAL PERFORMANCE ISSUES:'))
            for issue in critical_issues:
                self.stdout.write(f'  ❌ {issue}')
        
        if warnings:
            self.stdout.write(self.style.WARNING('PERFORMANCE WARNINGS:'))
            for warning in warnings:
                self.stdout.write(f'  ⚠️  {warning}')
        
        if not critical_issues and not warnings:
            self.stdout.write(self.style.SUCCESS('✅ All performance metrics within acceptable ranges'))
        
        self.stdout.write(f'\nBenchmark completed with {self.iterations} iterations per test.')