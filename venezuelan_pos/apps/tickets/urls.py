from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    DigitalTicketViewSet,
    TicketTemplateViewSet,
    TicketValidationLogViewSet
)

# Create router for API endpoints
router = DefaultRouter()
router.register(r'tickets', DigitalTicketViewSet, basename='digitalticket')
router.register(r'templates', TicketTemplateViewSet, basename='tickettemplate')
router.register(r'validation-logs', TicketValidationLogViewSet, basename='ticketvalidationlog')

app_name = 'tickets'

urlpatterns = [
    # API endpoints
    path('api/', include(router.urls)),
]