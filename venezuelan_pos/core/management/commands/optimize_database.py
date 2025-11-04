"""
Management command to optimize database performance.
Creates indexes, analyzes query performance, and provides optimization recommendations.
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.conf import settings
import time


class Command(BaseCommand):
    help = 'Optimize database performance with indexes and analysis'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--analyze-only',
            action='store_true',
            help='Only analyze performance, do not create indexes',
        )
        parser.add_argument(
            '--create-indexes',
            action='store_true',
            help='Create additional performance indexes',
        )
        parser.add_argument(
            '--check-replicas',
            action='store_true',
            help='Check read replica health and lag',
        )
        parser.add_argument(
            '--vacuum',
            action='store_true',
            help='Run VACUUM ANALYZE on PostgreSQL (requires superuser)',
        )
    
    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('Starting database optimization...')
        )
        
        if options['analyze_only']:
            self.analyze_performance()
        elif options['create_indexes']:
            self.create_performance_indexes()
        elif options['check_replicas']:
            self.check_replica_health()
        elif options['vacuum']:
            self.vacuum_database()
        else:
            # Run all optimizations
            self.analyze_performance()
            self.create_performance_indexes()
            self.check_replica_health()
            self.provide_recommendations()
    
    def analyze_performance(self):
        """Analyze current database performance."""
        self.stdout.write('Analyzing database performance...')
        
        if connection.vendor == 'postgresql':
            self.analyze_postgresql_performance()
        else:
            self.stdout.write(
                self.style.WARNING('Performance analysis only available for PostgreSQL')
            )
    
    def analyze_postgresql_performance(self):
        """Analyze PostgreSQL specific performance metrics."""
        with connection.cursor() as cursor:
            # Check table sizes
            self.stdout.write('\nTable sizes:')
            cursor.execute("""
                SELECT 
                    schemaname,
                    tablename,
                    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
                    pg_total_relation_size(schemaname||'.'||tablename) as size_bytes
                FROM pg_tables 
                WHERE schemaname NOT IN ('information_schema', 'pg_catalog')
                ORDER BY size_bytes DESC
                LIMIT 10;
            """)
            
            for row in cursor.fetchall():
                self.stdout.write(f"  {row[1]}: {row[2]}")
            
            # Check index usage
            self.stdout.write('\nMost used indexes:')
            cursor.execute("""
                SELECT 
                    schemaname,
                    relname as tablename,
                    indexrelname as indexname,
                    idx_tup_read,
                    idx_tup_fetch
                FROM pg_stat_user_indexes 
                WHERE idx_tup_read > 0
                ORDER BY idx_tup_read DESC
                LIMIT 10;
            """)
            
            for row in cursor.fetchall():
                self.stdout.write(f"  {row[2]} on {row[1]}: {row[3]} reads")
            
            # Check for unused indexes
            self.stdout.write('\nPotentially unused indexes:')
            cursor.execute("""
                SELECT 
                    schemaname,
                    relname as tablename,
                    indexrelname as indexname,
                    idx_tup_read,
                    idx_tup_fetch
                FROM pg_stat_user_indexes 
                WHERE idx_tup_read = 0 AND idx_tup_fetch = 0
                ORDER BY schemaname, relname;
            """)
            
            unused_count = 0
            for row in cursor.fetchall():
                if unused_count < 5:  # Limit output
                    self.stdout.write(f"  {row[2]} on {row[1]} (never used)")
                unused_count += 1
            
            if unused_count > 5:
                self.stdout.write(f"  ... and {unused_count - 5} more unused indexes")
    
    def create_performance_indexes(self):
        """Create additional performance indexes."""
        self.stdout.write('Creating performance indexes...')
        
        # Comprehensive performance indexes for Venezuelan POS system
        performance_indexes = [
            # Tenant-aware composite indexes (most critical)
            {
                'name': 'idx_events_tenant_status_date',
                'sql': "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_events_tenant_status_date ON events(tenant_id, status, start_date);",
                'description': 'Events by tenant, status, and date'
            },
            {
                'name': 'idx_zones_tenant_event_type',
                'sql': "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_zones_tenant_event_type ON zones(tenant_id, event_id, zone_type);",
                'description': 'Zones by tenant, event, and type'
            },
            {
                'name': 'idx_transactions_tenant_status_date',
                'sql': "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_transactions_tenant_status_date ON transactions(tenant_id, status, created_at);",
                'description': 'Transactions by tenant, status, and date'
            },
            {
                'name': 'idx_customers_tenant_active',
                'sql': "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_customers_tenant_active ON customers(tenant_id, is_active);",
                'description': 'Active customers by tenant'
            },
            
            # Sales performance indexes
            {
                'name': 'idx_seats_zone_status_position',
                'sql': "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_seats_zone_status_position ON seats(zone_id, status, row_number, seat_number);",
                'description': 'Seats by zone, status, and position'
            },
            {
                'name': 'idx_transaction_items_transaction_zone',
                'sql': "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_transaction_items_transaction_zone ON transaction_items(transaction_id, zone_id);",
                'description': 'Transaction items by transaction and zone'
            },
            {
                'name': 'idx_reserved_tickets_tenant_expires',
                'sql': "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_reserved_tickets_tenant_expires ON reserved_tickets(tenant_id, reserved_until) WHERE status = 'reserved';",
                'description': 'Reserved tickets by tenant and expiration (partial)'
            },
            
            # Pricing system indexes
            {
                'name': 'idx_price_stages_event_active_order',
                'sql': "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_price_stages_event_active_order ON price_stages(event_id, is_active, stage_order);",
                'description': 'Price stages by event, active status, and order'
            },
            {
                'name': 'idx_stage_sales_stage_date',
                'sql': "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_stage_sales_stage_date ON stage_sales(stage_id, sales_date);",
                'description': 'Stage sales by stage and date'
            },
            {
                'name': 'idx_stage_transitions_event_date',
                'sql': "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_stage_transitions_event_date ON stage_transitions(event_id, transition_at);",
                'description': 'Stage transitions by event and date'
            },
            {
                'name': 'idx_row_pricing_zone_row',
                'sql': "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_row_pricing_zone_row ON row_pricing(zone_id, row_number);",
                'description': 'Row pricing by zone and row'
            },
            
            # Payment system indexes
            {
                'name': 'idx_payments_transaction_status_date',
                'sql': "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_payments_transaction_status_date ON payments(transaction_id, status, created_at);",
                'description': 'Payments by transaction, status, and date'
            },
            {
                'name': 'idx_payment_plans_transaction_type',
                'sql': "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_payment_plans_transaction_type ON payment_plans(transaction_id, plan_type);",
                'description': 'Payment plans by transaction and type'
            },
            
            # Fiscal compliance indexes
            {
                'name': 'idx_transactions_fiscal_series_unique',
                'sql': "CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS idx_transactions_fiscal_series_unique ON transactions(fiscal_series) WHERE fiscal_series IS NOT NULL;",
                'description': 'Unique fiscal series numbers (partial)'
            },
            {
                'name': 'idx_fiscal_counters_tenant_event_unique',
                'sql': "CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS idx_fiscal_counters_tenant_event_unique ON fiscal_series_counters(tenant_id, COALESCE(event_id, '00000000-0000-0000-0000-000000000000'::uuid));",
                'description': 'Unique fiscal counters per tenant/event'
            },
            
            # Notification system indexes
            {
                'name': 'idx_notification_logs_customer_status_date',
                'sql': "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_notification_logs_customer_status_date ON notification_logs(customer_id, status, created_at);",
                'description': 'Notification logs by customer, status, and date'
            },
            {
                'name': 'idx_notification_templates_tenant_type',
                'sql': "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_notification_templates_tenant_type ON notification_templates(tenant_id, template_type, is_active);",
                'description': 'Notification templates by tenant and type'
            },
            
            # Digital tickets indexes
            {
                'name': 'idx_digital_tickets_transaction_status',
                'sql': "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_digital_tickets_transaction_status ON digital_tickets(transaction_id, status);",
                'description': 'Digital tickets by transaction and status'
            },
            {
                'name': 'idx_ticket_validations_ticket_date',
                'sql': "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ticket_validations_ticket_date ON ticket_validations(ticket_id, validated_at);",
                'description': 'Ticket validations by ticket and date'
            },
            
            # Reporting indexes
            {
                'name': 'idx_sales_reports_tenant_period_date',
                'sql': "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sales_reports_tenant_period_date ON sales_reports(tenant_id, report_period, created_at);",
                'description': 'Sales reports by tenant, period, and date'
            },
            {
                'name': 'idx_occupancy_analysis_event_zone_date',
                'sql': "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_occupancy_analysis_event_zone_date ON occupancy_analysis(event_id, zone_id, analysis_date);",
                'description': 'Occupancy analysis by event, zone, and date'
            },
            
            # User and authentication indexes
            {
                'name': 'idx_users_tenant_role_active',
                'sql': "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_tenant_role_active ON users(tenant_id, role, is_active);",
                'description': 'Users by tenant, role, and active status'
            },
            {
                'name': 'idx_tenant_users_user_tenant_active',
                'sql': "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_tenant_users_user_tenant_active ON tenant_users(user_id, tenant_id, is_active);",
                'description': 'Tenant users by user, tenant, and active status'
            },
            
            # Partial indexes for better performance on filtered queries
            {
                'name': 'idx_events_active_tenant_date',
                'sql': "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_events_active_tenant_date ON events(tenant_id, start_date) WHERE status = 'active';",
                'description': 'Active events by tenant and date (partial)'
            },
            {
                'name': 'idx_seats_available_zone_position',
                'sql': "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_seats_available_zone_position ON seats(zone_id, row_number, seat_number) WHERE status = 'available';",
                'description': 'Available seats by zone and position (partial)'
            },
            {
                'name': 'idx_transactions_completed_tenant_date',
                'sql': "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_transactions_completed_tenant_date ON transactions(tenant_id, completed_at) WHERE status = 'completed';",
                'description': 'Completed transactions by tenant and date (partial)'
            },
            {
                'name': 'idx_price_stages_active_event_dates',
                'sql': "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_price_stages_active_event_dates ON price_stages(event_id, start_date, end_date) WHERE is_active = true;",
                'description': 'Active price stages by event and dates (partial)'
            },
        ]
        
        created_count = 0
        failed_count = 0
        
        with connection.cursor() as cursor:
            for index_info in performance_indexes:
                try:
                    self.stdout.write(f'Creating {index_info["name"]}...')
                    start_time = time.time()
                    cursor.execute(index_info['sql'])
                    end_time = time.time()
                    
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'  ✓ Created in {end_time - start_time:.2f}s - {index_info["description"]}'
                        )
                    )
                    created_count += 1
                    
                except Exception as e:
                    self.stdout.write(
                        self.style.WARNING(f'  ✗ Failed: {str(e)}')
                    )
                    failed_count += 1
        
        self.stdout.write(f'\nIndex creation summary: {created_count} created, {failed_count} failed')
    
    def check_replica_health(self):
        """Check read replica health and configuration."""
        self.stdout.write('Checking read replica configuration...')
        
        from venezuelan_pos.core.db_router import ReadReplicaManager
        
        # Check replica databases
        replicas = ReadReplicaManager.get_replica_databases()
        if not replicas:
            self.stdout.write(
                self.style.WARNING('No read replicas configured')
            )
            return
        
        # Check replica health
        health_status = ReadReplicaManager.check_replica_health()
        for replica, status in health_status.items():
            if 'healthy' in status:
                self.stdout.write(
                    self.style.SUCCESS(f'  {replica}: {status}')
                )
            else:
                self.stdout.write(
                    self.style.ERROR(f'  {replica}: {status}')
                )
        
        # Check replication lag
        lag_info = ReadReplicaManager.get_replica_lag()
        self.stdout.write('\nReplication lag:')
        for replica, lag in lag_info.items():
            if isinstance(lag, (int, float)):
                if lag < 1:
                    self.stdout.write(
                        self.style.SUCCESS(f'  {replica}: {lag:.2f} seconds')
                    )
                elif lag < 10:
                    self.stdout.write(
                        self.style.WARNING(f'  {replica}: {lag:.2f} seconds')
                    )
                else:
                    self.stdout.write(
                        self.style.ERROR(f'  {replica}: {lag:.2f} seconds (high lag)')
                    )
            else:
                self.stdout.write(
                    self.style.ERROR(f'  {replica}: {lag}')
                )
    
    def vacuum_database(self):
        """Run VACUUM ANALYZE on PostgreSQL."""
        if connection.vendor != 'postgresql':
            self.stdout.write(
                self.style.ERROR('VACUUM only available for PostgreSQL')
            )
            return
        
        self.stdout.write('Running VACUUM ANALYZE...')
        
        with connection.cursor() as cursor:
            try:
                cursor.execute('VACUUM ANALYZE;')
                self.stdout.write(
                    self.style.SUCCESS('VACUUM ANALYZE completed successfully')
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'VACUUM failed: {str(e)}')
                )
    
    def provide_recommendations(self):
        """Provide performance optimization recommendations."""
        self.stdout.write('\n' + '='*50)
        self.stdout.write('PERFORMANCE RECOMMENDATIONS')
        self.stdout.write('='*50)
        
        recommendations = [
            "1. Monitor query performance using django-silk in development",
            "2. Use select_related() and prefetch_related() for related objects",
            "3. Consider database connection pooling for high-traffic applications",
            "4. Set up read replicas for reporting and analytics queries",
            "5. Use database indexes for frequently filtered fields",
            "6. Cache expensive queries using Redis",
            "7. Monitor slow queries and optimize them regularly",
            "8. Use database-level constraints for data integrity",
            "9. Consider partitioning large tables by tenant or date",
            "10. Regular VACUUM and ANALYZE for PostgreSQL maintenance",
        ]
        
        for recommendation in recommendations:
            self.stdout.write(f"  {recommendation}")
        
        self.stdout.write('\nFor more detailed analysis, use:')
        self.stdout.write('  python manage.py optimize_database --analyze-only')
        self.stdout.write('  python manage.py optimize_database --check-replicas')
        
        self.stdout.write(
            self.style.SUCCESS('\nDatabase optimization completed!')
        )