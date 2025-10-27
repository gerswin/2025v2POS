from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .models import (
    FiscalSeriesCounter,
    Transaction,
    TransactionItem,
    ReservedTicket,
    OfflineBlock
)


@admin.register(FiscalSeriesCounter)
class FiscalSeriesCounterAdmin(admin.ModelAdmin):
    """Admin interface for Fiscal Series Counter."""
    
    list_display = [
        'tenant', 'event', 'current_series', 'created_at', 'updated_at'
    ]
    list_filter = ['tenant', 'created_at']
    search_fields = ['tenant__name', 'event__name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        (None, {
            'fields': ('tenant', 'event', 'current_series')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def has_delete_permission(self, request, obj=None):
        """Prevent deletion of fiscal series counters."""
        return False


class TransactionItemInline(admin.TabularInline):
    """Inline admin for transaction items."""
    
    model = TransactionItem
    extra = 0
    readonly_fields = ['subtotal_price', 'tax_amount', 'total_price', 'created_at']
    fields = [
        'zone', 'seat', 'item_type', 'quantity', 'unit_price',
        'tax_rate', 'subtotal_price', 'tax_amount', 'total_price'
    ]
    
    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        return super().get_queryset(request).select_related('zone', 'seat')


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    """Admin interface for Transaction."""
    
    list_display = [
        'fiscal_series', 'customer_name', 'event', 'status',
        'total_amount', 'currency', 'transaction_type', 'created_at'
    ]
    list_filter = [
        'status', 'transaction_type', 'currency', 'tenant',
        'created_at', 'completed_at'
    ]
    search_fields = [
        'fiscal_series', 'customer__name', 'customer__surname',
        'customer__email', 'event__name'
    ]
    readonly_fields = [
        'id', 'fiscal_series', 'subtotal_amount', 'tax_amount',
        'total_amount', 'created_at', 'completed_at', 'updated_at'
    ]
    
    fieldsets = (
        (None, {
            'fields': (
                'id', 'tenant', 'event', 'customer', 'fiscal_series'
            )
        }),
        ('Transaction Details', {
            'fields': (
                'transaction_type', 'status', 'currency', 'exchange_rate'
            )
        }),
        ('Amounts', {
            'fields': (
                'subtotal_amount', 'tax_amount', 'total_amount'
            )
        }),
        ('Offline Sync', {
            'fields': ('offline_block_id', 'sync_status'),
            'classes': ('collapse',)
        }),
        ('Additional Information', {
            'fields': ('notes', 'metadata'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'completed_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [TransactionItemInline]
    
    def customer_name(self, obj):
        """Display customer name with link."""
        if obj.customer:
            url = reverse('admin:customers_customer_change', args=[obj.customer.pk])
            return format_html('<a href="{}">{}</a>', url, obj.customer.full_name)
        return '-'
    customer_name.short_description = 'Customer'
    customer_name.admin_order_field = 'customer__name'
    
    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        return super().get_queryset(request).select_related(
            'tenant', 'event', 'customer'
        )
    
    def has_delete_permission(self, request, obj=None):
        """Prevent deletion of completed transactions."""
        if obj and obj.status == Transaction.Status.COMPLETED:
            return False
        return super().has_delete_permission(request, obj)
    
    actions = ['complete_transactions', 'cancel_transactions']
    
    def complete_transactions(self, request, queryset):
        """Complete selected pending transactions."""
        completed = 0
        for transaction in queryset.filter(status=Transaction.Status.PENDING):
            try:
                transaction.complete()
                completed += 1
            except Exception as e:
                self.message_user(
                    request,
                    f"Error completing transaction {transaction.id}: {e}",
                    level='ERROR'
                )
        
        if completed:
            self.message_user(
                request,
                f"Successfully completed {completed} transactions."
            )
    complete_transactions.short_description = "Complete selected transactions"
    
    def cancel_transactions(self, request, queryset):
        """Cancel selected pending transactions."""
        cancelled = queryset.filter(
            status__in=[Transaction.Status.PENDING, Transaction.Status.RESERVED]
        ).update(status=Transaction.Status.CANCELLED)
        
        if cancelled:
            self.message_user(
                request,
                f"Successfully cancelled {cancelled} transactions."
            )
    cancel_transactions.short_description = "Cancel selected transactions"


@admin.register(TransactionItem)
class TransactionItemAdmin(admin.ModelAdmin):
    """Admin interface for Transaction Item."""
    
    list_display = [
        'transaction_fiscal_series', 'zone', 'seat_info', 'item_type',
        'quantity', 'unit_price', 'total_price', 'created_at'
    ]
    list_filter = ['item_type', 'zone', 'created_at']
    search_fields = [
        'transaction__fiscal_series', 'zone__name',
        'seat__row_number', 'seat__seat_number'
    ]
    readonly_fields = [
        'subtotal_price', 'tax_amount', 'total_price',
        'created_at', 'updated_at'
    ]
    
    fieldsets = (
        (None, {
            'fields': (
                'tenant', 'transaction', 'zone', 'seat', 'item_type'
            )
        }),
        ('Pricing', {
            'fields': (
                'quantity', 'unit_price', 'tax_rate',
                'subtotal_price', 'tax_amount', 'total_price'
            )
        }),
        ('Additional Information', {
            'fields': ('description', 'metadata'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def transaction_fiscal_series(self, obj):
        """Display transaction fiscal series with link."""
        if obj.transaction.fiscal_series:
            url = reverse('admin:sales_transaction_change', args=[obj.transaction.pk])
            return format_html('<a href="{}">{}</a>', url, obj.transaction.fiscal_series)
        return f"Transaction {obj.transaction.id} (Pending)"
    transaction_fiscal_series.short_description = 'Transaction'
    transaction_fiscal_series.admin_order_field = 'transaction__fiscal_series'
    
    def seat_info(self, obj):
        """Display seat information."""
        if obj.seat:
            return f"Row {obj.seat.row_number}, Seat {obj.seat.seat_number}"
        return f"General Admission (x{obj.quantity})"
    seat_info.short_description = 'Seat/Quantity'
    
    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        return super().get_queryset(request).select_related(
            'transaction', 'zone', 'seat'
        )


@admin.register(ReservedTicket)
class ReservedTicketAdmin(admin.ModelAdmin):
    """Admin interface for Reserved Ticket."""
    
    list_display = [
        'transaction_info', 'zone', 'seat_info', 'quantity',
        'status', 'reserved_until', 'is_expired_display', 'created_at'
    ]
    list_filter = ['status', 'zone', 'reserved_until', 'created_at']
    search_fields = [
        'transaction__fiscal_series', 'transaction__customer__name',
        'zone__name', 'seat__row_number', 'seat__seat_number'
    ]
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        (None, {
            'fields': (
                'tenant', 'transaction', 'zone', 'seat', 'quantity'
            )
        }),
        ('Reservation Details', {
            'fields': ('status', 'reserved_until')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def transaction_info(self, obj):
        """Display transaction information with link."""
        url = reverse('admin:sales_transaction_change', args=[obj.transaction.pk])
        if obj.transaction.fiscal_series:
            return format_html('<a href="{}">{}</a>', url, obj.transaction.fiscal_series)
        return format_html('<a href="{}">Transaction {}</a>', url, obj.transaction.id)
    transaction_info.short_description = 'Transaction'
    
    def seat_info(self, obj):
        """Display seat information."""
        if obj.seat:
            return f"Row {obj.seat.row_number}, Seat {obj.seat.seat_number}"
        return f"General Admission"
    seat_info.short_description = 'Seat'
    
    def is_expired_display(self, obj):
        """Display expiration status with color."""
        if obj.is_expired:
            return format_html('<span style="color: red;">Expired</span>')
        elif obj.is_active:
            return format_html('<span style="color: green;">Active</span>')
        return obj.get_status_display()
    is_expired_display.short_description = 'Expiration Status'
    
    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        return super().get_queryset(request).select_related(
            'transaction', 'zone', 'seat'
        )
    
    actions = ['expire_reservations', 'cancel_reservations']
    
    def expire_reservations(self, request, queryset):
        """Expire selected active reservations."""
        expired = 0
        for reservation in queryset.filter(status=ReservedTicket.Status.ACTIVE):
            reservation.expire()
            expired += 1
        
        if expired:
            self.message_user(
                request,
                f"Successfully expired {expired} reservations."
            )
    expire_reservations.short_description = "Expire selected reservations"
    
    def cancel_reservations(self, request, queryset):
        """Cancel selected active reservations."""
        cancelled = 0
        for reservation in queryset.filter(status=ReservedTicket.Status.ACTIVE):
            reservation.cancel()
            cancelled += 1
        
        if cancelled:
            self.message_user(
                request,
                f"Successfully cancelled {cancelled} reservations."
            )
    cancel_reservations.short_description = "Cancel selected reservations"


@admin.register(OfflineBlock)
class OfflineBlockAdmin(admin.ModelAdmin):
    """Admin interface for Offline Block."""
    
    list_display = [
        'block_id', 'assigned_to', 'series_range', 'used_count',
        'status', 'expires_at', 'is_expired_display', 'assigned_at'
    ]
    list_filter = ['status', 'tenant', 'assigned_at', 'expires_at']
    search_fields = ['block_id', 'assigned_to']
    readonly_fields = [
        'block_id', 'start_series', 'end_series', 'current_series',
        'assigned_at', 'synced_at'
    ]
    
    fieldsets = (
        (None, {
            'fields': (
                'tenant', 'block_id', 'assigned_to', 'status'
            )
        }),
        ('Series Range', {
            'fields': (
                'start_series', 'end_series', 'current_series'
            )
        }),
        ('Timing', {
            'fields': ('assigned_at', 'expires_at', 'synced_at')
        }),
        ('Additional Information', {
            'fields': ('metadata',),
            'classes': ('collapse',)
        }),
    )
    
    def series_range(self, obj):
        """Display series range."""
        return f"{obj.start_series} - {obj.end_series}"
    series_range.short_description = 'Series Range'
    
    def used_count(self, obj):
        """Display used series count."""
        return f"{obj.used_series} / 50"
    used_count.short_description = 'Used'
    
    def is_expired_display(self, obj):
        """Display expiration status with color."""
        if obj.is_expired:
            return format_html('<span style="color: red;">Expired</span>')
        elif obj.is_active:
            return format_html('<span style="color: green;">Active</span>')
        return obj.get_status_display()
    is_expired_display.short_description = 'Expiration Status'
    
    def has_delete_permission(self, request, obj=None):
        """Prevent deletion of synced blocks."""
        if obj and obj.status == OfflineBlock.Status.SYNCED:
            return False
        return super().has_delete_permission(request, obj)
    
    actions = ['expire_blocks', 'sync_blocks']
    
    def expire_blocks(self, request, queryset):
        """Expire selected active blocks."""
        expired = queryset.filter(status=OfflineBlock.Status.ACTIVE).update(
            status=OfflineBlock.Status.EXPIRED
        )
        
        if expired:
            self.message_user(
                request,
                f"Successfully expired {expired} blocks."
            )
    expire_blocks.short_description = "Expire selected blocks"
    
    def sync_blocks(self, request, queryset):
        """Mark selected blocks as synced."""
        synced = 0
        for block in queryset.filter(status__in=[
            OfflineBlock.Status.ACTIVE, OfflineBlock.Status.EXPIRED
        ]):
            block.sync_complete()
            synced += 1
        
        if synced:
            self.message_user(
                request,
                f"Successfully marked {synced} blocks as synced."
            )
    sync_blocks.short_description = "Mark selected blocks as synced"