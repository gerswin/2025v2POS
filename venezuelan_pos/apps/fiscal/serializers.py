"""
Serializers for Fiscal Compliance API endpoints.
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    FiscalSeries, FiscalDay, FiscalReport, AuditLog,
    TaxConfiguration, TaxCalculationHistory
)

User = get_user_model()


class FiscalSeriesSerializer(serializers.ModelSerializer):
    """Serializer for Fiscal Series"""
    
    issued_by_username = serializers.CharField(source='issued_by.username', read_only=True)
    voided_by_username = serializers.CharField(source='voided_by.username', read_only=True)
    transaction_id = serializers.CharField(source='transaction.id', read_only=True)
    
    class Meta:
        model = FiscalSeries
        fields = [
            'id', 'series_number', 'transaction_id', 'issued_by_username',
            'issued_at', 'is_voided', 'voided_at', 'voided_by_username',
            'void_reason'
        ]
        read_only_fields = [
            'id', 'series_number', 'transaction_id', 'issued_by_username',
            'issued_at', 'voided_at', 'voided_by_username'
        ]


class FiscalDaySerializer(serializers.ModelSerializer):
    """Serializer for Fiscal Day"""
    
    user_username = serializers.CharField(source='user.username', read_only=True)
    z_report_number = serializers.IntegerField(source='z_report.report_number', read_only=True)
    
    class Meta:
        model = FiscalDay
        fields = [
            'id', 'user_username', 'fiscal_date', 'is_closed',
            'opened_at', 'closed_at', 'z_report_number'
        ]
        read_only_fields = [
            'id', 'user_username', 'opened_at', 'closed_at', 'z_report_number'
        ]


class FiscalReportSerializer(serializers.ModelSerializer):
    """Serializer for Fiscal Reports"""
    
    user_username = serializers.CharField(source='user.username', read_only=True)
    report_type_display = serializers.CharField(source='get_report_type_display', read_only=True)
    
    class Meta:
        model = FiscalReport
        fields = [
            'id', 'report_type', 'report_type_display', 'report_number',
            'user_username', 'fiscal_date', 'generated_at',
            'total_transactions', 'total_amount', 'total_tax',
            'cash_amount', 'card_amount', 'transfer_amount', 'other_amount',
            'first_series', 'last_series', 'report_data'
        ]
        read_only_fields = [
            'id', 'report_number', 'user_username', 'generated_at',
            'total_transactions', 'total_amount', 'total_tax',
            'cash_amount', 'card_amount', 'transfer_amount', 'other_amount',
            'first_series', 'last_series', 'report_data'
        ]


class FiscalReportCreateSerializer(serializers.Serializer):
    """Serializer for creating fiscal reports"""
    
    report_type = serializers.ChoiceField(choices=FiscalReport.REPORT_TYPES)
    fiscal_date = serializers.DateField(required=False)
    
    def validate_report_type(self, value):
        """Validate report type"""
        if value not in ['X', 'Z']:
            raise serializers.ValidationError("Report type must be 'X' or 'Z'")
        return value


class AuditLogSerializer(serializers.ModelSerializer):
    """Serializer for Audit Logs"""
    
    user_username = serializers.CharField(source='user.username', read_only=True)
    fiscal_series_number = serializers.IntegerField(source='fiscal_series.series_number', read_only=True)
    action_type_display = serializers.CharField(source='get_action_type_display', read_only=True)
    
    class Meta:
        model = AuditLog
        fields = [
            'id', 'user_username', 'action_type', 'action_type_display',
            'object_type', 'object_id', 'fiscal_series_number',
            'timestamp', 'ip_address', 'description'
        ]
        read_only_fields = fields


class TaxConfigurationSerializer(serializers.ModelSerializer):
    """Serializer for Tax Configuration"""
    
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    event_name = serializers.CharField(source='event.name', read_only=True)
    tax_type_display = serializers.CharField(source='get_tax_type_display', read_only=True)
    scope_display = serializers.CharField(source='get_scope_display', read_only=True)
    
    class Meta:
        model = TaxConfiguration
        fields = [
            'id', 'name', 'tax_type', 'tax_type_display', 'scope', 'scope_display',
            'event', 'event_name', 'rate', 'fixed_amount', 'is_active',
            'effective_from', 'effective_until', 'created_at', 'updated_at',
            'created_by_username'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'created_by_username',
            'event_name', 'tax_type_display', 'scope_display'
        ]
    
    def validate(self, data):
        """Validate tax configuration data"""
        # Import here to avoid circular imports
        from .services import TaxCalculationService
        
        # Create a temporary instance for validation
        instance = TaxConfiguration(**data)
        if self.instance:
            instance.pk = self.instance.pk
        
        TaxCalculationService.validate_tax_configuration(instance)
        return data


class TaxCalculationHistorySerializer(serializers.ModelSerializer):
    """Serializer for Tax Calculation History"""
    
    calculated_by_username = serializers.CharField(source='calculated_by.username', read_only=True)
    transaction_id = serializers.CharField(source='transaction.id', read_only=True)
    tax_configuration_name = serializers.CharField(source='tax_configuration.name', read_only=True)
    
    class Meta:
        model = TaxCalculationHistory
        fields = [
            'id', 'transaction_id', 'tax_configuration_name',
            'base_amount', 'tax_amount', 'calculated_at',
            'calculated_by_username'
        ]
        read_only_fields = fields


class TaxCalculationRequestSerializer(serializers.Serializer):
    """Serializer for tax calculation requests"""
    
    base_amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0)
    event_id = serializers.UUIDField(required=False, allow_null=True)
    
    def validate_base_amount(self, value):
        """Validate base amount"""
        if value <= 0:
            raise serializers.ValidationError("Base amount must be greater than 0")
        return value


class TaxCalculationResponseSerializer(serializers.Serializer):
    """Serializer for tax calculation responses"""
    
    base_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    tax_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    tax_details = serializers.ListField(child=serializers.DictField())


class FiscalStatusSerializer(serializers.Serializer):
    """Serializer for fiscal status responses"""
    
    fiscal_day = serializers.DictField()
    today_stats = serializers.DictField()
    can_process_sales = serializers.BooleanField()


class VoidFiscalSeriesSerializer(serializers.Serializer):
    """Serializer for voiding fiscal series"""
    
    reason = serializers.CharField(max_length=500, required=True)
    
    def validate_reason(self, value):
        """Validate void reason"""
        if not value.strip():
            raise serializers.ValidationError("Void reason is required")
        return value.strip()


class CloseFiscalDaySerializer(serializers.Serializer):
    """Serializer for closing fiscal day"""
    
    confirm = serializers.BooleanField(default=False)
    
    def validate_confirm(self, value):
        """Validate confirmation"""
        if not value:
            raise serializers.ValidationError("Confirmation is required to close fiscal day")
        return value