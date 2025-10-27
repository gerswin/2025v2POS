from django import forms
from django.core.exceptions import ValidationError
from phonenumber_field.formfields import PhoneNumberField
from .models import Customer, CustomerPreferences


class CustomerForm(forms.ModelForm):
    """Form for creating and editing customers."""
    
    phone = PhoneNumberField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+584121234567'
        }),
        help_text="Venezuelan phone number (include country code)"
    )
    
    class Meta:
        model = Customer
        fields = [
            'name', 'surname', 'phone', 'email', 'identification',
            'date_of_birth', 'address', 'notes', 'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'First name'
            }),
            'surname': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Last name'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'email@example.com'
            }),
            'identification': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'V-12345678 or E-12345678'
            }),
            'date_of_birth': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Customer address'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Additional notes about the customer'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }
    
    def clean(self):
        """Validate that at least phone or email is provided."""
        cleaned_data = super().clean()
        phone = cleaned_data.get('phone')
        email = cleaned_data.get('email')
        
        if not phone and not email:
            raise ValidationError(
                "Customer must have at least a phone number or email address"
            )
        
        return cleaned_data


class CustomerPreferencesForm(forms.ModelForm):
    """Form for editing customer communication preferences."""
    
    class Meta:
        model = CustomerPreferences
        fields = [
            'email_enabled', 'sms_enabled', 'whatsapp_enabled', 'phone_enabled',
            'purchase_confirmations', 'payment_reminders', 'event_reminders',
            'promotional_messages', 'system_updates',
            'preferred_contact_time_start', 'preferred_contact_time_end',
            'preferred_language'
        ]
        widgets = {
            'email_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'sms_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'whatsapp_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'phone_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'purchase_confirmations': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'payment_reminders': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'event_reminders': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'promotional_messages': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'system_updates': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'preferred_contact_time_start': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time'
            }),
            'preferred_contact_time_end': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time'
            }),
            'preferred_language': forms.Select(attrs={'class': 'form-select'})
        }


class CustomerSearchForm(forms.Form):
    """Form for searching customers."""
    
    query = forms.CharField(
        max_length=255,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by name, phone, email, or identification...',
            'autofocus': True
        }),
        help_text="Enter name, phone number, email, or identification number"
    )
    
    is_active = forms.ChoiceField(
        choices=[
            ('', 'All customers'),
            ('true', 'Active only'),
            ('false', 'Inactive only')
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )


class CustomerQuickAddForm(forms.ModelForm):
    """Simplified form for quickly adding customers during sales."""
    
    phone = PhoneNumberField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-sm',
            'placeholder': '+584121234567'
        })
    )
    
    class Meta:
        model = Customer
        fields = ['name', 'surname', 'phone', 'email', 'identification']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control form-control-sm',
                'placeholder': 'First name',
                'required': True
            }),
            'surname': forms.TextInput(attrs={
                'class': 'form-control form-control-sm',
                'placeholder': 'Last name',
                'required': True
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control form-control-sm',
                'placeholder': 'email@example.com'
            }),
            'identification': forms.TextInput(attrs={
                'class': 'form-control form-control-sm',
                'placeholder': 'V-12345678'
            })
        }
    
    def clean(self):
        """Validate that at least phone or email is provided."""
        cleaned_data = super().clean()
        phone = cleaned_data.get('phone')
        email = cleaned_data.get('email')
        
        if not phone and not email:
            raise ValidationError(
                "Customer must have at least a phone number or email address"
            )
        
        return cleaned_data


class CustomerLookupForm(forms.Form):
    """Form for looking up customers by identification."""
    
    identification = forms.CharField(
        max_length=15,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'V-12345678 or E-12345678',
            'autofocus': True
        }),
        help_text="Enter Venezuelan identification number"
    )
    
    def clean_identification(self):
        """Validate and normalize identification format."""
        identification = self.cleaned_data.get('identification')
        if identification:
            # Normalize format
            normalized = identification.replace(' ', '').upper()
            
            # Validate format using the model validator
            from .models import validate_venezuelan_cedula
            try:
                validate_venezuelan_cedula(normalized)
            except ValidationError as e:
                raise forms.ValidationError(str(e))
            
            return normalized
        return identification