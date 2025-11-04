from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import PaymentMethod, PaymentPlan, Payment, PaymentReconciliation


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    """Admin interface for PaymentMethod model."""
    
    list_display = [
        'name', 'method_type', 'tenant', 'is_active', 
        'allows_partial', 'processing_fee_display', 'sort_order'
    ]
    list_filter = ['method_type', 'is_active', 'allows_partial', 'tenant']
    search_fields = ['name', 'description']
    ordering = ['tenant', 'sort_order', 'name']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('tenant', 'method_type', 'name', 'description')
        }),
        ('Configuration', {
            'fields': (
                'requires_reference', 'allows_partial', 
                'processing_fee_percentage', 'processing_fee_fixed'
            )
        }),
        ('Display Settings', {
            'fields': ('is_active', 'sort_order')
        }),
        ('Advanced Configuration', {
            'fields': ('configuration',),
            'classes': ('collapse',)
        })
    )
    
    def processing_fee_display(self, obj):
        """Display processing fee information."""
        if obj.processing_fee_percentage > 0 or obj.processing_fee_fixed > 0:
            fee_parts = []
            if obj.processing_fee_percentage > 0:
                fee_parts.append(f"{obj.processing_fee_percentage * 100:.2f}%")
            if obj.processing_fee_fixed > 0:
                fee_parts.append(f"${obj.processing_fee_fixed}")
            return " + ".join(fee_parts)
        return "No fee"
    processing_fee_display.short_description = "Processing Fee"
    
    def get_queryset(self, request):
        """Filter by tenant if user is not superuser."""
        qs = super().get_queryset(request)
        if not request.user.is_superuser and hasattr(request.user, 'tenant'):
            qs = qs.filter(tenant=request.user.tenant)
        return qs


@admin.register(PaymentPlan)
class PaymentPlanAdmin(admin.ModelAdmin):
    """Admin interface for PaymentPlan model."""
    
    list_display = [
        'transaction_link', 'customer', 'plan_type', 'status',
        'total_amount', 'paid_amount', 'remaining_balance',
        'completion_percentage_display', 'expires_at'
    ]
    list_filter = ['plan_type', 'status', 'tenant', 'created_at']
    search_fields = ['customer__name', 'customer__surname', 'customer__email']
    readonly_fields = [
        'transaction', 'customer', 'total_amount', 'paid_amount', 
        'remaining_balance', 'completion_percentage_display', 'created_at'
    ]
    ordering = ['-created_at']
    
    fieldsets = (
        ('Plan Information', {
            'fields': (
                'transaction', 'customer', 'plan_type', 'status'
            )
        }),
        ('Amounts', {
            'fields': (
                'total_amount', 'paid_amount', 'remaining_balance',
                'completion_percentage_display'
            )
        }),
        ('Installment Details', {
            'fields': ('installment_count', 'installment_amount'),
            'classes': ('collapse',)
        }),
        ('Timing', {
            'fields': ('created_at', 'expires_at', 'completed_at')
        }),
        ('Additional Information', {
            'fields': ('configuration', 'notes'),
            'classes': ('collapse',)
        })
    )
    
    def transaction_link(self, obj):
        """Create link to transaction."""
        if obj.transaction:
            url = reverse('admin:sales_transaction_change', args=[obj.transaction.pk])
            return format_html('<a href="{}">{}</a>', url, str(obj.transaction))
        return "-"
    transaction_link.short_description = "Transaction"
    
    def completion_percentage_display(self, obj):
        """Display completion percentage with progress bar."""
        percentage = obj.completion_percentage
        color = 'green' if percentage >= 100 else 'orange' if percentage >= 50 else 'red'
        return format_html(
            '<div style="width: 100px; background-color: #f0f0f0; border-radius: 3px;">'
            '<div style="width: {}%; background-color: {}; height: 20px; border-radius: 3px; '
            'text-align: center; color: white; font-size: 12px; line-height: 20px;">'
            '{:.1f}%</div></div>',
            min(percentage, 100), color, percentage
        )
    completion_percentage_display.short_description = "Completion"
    
    def get_queryset(self, request):
        """Filter by tenant and optimize queries."""
        qs = super().get_queryset(request)
        qs = qs.select_related('transaction', 'customer', 'tenant')
        if not request.user.is_superuser and hasattr(request.user, 'tenant'):
            qs = qs.filter(tenant=request.user.tenant)
        return qs


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    """Admin interface for Payment model."""
    
    list_display = [
        'id', 'transaction_link', 'payment_method', 'amount_display',
        'status', 'reference_number', 'created_at', 'completed_at'
    ]
    list_filter = [
        'status', 'payment_method', 'currency', 'tenant', 'created_at'
    ]
    search_fields = [
        'reference_number', 'external_transaction_id',
        'transaction__fiscal_series', 'transaction__customer__name'
    ]
    readonly_fields = [
        'id', 'transaction', 'net_amount', 'processing_fee',
        'created_at', 'processed_at', 'completed_at'
    ]
    ordering = ['-created_at']
    
    fieldsets = (
        ('Payment Information', {
            'fields': (
                'id', 'transaction', 'payment_method', 'payment_plan'
            )
        }),
        ('Amounts', {
            'fields': (
                'amount', 'processing_fee', 'net_amount', 'currency', 'exchange_rate'
            )
        }),
        ('Reference Information', {
            'fields': ('reference_number', 'external_transaction_id')
        }),
        ('Status and Timing', {
            'fields': (
                'status', 'created_at', 'processed_at', 'completed_at'
            )
        }),
        ('Additional Data', {
            'fields': ('processor_response', 'metadata', 'notes'),
            'classes': ('collapse',)
        })
    )
    
    def transaction_link(self, obj):
        """Create link to transaction."""
        if obj.transaction:
            url = reverse('admin:sales_transaction_change', args=[obj.transaction.pk])
            fiscal_series = obj.transaction.fiscal_series or 'Pending'
            return format_html('<a href="{}">{}</a>', url, fiscal_series)
        return "-"
    transaction_link.short_description = "Transaction"
    
    def amount_display(self, obj):
        """Display amount with currency and processing fee."""
        fee_info = f" (Fee: {obj.processing_fee})" if obj.processing_fee > 0 else ""
        return f"{obj.amount} {obj.currency}{fee_info}"
    amount_display.short_description = "Amount"
    
    def get_queryset(self, request):
        """Filter by tenant and optimize queries."""
        qs = super().get_queryset(request)
        qs = qs.select_related('transaction', 'payment_method', 'payment_plan', 'tenant')
        if not request.user.is_superuser and hasattr(request.user, 'tenant'):
            qs = qs.filter(tenant=request.user.tenant)
        return qs
    
    actions = ['mark_as_completed', 'mark_as_failed']
    
    def mark_as_completed(self, request, queryset):
        """Mark selected payments as completed."""
        updated = 0
        for payment in queryset.filter(status__in=['pending', 'processing']):
            try:
                payment.mark_completed()
                updated += 1
            except Exception as e:
                self.message_user(
                    request, 
                    f"Error completing payment {payment.id}: {str(e)}", 
                    level='ERROR'
                )
        
        if updated:
            self.message_user(
                request, 
                f"Successfully marked {updated} payments as completed."
            )
    mark_as_completed.short_description = "Mark selected payments as completed"
    
    def mark_as_failed(self, request, queryset):
        """Mark selected payments as failed."""
        updated = 0
        for payment in queryset.filter(status__in=['pending', 'processing']):
            try:
                payment.mark_failed("Manually marked as failed by admin")
                updated += 1
            except Exception as e:
                self.message_user(
                    request, 
                    f"Error failing payment {payment.id}: {str(e)}", 
                    level='ERROR'
                )
        
        if updated:
            self.message_user(
                request, 
                f"Successfully marked {updated} payments as failed."
            )
    mark_as_failed.short_description = "Mark selected payments as failed"


@admin.register(PaymentReconciliation)
class PaymentReconciliationAdmin(admin.ModelAdmin):
    """Admin interface for PaymentReconciliation model."""
    
    list_display = [
        'reconciliation_date', 'payment_method', 'status',
        'system_total', 'external_total', 'discrepancy_display',
        'system_transaction_count', 'completed_at'
    ]
    list_filter = ['status', 'payment_method', 'tenant', 'reconciliation_date']
    search_fields = ['payment_method__name', 'notes']
    readonly_fields = [
        'discrepancy_amount', 'created_at', 'completed_at'
    ]
    ordering = ['-reconciliation_date', '-created_at']
    
    fieldsets = (
        ('Reconciliation Information', {
            'fields': (
                'reconciliation_date', 'payment_method', 'status'
            )
        }),
        ('Period', {
            'fields': ('start_datetime', 'end_datetime')
        }),
        ('System Records', {
            'fields': ('system_total', 'system_transaction_count')
        }),
        ('External Records', {
            'fields': ('external_total', 'external_transaction_count')
        }),
        ('Discrepancy', {
            'fields': ('discrepancy_amount',)
        }),
        ('Timing', {
            'fields': ('created_at', 'completed_at')
        }),
        ('Additional Data', {
            'fields': ('reconciliation_data', 'notes'),
            'classes': ('collapse',)
        })
    )
    
    def discrepancy_display(self, obj):
        """Display discrepancy with color coding."""
        if obj.discrepancy_amount == 0:
            return format_html(
                '<span style="color: green; font-weight: bold;">No Discrepancy</span>'
            )
        else:
            return format_html(
                '<span style="color: red; font-weight: bold;">${}</span>',
                obj.discrepancy_amount
            )
    discrepancy_display.short_description = "Discrepancy"
    
    def get_queryset(self, request):
        """Filter by tenant and optimize queries."""
        qs = super().get_queryset(request)
        qs = qs.select_related('payment_method', 'tenant')
        if not request.user.is_superuser and hasattr(request.user, 'tenant'):
            qs = qs.filter(tenant=request.user.tenant)
        return qs
    
    actions = ['recalculate_system_totals', 'mark_as_completed']
    
    def recalculate_system_totals(self, request, queryset):
        """Recalculate system totals for selected reconciliations."""
        updated = 0
        for reconciliation in queryset:
            try:
                reconciliation.calculate_system_totals()
                reconciliation.save()
                updated += 1
            except Exception as e:
                self.message_user(
                    request, 
                    f"Error recalculating {reconciliation}: {str(e)}", 
                    level='ERROR'
                )
        
        if updated:
            self.message_user(
                request, 
                f"Successfully recalculated {updated} reconciliations."
            )
    recalculate_system_totals.short_description = "Recalculate system totals"
    
    def mark_as_completed(self, request, queryset):
        """Mark selected reconciliations as completed."""
        updated = 0
        for reconciliation in queryset.filter(status__in=['pending', 'in_progress']):
            try:
                reconciliation.complete_reconciliation()
                updated += 1
            except Exception as e:
                self.message_user(
                    request, 
                    f"Error completing {reconciliation}: {str(e)}", 
                    level='ERROR'
                )
        
        if updated:
            self.message_user(
                request, 
                f"Successfully completed {updated} reconciliations."
            )
    mark_as_completed.short_description = "Mark selected reconciliations as completed"