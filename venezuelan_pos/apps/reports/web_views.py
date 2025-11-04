from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count, Sum, Avg
from django.utils import timezone
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime, timedelta
import json

from .models import SalesReport, OccupancyAnalysis, ReportSchedule
from .forms import (
    SalesReportForm, OccupancyAnalysisForm, ReportScheduleForm,
    ReportFilterForm, HeatMapConfigForm, CustomReportBuilderForm
)
from .services import ReportService
from venezuelan_pos.apps.events.models import Event
from venezuelan_pos.apps.zones.models import Zone
from venezuelan_pos.apps.sales.models import Transaction, TransactionItem


@login_required
def dashboard(request):
    """Reports and analytics dashboard."""
    
    # Filter by user tenant
    if request.user.is_admin_user:
        reports = SalesReport.objects.all()
        analyses = OccupancyAnalysis.objects.all()
        schedules = ReportSchedule.objects.all()
        transactions = Transaction.objects.filter(status=Transaction.Status.COMPLETED)
    else:
        reports = SalesReport.objects.filter(tenant=request.user.tenant)
        analyses = OccupancyAnalysis.objects.filter(tenant=request.user.tenant)
        schedules = ReportSchedule.objects.filter(tenant=request.user.tenant)
        transactions = Transaction.objects.filter(
            tenant=request.user.tenant,
            status=Transaction.Status.COMPLETED
        )
    
    # Dashboard statistics
    stats = {
        'total_reports': reports.count(),
        'completed_reports': reports.filter(status=SalesReport.Status.COMPLETED).count(),
        'pending_reports': reports.filter(status=SalesReport.Status.GENERATING).count(),
        'failed_reports': reports.filter(status=SalesReport.Status.FAILED).count(),
        'total_analyses': analyses.count(),
        'active_schedules': schedules.filter(status=ReportSchedule.Status.ACTIVE).count(),
        'due_schedules': schedules.filter(
            status=ReportSchedule.Status.ACTIVE,
            next_run__lte=timezone.now()
        ).count(),
    }
    
    # Recent activity
    recent_reports = reports.order_by('-created_at')[:5]
    recent_analyses = analyses.order_by('-created_at')[:5]
    
    # Quick metrics (last 30 days)
    thirty_days_ago = timezone.now() - timedelta(days=30)
    recent_transactions = transactions.filter(completed_at__gte=thirty_days_ago)
    
    quick_metrics = recent_transactions.aggregate(
        total_revenue=Sum('total_amount'),
        total_transactions=Count('id'),
        total_tickets=Sum('items__quantity'),
        avg_transaction_value=Avg('total_amount')
    )
    
    # Handle None values
    for key, value in quick_metrics.items():
        if value is None:
            quick_metrics[key] = 0
    
    # Top performing zones (last 30 days)
    if request.user.is_admin_user:
        zones = Zone.objects.all()
    else:
        zones = Zone.objects.filter(tenant=request.user.tenant)
    
    top_zones = []
    for zone in zones[:10]:  # Limit to top 10 for performance
        zone_items = TransactionItem.objects.filter(
            zone=zone,
            transaction__status=Transaction.Status.COMPLETED,
            transaction__completed_at__gte=thirty_days_ago
        )
        
        zone_stats = zone_items.aggregate(
            tickets_sold=Sum('quantity'),
            revenue=Sum('total_price')
        )
        
        if zone_stats['tickets_sold']:
            fill_rate = (zone_stats['tickets_sold'] / zone.capacity * 100) if zone.capacity > 0 else 0
            top_zones.append({
                'zone': zone,
                'tickets_sold': zone_stats['tickets_sold'] or 0,
                'revenue': zone_stats['revenue'] or 0,
                'fill_rate': round(fill_rate, 2)
            })
    
    # Sort by revenue and take top 5
    top_zones = sorted(top_zones, key=lambda x: x['revenue'], reverse=True)[:5]
    
    context = {
        'stats': stats,
        'recent_reports': recent_reports,
        'recent_analyses': recent_analyses,
        'quick_metrics': quick_metrics,
        'top_zones': top_zones,
        'today': timezone.now(),
    }
    
    return render(request, 'reports/dashboard.html', context)


@login_required
def sales_reports_list(request):
    """List of sales reports with filtering."""
    
    # Filter by tenant
    if request.user.is_admin_user:
        reports = SalesReport.objects.all()
    else:
        reports = SalesReport.objects.filter(tenant=request.user.tenant)
    
    reports = reports.select_related('generated_by').order_by('-created_at')
    
    # Apply filters
    filter_form = ReportFilterForm(request.GET)
    if filter_form.is_valid():
        search = filter_form.cleaned_data.get('search')
        report_type = filter_form.cleaned_data.get('report_type')
        status = filter_form.cleaned_data.get('status')
        date_from = filter_form.cleaned_data.get('date_from')
        date_to = filter_form.cleaned_data.get('date_to')
        
        if search:
            reports = reports.filter(
                Q(name__icontains=search) |
                Q(generated_by__username__icontains=search)
            )
        
        if report_type:
            reports = reports.filter(report_type=report_type)
        
        if status:
            reports = reports.filter(status=status)
        
        if date_from:
            reports = reports.filter(created_at__date__gte=date_from)
        
        if date_to:
            reports = reports.filter(created_at__date__lte=date_to)
    
    # Pagination
    paginator = Paginator(reports, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'reports': page_obj,
        'filter_form': filter_form,
        'total_reports': paginator.count,
        'is_paginated': page_obj.has_other_pages(),
        'page_obj': page_obj,
    }
    
    return render(request, 'reports/sales_reports_list.html', context)


@login_required
def sales_report_detail(request, report_id):
    """Detail view for a sales report."""
    
    if request.user.is_admin_user:
        report = get_object_or_404(SalesReport, id=report_id)
    else:
        report = get_object_or_404(SalesReport, id=report_id, tenant=request.user.tenant)
    
    context = {
        'report': report,
    }
    
    return render(request, 'reports/sales_report_detail.html', context)


@login_required
def sales_report_create(request):
    """Create a new sales report."""
    
    if request.method == 'POST':
        form = SalesReportForm(request.POST, user=request.user)
        if form.is_valid():
            # Get filters from form
            filters = form.get_filters()
            
            # Create report using manager method
            report = SalesReport.objects.create_sales_report(
                tenant=request.user.tenant,
                report_type=form.cleaned_data['report_type'],
                filters=filters,
                name=form.cleaned_data['name'],
                period_start=filters.get('start_date'),
                period_end=filters.get('end_date'),
                generated_by=request.user
            )
            
            # Generate detailed data
            detailed_data = ReportService.generate_sales_report_data(
                tenant=request.user.tenant,
                filters=filters
            )
            
            report.detailed_data = detailed_data
            report.mark_completed()
            
            messages.success(request, f'Reporte "{report.name}" generado exitosamente.')
            return redirect('reports:sales_report_detail', report_id=report.id)
    else:
        form = SalesReportForm(user=request.user)
    
    context = {
        'form': form,
        'report': None,
    }
    
    return render(request, 'reports/sales_report_form.html', context)


@login_required
def occupancy_analysis_list(request):
    """List of occupancy analyses."""
    
    # Filter by tenant
    if request.user.is_admin_user:
        analyses = OccupancyAnalysis.objects.all()
    else:
        analyses = OccupancyAnalysis.objects.filter(tenant=request.user.tenant)
    
    analyses = analyses.select_related('event', 'zone', 'generated_by').order_by('-created_at')
    
    # Apply filters
    search = request.GET.get('search', '')
    analysis_type = request.GET.get('analysis_type', '')
    event_id = request.GET.get('event_id', '')
    
    if search:
        analyses = analyses.filter(
            Q(name__icontains=search) |
            Q(event__name__icontains=search) |
            Q(zone__name__icontains=search)
        )
    
    if analysis_type:
        analyses = analyses.filter(analysis_type=analysis_type)
    
    if event_id:
        analyses = analyses.filter(event_id=event_id)
    
    # Pagination
    paginator = Paginator(analyses, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Events for filter
    if request.user.is_admin_user:
        events_for_filter = Event.objects.all().order_by('-start_date')
    else:
        events_for_filter = Event.objects.filter(tenant=request.user.tenant).order_by('-start_date')
    
    context = {
        'analyses': page_obj,
        'events_for_filter': events_for_filter,
        'total_analyses': paginator.count,
        'is_paginated': page_obj.has_other_pages(),
        'page_obj': page_obj,
    }
    
    return render(request, 'reports/occupancy_analysis_list.html', context)


@login_required
def occupancy_analysis_detail(request, analysis_id):
    """Detail view for occupancy analysis."""
    
    if request.user.is_admin_user:
        analysis = get_object_or_404(OccupancyAnalysis, id=analysis_id)
    else:
        analysis = get_object_or_404(OccupancyAnalysis, id=analysis_id, tenant=request.user.tenant)
    
    context = {
        'analysis': analysis,
    }
    
    return render(request, 'reports/occupancy_analysis_detail.html', context)


@login_required
def occupancy_analysis_create(request):
    """Create a new occupancy analysis."""
    
    if request.method == 'POST':
        form = OccupancyAnalysisForm(request.POST, user=request.user)
        if form.is_valid():
            analysis = form.save(commit=False)
            analysis.tenant = request.user.tenant
            analysis.generated_by = request.user
            
            # Set analysis period
            period_days = form.cleaned_data.get('analysis_period_days', 30)
            analysis.analysis_end = timezone.now()
            analysis.analysis_start = analysis.analysis_end - timedelta(days=period_days)
            
            # Generate analysis using manager method
            if analysis.zone:
                analysis = OccupancyAnalysis.objects.create_occupancy_analysis(
                    tenant=request.user.tenant,
                    event=analysis.event,
                    zone=analysis.zone,
                    name=analysis.name,
                    analysis_type=analysis.analysis_type,
                    generated_by=request.user
                )
            else:
                analysis.save()
            
            messages.success(request, f'Análisis "{analysis.name}" generado exitosamente.')
            return redirect('reports:occupancy_analysis_detail', analysis_id=analysis.id)
    else:
        form = OccupancyAnalysisForm(user=request.user)
    
    context = {
        'form': form,
        'analysis': None,
    }
    
    return render(request, 'reports/occupancy_analysis_form.html', context)


@login_required
def heat_map_generator(request):
    """Heat map generator interface."""
    
    if request.method == 'POST':
        form = HeatMapConfigForm(request.POST, user=request.user)
        if form.is_valid():
            zone = form.cleaned_data['zone']
            event = form.cleaned_data.get('event')
            
            # Generate heat map data
            heat_map_data = ReportService.generate_occupancy_heat_map(zone, event)
            
            context = {
                'form': form,
                'heat_map_data': heat_map_data,
                'zone': zone,
                'event': event,
                'show_prices': form.cleaned_data['show_prices'],
                'show_sales_count': form.cleaned_data['show_sales_count'],
                'color_scheme': form.cleaned_data['color_scheme'],
            }
            
            return render(request, 'reports/heat_map_result.html', context)
    else:
        form = HeatMapConfigForm(user=request.user)
    
    context = {
        'form': form,
    }
    
    return render(request, 'reports/heat_map_generator.html', context)


@login_required
def custom_report_builder(request):
    """Custom report builder with drag-and-drop interface."""
    
    if request.method == 'POST':
        form = CustomReportBuilderForm(request.POST, user=request.user)
        if form.is_valid():
            # Process form data and generate custom report
            filters = {}
            
            # Handle date range
            date_range_type = form.cleaned_data['date_range_type']
            if date_range_type == 'custom':
                filters['start_date'] = timezone.make_aware(
                    datetime.combine(form.cleaned_data['custom_start_date'], datetime.min.time())
                )
                filters['end_date'] = timezone.make_aware(
                    datetime.combine(form.cleaned_data['custom_end_date'], datetime.max.time())
                )
            else:
                # Calculate date range based on type
                end_date = timezone.now()
                if date_range_type == 'last_7_days':
                    start_date = end_date - timedelta(days=7)
                elif date_range_type == 'last_30_days':
                    start_date = end_date - timedelta(days=30)
                elif date_range_type == 'last_90_days':
                    start_date = end_date - timedelta(days=90)
                elif date_range_type == 'this_month':
                    start_date = end_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                elif date_range_type == 'last_month':
                    first_day_this_month = end_date.replace(day=1)
                    end_date = first_day_this_month - timedelta(days=1)
                    start_date = end_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                else:
                    start_date = end_date - timedelta(days=30)
                
                filters['start_date'] = start_date
                filters['end_date'] = end_date
            
            # Add event and zone filters
            events = form.cleaned_data.get('events')
            if events:
                filters['event_ids'] = [str(event.id) for event in events]
            
            zones = form.cleaned_data.get('zones')
            if zones:
                filters['zone_ids'] = [str(zone.id) for zone in zones]
            
            # Generate report data
            report_data = ReportService.generate_sales_report_data(
                tenant=request.user.tenant,
                filters=filters
            )
            
            # Create report record
            report = SalesReport.objects.create(
                tenant=request.user.tenant,
                name=form.cleaned_data['report_name'],
                report_type=SalesReport.ReportType.CUSTOM,
                filters=filters,
                period_start=filters.get('start_date'),
                period_end=filters.get('end_date'),
                generated_by=request.user,
                detailed_data=report_data,
                status=SalesReport.Status.COMPLETED
            )
            
            context = {
                'form': form,
                'report': report,
                'report_data': report_data,
                'group_by': form.cleaned_data.get('group_by', []),
                'metrics': form.cleaned_data.get('metrics', []),
                'include_charts': form.cleaned_data.get('include_charts', True),
            }
            
            return render(request, 'reports/custom_report_result.html', context)
    else:
        form = CustomReportBuilderForm(user=request.user)
    
    context = {
        'form': form,
    }
    
    return render(request, 'reports/custom_report_builder.html', context)


@login_required
def report_schedules_list(request):
    """List of report schedules."""
    
    # Filter by tenant
    if request.user.is_admin_user:
        schedules = ReportSchedule.objects.all()
    else:
        schedules = ReportSchedule.objects.filter(tenant=request.user.tenant)
    
    schedules = schedules.select_related('created_by').order_by('next_run')
    
    # Apply filters
    search = request.GET.get('search', '')
    status = request.GET.get('status', '')
    frequency = request.GET.get('frequency', '')
    
    if search:
        schedules = schedules.filter(
            Q(name__icontains=search) |
            Q(description__icontains=search)
        )
    
    if status:
        schedules = schedules.filter(status=status)
    
    if frequency:
        schedules = schedules.filter(frequency=frequency)
    
    # Pagination
    paginator = Paginator(schedules, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'schedules': page_obj,
        'total_schedules': paginator.count,
        'is_paginated': page_obj.has_other_pages(),
        'page_obj': page_obj,
    }
    
    return render(request, 'reports/report_schedules_list.html', context)


@login_required
def report_schedule_detail(request, schedule_id):
    """Detail view for report schedule."""
    
    if request.user.is_admin_user:
        schedule = get_object_or_404(ReportSchedule, id=schedule_id)
    else:
        schedule = get_object_or_404(ReportSchedule, id=schedule_id, tenant=request.user.tenant)
    
    # Get recent reports generated by this schedule
    recent_reports = SalesReport.objects.filter(
        tenant=schedule.tenant,
        name__icontains=schedule.name
    ).order_by('-created_at')[:10]
    
    context = {
        'schedule': schedule,
        'recent_reports': recent_reports,
    }
    
    return render(request, 'reports/report_schedule_detail.html', context)


@login_required
def report_schedule_create(request):
    """Create a new report schedule."""
    
    if request.method == 'POST':
        form = ReportScheduleForm(request.POST)
        if form.is_valid():
            schedule = form.save(commit=False)
            schedule.tenant = request.user.tenant
            schedule.created_by = request.user
            schedule.save()
            
            messages.success(request, f'Programación "{schedule.name}" creada exitosamente.')
            return redirect('reports:report_schedule_detail', schedule_id=schedule.id)
    else:
        form = ReportScheduleForm()
    
    context = {
        'form': form,
        'schedule': None,
    }
    
    return render(request, 'reports/report_schedule_form.html', context)


@login_required
def report_schedule_edit(request, schedule_id):
    """Edit an existing report schedule."""
    
    if request.user.is_admin_user:
        schedule = get_object_or_404(ReportSchedule, id=schedule_id)
    else:
        schedule = get_object_or_404(ReportSchedule, id=schedule_id, tenant=request.user.tenant)
    
    if request.method == 'POST':
        form = ReportScheduleForm(request.POST, instance=schedule)
        if form.is_valid():
            schedule = form.save()
            messages.success(request, f'Programación "{schedule.name}" actualizada exitosamente.')
            return redirect('reports:report_schedule_detail', schedule_id=schedule.id)
    else:
        form = ReportScheduleForm(instance=schedule)
    
    context = {
        'form': form,
        'schedule': schedule,
    }
    
    return render(request, 'reports/report_schedule_form.html', context)


@login_required
@require_http_methods(["POST"])
def report_schedule_execute(request, schedule_id):
    """Execute a report schedule immediately."""
    
    if request.user.is_admin_user:
        schedule = get_object_or_404(ReportSchedule, id=schedule_id)
    else:
        schedule = get_object_or_404(ReportSchedule, id=schedule_id, tenant=request.user.tenant)
    
    if not schedule.is_active:
        messages.error(request, 'La programación no está activa.')
        return redirect('reports:report_schedule_detail', schedule_id=schedule.id)
    
    try:
        report = schedule.execute()
        if report:
            messages.success(request, f'Programación ejecutada exitosamente. Reporte generado: {report.name}')
        else:
            messages.error(request, 'Error al ejecutar la programación.')
    except Exception as e:
        messages.error(request, f'Error al ejecutar la programación: {str(e)}')
    
    return redirect('reports:report_schedule_detail', schedule_id=schedule.id)


@login_required
@require_http_methods(["POST"])
def report_schedule_toggle_status(request, schedule_id):
    """Toggle schedule status (active/paused)."""
    
    if request.user.is_admin_user:
        schedule = get_object_or_404(ReportSchedule, id=schedule_id)
    else:
        schedule = get_object_or_404(ReportSchedule, id=schedule_id, tenant=request.user.tenant)
    
    if schedule.status == ReportSchedule.Status.ACTIVE:
        schedule.status = ReportSchedule.Status.PAUSED
        messages.success(request, f'Programación "{schedule.name}" pausada.')
    else:
        schedule.status = ReportSchedule.Status.ACTIVE
        messages.success(request, f'Programación "{schedule.name}" activada.')
    
    schedule.save(update_fields=['status'])
    
    return redirect('reports:report_schedule_detail', schedule_id=schedule.id)


@login_required
def analytics_dashboard(request):
    """Advanced analytics dashboard with real-time metrics."""
    
    # Get tenant-filtered data
    if request.user.is_admin_user:
        events = Event.objects.all()
        zones = Zone.objects.all()
        transactions = Transaction.objects.filter(status=Transaction.Status.COMPLETED)
    else:
        events = Event.objects.filter(tenant=request.user.tenant)
        zones = Zone.objects.filter(tenant=request.user.tenant)
        transactions = Transaction.objects.filter(
            tenant=request.user.tenant,
            status=Transaction.Status.COMPLETED
        )
    
    # Time periods for analysis
    now = timezone.now()
    periods = {
        'today': now.replace(hour=0, minute=0, second=0, microsecond=0),
        'week': now - timedelta(days=7),
        'month': now - timedelta(days=30),
        'quarter': now - timedelta(days=90),
    }
    
    # Calculate metrics for each period
    metrics = {}
    for period_name, start_date in periods.items():
        period_transactions = transactions.filter(completed_at__gte=start_date)
        period_items = TransactionItem.objects.filter(
            transaction__in=period_transactions
        )
        
        metrics[period_name] = {
            'revenue': period_transactions.aggregate(Sum('total_amount'))['total_amount__sum'] or 0,
            'transactions': period_transactions.count(),
            'tickets': period_items.aggregate(Sum('quantity'))['quantity__sum'] or 0,
            'avg_transaction': period_transactions.aggregate(Avg('total_amount'))['total_amount__avg'] or 0,
        }
    
    # Top performing events
    top_events = []
    for event in events.order_by('-start_date')[:10]:
        event_transactions = transactions.filter(event=event)
        event_stats = event_transactions.aggregate(
            revenue=Sum('total_amount'),
            transactions=Count('id'),
            tickets=Sum('items__quantity')
        )
        
        if event_stats['revenue']:
            top_events.append({
                'event': event,
                'revenue': event_stats['revenue'] or 0,
                'transactions': event_stats['transactions'] or 0,
                'tickets': event_stats['tickets'] or 0,
            })
    
    top_events = sorted(top_events, key=lambda x: x['revenue'], reverse=True)[:5]
    
    # Zone performance ranking
    zone_ranking = ReportService.generate_zone_popularity_ranking(
        tenant=request.user.tenant,
        limit=10
    )
    
    # Sales trends (last 30 days)
    sales_trends = []
    for i in range(30):
        day = now - timedelta(days=i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        
        day_transactions = transactions.filter(
            completed_at__gte=day_start,
            completed_at__lt=day_end
        )
        
        day_stats = day_transactions.aggregate(
            revenue=Sum('total_amount'),
            transactions=Count('id')
        )
        
        sales_trends.append({
            'date': day.date().isoformat(),
            'revenue': float(day_stats['revenue'] or 0),
            'transactions': day_stats['transactions'] or 0,
        })
    
    sales_trends.reverse()  # Chronological order
    
    context = {
        'metrics': metrics,
        'top_events': top_events,
        'zone_ranking': zone_ranking,
        'sales_trends': sales_trends,
        'total_events': events.count(),
        'total_zones': zones.count(),
        'active_events': events.filter(status=Event.Status.ACTIVE).count(),
    }
    
    return render(request, 'reports/analytics_dashboard.html', context)


# AJAX endpoints for real-time data

@login_required
def ajax_zone_performance(request):
    """AJAX endpoint for zone performance data."""
    
    zone_id = request.GET.get('zone_id')
    period_days = int(request.GET.get('period_days', 30))
    
    if not zone_id:
        return JsonResponse({'error': 'zone_id required'}, status=400)
    
    try:
        if request.user.is_admin_user:
            zone = Zone.objects.get(id=zone_id)
        else:
            zone = Zone.objects.get(id=zone_id, tenant=request.user.tenant)
        
        metrics = ReportService.calculate_zone_performance_metrics(
            zone=zone,
            period_days=period_days
        )
        
        return JsonResponse(metrics)
        
    except Zone.DoesNotExist:
        return JsonResponse({'error': 'Zone not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def ajax_heat_map_data(request):
    """AJAX endpoint for heat map data."""
    
    zone_id = request.GET.get('zone_id')
    event_id = request.GET.get('event_id')
    
    if not zone_id:
        return JsonResponse({'error': 'zone_id required'}, status=400)
    
    try:
        if request.user.is_admin_user:
            zone = Zone.objects.get(id=zone_id)
        else:
            zone = Zone.objects.get(id=zone_id, tenant=request.user.tenant)
        
        event = None
        if event_id:
            if request.user.is_admin_user:
                event = Event.objects.get(id=event_id)
            else:
                event = Event.objects.get(id=event_id, tenant=request.user.tenant)
        
        heat_map_data = ReportService.generate_occupancy_heat_map(zone, event)
        
        return JsonResponse(heat_map_data)
        
    except (Zone.DoesNotExist, Event.DoesNotExist):
        return JsonResponse({'error': 'Zone or Event not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def ajax_sales_trends(request):
    """AJAX endpoint for sales trends data."""
    
    days = int(request.GET.get('days', 30))
    event_id = request.GET.get('event_id')
    
    # Filter transactions by tenant
    if request.user.is_admin_user:
        transactions = Transaction.objects.filter(status=Transaction.Status.COMPLETED)
    else:
        transactions = Transaction.objects.filter(
            tenant=request.user.tenant,
            status=Transaction.Status.COMPLETED
        )
    
    if event_id:
        transactions = transactions.filter(event_id=event_id)
    
    # Generate daily trends
    trends = []
    now = timezone.now()
    
    for i in range(days):
        day = now - timedelta(days=i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        
        day_transactions = transactions.filter(
            completed_at__gte=day_start,
            completed_at__lt=day_end
        )
        
        day_stats = day_transactions.aggregate(
            revenue=Sum('total_amount'),
            transactions=Count('id'),
            tickets=Sum('items__quantity')
        )
        
        trends.append({
            'date': day.date().isoformat(),
            'revenue': float(day_stats['revenue'] or 0),
            'transactions': day_stats['transactions'] or 0,
            'tickets': day_stats['tickets'] or 0,
        })
    
    trends.reverse()  # Chronological order
    
    return JsonResponse({'trends': trends})


@login_required
def ajax_real_time_metrics(request):
    """AJAX endpoint for real-time dashboard metrics."""
    
    # Filter by tenant
    if request.user.is_admin_user:
        transactions = Transaction.objects.filter(status=Transaction.Status.COMPLETED)
        reports = SalesReport.objects.all()
    else:
        transactions = Transaction.objects.filter(
            tenant=request.user.tenant,
            status=Transaction.Status.COMPLETED
        )
        reports = SalesReport.objects.filter(tenant=request.user.tenant)
    
    # Today's metrics
    today = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_transactions = transactions.filter(completed_at__gte=today)
    
    today_stats = today_transactions.aggregate(
        revenue=Sum('total_amount'),
        transactions=Count('id'),
        tickets=Sum('items__quantity')
    )
    
    # This week's metrics
    week_start = today - timedelta(days=today.weekday())
    week_transactions = transactions.filter(completed_at__gte=week_start)
    
    week_stats = week_transactions.aggregate(
        revenue=Sum('total_amount'),
        transactions=Count('id'),
        tickets=Sum('items__quantity')
    )
    
    # Report statistics
    report_stats = {
        'total': reports.count(),
        'completed': reports.filter(status=SalesReport.Status.COMPLETED).count(),
        'pending': reports.filter(status=SalesReport.Status.GENERATING).count(),
        'failed': reports.filter(status=SalesReport.Status.FAILED).count(),
    }
    
    return JsonResponse({
        'today': {
            'revenue': float(today_stats['revenue'] or 0),
            'transactions': today_stats['transactions'] or 0,
            'tickets': today_stats['tickets'] or 0,
        },
        'week': {
            'revenue': float(week_stats['revenue'] or 0),
            'transactions': week_stats['transactions'] or 0,
            'tickets': week_stats['tickets'] or 0,
        },
        'reports': report_stats,
        'timestamp': timezone.now().isoformat(),
    })