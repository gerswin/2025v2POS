from django.urls import path
from .views import (
    CustomTokenObtainPairView,
    CustomTokenRefreshView,
    UserRegistrationView,
    UserProfileView,
    PasswordChangeView,
    LogoutView,
    TenantListView,
    user_permissions,
    health_check
)

app_name = 'authentication'

urlpatterns = [
    # JWT Authentication
    path('login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('refresh/', CustomTokenRefreshView.as_view(), name='token_refresh'),
    path('logout/', LogoutView.as_view(), name='logout'),
    
    # User Management
    path('register/', UserRegistrationView.as_view(), name='register'),
    path('profile/', UserProfileView.as_view(), name='profile'),
    path('change-password/', PasswordChangeView.as_view(), name='change_password'),
    path('permissions/', user_permissions, name='permissions'),
    
    # Tenant Information
    path('tenants/', TenantListView.as_view(), name='tenant_list'),
    
    # Health Check
    path('health/', health_check, name='health_check'),
]