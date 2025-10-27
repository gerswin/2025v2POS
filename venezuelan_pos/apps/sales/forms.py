"""
Forms for sales web interface.
"""

from django import forms
from django.utils.translation import gettext_lazy as _
from .models import Transaction, ReservedTicket
from ..customers.models import Customer


class CustomerSelectionForm(forms.Form):
    """Form for selecting or creating a customer during checkout."""
    
    customer_id = forms.UUIDField(
        required=False,
        widget=forms.HiddenInput()
    )
    
    # New customer fields
    name = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('First Name')
        })
    )
    
    surname = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Last Name')
        })
    )
    
    phone = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+58 414 123 4567'
        })
    )
    
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'customer@example.com'
        })
    )
    
    identification = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'V-12345678'
        })
    )
    
    def clean(self):
        cleaned_data = super().clean()
        customer_id = cleaned_data.get('customer_id')
        
        if not customer_id:
            # New customer - validate required fields
            name = cleaned_data.get('name')
            surname = cleaned_data.get('surname')
            phone = cleaned_data.get('phone')
            
            if not name:
                raise forms.ValidationError(_('First name is required for new customers'))
            
            if not surname:
                raise forms.ValidationError(_('Last name is required for new customers'))
            
            if not phone:
                raise forms.ValidationError(_('Phone number is required for new customers'))
        
        return cleaned_data


class TransactionFilterForm(forms.Form):
    """Form for filtering transactions in the list view."""
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Search by fiscal series, customer name, email...')
        })
    )
    
    status = forms.ChoiceField(
        choices=[('', _('All Statuses'))] + Transaction.Status.choices,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    event = forms.ModelChoiceField(
        queryset=None,  # Will be set in __init__
        required=False,
        empty_label=_('All Events'),
        widget=forms.Select(attrs={'class': 'form-select'})
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
    
    def __init__(self, *args, **kwargs):
        events_queryset = kwargs.pop('events_queryset', None)
        super().__init__(*args, **kwargs)
        
        if events_queryset is not None:
            self.fields['event'].queryset = events_queryset


class ReservationExtendForm(forms.Form):
    """Form for extending reservation time."""
    
    EXTENSION_CHOICES = [
        (15, _('15 minutes')),
        (30, _('30 minutes')),
        (60, _('1 hour')),
        (120, _('2 hours')),
    ]
    
    extension_minutes = forms.ChoiceField(
        choices=EXTENSION_CHOICES,
        initial=30,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    reason = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': _('Optional reason for extension...')
        })
    )