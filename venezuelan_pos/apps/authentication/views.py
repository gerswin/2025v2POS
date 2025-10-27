from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle
from django.contrib.auth import logout
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from .serializers import (
    CustomTokenObtainPairSerializer,
    UserRegistrationSerializer,
    UserProfileSerializer,
    PasswordChangeSerializer,
    TenantSerializer
)
from venezuelan_pos.apps.tenants.models import User, Tenant


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Custom JWT token obtain view with rate limiting and tenant information.
    """
    serializer_class = CustomTokenObtainPairSerializer
    throttle_classes = [AnonRateThrottle]
    
    @method_decorator(never_cache)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)


class CustomTokenRefreshView(TokenRefreshView):
    """
    Custom JWT token refresh view with rate limiting.
    """
    throttle_classes = [UserRateThrottle]
    
    @method_decorator(never_cache)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)


class UserRegistrationView(APIView):
    """
    User registration endpoint.
    """
    permission_classes = [permissions.AllowAny]
    throttle_classes = [AnonRateThrottle]
    
    def post(self, request):
        """Register a new user."""
        serializer = UserRegistrationSerializer(data=request.data)
        
        if serializer.is_valid():
            user = serializer.save()
            
            # Return user profile data
            profile_serializer = UserProfileSerializer(user)
            
            return Response({
                'message': 'User registered successfully',
                'user': profile_serializer.data
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserProfileView(APIView):
    """
    User profile management endpoint.
    """
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [UserRateThrottle]
    
    def get(self, request):
        """Get current user profile."""
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data)
    
    def put(self, request):
        """Update user profile."""
        serializer = UserProfileSerializer(
            request.user, 
            data=request.data, 
            partial=True
        )
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PasswordChangeView(APIView):
    """
    Password change endpoint.
    """
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [UserRateThrottle]
    
    def post(self, request):
        """Change user password."""
        serializer = PasswordChangeSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            serializer.save()
            return Response({
                'message': 'Password changed successfully'
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(APIView):
    """
    Logout endpoint that clears session data.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        """Logout user and clear session."""
        logout(request)
        return Response({
            'message': 'Logged out successfully'
        })


class TenantListView(APIView):
    """
    List available tenants (for admin users or registration).
    """
    permission_classes = [permissions.AllowAny]
    throttle_classes = [AnonRateThrottle]
    
    def get(self, request):
        """Get list of active tenants."""
        tenants = Tenant.objects.filter(is_active=True)
        serializer = TenantSerializer(tenants, many=True)
        return Response(serializer.data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def user_permissions(request):
    """
    Get current user's permissions and role information.
    """
    user = request.user
    
    permissions_data = {
        'user_id': str(user.id),
        'username': user.username,
        'role': user.role,
        'is_admin_user': user.is_admin_user,
        'is_tenant_admin': user.is_tenant_admin,
        'is_event_operator': user.is_event_operator,
        'tenant': {
            'id': str(user.tenant.id),
            'name': user.tenant.name,
            'slug': user.tenant.slug,
        } if user.tenant else None,
        'permissions': {
            'can_manage_tenants': user.is_admin_user,
            'can_manage_users': user.is_admin_user or user.is_tenant_admin,
            'can_manage_events': user.is_admin_user or user.is_tenant_admin,
            'can_operate_pos': True,  # All authenticated users can operate POS
            'can_view_reports': user.is_admin_user or user.is_tenant_admin,
        }
    }
    
    return Response(permissions_data)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def health_check(request):
    """
    Health check endpoint for authentication service.
    """
    return Response({
        'status': 'healthy',
        'service': 'authentication',
        'timestamp': request.META.get('HTTP_DATE')
    })