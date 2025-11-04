"""
Web views for Fiscal Compliance management interface.
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.views.decorators.http import require_http_methods
import json

from venezuelan_pos.apps.tenants.mixins import TenantRequiredMixin
from .models import (
    FiscalSeries, FiscalDay, FiscalReport, AuditLog,
    TaxConfiguration, TaxCalculationHistory
)
from .forms import (
    TaxConfigurationForm, FiscalReportGenerationForm, TaxCalculationForm,
    FiscalDayClosureForm, VoidFiscalSeriesForm, FiscalComplianceSearchForm
)
from .services import (
    FiscalSeriesService, FiscalDayService, FiscalReportService,
    TaxCalculationService, FiscalComplianceService
)


@login_required
def fiscal_dashboard(request):
    """Main fiscal compliance dashboard"""
    tenant = request.tenant
    user = request.user
    
    # Get fiscal status
    fiscal_status = FiscalComplianceService.get_fiscal_status(tenant, user)
    
    # Get recent fiscal series
    recent_series = FiscalSeries.objects.filter(
        tenant=tenant
    ).select_related('transaction', 'issued_by')[:10]
    
    # Get recent reports
    recent_reports = FiscalReport.objects.filter(
        tenant=tenant
    ).select_related('user')[:5]
    
    # Get active tax configurations
    active_taxes = TaxConfiguration.objects.filter(
        tenant=tenant,
        is_active=True
    ).select_related('event')
    
    context = {
        'fiscal_status': fiscal_status,
        'recent_series': recent_series,
        'recent_reports': recent_reports,
        'active_taxes': active_taxes,
    }
    
    return render(request, 'fiscal/dashboard.html', context)


@login_required
def fiscal_series_list(request):
    """List fiscal series with search and filtering"""
    tenant = request.tenant
    
    # Get search form
    search_form = FiscalComplianceSearchForm(
        request.GET or None,
        tenant=tenant
    )
    
    # Base queryset
    queryset = FiscalSeries.objects.filter(
        tenant=tenant
    ).select_related('transaction', 'issued_by', 'voided_by')
    
    # Apply search filters
    if search_form.is_valid():
        search_query = search_form.cleaned_data.get('search_query')
        date_from = search_form.cleaned_data.get('date_from')
        date_to = search_form.cleaned_data.get('date_to')
        user = search_form.cleaned_data.get('user')
        
        if search_query:
            queryset = queryset.filter(
                Q(series_number__icontains=search_query) |
                Q(transaction__id__icontains=search_query)
            )
        
        if date_from:
            queryset = queryset.filter(issued_at__date__gte=date_from)
        
        if date_to:
            queryset = queryset.filter(issued_at__date__lte=date_to)
        
        if user:
            queryset = queryset.filter(issued_by=user)
    
    # Pagination
    paginator = Paginator(queryset, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_form': search_form,
    }
    
    return render(request, 'fiscal/fiscal_series_list.html', context)


@login_required
def fiscal_series_detail(request, series_id):
    """View fiscal series details"""
    tenant = request.tenant
    
    fiscal_series = get_object_or_404(
        FiscalSeries,
        id=series_id,
        tenant=tenant
    )
    
    # Get audit logs for this series
    audit_logs = AuditLog.objects.filter(
        tenant=tenant,
        fiscal_series=fiscal_series
    ).select_related('user')
    
    context = {
        'fiscal_series': fiscal_series,
        'audit_logs': audit_logs,
    }
    
    return render(request, 'fiscal/fiscal_series_detail.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def void_fiscal_series(request, series_id):
    """Void a fiscal series"""
    tenant = request.tenant
    
    fiscal_series = get_object_or_404(
        FiscalSeries,
        id=series_id,
        tenant=tenant
    )
    
    if fiscal_series.is_voided:
        messages.error(request, "This fiscal series is already voided.")
        return redirect('fiscal:fiscal_series_detail', series_id=series_id)
    
    if request.method == 'POST':
        form = VoidFiscalSeriesForm(request.POST)
        if form.is_valid():
            try:
                FiscalSeriesService.void_fiscal_series(
                    fiscal_series_id=fiscal_series.id,
                    user=request.user,
                    reason=form.cleaned_data['reason']
                )
                messages.success(
                    request,
                    f"Fiscal series {fiscal_series.series_number} has been voided."
                )
                return redirect('fiscal:fiscal_series_detail', series_id=series_id)
            except ValidationError as e:
                messages.error(request, str(e))
    else:
        form = VoidFiscalSeriesForm()
    
    context = {
        'fiscal_series': fiscal_series,
        'form': form,
    }
    
    return render(request, 'fiscal/void_fiscal_series.html', context)


@login_required
def fiscal_reports_list(request):
    """List fiscal reports"""
    tenant = request.tenant
    
    # Get search form
    search_form = FiscalComplianceSearchForm(
        request.GET or None,
        tenant=tenant
    )
    
    # Base queryset
    queryset = FiscalReport.objects.filter(
        tenant=tenant
    ).select_related('user')
    
    # Apply search filters
    if search_form.is_valid():
        search_query = search_form.cleaned_data.get('search_query')
        date_from = search_form.cleaned_data.get('date_from')
        date_to = search_form.cleaned_data.get('date_to')
        user = search_form.cleaned_data.get('user')
        
        if search_query:
            queryset = queryset.filter(
                Q(report_number__icontains=search_query) |
                Q(report_type__icontains=search_query)
            )
        
        if date_from:
            queryset = queryset.filter(fiscal_date__gte=date_from)
        
        if date_to:
            queryset = queryset.filter(fiscal_date__lte=date_to)
        
        if user:
            queryset = queryset.filter(user=user)
    
    # Pagination
    paginator = Paginator(queryset, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_form': search_form,
    }
    
    return render(request, 'fiscal/fiscal_reports_list.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def generate_fiscal_report(request):
    """Generate X or Z report"""
    tenant = request.tenant
    
    if request.method == 'POST':
        form = FiscalReportGenerationForm(request.POST)
        if form.is_valid():
            try:
                report_type = form.cleaned_data['report_type']
                fiscal_date = form.cleaned_data.get('fiscal_date')
                
                if report_type == 'X':
                    report = FiscalReportService.generate_x_report(
                        tenant=tenant,
                        user=request.user,
                        fiscal_date=fiscal_date
                    )
                    messages.success(
                        request,
                        f"X-Report #{report.report_number} generated successfully."
                    )
                else:  # Z Report
                    report = FiscalReportService.generate_z_report(
                        tenant=tenant,
                        user=request.user,
                        fiscal_date=fiscal_date
                    )
                    messages.success(
                        request,
                        f"Z-Report #{report.report_number} generated successfully."
                    )
                
                return redirect('fiscal:fiscal_report_detail', report_id=report.id)
                
            except ValidationError as e:
                messages.error(request, str(e))
    else:
        form = FiscalReportGenerationForm()
    
    context = {
        'form': form,
    }
    
    return render(request, 'fiscal/generate_report.html', context)


@login_required
def fiscal_report_detail(request, report_id):
    """View fiscal report details"""
    tenant = request.tenant
    
    report = get_object_or_404(
        FiscalReport,
        id=report_id,
        tenant=tenant
    )
    
    context = {
        'report': report,
    }
    
    return render(request, 'fiscal/fiscal_report_detail.html', context)


@login_required
def tax_configurations_list(request):
    """List tax configurations"""
    tenant = request.tenant
    
    # Get search form
    search_form = FiscalComplianceSearchForm(
        request.GET or None,
        tenant=tenant
    )
    
    # Base queryset
    queryset = TaxConfiguration.objects.filter(
        tenant=tenant
    ).select_related('event', 'created_by')
    
    # Apply search filters
    if search_form.is_valid():
        search_query = search_form.cleaned_data.get('search_query')
        
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(event__name__icontains=search_query)
            )
    
    # Pagination
    paginator = Paginator(queryset, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_form': search_form,
    }
    
    return render(request, 'fiscal/tax_configurations_list.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def tax_configuration_create(request):
    """Create new tax configuration"""
    tenant = request.tenant
    
    # Get event from URL parameter if provided
    event_id = request.GET.get('event')
    selected_event = None
    
    if event_id:
        try:
            from venezuelan_pos.apps.events.models import Event
            selected_event = Event.objects.get(id=event_id, tenant=tenant)
        except Event.DoesNotExist:
            messages.warning(request, "The specified event was not found.")
    
    if request.method == 'POST':
        form = TaxConfigurationForm(request.POST, tenant=tenant)
        if form.is_valid():
            tax_config = form.save(commit=False)
            tax_config.tenant = tenant
            tax_config.created_by = request.user
            tax_config.save()
            
            messages.success(
                request,
                f"Tax configuration '{tax_config.name}' created successfully."
            )
            return redirect('fiscal_web:tax_configuration_detail', config_id=tax_config.id)
    else:
        # Initialize form with event preselected if provided
        initial_data = {}
        if selected_event:
            initial_data['event'] = selected_event
            initial_data['scope'] = 'EVENT'  # Set scope to EVENT when event is preselected
        
        form = TaxConfigurationForm(tenant=tenant, initial=initial_data)
    
    context = {
        'form': form,
        'action': 'Create',
        'selected_event': selected_event,
    }
    
    return render(request, 'fiscal/tax_configuration_form.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def tax_configuration_edit(request, config_id):
    """Edit tax configuration"""
    tenant = request.tenant
    
    tax_config = get_object_or_404(
        TaxConfiguration,
        id=config_id,
        tenant=tenant
    )
    
    if request.method == 'POST':
        form = TaxConfigurationForm(
            request.POST,
            instance=tax_config,
            tenant=tenant
        )
        if form.is_valid():
            form.save()
            messages.success(
                request,
                f"Tax configuration '{tax_config.name}' updated successfully."
            )
            return redirect('fiscal:tax_configuration_detail', config_id=config_id)
    else:
        form = TaxConfigurationForm(instance=tax_config, tenant=tenant)
    
    context = {
        'form': form,
        'tax_config': tax_config,
        'action': 'Edit',
    }
    
    return render(request, 'fiscal/tax_configuration_form.html', context)


@login_required
def tax_configuration_detail(request, config_id):
    """View tax configuration details"""
    tenant = request.tenant
    
    tax_config = get_object_or_404(
        TaxConfiguration,
        id=config_id,
        tenant=tenant
    )
    
    # Get calculation history
    calculation_history = TaxCalculationHistory.objects.filter(
        tenant=tenant,
        tax_configuration=tax_config
    ).select_related('transaction', 'calculated_by')[:20]
    
    context = {
        'tax_config': tax_config,
        'calculation_history': calculation_history,
    }
    
    return render(request, 'fiscal/tax_configuration_detail.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def tax_calculator(request):
    """Tax calculation tool"""
    tenant = request.tenant
    
    calculation_result = None
    
    if request.method == 'POST':
        form = TaxCalculationForm(request.POST, tenant=tenant)
        if form.is_valid():
            base_amount = form.cleaned_data['base_amount']
            event = form.cleaned_data.get('event')
            
            try:
                tax_amount, tax_details, _ = TaxCalculationService.calculate_taxes(
                    base_amount=base_amount,
                    tenant=tenant,
                    event=event,
                    user=request.user
                )
                
                calculation_result = {
                    'base_amount': base_amount,
                    'tax_amount': tax_amount,
                    'total_amount': base_amount + tax_amount,
                    'tax_details': tax_details,
                }
                
            except ValidationError as e:
                messages.error(request, str(e))
    else:
        form = TaxCalculationForm(tenant=tenant)
    
    context = {
        'form': form,
        'calculation_result': calculation_result,
    }
    
    return render(request, 'fiscal/tax_calculator.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def close_fiscal_day(request):
    """Close current fiscal day"""
    tenant = request.tenant
    
    # Get current fiscal day
    current_fiscal_day = FiscalDayService.get_current_fiscal_day(tenant, request.user)
    
    if current_fiscal_day.is_closed:
        messages.info(request, "Current fiscal day is already closed.")
        return redirect('fiscal:fiscal_dashboard')
    
    if request.method == 'POST':
        form = FiscalDayClosureForm(request.POST)
        if form.is_valid():
            try:
                fiscal_day, z_report = FiscalDayService.close_fiscal_day(
                    tenant=tenant,
                    user=request.user
                )
                
                messages.success(
                    request,
                    f"Fiscal day {fiscal_day.fiscal_date} closed successfully. "
                    f"Z-Report #{z_report.report_number} generated."
                )
                return redirect('fiscal:fiscal_report_detail', report_id=z_report.id)
                
            except ValidationError as e:
                messages.error(request, str(e))
    else:
        form = FiscalDayClosureForm()
    
    context = {
        'form': form,
        'current_fiscal_day': current_fiscal_day,
    }
    
    return render(request, 'fiscal/close_fiscal_day.html', context)


@login_required
def audit_trail(request):
    """View audit trail"""
    tenant = request.tenant
    
    # Get search form
    search_form = FiscalComplianceSearchForm(
        request.GET or None,
        tenant=tenant
    )
    
    # Base queryset
    queryset = AuditLog.objects.filter(
        tenant=tenant
    ).select_related('user', 'fiscal_series')
    
    # Apply search filters
    if search_form.is_valid():
        search_query = search_form.cleaned_data.get('search_query')
        date_from = search_form.cleaned_data.get('date_from')
        date_to = search_form.cleaned_data.get('date_to')
        user = search_form.cleaned_data.get('user')
        
        if search_query:
            queryset = queryset.filter(
                Q(object_id__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(object_type__icontains=search_query)
            )
        
        if date_from:
            queryset = queryset.filter(timestamp__date__gte=date_from)
        
        if date_to:
            queryset = queryset.filter(timestamp__date__lte=date_to)
        
        if user:
            queryset = queryset.filter(user=user)
    
    # Pagination
    paginator = Paginator(queryset, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_form': search_form,
    }
    
    return render(request, 'fiscal/audit_trail.html', context)


@login_required
def fiscal_status_api(request):
    """API endpoint for fiscal status (for AJAX updates)"""
    tenant = request.tenant
    
    try:
        fiscal_status = FiscalComplianceService.get_fiscal_status(tenant, request.user)
        return JsonResponse(fiscal_status)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)