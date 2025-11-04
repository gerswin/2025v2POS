from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from venezuelan_pos.apps.tenants.middleware import AdminTenantMixin
from .models import DigitalTicket, TicketTemplate, TicketValidationLog


@admin.register(DigitalTicket)
class DigitalTicketAdmin(AdminTenantMixin, admin.ModelAdmin):
    """Admin interface for Digital Tickets."""
    
    list_display = [
        'ticket_number', 'customer_name', 'event_name', 'zone_name',
        'seat_label_display', 'status', 'usage_display', 'created_at'
    ]
    list_filter = [
        'status', 'ticket_type', 'event', 'zone', 'created_at'
    ]
    search_fields = [
        'ticket_number', 'customer__name', 'customer__surname',
        'customer__email', 'customer__phone', 'event__name'
    ]
    readonly_fields = [
        'id', 'ticket_number', 'qr_code_display', 'validation_hash',
        'usage_count', 'first_used_at', 'last_used_at', 'created_at', 'updated_at'
    ]
    
    fieldsets = (
        ('Ticket Information', {
            'fields': (
                'id', 'ticket_number', 'sequence_number', 'ticket_type', 'status'
            )
        }),
        ('Event & Customer', {
            'fields': (
                'event', 'customer', 'transaction', 'transaction_item'
            )
        }),
        ('Seating', {
            'fields': (
                'zone', 'seat'
            )
        }),
        ('Pricing', {
            'fields': (
                'unit_price', 'total_price', 'currency'
            )
        }),
        ('Validation & QR Code', {
            'fields': (
                'qr_code_display', 'validation_hash', 'qr_code_data'
            )
        }),
        ('Usage Tracking', {
            'fields': (
                'usage_count', 'max_usage_count', 'first_used_at', 'last_used_at'
            )
        }),
        ('Validity Period', {
            'fields': (
                'valid_from', 'valid_until'
            )
        }),
        ('Metadata', {
            'fields': (
                'metadata',
            ),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': (
                'created_at', 'updated_at'
            ),
            'classes': ('collapse',)
        }),
    )
    
    def customer_name(self, obj):
        """Display customer name with link."""
        url = reverse('admin:customers_customer_change', args=[obj.customer.pk])
        return format_html('<a href="{}">{}</a>', url, obj.customer.full_name)
    customer_name.short_description = 'Customer'
    
    def event_name(self, obj):
        """Display event name with link."""
        url = reverse('admin:events_event_change', args=[obj.event.pk])
        return format_html('<a href="{}">{}</a>', url, obj.event.name)
    event_name.short_description = 'Event'
    
    def zone_name(self, obj):
        """Display zone name."""
        return obj.zone.name
    zone_name.short_description = 'Zone'
    
    def seat_label_display(self, obj):
        """Display seat label or general admission."""
        if obj.seat:
            return obj.seat.seat_label
        return "General Admission"
    seat_label_display.short_description = 'Seat'
    
    def usage_display(self, obj):
        """Display usage count with status."""
        if obj.usage_count >= obj.max_usage_count:
            color = 'red'
        elif obj.usage_count > 0:
            color = 'orange'
        else:
            color = 'green'
        
        return format_html(
            '<span style="color: {};">{}/{}</span>',
            color, obj.usage_count, obj.max_usage_count
        )
    usage_display.short_description = 'Usage'
    
    def qr_code_display(self, obj):
        """Display QR code image if available."""
        if obj.qr_code_image:
            return format_html(
                '<img src="{}" width="100" height="100" />',
                obj.qr_code_image.url
            )
        return "No QR Code"
    qr_code_display.short_description = 'QR Code'
    
    actions = ['regenerate_qr_codes', 'mark_as_used', 'mark_as_cancelled']
    
    def regenerate_qr_codes(self, request, queryset):
        """Regenerate QR codes for selected tickets."""
        count = 0
        for ticket in queryset:
            ticket.generate_qr_code()
            count += 1
        
        self.message_user(
            request,
            f"Successfully regenerated QR codes for {count} tickets."
        )
    regenerate_qr_codes.short_description = "Regenerate QR codes"
    
    def mark_as_used(self, request, queryset):
        """Mark selected tickets as used."""
        count = queryset.update(status=DigitalTicket.Status.USED)
        self.message_user(
            request,
            f"Successfully marked {count} tickets as used."
        )
    mark_as_used.short_description = "Mark as used"
    
    def mark_as_cancelled(self, request, queryset):
        """Mark selected tickets as cancelled."""
        count = queryset.update(status=DigitalTicket.Status.CANCELLED)
        self.message_user(
            request,
            f"Successfully marked {count} tickets as cancelled."
        )
    mark_as_cancelled.short_description = "Mark as cancelled"


@admin.register(TicketTemplate)
class TicketTemplateAdmin(AdminTenantMixin, admin.ModelAdmin):
    """Admin interface for Ticket Templates."""
    
    list_display = [
        'name', 'template_type', 'is_default', 'is_active',
        'include_qr_code', 'created_at'
    ]
    list_filter = [
        'template_type', 'is_default', 'is_active',
        'include_qr_code', 'created_at'
    ]
    search_fields = ['name', 'template_type']
    
    fieldsets = (
        ('Template Information', {
            'fields': (
                'name', 'template_type', 'is_default', 'is_active'
            )
        }),
        ('Template Content', {
            'fields': (
                'html_content', 'css_styles'
            )
        }),
        ('Layout Settings', {
            'fields': (
                'page_size', 'orientation'
            )
        }),
        ('Features', {
            'fields': (
                'include_qr_code', 'include_barcode', 'include_logo'
            )
        }),
    )
    
    actions = ['make_default', 'activate_templates', 'deactivate_templates']
    
    def make_default(self, request, queryset):
        """Make selected template the default for its type."""
        for template in queryset:
            # Remove default flag from other templates of same type
            TicketTemplate.objects.filter(
                tenant=template.tenant,
                template_type=template.template_type
            ).update(is_default=False)
            
            # Set this template as default
            template.is_default = True
            template.save()
        
        self.message_user(
            request,
            f"Successfully set {queryset.count()} templates as default."
        )
    make_default.short_description = "Make default template"
    
    def activate_templates(self, request, queryset):
        """Activate selected templates."""
        count = queryset.update(is_active=True)
        self.message_user(
            request,
            f"Successfully activated {count} templates."
        )
    activate_templates.short_description = "Activate templates"
    
    def deactivate_templates(self, request, queryset):
        """Deactivate selected templates."""
        count = queryset.update(is_active=False)
        self.message_user(
            request,
            f"Successfully deactivated {count} templates."
        )
    deactivate_templates.short_description = "Deactivate templates"


@admin.register(TicketValidationLog)
class TicketValidationLogAdmin(AdminTenantMixin, admin.ModelAdmin):
    """Admin interface for Ticket Validation Logs."""
    
    list_display = [
        'ticket_number', 'validation_result_display', 'validation_method',
        'validation_system_id', 'usage_change', 'validated_at'
    ]
    list_filter = [
        'validation_result', 'validation_method', 'validated_at'
    ]
    search_fields = [
        'ticket__ticket_number', 'validation_system_id',
        'ticket__customer__name', 'ticket__customer__surname'
    ]
    readonly_fields = [
        'ticket', 'validation_system_id', 'validation_result',
        'validation_method', 'usage_count_before', 'usage_count_after',
        'validation_location', 'ip_address', 'user_agent',
        'metadata', 'validated_at'
    ]
    
    fieldsets = (
        ('Validation Information', {
            'fields': (
                'ticket', 'validation_result', 'validation_method'
            )
        }),
        ('System Information', {
            'fields': (
                'validation_system_id', 'validation_location',
                'ip_address', 'user_agent'
            )
        }),
        ('Usage Tracking', {
            'fields': (
                'usage_count_before', 'usage_count_after'
            )
        }),
        ('Metadata', {
            'fields': (
                'metadata',
            ),
            'classes': ('collapse',)
        }),
        ('Timestamp', {
            'fields': (
                'validated_at',
            )
        }),
    )
    
    def ticket_number(self, obj):
        """Display ticket number with link."""
        url = reverse('admin:tickets_digitalticket_change', args=[obj.ticket.pk])
        return format_html('<a href="{}">{}</a>', url, obj.ticket.ticket_number)
    ticket_number.short_description = 'Ticket'
    
    def validation_result_display(self, obj):
        """Display validation result with color."""
        if obj.validation_result:
            return format_html(
                '<span style="color: green; font-weight: bold;">SUCCESS</span>'
            )
        else:
            return format_html(
                '<span style="color: red; font-weight: bold;">FAILED</span>'
            )
    validation_result_display.short_description = 'Result'
    
    def usage_change(self, obj):
        """Display usage count change."""
        change = obj.usage_count_after - obj.usage_count_before
        if change > 0:
            return format_html(
                '<span style="color: blue;">+{}</span>',
                change
            )
        return "0"
    usage_change.short_description = 'Usage Change'
    
    def has_add_permission(self, request):
        """Validation logs are read-only."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Validation logs are read-only."""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Allow deletion for cleanup purposes."""
        return request.user.is_superuser


# Inline admin for showing tickets in transaction admin
class DigitalTicketInline(admin.TabularInline):
    """Inline admin for digital tickets in transaction admin."""
    
    model = DigitalTicket
    extra = 0
    readonly_fields = [
        'ticket_number', 'status', 'usage_count', 'qr_code_display_small'
    ]
    fields = [
        'ticket_number', 'ticket_type', 'zone', 'seat',
        'status', 'usage_count', 'qr_code_display_small'
    ]
    
    def qr_code_display_small(self, obj):
        """Display small QR code image."""
        if obj.qr_code_image:
            return format_html(
                '<img src="{}" width="50" height="50" />',
                obj.qr_code_image.url
            )
        return "No QR Code"
    qr_code_display_small.short_description = 'QR'
    
    def has_add_permission(self, request, obj=None):
        """Tickets are auto-generated."""
        return False


# Inline admin for showing validation logs in ticket admin
class TicketValidationLogInline(admin.TabularInline):
    """Inline admin for validation logs in ticket admin."""
    
    model = TicketValidationLog
    extra = 0
    readonly_fields = [
        'validation_result', 'validation_method', 'validation_system_id',
        'usage_count_after', 'validated_at'
    ]
    fields = [
        'validation_result', 'validation_method', 'validation_system_id',
        'usage_count_after', 'validated_at'
    ]
    
    def has_add_permission(self, request, obj=None):
        """Validation logs are auto-generated."""
        return False


# Add the inline to DigitalTicketAdmin
DigitalTicketAdmin.inlines = [TicketValidationLogInline]