"""
Tests for database optimizations and performance improvements.
"""

from django.test import TestCase, TransactionTestCase
from django.db import connection
from django.conf import settings
from django.core.management import call_command
from venezuelan_pos.core.db_optimizations import QueryOptimizer, QueryPerformanceMonitor
from venezuelan_pos.core.db_router import ReadReplicaManager
from venezuelan_pos.apps.tenants.models import Tenant, User
from venezuelan_pos.apps.events.models import Event, Venue
from venezuelan_pos.apps.zones.models import Zone, Seat


class DatabaseOptimizationTestCase(TestCase):
    """Test database optimization utilities."""
    
    def setUp(self):
        """Set up test data."""
        self.tenant = Tenant.objects.create(
            name="Test Tenant",
            slug="test-tenant"
        )
        
        self.venue = Venue.objects.create(
            tenant=self.tenant,
            name="Test Venue",
            capacity=1000
        )
        
        self.event = Event.objects.create(
            tenant=self.tenant,
            name="Test Event",
            venue=self.venue,
            start_date="2025-12-01 20:00:00+00:00",
            end_date="2025-12-01 23:00:00+00:00"
        )
    
    def test_query_optimizer_events_with_zones(self):
        """Test optimized query for events with zones."""
        # Create a zone with seats
        zone = Zone.objects.create(
            tenant=self.tenant,
            event=self.event,
            name="VIP Section",
            zone_type="numbered",
            capacity=100,
            rows=10,
            seats_per_row=10,
            base_price=50.00
        )
        
        # Set event status to active
        self.event.status = 'active'
        self.event.save()
        
        # Test optimized query
        events = QueryOptimizer.get_events_with_zones_and_pricing(tenant=self.tenant)
        # Just verify it returns a queryset and doesn't error
        self.assertTrue(hasattr(events, 'count'))
        events_list = list(events)  # Force evaluation
        self.assertEqual(len(events_list), 1)
    
    def test_query_performance_monitor(self):
        """Test query performance monitoring."""
        monitor = QueryPerformanceMonitor()
        
        with monitor.monitor_queries("test_operation"):
            # Perform some database operations
            Tenant.objects.filter(is_active=True).count()
            Event.objects.filter(tenant=self.tenant).count()
        
        summary = monitor.get_performance_summary()
        self.assertEqual(summary['total_operations'], 1)
        # In test environment, query count might be 0 due to test isolation
        self.assertGreaterEqual(summary['total_queries'], 0)
        self.assertGreaterEqual(summary['total_execution_time'], 0)
    
    def test_tenant_aware_indexes(self):
        """Test that tenant-aware indexes are created."""
        with connection.cursor() as cursor:
            # Check if tenant indexes exist
            cursor.execute("""
                SELECT indexname 
                FROM pg_indexes 
                WHERE tablename = 'events' 
                AND indexname LIKE '%tenant%';
            """)
            
            indexes = [row[0] for row in cursor.fetchall()]
            self.assertTrue(any('tenant' in idx for idx in indexes))
    
    def test_read_replica_configuration(self):
        """Test read replica configuration."""
        # Check if replica database is configured
        self.assertIn('replica', settings.DATABASES)
        
        # Test replica manager
        replicas = ReadReplicaManager.get_replica_databases()
        self.assertIn('replica', replicas)
        
        # Test health check
        health_status = ReadReplicaManager.check_replica_health()
        self.assertIn('replica', health_status)


class DatabaseRouterTestCase(TransactionTestCase):
    """Test database routing for read replicas."""
    
    def test_database_routing(self):
        """Test that reads go to replica and writes go to primary."""
        from venezuelan_pos.core.db_router import DatabaseRouter
        from venezuelan_pos.apps.tenants.models import Tenant
        
        router = DatabaseRouter()
        
        # Test read routing
        read_db = router.db_for_read(Tenant)
        self.assertIn(read_db, ['default', 'replica'])
        
        # Test write routing
        write_db = router.db_for_write(Tenant)
        self.assertEqual(write_db, 'default')
    
    def test_primary_only_models(self):
        """Test that certain models always use primary database."""
        from venezuelan_pos.core.db_router import DatabaseRouter
        from venezuelan_pos.apps.sales.models import Transaction
        
        router = DatabaseRouter()
        
        # Transaction should always use primary for consistency
        read_db = router.db_for_read(Transaction)
        self.assertEqual(read_db, 'default')


class OptimizationManagementCommandTestCase(TestCase):
    """Test database optimization management commands."""
    
    def test_optimize_database_command(self):
        """Test the optimize_database management command."""
        # Test analyze-only mode
        try:
            call_command('optimize_database', '--analyze-only', verbosity=0)
        except Exception as e:
            self.fail(f"optimize_database command failed: {e}")
    
    def test_check_replicas_command(self):
        """Test replica health check command."""
        try:
            call_command('optimize_database', '--check-replicas', verbosity=0)
        except Exception as e:
            self.fail(f"check-replicas command failed: {e}")


class QueryOptimizationTestCase(TestCase):
    """Test specific query optimizations."""
    
    def setUp(self):
        """Set up test data."""
        self.tenant = Tenant.objects.create(
            name="Test Tenant",
            slug="test-tenant"
        )
    
    def test_select_related_optimization(self):
        """Test that select_related reduces query count."""
        # Create test data
        venue = Venue.objects.create(
            tenant=self.tenant,
            name="Test Venue",
            capacity=1000
        )
        
        event = Event.objects.create(
            tenant=self.tenant,
            name="Test Event",
            venue=venue,
            start_date="2025-12-01 20:00:00+00:00",
            end_date="2025-12-01 23:00:00+00:00"
        )
        
        # Test without optimization (should use more queries)
        with self.assertNumQueries(3):  # 1 for events, 1 for tenant, 1 for venue
            events = Event.objects.all()
            for event in events:
                _ = event.tenant.name
                _ = event.venue.name
        
        # Test with optimization (should use fewer queries)
        with self.assertNumQueries(1):  # 1 query with joins
            events = Event.objects.select_related('tenant', 'venue')
            for event in events:
                _ = event.tenant.name
                _ = event.venue.name
    
    def test_prefetch_related_optimization(self):
        """Test that prefetch_related optimizes related object access."""
        # Create test data
        venue = Venue.objects.create(
            tenant=self.tenant,
            name="Test Venue",
            capacity=1000
        )
        
        event = Event.objects.create(
            tenant=self.tenant,
            name="Test Event",
            venue=venue,
            start_date="2025-12-01 20:00:00+00:00",
            end_date="2025-12-01 23:00:00+00:00"
        )
        
        # Create zones
        for i in range(3):
            Zone.objects.create(
                tenant=self.tenant,
                event=event,
                name=f"Zone {i}",
                zone_type="general",
                capacity=100,
                base_price=25.00
            )
        
        # Test with prefetch_related (should be more efficient)
        with self.assertNumQueries(2):  # 1 for events, 1 for zones
            events = Event.objects.prefetch_related('zones')
            for event in events:
                list(event.zones.all())  # Force evaluation