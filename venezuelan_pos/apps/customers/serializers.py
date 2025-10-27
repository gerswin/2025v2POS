from rest_framework import serializers
from phonenumber_field.serializerfields import PhoneNumberField
from .models import Customer, CustomerPreferences


class CustomerPreferencesSerializer(serializers.ModelSerializer):
    """Serializer for customer communication preferences."""
    
    class Meta:
        model = CustomerPreferences
        fields = [
            'id',
            'email_enabled',
            'sms_enabled',
            'whatsapp_enabled',
            'phone_enabled',
            'purchase_confirmations',
            'payment_reminders',
            'event_reminders',
            'promotional_messages',
            'system_updates',
            'preferred_contact_time_start',
            'preferred_contact_time_end',
            'preferred_language',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class CustomerSerializer(serializers.ModelSerializer):
    """Serializer for customer data."""
    
    phone = PhoneNumberField(required=False, allow_blank=True)
    preferences = CustomerPreferencesSerializer(read_only=True)
    full_name = serializers.ReadOnlyField()
    display_identification = serializers.ReadOnlyField()
    primary_contact = serializers.ReadOnlyField()
    
    class Meta:
        model = Customer
        fields = [
            'id',
            'name',
            'surname',
            'phone',
            'email',
            'identification',
            'date_of_birth',
            'address',
            'notes',
            'is_active',
            'full_name',
            'display_identification',
            'primary_contact',
            'preferences',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'full_name',
            'display_identification',
            'primary_contact',
            'created_at',
            'updated_at',
        ]
    
    def validate(self, data):
        """Validate that at least phone or email is provided."""
        phone = data.get('phone')
        email = data.get('email')
        
        # If this is an update, check existing values
        if self.instance:
            phone = phone if phone is not None else self.instance.phone
            email = email if email is not None else self.instance.email
        
        if not phone and not email:
            raise serializers.ValidationError(
                "Customer must have at least a phone number or email address"
            )
        
        return data
    
    def validate_name(self, value):
        """Validate name is not empty."""
        if not value or not value.strip():
            raise serializers.ValidationError("Name cannot be empty")
        return value.strip()
    
    def validate_surname(self, value):
        """Validate surname is not empty."""
        if not value or not value.strip():
            raise serializers.ValidationError("Surname cannot be empty")
        return value.strip()
    
    def validate_identification(self, value):
        """Validate and normalize identification format."""
        if not value:
            return value
        
        # Normalize format
        normalized = value.replace(' ', '').upper()
        
        # The model validator will handle the format validation
        return normalized


class CustomerCreateSerializer(CustomerSerializer):
    """Serializer for creating customers with preferences."""
    
    preferences = CustomerPreferencesSerializer(required=False)
    
    class Meta(CustomerSerializer.Meta):
        fields = CustomerSerializer.Meta.fields
    
    def create(self, validated_data):
        """Create customer with optional preferences."""
        preferences_data = validated_data.pop('preferences', None)
        customer = Customer.objects.create(**validated_data)
        
        # Update preferences if provided (default preferences are created automatically)
        if preferences_data:
            preferences_serializer = CustomerPreferencesSerializer(
                customer.preferences,
                data=preferences_data,
                partial=True
            )
            if preferences_serializer.is_valid():
                preferences_serializer.save()
        
        return customer


class CustomerUpdateSerializer(CustomerSerializer):
    """Serializer for updating customers."""
    
    preferences = CustomerPreferencesSerializer(required=False)
    
    class Meta(CustomerSerializer.Meta):
        fields = CustomerSerializer.Meta.fields
    
    def update(self, instance, validated_data):
        """Update customer and preferences."""
        preferences_data = validated_data.pop('preferences', None)
        
        # Update customer fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update preferences if provided
        if preferences_data:
            preferences_serializer = CustomerPreferencesSerializer(
                instance.preferences,
                data=preferences_data,
                partial=True
            )
            if preferences_serializer.is_valid():
                preferences_serializer.save()
        
        return instance


class CustomerSearchSerializer(serializers.Serializer):
    """Serializer for customer search parameters."""
    
    query = serializers.CharField(
        max_length=255,
        required=True,
        help_text="Search query (name, phone, email, or identification)"
    )
    
    def validate_query(self, value):
        """Validate search query is not empty."""
        if not value or not value.strip():
            raise serializers.ValidationError("Search query cannot be empty")
        return value.strip()


class CustomerLookupSerializer(serializers.Serializer):
    """Serializer for customer lookup by identification."""
    
    identification = serializers.CharField(
        max_length=15,
        required=True,
        help_text="Customer identification number (cédula)"
    )
    
    def validate_identification(self, value):
        """Validate and normalize identification format."""
        if not value or not value.strip():
            raise serializers.ValidationError("Identification cannot be empty")
        
        # Normalize format
        normalized = value.replace(' ', '').upper()
        return normalized


class CustomerSummarySerializer(serializers.ModelSerializer):
    """Lightweight serializer for customer summaries in lists."""
    
    full_name = serializers.ReadOnlyField()
    primary_contact = serializers.ReadOnlyField()
    
    class Meta:
        model = Customer
        fields = [
            'id',
            'name',
            'surname',
            'full_name',
            'primary_contact',
            'identification',
            'is_active',
        ]