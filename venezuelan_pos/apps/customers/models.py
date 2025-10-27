import uuid
import re
from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from phonenumber_field.modelfields import PhoneNumberField
from venezuelan_pos.apps.tenants.models import TenantAwareModel


def validate_venezuelan_cedula(value):
    """
    Validate Venezuelan cédula format.
    Format: V-12345678 or E-12345678 (V for Venezuelan, E for foreigner)
    """
    if not value:
        return
    
    # Remove spaces and convert to uppercase
    cedula = value.replace(' ', '').upper()
    
    # Check format: Letter-Numbers
    pattern = r'^[VE]-\d{7,8}$'
    if not re.match(pattern, cedula):
        raise ValidationError(
            'Cédula must be in format V-12345678 or E-12345678'
        )
    
    # Extract the numeric part for additional validation
    numeric_part = cedula.split('-')[1]
    if len(numeric_part) < 7:
        raise ValidationError('Cédula number must have at least 7 digits')


class CustomerManager(models.Manager):
    """Custom manager for Customer model."""
    
    def search(self, query):
        """Search customers by name, phone, email, or cédula."""
        if not query:
            return self.none()
        
        return self.filter(
            models.Q(name__icontains=query) |
            models.Q(surname__icontains=query) |
            models.Q(phone__icontains=query) |
            models.Q(email__icontains=query) |
            models.Q(identification__icontains=query)
        ).distinct()
    
    def by_identification(self, identification):
        """Find customer by identification number."""
        if not identification:
            return self.none()
        
        # Normalize identification format
        normalized = identification.replace(' ', '').upper()
        return self.filter(identification=normalized)


class Customer(TenantAwareModel):
    """
    Customer model for storing customer information.
    Captures basic customer data required for ticket sales and notifications.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Required fields
    name = models.CharField(
        max_length=100,
        help_text="Customer's first name"
    )
    surname = models.CharField(
        max_length=100,
        help_text="Customer's last name"
    )
    
    # Contact information (at least one required)
    phone = PhoneNumberField(
        blank=True,
        null=True,
        region='VE',  # Default to Venezuela
        help_text="Customer's phone number (Venezuelan format preferred)"
    )
    email = models.EmailField(
        blank=True,
        null=True,
        help_text="Customer's email address"
    )
    
    # Venezuelan identification
    identification = models.CharField(
        max_length=15,
        blank=True,
        null=True,
        validators=[validate_venezuelan_cedula],
        help_text="Venezuelan cédula (format: V-12345678 or E-12345678)"
    )
    
    # Additional information
    date_of_birth = models.DateField(
        blank=True,
        null=True,
        help_text="Customer's date of birth"
    )
    address = models.TextField(
        blank=True,
        help_text="Customer's address"
    )
    
    # Metadata
    notes = models.TextField(
        blank=True,
        help_text="Additional notes about the customer"
    )
    
    # Status and timestamps
    is_active = models.BooleanField(
        default=True,
        help_text="Whether customer is active"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    objects = CustomerManager()
    
    class Meta:
        db_table = 'customers'
        verbose_name = 'Customer'
        verbose_name_plural = 'Customers'
        ordering = ['surname', 'name']
        indexes = [
            models.Index(fields=['tenant', 'surname', 'name']),
            models.Index(fields=['tenant', 'phone']),
            models.Index(fields=['tenant', 'email']),
            models.Index(fields=['tenant', 'identification']),
        ]
        constraints = [
            # Ensure unique identification per tenant
            models.UniqueConstraint(
                fields=['tenant', 'identification'],
                condition=models.Q(identification__isnull=False),
                name='unique_identification_per_tenant'
            ),
            # Ensure unique email per tenant
            models.UniqueConstraint(
                fields=['tenant', 'email'],
                condition=models.Q(email__isnull=False),
                name='unique_email_per_tenant'
            ),
        ]
    
    def __str__(self):
        return f"{self.name} {self.surname}"
    
    def clean(self):
        """Validate customer data."""
        super().clean()
        
        # At least phone or email must be provided
        if not self.phone and not self.email:
            raise ValidationError(
                'Customer must have at least a phone number or email address'
            )
        
        # Normalize identification if provided
        if self.identification:
            self.identification = self.identification.replace(' ', '').upper()
        
        # Validate name fields are not empty
        if not self.name.strip():
            raise ValidationError({'name': 'Name cannot be empty'})
        if not self.surname.strip():
            raise ValidationError({'surname': 'Surname cannot be empty'})
    
    def save(self, *args, **kwargs):
        """Override save to ensure data validation."""
        self.full_clean()
        super().save(*args, **kwargs)
    
    @property
    def full_name(self):
        """Return customer's full name."""
        return f"{self.name} {self.surname}"
    
    @property
    def display_identification(self):
        """Return formatted identification or 'N/A' if not provided."""
        return self.identification or 'N/A'
    
    @property
    def primary_contact(self):
        """Return primary contact method (phone or email)."""
        if self.phone:
            return str(self.phone)
        elif self.email:
            return self.email
        return 'No contact info'
    
    def get_purchase_history(self):
        """Get customer's purchase history (to be implemented with sales integration)."""
        # This will be implemented in task 4.2 when integrating with sales
        return []


class CustomerPreferences(TenantAwareModel):
    """
    Customer communication preferences for notifications.
    Manages opt-in/opt-out settings for different communication channels.
    """
    
    class CommunicationChannel(models.TextChoices):
        EMAIL = 'email', 'Email'
        SMS = 'sms', 'SMS'
        WHATSAPP = 'whatsapp', 'WhatsApp'
        PHONE = 'phone', 'Phone Call'
    
    class NotificationType(models.TextChoices):
        PURCHASE_CONFIRMATION = 'purchase_confirmation', 'Purchase Confirmation'
        PAYMENT_REMINDER = 'payment_reminder', 'Payment Reminder'
        EVENT_REMINDER = 'event_reminder', 'Event Reminder'
        PROMOTIONAL = 'promotional', 'Promotional'
        SYSTEM_UPDATES = 'system_updates', 'System Updates'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.OneToOneField(
        Customer,
        on_delete=models.CASCADE,
        related_name='preferences',
        help_text="Customer these preferences belong to"
    )
    
    # Communication channel preferences
    email_enabled = models.BooleanField(
        default=True,
        help_text="Allow email communications"
    )
    sms_enabled = models.BooleanField(
        default=True,
        help_text="Allow SMS communications"
    )
    whatsapp_enabled = models.BooleanField(
        default=True,
        help_text="Allow WhatsApp communications"
    )
    phone_enabled = models.BooleanField(
        default=False,
        help_text="Allow phone call communications"
    )
    
    # Notification type preferences
    purchase_confirmations = models.BooleanField(
        default=True,
        help_text="Receive purchase confirmation notifications"
    )
    payment_reminders = models.BooleanField(
        default=True,
        help_text="Receive payment reminder notifications"
    )
    event_reminders = models.BooleanField(
        default=True,
        help_text="Receive event reminder notifications"
    )
    promotional_messages = models.BooleanField(
        default=False,
        help_text="Receive promotional messages"
    )
    system_updates = models.BooleanField(
        default=True,
        help_text="Receive system update notifications"
    )
    
    # Preferred communication times
    preferred_contact_time_start = models.TimeField(
        default='09:00',
        help_text="Preferred start time for communications"
    )
    preferred_contact_time_end = models.TimeField(
        default='18:00',
        help_text="Preferred end time for communications"
    )
    
    # Language preference
    preferred_language = models.CharField(
        max_length=5,
        choices=[('es', 'Español'), ('en', 'English')],
        default='es',
        help_text="Preferred language for communications"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'customer_preferences'
        verbose_name = 'Customer Preferences'
        verbose_name_plural = 'Customer Preferences'
    
    def __str__(self):
        return f"Preferences for {self.customer.full_name}"
    
    def can_receive_notification(self, channel, notification_type):
        """
        Check if customer can receive a specific type of notification
        through a specific channel.
        """
        # Check if channel is enabled
        channel_enabled = {
            self.CommunicationChannel.EMAIL: self.email_enabled,
            self.CommunicationChannel.SMS: self.sms_enabled,
            self.CommunicationChannel.WHATSAPP: self.whatsapp_enabled,
            self.CommunicationChannel.PHONE: self.phone_enabled,
        }.get(channel, False)
        
        if not channel_enabled:
            return False
        
        # Check if notification type is enabled
        notification_enabled = {
            self.NotificationType.PURCHASE_CONFIRMATION: self.purchase_confirmations,
            self.NotificationType.PAYMENT_REMINDER: self.payment_reminders,
            self.NotificationType.EVENT_REMINDER: self.event_reminders,
            self.NotificationType.PROMOTIONAL: self.promotional_messages,
            self.NotificationType.SYSTEM_UPDATES: self.system_updates,
        }.get(notification_type, False)
        
        return notification_enabled
    
    def get_enabled_channels(self):
        """Get list of enabled communication channels."""
        channels = []
        if self.email_enabled:
            channels.append(self.CommunicationChannel.EMAIL)
        if self.sms_enabled:
            channels.append(self.CommunicationChannel.SMS)
        if self.whatsapp_enabled:
            channels.append(self.CommunicationChannel.WHATSAPP)
        if self.phone_enabled:
            channels.append(self.CommunicationChannel.PHONE)
        return channels
    
    @classmethod
    def create_default_preferences(cls, customer):
        """Create default preferences for a customer."""
        return cls.objects.create(
            customer=customer,
            tenant=customer.tenant,
            # All defaults are set in the field definitions
        )


# Signal to automatically create preferences when customer is created
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=Customer)
def create_customer_preferences(sender, instance, created, **kwargs):
    """Automatically create preferences when a customer is created."""
    if created:
        CustomerPreferences.create_default_preferences(instance)