"""
Mixins for integrating customer data with other models.
"""

from django.db import models
from django.core.exceptions import ValidationError
from .models import Customer


class CustomerRelatedMixin(models.Model):
    """
    Mixin for models that need to relate to customers.
    
    This mixin provides:
    - Customer foreign key relationship
    - Customer validation methods
    - Customer data access helpers
    """
    
    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,  # Protect customer data
        related_name='%(class)s_set',
        help_text="Customer associated with this record"
    )
    
    # Customer contact information (denormalized for performance)
    customer_name = models.CharField(
        max_length=100,
        help_text="Customer's full name (cached)"
    )
    customer_email = models.EmailField(
        blank=True,
        null=True,
        help_text="Customer's email (cached)"
    )
    customer_phone = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Customer's phone (cached)"
    )
    customer_identification = models.CharField(
        max_length=15,
        blank=True,
        null=True,
        help_text="Customer's identification (cached)"
    )
    
    class Meta:
        abstract = True
    
    def save(self, *args, **kwargs):
        """Override save to cache customer data."""
        if self.customer_id:
            self._cache_customer_data()
        super().save(*args, **kwargs)
    
    def _cache_customer_data(self):
        """Cache customer data for performance."""
        if self.customer:
            self.customer_name = self.customer.full_name
            self.customer_email = self.customer.email
            self.customer_phone = str(self.customer.phone) if self.customer.phone else None
            self.customer_identification = self.customer.identification
    
    def refresh_customer_data(self):
        """Refresh cached customer data from customer record."""
        if self.customer:
            self._cache_customer_data()
            self.save(update_fields=[
                'customer_name', 'customer_email', 
                'customer_phone', 'customer_identification'
            ])
    
    def get_customer_notification_preferences(self):
        """Get customer's notification preferences."""
        if self.customer:
            from .services import CustomerService
            return CustomerService.get_customer_notification_preferences(self.customer)
        return {}
    
    def validate_customer_for_transaction(self):
        """Validate customer data for transaction processing."""
        if not self.customer:
            raise ValidationError("Customer is required")
        
        if not self.customer.is_active:
            raise ValidationError("Customer account is inactive")
        
        from .services import CustomerService
        validation = CustomerService.validate_customer_for_purchase(self.customer)
        
        if not validation['is_valid']:
            raise ValidationError(f"Customer validation failed: {validation['errors']}")
        
        return validation


class CustomerTrackingMixin(models.Model):
    """
    Mixin for tracking customer-related activities.
    
    This mixin provides:
    - Customer activity tracking
    - Customer interaction logging
    """
    
    # Customer interaction metadata
    customer_ip_address = models.GenericIPAddressField(
        blank=True,
        null=True,
        help_text="Customer's IP address during interaction"
    )
    customer_user_agent = models.TextField(
        blank=True,
        help_text="Customer's user agent string"
    )
    customer_session_id = models.CharField(
        max_length=100,
        blank=True,
        help_text="Customer's session identifier"
    )
    
    class Meta:
        abstract = True
    
    def set_customer_tracking_data(self, request):
        """Set customer tracking data from request."""
        if request:
            self.customer_ip_address = self._get_client_ip(request)
            self.customer_user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]
            self.customer_session_id = request.session.session_key or ''
    
    def _get_client_ip(self, request):
        """Get client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class CustomerNotificationMixin:
    """
    Mixin for models that need to send notifications to customers.
    
    This mixin provides:
    - Customer notification helpers
    - Notification preference checking
    """
    
    def can_notify_customer(self, notification_type, channel):
        """
        Check if customer can receive notifications.
        
        Args:
            notification_type: Type of notification (e.g., 'purchase_confirmation')
            channel: Communication channel (e.g., 'email', 'sms')
        
        Returns:
            bool: True if customer can receive notification
        """
        if not hasattr(self, 'customer') or not self.customer:
            return False
        
        try:
            prefs = self.customer.preferences
            return prefs.can_receive_notification(channel, notification_type)
        except:
            return False
    
    def get_customer_contact_info(self):
        """Get customer contact information for notifications."""
        if not hasattr(self, 'customer') or not self.customer:
            return {}
        
        return {
            'email': self.customer.email,
            'phone': str(self.customer.phone) if self.customer.phone else None,
            'name': self.customer.full_name,
            'preferred_language': getattr(self.customer.preferences, 'preferred_language', 'es')
        }
    
    def prepare_customer_notification_data(self):
        """Prepare data for customer notifications."""
        contact_info = self.get_customer_contact_info()
        
        return {
            'customer': {
                'id': str(self.customer.id) if self.customer else None,
                'name': contact_info.get('name', ''),
                'email': contact_info.get('email', ''),
                'phone': contact_info.get('phone', ''),
                'preferred_language': contact_info.get('preferred_language', 'es'),
            },
            'record': {
                'id': str(self.id) if hasattr(self, 'id') else None,
                'type': self.__class__.__name__.lower(),
                'created_at': self.created_at.isoformat() if hasattr(self, 'created_at') else None,
            }
        }


# Example usage for future Transaction model:
"""
class Transaction(TenantAwareModel, CustomerRelatedMixin, CustomerTrackingMixin):
    # Transaction-specific fields
    fiscal_series = models.CharField(max_length=20, unique=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        # Validate customer before saving
        self.validate_customer_for_transaction()
        super().save(*args, **kwargs)
    
    def send_confirmation_notification(self):
        if self.can_notify_customer('purchase_confirmation', 'email'):
            # Send email notification
            pass
        
        if self.can_notify_customer('purchase_confirmation', 'sms'):
            # Send SMS notification
            pass
"""