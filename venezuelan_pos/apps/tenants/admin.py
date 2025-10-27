from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import Tenant, User, TenantUser
from .middleware import AdminTenantMixin


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    """Admin interface for Tenant model."""
    
    list_display = ['name', 'slug', 'is_active', 'created_at', 'user_count']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'slug', 'contact_email']
    readonly_fields = ['id', 'created_at', 'updated_at']
    prepopulated_fields = {'slug': ('name',)}
    
    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'is_active')
        }),
        ('Contact Information', {
            'fields': ('contact_email', 'contact_phone')
        }),
        ('Fiscal Configuration', {
            'fields': ('fiscal_series_prefix',)
        }),
        ('Configuration', {
            'fields': ('configuration',),
            'classes': ('collapse',)
        }),
        ('System Information', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def user_count(self, obj):
        """Display number of users in this tenant."""
        count = obj.users.count()
        return format_html('<strong>{}</strong>', count)
    user_count.short_description = 'Users'
    
    def get_queryset(self, request):
        """Filter tenants for non-admin users."""
        qs = super().get_queryset(request)
        if not request.user.is_admin_user:
            if request.user.tenant:
                qs = qs.filter(id=request.user.tenant.id)
            else:
                qs = qs.none()
        return qs


@admin.register(User)
class UserAdmin(AdminTenantMixin, BaseUserAdmin):
    """Admin interface for User model with tenant awareness."""
    
    list_display = ['username', 'email', 'first_name', 'last_name', 'role', 'tenant', 'is_active']
    list_filter = ['role', 'is_active', 'is_staff', 'tenant']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Tenant Information', {
            'fields': ('tenant', 'role', 'phone')
        }),
        ('System Information', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Tenant Information', {
            'fields': ('tenant', 'role', 'phone')
        }),
    )
    
    def get_queryset(self, request):
        """Filter users based on tenant access."""
        qs = super().get_queryset(request)
        
        if request.user.is_admin_user:
            return qs
        elif request.user.tenant:
            # Tenant admins can see users in their tenant
            return qs.filter(tenant=request.user.tenant)
        else:
            return qs.none()
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Limit tenant choices based on user permissions."""
        if db_field.name == 'tenant':
            if not request.user.is_admin_user:
                if request.user.tenant:
                    kwargs['queryset'] = Tenant.objects.filter(id=request.user.tenant.id)
                else:
                    kwargs['queryset'] = Tenant.objects.none()
        
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(TenantUser)
class TenantUserAdmin(AdminTenantMixin, admin.ModelAdmin):
    """Admin interface for TenantUser relationships."""
    
    list_display = ['user', 'tenant', 'role', 'is_active', 'created_at']
    list_filter = ['role', 'is_active', 'tenant']
    search_fields = ['user__username', 'user__email', 'tenant__name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    fieldsets = (
        (None, {
            'fields': ('user', 'tenant', 'role', 'is_active')
        }),
        ('System Information', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """Filter tenant users based on access."""
        qs = super().get_queryset(request)
        
        if request.user.is_admin_user:
            return qs
        elif request.user.tenant:
            return qs.filter(tenant=request.user.tenant)
        else:
            return qs.none()
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Limit choices based on user permissions."""
        if db_field.name == 'tenant':
            if not request.user.is_admin_user:
                if request.user.tenant:
                    kwargs['queryset'] = Tenant.objects.filter(id=request.user.tenant.id)
                else:
                    kwargs['queryset'] = Tenant.objects.none()
        elif db_field.name == 'user':
            if not request.user.is_admin_user:
                if request.user.tenant:
                    kwargs['queryset'] = User.objects.filter(tenant=request.user.tenant)
                else:
                    kwargs['queryset'] = User.objects.none()
        
        return super().formfield_for_foreignkey(db_field, request, **kwargs)