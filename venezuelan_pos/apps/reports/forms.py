from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import datetime, timedelta
import json

from .models import SalesReport, OccupancyAnalysis, ReportSchedule
from venezuelan_pos.apps.events.models import Event
from venezuelan_pos.apps.zones.models import Zone
from venezuelan_pos.apps.tenants.models import User


class SalesReportForm(forms.ModelForm):
    """Form for creating and editing sales reports."""
    
    # Additional fields for filtering
    start_date = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={
            'class': 'form-control',
            'type': 'datetime-local'
        }),
        label="Fecha de inicio"
    )
    
    end_date = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={
            'class': 'form-control',
            'type': 'datetime-local'
        }),
        label="Fecha de fin"
    )
    
    event = forms.ModelChoiceField(
        queryset=Event.objects.none(),
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        label="Evento específico"
    )
    
    zone = forms.ModelChoiceField(
        queryset=Zone.objects.none(),
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        label="Zona específica"
    )
    
    operator = forms.ModelChoiceField(
        queryset=User.objects.none(),
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        label="Operador específico"
    )
    
    class Meta:
        model = SalesReport
        fields = ['name', 'report_type']
        
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre del reporte'
            }),
            'report_type': forms.Select(attrs={
                'class': 'form-select'
            })
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if self.user and self.user.tenant:
            # Filter events by tenant
            self.fields['event'].queryset = Event.objects.filter(
                tenant=self.user.tenant
            ).order_by('-start_date')
            
            # Filter zones by tenant
            self.fields['zone'].queryset = Zone.objects.filter(
                tenant=self.user.tenant
            ).order_by('event__name', 'name')
            
            # Filter operators by tenant
            self.fields['operator'].queryset = User.objects.filter(
                tenant=self.user.tenant,
                role__in=[User.Role.EVENT_OPERATOR, User.Role.TENANT_ADMIN]
            ).order_by('username')
        
        # Set default date range (last 30 days)
        if not self.instance.pk:
            end_date = timezone.now()
            start_date = end_date - timedelta(days=30)
            self.fields['start_date'].initial = start_date
            self.fields['end_date'].initial = end_date
    
    def clean_name(self):
        """Validate report name."""
        name = self.cleaned_data.get('name', '').strip()
        if not name:
            raise ValidationError('El nombre del reporte es obligatorio.')
        return name
    
    def clean(self):
        """Cross-field validation."""
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date:
            if start_date >= end_date:
                raise ValidationError({
                    'end_date': 'La fecha de fin debe ser posterior a la fecha de inicio.'
                })
        
        return cleaned_data
    
    def get_filters(self):
        """Get filters dictionary for report generation."""
        filters = {}
        
        if self.cleaned_data.get('start_date'):
            filters['start_date'] = self.cleaned_data['start_date']
        
        if self.cleaned_data.get('end_date'):
            filters['end_date'] = self.cleaned_data['end_date']
        
        if self.cleaned_data.get('event'):
            filters['event_id'] = str(self.cleaned_data['event'].id)
        
        if self.cleaned_data.get('zone'):
            filters['zone_id'] = str(self.cleaned_data['zone'].id)
        
        if self.cleaned_data.get('operator'):
            filters['operator_id'] = str(self.cleaned_data['operator'].id)
        
        return filters


class OccupancyAnalysisForm(forms.ModelForm):
    """Form for creating occupancy analysis."""
    
    event = forms.ModelChoiceField(
        queryset=Event.objects.none(),
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        label="Evento"
    )
    
    zone = forms.ModelChoiceField(
        queryset=Zone.objects.none(),
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        label="Zona"
    )
    
    analysis_period_days = forms.IntegerField(
        initial=30,
        min_value=1,
        max_value=365,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '30'
        }),
        label="Período de análisis (días)"
    )
    
    class Meta:
        model = OccupancyAnalysis
        fields = ['name', 'analysis_type']
        
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre del análisis'
            }),
            'analysis_type': forms.Select(attrs={
                'class': 'form-select'
            })
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if self.user and self.user.tenant:
            # Filter events by tenant
            self.fields['event'].queryset = Event.objects.filter(
                tenant=self.user.tenant
            ).order_by('-start_date')
            
            # Filter zones by tenant
            self.fields['zone'].queryset = Zone.objects.filter(
                tenant=self.user.tenant
            ).order_by('event__name', 'name')
    
    def clean_name(self):
        """Validate analysis name."""
        name = self.cleaned_data.get('name', '').strip()
        if not name:
            raise ValidationError('El nombre del análisis es obligatorio.')
        return name
    
    def clean(self):
        """Cross-field validation."""
        cleaned_data = super().clean()
        analysis_type = cleaned_data.get('analysis_type')
        event = cleaned_data.get('event')
        zone = cleaned_data.get('zone')
        
        if analysis_type == OccupancyAnalysis.AnalysisType.ZONE and not zone:
            raise ValidationError({
                'zone': 'Debe seleccionar una zona para análisis de zona.'
            })
        
        if analysis_type == OccupancyAnalysis.AnalysisType.EVENT and not event:
            raise ValidationError({
                'event': 'Debe seleccionar un evento para análisis de evento.'
            })
        
        return cleaned_data


class ReportScheduleForm(forms.ModelForm):
    """Form for creating and editing report schedules."""
    
    # Additional fields for email configuration
    email_recipients_text = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'admin@example.com\nmanager@example.com'
        }),
        label="Destinatarios de email (uno por línea)"
    )
    
    export_formats_choices = forms.MultipleChoiceField(
        choices=[
            ('json', 'JSON'),
            ('csv', 'CSV'),
            ('pdf', 'PDF')
        ],
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-check-input'
        }),
        required=False,
        label="Formatos de exportación"
    )
    
    class Meta:
        model = ReportSchedule
        fields = [
            'name', 'description', 'report_type', 'frequency',
            'next_run', 'status'
        ]
        
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre de la programación'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Descripción de la programación'
            }),
            'report_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'frequency': forms.Select(attrs={
                'class': 'form-select'
            }),
            'next_run': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'status': forms.Select(attrs={
                'class': 'form-select'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set default next run time (tomorrow at 9 AM)
        if not self.instance.pk:
            tomorrow = timezone.now() + timedelta(days=1)
            next_run = tomorrow.replace(hour=9, minute=0, second=0, microsecond=0)
            self.fields['next_run'].initial = next_run
        
        # Populate email recipients if editing
        if self.instance.pk and self.instance.email_recipients:
            self.fields['email_recipients_text'].initial = '\n'.join(
                self.instance.email_recipients
            )
        
        # Populate export formats if editing
        if self.instance.pk and self.instance.export_formats:
            self.fields['export_formats_choices'].initial = self.instance.export_formats
    
    def clean_name(self):
        """Validate schedule name."""
        name = self.cleaned_data.get('name', '').strip()
        if not name:
            raise ValidationError('El nombre de la programación es obligatorio.')
        return name
    
    def clean_next_run(self):
        """Validate next run time."""
        next_run = self.cleaned_data.get('next_run')
        if next_run and next_run <= timezone.now():
            raise ValidationError('La próxima ejecución debe ser en el futuro.')
        return next_run
    
    def clean_email_recipients_text(self):
        """Validate and parse email recipients."""
        recipients_text = self.cleaned_data.get('email_recipients_text', '').strip()
        
        if not recipients_text:
            return []
        
        recipients = []
        for line in recipients_text.split('\n'):
            email = line.strip()
            if email:
                # Basic email validation
                if '@' not in email or '.' not in email:
                    raise ValidationError(f'Email inválido: {email}')
                recipients.append(email)
        
        return recipients
    
    def save(self, commit=True):
        """Save with processed email recipients and export formats."""
        instance = super().save(commit=False)
        
        # Set email recipients
        instance.email_recipients = self.cleaned_data.get('email_recipients_text', [])
        
        # Set export formats
        instance.export_formats = self.cleaned_data.get('export_formats_choices', [])
        
        if commit:
            instance.save()
        
        return instance


class ReportFilterForm(forms.Form):
    """Form for filtering reports in list views."""
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Buscar reportes...'
        }),
        label="Buscar"
    )
    
    report_type = forms.ChoiceField(
        choices=[('', 'Todos los tipos')] + list(SalesReport.ReportType.choices),
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        label="Tipo de reporte"
    )
    
    status = forms.ChoiceField(
        choices=[('', 'Todos los estados')] + list(SalesReport.Status.choices),
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        label="Estado"
    )
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label="Desde"
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label="Hasta"
    )


class HeatMapConfigForm(forms.Form):
    """Form for configuring heat map generation."""
    
    zone = forms.ModelChoiceField(
        queryset=Zone.objects.none(),
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        label="Zona"
    )
    
    event = forms.ModelChoiceField(
        queryset=Event.objects.none(),
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        label="Evento (opcional)"
    )
    
    show_prices = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        label="Mostrar precios"
    )
    
    show_sales_count = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        label="Mostrar cantidad de ventas"
    )
    
    color_scheme = forms.ChoiceField(
        choices=[
            ('heat', 'Mapa de calor (rojo-amarillo-verde)'),
            ('blue', 'Azul (claro-oscuro)'),
            ('grayscale', 'Escala de grises')
        ],
        initial='heat',
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        label="Esquema de colores"
    )
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if self.user and self.user.tenant:
            # Filter zones by tenant and only numbered zones
            self.fields['zone'].queryset = Zone.objects.filter(
                tenant=self.user.tenant,
                zone_type=Zone.ZoneType.NUMBERED
            ).order_by('event__name', 'name')
            
            # Filter events by tenant
            self.fields['event'].queryset = Event.objects.filter(
                tenant=self.user.tenant
            ).order_by('-start_date')


class CustomReportBuilderForm(forms.Form):
    """Form for building custom reports with drag-and-drop filters."""
    
    report_name = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nombre del reporte personalizado'
        }),
        label="Nombre del reporte"
    )
    
    # Date range
    date_range_type = forms.ChoiceField(
        choices=[
            ('last_7_days', 'Últimos 7 días'),
            ('last_30_days', 'Últimos 30 días'),
            ('last_90_days', 'Últimos 90 días'),
            ('this_month', 'Este mes'),
            ('last_month', 'Mes pasado'),
            ('custom', 'Rango personalizado')
        ],
        initial='last_30_days',
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        label="Rango de fechas"
    )
    
    custom_start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label="Fecha de inicio personalizada"
    )
    
    custom_end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label="Fecha de fin personalizada"
    )
    
    # Grouping options
    group_by = forms.MultipleChoiceField(
        choices=[
            ('event', 'Por evento'),
            ('zone', 'Por zona'),
            ('operator', 'Por operador'),
            ('payment_method', 'Por método de pago'),
            ('day', 'Por día'),
            ('hour', 'Por hora')
        ],
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-check-input'
        }),
        required=False,
        label="Agrupar por"
    )
    
    # Metrics to include
    metrics = forms.MultipleChoiceField(
        choices=[
            ('total_revenue', 'Ingresos totales'),
            ('total_transactions', 'Total de transacciones'),
            ('total_tickets', 'Total de tickets'),
            ('average_ticket_price', 'Precio promedio por ticket'),
            ('fill_rate', 'Tasa de ocupación'),
            ('sales_velocity', 'Velocidad de ventas')
        ],
        initial=['total_revenue', 'total_transactions', 'total_tickets'],
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-check-input'
        }),
        label="Métricas a incluir"
    )
    
    # Filters
    events = forms.ModelMultipleChoiceField(
        queryset=Event.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-check-input'
        }),
        label="Eventos específicos"
    )
    
    zones = forms.ModelMultipleChoiceField(
        queryset=Zone.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-check-input'
        }),
        label="Zonas específicas"
    )
    
    # Export options
    export_format = forms.ChoiceField(
        choices=[
            ('json', 'JSON'),
            ('csv', 'CSV'),
            ('pdf', 'PDF')
        ],
        initial='csv',
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        label="Formato de exportación"
    )
    
    include_charts = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        label="Incluir gráficos"
    )
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if self.user and self.user.tenant:
            # Filter events by tenant
            self.fields['events'].queryset = Event.objects.filter(
                tenant=self.user.tenant
            ).order_by('-start_date')
            
            # Filter zones by tenant
            self.fields['zones'].queryset = Zone.objects.filter(
                tenant=self.user.tenant
            ).order_by('event__name', 'name')
    
    def clean(self):
        """Validate custom date range."""
        cleaned_data = super().clean()
        date_range_type = cleaned_data.get('date_range_type')
        
        if date_range_type == 'custom':
            start_date = cleaned_data.get('custom_start_date')
            end_date = cleaned_data.get('custom_end_date')
            
            if not start_date:
                raise ValidationError({
                    'custom_start_date': 'Fecha de inicio requerida para rango personalizado.'
                })
            
            if not end_date:
                raise ValidationError({
                    'custom_end_date': 'Fecha de fin requerida para rango personalizado.'
                })
            
            if start_date >= end_date:
                raise ValidationError({
                    'custom_end_date': 'La fecha de fin debe ser posterior a la fecha de inicio.'
                })
        
        return cleaned_data