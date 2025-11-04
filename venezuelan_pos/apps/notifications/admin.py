"""
Django admin configuration for notifications.
"""

from django.contrib import admin
from django.utils.html import format_html
from venezuelan_pos.apps.tenants.middleware import AdminTenantMixin
from .models import NotificationTemplate, NotificationLog, NotificationPreference


@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(AdminTenantMixin, admin.ModelAdmin):
    list_display = ['name', 'template_type', 'is_active', 'created_at']
    list_filter = ['template_type', 'is_active', 'created_at']
    search_fields = ['name', 'subject', 'content']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        (None, {
            'fields': ('name', 'template_type', 'is_active')
        }),
        ('Content', {
            'fields': ('subject', 'content')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(NotificationLog)
class NotificationLogAdmin(AdminTenantMixin, admin.ModelAdmin):
    list_display = [
        'recipient', 'channel', 'status_badge', 'subject_truncated', 
        'sent_at', 'created_at'
    ]
    list_filter = ['channel', 'status', 'created_at', 'sent_at']
    search_fields = ['recipient', 'subject', 'content']
    readonly_fields = [
        'template', 'channel', 'recipient', 'subject', 'content',
        'task_id', 'sent_at', 'created_at', 'customer', 'transaction', 'event'
    ]
    
    fieldsets = (
        (None, {
            'fields': ('template', 'channel', 'recipient', 'status')
        }),
        ('Content', {
            'fields': ('subject', 'content')
        }),
        ('Status', {
            'fields': ('error_message', 'task_id', 'sent_at')
        }),
        ('Relationships', {
            'fields': ('customer', 'transaction', 'event'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def status_badge(self, obj):
        colors = {
            'pending': 'orange',
            'sent': 'green',
            'failed': 'red',
            'retry': 'blue',
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def subject_truncated(self, obj):
        if obj.subject:
            return obj.subject[:50] + '...' if len(obj.subject) > 50 else obj.subject
        return '-'
    subject_truncated.short_description = 'Subject'


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(AdminTenantMixin, admin.ModelAdmin):
    list_display = [
        'customer', 'email_enabled', 'sms_enabled', 'whatsapp_enabled',
        'purchase_confirmations', 'payment_reminders', 'event_reminders'
    ]
    list_filter = [
        'email_enabled', 'sms_enabled', 'whatsapp_enabled',
        'purchase_confirmations', 'payment_reminders', 'event_reminders',
        'promotional_messages'
    ]
    search_fields = ['customer__name', 'customer__surname', 'customer__email']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Customer', {
            'fields': ('customer',)
        }),
        ('Channel Preferences', {
            'fields': ('email_enabled', 'sms_enabled', 'whatsapp_enabled')
        }),
        ('Notification Types', {
            'fields': (
                'purchase_confirmations', 'payment_reminders', 
                'event_reminders', 'promotional_messages'
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )