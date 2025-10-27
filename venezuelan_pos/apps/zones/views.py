from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Prefetch
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import json
# Using standard DRF permissions for now
from .models import Zone, Seat, Table, TableSeat
from .serializers import (
    ZoneSerializer, ZoneListSerializer, SeatSerializer, 
    TableSerializer, TableSeatSerializer, SeatAvailabilitySerializer
)
from venezuelan_pos.apps.events.models import Event


class ZoneViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Zone management.
    Supports both general and numbered zones with automatic seat generation.
    """
    
    serializer_class = ZoneSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['event', 'zone_type', 'status']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'display_order', 'base_price', 'capacity', 'created_at']
    ordering = ['display_order', 'name']
    
    def get_queryset(self):
        """Get zones filtered by tenant."""
        return Zone.objects.select_related('event', 'event__venue').prefetch_related(
            Prefetch('seats', queryset=Seat.objects.order_by('row_number', 'seat_number')),
            Prefetch('tables', queryset=Table.objects.order_by('display_order', 'name'))
        )
    
    def get_serializer_class(self):
        """Use simplified serializer for list view."""
        if self.action == 'list':
            return ZoneListSerializer
        return ZoneSerializer
    
    def perform_create(self, serializer):
        """Set tenant when creating a zone."""
        user = self.request.user
        
        # For superusers without tenant, try to get tenant from the event
        if not user.tenant and user.is_superuser:
            event_id = serializer.validated_data.get('event')
            if event_id:
                tenant = event_id.tenant
                serializer.save(tenant=tenant)
            else:
                from rest_framework.exceptions import ValidationError
                raise ValidationError("Superuser must specify an event to determine tenant")
        elif user.tenant:
            serializer.save(tenant=user.tenant)
        else:
            from rest_framework.exceptions import ValidationError
            raise ValidationError("User must have a tenant assigned")
    
    @action(detail=True, methods=['get'])
    def seats(self, request, pk=None):
        """Get all seats for a zone."""
        zone = self.get_object()
        
        if zone.zone_type != Zone.ZoneType.NUMBERED:
            return Response(
                {'error': 'Seats are only available for numbered zones'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        seats = zone.seats.all().order_by('row_number', 'seat_number')
        serializer = SeatSerializer(seats, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def tables(self, request, pk=None):
        """Get all tables for a zone."""
        zone = self.get_object()
        
        if zone.zone_type != Zone.ZoneType.NUMBERED:
            return Response(
                {'error': 'Tables are only available for numbered zones'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        tables = zone.tables.all().order_by('display_order', 'name')
        serializer = TableSerializer(tables, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def check_availability(self, request, pk=None):
        """Check seat availability for a zone."""
        zone = self.get_object()
        serializer = SeatAvailabilitySerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        
        if zone.zone_type == Zone.ZoneType.NUMBERED:
            seat_ids = data.get('seat_ids', [])
            seats = Seat.objects.filter(id__in=seat_ids, zone=zone)
            
            availability = []
            for seat in seats:
                availability.append({
                    'seat_id': seat.id,
                    'row_number': seat.row_number,
                    'seat_number': seat.seat_number,
                    'is_available': seat.is_available,
                    'status': seat.status,
                    'price': seat.calculated_price
                })
            
            return Response({
                'zone_type': 'numbered',
                'seats': availability,
                'all_available': all(seat.is_available for seat in seats)
            })
        
        else:  # General zone
            quantity = data.get('quantity', 1)
            available = zone.available_capacity >= quantity
            
            return Response({
                'zone_type': 'general',
                'requested_quantity': quantity,
                'available_capacity': zone.available_capacity,
                'is_available': available
            })
    
    @action(detail=True, methods=['post'])
    def regenerate_seats(self, request, pk=None):
        """Regenerate seats for a numbered zone."""
        zone = self.get_object()
        
        if zone.zone_type != Zone.ZoneType.NUMBERED:
            return Response(
                {'error': 'Seat regeneration is only available for numbered zones'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if zone has any sold or reserved seats
        if zone.seats.filter(status__in=[Seat.Status.SOLD, Seat.Status.RESERVED]).exists():
            return Response(
                {'error': 'Cannot regenerate seats when some seats are sold or reserved'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        zone.generate_seats()
        
        return Response({
            'message': f'Successfully regenerated {zone.capacity} seats for zone {zone.name}',
            'seat_count': zone.seats.count()
        })


class SeatViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Seat management.
    Read-only for most operations since seats are auto-generated.
    """
    
    serializer_class = SeatSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['zone', 'status', 'row_number']
    search_fields = ['zone__name', 'zone__event__name']
    ordering_fields = ['row_number', 'seat_number', 'status']
    ordering = ['row_number', 'seat_number']
    
    def get_queryset(self):
        """Get seats filtered by tenant."""
        return Seat.objects.select_related('zone', 'zone__event')
    
    def create(self, request, *args, **kwargs):
        """Prevent manual seat creation."""
        return Response(
            {'error': 'Seats are automatically generated when creating numbered zones'},
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )
    
    def destroy(self, request, *args, **kwargs):
        """Prevent seat deletion if sold or reserved."""
        seat = self.get_object()
        
        if seat.status in [Seat.Status.SOLD, Seat.Status.RESERVED]:
            return Response(
                {'error': 'Cannot delete sold or reserved seats'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return super().destroy(request, *args, **kwargs)
    
    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """Update seat status."""
        seat = self.get_object()
        new_status = request.data.get('status')
        
        if new_status not in [choice[0] for choice in Seat.Status.choices]:
            return Response(
                {'error': 'Invalid status'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate status transitions
        if seat.status == Seat.Status.SOLD and new_status != Seat.Status.SOLD:
            return Response(
                {'error': 'Cannot change status of sold seats'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        seat.status = new_status
        seat.save()
        
        serializer = self.get_serializer(seat)
        return Response(serializer.data)


class TableViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Table management.
    Handles seat grouping for numbered zones.
    """
    
    serializer_class = TableSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['zone', 'sale_mode', 'status']
    search_fields = ['name', 'description', 'zone__name']
    ordering_fields = ['name', 'display_order', 'created_at']
    ordering = ['display_order', 'name']
    
    def get_queryset(self):
        """Get tables filtered by tenant."""
        return Table.objects.select_related('zone', 'zone__event').prefetch_related(
            'seats', 'table_seats__seat'
        )
    
    @action(detail=True, methods=['post'])
    def add_seats(self, request, pk=None):
        """Add seats to a table."""
        table = self.get_object()
        seat_ids = request.data.get('seat_ids', [])
        
        if not seat_ids:
            return Response(
                {'error': 'seat_ids is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate seats belong to the same zone
        seats = Seat.objects.filter(id__in=seat_ids, zone=table.zone)
        if seats.count() != len(seat_ids):
            return Response(
                {'error': 'Some seats do not belong to the table zone'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if seats are already in other tables
        existing_table_seats = TableSeat.objects.filter(
            seat__in=seats
        ).exclude(table=table)
        
        if existing_table_seats.exists():
            return Response(
                {'error': 'Some seats are already assigned to other tables'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Add seats to table
        table_seats = []
        for i, seat in enumerate(seats):
            table_seat, created = TableSeat.objects.get_or_create(
                table=table,
                seat=seat,
                defaults={'position': i}
            )
            if created:
                table_seats.append(table_seat)
        
        return Response({
            'message': f'Added {len(table_seats)} seats to table {table.name}',
            'added_seats': len(table_seats)
        })
    
    @action(detail=True, methods=['post'])
    def remove_seats(self, request, pk=None):
        """Remove seats from a table."""
        table = self.get_object()
        seat_ids = request.data.get('seat_ids', [])
        
        if not seat_ids:
            return Response(
                {'error': 'seat_ids is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Remove seats from table
        removed_count = TableSeat.objects.filter(
            table=table,
            seat_id__in=seat_ids
        ).delete()[0]
        
        return Response({
            'message': f'Removed {removed_count} seats from table {table.name}',
            'removed_seats': removed_count
        })
    
    @action(detail=True, methods=['get'])
    def availability(self, request, pk=None):
        """Check table availability."""
        table = self.get_object()
        
        return Response({
            'table_id': table.id,
            'name': table.name,
            'sale_mode': table.sale_mode,
            'seat_count': table.seat_count,
            'available_seats': table.available_seats.count(),
            'sold_seats': table.sold_seats.count(),
            'is_available': table.is_available,
            'is_sold_out': table.is_sold_out,
            'total_price': table.total_price
        })


class TableSeatViewSet(viewsets.ModelViewSet):
    """
    ViewSet for TableSeat management.
    Handles the many-to-many relationship between tables and seats.
    """
    
    serializer_class = TableSeatSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['table', 'seat']
    ordering_fields = ['position']
    ordering = ['position']
    
    def get_queryset(self):
        """Get table seats filtered by tenant."""
        return TableSeat.objects.select_related(
            'table', 'seat', 'table__zone', 'seat__zone'
        )


# Web Views for Zone Map Editor

@login_required
def zone_map_editor(request, event_id):
    """
    Zone map editor view - allows visual arrangement of zones on a venue map.
    """
    user = request.user
    
    # Handle tenant filtering for different user types
    if user.tenant:
        # Regular user with tenant
        event = get_object_or_404(Event, id=event_id, tenant=user.tenant)
    elif user.is_superuser:
        # Superuser without tenant - can access any event
        event = get_object_or_404(Event, id=event_id)
    else:
        # User without tenant and not superuser - no access
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied("User must have a tenant assigned or be a superuser")
    
    zones = Zone.objects.filter(event=event).order_by('display_order', 'name')
    
    context = {
        'event': event,
        'zones': zones,
        'venue': event.venue,
    }
    
    return render(request, 'zones/zone_map_editor.html', context)


@csrf_exempt
@require_http_methods(["POST"])
@login_required
def update_zone_position(request, zone_id):
    """
    Update zone position on the map via AJAX.
    """
    try:
        user = request.user
        
        # Handle tenant filtering for different user types
        if user.tenant:
            zone = get_object_or_404(Zone, id=zone_id, tenant=user.tenant)
        elif user.is_superuser:
            zone = get_object_or_404(Zone, id=zone_id)
        else:
            return JsonResponse({
                'success': False,
                'error': 'User must have a tenant assigned or be a superuser'
            }, status=403)
        
        data = json.loads(request.body)
        
        # Update position fields
        zone.map_x = data.get('x')
        zone.map_y = data.get('y')
        zone.map_width = data.get('width', zone.map_width)
        zone.map_height = data.get('height', zone.map_height)
        zone.map_rotation = data.get('rotation', zone.map_rotation)
        
        zone.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Updated position for zone {zone.name}'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@csrf_exempt
@require_http_methods(["POST"])
@login_required
def save_zone_layout(request, event_id):
    """
    Save the entire zone layout for an event.
    """
    try:
        user = request.user
        
        # Handle tenant filtering for different user types
        if user.tenant:
            event = get_object_or_404(Event, id=event_id, tenant=user.tenant)
        elif user.is_superuser:
            event = get_object_or_404(Event, id=event_id)
        else:
            return JsonResponse({
                'success': False,
                'error': 'User must have a tenant assigned or be a superuser'
            }, status=403)
        
        data = json.loads(request.body)
        zones_data = data.get('zones', [])
        updated_count = 0
        
        for zone_data in zones_data:
            zone_id = zone_data.get('id')
            if zone_id:
                try:
                    # Filter zones by event and tenant context
                    if user.tenant:
                        zone = Zone.objects.get(id=zone_id, event=event, tenant=user.tenant)
                    else:
                        zone = Zone.objects.get(id=zone_id, event=event)
                    
                    zone.map_x = zone_data.get('x')
                    zone.map_y = zone_data.get('y')
                    zone.map_width = zone_data.get('width', zone.map_width)
                    zone.map_height = zone_data.get('height', zone.map_height)
                    zone.map_rotation = zone_data.get('rotation', zone.map_rotation)
                    zone.save()
                    updated_count += 1
                except Zone.DoesNotExist:
                    continue
        
        return JsonResponse({
            'success': True,
            'message': f'Updated layout for {updated_count} zones',
            'updated_count': updated_count
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)