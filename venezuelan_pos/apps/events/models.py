import uuid
from decimal import Decimal
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from venezuelan_pos.apps.tenants.models import TenantAwareModel


class Venue(TenantAwareModel):
    """
    Venue model for event locations.
    Supports both physical and virtual venues.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, help_text="Venue name")
    address = models.TextField(blank=True, help_text="Physical address of the venue")
    city = models.CharField(max_length=100, blank=True, help_text="City where venue is located")
    state = models.CharField(max_length=100, blank=True, help_text="State/Province")
    country = models.CharField(max_length=100, default='Venezuela', help_text="Country")
    postal_code = models.CharField(max_length=20, blank=True, help_text="Postal/ZIP code")
    
    # Venue details
    capacity = models.PositiveIntegerField(null=True, blank=True, help_text="Maximum venue capacity")
    venue_type = models.CharField(
        max_length=50,
        choices=[
            ('physical', 'Physical Venue'),
            ('virtual', 'Virtual Venue'),
            ('hybrid', 'Hybrid Venue'),
        ],
        default='physical',
        help_text="Type of venue"
    )
    
    # Contact information
    contact_phone = models.CharField(max_length=20, blank=True, help_text="Venue contact phone")
    contact_email = models.EmailField(blank=True, help_text="Venue contact email")
    
    # Configuration
    configuration = models.JSONField(
        default=dict,
        blank=True,
        help_text="Venue-specific configuration settings"
    )
    
    # Status and timestamps
    is_active = models.BooleanField(default=True, help_text="Whether venue is active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'venues'
        verbose_name = 'Venue'
        verbose_name_plural = 'Venues'
        ordering = ['name']
        unique_together = ['tenant', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.city})"
    
    def clean(self):
        """Validate venue data."""
        super().clean()
        if not self.name.strip():
            raise ValidationError({'name': 'Venue name cannot be empty'})


class Event(TenantAwareModel):
    """
    Event model with tenant relationship.
    Supports both general assignment and numbered seating events.
    """
    
    class EventType(models.TextChoices):
        GENERAL_ASSIGNMENT = 'general_assignment', 'General Assignment Event'
        NUMBERED_SEAT = 'numbered_seat', 'Numbered Seat Event'
        MIXED = 'mixed', 'Mixed Event (Both Types)'
    
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        ACTIVE = 'active', 'Active'
        CLOSED = 'closed', 'Closed'
        CANCELLED = 'cancelled', 'Cancelled'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, help_text="Event name")
    description = models.TextField(blank=True, help_text="Event description")
    
    # Event type and venue
    event_type = models.CharField(
        max_length=20,
        choices=EventType.choices,
        default=EventType.GENERAL_ASSIGNMENT,
        help_text="Type of event seating"
    )
    venue = models.ForeignKey(
        Venue,
        on_delete=models.PROTECT,
        related_name='events',
        help_text="Venue where event takes place"
    )
    
    # Event dates and times
    start_date = models.DateTimeField(help_text="Event start date and time")
    end_date = models.DateTimeField(help_text="Event end date and time")
    
    # Sales configuration
    sales_start_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When ticket sales begin"
    )
    sales_end_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When ticket sales end"
    )
    
    # Currency and pricing
    base_currency = models.CharField(
        max_length=3,
        default='USD',
        help_text="Base currency for event pricing"
    )
    currency_conversion_rate = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        default=Decimal('1.0000'),
        help_text="Conversion rate from USD to local currency"
    )
    
    # Event status
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.DRAFT,
        help_text="Current event status"
    )
    
    # Configuration
    configuration = models.JSONField(
        default=dict,
        blank=True,
        help_text="Event-specific configuration settings"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'events'
        verbose_name = 'Event'
        verbose_name_plural = 'Events'
        ordering = ['-start_date']
        unique_together = ['tenant', 'name', 'start_date']
    
    def __str__(self):
        return f"{self.name} - {self.start_date.strftime('%Y-%m-%d')}"
    
    def clean(self):
        """Validate event data."""
        super().clean()
        
        if not self.name.strip():
            raise ValidationError({'name': 'Event name cannot be empty'})
        
        if self.start_date and self.end_date:
            if self.start_date >= self.end_date:
                raise ValidationError({
                    'end_date': 'End date must be after start date'
                })
        
        if self.sales_start_date and self.sales_end_date:
            if self.sales_start_date >= self.sales_end_date:
                raise ValidationError({
                    'sales_end_date': 'Sales end date must be after sales start date'
                })
        
        if self.sales_end_date and self.start_date:
            if self.sales_end_date > self.start_date:
                raise ValidationError({
                    'sales_end_date': 'Sales must end before event starts'
                })
        
        if self.currency_conversion_rate <= 0:
            raise ValidationError({
                'currency_conversion_rate': 'Currency conversion rate must be positive'
            })
    
    @property
    def is_sales_active(self):
        """Check if ticket sales are currently active."""
        now = timezone.now()
        
        if self.status != self.Status.ACTIVE:
            return False
        
        if self.sales_start_date and now < self.sales_start_date:
            return False
        
        if self.sales_end_date and now > self.sales_end_date:
            return False
        
        return True
    
    @property
    def is_upcoming(self):
        """Check if event is upcoming."""
        return timezone.now() < self.start_date
    
    @property
    def is_ongoing(self):
        """Check if event is currently ongoing."""
        now = timezone.now()
        return self.start_date <= now <= self.end_date
    
    @property
    def is_past(self):
        """Check if event has ended."""
        return timezone.now() > self.end_date


class EventConfiguration(TenantAwareModel):
    """
    Event configuration for partial payments and notifications.
    Separate model to allow flexible configuration per event.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.OneToOneField(
        Event,
        on_delete=models.CASCADE,
        related_name='event_configuration',
        help_text="Event this configuration belongs to"
    )
    
    # Partial payment configuration
    partial_payments_enabled = models.BooleanField(
        default=False,
        help_text="Whether partial payments are allowed for this event"
    )
    installment_plans_enabled = models.BooleanField(
        default=False,
        help_text="Whether installment payment plans are available"
    )
    flexible_payments_enabled = models.BooleanField(
        default=False,
        help_text="Whether flexible payment plans are available"
    )
    
    # Payment plan limits
    max_installments = models.PositiveIntegerField(
        default=3,
        help_text="Maximum number of installments allowed"
    )
    min_down_payment_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('20.00'),
        help_text="Minimum down payment percentage required"
    )
    payment_plan_expiry_days = models.PositiveIntegerField(
        default=30,
        help_text="Days until payment plan expires"
    )
    
    # Notification configuration
    notifications_enabled = models.BooleanField(
        default=True,
        help_text="Whether notifications are enabled for this event"
    )
    email_notifications = models.BooleanField(
        default=True,
        help_text="Send email notifications"
    )
    sms_notifications = models.BooleanField(
        default=False,
        help_text="Send SMS notifications"
    )
    whatsapp_notifications = models.BooleanField(
        default=False,
        help_text="Send WhatsApp notifications"
    )
    
    # Notification timing
    send_purchase_confirmation = models.BooleanField(
        default=True,
        help_text="Send confirmation when purchase is completed"
    )
    send_payment_reminders = models.BooleanField(
        default=True,
        help_text="Send reminders for pending payments"
    )
    send_event_reminders = models.BooleanField(
        default=True,
        help_text="Send reminders before event starts"
    )
    event_reminder_days = models.PositiveIntegerField(
        default=1,
        help_text="Days before event to send reminder"
    )
    
    # Digital ticket configuration
    digital_tickets_enabled = models.BooleanField(
        default=True,
        help_text="Whether digital tickets are generated"
    )
    qr_codes_enabled = models.BooleanField(
        default=True,
        help_text="Whether QR codes are included in tickets"
    )
    pdf_tickets_enabled = models.BooleanField(
        default=True,
        help_text="Whether PDF tickets are generated"
    )
    
    # Additional configuration
    configuration = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional event-specific configuration"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'event_configurations'
        verbose_name = 'Event Configuration'
        verbose_name_plural = 'Event Configurations'
    
    def __str__(self):
        return f"Configuration for {self.event.name}"
    
    def clean(self):
        """Validate event configuration."""
        super().clean()
        
        if self.min_down_payment_percentage < 0 or self.min_down_payment_percentage > 100:
            raise ValidationError({
                'min_down_payment_percentage': 'Down payment percentage must be between 0 and 100'
            })
        
        if self.max_installments < 1:
            raise ValidationError({
                'max_installments': 'Maximum installments must be at least 1'
            })
        
        if self.payment_plan_expiry_days < 1:
            raise ValidationError({
                'payment_plan_expiry_days': 'Payment plan expiry must be at least 1 day'
            })