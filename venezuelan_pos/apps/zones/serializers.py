from rest_framework import serializers
from django.db import transaction
from .models import Zone, Seat, Table, TableSeat


class SeatSerializer(serializers.ModelSerializer):
    """Serializer for Seat model."""
    
    calculated_price = serializers.ReadOnlyField()
    seat_label = serializers.ReadOnlyField()
    is_available = serializers.ReadOnlyField()
    
    class Meta:
        model = Seat
        fields = [
            'id', 'zone', 'row_number', 'seat_number', 'price_modifier',
            'status', 'calculated_price', 'seat_label', 'is_available',
            'configuration', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate(self, data):
        """Validate seat data."""
        zone = data.get('zone')
        row_number = data.get('row_number')
        seat_number = data.get('seat_number')
        
        if zone and zone.zone_type != Zone.ZoneType.NUMBERED:
            raise serializers.ValidationError({
                'zone': 'Seats can only be created for numbered zones'
            })
        
        if zone and row_number and zone.rows and row_number > zone.rows:
            raise serializers.ValidationError({
                'row_number': f'Row number cannot exceed zone rows ({zone.rows})'
            })
        
        if zone and seat_number and zone.seats_per_row and seat_number > zone.seats_per_row:
            raise serializers.ValidationError({
                'seat_number': f'Seat number cannot exceed seats per row ({zone.seats_per_row})'
            })
        
        return data


class TableSeatSerializer(serializers.ModelSerializer):
    """Serializer for TableSeat model."""
    
    seat_details = SeatSerializer(source='seat', read_only=True)
    
    class Meta:
        model = TableSeat
        fields = [
            'id', 'table', 'seat', 'position', 'seat_details',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate(self, data):
        """Validate table seat relationship."""
        table = data.get('table')
        seat = data.get('seat')
        
        if table and seat and table.zone != seat.zone:
            raise serializers.ValidationError({
                'seat': 'Seat must belong to the same zone as the table'
            })
        
        return data


class TableSerializer(serializers.ModelSerializer):
    """Serializer for Table model."""
    
    seat_count = serializers.ReadOnlyField()
    available_seats_count = serializers.SerializerMethodField()
    sold_seats_count = serializers.SerializerMethodField()
    is_available = serializers.ReadOnlyField()
    is_sold_out = serializers.ReadOnlyField()
    total_price = serializers.ReadOnlyField()
    seats = SeatSerializer(many=True, read_only=True)
    table_seats = TableSeatSerializer(many=True, read_only=True)
    
    class Meta:
        model = Table
        fields = [
            'id', 'zone', 'name', 'description', 'sale_mode', 'status',
            'display_order', 'seat_count', 'available_seats_count', 
            'sold_seats_count', 'is_available', 'is_sold_out', 'total_price',
            'seats', 'table_seats', 'configuration', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_available_seats_count(self, obj):
        """Get available seats count."""
        return obj.available_seats.count()
    
    def get_sold_seats_count(self, obj):
        """Get sold seats count."""
        return obj.sold_seats.count()
    
    def validate(self, data):
        """Validate table data."""
        zone = data.get('zone')
        
        if zone and zone.zone_type != Zone.ZoneType.NUMBERED:
            raise serializers.ValidationError({
                'zone': 'Tables can only be created for numbered zones'
            })
        
        return data


class ZoneSerializer(serializers.ModelSerializer):
    """Serializer for Zone model."""
    
    available_capacity = serializers.ReadOnlyField()
    sold_capacity = serializers.ReadOnlyField()
    is_sold_out = serializers.ReadOnlyField()
    seats = SeatSerializer(many=True, read_only=True)
    tables = TableSerializer(many=True, read_only=True)
    
    class Meta:
        model = Zone
        fields = [
            'id', 'event', 'name', 'description', 'zone_type', 'capacity',
            'rows', 'seats_per_row', 'row_configuration', 'base_price', 'status', 'display_order',
            'map_x', 'map_y', 'map_width', 'map_height', 'map_rotation', 'map_color',
            'available_capacity', 'sold_capacity', 'is_sold_out',
            'seats', 'tables', 'configuration', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def to_internal_value(self, data):
        """Pre-process data before validation."""
        # Para zonas numeradas, calcular capacity automáticamente si no se proporciona
        if data.get('zone_type') == 'numbered':
            rows = data.get('rows')
            row_configuration = data.get('row_configuration')
            seats_per_row = data.get('seats_per_row')
            
            if rows and not data.get('capacity'):
                data = data.copy()  # No modificar el original
                
                if row_configuration:
                    # Calcular capacity basado en configuración por fila
                    total_capacity = 0
                    for row_num in range(1, int(rows) + 1):
                        row_seats = row_configuration.get(str(row_num))
                        if row_seats is None and seats_per_row:
                            row_seats = int(seats_per_row)
                        if row_seats:
                            total_capacity += int(row_seats)
                    data['capacity'] = total_capacity
                elif seats_per_row:
                    # Calcular capacity estándar
                    data['capacity'] = int(rows) * int(seats_per_row)
        
        return super().to_internal_value(data)
    
    def validate(self, data):
        """Validate zone data."""
        zone_type = data.get('zone_type')
        capacity = data.get('capacity')
        rows = data.get('rows')
        seats_per_row = data.get('seats_per_row')
        base_price = data.get('base_price')
        
        if base_price is not None and base_price < 0:
            raise serializers.ValidationError({
                'base_price': 'Base price cannot be negative'
            })
        
        if zone_type == Zone.ZoneType.NUMBERED:
            if not rows or rows <= 0:
                raise serializers.ValidationError({
                    'rows': 'Numbered zones must have at least 1 row'
                })
            
            if not seats_per_row or seats_per_row <= 0:
                raise serializers.ValidationError({
                    'seats_per_row': 'Numbered zones must have at least 1 seat per row'
                })
            
            # Calcular automáticamente la capacidad para zonas numeradas
            calculated_capacity = rows * seats_per_row
            data['capacity'] = calculated_capacity
        
        elif zone_type == Zone.ZoneType.GENERAL:
            if capacity is None or capacity <= 0:
                raise serializers.ValidationError({
                    'capacity': 'General zones must have capacity greater than 0'
                })
        
        return data
    
    @transaction.atomic
    def create(self, validated_data):
        """Create zone and generate seats if numbered."""
        # The tenant is passed from the viewset's perform_create method
        zone = Zone.objects.create(**validated_data)
        
        # Seats are automatically generated in the model's save method
        return zone
    
    @transaction.atomic
    def update(self, instance, validated_data):
        """Update zone and regenerate seats if needed."""
        old_zone_type = instance.zone_type
        old_rows = instance.rows
        old_seats_per_row = instance.seats_per_row
        
        zone = super().update(instance, validated_data)
        
        # Regenerate seats if numbered zone configuration changed
        if (zone.zone_type == Zone.ZoneType.NUMBERED and 
            (old_zone_type != zone.zone_type or 
             old_rows != zone.rows or 
             old_seats_per_row != zone.seats_per_row)):
            zone.generate_seats()
        
        return zone


class ZoneListSerializer(serializers.ModelSerializer):
    """Simplified serializer for zone lists."""
    
    available_capacity = serializers.ReadOnlyField()
    sold_capacity = serializers.ReadOnlyField()
    is_sold_out = serializers.ReadOnlyField()
    
    class Meta:
        model = Zone
        fields = [
            'id', 'event', 'name', 'description', 'zone_type', 'capacity',
            'rows', 'seats_per_row', 'base_price', 'status', 'display_order',
            'map_color',
            'available_capacity', 'sold_capacity', 'is_sold_out',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class SeatAvailabilitySerializer(serializers.Serializer):
    """Serializer for seat availability checking."""
    
    zone_id = serializers.UUIDField()
    seat_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        help_text="List of seat IDs to check (for numbered zones)"
    )
    quantity = serializers.IntegerField(
        min_value=1,
        required=False,
        help_text="Number of tickets needed (for general zones)"
    )
    
    def validate(self, data):
        """Validate availability check request."""
        zone_id = data.get('zone_id')
        seat_ids = data.get('seat_ids')
        quantity = data.get('quantity')
        
        try:
            zone = Zone.objects.get(id=zone_id)
        except Zone.DoesNotExist:
            raise serializers.ValidationError({
                'zone_id': 'Zone not found'
            })
        
        if zone.zone_type == Zone.ZoneType.NUMBERED:
            if not seat_ids:
                raise serializers.ValidationError({
                    'seat_ids': 'Seat IDs are required for numbered zones'
                })
            
            # Validate that all seats belong to the zone
            seats = Seat.objects.filter(id__in=seat_ids, zone=zone)
            if seats.count() != len(seat_ids):
                raise serializers.ValidationError({
                    'seat_ids': 'Some seats do not belong to the specified zone'
                })
        
        elif zone.zone_type == Zone.ZoneType.GENERAL:
            if not quantity:
                raise serializers.ValidationError({
                    'quantity': 'Quantity is required for general zones'
                })
            
            if quantity > zone.available_capacity:
                raise serializers.ValidationError({
                    'quantity': f'Only {zone.available_capacity} tickets available'
                })
        
        data['zone'] = zone
        return data
