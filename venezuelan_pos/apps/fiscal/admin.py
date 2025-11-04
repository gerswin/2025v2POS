"""
Django Admin configuration for Fiscal Compliance models.
Provides comprehensive management interfaces for Venezuelan fiscal compliance.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from django.db.models import Count, Sum
from django.contrib.admin import SimpleListFilter
from .models import (
    FiscalSeries, FiscalSeriesCounter, FiscalDay, FiscalReport,
    AuditLog, TaxConfiguration, TaxCalculationHistory
)


class TenantFilter(SimpleListFilter):
    """Filter by tenant for multi-tenant admin"""
    title = 'Tenant'
    parameter_name = 'tenant'
    
    def lookups(self, request, model_admin):
        from venezuelan_pos.apps.tenants.models import Tenant
        return [(tenant.id, tenant.name) for tenant in Tenant.objects.all()]
    
    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(tenant_id=self.value())
        return queryset


@admin.register(FiscalSeriesCounter)
class FiscalSeriesCounterAdmin(admin.ModelAdmin):
    """Admin interface for Fiscal Series Counters"""
    list_display = ['tenant', 'current_series', 'created_at', 'updated_at']
    list_filter = [TenantFilter, 'created_at']
    search_fields = ['tenant__name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    def has_add_permission(self, request):
        """Prevent manual creation - counters are auto-created"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Prevent deletion of fiscal series counters"""
        return False


@admin.register(FiscalSeries)
class FiscalSeriesAdmin(admin.ModelAdmin):
    """Admin interface for Fiscal Series"""
    list_display = [
        'series_number', 'tenant', 'transaction_link', 'issued_by',
        'issued_at', 'is_voided', 'void_status'
    ]
    list_filter = [
        TenantFilter, 'is_voided', 'issued_at', 'issued_by'
    ]
    search_fields = [
        'series_number', 'tenant__name', 'transaction__id',
        'issued_by__username', 'issued_by__email'
    ]
    readonly_fields = [
        'id', 'series_number', 'tenant', 'transaction', 'issued_by',
        'issued_at', 'voided_at', 'voided_by'
    ]
    fieldsets = (
        ('Fiscal Series Information', {
            'fields': ('id', 'series_number', 'tenant', 'transaction', 'issued_by', 'issued_at')
        }),
        ('Void Information', {
            'fields': ('is_voided', 'voided_at', 'voided_by', 'void_reason'),
            'classes': ('collapse',)
        }),
    )
    
    def transaction_link(self, obj):
        """Link to related transaction"""
        if obj.transaction:
            url = reverse('admin:sales_transaction_change', args=[obj.transaction.id])
            return format_html('<a href="{}">{}</a>', url, obj.transaction.id)
        return '-'
    transaction_link.short_description = 'Transaction'
    
    def void_status(self, obj):
        """Display void status with color coding"""
        if obj.is_voided:
            return format_html(
                '<span style="color: red; font-weight: bold;">VOIDED</span>'
            )
        return format_html(
            '<span style="color: green; font-weight: bold;">ACTIVE</span>'
        )
    void_status.short_description = 'Status'
    
    def has_add_permission(self, request):
        """Prevent manual creation - series are auto-generated"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Prevent deletion of fiscal series"""
        return False


@admin.register(FiscalDay)
class FiscalDayAdmin(admin.ModelAdmin):
    """Admin interface for Fiscal Days"""
    list_display = [
        'fiscal_date', 'tenant', 'user', 'is_closed',
        'opened_at', 'closed_at', 'z_report_link'
    ]
    list_filter = [
        TenantFilter, 'is_closed', 'fiscal_date', 'user'
    ]
    search_fields = [
        'tenant__name', 'user__username', 'user__email'
    ]
    readonly_fields = [
        'id', 'opened_at', 'closed_at', 'z_report'
    ]
    date_hierarchy = 'fiscal_date'
    
    def z_report_link(self, obj):
        """Link to Z-Report if exists"""
        if obj.z_report:
            url = reverse('admin:fiscal_fiscalreport_change', args=[obj.z_report.id])
            return format_html('<a href="{}">Z-Report #{}</a>', url, obj.z_report.report_number)
        return '-'
    z_report_link.short_description = 'Z-Report'
    
    actions = ['close_fiscal_days']
    
    def close_fiscal_days(self, request, queryset):
        """Admin action to close selected fiscal days"""
        closed_count = 0
        for fiscal_day in queryset.filter(is_closed=False):
            fiscal_day.close_fiscal_day()
            closed_count += 1
        
        self.message_user(
            request,
            f"Successfully closed {closed_count} fiscal days."
        )
    close_fiscal_days.short_description = "Close selected fiscal days"


@admin.register(FiscalReport)
class FiscalReportAdmin(admin.ModelAdmin):
    """Admin interface for Fiscal Reports"""
    list_display = [
        'report_number', 'report_type', 'tenant', 'user',
        'fiscal_date', 'total_transactions', 'total_amount',
        'generated_at'
    ]
    list_filter = [
        TenantFilter, 'report_type', 'fiscal_date', 'user', 'generated_at'
    ]
    search_fields = [
        'report_number', 'tenant__name', 'user__username'
    ]
    readonly_fields = [
        'id', 'report_number', 'generated_at', 'report_data'
    ]
    fieldsets = (
        ('Report Information', {
            'fields': (
                'id', 'report_type', 'report_number', 'tenant',
                'user', 'fiscal_date', 'generated_at'
            )
        }),
        ('Financial Summary', {
            'fields': (
                'total_transactions', 'total_amount', 'total_tax',
                'first_series', 'last_series'
            )
        }),
        ('Payment Methods Breakdown', {
            'fields': (
                'cash_amount', 'card_amount', 'transfer_amount', 'other_amount'
            ),
            'classes': ('collapse',)
        }),
        ('Detailed Report Data', {
            'fields': ('report_data',),
            'classes': ('collapse',)
        }),
    )
    date_hierarchy = 'fiscal_date'
    
    def has_add_permission(self, request):
        """Prevent manual creation - reports are auto-generated"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Prevent deletion of fiscal reports"""
        return False


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """Admin interface for Audit Logs"""
    list_display = [
        'timestamp', 'tenant', 'user', 'action_type',
        'object_type', 'object_id', 'fiscal_series_link'
    ]
    list_filter = [
        TenantFilter, 'action_type', 'object_type', 'timestamp', 'user'
    ]
    search_fields = [
        'tenant__name', 'user__username', 'object_type',
        'object_id', 'description'
    ]
    readonly_fields = [
        'id', 'tenant', 'user', 'action_type', 'object_type',
        'object_id', 'fiscal_series', 'timestamp', 'ip_address',
        'user_agent', 'old_values', 'new_values', 'description'
    ]
    fieldsets = (
        ('Audit Information', {
            'fields': (
                'id', 'timestamp', 'tenant', 'user', 'action_type',
                'object_type', 'object_id', 'fiscal_series'
            )
        }),
        ('Request Information', {
            'fields': ('ip_address', 'user_agent'),
            'classes': ('collapse',)
        }),
        ('Change Details', {
            'fields': ('old_values', 'new_values', 'description'),
            'classes': ('collapse',)
        }),
    )
    date_hierarchy = 'timestamp'
    
    def fiscal_series_link(self, obj):
        """Link to related fiscal series"""
        if obj.fiscal_series:
            url = reverse('admin:fiscal_fiscalseries_change', args=[obj.fiscal_series.id])
            return format_html('<a href="{}">Series {}</a>', url, obj.fiscal_series.series_number)
        return '-'
    fiscal_series_link.short_description = 'Fiscal Series'
    
    def has_add_permission(self, request):
        """Prevent manual creation - audit logs are auto-generated"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Prevent modification - audit logs are immutable"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Prevent deletion - audit logs are immutable"""
        return False


@admin.register(TaxConfiguration)
class TaxConfigurationAdmin(admin.ModelAdmin):
    """Admin interface for Tax Configurations"""
    list_display = [
        'name', 'tenant', 'event', 'tax_type', 'scope',
        'rate_display', 'is_active', 'effective_period'
    ]
    list_filter = [
        TenantFilter, 'tax_type', 'scope', 'is_active',
        'effective_from', 'created_at'
    ]
    search_fields = [
        'name', 'tenant__name', 'event__name'
    ]
    readonly_fields = [
        'id', 'created_at', 'updated_at'
    ]
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'tenant', 'event', 'scope', 'created_by')
        }),
        ('Tax Configuration', {
            'fields': ('tax_type', 'rate', 'fixed_amount', 'is_active')
        }),
        ('Effective Period', {
            'fields': ('effective_from', 'effective_until')
        }),
        ('Metadata', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def rate_display(self, obj):
        """Display rate with appropriate formatting"""
        if obj.tax_type == 'FIXED':
            return f"${obj.fixed_amount}"
        else:
            return f"{obj.rate * 100:.2f}%"
    rate_display.short_description = 'Rate'
    
    def effective_period(self, obj):
        """Display effective period"""
        start = obj.effective_from.strftime('%Y-%m-%d')
        end = obj.effective_until.strftime('%Y-%m-%d') if obj.effective_until else 'Ongoing'
        return f"{start} to {end}"
    effective_period.short_description = 'Effective Period'
    
    def save_model(self, request, obj, form, change):
        """Set created_by field"""
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(TaxCalculationHistory)
class TaxCalculationHistoryAdmin(admin.ModelAdmin):
    """Admin interface for Tax Calculation History"""
    list_display = [
        'calculated_at', 'tenant', 'transaction_link',
        'tax_configuration', 'base_amount', 'tax_amount',
        'calculated_by'
    ]
    list_filter = [
        TenantFilter, 'tax_configuration', 'calculated_at', 'calculated_by'
    ]
    search_fields = [
        'tenant__name', 'transaction__id', 'tax_configuration__name'
    ]
    readonly_fields = [
        'id', 'tenant', 'transaction', 'tax_configuration',
        'base_amount', 'tax_amount', 'calculated_at', 'calculated_by'
    ]
    date_hierarchy = 'calculated_at'
    
    def transaction_link(self, obj):
        """Link to related transaction"""
        if obj.transaction:
            url = reverse('admin:sales_transaction_change', args=[obj.transaction.id])
            return format_html('<a href="{}">{}</a>', url, obj.transaction.id)
        return '-'
    transaction_link.short_description = 'Transaction'
    
    def has_add_permission(self, request):
        """Prevent manual creation - history is auto-generated"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Prevent modification - history is immutable"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Prevent deletion - history is immutable"""
        return False


# Custom admin site configuration
admin.site.site_header = "Venezuelan POS - Fiscal Compliance"
admin.site.site_title = "Fiscal Admin"
admin.site.index_title = "Fiscal Compliance Management"