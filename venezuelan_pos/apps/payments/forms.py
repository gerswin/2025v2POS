"""
Forms for payment processing web interface.
"""

from django import forms
from django.core.exceptions import ValidationError
from decimal import Decimal
from datetime import date, timedelta
from django.utils import timezone

from .models import PaymentMethod, PaymentPlan, Payment, PaymentReconciliation
from venezuelan_pos.apps.events.models import EventConfiguration


class PaymentMethodForm(forms.ModelForm):
    """Form for creating/editing payment methods."""
    
    class Meta:
        model = PaymentMethod
        fields = [
            'method_type', 'name', 'description', 'requires_reference',
            'allows_partial', 'processing_fee_percentage', 'processing_fee_fixed',
            'is_active', 'sort_order'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'processing_fee_percentage': forms.NumberInput(attrs={
                'step': '0.0001',
                'min': '0',
                'placeholder': '0.0300 (for 3%)'
            }),
            'processing_fee_fixed': forms.NumberInput(attrs={
                'step': '0.01',
                'min': '0',
                'placeholder': '0.50'
            }),
            'sort_order': forms.NumberInput(attrs={'min': '0'})
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add CSS classes
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = 'form-check-input'
            else:
                field.widget.attrs['class'] = 'form-control'
        
        # Make name required and add help text
        self.fields['name'].required = True
        self.fields['processing_fee_percentage'].help_text = 'Enter as decimal (e.g., 0.03 for 3%)'
        self.fields['processing_fee_fixed'].help_text = 'Fixed fee amount in USD'


class PaymentPlanForm(forms.ModelForm):
    """Form for creating/editing payment plans."""
    
    initial_payment_amount = forms.DecimalField(
        required=False,
        min_value=Decimal('0.00'),
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
        })
    )
    payment_method = forms.ModelChoiceField(
        queryset=PaymentMethod.objects.none(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        empty_label='Select payment method'
    )
    
    class Meta:
        model = PaymentPlan
        fields = [
            'plan_type', 'installment_count', 'expires_at', 'notes'
        ]
        widgets = {
            'expires_at': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'form-control'
            }),
            'notes': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'installment_count': forms.NumberInput(attrs={
                'min': '1',
                'max': '12',
                'class': 'form-control'
            })
        }
    
    def __init__(self, *args, **kwargs):
        self.tenant = kwargs.pop('tenant', None)
        self.transaction = kwargs.pop('transaction', None)
        super().__init__(*args, **kwargs)
        
        # Add CSS classes
        self.fields['plan_type'].widget.attrs['class'] = 'form-select'
        self.fields['installment_count'].required = False
        self.fields['expires_at'].required = False
        self.fields['notes'].widget.attrs.setdefault('class', 'form-control')
        
        # Configure payment methods
        if self.tenant:
            self.fields['payment_method'].queryset = PaymentMethod.objects.filter(
                tenant=self.tenant,
                is_active=True,
                allows_partial=True
            ).order_by('sort_order', 'name')
        
        event_config = self._get_event_config()
        min_percentage = event_config.min_down_payment_percentage if event_config else Decimal('0.00')
        min_help = (
            f"Minimum deposit {min_percentage}% of total "
            if min_percentage else "Optional initial payment (defaults to 0)"
        )
        self.fields['initial_payment_amount'].help_text = min_help
        self.fields['installment_count'].help_text = (
            f"Number of equal payments (max {event_config.max_installments})"
            if event_config else 'Number of equal payments'
        )
        self.fields['expires_at'].help_text = (
            f"Plan expiry (defaults to +{event_config.payment_plan_expiry_days} days)"
            if event_config else 'Plan expiry date and time'
        )
        
        if not self.initial.get('expires_at') and event_config:
            default_expiry = timezone.now() + timedelta(days=event_config.payment_plan_expiry_days or 1)
            self.initial['expires_at'] = default_expiry.strftime('%Y-%m-%dT%H:%M')
    
    def _get_event_config(self):
        if not self.transaction:
            return None
        try:
            return EventConfiguration.objects.get(event=self.transaction.event)
        except EventConfiguration.DoesNotExist:
            return None
    
    def clean(self):
        cleaned_data = super().clean()
        plan_type = cleaned_data.get('plan_type')
        installment_count = cleaned_data.get('installment_count') or 0
        initial_payment = cleaned_data.get('initial_payment_amount')
        payment_method = cleaned_data.get('payment_method')
        expires_at = cleaned_data.get('expires_at')
        
        event_config = self._get_event_config()
        if not event_config:
            raise ValidationError("This event has no configuration for partial payments.")
        
        if not event_config.partial_payments_enabled:
            raise ValidationError("Partial payments are not enabled for this event.")
        
        if plan_type == PaymentPlan.PlanType.INSTALLMENT:
            if not event_config.installment_plans_enabled:
                raise ValidationError("Installment plans are not enabled for this event.")
            max_installments = event_config.max_installments or 1
            if installment_count < 1 or installment_count > max_installments:
                raise ValidationError({
                    'installment_count': f'Installments must be between 1 and {max_installments}.'
                })
        else:
            if not event_config.flexible_payments_enabled:
                raise ValidationError("Flexible plans are not enabled for this event.")
        
        if initial_payment and initial_payment > self.transaction.total_amount:
            self.add_error('initial_payment_amount', 'Initial payment cannot exceed total amount.')
        
        min_percentage = event_config.min_down_payment_percentage or Decimal('0.00')
        if min_percentage:
            min_required = self.transaction.total_amount * (min_percentage / Decimal('100'))
            if not initial_payment or initial_payment < min_required:
                self.add_error(
                    'initial_payment_amount',
                    f'Initial payment must be at least {min_percentage}% ({min_required:.2f}).'
                )
        
        if expires_at and expires_at <= timezone.now():
            self.add_error('expires_at', 'Expiry must be in the future.')
        
        if initial_payment and not payment_method:
            self.add_error('payment_method', 'Select a payment method for the initial payment.')
        
        if payment_method and not payment_method.allows_partial:
            self.add_error('payment_method', 'Selected payment method does not allow partial payments.')
        
        return cleaned_data


class PaymentForm(forms.ModelForm):
    """Form for creating payments."""

    currency = forms.ChoiceField(
        choices=[
            ('USD', 'USD - US Dollar'),
            ('VES', 'VES - Venezuelan Bolívar'),
            ('EUR', 'EUR - Euro')
        ],
        initial='USD',
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = Payment
        fields = [
            'payment_method', 'amount', 'currency', 'reference_number', 'notes'
        ]
        widgets = {
            'amount': forms.NumberInput(attrs={
                'step': '0.01',
                'min': '0.01',
                'class': 'form-control'
            }),
            'reference_number': forms.TextInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'})
        }
    
    def __init__(self, *args, **kwargs):
        tenant = kwargs.pop('tenant', None)
        super().__init__(*args, **kwargs)

        # Filter payment methods by tenant
        if tenant:
            self.fields['payment_method'].queryset = PaymentMethod.objects.filter(
                tenant=tenant,
                is_active=True
            ).order_by('sort_order', 'name')

        # Add CSS classes
        self.fields['payment_method'].widget.attrs['class'] = 'form-select'

        # Help text
        self.fields['reference_number'].help_text = 'Bank reference, card authorization, etc.'
        self.fields['amount'].help_text = 'Payment amount'
    
    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount and amount <= 0:
            raise ValidationError('Amount must be positive')
        return amount


class PaymentSearchForm(forms.Form):
    """Form for searching payments."""
    
    STATUS_CHOICES = [('', 'All Statuses')] + Payment.Status.choices
    
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    payment_method = forms.ModelChoiceField(
        queryset=PaymentMethod.objects.none(),
        required=False,
        empty_label='All Payment Methods',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        })
    )
    
    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        })
    )
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by reference, transaction, customer...'
        })
    )
    
    def __init__(self, *args, **kwargs):
        tenant = kwargs.pop('tenant', None)
        super().__init__(*args, **kwargs)
        
        if tenant:
            self.fields['payment_method'].queryset = PaymentMethod.objects.filter(
                tenant=tenant,
                is_active=True
            ).order_by('sort_order', 'name')


class PaymentReconciliationForm(forms.ModelForm):
    """Form for creating payment reconciliations."""
    
    class Meta:
        model = PaymentReconciliation
        fields = ['payment_method', 'reconciliation_date']
        widgets = {
            'reconciliation_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            })
        }
    
    def __init__(self, *args, **kwargs):
        tenant = kwargs.pop('tenant', None)
        super().__init__(*args, **kwargs)
        
        # Filter payment methods by tenant
        if tenant:
            self.fields['payment_method'].queryset = PaymentMethod.objects.filter(
                tenant=tenant,
                is_active=True
            ).order_by('sort_order', 'name')
        
        # Add CSS classes
        self.fields['payment_method'].widget.attrs['class'] = 'form-select'
        
        # Default to today
        self.fields['reconciliation_date'].initial = date.today()
        
        # Help text
        self.fields['reconciliation_date'].help_text = 'Date to reconcile payments for'
    
    def clean_reconciliation_date(self):
        reconciliation_date = self.cleaned_data.get('reconciliation_date')
        
        if reconciliation_date and reconciliation_date > date.today():
            raise ValidationError('Cannot reconcile future dates')
        
        return reconciliation_date


class PaymentReconciliationCompleteForm(forms.Form):
    """Form for completing payment reconciliation."""
    
    external_total = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'step': '0.01',
            'min': '0',
            'class': 'form-control'
        }),
        help_text='Total amount from external records (bank, processor)'
    )
    
    external_transaction_count = forms.IntegerField(
        min_value=0,
        widget=forms.NumberInput(attrs={
            'min': '0',
            'class': 'form-control'
        }),
        help_text='Number of transactions in external records'
    )
    
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'rows': 3,
            'class': 'form-control',
            'placeholder': 'Reconciliation notes and comments...'
        })
    )


class PaymentProcessForm(forms.Form):
    """Form for processing payments."""
    
    external_transaction_id = forms.CharField(
        required=False,
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'External transaction ID from processor'
        })
    )
    
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'rows': 3,
            'class': 'form-control',
            'placeholder': 'Processing notes...'
        })
    )


class PaymentRefundForm(forms.Form):
    """Form for processing payment refunds."""
    
    refund_amount = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0.01,
        required=False,
        widget=forms.NumberInput(attrs={
            'step': '0.01',
            'min': '0.01',
            'class': 'form-control'
        }),
        help_text='Leave empty for full refund'
    )
    
    reason = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 3,
            'class': 'form-control',
            'placeholder': 'Reason for refund...'
        }),
        help_text='Reason for the refund'
    )
    
    def __init__(self, *args, **kwargs):
        max_amount = kwargs.pop('max_amount', None)
        super().__init__(*args, **kwargs)
        
        if max_amount:
            self.fields['refund_amount'].widget.attrs['max'] = str(max_amount)
            self.fields['refund_amount'].help_text = f'Maximum refund: {max_amount}. Leave empty for full refund.'
    
    def clean_refund_amount(self):
        refund_amount = self.cleaned_data.get('refund_amount')
        max_amount = getattr(self, 'max_amount', None)
        
        if refund_amount and max_amount and refund_amount > max_amount:
            raise ValidationError(f'Refund amount cannot exceed {max_amount}')
        
        return refund_amount
