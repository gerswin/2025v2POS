from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import VenueViewSet, EventViewSet, EventConfigurationViewSet

# Create router and register viewsets
router = DefaultRouter()
router.register(r'venues', VenueViewSet, basename='venue')
router.register(r'events', EventViewSet, basename='event')
router.register(r'configurations', EventConfigurationViewSet, basename='eventconfiguration')

app_name = 'events_api'

urlpatterns = [
    path('', include(router.urls)),
]