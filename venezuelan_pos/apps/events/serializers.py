from rest_framework import serializers
from django.utils import timezone
from .models import Venue, Event, EventConfiguration


class VenueSerializer(serializers.ModelSerializer):
    """Serializer for Venue model."""
    
    class Meta:
        model = Venue
        fields = [
            'id', 'name', 'address', 'city', 'state', 'country', 'postal_code',
            'capacity', 'venue_type', 'contact_phone', 'contact_email',
            'configuration', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate_name(self, value):
        """Validate venue name is not empty."""
        if not value.strip():
            raise serializers.ValidationError("Venue name cannot be empty.")
        return value.strip()
    
    def validate_capacity(self, value):
        """Validate venue capacity is positive."""
        if value is not None and value <= 0:
            raise serializers.ValidationError("Venue capacity must be positive.")
        return value


class EventConfigurationSerializer(serializers.ModelSerializer):
    """Serializer for EventConfiguration model."""
    
    class Meta:
        model = EventConfiguration
        fields = [
            'id', 'partial_payments_enabled', 'installment_plans_enabled',
            'flexible_payments_enabled', 'max_installments',
            'min_down_payment_percentage', 'payment_plan_expiry_days',
            'notifications_enabled', 'email_notifications', 'sms_notifications',
            'whatsapp_notifications', 'send_purchase_confirmation',
            'send_payment_reminders', 'send_event_reminders', 'event_reminder_days',
            'digital_tickets_enabled', 'qr_codes_enabled', 'pdf_tickets_enabled',
            'configuration', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate_min_down_payment_percentage(self, value):
        """Validate down payment percentage is between 0 and 100."""
        if value < 0 or value > 100:
            raise serializers.ValidationError(
                "Down payment percentage must be between 0 and 100."
            )
        return value
    
    def validate_max_installments(self, value):
        """Validate maximum installments is positive."""
        if value < 1:
            raise serializers.ValidationError(
                "Maximum installments must be at least 1."
            )
        return value
    
    def validate_payment_plan_expiry_days(self, value):
        """Validate payment plan expiry days is positive."""
        if value < 1:
            raise serializers.ValidationError(
                "Payment plan expiry must be at least 1 day."
            )
        return value


class EventSerializer(serializers.ModelSerializer):
    """Serializer for Event model."""
    
    venue_details = VenueSerializer(source='venue', read_only=True)
    event_configuration = EventConfigurationSerializer(read_only=True)
    is_sales_active = serializers.ReadOnlyField()
    is_upcoming = serializers.ReadOnlyField()
    is_ongoing = serializers.ReadOnlyField()
    is_past = serializers.ReadOnlyField()
    
    class Meta:
        model = Event
        fields = [
            'id', 'name', 'description', 'event_type', 'venue', 'venue_details',
            'start_date', 'end_date', 'sales_start_date', 'sales_end_date',
            'base_currency', 'currency_conversion_rate', 'status', 'configuration',
            'event_configuration', 'is_sales_active', 'is_upcoming', 'is_ongoing',
            'is_past', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate_name(self, value):
        """Validate event name is not empty."""
        if not value.strip():
            raise serializers.ValidationError("Event name cannot be empty.")
        return value.strip()
    
    def validate_currency_conversion_rate(self, value):
        """Validate currency conversion rate is positive."""
        if value <= 0:
            raise serializers.ValidationError(
                "Currency conversion rate must be positive."
            )
        return value
    
    def validate(self, data):
        """Validate event dates and sales configuration."""
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        sales_start_date = data.get('sales_start_date')
        sales_end_date = data.get('sales_end_date')
        
        # Validate event dates
        if start_date and end_date:
            if start_date >= end_date:
                raise serializers.ValidationError({
                    'end_date': 'End date must be after start date.'
                })
        
        # Validate sales dates
        if sales_start_date and sales_end_date:
            if sales_start_date >= sales_end_date:
                raise serializers.ValidationError({
                    'sales_end_date': 'Sales end date must be after sales start date.'
                })
        
        # Validate sales end before event start
        if sales_end_date and start_date:
            if sales_end_date > start_date:
                raise serializers.ValidationError({
                    'sales_end_date': 'Sales must end before event starts.'
                })
        
        return data
    
    def validate_venue(self, value):
        """Validate venue belongs to the same tenant."""
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            if not request.user.is_admin_user and value.tenant != request.user.tenant:
                raise serializers.ValidationError(
                    "Venue must belong to your tenant."
                )
        return value


class EventCreateSerializer(EventSerializer):
    """Serializer for creating events with configuration."""
    
    event_configuration = EventConfigurationSerializer(required=False)
    
    class Meta(EventSerializer.Meta):
        pass
    
    def create(self, validated_data):
        """Create event with optional configuration."""
        config_data = validated_data.pop('event_configuration', None)
        event = Event.objects.create(**validated_data)
        
        if config_data:
            config_data['tenant'] = event.tenant
            EventConfiguration.objects.create(event=event, **config_data)
        else:
            # Create default configuration
            EventConfiguration.objects.create(event=event, tenant=event.tenant)
        
        return event


class EventUpdateSerializer(EventSerializer):
    """Serializer for updating events with configuration."""
    
    event_configuration = EventConfigurationSerializer(required=False)
    
    class Meta(EventSerializer.Meta):
        pass
    
    def update(self, instance, validated_data):
        """Update event and its configuration."""
        config_data = validated_data.pop('event_configuration', None)
        
        # Update event fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update or create configuration
        if config_data:
            config_data['tenant'] = instance.tenant
            config, created = EventConfiguration.objects.get_or_create(
                event=instance,
                defaults=config_data
            )
            if not created:
                for attr, value in config_data.items():
                    setattr(config, attr, value)
                config.save()
        
        return instance


class EventListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for event lists."""
    
    venue_name = serializers.CharField(source='venue.name', read_only=True)
    venue_city = serializers.CharField(source='venue.city', read_only=True)
    is_sales_active = serializers.ReadOnlyField()
    
    class Meta:
        model = Event
        fields = [
            'id', 'name', 'event_type', 'venue_name', 'venue_city',
            'start_date', 'end_date', 'status', 'is_sales_active',
            'created_at'
        ]