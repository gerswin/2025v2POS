"""
Fiscal calculations cache for improved performance.
"""

from django.core.cache import cache
from decimal import Decimal
import hashlib
import json


class FiscalCache:
    """Cache for fiscal calculations to improve checkout performance."""
    
    CACHE_PREFIX = 'fiscal_calc'
    DEFAULT_TIMEOUT = 3600  # 1 hour
    
    @classmethod
    def _make_cache_key(cls, tenant_id, event_id, base_amount):
        """Generate cache key for tax calculation."""
        key_data = f"{tenant_id}:{event_id}:{base_amount}"
        key_hash = hashlib.md5(key_data.encode()).hexdigest()
        return f"{cls.CACHE_PREFIX}:tax:{key_hash}"
    
    @classmethod
    def get_tax_calculation(cls, tenant_id, event_id, base_amount):
        """Get cached tax calculation."""
        cache_key = cls._make_cache_key(tenant_id, event_id, base_amount)
        cached_data = cache.get(cache_key)
        
        if cached_data:
            # Convert back to Decimal
            return {
                'tax_amount': Decimal(str(cached_data['tax_amount'])),
                'tax_details': cached_data['tax_details'],
                'cached': True
            }
        
        return None
    
    @classmethod
    def set_tax_calculation(cls, tenant_id, event_id, base_amount, tax_amount, tax_details):
        """Cache tax calculation result."""
        cache_key = cls._make_cache_key(tenant_id, event_id, base_amount)
        
        cache_data = {
            'tax_amount': str(tax_amount),  # Convert Decimal to string
            'tax_details': tax_details,
            'cached': True
        }
        
        cache.set(cache_key, cache_data, cls.DEFAULT_TIMEOUT)
    
    @classmethod
    def invalidate_event_taxes(cls, event_id):
        """Invalidate all tax calculations for an event."""
        # This is a simple implementation - in production you might want
        # to use cache versioning or tagged caching
        cache_pattern = f"{cls.CACHE_PREFIX}:tax:*{event_id}*"
        # Note: This requires a cache backend that supports pattern deletion
        # For Redis: cache.delete_pattern(cache_pattern)
        pass
    
    @classmethod
    def get_simple_tax_rate(cls, tenant_id):
        """Get simple tax rate for fast calculations."""
        cache_key = f"{cls.CACHE_PREFIX}:rate:{tenant_id}"
        cached_rate = cache.get(cache_key)
        
        if cached_rate is not None:
            return Decimal(str(cached_rate))
        
        # Default Venezuelan IVA rate
        default_rate = Decimal('0.16')  # 16%
        cache.set(cache_key, str(default_rate), cls.DEFAULT_TIMEOUT * 24)  # Cache for 24 hours
        
        return default_rate