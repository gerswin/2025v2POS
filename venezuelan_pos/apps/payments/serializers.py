from rest_framework import serializers
from decimal import Decimal
from django.utils import timezone
from .models import PaymentMethod, PaymentPlan, Payment, PaymentReconciliation


class PaymentMethodSerializer(serializers.ModelSerializer):
    """Serializer for PaymentMethod model."""
    
    processing_fee_display = serializers.SerializerMethodField()
    
    class Meta:
        model = PaymentMethod
        fields = [
            'id', 'method_type', 'name', 'description',
            'requires_reference', 'allows_partial',
            'processing_fee_percentage', 'processing_fee_fixed',
            'processing_fee_display', 'is_active', 'sort_order'
        ]
        read_only_fields = ['id']
    
    def get_processing_fee_display(self, obj):
        """Get human-readable processing fee display."""
        if obj.processing_fee_percentage > 0 or obj.processing_fee_fixed > 0:
            fee_parts = []
            if obj.processing_fee_percentage > 0:
                fee_parts.append(f"{obj.processing_fee_percentage * 100:.2f}%")
            if obj.processing_fee_fixed > 0:
                fee_parts.append(f"${obj.processing_fee_fixed}")
            return " + ".join(fee_parts)
        return "No fee"
    
    def validate(self, data):
        """Validate payment method data."""
        if data.get('processing_fee_percentage', 0) < 0:
            raise serializers.ValidationError({
                'processing_fee_percentage': 'Processing fee percentage cannot be negative'
            })
        
        if data.get('processing_fee_fixed', 0) < 0:
            raise serializers.ValidationError({
                'processing_fee_fixed': 'Fixed processing fee cannot be negative'
            })
        
        return data


class PaymentPlanSerializer(serializers.ModelSerializer):
    """Serializer for PaymentPlan model."""
    
    customer_name = serializers.CharField(source='customer.full_name', read_only=True)
    transaction_fiscal_series = serializers.CharField(
        source='transaction.fiscal_series', read_only=True
    )
    completion_percentage = serializers.DecimalField(
        max_digits=5, decimal_places=2, read_only=True
    )
    next_installment_amount = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )
    installments_paid = serializers.IntegerField(read_only=True)
    installments_remaining = serializers.IntegerField(read_only=True)
    is_expired = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = PaymentPlan
        fields = [
            'id', 'transaction', 'customer', 'customer_name',
            'transaction_fiscal_series', 'plan_type',
            'total_amount', 'paid_amount', 'remaining_balance',
            'installment_count', 'installment_amount',
            'next_installment_amount', 'installments_paid', 'installments_remaining',
            'completion_percentage', 'created_at', 'expires_at',
            'completed_at', 'status', 'is_expired', 'configuration', 'notes'
        ]
        read_only_fields = [
            'id', 'paid_amount', 'remaining_balance', 'completion_percentage',
            'next_installment_amount', 'installments_paid', 'installments_remaining',
            'is_expired', 'created_at', 'completed_at'
        ]
    
    def validate(self, data):
        """Validate payment plan data."""
        plan_type = data.get('plan_type')
        
        if plan_type == PaymentPlan.PlanType.INSTALLMENT:
            if not data.get('installment_count') or data['installment_count'] <= 0:
                raise serializers.ValidationError({
                    'installment_count': 'Installment count is required for installment plans'
                })
            
            if not data.get('installment_amount') or data['installment_amount'] <= 0:
                raise serializers.ValidationError({
                    'installment_amount': 'Installment amount is required for installment plans'
                })
        
        expires_at = data.get('expires_at')
        if expires_at and expires_at <= timezone.now():
            raise serializers.ValidationError({
                'expires_at': 'Expiration date must be in the future'
            })
        
        return data


class PaymentPlanCreateSerializer(serializers.Serializer):
    """Serializer for creating payment plans."""
    
    transaction_id = serializers.UUIDField()
    plan_type = serializers.ChoiceField(choices=PaymentPlan.PlanType.choices)
    installment_count = serializers.IntegerField(required=False, min_value=1)
    expires_at = serializers.DateTimeField(required=False)
    initial_payment_amount = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        min_value=Decimal('0.00')
    )
    payment_method_id = serializers.UUIDField(required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    
    def validate(self, data):
        """Validate payment plan creation data."""
        plan_type = data['plan_type']
        
        if plan_type == PaymentPlan.PlanType.INSTALLMENT:
            if 'installment_count' not in data:
                raise serializers.ValidationError({
                    'installment_count': 'Installment count is required for installment plans'
                })
        
        expires_at = data.get('expires_at')
        if expires_at and expires_at <= timezone.now():
            raise serializers.ValidationError({
                'expires_at': 'Expiration date must be in the future'
            })
        
        return data


class PaymentSerializer(serializers.ModelSerializer):
    """Serializer for Payment model."""
    
    payment_method_name = serializers.CharField(
        source='payment_method.name', read_only=True
    )
    transaction_fiscal_series = serializers.CharField(
        source='transaction.fiscal_series', read_only=True
    )
    customer_name = serializers.CharField(
        source='transaction.customer.full_name', read_only=True
    )
    
    class Meta:
        model = Payment
        fields = [
            'id', 'transaction', 'payment_method', 'payment_method_name',
            'payment_plan', 'amount', 'processing_fee', 'net_amount',
            'currency', 'exchange_rate', 'reference_number',
            'external_transaction_id', 'status', 'created_at',
            'processed_at', 'completed_at', 'transaction_fiscal_series',
            'customer_name', 'processor_response', 'metadata', 'notes'
        ]
        read_only_fields = [
            'id', 'processing_fee', 'net_amount', 'created_at',
            'processed_at', 'completed_at', 'payment_method_name',
            'transaction_fiscal_series', 'customer_name'
        ]
    
    def validate(self, data):
        """Validate payment data."""
        amount = data.get('amount')
        if amount and amount <= 0:
            raise serializers.ValidationError({
                'amount': 'Payment amount must be positive'
            })
        
        exchange_rate = data.get('exchange_rate', Decimal('1.0000'))
        if exchange_rate <= 0:
            raise serializers.ValidationError({
                'exchange_rate': 'Exchange rate must be positive'
            })
        
        # Validate payment method requires reference
        payment_method = data.get('payment_method')
        reference_number = data.get('reference_number')
        
        if (payment_method and 
            payment_method.requires_reference and 
            not reference_number):
            raise serializers.ValidationError({
                'reference_number': 'Reference number is required for this payment method'
            })
        
        return data


class PaymentCreateSerializer(serializers.Serializer):
    """Serializer for creating payments."""
    
    transaction_id = serializers.UUIDField()
    payment_method_id = serializers.UUIDField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0.01)
    currency = serializers.CharField(max_length=3, default='USD')
    exchange_rate = serializers.DecimalField(
        max_digits=10, decimal_places=4, default=Decimal('1.0000'), min_value=0.0001
    )
    reference_number = serializers.CharField(max_length=100, required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    
    def validate(self, data):
        """Validate payment creation data."""
        # Additional validation can be added here
        return data


class PaymentProcessSerializer(serializers.Serializer):
    """Serializer for processing payments."""
    
    external_transaction_id = serializers.CharField(max_length=100, required=False)
    processor_response = serializers.JSONField(required=False)
    notes = serializers.CharField(required=False, allow_blank=True)


class PaymentReconciliationSerializer(serializers.ModelSerializer):
    """Serializer for PaymentReconciliation model."""
    
    payment_method_name = serializers.CharField(
        source='payment_method.name', read_only=True
    )
    has_discrepancy = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = PaymentReconciliation
        fields = [
            'id', 'reconciliation_date', 'start_datetime', 'end_datetime',
            'payment_method', 'payment_method_name', 'system_total',
            'external_total', 'discrepancy_amount', 'has_discrepancy',
            'system_transaction_count', 'external_transaction_count',
            'status', 'created_at', 'completed_at',
            'reconciliation_data', 'notes'
        ]
        read_only_fields = [
            'id', 'discrepancy_amount', 'has_discrepancy',
            'created_at', 'completed_at', 'payment_method_name'
        ]
    
    def validate(self, data):
        """Validate reconciliation data."""
        start_datetime = data.get('start_datetime')
        end_datetime = data.get('end_datetime')
        
        if start_datetime and end_datetime and start_datetime >= end_datetime:
            raise serializers.ValidationError({
                'end_datetime': 'End datetime must be after start datetime'
            })
        
        system_total = data.get('system_total')
        if system_total and system_total < 0:
            raise serializers.ValidationError({
                'system_total': 'System total cannot be negative'
            })
        
        external_total = data.get('external_total')
        if external_total is not None and external_total < 0:
            raise serializers.ValidationError({
                'external_total': 'External total cannot be negative'
            })
        
        return data


class PaymentReconciliationCompleteSerializer(serializers.Serializer):
    """Serializer for completing payment reconciliation."""
    
    external_total = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, min_value=0
    )
    external_transaction_count = serializers.IntegerField(
        required=False, min_value=0
    )
    notes = serializers.CharField(required=False, allow_blank=True)


class PaymentSummarySerializer(serializers.Serializer):
    """Serializer for payment summary data."""
    
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_count = serializers.IntegerField()
    by_method = serializers.DictField()
    by_status = serializers.DictField()
    by_currency = serializers.DictField()
    processing_fees = serializers.DecimalField(max_digits=12, decimal_places=2)
    net_amount = serializers.DecimalField(max_digits=12, decimal_places=2)


class PaymentMethodSummarySerializer(serializers.Serializer):
    """Serializer for payment method summary data."""
    
    payment_method = PaymentMethodSerializer()
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_count = serializers.IntegerField()
    average_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    processing_fees = serializers.DecimalField(max_digits=12, decimal_places=2)
    net_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
