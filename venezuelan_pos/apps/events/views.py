from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from django.db.models import Q

from .models import Venue, Event, EventConfiguration
from .serializers import (
    VenueSerializer, EventSerializer, EventCreateSerializer,
    EventUpdateSerializer, EventListSerializer, EventConfigurationSerializer
)


class VenueViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing venues.
    Provides CRUD operations for event venues.
    """
    
    serializer_class = VenueSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['venue_type', 'is_active', 'city', 'state', 'country']
    search_fields = ['name', 'city', 'address']
    ordering_fields = ['name', 'city', 'capacity', 'created_at']
    ordering = ['name']
    
    def get_queryset(self):
        """Filter venues by tenant."""
        if self.request.user.is_admin_user:
            return Venue.objects.all()
        return Venue.objects.filter(tenant=self.request.user.tenant)
    
    def perform_create(self, serializer):
        """Set tenant when creating venue."""
        if not self.request.user.is_admin_user:
            serializer.save(tenant=self.request.user.tenant)
        else:
            # Admin users must specify tenant
            serializer.save()
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """Get only active venues."""
        queryset = self.get_queryset().filter(is_active=True)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class EventViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing events.
    Provides CRUD operations for events with configuration.
    """
    
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['event_type', 'status', 'venue', 'base_currency']
    search_fields = ['name', 'description', 'venue__name']
    ordering_fields = ['name', 'start_date', 'end_date', 'created_at']
    ordering = ['-start_date']
    
    def get_queryset(self):
        """Filter events by tenant."""
        if self.request.user.is_admin_user:
            return Event.objects.select_related('venue', 'event_configuration')
        return Event.objects.select_related('venue', 'event_configuration').filter(
            tenant=self.request.user.tenant
        )
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'create':
            return EventCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return EventUpdateSerializer
        elif self.action == 'list':
            return EventListSerializer
        return EventSerializer
    
    def perform_create(self, serializer):
        """Set tenant when creating event."""
        if not self.request.user.is_admin_user:
            serializer.save(tenant=self.request.user.tenant)
        else:
            # Admin users must specify tenant
            serializer.save()
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """Get only active events."""
        queryset = self.get_queryset().filter(status=Event.Status.ACTIVE)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        """Get upcoming events."""
        now = timezone.now()
        queryset = self.get_queryset().filter(
            start_date__gt=now,
            status=Event.Status.ACTIVE
        )
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def ongoing(self, request):
        """Get currently ongoing events."""
        now = timezone.now()
        queryset = self.get_queryset().filter(
            start_date__lte=now,
            end_date__gte=now,
            status=Event.Status.ACTIVE
        )
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def sales_active(self, request):
        """Get events with active sales."""
        now = timezone.now()
        queryset = self.get_queryset().filter(
            status=Event.Status.ACTIVE
        ).filter(
            Q(sales_start_date__isnull=True) | Q(sales_start_date__lte=now)
        ).filter(
            Q(sales_end_date__isnull=True) | Q(sales_end_date__gte=now)
        )
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activate an event."""
        event = self.get_object()
        
        # Validate event can be activated
        if event.status == Event.Status.CANCELLED:
            return Response(
                {'error': 'Cannot activate a cancelled event.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if venue is active
        if not event.venue.is_active:
            return Response(
                {'error': 'Cannot activate event with inactive venue.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        event.status = Event.Status.ACTIVE
        event.save()
        
        serializer = self.get_serializer(event)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """Deactivate an event."""
        event = self.get_object()
        
        if event.status == Event.Status.CANCELLED:
            return Response(
                {'error': 'Cannot deactivate a cancelled event.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        event.status = Event.Status.CLOSED
        event.save()
        
        serializer = self.get_serializer(event)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel an event."""
        event = self.get_object()
        
        if event.status == Event.Status.CANCELLED:
            return Response(
                {'error': 'Event is already cancelled.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        event.status = Event.Status.CANCELLED
        event.save()
        
        serializer = self.get_serializer(event)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get', 'put', 'patch'])
    def configuration(self, request, pk=None):
        """Get or update event configuration."""
        event = self.get_object()
        
        try:
            config = event.event_configuration
        except EventConfiguration.DoesNotExist:
            if request.method == 'GET':
                # Create default configuration if it doesn't exist
                config = EventConfiguration.objects.create(event=event)
            else:
                return Response(
                    {'error': 'Event configuration not found.'},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        if request.method == 'GET':
            serializer = EventConfigurationSerializer(config)
            return Response(serializer.data)
        
        elif request.method in ['PUT', 'PATCH']:
            partial = request.method == 'PATCH'
            serializer = EventConfigurationSerializer(
                config, data=request.data, partial=partial
            )
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class EventConfigurationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing event configurations.
    Provides CRUD operations for event-specific settings.
    """
    
    serializer_class = EventConfigurationSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = [
        'partial_payments_enabled', 'installment_plans_enabled',
        'flexible_payments_enabled', 'notifications_enabled',
        'digital_tickets_enabled'
    ]
    ordering_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Filter configurations by tenant."""
        if self.request.user.is_admin_user:
            return EventConfiguration.objects.select_related('event')
        return EventConfiguration.objects.select_related('event').filter(
            tenant=self.request.user.tenant
        )
    
    def perform_create(self, serializer):
        """Set tenant when creating configuration."""
        if not self.request.user.is_admin_user:
            serializer.save(tenant=self.request.user.tenant)
        else:
            # Admin users must specify tenant
            serializer.save()