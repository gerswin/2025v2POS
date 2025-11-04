"""
Django admin configuration for pricing models.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone

from .models import PriceStage, RowPricing, PriceHistory


@admin.register(PriceStage)
class PriceStageAdmin(admin.ModelAdmin):
    """Admin interface for PriceStage model."""
    
    list_display = [
        'name', 'event', 'start_date', 'end_date', 'modifier_value',
        'stage_order', 'is_active', 'status_indicator'
    ]
    list_filter = [
        'is_active', 'event__event_type', 'tenant', 'start_date', 'end_date'
    ]
    search_fields = ['name', 'event__name', 'description']
    ordering = ['event', 'stage_order', 'start_date']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('event', 'name', 'description')
        }),
        ('Date Range', {
            'fields': ('start_date', 'end_date')
        }),
        ('Pricing Configuration', {
            'fields': ('modifier_type', 'modifier_value', 'stage_order')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Advanced Configuration', {
            'fields': ('configuration',),
            'classes': ('collapse',)
        })
    )
    
    readonly_fields = ['tenant']
    
    def get_queryset(self, request):
        """Filter by tenant."""
        qs = super().get_queryset(request)
        if hasattr(request.user, 'tenant'):
            return qs.filter(tenant=request.user.tenant)
        return qs
    
    def save_model(self, request, obj, form, change):
        """Set tenant when saving."""
        if not change and hasattr(request.user, 'tenant'):
            obj.tenant = request.user.tenant
        super().save_model(request, obj, form, change)
    
    def status_indicator(self, obj):
        """Show current status of price stage."""
        now = timezone.now()
        
        if not obj.is_active:
            return format_html(
                '<span style="color: #999;">Inactive</span>'
            )
        elif obj.start_date <= now <= obj.end_date:
            return format_html(
                '<span style="color: #28a745; font-weight: bold;">● Current</span>'
            )
        elif now < obj.start_date:
            return format_html(
                '<span style="color: #007bff;">⏳ Upcoming</span>'
            )
        else:
            return format_html(
                '<span style="color: #6c757d;">Past</span>'
            )
    
    status_indicator.short_description = 'Status'
    
    def get_form(self, request, obj=None, **kwargs):
        """Customize form based on user's tenant."""
        form = super().get_form(request, obj, **kwargs)
        
        if hasattr(request.user, 'tenant'):
            # Filter events by tenant
            form.base_fields['event'].queryset = form.base_fields['event'].queryset.filter(
                tenant=request.user.tenant
            )
        
        return form


@admin.register(RowPricing)
class RowPricingAdmin(admin.ModelAdmin):
    """Admin interface for RowPricing model."""
    
    list_display = [
        'zone', 'row_number', 'percentage_markup', 'name', 'is_active'
    ]
    list_filter = [
        'is_active', 'zone__event', 'zone__zone_type', 'tenant'
    ]
    search_fields = ['zone__name', 'zone__event__name', 'name', 'description']
    ordering = ['zone', 'row_number']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('zone', 'row_number', 'name', 'description')
        }),
        ('Pricing Configuration', {
            'fields': ('percentage_markup',)
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Advanced Configuration', {
            'fields': ('configuration',),
            'classes': ('collapse',)
        })
    )
    
    readonly_fields = ['tenant']
    
    def get_queryset(self, request):
        """Filter by tenant."""
        qs = super().get_queryset(request)
        if hasattr(request.user, 'tenant'):
            return qs.filter(tenant=request.user.tenant)
        return qs.select_related('zone', 'zone__event')
    
    def save_model(self, request, obj, form, change):
        """Set tenant when saving."""
        if not change and hasattr(request.user, 'tenant'):
            obj.tenant = request.user.tenant
        super().save_model(request, obj, form, change)
    
    def get_form(self, request, obj=None, **kwargs):
        """Customize form based on user's tenant."""
        form = super().get_form(request, obj, **kwargs)
        
        if hasattr(request.user, 'tenant'):
            # Filter zones by tenant and only numbered zones
            from venezuelan_pos.apps.zones.models import Zone
            form.base_fields['zone'].queryset = form.base_fields['zone'].queryset.filter(
                tenant=request.user.tenant,
                zone_type=Zone.ZoneType.NUMBERED
            )
        
        return form


@admin.register(PriceHistory)
class PriceHistoryAdmin(admin.ModelAdmin):
    """Admin interface for PriceHistory model."""
    
    list_display = [
        'event', 'zone', 'price_type', 'base_price', 'markup_percentage',
        'final_price', 'calculation_date', 'row_seat_info'
    ]
    list_filter = [
        'price_type', 'calculation_date', 'event', 'zone', 'tenant'
    ]
    search_fields = [
        'event__name', 'zone__name', 'price_stage__name'
    ]
    ordering = ['-calculation_date', '-created_at']
    
    fieldsets = (
        ('Related Objects', {
            'fields': ('event', 'zone', 'price_stage', 'row_pricing')
        }),
        ('Price Information', {
            'fields': (
                'price_type', 'base_price', 'markup_percentage',
                'markup_amount', 'final_price'
            )
        }),
        ('Context', {
            'fields': (
                'calculation_date', 'row_number', 'seat_number'
            )
        }),
        ('Calculation Details', {
            'fields': ('calculation_details',),
            'classes': ('collapse',)
        })
    )
    
    readonly_fields = [
        'tenant', 'event', 'zone', 'price_stage', 'row_pricing',
        'price_type', 'base_price', 'markup_percentage', 'markup_amount',
        'final_price', 'calculation_date', 'row_number', 'seat_number',
        'calculation_details', 'created_at'
    ]
    
    def has_add_permission(self, request):
        """Disable adding price history records manually."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Disable editing price history records."""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Allow deletion for cleanup purposes."""
        return request.user.is_superuser
    
    def get_queryset(self, request):
        """Filter by tenant."""
        qs = super().get_queryset(request)
        if hasattr(request.user, 'tenant'):
            return qs.filter(tenant=request.user.tenant)
        return qs.select_related('event', 'zone', 'price_stage', 'row_pricing')
    
    def row_seat_info(self, obj):
        """Display row and seat information."""
        if obj.row_number and obj.seat_number:
            return f"Row {obj.row_number}, Seat {obj.seat_number}"
        elif obj.row_number:
            return f"Row {obj.row_number}"
        else:
            return "Zone pricing"
    
    row_seat_info.short_description = 'Location'
    
    def get_readonly_fields(self, request, obj=None):
        """All fields are readonly for price history."""
        return [field.name for field in self.model._meta.fields]


# Inline admin for price stages in event admin
class PriceStageInline(admin.TabularInline):
    """Inline admin for price stages."""
    
    model = PriceStage
    extra = 0
    fields = [
        'name', 'start_date', 'end_date', 'modifier_type', 'modifier_value',
        'stage_order', 'is_active'
    ]
    ordering = ['stage_order', 'start_date']


# Inline admin for row pricing in zone admin
class RowPricingInline(admin.TabularInline):
    """Inline admin for row pricing."""
    
    model = RowPricing
    extra = 0
    fields = [
        'row_number', 'percentage_markup', 'name', 'is_active'
    ]
    ordering = ['row_number']