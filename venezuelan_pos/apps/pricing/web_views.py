"""
Web views for pricing administration interface.
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count, Avg, Min, Max
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db import transaction
from decimal import Decimal
import json

from .models import PriceStage, RowPricing, PriceHistory, StageTransition
from .forms import (
    PriceStageForm, RowPricingForm, BulkRowPricingForm,
    PriceCalculationForm, PricingDashboardFilterForm
)
from .services import PricingCalculationService
from venezuelan_pos.apps.events.models import Event
from venezuelan_pos.apps.zones.models import Zone, Seat


@login_required
def pricing_dashboard(request):
    """Pricing dashboard with current stage indicators and overview."""
    
    # Filter by tenant
    if request.user.is_admin_user:
        events = Event.objects.all()
        price_stages = PriceStage.objects.all()
        row_pricing = RowPricing.objects.all()
    else:
        events = Event.objects.filter(tenant=request.user.tenant)
        price_stages = PriceStage.objects.filter(tenant=request.user.tenant)
        row_pricing = RowPricing.objects.filter(tenant=request.user.tenant)
    
    # Apply filters
    filter_form = PricingDashboardFilterForm(request.GET, user=request.user)
    if filter_form.is_valid():
        event = filter_form.cleaned_data.get('event')
        zone = filter_form.cleaned_data.get('zone')
        stage_status = filter_form.cleaned_data.get('stage_status')
        
        if event:
            price_stages = price_stages.filter(event=event)
            row_pricing = row_pricing.filter(zone__event=event)
        
        if zone:
            row_pricing = row_pricing.filter(zone=zone)
        
        if stage_status:
            now = timezone.now()
            if stage_status == 'current':
                price_stages = price_stages.filter(
                    is_active=True,
                    start_date__lte=now,
                    end_date__gte=now
                )
            elif stage_status == 'upcoming':
                price_stages = price_stages.filter(
                    is_active=True,
                    start_date__gt=now
                )
            elif stage_status == 'past':
                price_stages = price_stages.filter(end_date__lt=now)
    
    # Statistics
    now = timezone.now()
    stats = {
        'total_events': events.count(),
        'events_with_pricing': events.filter(price_stages__isnull=False).distinct().count(),
        'total_price_stages': price_stages.count(),
        'active_price_stages': price_stages.filter(is_active=True).count(),
        'current_price_stages': price_stages.filter(
            is_active=True,
            start_date__lte=now,
            end_date__gte=now
        ).count(),
        'total_row_pricing': row_pricing.count(),
        'active_row_pricing': row_pricing.filter(is_active=True).count(),
    }
    
    # Current price stages
    current_stages = price_stages.filter(
        is_active=True,
        start_date__lte=now,
        end_date__gte=now
    ).select_related('event').order_by('event__name', 'stage_order')[:10]
    
    # Upcoming price stages
    upcoming_stages = price_stages.filter(
        is_active=True,
        start_date__gt=now
    ).select_related('event').order_by('start_date')[:5]
    
    # Recent price history
    recent_history = PriceHistory.objects.filter(
        tenant=request.user.tenant if not request.user.is_admin_user else None
    ).select_related('event', 'zone', 'price_stage').order_by('-created_at')[:10]
    
    # Price stage distribution
    stage_distribution = price_stages.values('event__name').annotate(
        stage_count=Count('id'),
        avg_markup=Avg('modifier_value'),
        min_markup=Min('modifier_value'),
        max_markup=Max('modifier_value')
    ).order_by('-stage_count')[:5]
    
    context = {
        'stats': stats,
        'current_stages': current_stages,
        'upcoming_stages': upcoming_stages,
        'recent_history': recent_history,
        'stage_distribution': stage_distribution,
        'filter_form': filter_form,
    }
    
    return render(request, 'pricing/dashboard.html', context)


@login_required
def price_stage_list(request, event_id):
    """List price stages for a specific event."""
    
    if request.user.is_admin_user:
        event = get_object_or_404(Event, id=event_id)
    else:
        event = get_object_or_404(Event, id=event_id, tenant=request.user.tenant)
    
    # Get price stages for this event
    stages = event.price_stages.all().order_by('stage_order', 'start_date')
    
    # Calculate current stage
    now = timezone.now()
    current_stage = stages.filter(
        is_active=True,
        start_date__lte=now,
        end_date__gte=now
    ).first()
    
    context = {
        'event': event,
        'stages': stages,
        'current_stage': current_stage,
        'now': now,
    }
    
    return render(request, 'pricing/price_stage_list.html', context)


@login_required
def price_stage_create(request, event_id):
    """Create a new price stage for an event."""
    
    if request.user.is_admin_user:
        event = get_object_or_404(Event, id=event_id)
    else:
        event = get_object_or_404(Event, id=event_id, tenant=request.user.tenant)
    
    if request.method == 'POST':
        form = PriceStageForm(request.POST, event=event)
        if form.is_valid():
            stage = form.save(commit=False)
            stage.event = event
            if not request.user.is_admin_user:
                stage.tenant = request.user.tenant
            stage.save()
            
            messages.success(
                request,
                f'Etapa de precios "{stage.name}" creada exitosamente.'
            )
            return redirect('pricing_web:price_stage_list', event_id=event.id)
    else:
        form = PriceStageForm(event=event)
    
    context = {
        'form': form,
        'event': event,
        'stage': None,
    }
    
    return render(request, 'pricing/price_stage_form.html', context)


@login_required
def price_stage_edit(request, stage_id):
    """Edit an existing price stage."""
    
    if request.user.is_admin_user:
        stage = get_object_or_404(PriceStage, id=stage_id)
    else:
        stage = get_object_or_404(PriceStage, id=stage_id, tenant=request.user.tenant)
    
    if request.method == 'POST':
        form = PriceStageForm(request.POST, instance=stage, event=stage.event)
        if form.is_valid():
            stage = form.save()
            messages.success(
                request,
                f'Etapa de precios "{stage.name}" actualizada exitosamente.'
            )
            return redirect('pricing_web:price_stage_list', event_id=stage.event.id)
    else:
        form = PriceStageForm(instance=stage, event=stage.event)
    
    context = {
        'form': form,
        'event': stage.event,
        'stage': stage,
    }
    
    return render(request, 'pricing/price_stage_form.html', context)


@login_required
@require_http_methods(["POST"])
def price_stage_delete(request, stage_id):
    """Delete a price stage."""
    
    if request.user.is_admin_user:
        stage = get_object_or_404(PriceStage, id=stage_id)
    else:
        stage = get_object_or_404(PriceStage, id=stage_id, tenant=request.user.tenant)
    
    event_id = stage.event.id
    stage_name = stage.name
    stage.delete()
    
    messages.success(request, f'Etapa de precios "{stage_name}" eliminada exitosamente.')
    return redirect('pricing_web:price_stage_list', event_id=event_id)


@login_required
def row_pricing_list(request, zone_id):
    """List row pricing for a specific zone."""
    
    if request.user.is_admin_user:
        zone = get_object_or_404(Zone, id=zone_id)
    else:
        zone = get_object_or_404(Zone, id=zone_id, tenant=request.user.tenant)
    
    if zone.zone_type != Zone.ZoneType.NUMBERED:
        messages.error(
            request,
            'Los precios por fila solo están disponibles para zonas numeradas.'
        )
        return redirect('events:event_detail', event_id=zone.event.id)
    
    # Get row pricing for this zone
    row_pricing = zone.row_pricing.all().order_by('row_number')
    
    # Get rows without pricing
    configured_rows = set(row_pricing.values_list('row_number', flat=True))
    all_rows = set(range(1, zone.rows + 1)) if zone.rows else set()
    unconfigured_rows = sorted(all_rows - configured_rows)
    
    context = {
        'zone': zone,
        'row_pricing': row_pricing,
        'unconfigured_rows': unconfigured_rows,
        'total_rows': zone.rows,
        'configured_count': len(configured_rows),
    }
    
    return render(request, 'pricing/row_pricing_list.html', context)


@login_required
def row_pricing_create(request, zone_id):
    """Create row pricing for a zone."""
    
    if request.user.is_admin_user:
        zone = get_object_or_404(Zone, id=zone_id)
    else:
        zone = get_object_or_404(Zone, id=zone_id, tenant=request.user.tenant)
    
    if zone.zone_type != Zone.ZoneType.NUMBERED:
        messages.error(
            request,
            'Los precios por fila solo están disponibles para zonas numeradas.'
        )
        return redirect('events:event_detail', event_id=zone.event.id)
    
    if request.method == 'POST':
        form = RowPricingForm(request.POST, zone=zone)
        if form.is_valid():
            row_pricing = form.save(commit=False)
            row_pricing.zone = zone
            if not request.user.is_admin_user:
                row_pricing.tenant = request.user.tenant
            row_pricing.save()
            
            messages.success(
                request,
                f'Precio para fila {row_pricing.row_number} creado exitosamente.'
            )
            return redirect('pricing_web:row_pricing_list', zone_id=zone.id)
    else:
        form = RowPricingForm(zone=zone)
    
    context = {
        'form': form,
        'zone': zone,
        'row_pricing': None,
    }
    
    return render(request, 'pricing/row_pricing_form.html', context)


@login_required
def row_pricing_edit(request, row_pricing_id):
    """Edit existing row pricing."""
    
    if request.user.is_admin_user:
        row_pricing = get_object_or_404(RowPricing, id=row_pricing_id)
    else:
        row_pricing = get_object_or_404(
            RowPricing, id=row_pricing_id, tenant=request.user.tenant
        )
    
    if request.method == 'POST':
        form = RowPricingForm(request.POST, instance=row_pricing, zone=row_pricing.zone)
        if form.is_valid():
            row_pricing = form.save()
            messages.success(
                request,
                f'Precio para fila {row_pricing.row_number} actualizado exitosamente.'
            )
            return redirect('pricing_web:row_pricing_list', zone_id=row_pricing.zone.id)
    else:
        form = RowPricingForm(instance=row_pricing, zone=row_pricing.zone)
    
    context = {
        'form': form,
        'zone': row_pricing.zone,
        'row_pricing': row_pricing,
    }
    
    return render(request, 'pricing/row_pricing_form.html', context)


@login_required
@require_http_methods(["POST"])
def row_pricing_delete(request, row_pricing_id):
    """Delete row pricing."""
    
    if request.user.is_admin_user:
        row_pricing = get_object_or_404(RowPricing, id=row_pricing_id)
    else:
        row_pricing = get_object_or_404(
            RowPricing, id=row_pricing_id, tenant=request.user.tenant
        )
    
    zone_id = row_pricing.zone.id
    row_number = row_pricing.row_number
    row_pricing.delete()
    
    messages.success(
        request,
        f'Precio para fila {row_number} eliminado exitosamente.'
    )
    return redirect('pricing_web:row_pricing_list', zone_id=zone_id)


@login_required
def bulk_row_pricing_create(request, zone_id):
    """Create multiple row pricing entries at once."""
    
    if request.user.is_admin_user:
        zone = get_object_or_404(Zone, id=zone_id)
    else:
        zone = get_object_or_404(Zone, id=zone_id, tenant=request.user.tenant)
    
    if zone.zone_type != Zone.ZoneType.NUMBERED:
        messages.error(
            request,
            'Los precios por fila solo están disponibles para zonas numeradas.'
        )
        return redirect('events:event_detail', event_id=zone.event.id)
    
    if request.method == 'POST':
        form = BulkRowPricingForm(request.POST, zone=zone)
        if form.is_valid():
            start_row = form.cleaned_data['start_row']
            end_row = form.cleaned_data['end_row']
            percentage_markup = form.cleaned_data['percentage_markup']
            name_pattern = form.cleaned_data.get('name_pattern', '')
            
            created_count = 0
            with transaction.atomic():
                for row_num in range(start_row, end_row + 1):
                    name = ''
                    if name_pattern:
                        name = name_pattern.format(row=row_num)
                    
                    RowPricing.objects.create(
                        tenant=request.user.tenant if not request.user.is_admin_user else zone.tenant,
                        zone=zone,
                        row_number=row_num,
                        percentage_markup=percentage_markup,
                        name=name,
                        is_active=True
                    )
                    created_count += 1
            
            messages.success(
                request,
                f'Se crearon {created_count} precios por fila exitosamente.'
            )
            return redirect('pricing_web:row_pricing_list', zone_id=zone.id)
    else:
        form = BulkRowPricingForm(zone=zone)
    
    context = {
        'form': form,
        'zone': zone,
    }
    
    return render(request, 'pricing/bulk_row_pricing_form.html', context)


@login_required
def price_calculation_interface(request):
    """Price calculation interface with real-time preview."""
    
    calculation_result = None
    
    if request.method == 'POST':
        form = PriceCalculationForm(request.POST, user=request.user)
        if form.is_valid():
            event = form.cleaned_data['event']
            zone = form.cleaned_data['zone']
            row_number = form.cleaned_data.get('row_number')
            seat_number = form.cleaned_data.get('seat_number')
            calculation_date = form.cleaned_data.get('calculation_date') or timezone.now()
            
            service = PricingCalculationService()
            
            try:
                if seat_number and row_number and zone.zone_type == Zone.ZoneType.NUMBERED:
                    seat = zone.seats.get(row_number=row_number, seat_number=seat_number)
                    final_price, calculation_details = service.calculate_seat_price(
                        seat, calculation_date, create_history=False
                    )
                else:
                    final_price, calculation_details = service.calculate_zone_price(
                        zone, row_number, calculation_date, create_history=False
                    )
                
                calculation_result = calculation_details
                
            except Seat.DoesNotExist:
                messages.error(
                    request,
                    f'Asiento {seat_number} no encontrado en la fila {row_number}'
                )
            except Exception as e:
                messages.error(request, f'Error en el cálculo: {str(e)}')
    else:
        form = PriceCalculationForm(user=request.user)
    
    context = {
        'form': form,
        'calculation_result': calculation_result,
    }
    
    return render(request, 'pricing/price_calculation.html', context)


@login_required
def price_history_list(request):
    """List price calculation history with filters."""
    
    # Filter by tenant
    if request.user.is_admin_user:
        history = PriceHistory.objects.all()
    else:
        history = PriceHistory.objects.filter(tenant=request.user.tenant)
    
    history = history.select_related('event', 'zone', 'price_stage', 'row_pricing')
    
    # Filters
    event_id = request.GET.get('event')
    zone_id = request.GET.get('zone')
    price_type = request.GET.get('price_type')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if event_id:
        history = history.filter(event_id=event_id)
    
    if zone_id:
        history = history.filter(zone_id=zone_id)
    
    if price_type:
        history = history.filter(price_type=price_type)
    
    if date_from:
        history = history.filter(calculation_date__gte=date_from)
    
    if date_to:
        history = history.filter(calculation_date__lte=date_to)
    
    # Ordering
    history = history.order_by('-calculation_date', '-created_at')
    
    # Pagination
    paginator = Paginator(history, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Filter options
    if request.user.is_admin_user:
        events_for_filter = Event.objects.all().order_by('name')
        zones_for_filter = Zone.objects.all().order_by('name')
    else:
        events_for_filter = Event.objects.filter(
            tenant=request.user.tenant
        ).order_by('name')
        zones_for_filter = Zone.objects.filter(
            tenant=request.user.tenant
        ).order_by('name')
    
    context = {
        'history': page_obj,
        'events_for_filter': events_for_filter,
        'zones_for_filter': zones_for_filter,
        'price_types': PriceHistory.PriceType.choices,
        'total_history': paginator.count,
        'is_paginated': page_obj.has_other_pages(),
        'page_obj': page_obj,
    }
    
    return render(request, 'pricing/price_history_list.html', context)


# AJAX Views

@login_required
def ajax_get_zones(request):
    """AJAX endpoint to get zones for an event."""
    event_id = request.GET.get('event_id')
    
    if not event_id:
        return JsonResponse({'zones': []})
    
    try:
        if request.user.is_admin_user:
            event = Event.objects.get(id=event_id)
        else:
            event = Event.objects.get(id=event_id, tenant=request.user.tenant)
        
        zones = event.zones.filter(status=Zone.Status.ACTIVE).values(
            'id', 'name', 'zone_type', 'base_price'
        ).order_by('display_order', 'name')
        
        return JsonResponse({'zones': list(zones)})
        
    except Event.DoesNotExist:
        return JsonResponse({'zones': []})


@login_required
def stage_transition_monitoring(request):
    """Stage transition monitoring dashboard with real-time status indicators."""
    
    # Filter by tenant
    if request.user.is_admin_user:
        events = Event.objects.filter(status=Event.Status.ACTIVE)
        stages = PriceStage.objects.filter(is_active=True)
        transitions = StageTransition.objects.all()
    else:
        events = Event.objects.filter(tenant=request.user.tenant, status=Event.Status.ACTIVE)
        stages = PriceStage.objects.filter(tenant=request.user.tenant, is_active=True)
        transitions = StageTransition.objects.filter(tenant=request.user.tenant)
    
    # Get current stages with status
    from .services import HybridPricingService
    hybrid_service = HybridPricingService()
    
    current_stages = []
    upcoming_transitions = []
    
    for event in events:
        # Get event-wide current stage
        current_stage = hybrid_service.get_current_stage(event, None)
        if current_stage:
            stage_status = hybrid_service.get_stage_status(current_stage)
            stage_status['event_name'] = event.name
            stage_status['scope_display'] = 'Event-wide'
            current_stages.append(stage_status)
            
            # Check if transition is imminent
            if stage_status['should_transition']:
                upcoming_transitions.append(stage_status)
        
        # Get zone-specific current stages
        for zone in event.zones.all():
            zone_stage = hybrid_service.get_current_stage(event, zone)
            if zone_stage:
                zone_status = hybrid_service.get_stage_status(zone_stage)
                zone_status['event_name'] = event.name
                zone_status['scope_display'] = f'Zone: {zone.name}'
                zone_status['zone_name'] = zone.name
                current_stages.append(zone_status)
                
                # Check if transition is imminent
                if zone_status['should_transition']:
                    upcoming_transitions.append(zone_status)
    
    # Recent transitions
    recent_transitions = transitions.select_related(
        'event', 'zone', 'stage_from', 'stage_to'
    ).order_by('-transition_at')[:20]
    
    # Statistics
    stats = {
        'total_active_events': events.count(),
        'total_active_stages': stages.count(),
        'current_stages_count': len(current_stages),
        'upcoming_transitions_count': len(upcoming_transitions),
        'recent_transitions_count': recent_transitions.count(),
        'stages_with_quantity_limits': stages.filter(quantity_limit__isnull=False).count(),
        'auto_transition_stages': stages.filter(auto_transition=True).count(),
    }
    
    context = {
        'stats': stats,
        'current_stages': current_stages,
        'upcoming_transitions': upcoming_transitions,
        'recent_transitions': recent_transitions,
    }
    
    return render(request, 'pricing/stage_transition_monitoring.html', context)


@login_required
def stage_performance_analytics(request, event_id):
    """Stage performance analytics with transition history and sales tracking."""
    
    if request.user.is_admin_user:
        event = get_object_or_404(Event, id=event_id)
    else:
        event = get_object_or_404(Event, id=event_id, tenant=request.user.tenant)
    
    # Get all stages for this event
    stages = event.price_stages.all().order_by('stage_order', 'start_date')
    
    # Get transition history
    transitions = StageTransition.objects.filter(
        event=event
    ).select_related('stage_from', 'stage_to', 'zone').order_by('-transition_at')
    
    # Get stage sales data
    from .models import StageSales
    stage_sales = {}
    
    for stage in stages:
        sales_data = StageSales.get_stage_totals(stage)
        stage_sales[stage.id] = {
            'stage': stage,
            'tickets_sold': sales_data['tickets_sold'],
            'revenue_generated': sales_data['revenue_generated'],
            'completion_percentage': 0
        }
        
        # Calculate completion percentage if quantity limit exists
        if stage.quantity_limit and stage.quantity_limit > 0:
            completion_percentage = (sales_data['tickets_sold'] / stage.quantity_limit) * 100
            stage_sales[stage.id]['completion_percentage'] = min(completion_percentage, 100)
    
    # Get current stage status
    from .services import HybridPricingService
    hybrid_service = HybridPricingService()
    
    event_overview = hybrid_service.get_event_stage_overview(event)
    
    context = {
        'event': event,
        'stages': stages,
        'transitions': transitions,
        'stage_sales': stage_sales,
        'event_overview': event_overview,
    }
    
    return render(request, 'pricing/stage_performance_analytics.html', context)


@login_required
def ajax_get_stage_status(request):
    """AJAX endpoint to get real-time stage status."""
    stage_id = request.GET.get('stage_id')
    
    if not stage_id:
        return JsonResponse({'error': 'Stage ID required'}, status=400)
    
    try:
        if request.user.is_admin_user:
            stage = PriceStage.objects.get(id=stage_id)
        else:
            stage = PriceStage.objects.get(id=stage_id, tenant=request.user.tenant)
        
        from .services import HybridPricingService
        hybrid_service = HybridPricingService()
        stage_status = hybrid_service.get_stage_status(stage)
        
        return JsonResponse({
            'success': True,
            'status': stage_status
        })
        
    except PriceStage.DoesNotExist:
        return JsonResponse({'error': 'Stage not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def ajax_calculate_price(request):
    """AJAX endpoint for real-time price calculation."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        event_id = data.get('event_id')
        zone_id = data.get('zone_id')
        row_number = data.get('row_number')
        seat_number = data.get('seat_number')
        calculation_date = data.get('calculation_date')
        
        if not event_id or not zone_id:
            return JsonResponse({'error': 'Event and zone are required'}, status=400)
        
        # Get event and zone
        if request.user.is_admin_user:
            event = Event.objects.get(id=event_id)
            zone = Zone.objects.get(id=zone_id, event=event)
        else:
            event = Event.objects.get(id=event_id, tenant=request.user.tenant)
            zone = Zone.objects.get(id=zone_id, event=event, tenant=request.user.tenant)
        
        # Parse calculation date
        if calculation_date:
            from django.utils.dateparse import parse_datetime
            calculation_date = parse_datetime(calculation_date)
        else:
            calculation_date = timezone.now()
        
        service = PricingCalculationService()
        
        # Calculate price
        if seat_number and row_number and zone.zone_type == Zone.ZoneType.NUMBERED:
            seat = zone.seats.get(row_number=row_number, seat_number=seat_number)
            final_price, calculation_details = service.calculate_seat_price(
                seat, calculation_date, create_history=False
            )
        else:
            final_price, calculation_details = service.calculate_zone_price(
                zone, row_number, calculation_date, create_history=False
            )
        
        return JsonResponse({
            'success': True,
            'calculation': calculation_details
        })
        
    except (Event.DoesNotExist, Zone.DoesNotExist, Seat.DoesNotExist) as e:
        return JsonResponse({'error': 'Resource not found'}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)