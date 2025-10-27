from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
import json

from .models import Venue, Event, EventConfiguration
from venezuelan_pos.apps.zones.models import Zone


class VenueForm(forms.ModelForm):
    """Formulario para crear y editar venues."""
    
    class Meta:
        model = Venue
        fields = [
            'name', 'venue_type', 'capacity', 'is_active',
            'address', 'city', 'state', 'country', 'postal_code',
            'contact_phone', 'contact_email', 'configuration'
        ]
        
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre de la venue'
            }),
            'venue_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'capacity': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: 1000',
                'min': '1'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Dirección completa de la venue'
            }),
            'city': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ciudad'
            }),
            'state': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Estado o Provincia'
            }),
            'country': forms.TextInput(attrs={
                'class': 'form-control',
                'value': 'Venezuela'
            }),
            'postal_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Código postal'
            }),
            'contact_phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+58-212-555-0123'
            }),
            'contact_email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'contacto@venue.com'
            }),
            'configuration': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': '{"parking": true, "wifi": true, "air_conditioning": true}'
            })
        }
    
    def clean_name(self):
        """Validar que el nombre no esté vacío."""
        name = self.cleaned_data.get('name', '').strip()
        if not name:
            raise ValidationError('El nombre de la venue es obligatorio.')
        return name
    
    def clean_capacity(self):
        """Validar que la capacidad sea positiva."""
        capacity = self.cleaned_data.get('capacity')
        if capacity is not None and capacity <= 0:
            raise ValidationError('La capacidad debe ser un número positivo.')
        return capacity
    
    def clean_configuration(self):
        """Validar que la configuración sea JSON válido."""
        config = self.cleaned_data.get('configuration', '')
        
        # Handle both string and dict inputs
        if isinstance(config, dict):
            return json.dumps(config)
        elif isinstance(config, str):
            config = config.strip()
            if config:
                try:
                    json.loads(config)
                except json.JSONDecodeError:
                    raise ValidationError('La configuración debe ser un JSON válido.')
            return config or '{}'
        else:
            return '{}'


class EventForm(forms.ModelForm):
    """Formulario para crear y editar eventos."""
    
    class Meta:
        model = Event
        fields = [
            'name', 'description', 'event_type', 'venue',
            'start_date', 'end_date', 'sales_start_date', 'sales_end_date',
            'base_currency', 'currency_conversion_rate', 'status', 'configuration'
        ]
        
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre del evento'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Descripción detallada del evento'
            }),
            'event_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'venue': forms.Select(attrs={
                'class': 'form-select'
            }),
            'start_date': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'end_date': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'sales_start_date': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'sales_end_date': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'base_currency': forms.Select(attrs={
                'class': 'form-select'
            }, choices=[
                ('USD', 'Dólar Estadounidense (USD)'),
                ('VES', 'Bolívar Venezolano (VES)'),
                ('EUR', 'Euro (EUR)'),
            ]),
            'currency_conversion_rate': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.0001',
                'min': '0.0001',
                'placeholder': '36.5000'
            }),
            'status': forms.Select(attrs={
                'class': 'form-select'
            }),
            'configuration': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': '{"special_requirements": "Ninguno"}'
            })
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Filtrar venues por tenant del usuario
        if self.user:
            if self.user.is_admin_user:
                venues = Venue.objects.filter(is_active=True)
            else:
                venues = Venue.objects.filter(
                    tenant=self.user.tenant,
                    is_active=True
                )
            
            self.fields['venue'].queryset = venues.order_by('name')
            
            # Si no hay venues, mostrar mensaje
            if not venues.exists():
                self.fields['venue'].empty_label = "No hay venues disponibles"
        
        # Configurar valores por defecto
        if not self.instance.pk:  # Solo para nuevos eventos
            self.fields['base_currency'].initial = 'USD'
            self.fields['currency_conversion_rate'].initial = '36.5000'
            self.fields['status'].initial = Event.Status.DRAFT
    
    def clean_name(self):
        """Validar que el nombre no esté vacío."""
        name = self.cleaned_data.get('name', '').strip()
        if not name:
            raise ValidationError('El nombre del evento es obligatorio.')
        return name
    
    def clean_currency_conversion_rate(self):
        """Validar que la tasa de conversión sea positiva."""
        rate = self.cleaned_data.get('currency_conversion_rate')
        if rate is not None and rate <= 0:
            raise ValidationError('La tasa de conversión debe ser un número positivo.')
        return rate
    
    def clean_configuration(self):
        """Validar que la configuración sea JSON válido."""
        config = self.cleaned_data.get('configuration', '')
        
        # Handle both string and dict inputs
        if isinstance(config, dict):
            return json.dumps(config)
        elif isinstance(config, str):
            config = config.strip()
            if config:
                try:
                    json.loads(config)
                except json.JSONDecodeError:
                    raise ValidationError('La configuración debe ser un JSON válido.')
            return config or '{}'
        else:
            return '{}'
    
    def clean(self):
        """Validaciones cruzadas."""
        cleaned_data = super().clean()
        
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        sales_start_date = cleaned_data.get('sales_start_date')
        sales_end_date = cleaned_data.get('sales_end_date')
        
        # Validar fechas del evento
        if start_date and end_date:
            if start_date >= end_date:
                raise ValidationError({
                    'end_date': 'La fecha de fin debe ser posterior a la fecha de inicio.'
                })
        
        # Validar fechas de venta
        if sales_start_date and sales_end_date:
            if sales_start_date >= sales_end_date:
                raise ValidationError({
                    'sales_end_date': 'La fecha de fin de ventas debe ser posterior a la fecha de inicio de ventas.'
                })
        
        # Validar que las ventas terminen antes del evento
        if sales_end_date and start_date:
            if sales_end_date > start_date:
                raise ValidationError({
                    'sales_end_date': 'Las ventas deben terminar antes del inicio del evento.'
                })
        
        return cleaned_data


class EventConfigurationForm(forms.ModelForm):
    """Formulario para configuración de eventos."""
    
    class Meta:
        model = EventConfiguration
        fields = [
            'partial_payments_enabled', 'installment_plans_enabled', 'flexible_payments_enabled',
            'max_installments', 'min_down_payment_percentage', 'payment_plan_expiry_days',
            'notifications_enabled', 'email_notifications', 'sms_notifications', 'whatsapp_notifications',
            'send_purchase_confirmation', 'send_payment_reminders', 'send_event_reminders', 'event_reminder_days',
            'digital_tickets_enabled', 'qr_codes_enabled', 'pdf_tickets_enabled',
            'configuration'
        ]
        
        widgets = {
            'partial_payments_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'installment_plans_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'flexible_payments_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'max_installments': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'max': '12'
            }),
            'min_down_payment_percentage': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'max': '100',
                'step': '0.01'
            }),
            'payment_plan_expiry_days': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1'
            }),
            'notifications_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'email_notifications': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'sms_notifications': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'whatsapp_notifications': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'send_purchase_confirmation': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'send_payment_reminders': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'send_event_reminders': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'event_reminder_days': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1'
            }),
            'digital_tickets_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'qr_codes_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'pdf_tickets_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'configuration': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4
            })
        }
    
    def clean_min_down_payment_percentage(self):
        """Validar porcentaje de pago inicial."""
        percentage = self.cleaned_data.get('min_down_payment_percentage')
        if percentage is not None:
            if percentage < 0 or percentage > 100:
                raise ValidationError('El porcentaje debe estar entre 0 y 100.')
        return percentage
    
    def clean_max_installments(self):
        """Validar número máximo de cuotas."""
        installments = self.cleaned_data.get('max_installments')
        if installments is not None and installments < 1:
            raise ValidationError('El número de cuotas debe ser al menos 1.')
        return installments
    
    def clean_configuration(self):
        """Validar configuración JSON."""
        config = self.cleaned_data.get('configuration', '')
        
        # Handle both string and dict inputs
        if isinstance(config, dict):
            return json.dumps(config)
        elif isinstance(config, str):
            config = config.strip()
            if config:
                try:
                    json.loads(config)
                except json.JSONDecodeError:
                    raise ValidationError('La configuración debe ser un JSON válido.')
            return config or '{}'
        else:
            return '{}'


class ZoneForm(forms.ModelForm):
    """Formulario para crear y editar zonas con soporte para configuración variable por fila."""
    
    # Campo adicional para configuración de filas
    use_variable_rows = forms.BooleanField(
        required=False,
        label="Usar configuración variable por fila",
        help_text="Permite configurar diferente número de asientos por fila",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    row_config_json = forms.CharField(
        required=False,
        widget=forms.HiddenInput(),
        help_text="Configuración JSON de asientos por fila"
    )
    
    class Meta:
        model = Zone
        fields = [
            'name', 'description', 'zone_type', 'capacity',
            'rows', 'seats_per_row', 'row_configuration',
            'base_price', 'status', 'display_order'
        ]
        
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre de la zona'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Descripción de la zona'
            }),
            'zone_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'capacity': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Capacidad total',
                'min': '1',
                'readonly': True  # Se calcula automáticamente
            }),
            'rows': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Número de filas',
                'min': '1'
            }),
            'seats_per_row': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Asientos por fila (por defecto)',
                'min': '1'
            }),
            'row_configuration': forms.HiddenInput(),
            'base_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Precio base',
                'min': '0',
                'step': '0.01'
            }),
            'status': forms.Select(attrs={
                'class': 'form-select'
            }),
            'display_order': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Orden de visualización',
                'min': '0'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Si hay una instancia existente con row_configuration, marcar el checkbox
        if self.instance and self.instance.pk and self.instance.row_configuration:
            self.fields['use_variable_rows'].initial = True
            self.fields['row_config_json'].initial = json.dumps(self.instance.row_configuration)
    
    def clean(self):
        """Validación personalizada del formulario."""
        cleaned_data = super().clean()
        zone_type = cleaned_data.get('zone_type')
        rows = cleaned_data.get('rows')
        seats_per_row = cleaned_data.get('seats_per_row')
        use_variable_rows = cleaned_data.get('use_variable_rows')
        row_config_json = cleaned_data.get('row_config_json')
        
        if zone_type == Zone.ZoneType.NUMBERED:
            if not rows or rows <= 0:
                raise ValidationError({'rows': 'Las zonas numeradas deben tener al menos 1 fila.'})
            
            if use_variable_rows and row_config_json:
                try:
                    row_config = json.loads(row_config_json)
                    
                    # Validar que la configuración sea un diccionario
                    if not isinstance(row_config, dict):
                        raise ValidationError({'row_config_json': 'La configuración debe ser un objeto JSON.'})
                    
                    # Calcular capacidad total
                    total_capacity = 0
                    for row_num in range(1, rows + 1):
                        row_seats = row_config.get(str(row_num))
                        if row_seats is None:
                            if not seats_per_row:
                                raise ValidationError({
                                    'seats_per_row': f'Debe especificar asientos por defecto o configurar la fila {row_num}'
                                })
                            row_seats = seats_per_row
                        
                        if not isinstance(row_seats, int) or row_seats <= 0:
                            raise ValidationError({
                                'row_config_json': f'La fila {row_num} debe tener al menos 1 asiento'
                            })
                        
                        total_capacity += row_seats
                    
                    # Actualizar campos calculados
                    cleaned_data['capacity'] = total_capacity
                    cleaned_data['row_configuration'] = row_config
                    
                except json.JSONDecodeError:
                    raise ValidationError({'row_config_json': 'Configuración JSON inválida.'})
            
            else:
                # Configuración estándar
                if not seats_per_row or seats_per_row <= 0:
                    raise ValidationError({'seats_per_row': 'Las zonas numeradas deben tener al menos 1 asiento por fila.'})
                
                cleaned_data['capacity'] = rows * seats_per_row
                cleaned_data['row_configuration'] = {}
        
        return cleaned_data
    
    class Media:
        js = ('js/zone_form.js',)
        css = {
            'all': ('css/zone_form.css',)
        }