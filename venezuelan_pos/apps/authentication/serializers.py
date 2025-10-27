from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from venezuelan_pos.apps.tenants.models import User, Tenant


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Custom JWT token serializer that includes user and tenant information.
    """
    
    def validate(self, attrs):
        """Validate credentials and add custom claims."""
        data = super().validate(attrs)
        
        # Add custom user information to the response
        data.update({
            'user': {
                'id': str(self.user.id),
                'username': self.user.username,
                'email': self.user.email,
                'first_name': self.user.first_name,
                'last_name': self.user.last_name,
                'role': self.user.role,
                'tenant': {
                    'id': str(self.user.tenant.id),
                    'name': self.user.tenant.name,
                    'slug': self.user.tenant.slug,
                } if self.user.tenant else None,
            }
        })
        
        return data
    
    @classmethod
    def get_token(cls, user):
        """Add custom claims to JWT token."""
        token = super().get_token(user)
        
        # Add custom claims
        token['user_id'] = str(user.id)
        token['username'] = user.username
        token['role'] = user.role
        
        if user.tenant:
            token['tenant_id'] = str(user.tenant.id)
            token['tenant_slug'] = user.tenant.slug
        
        return token


class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration.
    """
    
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)
    tenant_slug = serializers.CharField(write_only=True, required=False)
    
    class Meta:
        model = User
        fields = [
            'username', 'email', 'first_name', 'last_name', 
            'password', 'password_confirm', 'phone', 'tenant_slug'
        ]
    
    def validate(self, attrs):
        """Validate password confirmation and tenant."""
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Passwords don't match")
        
        # Validate tenant if provided
        tenant_slug = attrs.get('tenant_slug')
        if tenant_slug:
            try:
                tenant = Tenant.objects.get(slug=tenant_slug, is_active=True)
                attrs['tenant'] = tenant
            except Tenant.DoesNotExist:
                raise serializers.ValidationError("Invalid tenant")
        
        return attrs
    
    def create(self, validated_data):
        """Create new user with validated data."""
        validated_data.pop('password_confirm')
        tenant_slug = validated_data.pop('tenant_slug', None)
        tenant = validated_data.pop('tenant', None)
        
        user = User.objects.create_user(**validated_data)
        
        if tenant:
            user.tenant = tenant
            user.save()
        
        return user


class UserProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for user profile information.
    """
    
    tenant = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'phone', 'role', 'tenant', 'is_active', 'date_joined'
        ]
        read_only_fields = ['id', 'username', 'role', 'tenant', 'date_joined']
    
    def get_tenant(self, obj):
        """Get tenant information."""
        if obj.tenant:
            return {
                'id': str(obj.tenant.id),
                'name': obj.tenant.name,
                'slug': obj.tenant.slug,
            }
        return None


class PasswordChangeSerializer(serializers.Serializer):
    """
    Serializer for password change.
    """
    
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, validators=[validate_password])
    new_password_confirm = serializers.CharField(required=True)
    
    def validate(self, attrs):
        """Validate old password and new password confirmation."""
        user = self.context['request'].user
        
        if not user.check_password(attrs['old_password']):
            raise serializers.ValidationError("Old password is incorrect")
        
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError("New passwords don't match")
        
        return attrs
    
    def save(self):
        """Change user password."""
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user


class TenantSerializer(serializers.ModelSerializer):
    """
    Serializer for tenant information.
    """
    
    class Meta:
        model = Tenant
        fields = ['id', 'name', 'slug', 'contact_email', 'contact_phone']
        read_only_fields = ['id']