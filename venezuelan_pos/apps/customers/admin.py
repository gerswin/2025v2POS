from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Customer, CustomerPreferences


class CustomerPreferencesInline(admin.StackedInline):
    """Inline admin for customer preferences."""
    model = CustomerPreferences
    extra = 0
    fieldsets = (
        ('Communication Channels', {
            'fields': (
                ('email_enabled', 'sms_enabled'),
                ('whatsapp_enabled', 'phone_enabled'),
            )
        }),
        ('Notification Types', {
            'fields': (
                ('purchase_confirmations', 'payment_reminders'),
                ('event_reminders', 'promotional_messages'),
                'system_updates',
            )
        }),
        ('Contact Preferences', {
            'fields': (
                ('preferred_contact_time_start', 'preferred_contact_time_end'),
                'preferred_language',
            )
        }),
    )


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    """Admin interface for Customer model."""
    
    list_display = [
        'full_name',
        'primary_contact',
        'display_identification',
        'tenant',
        'is_active',
        'created_at',
    ]
    
    list_filter = [
        'is_active',
        'tenant',
        'created_at',
        'preferences__email_enabled',
        'preferences__sms_enabled',
        'preferences__whatsapp_enabled',
    ]
    
    search_fields = [
        'name',
        'surname',
        'phone',
        'email',
        'identification',
    ]
    
    readonly_fields = [
        'id',
        'full_name',
        'display_identification',
        'primary_contact',
        'created_at',
        'updated_at',
    ]
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'id',
                ('name', 'surname'),
                'full_name',
            )
        }),
        ('Contact Information', {
            'fields': (
                ('phone', 'email'),
                'primary_contact',
                'identification',
                'display_identification',
            )
        }),
        ('Additional Information', {
            'fields': (
                'date_of_birth',
                'address',
                'notes',
            ),
            'classes': ('collapse',),
        }),
        ('Status', {
            'fields': (
                'is_active',
                ('created_at', 'updated_at'),
            )
        }),
    )
    
    inlines = [CustomerPreferencesInline]
    
    ordering = ['surname', 'name']
    date_hierarchy = 'created_at'
    
    def get_queryset(self, request):
        """Filter customers by tenant for non-admin users."""
        qs = super().get_queryset(request)
        if request.user.is_superuser or request.user.is_admin_user:
            return qs
        return qs.filter(tenant=request.user.tenant)
    
    def save_model(self, request, obj, form, change):
        """Ensure tenant is set when saving."""
        if not obj.tenant_id and not request.user.is_admin_user:
            obj.tenant = request.user.tenant
        super().save_model(request, obj, form, change)
    
    def full_name(self, obj):
        """Display full name with link to detail view."""
        url = reverse('admin:customers_customer_change', args=[obj.pk])
        return format_html('<a href="{}">{}</a>', url, obj.full_name)
    full_name.short_description = 'Full Name'
    full_name.admin_order_field = 'surname'
    
    def primary_contact(self, obj):
        """Display primary contact method."""
        contact = obj.primary_contact
        if obj.phone and obj.email:
            return format_html(
                '<strong>Phone:</strong> {}<br><strong>Email:</strong> {}',
                obj.phone, obj.email
            )
        elif obj.phone:
            return format_html('<strong>Phone:</strong> {}', obj.phone)
        elif obj.email:
            return format_html('<strong>Email:</strong> {}', obj.email)
        return 'No contact info'
    primary_contact.short_description = 'Contact Info'
    
    def display_identification(self, obj):
        """Display formatted identification."""
        if obj.identification:
            return format_html('<code>{}</code>', obj.identification)
        return '-'
    display_identification.short_description = 'Identification'
    display_identification.admin_order_field = 'identification'
    
    actions = ['activate_customers', 'deactivate_customers']
    
    def activate_customers(self, request, queryset):
        """Activate selected customers."""
        updated = queryset.update(is_active=True)
        self.message_user(
            request,
            f'{updated} customer(s) were successfully activated.'
        )
    activate_customers.short_description = 'Activate selected customers'
    
    def deactivate_customers(self, request, queryset):
        """Deactivate selected customers."""
        updated = queryset.update(is_active=False)
        self.message_user(
            request,
            f'{updated} customer(s) were successfully deactivated.'
        )
    deactivate_customers.short_description = 'Deactivate selected customers'


@admin.register(CustomerPreferences)
class CustomerPreferencesAdmin(admin.ModelAdmin):
    """Admin interface for CustomerPreferences model."""
    
    list_display = [
        'customer',
        'tenant',
        'communication_channels',
        'notification_types',
        'preferred_language',
        'updated_at',
    ]
    
    list_filter = [
        'tenant',
        'email_enabled',
        'sms_enabled',
        'whatsapp_enabled',
        'phone_enabled',
        'preferred_language',
        'promotional_messages',
        'updated_at',
    ]
    
    search_fields = [
        'customer__name',
        'customer__surname',
        'customer__phone',
        'customer__email',
    ]
    
    readonly_fields = [
        'id',
        'created_at',
        'updated_at',
    ]
    
    fieldsets = (
        ('Customer', {
            'fields': ('customer',)
        }),
        ('Communication Channels', {
            'fields': (
                ('email_enabled', 'sms_enabled'),
                ('whatsapp_enabled', 'phone_enabled'),
            )
        }),
        ('Notification Types', {
            'fields': (
                ('purchase_confirmations', 'payment_reminders'),
                ('event_reminders', 'promotional_messages'),
                'system_updates',
            )
        }),
        ('Contact Preferences', {
            'fields': (
                ('preferred_contact_time_start', 'preferred_contact_time_end'),
                'preferred_language',
            )
        }),
        ('Metadata', {
            'fields': (
                'id',
                ('created_at', 'updated_at'),
            ),
            'classes': ('collapse',),
        }),
    )
    
    def get_queryset(self, request):
        """Filter preferences by tenant for non-admin users."""
        qs = super().get_queryset(request)
        if request.user.is_superuser or request.user.is_admin_user:
            return qs
        return qs.filter(tenant=request.user.tenant)
    
    def communication_channels(self, obj):
        """Display enabled communication channels."""
        channels = []
        if obj.email_enabled:
            channels.append('📧 Email')
        if obj.sms_enabled:
            channels.append('📱 SMS')
        if obj.whatsapp_enabled:
            channels.append('💬 WhatsApp')
        if obj.phone_enabled:
            channels.append('📞 Phone')
        
        if channels:
            return mark_safe('<br>'.join(channels))
        return 'None enabled'
    communication_channels.short_description = 'Enabled Channels'
    
    def notification_types(self, obj):
        """Display enabled notification types."""
        types = []
        if obj.purchase_confirmations:
            types.append('✅ Purchase')
        if obj.payment_reminders:
            types.append('💰 Payment')
        if obj.event_reminders:
            types.append('📅 Events')
        if obj.promotional_messages:
            types.append('🎯 Promo')
        if obj.system_updates:
            types.append('🔧 System')
        
        if types:
            return mark_safe('<br>'.join(types))
        return 'None enabled'
    notification_types.short_description = 'Notifications'