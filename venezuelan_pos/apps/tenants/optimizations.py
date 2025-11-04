"""
Optimized managers and querysets for tenant models.
"""

from django.db import models
from django.db.models import Prefetch, Q, F
from django.core.cache import cache


class OptimizedTenantManager(models.Manager):
    """Optimized manager for Tenant model."""
    
    def get_active_with_stats(self):
        """Get active tenants with user and event counts."""
        return self.filter(is_active=True).annotate(
            user_count=models.Count('users', distinct=True),
            event_count=models.Count('event_set', distinct=True),
            active_event_count=models.Count(
                'event_set',
                filter=Q(event_set__status='active'),
                distinct=True
            )
        ).select_related().order_by('name')
    
    def get_with_recent_activity(self, days=30):
        """Get tenants with recent activity."""
        from django.utils import timezone
        from datetime import timedelta
        
        cutoff_date = timezone.now() - timedelta(days=days)
        
        return self.filter(
            is_active=True,
            event_set__created_at__gte=cutoff_date
        ).distinct().annotate(
            recent_events=models.Count(
                'event_set',
                filter=Q(event_set__created_at__gte=cutoff_date),
                distinct=True
            ),
            recent_transactions=models.Count(
                'transaction_set',
                filter=Q(transaction_set__created_at__gte=cutoff_date),
                distinct=True
            )
        ).order_by('-recent_transactions')


class OptimizedTenantAwareManager(models.Manager):
    """Optimized base manager for tenant-aware models."""
    
    def get_queryset(self):
        """Override to add tenant filtering and optimization."""
        from .middleware import get_current_tenant
        
        queryset = super().get_queryset().select_related('tenant')
        current_tenant = get_current_tenant()
        
        if current_tenant:
            return queryset.filter(tenant=current_tenant)
        return queryset
    
    def with_tenant_data(self):
        """Get objects with tenant data preloaded."""
        return self.get_queryset().select_related('tenant')
    
    def for_tenant(self, tenant):
        """Get objects for a specific tenant."""
        return self.get_queryset().filter(tenant=tenant)
    
    def active_only(self):
        """Get only active objects (if model has is_active field)."""
        if hasattr(self.model, 'is_active'):
            return self.get_queryset().filter(is_active=True)
        return self.get_queryset()


class OptimizedUserManager(models.Manager):
    """Optimized manager for User model."""
    
    def get_with_tenant_info(self):
        """Get users with tenant information."""
        return self.select_related('tenant').prefetch_related(
            'tenant_memberships__tenant'
        )
    
    def get_active_by_tenant(self, tenant):
        """Get active users for a specific tenant."""
        return self.filter(
            tenant=tenant,
            is_active=True
        ).select_related('tenant').order_by('username')
    
    def get_operators_for_event(self, event):
        """Get event operators who can access a specific event."""
        return self.filter(
            Q(tenant=event.tenant) & 
            Q(role__in=['tenant_admin', 'event_operator']) &
            Q(is_active=True)
        ).select_related('tenant').order_by('username')
    
    def get_with_permissions(self):
        """Get users with permission information."""
        return self.select_related('tenant').prefetch_related(
            'groups',
            'user_permissions',
            'tenant_memberships__tenant'
        )
    
    def search_by_name_or_email(self, query, tenant=None):
        """Search users by name or email."""
        queryset = self.filter(
            Q(username__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(email__icontains=query)
        ).select_related('tenant')
        
        if tenant:
            queryset = queryset.filter(tenant=tenant)
        
        return queryset.order_by('username')


class CachedTenantManager(models.Manager):
    """Manager with caching for tenant data."""
    
    def get_cached_active_tenants(self, timeout=300):
        """Get active tenants with caching."""
        cache_key = 'active_tenants_list'
        tenants = cache.get(cache_key)
        
        if tenants is None:
            tenants = list(
                self.filter(is_active=True)
                .values('id', 'name', 'slug')
                .order_by('name')
            )
            cache.set(cache_key, tenants, timeout)
        
        return tenants
    
    def get_tenant_config(self, tenant_id, timeout=600):
        """Get tenant configuration with caching."""
        cache_key = f'tenant_config_{tenant_id}'
        config = cache.get(cache_key)
        
        if config is None:
            try:
                tenant = self.get(id=tenant_id)
                config = {
                    'id': str(tenant.id),
                    'name': tenant.name,
                    'slug': tenant.slug,
                    'configuration': tenant.configuration,
                    'fiscal_series_prefix': tenant.fiscal_series_prefix,
                }
                cache.set(cache_key, config, timeout)
            except self.model.DoesNotExist:
                config = None
        
        return config
    
    def invalidate_tenant_cache(self, tenant_id):
        """Invalidate cached data for a tenant."""
        cache_keys = [
            'active_tenants_list',
            f'tenant_config_{tenant_id}',
            f'tenant_{tenant_id}_events',
            f'tenant_{tenant_id}_users',
        ]
        
        cache.delete_many(cache_keys)


class TenantQueryOptimizer:
    """Utility class for optimizing tenant-related queries."""
    
    @staticmethod
    def get_tenant_dashboard_data(tenant):
        """Get optimized data for tenant dashboard."""
        from venezuelan_pos.apps.events.models import Event
        from venezuelan_pos.apps.sales.models import Transaction
        from django.utils import timezone
        from datetime import timedelta
        
        # Cache key for dashboard data
        cache_key = f'tenant_dashboard_{tenant.id}'
        data = cache.get(cache_key)
        
        if data is None:
            # Get recent activity (last 30 days)
            thirty_days_ago = timezone.now() - timedelta(days=30)
            
            # Optimized queries with select_related and annotations
            active_events = Event.objects.filter(
                tenant=tenant,
                status='active'
            ).select_related('venue').count()
            
            recent_transactions = Transaction.objects.filter(
                tenant=tenant,
                created_at__gte=thirty_days_ago,
                status='completed'
            ).aggregate(
                count=models.Count('id'),
                total_revenue=models.Sum('total_amount')
            )
            
            total_users = tenant.users.filter(is_active=True).count()
            
            data = {
                'active_events': active_events,
                'recent_transactions': recent_transactions['count'] or 0,
                'recent_revenue': float(recent_transactions['total_revenue'] or 0),
                'total_users': total_users,
                'last_updated': timezone.now().isoformat(),
            }
            
            # Cache for 5 minutes
            cache.set(cache_key, data, 300)
        
        return data
    
    @staticmethod
    def get_tenant_events_optimized(tenant, status=None):
        """Get tenant events with optimized queries."""
        from venezuelan_pos.apps.events.models import Event
        
        queryset = Event.objects.filter(tenant=tenant).select_related(
            'venue'
        ).prefetch_related(
            Prefetch(
                'zones',
                queryset=models.QuerySet().select_related('tenant')
            ),
            'transactions'
        ).annotate(
            zone_count=models.Count('zones', distinct=True),
            transaction_count=models.Count('transactions', distinct=True),
            total_revenue=models.Sum('transactions__total_amount')
        )
        
        if status:
            queryset = queryset.filter(status=status)
        
        return queryset.order_by('-start_date')
    
    @staticmethod
    def get_tenant_sales_summary(tenant, start_date=None, end_date=None):
        """Get optimized sales summary for tenant."""
        from venezuelan_pos.apps.sales.models import Transaction
        
        cache_key = f'tenant_sales_{tenant.id}_{start_date}_{end_date}'
        summary = cache.get(cache_key)
        
        if summary is None:
            queryset = Transaction.objects.filter(
                tenant=tenant,
                status='completed'
            )
            
            if start_date:
                queryset = queryset.filter(completed_at__gte=start_date)
            if end_date:
                queryset = queryset.filter(completed_at__lte=end_date)
            
            summary = queryset.aggregate(
                total_transactions=models.Count('id'),
                total_revenue=models.Sum('total_amount'),
                average_transaction=models.Avg('total_amount'),
                total_tickets=models.Count('items__id')
            )
            
            # Cache for 1 hour
            cache.set(cache_key, summary, 3600)
        
        return summary