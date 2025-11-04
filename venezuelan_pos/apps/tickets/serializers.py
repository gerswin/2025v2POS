from rest_framework import serializers
from django.utils import timezone
from .models import DigitalTicket, TicketTemplate, TicketValidationLog


class DigitalTicketSerializer(serializers.ModelSerializer):
    """Serializer for Digital Tickets."""
    
    # Read-only computed fields
    customer_name = serializers.CharField(source='customer.full_name', read_only=True)
    event_name = serializers.CharField(source='event.name', read_only=True)
    zone_name = serializers.CharField(source='zone.name', read_only=True)
    seat_label = serializers.SerializerMethodField()
    is_valid = serializers.BooleanField(read_only=True)
    can_be_used = serializers.BooleanField(read_only=True)
    remaining_uses = serializers.IntegerField(read_only=True)
    
    # QR code image URL
    qr_code_image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = DigitalTicket
        fields = [
            'id', 'ticket_number', 'sequence_number', 'ticket_type',
            'customer_name', 'event_name', 'zone_name', 'seat_label',
            'unit_price', 'total_price', 'currency',
            'status', 'usage_count', 'max_usage_count',
            'is_valid', 'can_be_used', 'remaining_uses',
            'valid_from', 'valid_until',
            'first_used_at', 'last_used_at',
            'qr_code_image_url', 'validation_hash',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'ticket_number', 'validation_hash',
            'usage_count', 'first_used_at', 'last_used_at',
            'created_at', 'updated_at'
        ]
    
    def get_seat_label(self, obj):
        """Get seat label or general admission."""
        return obj.seat_label
    
    def get_qr_code_image_url(self, obj):
        """Get QR code image URL."""
        if obj.qr_code_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.qr_code_image.url)
            return obj.qr_code_image.url
        return None


class TicketValidationSerializer(serializers.Serializer):
    """Serializer for ticket validation requests."""
    
    ticket_number = serializers.CharField(
        max_length=50,
        required=False,
        help_text="Ticket number to validate"
    )
    qr_code_data = serializers.CharField(
        required=False,
        help_text="QR code data to validate"
    )
    validation_system_id = serializers.CharField(
        max_length=255,
        required=True,
        help_text="ID of the validation system"
    )
    validation_location = serializers.CharField(
        max_length=255,
        required=False,
        help_text="Location where validation is occurring"
    )
    mark_as_used = serializers.BooleanField(
        default=True,
        help_text="Whether to mark ticket as used (false for check-only)"
    )
    
    def validate(self, data):
        """Validate that either ticket_number or qr_code_data is provided."""
        if not data.get('ticket_number') and not data.get('qr_code_data'):
            raise serializers.ValidationError(
                "Either ticket_number or qr_code_data must be provided"
            )
        return data


class TicketValidationResponseSerializer(serializers.Serializer):
    """Serializer for ticket validation responses."""
    
    valid = serializers.BooleanField()
    ticket_number = serializers.CharField(required=False)
    customer_name = serializers.CharField(required=False)
    event_name = serializers.CharField(required=False)
    seat_label = serializers.CharField(required=False)
    status = serializers.CharField(required=False)
    usage_count = serializers.IntegerField(required=False)
    max_usage = serializers.IntegerField(required=False)
    remaining_uses = serializers.IntegerField(required=False)
    valid_from = serializers.DateTimeField(required=False)
    valid_until = serializers.DateTimeField(required=False)
    reason = serializers.CharField(required=False)
    validation_timestamp = serializers.DateTimeField(default=timezone.now)


class TicketValidationLogSerializer(serializers.ModelSerializer):
    """Serializer for Ticket Validation Logs."""
    
    ticket_number = serializers.CharField(source='ticket.ticket_number', read_only=True)
    customer_name = serializers.CharField(source='ticket.customer.full_name', read_only=True)
    event_name = serializers.CharField(source='ticket.event.name', read_only=True)
    
    class Meta:
        model = TicketValidationLog
        fields = [
            'id', 'ticket_number', 'customer_name', 'event_name',
            'validation_system_id', 'validation_result', 'validation_method',
            'usage_count_before', 'usage_count_after',
            'validation_location', 'validated_at'
        ]
        read_only_fields = ['id', 'validated_at']


class TicketTemplateSerializer(serializers.ModelSerializer):
    """Serializer for Ticket Templates."""
    
    class Meta:
        model = TicketTemplate
        fields = [
            'id', 'name', 'template_type', 'html_content', 'css_styles',
            'page_size', 'orientation', 'include_qr_code', 'include_barcode',
            'include_logo', 'is_active', 'is_default',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate_name(self, value):
        """Validate template name is unique for tenant and type."""
        if not value.strip():
            raise serializers.ValidationError("Template name cannot be empty")
        
        # Check uniqueness within tenant and template type
        tenant = self.context['request'].user.tenant
        template_type = self.initial_data.get('template_type', self.instance.template_type if self.instance else None)
        
        existing = TicketTemplate.objects.filter(
            tenant=tenant,
            name=value.strip(),
            template_type=template_type
        )
        
        if self.instance:
            existing = existing.exclude(pk=self.instance.pk)
        
        if existing.exists():
            raise serializers.ValidationError(
                f"Template with name '{value}' already exists for this type"
            )
        
        return value.strip()


class TicketGenerationSerializer(serializers.Serializer):
    """Serializer for manual ticket generation requests."""
    
    transaction_id = serializers.UUIDField(
        help_text="Transaction ID to generate tickets for"
    )
    regenerate = serializers.BooleanField(
        default=False,
        help_text="Whether to regenerate existing tickets"
    )


class TicketLookupSerializer(serializers.Serializer):
    """Serializer for ticket lookup requests."""
    
    ticket_number = serializers.CharField(
        max_length=50,
        required=False,
        help_text="Ticket number to lookup"
    )
    customer_email = serializers.EmailField(
        required=False,
        help_text="Customer email to lookup tickets"
    )
    customer_phone = serializers.CharField(
        max_length=20,
        required=False,
        help_text="Customer phone to lookup tickets"
    )
    event_id = serializers.UUIDField(
        required=False,
        help_text="Event ID to filter tickets"
    )
    
    def validate(self, data):
        """Validate that at least one lookup parameter is provided."""
        if not any([
            data.get('ticket_number'),
            data.get('customer_email'),
            data.get('customer_phone')
        ]):
            raise serializers.ValidationError(
                "At least one lookup parameter must be provided"
            )
        return data


class TicketResendSerializer(serializers.Serializer):
    """Serializer for ticket resend requests."""
    
    ticket_ids = serializers.ListField(
        child=serializers.UUIDField(),
        help_text="List of ticket IDs to resend"
    )
    delivery_method = serializers.ChoiceField(
        choices=[
            ('email', 'Email'),
            ('sms', 'SMS'),
            ('whatsapp', 'WhatsApp'),
        ],
        default='email',
        help_text="Delivery method for resending tickets"
    )
    custom_message = serializers.CharField(
        max_length=500,
        required=False,
        help_text="Custom message to include with resent tickets"
    )


class TicketUsageStatsSerializer(serializers.Serializer):
    """Serializer for ticket usage statistics."""
    
    event_id = serializers.UUIDField(required=False)
    zone_id = serializers.UUIDField(required=False)
    date_from = serializers.DateTimeField(required=False)
    date_to = serializers.DateTimeField(required=False)
    
    # Response fields
    total_tickets = serializers.IntegerField(read_only=True)
    active_tickets = serializers.IntegerField(read_only=True)
    used_tickets = serializers.IntegerField(read_only=True)
    expired_tickets = serializers.IntegerField(read_only=True)
    cancelled_tickets = serializers.IntegerField(read_only=True)
    usage_rate = serializers.FloatField(read_only=True)
    
    def validate(self, data):
        """Validate date range."""
        date_from = data.get('date_from')
        date_to = data.get('date_to')
        
        if date_from and date_to and date_from >= date_to:
            raise serializers.ValidationError(
                "date_from must be before date_to"
            )
        
        return data


class MultiEntryValidationSerializer(serializers.Serializer):
    """Serializer for multi-entry ticket validation requests."""
    
    ticket_number = serializers.CharField(
        max_length=50,
        required=False,
        help_text="Ticket number to validate"
    )
    qr_code_data = serializers.CharField(
        required=False,
        help_text="QR code data to validate"
    )
    validation_system_id = serializers.CharField(
        max_length=255,
        required=True,
        help_text="ID of the validation system"
    )
    validation_location = serializers.CharField(
        max_length=255,
        required=False,
        help_text="Location where validation is occurring"
    )
    action = serializers.ChoiceField(
        choices=[('check_in', 'Check In'), ('check_out', 'Check Out')],
        default='check_in',
        help_text="Action to perform (check_in or check_out)"
    )
    
    def validate(self, data):
        """Validate that either ticket_number or qr_code_data is provided."""
        if not data.get('ticket_number') and not data.get('qr_code_data'):
            raise serializers.ValidationError(
                "Either ticket_number or qr_code_data must be provided"
            )
        return data


class BulkValidationSerializer(serializers.Serializer):
    """Serializer for bulk ticket validation requests."""
    
    ticket_identifiers = serializers.ListField(
        child=serializers.CharField(max_length=500),
        max_length=100,
        help_text="List of ticket numbers or QR code data to validate"
    )
    validation_system_id = serializers.CharField(
        max_length=255,
        required=True,
        help_text="ID of the validation system"
    )
    validation_location = serializers.CharField(
        max_length=255,
        required=False,
        help_text="Location where validation is occurring"
    )
    mark_as_used = serializers.BooleanField(
        default=True,
        help_text="Whether to mark tickets as used (false for check-only)"
    )


class ValidationStatsDetailedSerializer(serializers.Serializer):
    """Serializer for detailed validation statistics."""
    
    date_from = serializers.DateTimeField(required=False)
    date_to = serializers.DateTimeField(required=False)
    system_id = serializers.CharField(max_length=255, required=False)
    
    # Response fields
    total_validations = serializers.IntegerField(read_only=True)
    successful_validations = serializers.IntegerField(read_only=True)
    failed_validations = serializers.IntegerField(read_only=True)
    success_rate = serializers.FloatField(read_only=True)
    method_breakdown = serializers.DictField(read_only=True)
    system_breakdown = serializers.DictField(read_only=True)
    recent_activity = serializers.DictField(read_only=True)