from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .models import Venue, Event, EventConfiguration


@admin.register(Venue)
class VenueAdmin(admin.ModelAdmin):
    """Django admin interface for Venue model."""
    
    list_display = [
        'name', 'city', 'state', 'venue_type', 'capacity', 
        'is_active', 'tenant', 'created_at'
    ]
    list_filter = ['venue_type', 'is_active', 'city', 'state', 'created_at']
    search_fields = ['name', 'city', 'address', 'contact_email']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'venue_type', 'capacity', 'is_active')
        }),
        ('Location', {
            'fields': ('address', 'city', 'state', 'country', 'postal_code')
        }),
        ('Contact Information', {
            'fields': ('contact_phone', 'contact_email')
        }),
        ('Configuration', {
            'fields': ('configuration',),
            'classes': ('collapse',)
        }),
        ('System Information', {
            'fields': ('id', 'tenant', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_queryset(self, request):
        """Filter venues by tenant for non-admin users."""
        qs = super().get_queryset(request)
        if request.user.is_admin_user:
            return qs
        return qs.filter(tenant=request.user.tenant)


class EventConfigurationInline(admin.StackedInline):
    """Inline admin for EventConfiguration."""
    
    model = EventConfiguration
    extra = 0
    
    fieldsets = (
        ('Payment Configuration', {
            'fields': (
                'partial_payments_enabled',
                'installment_plans_enabled', 
                'flexible_payments_enabled',
                'max_installments',
                'min_down_payment_percentage',
                'payment_plan_expiry_days'
            )
        }),
        ('Notification Settings', {
            'fields': (
                'notifications_enabled',
                'email_notifications',
                'sms_notifications',
                'whatsapp_notifications',
                'send_purchase_confirmation',
                'send_payment_reminders',
                'send_event_reminders',
                'event_reminder_days'
            )
        }),
        ('Digital Tickets', {
            'fields': (
                'digital_tickets_enabled',
                'qr_codes_enabled',
                'pdf_tickets_enabled'
            )
        }),
        ('Additional Configuration', {
            'fields': ('configuration',),
            'classes': ('collapse',)
        })
    )


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    """Django admin interface for Event model."""
    
    list_display = [
        'name', 'venue', 'event_type', 'start_date', 'end_date',
        'status', 'sales_status', 'tenant', 'created_at'
    ]
    list_filter = [
        'event_type', 'status', 'start_date', 'venue__city', 
        'base_currency', 'created_at'
    ]
    search_fields = ['name', 'description', 'venue__name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    date_hierarchy = 'start_date'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'event_type', 'venue', 'status')
        }),
        ('Event Schedule', {
            'fields': ('start_date', 'end_date', 'sales_start_date', 'sales_end_date')
        }),
        ('Currency and Pricing', {
            'fields': ('base_currency', 'currency_conversion_rate')
        }),
        ('Configuration', {
            'fields': ('configuration',),
            'classes': ('collapse',)
        }),
        ('System Information', {
            'fields': ('id', 'tenant', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    inlines = [EventConfigurationInline]
    
    def get_queryset(self, request):
        """Filter events by tenant for non-admin users."""
        qs = super().get_queryset(request)
        if request.user.is_admin_user:
            return qs
        return qs.filter(tenant=request.user.tenant)
    
    def sales_status(self, obj):
        """Display current sales status with color coding."""
        if obj.is_sales_active:
            return format_html(
                '<span style="color: green; font-weight: bold;">Active</span>'
            )
        elif obj.status == Event.Status.DRAFT:
            return format_html(
                '<span style="color: orange;">Draft</span>'
            )
        elif obj.status == Event.Status.CANCELLED:
            return format_html(
                '<span style="color: red;">Cancelled</span>'
            )
        else:
            return format_html(
                '<span style="color: gray;">Inactive</span>'
            )
    
    sales_status.short_description = 'Sales Status'
    
    def get_form(self, request, obj=None, **kwargs):
        """Customize form based on user permissions."""
        form = super().get_form(request, obj, **kwargs)
        
        # Limit venue choices to user's tenant
        if not request.user.is_admin_user and hasattr(form.base_fields, 'venue'):
            form.base_fields['venue'].queryset = Venue.objects.filter(
                tenant=request.user.tenant,
                is_active=True
            )
        
        return form


@admin.register(EventConfiguration)
class EventConfigurationAdmin(admin.ModelAdmin):
    """Django admin interface for EventConfiguration model."""
    
    list_display = [
        'event', 'partial_payments_enabled', 'notifications_enabled',
        'digital_tickets_enabled', 'created_at'
    ]
    list_filter = [
        'partial_payments_enabled', 'installment_plans_enabled',
        'flexible_payments_enabled', 'notifications_enabled',
        'digital_tickets_enabled', 'created_at'
    ]
    search_fields = ['event__name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Event', {
            'fields': ('event',)
        }),
        ('Payment Configuration', {
            'fields': (
                'partial_payments_enabled',
                'installment_plans_enabled', 
                'flexible_payments_enabled',
                'max_installments',
                'min_down_payment_percentage',
                'payment_plan_expiry_days'
            )
        }),
        ('Notification Settings', {
            'fields': (
                'notifications_enabled',
                'email_notifications',
                'sms_notifications',
                'whatsapp_notifications',
                'send_purchase_confirmation',
                'send_payment_reminders',
                'send_event_reminders',
                'event_reminder_days'
            )
        }),
        ('Digital Tickets', {
            'fields': (
                'digital_tickets_enabled',
                'qr_codes_enabled',
                'pdf_tickets_enabled'
            )
        }),
        ('Additional Configuration', {
            'fields': ('configuration',),
            'classes': ('collapse',)
        }),
        ('System Information', {
            'fields': ('id', 'tenant', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_queryset(self, request):
        """Filter configurations by tenant for non-admin users."""
        qs = super().get_queryset(request)
        if request.user.is_admin_user:
            return qs
        return qs.filter(tenant=request.user.tenant)
    
    def get_form(self, request, obj=None, **kwargs):
        """Customize form based on user permissions."""
        form = super().get_form(request, obj, **kwargs)
        
        # Limit event choices to user's tenant
        if not request.user.is_admin_user and hasattr(form.base_fields, 'event'):
            form.base_fields['event'].queryset = Event.objects.filter(
                tenant=request.user.tenant
            )
        
        return form