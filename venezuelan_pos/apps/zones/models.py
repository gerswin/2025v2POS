import uuid
from decimal import Decimal
from django.db import models, transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from venezuelan_pos.apps.tenants.models import TenantAwareModel
from venezuelan_pos.apps.events.models import Event


class Zone(TenantAwareModel):
    """
    Zone model supporting both general and numbered zones.
    Defines areas within an event with specific capacity and pricing rules.
    """
    
    class ZoneType(models.TextChoices):
        GENERAL = 'general', 'General Zone'
        NUMBERED = 'numbered', 'Numbered Zone'
    
    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        INACTIVE = 'inactive', 'Inactive'
        SOLD_OUT = 'sold_out', 'Sold Out'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name='zones',
        help_text="Event this zone belongs to"
    )
    
    # Zone identification
    name = models.CharField(max_length=255, help_text="Zone name")
    description = models.TextField(blank=True, help_text="Zone description")
    zone_type = models.CharField(
        max_length=10,
        choices=ZoneType.choices,
        default=ZoneType.GENERAL,
        help_text="Type of zone (general or numbered)"
    )
    
    # Capacity configuration
    capacity = models.PositiveIntegerField(
        help_text="Maximum capacity for this zone"
    )
    
    # Numbered zone configuration
    rows = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Number of rows (for numbered zones only)"
    )
    seats_per_row = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Default number of seats per row (for numbered zones only)"
    )
    
    # Variable seats per row configuration
    row_configuration = models.JSONField(
        default=dict,
        blank=True,
        help_text="Custom seats per row configuration: {'1': 10, '2': 9, '3': 8, ...}"
    )
    
    # Pricing
    base_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Base price for tickets in this zone"
    )
    
    # Status and configuration
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.ACTIVE,
        help_text="Current zone status"
    )
    
    # Display order
    display_order = models.PositiveIntegerField(
        default=0,
        help_text="Order for displaying zones"
    )
    
    # Map position (for visual zone editor)
    map_x = models.FloatField(
        null=True,
        blank=True,
        help_text="X coordinate on venue map (pixels or percentage)"
    )
    map_y = models.FloatField(
        null=True,
        blank=True,
        help_text="Y coordinate on venue map (pixels or percentage)"
    )
    map_width = models.FloatField(
        null=True,
        blank=True,
        default=100.0,
        help_text="Width of zone on venue map (pixels or percentage)"
    )
    map_height = models.FloatField(
        null=True,
        blank=True,
        default=80.0,
        help_text="Height of zone on venue map (pixels or percentage)"
    )
    map_rotation = models.FloatField(
        null=True,
        blank=True,
        default=0.0,
        help_text="Rotation angle in degrees"
    )
    
    # Configuration
    configuration = models.JSONField(
        default=dict,
        blank=True,
        help_text="Zone-specific configuration settings"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'zones'
        verbose_name = 'Zone'
        verbose_name_plural = 'Zones'
        ordering = ['display_order', 'name']
        unique_together = ['event', 'name']
    
    def __str__(self):
        return f"{self.event.name} - {self.name}"
    
    def clean(self):
        """Validate zone data."""
        super().clean()
        
        if not self.name.strip():
            raise ValidationError({'name': 'Zone name cannot be empty'})
        
        if self.base_price < 0:
            raise ValidationError({'base_price': 'Base price cannot be negative'})
        
        if self.zone_type == self.ZoneType.NUMBERED:
            if not self.rows or self.rows <= 0:
                raise ValidationError({'rows': 'Numbered zones must have at least 1 row'})
            
            # Calculate capacity based on row configuration or default seats_per_row
            if self.row_configuration:
                # Validate row configuration
                try:
                    calculated_capacity = 0
                    for row_num in range(1, self.rows + 1):
                        row_seats = self.row_configuration.get(str(row_num))
                        if row_seats is None:
                            if not self.seats_per_row or self.seats_per_row <= 0:
                                raise ValidationError({
                                    'row_configuration': f'Row {row_num} not configured and no default seats_per_row set'
                                })
                            row_seats = self.seats_per_row
                        
                        if not isinstance(row_seats, int) or row_seats <= 0:
                            raise ValidationError({
                                'row_configuration': f'Row {row_num} must have at least 1 seat'
                            })
                        
                        calculated_capacity += row_seats
                    
                    if self.capacity != calculated_capacity:
                        raise ValidationError({
                            'capacity': f'Capacity must equal total seats from row configuration ({calculated_capacity})'
                        })
                        
                except (ValueError, TypeError) as e:
                    raise ValidationError({
                        'row_configuration': 'Invalid row configuration format. Use {"1": 10, "2": 9, ...}'
                    })
            else:
                # Standard validation for uniform rows
                if not self.seats_per_row or self.seats_per_row <= 0:
                    raise ValidationError({'seats_per_row': 'Numbered zones must have at least 1 seat per row'})
                
                calculated_capacity = self.rows * self.seats_per_row
                if self.capacity != calculated_capacity:
                    raise ValidationError({
                        'capacity': f'Capacity must equal rows × seats per row ({calculated_capacity}) for numbered zones'
                    })
        
        elif self.zone_type == self.ZoneType.GENERAL:
            if self.capacity <= 0:
                raise ValidationError({'capacity': 'General zones must have capacity greater than 0'})
    
    def save(self, *args, **kwargs):
        """Override save to generate seats for numbered zones."""
        # Check if this is a new instance by trying to get it from the database
        is_new = not Zone.objects.filter(pk=self.pk).exists() if self.pk else True
        is_numbered_zone = self.zone_type == self.ZoneType.NUMBERED
        
        # Call clean to validate
        self.clean()
        
        # Save the zone first
        super().save(*args, **kwargs)
        
        # Generate seats for new numbered zones
        if is_new and is_numbered_zone:
            self.generate_seats()
    
    @transaction.atomic
    def generate_seats(self):
        """Generate seats for numbered zones with support for variable seats per row."""
        if self.zone_type != self.ZoneType.NUMBERED:
            return
        
        if not self.rows:
            return
        
        # Clear existing seats
        self.seats.all().delete()
        
        # Generate new seats
        seats_to_create = []
        for row in range(1, self.rows + 1):
            # Get seats for this row from configuration or default
            if self.row_configuration and str(row) in self.row_configuration:
                seats_in_row = self.row_configuration[str(row)]
            elif self.seats_per_row:
                seats_in_row = self.seats_per_row
            else:
                continue  # Skip this row if no configuration
            
            for seat_num in range(1, seats_in_row + 1):
                seat = Seat(
                    tenant=self.tenant,
                    zone=self,
                    row_number=row,
                    seat_number=seat_num,
                    status=Seat.Status.AVAILABLE
                )
                seats_to_create.append(seat)
        
        # Bulk create seats for performance
        Seat.objects.bulk_create(seats_to_create)
    
    @property
    def available_capacity(self):
        """Get available capacity for this zone."""
        if self.zone_type == self.ZoneType.NUMBERED:
            return self.seats.filter(status=Seat.Status.AVAILABLE).count()
        else:
            # For general zones, we need to calculate based on sold tickets
            # This would be implemented when we have the sales models
            return self.capacity
    
    @property
    def sold_capacity(self):
        """Get sold capacity for this zone."""
        if self.zone_type == self.ZoneType.NUMBERED:
            return self.seats.filter(status__in=[Seat.Status.SOLD, Seat.Status.RESERVED]).count()
        else:
            # For general zones, we need to calculate based on sold tickets
            # This would be implemented when we have the sales models
            return 0
    
    @property
    def is_sold_out(self):
        """Check if zone is sold out."""
        return self.available_capacity == 0
    
    def get_seats_for_row(self, row_number):
        """Get the number of seats for a specific row."""
        if self.zone_type != self.ZoneType.NUMBERED:
            return 0
        
        if self.row_configuration and str(row_number) in self.row_configuration:
            return self.row_configuration[str(row_number)]
        elif self.seats_per_row:
            return self.seats_per_row
        else:
            return 0
    
    def get_row_configuration_display(self):
        """Get a human-readable display of the row configuration."""
        if not self.row_configuration:
            return f"{self.rows} rows × {self.seats_per_row} seats each"
        
        config_parts = []
        for row in range(1, self.rows + 1):
            seats = self.get_seats_for_row(row)
            config_parts.append(f"Row {row}: {seats} seats")
        
        return " | ".join(config_parts)


class Seat(TenantAwareModel):
    """
    Seat model for numbered zones with row and seat number fields.
    """
    
    class Status(models.TextChoices):
        AVAILABLE = 'available', 'Available'
        RESERVED = 'reserved', 'Reserved'
        SOLD = 'sold', 'Sold'
        BLOCKED = 'blocked', 'Blocked'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    zone = models.ForeignKey(
        Zone,
        on_delete=models.CASCADE,
        related_name='seats',
        help_text="Zone this seat belongs to"
    )
    
    # Seat identification
    row_number = models.PositiveIntegerField(help_text="Row number")
    seat_number = models.PositiveIntegerField(help_text="Seat number within the row")
    
    # Pricing modifier
    price_modifier = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Price modifier percentage (e.g., 10.00 for 10% increase)"
    )
    
    # Status
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.AVAILABLE,
        help_text="Current seat status"
    )
    
    # Configuration
    configuration = models.JSONField(
        default=dict,
        blank=True,
        help_text="Seat-specific configuration settings"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'seats'
        verbose_name = 'Seat'
        verbose_name_plural = 'Seats'
        ordering = ['row_number', 'seat_number']
        unique_together = ['zone', 'row_number', 'seat_number']
    
    def __str__(self):
        return f"{self.zone.name} - Row {self.row_number}, Seat {self.seat_number}"
    
    def clean(self):
        """Validate seat data."""
        super().clean()
        
        if self.zone and self.zone.zone_type != Zone.ZoneType.NUMBERED:
            raise ValidationError({'zone': 'Seats can only be created for numbered zones'})
        
        if self.row_number <= 0:
            raise ValidationError({'row_number': 'Row number must be positive'})
        
        if self.seat_number <= 0:
            raise ValidationError({'seat_number': 'Seat number must be positive'})
        
        if self.zone:
            if self.zone.rows and self.row_number > self.zone.rows:
                raise ValidationError({
                    'row_number': f'Row number cannot exceed zone rows ({self.zone.rows})'
                })
            
            if self.zone.seats_per_row and self.seat_number > self.zone.seats_per_row:
                raise ValidationError({
                    'seat_number': f'Seat number cannot exceed seats per row ({self.zone.seats_per_row})'
                })
    
    @property
    def calculated_price(self):
        """Calculate the final price for this seat."""
        base_price = self.zone.base_price
        modifier = self.price_modifier / 100  # Convert percentage to decimal
        return base_price * (1 + modifier)
    
    @property
    def seat_label(self):
        """Get a human-readable seat label."""
        return f"Row {self.row_number}, Seat {self.seat_number}"
    
    @property
    def is_available(self):
        """Check if seat is available for purchase."""
        return self.status == self.Status.AVAILABLE


class Table(TenantAwareModel):
    """
    Table model for seat grouping.
    Groups numbered seats into tables for sale as units.
    """
    
    class SaleMode(models.TextChoices):
        COMPLETE_ONLY = 'complete_only', 'Complete Table Only'
        INDIVIDUAL_ALLOWED = 'individual_allowed', 'Individual Seats Allowed'
    
    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        INACTIVE = 'inactive', 'Inactive'
        SOLD_OUT = 'sold_out', 'Sold Out'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    zone = models.ForeignKey(
        Zone,
        on_delete=models.CASCADE,
        related_name='tables',
        help_text="Zone this table belongs to"
    )
    
    # Table identification
    name = models.CharField(max_length=255, help_text="Table name or number")
    description = models.TextField(blank=True, help_text="Table description")
    
    # Table configuration
    sale_mode = models.CharField(
        max_length=20,
        choices=SaleMode.choices,
        default=SaleMode.INDIVIDUAL_ALLOWED,
        help_text="How this table can be sold"
    )
    
    # Status
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.ACTIVE,
        help_text="Current table status"
    )
    
    # Display order
    display_order = models.PositiveIntegerField(
        default=0,
        help_text="Order for displaying tables"
    )
    
    # Configuration
    configuration = models.JSONField(
        default=dict,
        blank=True,
        help_text="Table-specific configuration settings"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'tables'
        verbose_name = 'Table'
        verbose_name_plural = 'Tables'
        ordering = ['display_order', 'name']
        unique_together = ['zone', 'name']
    
    def __str__(self):
        return f"{self.zone.name} - {self.name}"
    
    def clean(self):
        """Validate table data."""
        super().clean()
        
        if not self.name.strip():
            raise ValidationError({'name': 'Table name cannot be empty'})
        
        if self.zone and self.zone.zone_type != Zone.ZoneType.NUMBERED:
            raise ValidationError({'zone': 'Tables can only be created for numbered zones'})
    
    @property
    def seat_count(self):
        """Get the number of seats in this table."""
        return self.seats.count()
    
    @property
    def available_seats(self):
        """Get available seats in this table."""
        return self.seats.filter(status=Seat.Status.AVAILABLE)
    
    @property
    def sold_seats(self):
        """Get sold seats in this table."""
        return self.seats.filter(status__in=[Seat.Status.SOLD, Seat.Status.RESERVED])
    
    @property
    def is_available(self):
        """Check if table is available for purchase."""
        if self.sale_mode == self.SaleMode.COMPLETE_ONLY:
            # All seats must be available
            return self.available_seats.count() == self.seat_count
        else:
            # At least one seat must be available
            return self.available_seats.exists()
    
    @property
    def is_sold_out(self):
        """Check if table is sold out."""
        return self.available_seats.count() == 0
    
    @property
    def total_price(self):
        """Calculate total price for all seats in the table."""
        return sum(seat.calculated_price for seat in self.seats.all())


class TableSeat(TenantAwareModel):
    """
    Many-to-many relationship between Tables and Seats.
    Allows seats to be grouped into tables.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    table = models.ForeignKey(
        Table,
        on_delete=models.CASCADE,
        related_name='table_seats',
        help_text="Table this relationship belongs to"
    )
    seat = models.ForeignKey(
        Seat,
        on_delete=models.CASCADE,
        related_name='table_memberships',
        help_text="Seat that belongs to the table"
    )
    
    # Position within table
    position = models.PositiveIntegerField(
        default=0,
        help_text="Position of seat within the table"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'table_seats'
        verbose_name = 'Table Seat'
        verbose_name_plural = 'Table Seats'
        ordering = ['position']
        unique_together = ['table', 'seat']
    
    def __str__(self):
        return f"{self.table.name} - {self.seat.seat_label}"
    
    def clean(self):
        """Validate table seat relationship."""
        super().clean()
        
        if self.table and self.seat:
            if self.table.zone != self.seat.zone:
                raise ValidationError({
                    'seat': 'Seat must belong to the same zone as the table'
                })


# Add reverse relationship to Seat model for tables
Seat.add_to_class(
    'tables',
    models.ManyToManyField(
        Table,
        through=TableSeat,
        related_name='seats',
        blank=True,
        help_text="Tables this seat belongs to"
    )
)