import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError


class TenantManager(models.Manager):
    """Custom manager for Tenant model."""
    
    def get_active(self):
        """Get all active tenants."""
        return self.filter(is_active=True)


class Tenant(models.Model):
    """
    Tenant model for multi-tenant architecture.
    Provides complete data isolation between organizations.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True, help_text="Tenant organization name")
    slug = models.SlugField(max_length=100, unique=True, help_text="URL-friendly tenant identifier")
    
    # Configuration fields
    configuration = models.JSONField(
        default=dict,
        blank=True,
        help_text="Tenant-specific configuration settings"
    )
    
    # Fiscal configuration
    fiscal_series_prefix = models.CharField(
        max_length=10,
        blank=True,
        help_text="Prefix for fiscal series numbering"
    )
    
    # Contact information
    contact_email = models.EmailField(blank=True, help_text="Primary contact email")
    contact_phone = models.CharField(max_length=20, blank=True, help_text="Primary contact phone")
    
    # Status and timestamps
    is_active = models.BooleanField(default=True, help_text="Whether tenant is active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    objects = TenantManager()
    
    # Import optimized manager
    @property
    def optimized_objects(self):
        from .optimizations import OptimizedTenantManager
        return OptimizedTenantManager()
    
    class Meta:
        db_table = 'tenants'
        verbose_name = 'Tenant'
        verbose_name_plural = 'Tenants'
        ordering = ['name']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['is_active']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return self.name
    
    def clean(self):
        """Validate tenant data."""
        super().clean()
        if not self.name.strip():
            raise ValidationError({'name': 'Tenant name cannot be empty'})
    
    def save(self, *args, **kwargs):
        """Override save to ensure data validation."""
        self.full_clean()
        super().save(*args, **kwargs)


class TenantAwareManager(models.Manager):
    """
    Base manager for tenant-aware models.
    Automatically filters queries by tenant.
    """
    
    def get_queryset(self):
        """Override to add tenant filtering."""
        from .middleware import get_current_tenant
        
        queryset = super().get_queryset()
        current_tenant = get_current_tenant()
        
        if current_tenant:
            return queryset.filter(tenant=current_tenant)
        return queryset
    
    def all_tenants(self):
        """Get objects from all tenants (admin use)."""
        return super().get_queryset()


class TenantAwareModel(models.Model):
    """
    Abstract base model for tenant-aware models.
    Automatically adds tenant relationship and filtering.
    """
    
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name='%(class)s_set',
        help_text="Tenant this record belongs to"
    )
    
    objects = TenantAwareManager()
    
    # Import optimized manager
    @classmethod
    def get_optimized_objects(cls):
        from .optimizations import OptimizedTenantAwareManager
        return OptimizedTenantAwareManager()
    
    class Meta:
        abstract = True
    
    def save(self, *args, **kwargs):
        """Override save to ensure tenant is set."""
        if not self.tenant_id:
            from .middleware import get_current_tenant
            current_tenant = get_current_tenant()
            if current_tenant:
                self.tenant = current_tenant
            else:
                raise ValidationError("No tenant context available")
        
        super().save(*args, **kwargs)


class User(AbstractUser):
    """
    Custom user model with tenant relationships and roles.
    """
    
    class Role(models.TextChoices):
        ADMIN_USER = 'admin_user', 'Admin User'
        TENANT_ADMIN = 'tenant_admin', 'Tenant Admin'
        EVENT_OPERATOR = 'event_operator', 'Event Operator'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Tenant relationships
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name='users',
        null=True,
        blank=True,
        help_text="Primary tenant for this user"
    )
    
    # Role and permissions
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.EVENT_OPERATOR,
        help_text="User role within the system"
    )
    
    # Additional fields
    phone = models.CharField(max_length=20, blank=True, help_text="Contact phone number")
    
    # Status fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        indexes = [
            models.Index(fields=['tenant', 'role']),
            models.Index(fields=['tenant', 'is_active']),
            models.Index(fields=['email']),
            models.Index(fields=['username']),
            models.Index(fields=['created_at']),
        ]
    
    # Add optimized manager
    @classmethod
    def get_optimized_objects(cls):
        from .optimizations import OptimizedUserManager
        return OptimizedUserManager()
    
    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
    
    def clean(self):
        """Validate user data."""
        super().clean()
        
        # Admin users don't need a tenant
        if self.role == self.Role.ADMIN_USER:
            self.tenant = None
        elif not self.tenant and self.role != self.Role.ADMIN_USER:
            raise ValidationError({'tenant': 'Non-admin users must have a tenant assigned'})
    
    def save(self, *args, **kwargs):
        """Override save to ensure data validation."""
        self.full_clean()
        super().save(*args, **kwargs)
    
    @property
    def is_admin_user(self):
        """Check if user is an admin user."""
        return self.role == self.Role.ADMIN_USER
    
    @property
    def is_tenant_admin(self):
        """Check if user is a tenant admin."""
        return self.role == self.Role.TENANT_ADMIN
    
    @property
    def is_event_operator(self):
        """Check if user is an event operator."""
        return self.role == self.Role.EVENT_OPERATOR
    
    def has_tenant_access(self, tenant):
        """Check if user has access to a specific tenant."""
        if self.is_admin_user:
            return True
        return self.tenant == tenant


class TenantUser(models.Model):
    """
    Many-to-many relationship between users and tenants.
    Allows users to have access to multiple tenants with different roles.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tenant_memberships')
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='user_memberships')
    role = models.CharField(
        max_length=20,
        choices=User.Role.choices,
        default=User.Role.EVENT_OPERATOR,
        help_text="User role within this specific tenant"
    )
    
    is_active = models.BooleanField(default=True, help_text="Whether membership is active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'tenant_users'
        verbose_name = 'Tenant User'
        verbose_name_plural = 'Tenant Users'
        unique_together = ['user', 'tenant']
        indexes = [
            models.Index(fields=['user', 'tenant']),
            models.Index(fields=['tenant', 'role']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.tenant.name} ({self.get_role_display()})"