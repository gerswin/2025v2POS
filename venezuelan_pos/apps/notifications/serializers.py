"""
Serializers for notification system.
"""

from rest_framework import serializers
from .models import NotificationTemplate, NotificationLog, NotificationPreference


class NotificationTemplateSerializer(serializers.ModelSerializer):
    """Serializer for notification templates."""
    
    class Meta:
        model = NotificationTemplate
        fields = [
            'id', 'name', 'template_type', 'subject', 'content',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate_content(self, value):
        """Validate template content for basic Django template syntax."""
        from django.template import Template, TemplateSyntaxError
        
        try:
            Template(value)
        except TemplateSyntaxError as e:
            raise serializers.ValidationError(f"Invalid template syntax: {e}")
        
        return value


class NotificationLogSerializer(serializers.ModelSerializer):
    """Serializer for notification logs."""
    
    template_name = serializers.CharField(source='template.name', read_only=True)
    customer_name = serializers.CharField(source='customer.full_name', read_only=True)
    
    class Meta:
        model = NotificationLog
        fields = [
            'id', 'template', 'template_name', 'channel', 'recipient',
            'subject', 'content', 'status', 'error_message', 'task_id',
            'sent_at', 'created_at', 'customer', 'customer_name',
            'transaction', 'event'
        ]
        read_only_fields = [
            'id', 'template_name', 'customer_name', 'sent_at', 'created_at'
        ]


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    """Serializer for notification preferences."""
    
    customer_name = serializers.CharField(source='customer.full_name', read_only=True)
    
    class Meta:
        model = NotificationPreference
        fields = [
            'customer', 'customer_name', 'email_enabled', 'sms_enabled',
            'whatsapp_enabled', 'purchase_confirmations', 'payment_reminders',
            'event_reminders', 'promotional_messages', 'created_at', 'updated_at'
        ]
        read_only_fields = ['customer_name', 'created_at', 'updated_at']


class SendNotificationSerializer(serializers.Serializer):
    """Serializer for sending notifications via API."""
    
    template_name = serializers.CharField(max_length=100)
    channel = serializers.ChoiceField(choices=['email', 'sms', 'whatsapp'])
    recipient = serializers.CharField(max_length=255)
    context = serializers.JSONField(default=dict)
    customer_id = serializers.UUIDField(required=False)
    transaction_id = serializers.UUIDField(required=False)
    event_id = serializers.UUIDField(required=False)
    
    def validate_recipient(self):
        """Validate recipient based on channel."""
        channel = self.initial_data.get('channel')
        recipient = self.validated_data.get('recipient')
        
        if channel == 'email':
            # Basic email validation
            if '@' not in recipient:
                raise serializers.ValidationError("Invalid email address")
        elif channel in ['sms', 'whatsapp']:
            # Basic phone validation
            if not recipient.replace('+', '').replace('-', '').replace(' ', '').isdigit():
                raise serializers.ValidationError("Invalid phone number")
        
        return recipient


class NotificationStatsSerializer(serializers.Serializer):
    """Serializer for notification statistics."""
    
    total_sent = serializers.IntegerField()
    by_channel = serializers.DictField()
    by_status = serializers.DictField()
    success_rate = serializers.FloatField()
    period_days = serializers.IntegerField()