from rest_framework import permissions
from venezuelan_pos.apps.tenants.models import User


class IsAdminUser(permissions.BasePermission):
    """
    Permission class for admin users only.
    """
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.is_admin_user
        )


class IsTenantAdmin(permissions.BasePermission):
    """
    Permission class for tenant admins and admin users.
    """
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            (request.user.is_admin_user or request.user.is_tenant_admin)
        )


class IsEventOperator(permissions.BasePermission):
    """
    Permission class for event operators and above.
    """
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role in [
                User.Role.ADMIN_USER,
                User.Role.TENANT_ADMIN,
                User.Role.EVENT_OPERATOR
            ]
        )


class IsTenantMember(permissions.BasePermission):
    """
    Permission class that checks if user belongs to the same tenant as the resource.
    """
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        # Admin users have access to all objects
        if request.user.is_admin_user:
            return True
        
        # Check if object has tenant attribute
        if hasattr(obj, 'tenant'):
            return obj.tenant == request.user.tenant
        
        # Check if object is a user and belongs to same tenant
        if isinstance(obj, User):
            return obj.tenant == request.user.tenant
        
        return False


class IsOwnerOrTenantAdmin(permissions.BasePermission):
    """
    Permission class that allows owners or tenant admins to access objects.
    """
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        # Admin users have access to all objects
        if request.user.is_admin_user:
            return True
        
        # Tenant admins have access to objects in their tenant
        if request.user.is_tenant_admin and hasattr(obj, 'tenant'):
            return obj.tenant == request.user.tenant
        
        # Users can access their own objects
        if hasattr(obj, 'user'):
            return obj.user == request.user
        
        # Check if the object is the user themselves
        if isinstance(obj, User):
            return obj == request.user
        
        return False


class ReadOnlyOrTenantAdmin(permissions.BasePermission):
    """
    Permission class that allows read-only access to all authenticated users,
    but write access only to tenant admins and above.
    """
    
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        
        # Read permissions for all authenticated users
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions only for tenant admins and above
        return request.user.is_admin_user or request.user.is_tenant_admin
    
    def has_object_permission(self, request, view, obj):
        # Read permissions for all authenticated users in same tenant
        if request.method in permissions.SAFE_METHODS:
            if request.user.is_admin_user:
                return True
            if hasattr(obj, 'tenant'):
                return obj.tenant == request.user.tenant
            return True
        
        # Write permissions only for tenant admins and above
        if request.user.is_admin_user:
            return True
        
        if request.user.is_tenant_admin and hasattr(obj, 'tenant'):
            return obj.tenant == request.user.tenant
        
        return False