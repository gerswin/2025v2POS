"""
Notification models for Venezuelan POS System.
"""

import uuid
from django.db import models
from django.utils import timezone
from venezuelan_pos.apps.tenants.models import TenantAwareModel


class NotificationTemplate(TenantAwareModel):
    """Template for notifications with personalization support."""
    
    TEMPLATE_TYPES = [
        ('email', 'Email'),
        ('sms', 'SMS'),
        ('whatsapp', 'WhatsApp'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    template_type = models.CharField(max_length=20, choices=TEMPLATE_TYPES)
    subject = models.CharField(max_length=200, blank=True)  # For email templates
    content = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'notification_templates'
        unique_together = ['tenant', 'name', 'template_type']
        indexes = [
            models.Index(fields=['tenant', 'template_type']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.template_type})"


class NotificationLog(TenantAwareModel):
    """Log of sent notifications for tracking and analytics."""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('retry', 'Retry'),
    ]
    
    CHANNEL_CHOICES = [
        ('email', 'Email'),
        ('sms', 'SMS'),
        ('whatsapp', 'WhatsApp'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    template = models.ForeignKey(
        NotificationTemplate, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES)
    recipient = models.CharField(max_length=255)  # Email or phone number
    subject = models.CharField(max_length=200, blank=True)
    content = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    error_message = models.TextField(blank=True)
    task_id = models.CharField(max_length=255, blank=True)  # Celery task ID
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Optional relationships
    customer = models.ForeignKey(
        'customers.Customer',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notifications'
    )
    transaction = models.ForeignKey(
        'sales.Transaction',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notifications'
    )
    event = models.ForeignKey(
        'events.Event',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notifications'
    )
    
    class Meta:
        db_table = 'notification_logs'
        indexes = [
            models.Index(fields=['tenant', 'status']),
            models.Index(fields=['channel', 'status']),
            models.Index(fields=['created_at']),
            models.Index(fields=['customer']),
            models.Index(fields=['transaction']),
            models.Index(fields=['event']),
        ]
    
    def __str__(self):
        return f"{self.channel} to {self.recipient} - {self.status}"
    
    def mark_sent(self):
        """Mark notification as sent."""
        self.status = 'sent'
        self.sent_at = timezone.now()
        self.save(update_fields=['status', 'sent_at'])
    
    def mark_failed(self, error_message):
        """Mark notification as failed with error message."""
        self.status = 'failed'
        self.error_message = error_message
        self.save(update_fields=['status', 'error_message'])


class NotificationPreference(TenantAwareModel):
    """Customer notification preferences."""
    
    customer = models.OneToOneField(
        'customers.Customer',
        on_delete=models.CASCADE,
        related_name='notification_preferences'
    )
    
    # Channel preferences
    email_enabled = models.BooleanField(default=True)
    sms_enabled = models.BooleanField(default=True)
    whatsapp_enabled = models.BooleanField(default=True)
    
    # Notification type preferences
    purchase_confirmations = models.BooleanField(default=True)
    payment_reminders = models.BooleanField(default=True)
    event_reminders = models.BooleanField(default=True)
    promotional_messages = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'notification_preferences'
        indexes = [
            models.Index(fields=['tenant', 'customer']),
        ]
    
    def __str__(self):
        return f"Preferences for {self.customer}"