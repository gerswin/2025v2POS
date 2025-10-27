"""
Forms for pricing administration web interface.
"""

from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal
import json

from .models import PriceStage, RowPricing
from venezuelan_pos.apps.events.models import Event
from venezuelan_pos.apps.zones.models import Zone


class PriceStageForm(forms.ModelForm):
    """Form for creating and editing price stages."""
    
    class Meta:
        model = PriceStage
        fields = [
            'name', 'description', 'start_date', 'end_date',
            'percentage_markup', 'stage_order', 'is_active'
        ]
        
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: Early Bird, Regular, Last Minute'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Descripción de esta etapa de precios'
            }),
            'start_date': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'end_date': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'percentage_markup': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '0.00',
                'min': '0',
                'step': '0.01'
            }),
            'stage_order': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '1',
                'min': '0'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }
    
    def __init__(self, *args, **kwargs):
        self.event = kwargs.pop('event', None)
        super().__init__(*args, **kwargs)
        
        # Set default values for new instances
        if not self.instance.pk:
            self.fields['is_active'].initial = True
            self.fields['percentage_markup'].initial = Decimal('0.00')
    
    def clean_name(self):
        """Validate stage name."""
        name = self.cleaned_data.get('name', '').strip()
        if not name:
            raise ValidationError('El nombre de la etapa es obligatorio.')
        return name
    
    def clean_percentage_markup(self):
        """Validate percentage markup."""
        markup = self.cleaned_data.get('percentage_markup')
        if markup is not None and markup < 0:
            raise ValidationError('El porcentaje de incremento no puede ser negativo.')
        return markup
    
    def clean(self):
        """Cross-field validation."""
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        # Validate date range
        if start_date and end_date:
            if start_date >= end_date:
                raise ValidationError({
                    'end_date': 'La fecha de fin debe ser posterior a la fecha de inicio.'
                })
        
        # Check for overlapping stages if event is provided
        if self.event and start_date and end_date:
            overlapping_stages = PriceStage.objects.filter(
                event=self.event,
                is_active=True
            )
            
            # Exclude current instance if updating
            if self.instance and self.instance.pk:
                overlapping_stages = overlapping_stages.exclude(pk=self.instance.pk)
            
            for stage in overlapping_stages:
                if stage.start_date and stage.end_date:
                    if (start_date < stage.end_date and end_date > stage.start_date):
                        raise ValidationError({
                            'start_date': f'El rango de fechas se superpone con la etapa "{stage.name}"',
                            'end_date': f'El rango de fechas se superpone con la etapa "{stage.name}"'
                        })
        
        return cleaned_data


class RowPricingForm(forms.ModelForm):
    """Form for creating and editing row pricing."""
    
    class Meta:
        model = RowPricing
        fields = [
            'row_number', 'percentage_markup', 'name', 'description', 'is_active'
        ]
        
        widgets = {
            'row_number': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Número de fila',
                'min': '1'
            }),
            'percentage_markup': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '0.00',
                'min': '0',
                'step': '0.01'
            }),
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: VIP, Premium, Estándar (opcional)'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Descripción de este precio por fila'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }
    
    def __init__(self, *args, **kwargs):
        self.zone = kwargs.pop('zone', None)
        super().__init__(*args, **kwargs)
        
        # Set default values for new instances
        if not self.instance.pk:
            self.fields['is_active'].initial = True
            self.fields['percentage_markup'].initial = Decimal('0.00')
    
    def clean_row_number(self):
        """Validate row number."""
        row_number = self.cleaned_data.get('row_number')
        
        if row_number is not None and row_number <= 0:
            raise ValidationError('El número de fila debe ser positivo.')
        
        # Check if zone has enough rows
        if self.zone and self.zone.rows and row_number and row_number > self.zone.rows:
            raise ValidationError(
                f'El número de fila no puede exceder las filas de la zona ({self.zone.rows})'
            )
        
        # Check for duplicate row numbers in the same zone
        if self.zone and row_number:
            existing = RowPricing.objects.filter(
                zone=self.zone,
                row_number=row_number
            )
            
            # Exclude current instance if updating
            if self.instance and self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            
            if existing.exists():
                raise ValidationError(
                    f'Ya existe un precio configurado para la fila {row_number}'
                )
        
        return row_number
    
    def clean(self):
        """Cross-field validation and set zone on instance."""
        cleaned_data = super().clean()
        
        # Set the zone on the instance before model validation
        # This prevents the RelatedObjectDoesNotExist error
        if self.zone and self.instance:
            self.instance.zone = self.zone
            self.instance.zone_id = self.zone.id
            # Also set the tenant from the zone
            self.instance.tenant = self.zone.tenant
        
        return cleaned_data
    
    def clean_percentage_markup(self):
        """Validate percentage markup."""
        markup = self.cleaned_data.get('percentage_markup')
        if markup is not None and markup < 0:
            raise ValidationError('El porcentaje de incremento no puede ser negativo.')
        return markup


class BulkRowPricingForm(forms.Form):
    """Form for creating multiple row pricing entries at once."""
    
    start_row = forms.IntegerField(
        label="Fila inicial",
        min_value=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '1'
        })
    )
    
    end_row = forms.IntegerField(
        label="Fila final",
        min_value=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '10'
        })
    )
    
    percentage_markup = forms.DecimalField(
        label="Porcentaje de incremento",
        min_value=0,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '0.00',
            'step': '0.01'
        })
    )
    
    name_pattern = forms.CharField(
        label="Patrón de nombre (opcional)",
        required=False,
        help_text="Use {row} para incluir el número de fila. Ej: 'Fila {row}'",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Fila {row}'
        })
    )
    
    def __init__(self, *args, **kwargs):
        self.zone = kwargs.pop('zone', None)
        super().__init__(*args, **kwargs)
    
    def clean(self):
        """Validate bulk row pricing data."""
        cleaned_data = super().clean()
        start_row = cleaned_data.get('start_row')
        end_row = cleaned_data.get('end_row')
        
        if start_row and end_row:
            if start_row > end_row:
                raise ValidationError({
                    'end_row': 'La fila final debe ser mayor o igual a la fila inicial.'
                })
            
            # Check zone capacity
            if self.zone and self.zone.rows:
                if end_row > self.zone.rows:
                    raise ValidationError({
                        'end_row': f'La fila final no puede exceder las filas de la zona ({self.zone.rows})'
                    })
            
            # Check for existing row pricing
            if self.zone:
                existing_rows = RowPricing.objects.filter(
                    zone=self.zone,
                    row_number__range=(start_row, end_row)
                ).values_list('row_number', flat=True)
                
                if existing_rows:
                    existing_list = ', '.join(map(str, sorted(existing_rows)))
                    raise ValidationError(
                        f'Ya existen precios configurados para las filas: {existing_list}'
                    )
        
        return cleaned_data


class PriceCalculationForm(forms.Form):
    """Form for price calculation preview."""
    
    event = forms.ModelChoiceField(
        queryset=Event.objects.none(),
        label="Evento",
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    zone = forms.ModelChoiceField(
        queryset=Zone.objects.none(),
        label="Zona",
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    row_number = forms.IntegerField(
        label="Número de fila (opcional)",
        required=False,
        min_value=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Dejar vacío para precio base de zona'
        })
    )
    
    seat_number = forms.IntegerField(
        label="Número de asiento (opcional)",
        required=False,
        min_value=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Dejar vacío para precio de fila'
        })
    )
    
    calculation_date = forms.DateTimeField(
        label="Fecha de cálculo",
        required=False,
        widget=forms.DateTimeInput(attrs={
            'class': 'form-control',
            'type': 'datetime-local'
        }),
        help_text="Dejar vacío para usar la fecha actual"
    )
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Filter events by user's tenant
        if self.user:
            if self.user.is_admin_user:
                events = Event.objects.filter(status=Event.Status.ACTIVE)
            else:
                events = Event.objects.filter(
                    tenant=self.user.tenant,
                    status=Event.Status.ACTIVE
                )
            
            self.fields['event'].queryset = events.order_by('name')
        
        # Set default calculation date to now
        if not self.data:
            self.fields['calculation_date'].initial = timezone.now()
    
    def clean(self):
        """Validate calculation form data."""
        cleaned_data = super().clean()
        event = cleaned_data.get('event')
        zone = cleaned_data.get('zone')
        row_number = cleaned_data.get('row_number')
        seat_number = cleaned_data.get('seat_number')
        
        # Validate zone belongs to event
        if event and zone and zone.event != event:
            raise ValidationError({
                'zone': 'La zona seleccionada no pertenece al evento seleccionado.'
            })
        
        # Validate row and seat for numbered zones
        if zone and zone.zone_type == Zone.ZoneType.NUMBERED:
            if row_number and zone.rows and row_number > zone.rows:
                raise ValidationError({
                    'row_number': f'El número de fila no puede exceder las filas de la zona ({zone.rows})'
                })
            
            if seat_number and not row_number:
                raise ValidationError({
                    'seat_number': 'Debe especificar el número de fila para seleccionar un asiento.'
                })
        
        return cleaned_data


class PricingDashboardFilterForm(forms.Form):
    """Form for filtering pricing dashboard data."""
    
    event = forms.ModelChoiceField(
        queryset=Event.objects.none(),
        required=False,
        label="Evento",
        empty_label="Todos los eventos",
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    zone = forms.ModelChoiceField(
        queryset=Zone.objects.none(),
        required=False,
        label="Zona",
        empty_label="Todas las zonas",
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    stage_status = forms.ChoiceField(
        choices=[
            ('', 'Todas las etapas'),
            ('current', 'Etapas actuales'),
            ('upcoming', 'Etapas próximas'),
            ('past', 'Etapas pasadas'),
        ],
        required=False,
        label="Estado de etapa",
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Filter events by user's tenant
        if self.user:
            if self.user.is_admin_user:
                events = Event.objects.all()
            else:
                events = Event.objects.filter(tenant=self.user.tenant)
            
            self.fields['event'].queryset = events.order_by('name')