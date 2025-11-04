"""
Forms for notification management.
"""

from django import forms
from django.template import Template, TemplateSyntaxError
from .models import NotificationTemplate, NotificationPreference


class NotificationTemplateForm(forms.ModelForm):
    """Form for creating and editing notification templates."""
    
    class Meta:
        model = NotificationTemplate
        fields = ['name', 'template_type', 'subject', 'content', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Template name'
            }),
            'template_type': forms.Select(attrs={
                'class': 'form-control'
            }),
            'subject': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Email subject (for email templates)'
            }),
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 10,
                'placeholder': 'Template content with Django template syntax'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
    
    def clean_content(self):
        """Validate template content for Django template syntax."""
        content = self.cleaned_data.get('content')
        
        if content:
            try:
                Template(content)
            except TemplateSyntaxError as e:
                raise forms.ValidationError(f"Invalid template syntax: {e}")
        
        return content
    
    def clean_subject(self):
        """Validate subject template syntax."""
        subject = self.cleaned_data.get('subject')
        
        if subject:
            try:
                Template(subject)
            except TemplateSyntaxError as e:
                raise forms.ValidationError(f"Invalid subject template syntax: {e}")
        
        return subject


class NotificationPreferenceForm(forms.ModelForm):
    """Form for editing customer notification preferences."""
    
    class Meta:
        model = NotificationPreference
        fields = [
            'email_enabled', 'sms_enabled', 'whatsapp_enabled',
            'purchase_confirmations', 'payment_reminders', 
            'event_reminders', 'promotional_messages'
        ]
        widgets = {
            'email_enabled': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'sms_enabled': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'whatsapp_enabled': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'purchase_confirmations': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'payment_reminders': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'event_reminders': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'promotional_messages': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }


class SendNotificationForm(forms.Form):
    """Form for sending manual notifications."""
    
    template = forms.ModelChoiceField(
        queryset=NotificationTemplate.objects.none(),
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text="Select notification template"
    )
    
    recipient = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email address or phone number'
        }),
        help_text="Email address or phone number"
    )
    
    customer = forms.ModelChoiceField(
        queryset=None,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text="Optional: Link to customer"
    )
    
    transaction = forms.ModelChoiceField(
        queryset=None,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text="Optional: Link to transaction"
    )
    
    event = forms.ModelChoiceField(
        queryset=None,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text="Optional: Link to event"
    )
    
    context = forms.JSONField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 5,
            'placeholder': '{"key": "value"}'
        }),
        help_text="Optional: JSON context for template variables"
    )
    
    def __init__(self, *args, **kwargs):
        tenant = kwargs.pop('tenant', None)
        super().__init__(*args, **kwargs)
        
        if tenant:
            self.fields['template'].queryset = NotificationTemplate.objects.filter(
                tenant=tenant,
                is_active=True
            )
            
            # Import here to avoid circular imports
            from venezuelan_pos.apps.customers.models import Customer
            from venezuelan_pos.apps.sales.models import Transaction
            from venezuelan_pos.apps.events.models import Event
            
            self.fields['customer'].queryset = Customer.objects.filter(tenant=tenant)
            self.fields['transaction'].queryset = Transaction.objects.filter(tenant=tenant)
            self.fields['event'].queryset = Event.objects.filter(tenant=tenant)
    
    def clean_recipient(self):
        """Validate recipient based on template type."""
        recipient = self.cleaned_data.get('recipient')
        template = self.cleaned_data.get('template')
        
        if template and recipient:
            if template.template_type == 'email':
                if '@' not in recipient:
                    raise forms.ValidationError("Invalid email address")
            elif template.template_type in ['sms', 'whatsapp']:
                # Basic phone validation
                clean_phone = recipient.replace('+', '').replace('-', '').replace(' ', '')
                if not clean_phone.isdigit():
                    raise forms.ValidationError("Invalid phone number")
        
        return recipient


class TemplatePreviewForm(forms.Form):
    """Form for previewing templates with test data."""
    
    test_data = forms.JSONField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 8,
            'placeholder': '{\n  "customer": {"name": "John", "surname": "Doe"},\n  "event": {"name": "Test Event"}\n}'
        }),
        help_text="JSON data for template preview"
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set default test data
        self.fields['test_data'].initial = {
            "customer": {
                "name": "John",
                "surname": "Doe",
                "email": "john.doe@example.com",
                "phone": "+58-412-1234567"
            },
            "event": {
                "name": "Test Event",
                "start_date": "2025-12-31 20:00:00",
                "venue": {
                    "name": "Test Venue",
                    "address": "123 Test Street"
                }
            },
            "transaction": {
                "fiscal_series": "TT00000001",
                "total_amount": "150.00"
            },
            "payment_plan": {
                "remaining_balance": "75.00",
                "next_payment_date": "2025-11-15"
            }
        }