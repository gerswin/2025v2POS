"""
Fiscal Compliance Services for Venezuelan POS System.

Provides business logic for:
- Fiscal series generation and management
- X/Z report generation
- Tax calculations with deterministic methodology
- Audit trail management
"""

import pytz
from decimal import Decimal, ROUND_UP
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple
from django.db import transaction
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.models import Sum, Count, Q, Max, Min

from .models import (
    FiscalSeries, FiscalDay, FiscalReport, AuditLog,
    TaxConfiguration, TaxCalculationHistory
)

User = get_user_model()


class FiscalSeriesService:
    """Service for managing fiscal series operations"""
    
    @staticmethod
    def generate_fiscal_series(tenant, user=None, transaction=None):
        """
        Generate next consecutive fiscal series for a tenant.
        Ensures thread-safe consecutive numbering.
        """
        try:
            with transaction.atomic():
                fiscal_series = FiscalSeries.objects.get_next_series(tenant, user)
                
                if transaction:
                    fiscal_series.transaction = transaction
                    fiscal_series.save(update_fields=['transaction'])
                
                # Create audit log
                AuditLogService.log_action(
                    tenant=tenant,
                    user=user,
                    action_type='CREATE',
                    object_type='FiscalSeries',
                    object_id=str(fiscal_series.id),
                    fiscal_series=fiscal_series,
                    description=f"Generated fiscal series {fiscal_series.series_number}"
                )
                
                return fiscal_series
                
        except Exception as e:
            raise ValidationError(f"Failed to generate fiscal series: {str(e)}")
    
    @staticmethod
    def void_fiscal_series(fiscal_series_id, user, reason):
        """
        Void a fiscal series with proper audit trail.
        """
        try:
            fiscal_series = FiscalSeries.objects.get(id=fiscal_series_id)
            
            if fiscal_series.is_voided:
                raise ValidationError("Fiscal series is already voided")
            
            old_values = {
                'is_voided': fiscal_series.is_voided,
                'voided_at': fiscal_series.voided_at,
                'voided_by': fiscal_series.voided_by,
                'void_reason': fiscal_series.void_reason
            }
            
            fiscal_series.void(user, reason)
            
            new_values = {
                'is_voided': fiscal_series.is_voided,
                'voided_at': fiscal_series.voided_at.isoformat() if fiscal_series.voided_at else None,
                'voided_by': fiscal_series.voided_by.username if fiscal_series.voided_by else None,
                'void_reason': fiscal_series.void_reason
            }
            
            # Create audit log
            AuditLogService.log_action(
                tenant=fiscal_series.tenant,
                user=user,
                action_type='VOID',
                object_type='FiscalSeries',
                object_id=str(fiscal_series.id),
                fiscal_series=fiscal_series,
                old_values=old_values,
                new_values=new_values,
                description=f"Voided fiscal series {fiscal_series.series_number}: {reason}"
            )
            
            return fiscal_series
            
        except FiscalSeries.DoesNotExist:
            raise ValidationError("Fiscal series not found")
        except Exception as e:
            raise ValidationError(f"Failed to void fiscal series: {str(e)}")
    
    @staticmethod
    def get_series_range_for_period(tenant, start_date, end_date):
        """Get fiscal series range for a specific period"""
        caracas_tz = pytz.timezone('America/Caracas')
        
        if isinstance(start_date, date):
            start_datetime = caracas_tz.localize(datetime.combine(start_date, datetime.min.time()))
        else:
            start_datetime = start_date.astimezone(caracas_tz)
        
        if isinstance(end_date, date):
            end_datetime = caracas_tz.localize(datetime.combine(end_date, datetime.max.time()))
        else:
            end_datetime = end_date.astimezone(caracas_tz)
        
        series_range = FiscalSeries.objects.filter(
            tenant=tenant,
            issued_at__range=(start_datetime, end_datetime),
            is_voided=False
        ).aggregate(
            first_series=Min('series_number'),
            last_series=Max('series_number'),
            total_count=Count('id')
        )
        
        return series_range


class FiscalDayService:
    """Service for managing fiscal day operations"""
    
    @staticmethod
    def get_current_fiscal_day(tenant, user):
        """Get or create current fiscal day for user"""
        return FiscalDay.objects.get_current_fiscal_day(tenant, user)
    
    @staticmethod
    def can_process_sales(tenant, user):
        """Check if sales can be processed for current fiscal day"""
        fiscal_day = FiscalDayService.get_current_fiscal_day(tenant, user)
        return fiscal_day.can_process_sales()
    
    @staticmethod
    def close_fiscal_day(tenant, user):
        """
        Close fiscal day and generate Z-Report.
        Prevents further sales until next day.
        """
        try:
            with transaction.atomic():
                fiscal_day = FiscalDayService.get_current_fiscal_day(tenant, user)
                
                if fiscal_day.is_closed:
                    raise ValidationError("Fiscal day is already closed")
                
                # Generate Z-Report before closing
                z_report = FiscalReportService.generate_z_report(
                    tenant=tenant,
                    user=user,
                    fiscal_date=fiscal_day.fiscal_date
                )
                
                # Close fiscal day
                fiscal_day.z_report = z_report
                fiscal_day.close_fiscal_day()
                
                # Create audit log
                AuditLogService.log_action(
                    tenant=tenant,
                    user=user,
                    action_type='CLOSE',
                    object_type='FiscalDay',
                    object_id=str(fiscal_day.id),
                    description=f"Closed fiscal day {fiscal_day.fiscal_date}"
                )
                
                return fiscal_day, z_report
                
        except Exception as e:
            raise ValidationError(f"Failed to close fiscal day: {str(e)}")


class FiscalReportService:
    """Service for generating fiscal reports"""
    
    @staticmethod
    def generate_x_report(tenant, user, fiscal_date=None):
        """
        Generate X-Report (daily summary without closing fiscal period).
        """
        if fiscal_date is None:
            caracas_tz = pytz.timezone('America/Caracas')
            fiscal_date = timezone.now().astimezone(caracas_tz).date()
        
        return FiscalReportService._generate_report(
            tenant=tenant,
            user=user,
            fiscal_date=fiscal_date,
            report_type='X'
        )
    
    @staticmethod
    def generate_z_report(tenant, user, fiscal_date=None):
        """
        Generate Z-Report (fiscal closure report).
        """
        if fiscal_date is None:
            caracas_tz = pytz.timezone('America/Caracas')
            fiscal_date = timezone.now().astimezone(caracas_tz).date()
        
        return FiscalReportService._generate_report(
            tenant=tenant,
            user=user,
            fiscal_date=fiscal_date,
            report_type='Z'
        )
    
    @staticmethod
    def _generate_report(tenant, user, fiscal_date, report_type):
        """Internal method to generate fiscal reports"""
        try:
            with transaction.atomic():
                # Get date range for the fiscal date
                caracas_tz = pytz.timezone('America/Caracas')
                start_datetime = caracas_tz.localize(
                    datetime.combine(fiscal_date, datetime.min.time())
                )
                end_datetime = caracas_tz.localize(
                    datetime.combine(fiscal_date, datetime.max.time())
                )
                
                # Get transactions for the period
                from venezuelan_pos.apps.sales.models import Transaction
                transactions = Transaction.objects.filter(
                    tenant=tenant,
                    created_at__range=(start_datetime, end_datetime),
                    status='COMPLETED'
                ).select_related('fiscal_series')
                
                # Calculate totals
                totals = transactions.aggregate(
                    total_amount=Sum('total_amount') or Decimal('0.00'),
                    total_tax=Sum('tax_amount') or Decimal('0.00'),
                    total_count=Count('id')
                )
                
                # Calculate payment method totals
                from venezuelan_pos.apps.payments.models import Payment
                payments = Payment.objects.filter(
                    transaction__in=transactions,
                    status='COMPLETED'
                )
                
                payment_totals = {
                    'cash_amount': Decimal('0.00'),
                    'card_amount': Decimal('0.00'),
                    'transfer_amount': Decimal('0.00'),
                    'other_amount': Decimal('0.00')
                }
                
                for payment in payments:
                    method_type = payment.payment_method.method_type.lower()
                    if method_type == 'cash':
                        payment_totals['cash_amount'] += payment.amount
                    elif method_type in ['credit_card', 'debit_card']:
                        payment_totals['card_amount'] += payment.amount
                    elif method_type in ['bank_transfer', 'wire_transfer']:
                        payment_totals['transfer_amount'] += payment.amount
                    else:
                        payment_totals['other_amount'] += payment.amount
                
                # Get fiscal series range
                series_range = FiscalSeriesService.get_series_range_for_period(
                    tenant, start_datetime, end_datetime
                )
                
                # Prepare detailed report data
                report_data = {
                    'period': {
                        'start': start_datetime.isoformat(),
                        'end': end_datetime.isoformat(),
                        'fiscal_date': fiscal_date.isoformat()
                    },
                    'transactions': {
                        'total_count': totals['total_count'],
                        'completed_count': transactions.count(),
                        'total_amount': str(totals['total_amount']),
                        'total_tax': str(totals['total_tax'])
                    },
                    'payment_methods': {
                        'cash': str(payment_totals['cash_amount']),
                        'cards': str(payment_totals['card_amount']),
                        'transfers': str(payment_totals['transfer_amount']),
                        'other': str(payment_totals['other_amount'])
                    },
                    'fiscal_series': {
                        'first': series_range.get('first_series'),
                        'last': series_range.get('last_series'),
                        'count': series_range.get('total_count', 0)
                    },
                    'generated_by': {
                        'user_id': str(user.id),
                        'username': user.username,
                        'timestamp': timezone.now().isoformat()
                    }
                }
                
                # Create fiscal report
                fiscal_report = FiscalReport.objects.create(
                    tenant=tenant,
                    report_type=report_type,
                    user=user,
                    fiscal_date=fiscal_date,
                    total_transactions=totals['total_count'],
                    total_amount=totals['total_amount'],
                    total_tax=totals['total_tax'],
                    cash_amount=payment_totals['cash_amount'],
                    card_amount=payment_totals['card_amount'],
                    transfer_amount=payment_totals['transfer_amount'],
                    other_amount=payment_totals['other_amount'],
                    first_series=series_range.get('first_series'),
                    last_series=series_range.get('last_series'),
                    report_data=report_data
                )
                
                # Create audit log
                AuditLogService.log_action(
                    tenant=tenant,
                    user=user,
                    action_type='REPORT',
                    object_type='FiscalReport',
                    object_id=str(fiscal_report.id),
                    description=f"Generated {report_type}-Report #{fiscal_report.report_number} for {fiscal_date}"
                )
                
                return fiscal_report
                
        except Exception as e:
            raise ValidationError(f"Failed to generate {report_type}-Report: {str(e)}")


class TaxCalculationService:
    """Service for tax calculations with deterministic methodology"""
    
    @staticmethod
    def get_active_tax_configurations(tenant, event=None):
        """Get active tax configurations for tenant/event"""
        # Get tenant-level taxes (simplified - only check is_active)
        tenant_taxes = TaxConfiguration.objects.filter(
            tenant=tenant,
            scope='TENANT',
            is_active=True
        )
        
        # Get event-level taxes if event is provided
        event_taxes = []
        if event:
            event_taxes = TaxConfiguration.objects.filter(
                tenant=tenant,
                event=event,
                scope='EVENT',
                is_active=True
            )
        
        return list(tenant_taxes) + list(event_taxes)
    
    @staticmethod
    def calculate_taxes(base_amount, tenant, event=None, user=None, transaction=None):
        """
        Calculate taxes using deterministic round-up methodology.
        Returns tuple of (tax_amount, tax_details, tax_history_records)
        """
        tax_configurations = TaxCalculationService.get_active_tax_configurations(tenant, event)
        
        if not tax_configurations:
            return Decimal('0.00'), [], []
        
        total_tax = Decimal('0.00')
        tax_details = []
        tax_history_records = []
        
        # Calculate each tax
        for tax_config in tax_configurations:
            tax_amount = tax_config.calculate_tax(base_amount)
            total_tax += tax_amount
            
            # Prepare tax detail
            tax_detail = {
                'configuration_id': str(tax_config.id),
                'name': tax_config.name,
                'type': tax_config.tax_type,
                'rate': str(tax_config.rate),
                'base_amount': str(base_amount),
                'tax_amount': str(tax_amount)
            }
            tax_details.append(tax_detail)
            
            # Prepare tax history record
            tax_history = TaxCalculationHistory(
                tenant=tenant,
                transaction=transaction,
                tax_configuration=tax_config,
                base_amount=base_amount,
                tax_amount=tax_amount,
                calculated_by=user
            )
            tax_history_records.append(tax_history)
        
        # Apply deterministic round-up to total
        total_tax = total_tax.quantize(Decimal('0.01'), rounding=ROUND_UP)
        
        return total_tax, tax_details, tax_history_records
    
    @staticmethod
    def save_tax_calculations(tax_history_records):
        """Save tax calculation history records"""
        if tax_history_records:
            TaxCalculationHistory.objects.bulk_create(tax_history_records)
    
    @staticmethod
    def validate_tax_configuration(tax_config):
        """Validate tax configuration before saving"""
        try:
            tax_config.clean()
            
            # Check for overlapping configurations
            overlapping = TaxConfiguration.objects.filter(
                tenant=tax_config.tenant,
                scope=tax_config.scope,
                is_active=True
            )
            
            if tax_config.event:
                overlapping = overlapping.filter(event=tax_config.event)
            else:
                overlapping = overlapping.filter(event__isnull=True)
            
            if tax_config.pk:
                overlapping = overlapping.exclude(pk=tax_config.pk)
            
            # Check for date overlaps
            for existing in overlapping:
                if TaxCalculationService._dates_overlap(
                    tax_config.effective_from, tax_config.effective_until,
                    existing.effective_from, existing.effective_until
                ):
                    raise ValidationError(
                        f"Tax configuration overlaps with existing configuration: {existing.name}"
                    )
            
            return True
            
        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError(f"Tax configuration validation failed: {str(e)}")
    
    @staticmethod
    def _dates_overlap(start1, end1, start2, end2):
        """Check if two date ranges overlap"""
        # Handle None end dates (ongoing)
        if end1 is None:
            end1 = datetime.max.replace(tzinfo=start1.tzinfo)
        if end2 is None:
            end2 = datetime.max.replace(tzinfo=start2.tzinfo)
        
        return start1 <= end2 and start2 <= end1


class AuditLogService:
    """Service for managing audit trail"""
    
    @staticmethod
    def log_action(tenant, user, action_type, object_type, object_id,
                   fiscal_series=None, old_values=None, new_values=None,
                   description="", ip_address=None, user_agent=None):
        """Create audit log entry"""
        try:
            audit_log = AuditLog.objects.create(
                tenant=tenant,
                user=user,
                action_type=action_type,
                object_type=object_type,
                object_id=object_id,
                fiscal_series=fiscal_series,
                old_values=old_values or {},
                new_values=new_values or {},
                description=description,
                ip_address=ip_address,
                user_agent=user_agent
            )
            return audit_log
            
        except Exception as e:
            # Log audit failures but don't break the main operation
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to create audit log: {str(e)}")
            return None
    
    @staticmethod
    def get_audit_trail(tenant, object_type=None, object_id=None, user=None,
                       start_date=None, end_date=None):
        """Get audit trail with filters"""
        queryset = AuditLog.objects.filter(tenant=tenant)
        
        if object_type:
            queryset = queryset.filter(object_type=object_type)
        
        if object_id:
            queryset = queryset.filter(object_id=object_id)
        
        if user:
            queryset = queryset.filter(user=user)
        
        if start_date:
            queryset = queryset.filter(timestamp__gte=start_date)
        
        if end_date:
            queryset = queryset.filter(timestamp__lte=end_date)
        
        return queryset.order_by('-timestamp')


class FiscalComplianceService:
    """Main service for fiscal compliance operations"""
    
    @staticmethod
    def process_transaction_fiscal_requirements(transaction, user):
        """
        Process all fiscal requirements for a transaction.
        This includes fiscal series generation and tax calculations.
        """
        try:
            with transaction.atomic():
                # Generate fiscal series
                fiscal_series = FiscalSeriesService.generate_fiscal_series(
                    tenant=transaction.tenant,
                    user=user,
                    transaction=transaction
                )
                
                # Calculate taxes
                tax_amount, tax_details, tax_history = TaxCalculationService.calculate_taxes(
                    base_amount=transaction.subtotal,
                    tenant=transaction.tenant,
                    event=transaction.event,
                    user=user,
                    transaction=transaction
                )
                
                # Update transaction with tax information
                transaction.tax_amount = tax_amount
                transaction.total_amount = transaction.subtotal + tax_amount
                transaction.save(update_fields=['tax_amount', 'total_amount'])
                
                # Save tax calculation history
                TaxCalculationService.save_tax_calculations(tax_history)
                
                return {
                    'fiscal_series': fiscal_series,
                    'tax_amount': tax_amount,
                    'tax_details': tax_details,
                    'total_amount': transaction.total_amount
                }
                
        except Exception as e:
            raise ValidationError(f"Fiscal compliance processing failed: {str(e)}")
    
    @staticmethod
    def validate_fiscal_day_operations(tenant, user):
        """Validate that fiscal operations can be performed"""
        if not FiscalDayService.can_process_sales(tenant, user):
            raise ValidationError(
                "Cannot process sales: Fiscal day is closed. "
                "Please start a new fiscal day to continue operations."
            )
        
        return True
    
    @staticmethod
    def get_fiscal_status(tenant, user):
        """Get current fiscal status for tenant/user"""
        fiscal_day = FiscalDayService.get_current_fiscal_day(tenant, user)
        
        # Get today's statistics
        caracas_tz = pytz.timezone('America/Caracas')
        today = timezone.now().astimezone(caracas_tz).date()
        
        from venezuelan_pos.apps.sales.models import Transaction
        today_transactions = Transaction.objects.filter(
            tenant=tenant,
            created_at__date=today,
            status='COMPLETED'
        ).aggregate(
            count=Count('id'),
            total=Sum('total_amount') or Decimal('0.00')
        )
        
        return {
            'fiscal_day': {
                'date': fiscal_day.fiscal_date,
                'is_closed': fiscal_day.is_closed,
                'opened_at': fiscal_day.opened_at,
                'closed_at': fiscal_day.closed_at
            },
            'today_stats': {
                'transactions': today_transactions['count'],
                'total_amount': today_transactions['total']
            },
            'can_process_sales': fiscal_day.can_process_sales()
        }