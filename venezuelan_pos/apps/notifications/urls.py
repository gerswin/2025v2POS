"""
URL configuration for notifications app.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    NotificationTemplateViewSet,
    NotificationLogViewSet,
    NotificationPreferenceViewSet,
    NotificationViewSet
)

app_name = 'notifications'

# API Router
router = DefaultRouter()
router.register('templates', NotificationTemplateViewSet, basename='template')
router.register('logs', NotificationLogViewSet, basename='log')
router.register('preferences', NotificationPreferenceViewSet, basename='preference')
router.register('send', NotificationViewSet, basename='send')

urlpatterns = [
    path('api/', include(router.urls)),
]