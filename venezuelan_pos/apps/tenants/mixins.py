"""
Tenant-aware mixins for views and viewsets.
"""

from django.http import Http404
from rest_framework import permissions


class TenantViewMixin:
    """
    Mixin for API views that require tenant context.
    Automatically filters querysets by tenant and ensures tenant access.
    """
    
    def dispatch(self, request, *args, **kwargs):
        """Ensure tenant is available before processing request."""
        if not hasattr(request, 'tenant') or not request.tenant:
            raise Http404("Tenant not found")
        return super().dispatch(request, *args, **kwargs)
    
    def get_queryset(self):
        """
        Filter queryset by current tenant.
        Subclasses should override this method and call super().get_queryset()
        to get the base tenant-filtered queryset.
        """
        if hasattr(self, 'queryset') and self.queryset is not None:
            queryset = self.queryset
        elif hasattr(self, 'model') and self.model is not None:
            queryset = self.model.objects.all()
        else:
            raise AttributeError(
                "TenantViewMixin requires either a 'queryset' attribute "
                "or a 'model' attribute to be defined."
            )
        
        # Filter by tenant if the model has a tenant field
        if hasattr(queryset.model, 'tenant'):
            return queryset.filter(tenant=self.request.tenant)
        
        return queryset
    
    def perform_create(self, serializer):
        """Automatically set tenant when creating new objects."""
        if hasattr(serializer.Meta.model, 'tenant'):
            serializer.save(tenant=self.request.tenant)
        else:
            serializer.save()


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
        
        if not request.user.is_superuser:
            if hasattr(qs.model, 'tenant'):
                # Filter by user's tenant
                if hasattr(request.user, 'tenant') and request.user.tenant:
                    qs = qs.filter(tenant=request.user.tenant)
                else:
                    # No tenant access
                    qs = qs.none()
        
        return qs
    
    def save_model(self, request, obj, form, change):
        """Automatically set tenant for new objects."""
        if not change and hasattr(obj, 'tenant') and not obj.tenant_id:
            if hasattr(request.user, 'tenant') and request.user.tenant:
                obj.tenant = request.user.tenant
        
        super().save_model(request, obj, form, change)