from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from venezuelan_pos.apps.tenants.middleware import AdminTenantMixin
from .models import Zone, Seat, Table, TableSeat


@admin.register(Zone)
class ZoneAdmin(AdminTenantMixin, admin.ModelAdmin):
    """Admin interface for Zone model."""
    
    list_display = [
        'name', 'event', 'zone_type', 'capacity', 'base_price', 
        'status', 'available_capacity', 'display_order'
    ]
    list_filter = ['zone_type', 'status', 'event__status', 'created_at']
    search_fields = ['name', 'event__name', 'description']
    ordering = ['event', 'display_order', 'name']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('event', 'name', 'description', 'zone_type', 'status')
        }),
        ('Capacity Configuration', {
            'fields': ('capacity', 'rows', 'seats_per_row'),
            'description': 'For numbered zones, capacity will be calculated as rows × seats per row'
        }),
        ('Pricing', {
            'fields': ('base_price',)
        }),
        ('Display', {
            'fields': ('display_order',)
        }),
        ('Configuration', {
            'fields': ('configuration',),
            'classes': ('collapse',)
        })
    )
    
    readonly_fields = ['available_capacity', 'sold_capacity']
    
    def get_queryset(self, request):
        """Filter queryset by tenant and optimize queries."""
        qs = super().get_queryset(request)
        return qs.select_related('event', 'event__venue').prefetch_related('seats')
    
    def available_capacity(self, obj):
        """Display available capacity."""
        return obj.available_capacity
    available_capacity.short_description = 'Available'
    
    def sold_capacity(self, obj):
        """Display sold capacity."""
        return obj.sold_capacity
    sold_capacity.short_description = 'Sold'
    
    def save_model(self, request, obj, form, change):
        """Override save to handle seat generation."""
        super().save_model(request, obj, form, change)
        
        # Show message about seat generation for numbered zones
        if obj.zone_type == Zone.ZoneType.NUMBERED and not change:
            self.message_user(
                request,
                f"Zone '{obj.name}' created with {obj.capacity} seats generated automatically."
            )


@admin.register(Seat)
class SeatAdmin(AdminTenantMixin, admin.ModelAdmin):
    """Admin interface for Seat model."""
    
    list_display = [
        'zone', 'row_number', 'seat_number', 'status', 
        'price_modifier', 'calculated_price'
    ]
    list_filter = ['status', 'zone__event', 'zone', 'row_number']
    search_fields = ['zone__name', 'zone__event__name']
    ordering = ['zone', 'row_number', 'seat_number']
    
    fieldsets = (
        ('Seat Information', {
            'fields': ('zone', 'row_number', 'seat_number', 'status')
        }),
        ('Pricing', {
            'fields': ('price_modifier', 'calculated_price'),
            'description': 'Price modifier is a percentage (e.g., 10.00 for 10% increase)'
        }),
        ('Configuration', {
            'fields': ('configuration',),
            'classes': ('collapse',)
        })
    )
    
    readonly_fields = ['calculated_price']
    
    def get_queryset(self, request):
        """Filter queryset by tenant and optimize queries."""
        qs = super().get_queryset(request)
        return qs.select_related('zone', 'zone__event')
    
    def calculated_price(self, obj):
        """Display calculated price."""
        return f"${obj.calculated_price:.2f}"
    calculated_price.short_description = 'Final Price'
    
    def has_add_permission(self, request):
        """Limit seat creation - seats are auto-generated for numbered zones."""
        return False  # Seats are created automatically when zones are created


class TableSeatInline(admin.TabularInline):
    """Inline for managing table seats."""
    model = TableSeat
    extra = 0
    fields = ['seat', 'position']
    ordering = ['position']
    
    def get_queryset(self, request):
        """Optimize queries for inline."""
        qs = super().get_queryset(request)
        return qs.select_related('seat')


@admin.register(Table)
class TableAdmin(AdminTenantMixin, admin.ModelAdmin):
    """Admin interface for Table model."""
    
    list_display = [
        'name', 'zone', 'sale_mode', 'status', 
        'seat_count', 'available_seats_count', 'total_price'
    ]
    list_filter = ['sale_mode', 'status', 'zone__event', 'zone']
    search_fields = ['name', 'zone__name', 'zone__event__name', 'description']
    ordering = ['zone', 'display_order', 'name']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('zone', 'name', 'description', 'status')
        }),
        ('Configuration', {
            'fields': ('sale_mode', 'display_order')
        }),
        ('Advanced Configuration', {
            'fields': ('configuration',),
            'classes': ('collapse',)
        })
    )
    
    inlines = [TableSeatInline]
    
    def get_queryset(self, request):
        """Filter queryset by tenant and optimize queries."""
        qs = super().get_queryset(request)
        return qs.select_related('zone', 'zone__event').prefetch_related('seats')
    
    def seat_count(self, obj):
        """Display seat count."""
        return obj.seat_count
    seat_count.short_description = 'Seats'
    
    def available_seats_count(self, obj):
        """Display available seats count."""
        return obj.available_seats.count()
    available_seats_count.short_description = 'Available'
    
    def total_price(self, obj):
        """Display total price."""
        return f"${obj.total_price:.2f}"
    total_price.short_description = 'Total Price'


@admin.register(TableSeat)
class TableSeatAdmin(AdminTenantMixin, admin.ModelAdmin):
    """Admin interface for TableSeat model."""
    
    list_display = ['table', 'seat', 'position']
    list_filter = ['table__zone__event', 'table__zone', 'table']
    search_fields = ['table__name', 'seat__zone__name']
    ordering = ['table', 'position']
    
    def get_queryset(self, request):
        """Filter queryset by tenant and optimize queries."""
        qs = super().get_queryset(request)
        return qs.select_related('table', 'seat', 'table__zone', 'seat__zone')