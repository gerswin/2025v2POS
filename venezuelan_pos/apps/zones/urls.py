from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ZoneViewSet, SeatViewSet, TableViewSet, TableSeatViewSet,
    zone_map_editor, update_zone_position, save_zone_layout
)

app_name = 'zones'

# Create router for API endpoints
router = DefaultRouter()
router.register(r'zones', ZoneViewSet, basename='zone')
router.register(r'seats', SeatViewSet, basename='seat')
router.register(r'tables', TableViewSet, basename='table')
router.register(r'table-seats', TableSeatViewSet, basename='tableseat')

urlpatterns = [
    # API endpoints
    path('api/', include(router.urls)),
    
    # Web views for zone map editor
    path('events/<uuid:event_id>/map-editor/', zone_map_editor, name='zone_map_editor'),
    path('zones/<uuid:zone_id>/update-position/', update_zone_position, name='update_zone_position'),
    path('events/<uuid:event_id>/save-layout/', save_zone_layout, name='save_zone_layout'),
]