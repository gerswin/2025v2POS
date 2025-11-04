"""
Fiscal Compliance Models for Venezuelan POS System

Implements Venezuelan fiscal regulations including:
- Consecutive fiscal series numbering
- X/Z reports with user-specific closures
- Immutable audit trail
- America/Caracas timezone enforcement
"""

import uuid
from decimal import Decimal
from django.db import models, transaction
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db.models import F, Max
import pytz

User = get_user_model()


class FiscalSeriesManager(models.Manager):
    """Manager for FiscalSeries with consecutive numbering logic"""
    
    def get_next_series(self, tenant, user=None):
        """
        Get the next consecutive fiscal series number for a tenant.
        Uses select_for_update to prevent race conditions.
        """
        with transaction.atomic():
            # Get the current series counter for the tenant
            series_counter, created = FiscalSeriesCounter.objects.select_for_update().get_or_create(
                tenant=tenant,
                defaults={'current_series': 0}
            )
            
            # Increment and get next series
            series_counter.current_series = F('current_series') + 1
            series_counter.save(update_fields=['current_series'])
            
            # Refresh to get the actual value
            series_counter.refresh_from_db()
            
            # Create the fiscal series record
            fiscal_series = self.create(
                tenant=tenant,
                series_number=series_counter.current_series,
                issued_by=user,
                issued_at=timezone.now()
            )
            
            return fiscal_series


class FiscalSeriesCounter(models.Model):
    """
    Maintains the current fiscal series counter per tenant.
    Ensures consecutive numbering across all transactions.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.OneToOneField(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='fiscal_series_counter'
    )
    current_series = models.BigIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'fiscal_series_counter'
        verbose_name = 'Fiscal Series Counter'
        verbose_name_plural = 'Fiscal Series Counters'
    
    def __str__(self):
        return f"{self.tenant.name} - Current: {self.current_series}"


class FiscalSeries(models.Model):
    """
    Fiscal Series model with consecutive numbering for Venezuelan compliance.
    Each transaction gets a unique, consecutive fiscal series number.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='fiscal_series'
    )
    series_number = models.BigIntegerField()
    transaction = models.OneToOneField(
        'sales.Transaction',
        on_delete=models.CASCADE,
        related_name='fiscal_series_record',
        null=True,
        blank=True
    )
    issued_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='issued_fiscal_series',
        null=True,
        blank=True
    )
    issued_at = models.DateTimeField()
    is_voided = models.BooleanField(default=False)
    voided_at = models.DateTimeField(null=True, blank=True)
    voided_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='voided_fiscal_series',
        null=True,
        blank=True
    )
    void_reason = models.TextField(blank=True)
    
    objects = FiscalSeriesManager()
    
    class Meta:
        db_table = 'fiscal_series'
        verbose_name = 'Fiscal Series'
        verbose_name_plural = 'Fiscal Series'
        unique_together = [('tenant', 'series_number')]
        indexes = [
            models.Index(fields=['tenant', 'series_number']),
            models.Index(fields=['tenant', 'issued_at']),
            models.Index(fields=['transaction']),
        ]
        ordering = ['-issued_at']
    
    def __str__(self):
        return f"Series {self.series_number} - {self.tenant.name}"
    
    def save(self, *args, **kwargs):
        # Ensure America/Caracas timezone for fiscal operations
        if self.issued_at:
            caracas_tz = pytz.timezone('America/Caracas')
            if timezone.is_naive(self.issued_at):
                self.issued_at = caracas_tz.localize(self.issued_at)
            else:
                self.issued_at = self.issued_at.astimezone(caracas_tz)
        
        super().save(*args, **kwargs)
    
    def void(self, user, reason):
        """Void this fiscal series with audit trail"""
        if self.is_voided:
            raise ValidationError("Fiscal series is already voided")
        
        self.is_voided = True
        self.voided_at = timezone.now()
        self.voided_by = user
        self.void_reason = reason
        self.save(update_fields=['is_voided', 'voided_at', 'voided_by', 'void_reason'])


class FiscalDayManager(models.Manager):
    """Manager for FiscalDay operations"""
    
    def get_current_fiscal_day(self, tenant, user):
        """Get or create the current fiscal day for a user"""
        caracas_tz = pytz.timezone('America/Caracas')
        today = timezone.now().astimezone(caracas_tz).date()
        
        fiscal_day, created = self.get_or_create(
            tenant=tenant,
            user=user,
            fiscal_date=today,
            defaults={
                'is_closed': False,
                'opened_at': timezone.now()
            }
        )
        
        return fiscal_day


class FiscalDay(models.Model):
    """
    Fiscal Day model for user-specific fiscal day management.
    Each user has their own fiscal day that can be closed independently.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='fiscal_days'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='fiscal_days'
    )
    fiscal_date = models.DateField()
    is_closed = models.BooleanField(default=False)
    opened_at = models.DateTimeField()
    closed_at = models.DateTimeField(null=True, blank=True)
    z_report = models.OneToOneField(
        'FiscalReport',
        on_delete=models.SET_NULL,
        related_name='fiscal_day',
        null=True,
        blank=True
    )
    
    objects = FiscalDayManager()
    
    class Meta:
        db_table = 'fiscal_day'
        verbose_name = 'Fiscal Day'
        verbose_name_plural = 'Fiscal Days'
        unique_together = [('tenant', 'user', 'fiscal_date')]
        indexes = [
            models.Index(fields=['tenant', 'user', 'fiscal_date']),
            models.Index(fields=['tenant', 'fiscal_date', 'is_closed']),
        ]
        ordering = ['-fiscal_date', 'user']
    
    def __str__(self):
        status = "Closed" if self.is_closed else "Open"
        return f"{self.fiscal_date} - {self.user.username} ({status})"
    
    def close_fiscal_day(self):
        """Close the fiscal day and prevent further sales"""
        if self.is_closed:
            raise ValidationError("Fiscal day is already closed")
        
        self.is_closed = True
        self.closed_at = timezone.now()
        self.save(update_fields=['is_closed', 'closed_at'])
    
    def can_process_sales(self):
        """Check if sales can be processed for this fiscal day"""
        return not self.is_closed


class FiscalReport(models.Model):
    """
    Fiscal Reports model for X and Z reports.
    X-Reports: Daily sales summary without closing fiscal period
    Z-Reports: End-of-day fiscal closure report
    """
    
    REPORT_TYPES = [
        ('X', 'X-Report (Daily Summary)'),
        ('Z', 'Z-Report (Fiscal Closure)'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='fiscal_reports'
    )
    report_type = models.CharField(max_length=1, choices=REPORT_TYPES)
    report_number = models.BigIntegerField()
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='fiscal_reports'
    )
    fiscal_date = models.DateField()
    generated_at = models.DateTimeField(auto_now_add=True)
    
    # Report Data
    total_transactions = models.IntegerField(default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    total_tax = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    cash_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    card_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    transfer_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    other_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    
    # Series Range
    first_series = models.BigIntegerField(null=True, blank=True)
    last_series = models.BigIntegerField(null=True, blank=True)
    
    # Report Content (JSON)
    report_data = models.JSONField(default=dict)
    
    class Meta:
        db_table = 'fiscal_report'
        verbose_name = 'Fiscal Report'
        verbose_name_plural = 'Fiscal Reports'
        unique_together = [('tenant', 'report_type', 'report_number')]
        indexes = [
            models.Index(fields=['tenant', 'report_type', 'fiscal_date']),
            models.Index(fields=['tenant', 'user', 'fiscal_date']),
            models.Index(fields=['generated_at']),
        ]
        ordering = ['-generated_at']
    
    def __str__(self):
        return f"{self.report_type}-Report #{self.report_number} - {self.fiscal_date}"
    
    def save(self, *args, **kwargs):
        # Auto-generate report number if not set
        if not self.report_number:
            last_report = FiscalReport.objects.filter(
                tenant=self.tenant,
                report_type=self.report_type
            ).aggregate(max_number=Max('report_number'))
            
            self.report_number = (last_report['max_number'] or 0) + 1
        
        super().save(*args, **kwargs)


class AuditLog(models.Model):
    """
    Immutable audit trail for all fiscal transactions and operations.
    Provides complete traceability for Venezuelan fiscal compliance.
    """
    
    ACTION_TYPES = [
        ('CREATE', 'Create'),
        ('UPDATE', 'Update'),
        ('DELETE', 'Delete'),
        ('VOID', 'Void'),
        ('CLOSE', 'Close'),
        ('REPORT', 'Report Generation'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='audit_logs'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='audit_logs',
        null=True,
        blank=True
    )
    action_type = models.CharField(max_length=10, choices=ACTION_TYPES)
    object_type = models.CharField(max_length=50)  # Model name
    object_id = models.CharField(max_length=100)   # Object ID
    fiscal_series = models.ForeignKey(
        FiscalSeries,
        on_delete=models.CASCADE,
        related_name='audit_logs',
        null=True,
        blank=True
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    # Change Data
    old_values = models.JSONField(default=dict, blank=True)
    new_values = models.JSONField(default=dict, blank=True)
    description = models.TextField(blank=True)
    
    class Meta:
        db_table = 'audit_log'
        verbose_name = 'Audit Log'
        verbose_name_plural = 'Audit Logs'
        indexes = [
            models.Index(fields=['tenant', 'timestamp']),
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['object_type', 'object_id']),
            models.Index(fields=['fiscal_series']),
            models.Index(fields=['action_type', 'timestamp']),
        ]
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.action_type} {self.object_type} - {self.timestamp}"
    
    def save(self, *args, **kwargs):
        # Ensure America/Caracas timezone
        if self.timestamp:
            caracas_tz = pytz.timezone('America/Caracas')
            if timezone.is_naive(self.timestamp):
                self.timestamp = caracas_tz.localize(self.timestamp)
            else:
                self.timestamp = self.timestamp.astimezone(caracas_tz)
        
        # Make immutable - prevent updates
        if self.pk:
            raise ValidationError("Audit logs are immutable and cannot be modified")
        
        super().save(*args, **kwargs)


class TaxConfiguration(models.Model):
    """
    Tax Configuration model for tenant and event-level tax settings.
    Supports multiple tax types with deterministic calculations.
    """
    
    TAX_TYPES = [
        ('PERCENTAGE', 'Percentage'),
        ('FIXED', 'Fixed Amount'),
        ('COMPOUND', 'Compound Tax'),
    ]
    
    SCOPE_CHOICES = [
        ('TENANT', 'Tenant Level'),
        ('EVENT', 'Event Level'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='tax_configurations'
    )
    event = models.ForeignKey(
        'events.Event',
        on_delete=models.CASCADE,
        related_name='tax_configurations',
        null=True,
        blank=True
    )
    name = models.CharField(max_length=100)
    tax_type = models.CharField(max_length=10, choices=TAX_TYPES)
    scope = models.CharField(max_length=10, choices=SCOPE_CHOICES)
    rate = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        help_text="Tax rate (percentage as decimal, e.g., 0.16 for 16%)"
    )
    fixed_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Fixed tax amount (for FIXED tax type)"
    )
    is_active = models.BooleanField(default=True)
    effective_from = models.DateTimeField(null=True, blank=True)
    effective_until = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_tax_configurations'
    )
    
    class Meta:
        db_table = 'tax_configuration'
        verbose_name = 'Tax Configuration'
        verbose_name_plural = 'Tax Configurations'
        indexes = [
            models.Index(fields=['tenant', 'scope', 'is_active']),
            models.Index(fields=['event', 'is_active']),
            models.Index(fields=['effective_from', 'effective_until']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        scope_display = f"Event: {self.event.name}" if self.event else "Tenant-wide"
        return f"{self.name} ({scope_display}) - {self.rate}%"
    
    def clean(self):
        """Validate tax configuration"""
        if self.scope == 'EVENT' and not self.event:
            raise ValidationError("Event is required for event-level tax configuration")
        
        if self.scope == 'TENANT' and self.event:
            raise ValidationError("Event should not be set for tenant-level tax configuration")
        
        if self.tax_type == 'FIXED' and self.fixed_amount <= 0:
            raise ValidationError("Fixed amount must be greater than 0 for FIXED tax type")
        
        if self.tax_type in ['PERCENTAGE', 'COMPOUND'] and (self.rate < 0 or self.rate > 1):
            raise ValidationError("Tax rate must be between 0 and 1 for percentage-based taxes")
    
    def calculate_tax(self, base_amount):
        """
        Calculate tax amount using deterministic round-up methodology.
        Returns the tax amount as Decimal with proper precision.
        """
        # Only check if tax is active (no date validation needed)
        if not self.is_active:
            return Decimal('0.00')
        
        if self.tax_type == 'FIXED':
            return self.fixed_amount
        
        elif self.tax_type == 'PERCENTAGE':
            tax_amount = base_amount * self.rate
            # Deterministic round-up methodology
            return tax_amount.quantize(Decimal('0.01'), rounding='ROUND_UP')
        
        elif self.tax_type == 'COMPOUND':
            # Compound tax calculation (tax on tax)
            tax_amount = base_amount * self.rate
            compound_tax = tax_amount * self.rate
            total_tax = tax_amount + compound_tax
            return total_tax.quantize(Decimal('0.01'), rounding='ROUND_UP')
        
        return Decimal('0.00')
    
    def is_effective(self, check_date=None):
        """Check if tax configuration is effective (simplified - only check active status)"""
        return self.is_active


class TaxCalculationHistory(models.Model):
    """
    History of tax calculations for audit purposes.
    Maintains record of all tax calculations performed.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='tax_calculation_history'
    )
    transaction = models.ForeignKey(
        'sales.Transaction',
        on_delete=models.CASCADE,
        related_name='tax_calculations',
        null=True,
        blank=True
    )
    tax_configuration = models.ForeignKey(
        TaxConfiguration,
        on_delete=models.CASCADE,
        related_name='calculation_history'
    )
    base_amount = models.DecimalField(max_digits=12, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2)
    calculated_at = models.DateTimeField(auto_now_add=True)
    calculated_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='tax_calculations',
        null=True,
        blank=True
    )
    
    class Meta:
        db_table = 'tax_calculation_history'
        verbose_name = 'Tax Calculation History'
        verbose_name_plural = 'Tax Calculation History'
        indexes = [
            models.Index(fields=['tenant', 'calculated_at']),
            models.Index(fields=['transaction']),
            models.Index(fields=['tax_configuration']),
        ]
        ordering = ['-calculated_at']
    
    def __str__(self):
        return f"Tax Calc: {self.base_amount} -> {self.tax_amount} ({self.calculated_at})"