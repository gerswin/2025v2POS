from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .models import SalesReport, OccupancyAnalysis, ReportSchedule


@admin.register(SalesReport)
class SalesReportAdmin(admin.ModelAdmin):
    """Django admin interface for SalesReport."""
    
    list_display = [
        'name',
        'report_type',
        'status_badge',
        'total_transactions',
        'total_revenue',
        'total_tickets',
        'average_ticket_price',
        'period_display',
        'generated_by',
        'created_at'
    ]
    
    list_filter = [
        'report_type',
        'status',
        'created_at',
        'period_start',
        'period_end'
    ]
    
    search_fields = [
        'name',
        'generated_by__username',
        'generated_by__email'
    ]
    
    readonly_fields = [
        'id',
        'total_transactions',
        'total_revenue',
        'total_tickets',
        'average_ticket_price',
        'status',
        'completed_at',
        'created_at',
        'updated_at'
    ]
    
    fieldsets = (
        ('Report Information', {
            'fields': (
                'id',
                'name',
                'report_type',
                'status',
                'generated_by'
            )
        }),
        ('Report Period', {
            'fields': (
                'period_start',
                'period_end'
            )
        }),
        ('Filters', {
            'fields': (
                'filters',
            ),
            'classes': ('collapse',)
        }),
        ('Results', {
            'fields': (
                'total_transactions',
                'total_revenue',
                'total_tickets',
                'average_ticket_price'
            )
        }),
        ('Export Options', {
            'fields': (
                'export_formats',
            ),
            'classes': ('collapse',)
        }),
        ('Additional Data', {
            'fields': (
                'detailed_data',
            ),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': (
                'created_at',
                'completed_at',
                'updated_at'
            ),
            'classes': ('collapse',)
        })
    )
    
    def status_badge(self, obj):
        """Display status with color coding."""
        colors = {
            'generating': 'orange',
            'completed': 'green',
            'failed': 'red'
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def period_display(self, obj):
        """Display report period in a readable format."""
        if obj.period_start and obj.period_end:
            return f"{obj.period_start.strftime('%Y-%m-%d')} to {obj.period_end.strftime('%Y-%m-%d')}"
        return "N/A"
    period_display.short_description = 'Period'
    
    def get_queryset(self, request):
        """Filter by tenant."""
        qs = super().get_queryset(request)
        if hasattr(request.user, 'tenant'):
            qs = qs.filter(tenant=request.user.tenant)
        return qs
    
    def save_model(self, request, obj, form, change):
        """Set tenant and generated_by on save."""
        if not change:  # Only for new objects
            if hasattr(request.user, 'tenant'):
                obj.tenant = request.user.tenant
            obj.generated_by = request.user
        super().save_model(request, obj, form, change)
    
    actions = ['generate_export', 'mark_completed']
    
    def generate_export(self, request, queryset):
        """Action to generate exports for selected reports."""
        # This would trigger export generation
        count = queryset.count()
        self.message_user(request, f"Export generation initiated for {count} reports.")
    generate_export.short_description = "Generate exports for selected reports"
    
    def mark_completed(self, request, queryset):
        """Action to mark reports as completed."""
        updated = queryset.filter(status='generating').update(
            status='completed',
            completed_at=timezone.now()
        )
        self.message_user(request, f"{updated} reports marked as completed.")
    mark_completed.short_description = "Mark selected reports as completed"


@admin.register(OccupancyAnalysis)
class OccupancyAnalysisAdmin(admin.ModelAdmin):
    """Django admin interface for OccupancyAnalysis."""
    
    list_display = [
        'name',
        'analysis_type',
        'event',
        'zone',
        'total_capacity',
        'sold_tickets',
        'fill_rate_display',
        'sales_velocity',
        'performance_rating',
        'generated_by',
        'created_at'
    ]
    
    list_filter = [
        'analysis_type',
        'event',
        'zone',
        'created_at'
    ]
    
    search_fields = [
        'name',
        'event__name',
        'zone__name',
        'generated_by__username'
    ]
    
    readonly_fields = [
        'id',
        'total_capacity',
        'sold_tickets',
        'fill_rate',
        'sales_velocity',
        'available_capacity',
        'occupancy_status',
        'performance_rating',
        'created_at',
        'updated_at'
    ]
    
    fieldsets = (
        ('Analysis Information', {
            'fields': (
                'id',
                'name',
                'analysis_type',
                'event',
                'zone',
                'generated_by'
            )
        }),
        ('Analysis Period', {
            'fields': (
                'analysis_start',
                'analysis_end'
            )
        }),
        ('Occupancy Metrics', {
            'fields': (
                'total_capacity',
                'sold_tickets',
                'available_capacity',
                'fill_rate',
                'occupancy_status',
                'sales_velocity',
                'performance_rating'
            )
        }),
        ('Heat Map Data', {
            'fields': (
                'heat_map_data',
            ),
            'classes': ('collapse',)
        }),
        ('Performance Metrics', {
            'fields': (
                'performance_metrics',
            ),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': (
                'created_at',
                'updated_at'
            ),
            'classes': ('collapse',)
        })
    )
    
    def fill_rate_display(self, obj):
        """Display fill rate with color coding."""
        rate = float(obj.fill_rate)
        if rate >= 80:
            color = 'green'
        elif rate >= 50:
            color = 'orange'
        else:
            color = 'red'
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{:.1f}%</span>',
            color,
            rate
        )
    fill_rate_display.short_description = 'Fill Rate'
    
    def get_queryset(self, request):
        """Filter by tenant."""
        qs = super().get_queryset(request)
        if hasattr(request.user, 'tenant'):
            qs = qs.filter(tenant=request.user.tenant)
        return qs.select_related('event', 'zone', 'generated_by')
    
    def save_model(self, request, obj, form, change):
        """Set tenant and generated_by on save."""
        if not change:  # Only for new objects
            if hasattr(request.user, 'tenant'):
                obj.tenant = request.user.tenant
            obj.generated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(ReportSchedule)
class ReportScheduleAdmin(admin.ModelAdmin):
    """Django admin interface for ReportSchedule."""
    
    list_display = [
        'name',
        'report_type',
        'frequency',
        'status_badge',
        'next_run',
        'last_run',
        'created_by',
        'created_at'
    ]
    
    list_filter = [
        'report_type',
        'frequency',
        'status',
        'created_at',
        'next_run'
    ]
    
    search_fields = [
        'name',
        'description',
        'created_by__username'
    ]
    
    readonly_fields = [
        'id',
        'last_run',
        'created_at',
        'updated_at'
    ]
    
    fieldsets = (
        ('Schedule Information', {
            'fields': (
                'id',
                'name',
                'description',
                'status',
                'created_by'
            )
        }),
        ('Report Configuration', {
            'fields': (
                'report_type',
                'report_filters'
            )
        }),
        ('Schedule Configuration', {
            'fields': (
                'frequency',
                'next_run',
                'last_run'
            )
        }),
        ('Delivery Options', {
            'fields': (
                'email_recipients',
                'export_formats'
            )
        }),
        ('Timestamps', {
            'fields': (
                'created_at',
                'updated_at'
            ),
            'classes': ('collapse',)
        })
    )
    
    def status_badge(self, obj):
        """Display status with color coding."""
        colors = {
            'active': 'green',
            'paused': 'orange',
            'inactive': 'red'
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def get_queryset(self, request):
        """Filter by tenant."""
        qs = super().get_queryset(request)
        if hasattr(request.user, 'tenant'):
            qs = qs.filter(tenant=request.user.tenant)
        return qs.select_related('created_by')
    
    def save_model(self, request, obj, form, change):
        """Set tenant and created_by on save."""
        if not change:  # Only for new objects
            if hasattr(request.user, 'tenant'):
                obj.tenant = request.user.tenant
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    actions = ['activate_schedules', 'pause_schedules', 'execute_now']
    
    def activate_schedules(self, request, queryset):
        """Action to activate selected schedules."""
        updated = queryset.update(status='active')
        self.message_user(request, f"{updated} schedules activated.")
    activate_schedules.short_description = "Activate selected schedules"
    
    def pause_schedules(self, request, queryset):
        """Action to pause selected schedules."""
        updated = queryset.update(status='paused')
        self.message_user(request, f"{updated} schedules paused.")
    pause_schedules.short_description = "Pause selected schedules"
    
    def execute_now(self, request, queryset):
        """Action to execute schedules immediately."""
        count = 0
        for schedule in queryset.filter(status='active'):
            try:
                schedule.execute()
                count += 1
            except Exception as e:
                self.message_user(request, f"Failed to execute {schedule.name}: {e}", level='ERROR')
        
        if count > 0:
            self.message_user(request, f"{count} schedules executed successfully.")
    execute_now.short_description = "Execute selected schedules now"