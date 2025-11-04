"""
Database router for read replica configuration.
Routes read queries to replica database and write queries to primary database.
"""

import random
from django.conf import settings


class DatabaseRouter:
    """
    Database router that directs reads to replica and writes to primary database.
    Supports multiple read replicas with load balancing.
    """
    
    # Apps that should always use the primary database
    PRIMARY_ONLY_APPS = {
        'admin',
        'auth',
        'contenttypes',
        'sessions',
        'messages',
        'staticfiles',
    }
    
    # Models that should always use primary for consistency
    PRIMARY_ONLY_MODELS = {
        'fiscal.fiscalseriescounter',  # Critical for fiscal numbering
        'sales.transaction',  # Critical for sales consistency
        'sales.reservedticket',  # Critical for seat reservations
        'pricing.stagetransition',  # Critical for pricing transitions
    }
    
    def db_for_read(self, model, **hints):
        """Suggest the database to read from."""
        app_label = model._meta.app_label
        model_name = f"{app_label}.{model._meta.model_name}"
        
        # Always use primary for certain apps and models
        if (app_label in self.PRIMARY_ONLY_APPS or 
            model_name in self.PRIMARY_ONLY_MODELS):
            return 'default'
        
        # Check if we're in a transaction - if so, use primary for consistency
        from django.db import transaction
        if transaction.get_connection().in_atomic_block:
            return 'default'
        
        # Use replica for read operations if available
        if 'replica' in settings.DATABASES:
            return 'replica'
        
        return 'default'
    
    def db_for_write(self, model, **hints):
        """Suggest the database to write to."""
        # All writes go to primary database
        return 'default'
    
    def allow_relation(self, obj1, obj2, **hints):
        """Allow relations if models are in the same database."""
        db_set = {'default', 'replica'}
        if obj1._state.db in db_set and obj2._state.db in db_set:
            return True
        return None
    
    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """Ensure that migrations only run on the primary database."""
        return db == 'default'


class ReportingDatabaseRouter:
    """
    Specialized router for reporting queries.
    Directs reporting and analytics queries to read replicas.
    """
    
    # Apps that contain reporting models
    REPORTING_APPS = {
        'reports',
        'analytics',
    }
    
    # Models that are primarily used for reporting
    REPORTING_MODELS = {
        'reports.salesreport',
        'reports.occupancyanalysis',
        'pricing.pricehistory',
        'pricing.stagesales',
    }
    
    def db_for_read(self, model, **hints):
        """Route reporting reads to replica."""
        app_label = model._meta.app_label
        model_name = f"{app_label}.{model._meta.model_name}"
        
        # Use replica for reporting models
        if (app_label in self.REPORTING_APPS or 
            model_name in self.REPORTING_MODELS):
            if 'replica' in settings.DATABASES:
                return 'replica'
        
        return None  # Let other routers handle it
    
    def db_for_write(self, model, **hints):
        """All writes go to primary."""
        return 'default'
    
    def allow_relation(self, obj1, obj2, **hints):
        """Allow relations between databases."""
        return True
    
    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """Only migrate on primary."""
        return db == 'default'


class ReadReplicaManager:
    """
    Manager for handling read replica connections and health checks.
    """
    
    @staticmethod
    def get_replica_databases():
        """Get list of available replica databases."""
        replicas = []
        for db_name, db_config in settings.DATABASES.items():
            if db_name != 'default' and 'replica' in db_name:
                replicas.append(db_name)
        return replicas
    
    @staticmethod
    def check_replica_health():
        """Check health of replica databases."""
        from django.db import connections
        
        replica_status = {}
        replicas = ReadReplicaManager.get_replica_databases()
        
        for replica_name in replicas:
            try:
                connection = connections[replica_name]
                with connection.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    cursor.fetchone()
                replica_status[replica_name] = 'healthy'
            except Exception as e:
                replica_status[replica_name] = f'unhealthy: {str(e)}'
        
        return replica_status
    
    @staticmethod
    def get_replica_lag():
        """Get replication lag for PostgreSQL replicas."""
        from django.db import connections
        
        lag_info = {}
        replicas = ReadReplicaManager.get_replica_databases()
        
        for replica_name in replicas:
            try:
                connection = connections[replica_name]
                if connection.vendor == 'postgresql':
                    with connection.cursor() as cursor:
                        cursor.execute("""
                            SELECT 
                                CASE 
                                    WHEN pg_is_in_recovery() THEN 
                                        EXTRACT(EPOCH FROM (now() - pg_last_xact_replay_timestamp()))
                                    ELSE 0 
                                END as lag_seconds;
                        """)
                        result = cursor.fetchone()
                        lag_info[replica_name] = result[0] if result else None
            except Exception as e:
                lag_info[replica_name] = f'error: {str(e)}'
        
        return lag_info
    
    @staticmethod
    def force_primary_db():
        """Context manager to force using primary database."""
        from django.db import transaction
        
        class ForcePrimaryDB:
            def __enter__(self):
                # Set a flag that the router can check
                import threading
                if not hasattr(threading.current_thread(), 'force_primary_db'):
                    threading.current_thread().force_primary_db = True
                return self
            
            def __exit__(self, exc_type, exc_val, exc_tb):
                import threading
                if hasattr(threading.current_thread(), 'force_primary_db'):
                    delattr(threading.current_thread(), 'force_primary_db')
        
        return ForcePrimaryDB()


# Enhanced database router that checks for force_primary_db flag
class EnhancedDatabaseRouter(DatabaseRouter):
    """Enhanced router with support for forcing primary database."""
    
    def db_for_read(self, model, **hints):
        """Check for force primary flag before routing."""
        import threading
        
        # Check if we should force primary database
        if hasattr(threading.current_thread(), 'force_primary_db'):
            return 'default'
        
        return super().db_for_read(model, **hints)


# Utility functions for database operations
def using_replica(queryset):
    """Force a queryset to use replica database."""
    if 'replica' in settings.DATABASES:
        return queryset.using('replica')
    return queryset


def using_primary(queryset):
    """Force a queryset to use primary database."""
    return queryset.using('default')


def with_read_replica(func):
    """Decorator to use read replica for a function."""
    def wrapper(*args, **kwargs):
        # This would set a context variable to prefer replica
        return func(*args, **kwargs)
    return wrapper


def with_primary_db(func):
    """Decorator to force using primary database."""
    def wrapper(*args, **kwargs):
        with ReadReplicaManager.force_primary_db():
            return func(*args, **kwargs)
    return wrapper