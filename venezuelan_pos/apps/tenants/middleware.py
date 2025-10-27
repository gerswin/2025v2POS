import threading
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.core.exceptions import PermissionDenied
from .models import Tenant

# Thread-local storage for current tenant
_thread_locals = threading.local()


def get_current_tenant():
    """Get the current tenant from thread-local storage."""
    return getattr(_thread_locals, 'tenant', None)


def set_current_tenant(tenant):
    """Set the current tenant in thread-local storage."""
    _thread_locals.tenant = tenant


class TenantMiddleware:
    """
    Middleware for tenant-aware request processing.
    
    This middleware:
    1. Identifies the tenant from the request (header, subdomain, or user)
    2. Sets the current tenant in thread-local storage
    3. Ensures users can only access their tenant's data
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Clear any existing tenant context
        set_current_tenant(None)
        
        # Skip tenant resolution for certain paths
        if self._should_skip_tenant_resolution(request):
            return self.get_response(request)
        
        # Resolve tenant from request
        tenant = self._resolve_tenant(request)
        
        if tenant:
            # Validate user has access to this tenant
            if request.user.is_authenticated:
                if not request.user.has_tenant_access(tenant):
                    raise PermissionDenied("User does not have access to this tenant")
            
            # Set tenant context
            set_current_tenant(tenant)
            request.tenant = tenant
        
        response = self.get_response(request)
        
        # Clear tenant context after request
        set_current_tenant(None)
        
        return response
    
    def _should_skip_tenant_resolution(self, request):
        """Check if tenant resolution should be skipped for this request."""
        skip_paths = [
            '/admin/login/',
            '/api/auth/login/',
            '/api/auth/refresh/',
            '/health/',
            '/metrics/',
            '/api/schema/',
            '/api/docs/',
        ]
        
        return any(request.path.startswith(path) for path in skip_paths)
    
    def _resolve_tenant(self, request):
        """
        Resolve tenant from request using multiple strategies:
        1. X-Tenant-ID header (for API requests)
        2. Subdomain (for web requests)
        3. User's primary tenant (fallback)
        """
        
        # Strategy 1: X-Tenant-ID header
        tenant_id = request.headers.get('X-Tenant-ID')
        if tenant_id:
            try:
                return Tenant.objects.get(id=tenant_id, is_active=True)
            except (Tenant.DoesNotExist, ValueError):
                pass
        
        # Strategy 2: X-Tenant-Slug header
        tenant_slug = request.headers.get('X-Tenant-Slug')
        if tenant_slug:
            try:
                return Tenant.objects.get(slug=tenant_slug, is_active=True)
            except Tenant.DoesNotExist:
                pass
        
        # Strategy 3: Subdomain (e.g., tenant1.example.com)
        host = request.get_host()
        if '.' in host:
            subdomain = host.split('.')[0]
            if subdomain != 'www' and subdomain != 'api':
                try:
                    return Tenant.objects.get(slug=subdomain, is_active=True)
                except Tenant.DoesNotExist:
                    pass
        
        # Strategy 4: User's primary tenant (authenticated users only)
        if request.user.is_authenticated and hasattr(request.user, 'tenant'):
            if request.user.tenant and request.user.tenant.is_active:
                return request.user.tenant
        
        # No tenant found - this is okay for some endpoints
        return None


class TenantRequiredMixin:
    """
    Mixin for views that require a tenant context.
    Raises Http404 if no tenant is available.
    """
    
    def dispatch(self, request, *args, **kwargs):
        if not hasattr(request, 'tenant') or not request.tenant:
            raise Http404("Tenant not found")
        return super().dispatch(request, *args, **kwargs)


class AdminTenantMixin:
    """
    Mixin for admin views that need tenant filtering.
    """
    
    def get_queryset(self, request):
        """Filter queryset by tenant for non-admin users."""
        qs = super().get_queryset(request)
        
        if not request.user.is_admin_user:
            if hasattr(qs.model, 'tenant'):
                # Filter by user's tenant
                if request.user.tenant:
                    qs = qs.filter(tenant=request.user.tenant)
                else:
                    # No tenant access
                    qs = qs.none()
        
        return qs
    
    def save_model(self, request, obj, form, change):
        """Automatically set tenant for new objects."""
        if not change and hasattr(obj, 'tenant') and not obj.tenant_id:
            if request.user.tenant:
                obj.tenant = request.user.tenant
        
        super().save_model(request, obj, form, change)