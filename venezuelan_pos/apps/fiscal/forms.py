"""
Forms for Fiscal Compliance web interface.
"""

from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import TaxConfiguration, FiscalReport
from .services import TaxCalculationService


class TaxConfigurationForm(forms.ModelForm):
    """Form for creating and editing tax configurations"""
    
    class Meta:
        model = TaxConfiguration
        fields = [
            'name', 'tax_type', 'scope', 'event', 'rate', 'fixed_amount',
            'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter tax name (e.g., VAT, Service Fee)'
            }),
            'tax_type': forms.Select(attrs={'class': 'form-select'}),
            'scope': forms.Select(attrs={'class': 'form-select'}),
            'event': forms.Select(attrs={'class': 'form-select'}),
            'rate': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.0001',
                'min': '0',
                'max': '1',
                'placeholder': '0.16 (for 16%)'
            }),
            'fixed_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'placeholder': '5.00'
            }),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.tenant = kwargs.pop('tenant', None)
        super().__init__(*args, **kwargs)
        
        # Filter events by tenant
        if self.tenant:
            self.fields['event'].queryset = self.tenant.event_set.all()
    
    def clean(self):
        """Validate tax configuration"""
        cleaned_data = super().clean()
        
        # Validate tax configuration using service
        if self.tenant:
            temp_instance = TaxConfiguration(**cleaned_data)
            temp_instance.tenant = self.tenant
            if self.instance.pk:
                temp_instance.pk = self.instance.pk
            
            try:
                TaxCalculationService.validate_tax_configuration(temp_instance)
            except ValidationError as e:
                raise ValidationError(str(e))
        
        return cleaned_data
    
    def clean_rate(self):
        """Validate tax rate"""
        rate = self.cleaned_data.get('rate')
        tax_type = self.cleaned_data.get('tax_type')
        
        if tax_type in ['PERCENTAGE', 'COMPOUND'] and rate is not None:
            if rate < 0 or rate > 1:
                raise ValidationError("Tax rate must be between 0 and 1 for percentage-based taxes")
        
        return rate
    
    def clean_fixed_amount(self):
        """Validate fixed amount"""
        fixed_amount = self.cleaned_data.get('fixed_amount')
        tax_type = self.cleaned_data.get('tax_type')
        
        if tax_type == 'FIXED' and (fixed_amount is None or fixed_amount <= 0):
            raise ValidationError("Fixed amount must be greater than 0 for FIXED tax type")
        
        return fixed_amount
    
    def save(self, commit=True):
        """Save tax configuration with automatic date handling"""
        instance = super().save(commit=False)
        
        # Always set effective_from to now for new instances
        if not instance.pk:
            instance.effective_from = timezone.now()
        
        # Ensure effective_from is set even for existing instances if somehow None
        if instance.effective_from is None:
            instance.effective_from = timezone.now()
        
        # Leave effective_until as None (ongoing tax)
        instance.effective_until = None
        
        if commit:
            instance.save()
        
        return instance


class FiscalReportGenerationForm(forms.Form):
    """Form for generating fiscal reports"""
    
    REPORT_TYPE_CHOICES = [
        ('X', 'X-Report (Daily Summary)'),
        ('Z', 'Z-Report (Fiscal Closure)'),
    ]
    
    report_type = forms.ChoiceField(
        choices=REPORT_TYPE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text="X-Report: Daily summary without closing fiscal period. Z-Report: End-of-day fiscal closure."
    )
    
    fiscal_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        help_text="Leave empty to use today's date"
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set default fiscal_date to today
        if not self.initial.get('fiscal_date'):
            self.fields['fiscal_date'].initial = timezone.now().date()


class TaxCalculationForm(forms.Form):
    """Form for calculating taxes on a base amount"""
    
    base_amount = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'min': '0',
            'placeholder': '100.00'
        }),
        help_text="Enter the base amount to calculate taxes"
    )
    
    event = forms.ModelChoiceField(
        queryset=None,
        required=False,
        empty_label="No specific event (tenant-level taxes only)",
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text="Select an event to include event-specific taxes"
    )
    
    def __init__(self, *args, **kwargs):
        tenant = kwargs.pop('tenant', None)
        super().__init__(*args, **kwargs)
        
        # Filter events by tenant
        if tenant:
            self.fields['event'].queryset = tenant.event_set.filter(
                status__in=['draft', 'active']
            )


class FiscalDayClosureForm(forms.Form):
    """Form for closing fiscal day"""
    
    confirm = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label="I confirm that I want to close the fiscal day",
        help_text="This action cannot be undone. No more sales can be processed until the next fiscal day."
    )
    
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Optional notes about the fiscal day closure...'
        }),
        help_text="Optional notes about the fiscal day closure"
    )


class VoidFiscalSeriesForm(forms.Form):
    """Form for voiding fiscal series"""
    
    reason = forms.CharField(
        max_length=500,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Enter the reason for voiding this fiscal series...'
        }),
        help_text="Provide a detailed reason for voiding this fiscal series"
    )
    
    confirm = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label="I confirm that I want to void this fiscal series",
        help_text="This action cannot be undone."
    )


class FiscalComplianceSearchForm(forms.Form):
    """Form for searching fiscal compliance records"""
    
    SEARCH_TYPE_CHOICES = [
        ('', 'All Records'),
        ('fiscal_series', 'Fiscal Series'),
        ('reports', 'Fiscal Reports'),
        ('audit_logs', 'Audit Logs'),
        ('tax_configs', 'Tax Configurations'),
    ]
    
    search_type = forms.ChoiceField(
        choices=SEARCH_TYPE_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    search_query = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by series number, report number, or description...'
        })
    )
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    user = forms.ModelChoiceField(
        queryset=None,
        required=False,
        empty_label="All Users",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    def __init__(self, *args, **kwargs):
        tenant = kwargs.pop('tenant', None)
        super().__init__(*args, **kwargs)
        
        # Filter users by tenant
        if tenant:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            self.fields['user'].queryset = User.objects.filter(tenant=tenant)