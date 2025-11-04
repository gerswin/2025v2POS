from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q, Count
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from datetime import datetime, timedelta

from .models import Venue, Event, EventConfiguration
from .forms import VenueForm, EventForm, EventConfigurationForm


@login_required
def dashboard(request):
    """Dashboard principal para tenant admins."""
    
    # Filtrar por tenant del usuario
    if request.user.is_admin_user:
        venues = Venue.objects.all()
        events = Event.objects.all()
    else:
        venues = Venue.objects.filter(tenant=request.user.tenant)
        events = Event.objects.filter(tenant=request.user.tenant)
    
    # Estadísticas
    stats = {
        'total_venues': venues.count(),
        'active_venues': venues.filter(is_active=True).count(),
        'total_events': events.count(),
        'active_events': events.filter(status=Event.Status.ACTIVE).count(),
        'upcoming_events': events.filter(
            start_date__gt=timezone.now(),
            status=Event.Status.ACTIVE
        ).count(),
        'draft_events': events.filter(status=Event.Status.DRAFT).count(),
    }
    
    # Eventos recientes
    recent_events = events.select_related('venue').order_by('-created_at')[:5]
    
    # Top venues (con más eventos)
    top_venues = venues.annotate(
        events_count=Count('events')
    ).order_by('-events_count')[:5]
    
    context = {
        'stats': stats,
        'recent_events': recent_events,
        'top_venues': top_venues,
        'today': timezone.now(),
    }
    
    return render(request, 'events/dashboard.html', context)


@login_required
def venue_list(request):
    """Lista de venues con filtros y búsqueda."""
    
    # Filtrar por tenant del usuario
    if request.user.is_admin_user:
        venues = Venue.objects.all()
    else:
        venues = Venue.objects.filter(tenant=request.user.tenant)
    
    # Agregar conteo de eventos
    venues = venues.annotate(events_count=Count('events'))
    
    # Filtros
    search = request.GET.get('search', '')
    venue_type = request.GET.get('venue_type', '')
    city = request.GET.get('city', '')
    is_active = request.GET.get('is_active', '')
    
    if search:
        venues = venues.filter(
            Q(name__icontains=search) |
            Q(city__icontains=search) |
            Q(address__icontains=search) |
            Q(contact_email__icontains=search)
        )
    
    if venue_type:
        venues = venues.filter(venue_type=venue_type)
    
    if city:
        venues = venues.filter(city=city)
    
    if is_active:
        venues = venues.filter(is_active=is_active.lower() == 'true')
    
    # Ordenamiento
    venues = venues.order_by('name')
    
    # Paginación
    paginator = Paginator(venues, 12)  # 12 venues por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Ciudades para el filtro
    if request.user.is_admin_user:
        cities = Venue.objects.values_list('city', flat=True).distinct().order_by('city')
    else:
        cities = Venue.objects.filter(tenant=request.user.tenant).values_list('city', flat=True).distinct().order_by('city')
    
    context = {
        'venues': page_obj,
        'cities': cities,
        'total_venues': paginator.count,
        'is_paginated': page_obj.has_other_pages(),
        'page_obj': page_obj,
    }
    
    return render(request, 'events/venue_list.html', context)


@login_required
def venue_detail(request, venue_id):
    """Detalle de una venue específica."""
    
    if request.user.is_admin_user:
        venue = get_object_or_404(Venue, id=venue_id)
    else:
        venue = get_object_or_404(Venue, id=venue_id, tenant=request.user.tenant)
    
    # Eventos de esta venue
    events = venue.events.all().order_by('-start_date')
    
    # Estadísticas de la venue
    stats = {
        'total_events': events.count(),
        'active_events': events.filter(status=Event.Status.ACTIVE).count(),
        'upcoming_events': events.filter(
            start_date__gt=timezone.now(),
            status=Event.Status.ACTIVE
        ).count(),
        'past_events': events.filter(end_date__lt=timezone.now()).count(),
    }
    
    context = {
        'venue': venue,
        'events': events[:10],  # Últimos 10 eventos
        'stats': stats,
    }
    
    return render(request, 'events/venue_detail.html', context)


@login_required
def venue_create(request):
    """Crear nueva venue."""
    
    if request.method == 'POST':
        form = VenueForm(request.POST)
        if form.is_valid():
            venue = form.save(commit=False)
            if not request.user.is_admin_user:
                venue.tenant = request.user.tenant
            venue.save()
            
            messages.success(request, f'Venue "{venue.name}" creada exitosamente.')
            return redirect('events:venue_detail', venue_id=venue.id)
    else:
        form = VenueForm()
    
    context = {
        'form': form,
        'venue': None,
    }
    
    return render(request, 'events/venue_form.html', context)


@login_required
def venue_edit(request, venue_id):
    """Editar venue existente."""
    
    if request.user.is_admin_user:
        venue = get_object_or_404(Venue, id=venue_id)
    else:
        venue = get_object_or_404(Venue, id=venue_id, tenant=request.user.tenant)
    
    if request.method == 'POST':
        form = VenueForm(request.POST, instance=venue)
        if form.is_valid():
            venue = form.save()
            messages.success(request, f'Venue "{venue.name}" actualizada exitosamente.')
            return redirect('events:venue_detail', venue_id=venue.id)
    else:
        form = VenueForm(instance=venue)
    
    context = {
        'form': form,
        'venue': venue,
    }
    
    return render(request, 'events/venue_form.html', context)


@login_required
@require_http_methods(["POST"])
def venue_delete(request, venue_id):
    """Eliminar venue."""
    
    if request.user.is_admin_user:
        venue = get_object_or_404(Venue, id=venue_id)
    else:
        venue = get_object_or_404(Venue, id=venue_id, tenant=request.user.tenant)
    
    # Verificar si tiene eventos asociados
    if venue.events.exists():
        messages.error(
            request, 
            f'No se puede eliminar la venue "{venue.name}" porque tiene eventos asociados.'
        )
        return redirect('events:venue_detail', venue_id=venue.id)
    
    venue_name = venue.name
    venue.delete()
    
    messages.success(request, f'Venue "{venue_name}" eliminada exitosamente.')
    return redirect('events:venue_list')


@login_required
def event_list(request):
    """Lista de eventos con filtros y búsqueda."""
    
    # Filtrar por tenant del usuario
    if request.user.is_admin_user:
        events = Event.objects.all()
    else:
        events = Event.objects.filter(tenant=request.user.tenant)
    
    events = events.select_related('venue')
    
    # Filtros
    search = request.GET.get('search', '')
    event_type = request.GET.get('event_type', '')
    status = request.GET.get('status', '')
    venue_id = request.GET.get('venue', '')
    
    if search:
        events = events.filter(
            Q(name__icontains=search) |
            Q(description__icontains=search) |
            Q(venue__name__icontains=search)
        )
    
    if event_type:
        events = events.filter(event_type=event_type)
    
    if status:
        events = events.filter(status=status)
    
    if venue_id:
        events = events.filter(venue_id=venue_id)
    
    # Ordenamiento
    events = events.order_by('-start_date')
    
    # Paginación
    paginator = Paginator(events, 10)  # 10 eventos por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Venues para el filtro
    if request.user.is_admin_user:
        venues_for_filter = Venue.objects.filter(is_active=True).order_by('name')
    else:
        venues_for_filter = Venue.objects.filter(
            tenant=request.user.tenant, 
            is_active=True
        ).order_by('name')
    
    context = {
        'events': page_obj,
        'venues_for_filter': venues_for_filter,
        'total_events': paginator.count,
        'is_paginated': page_obj.has_other_pages(),
        'page_obj': page_obj,
    }
    
    return render(request, 'events/event_list.html', context)


@login_required
def event_detail(request, event_id):
    """Detalle de un evento específico."""
    
    if request.user.is_admin_user:
        event = get_object_or_404(Event.objects.select_related('venue'), id=event_id)
    else:
        event = get_object_or_404(
            Event.objects.select_related('venue'), 
            id=event_id, 
            tenant=request.user.tenant
        )
    
    # Configuración del evento
    try:
        config = event.event_configuration
    except EventConfiguration.DoesNotExist:
        config = None
    
    context = {
        'event': event,
        'config': config,
    }
    
    return render(request, 'events/event_detail.html', context)


@login_required
def event_create(request):
    """Crear nuevo evento."""
    
    if request.method == 'POST':
        form = EventForm(request.POST, user=request.user)
        config_form = EventConfigurationForm(request.POST)
        if form.is_valid() and config_form.is_valid():
            with transaction.atomic():
                event = form.save(commit=False)
                if not request.user.is_admin_user:
                    event.tenant = request.user.tenant
                event.save()
                
                config = config_form.save(commit=False)
                config.event = event
                config.tenant = event.tenant
                config.save()
            
            messages.success(request, f'Evento "{event.name}" creado exitosamente.')
            return redirect('events:event_detail', event_id=event.id)
    else:
        form = EventForm(user=request.user)
        config_form = EventConfigurationForm()
    
    context = {
        'form': form,
        'event': None,
        'event_configuration_form': config_form,
    }
    
    return render(request, 'events/event_form.html', context)


@login_required
def event_edit(request, event_id):
    """Editar evento existente."""
    
    if request.user.is_admin_user:
        event = get_object_or_404(Event, id=event_id)
    else:
        event = get_object_or_404(Event, id=event_id, tenant=request.user.tenant)
    
    config, _ = EventConfiguration.objects.get_or_create(
        event=event,
        defaults={'tenant': event.tenant}
    )
    
    if request.method == 'POST':
        form = EventForm(request.POST, instance=event, user=request.user)
        config_form = EventConfigurationForm(request.POST, instance=config)
        if form.is_valid() and config_form.is_valid():
            with transaction.atomic():
                event = form.save()
                config = config_form.save(commit=False)
                config.event = event
                config.tenant = event.tenant
                config.save()
            
            messages.success(request, f'Evento "{event.name}" actualizado exitosamente.')
            return redirect('events:event_detail', event_id=event.id)
    else:
        form = EventForm(instance=event, user=request.user)
        config_form = EventConfigurationForm(instance=config)
    
    context = {
        'form': form,
        'event': event,
        'event_configuration_form': config_form,
    }
    
    return render(request, 'events/event_form.html', context)


@login_required
@require_http_methods(["POST"])
def event_delete(request, event_id):
    """Eliminar evento."""
    
    if request.user.is_admin_user:
        event = get_object_or_404(Event, id=event_id)
    else:
        event = get_object_or_404(Event, id=event_id, tenant=request.user.tenant)
    
    event_name = event.name
    event.delete()
    
    messages.success(request, f'Evento "{event_name}" eliminado exitosamente.')
    return redirect('events:event_list')


@login_required
@require_http_methods(["POST"])
def event_activate(request, event_id):
    """Activar evento."""
    
    if request.user.is_admin_user:
        event = get_object_or_404(Event, id=event_id)
    else:
        event = get_object_or_404(Event, id=event_id, tenant=request.user.tenant)
    
    if event.status == Event.Status.CANCELLED:
        messages.error(request, 'No se puede activar un evento cancelado.')
        return redirect('events:event_detail', event_id=event.id)
    
    if not event.venue.is_active:
        messages.error(request, 'No se puede activar un evento con venue inactiva.')
        return redirect('events:event_detail', event_id=event.id)
    
    event.status = Event.Status.ACTIVE
    event.save()
    
    messages.success(request, f'Evento "{event.name}" activado exitosamente.')
    return redirect('events:event_detail', event_id=event.id)


@login_required
@require_http_methods(["POST"])
def event_deactivate(request, event_id):
    """Desactivar evento."""
    
    if request.user.is_admin_user:
        event = get_object_or_404(Event, id=event_id)
    else:
        event = get_object_or_404(Event, id=event_id, tenant=request.user.tenant)
    
    if event.status == Event.Status.CANCELLED:
        messages.error(request, 'No se puede desactivar un evento cancelado.')
        return redirect('events:event_detail', event_id=event.id)
    
    event.status = Event.Status.CLOSED
    event.save()
    
    messages.success(request, f'Evento "{event.name}" desactivado exitosamente.')
    return redirect('events:event_detail', event_id=event.id)


@login_required
@require_http_methods(["POST"])
def event_cancel(request, event_id):
    """Cancelar evento."""
    
    if request.user.is_admin_user:
        event = get_object_or_404(Event, id=event_id)
    else:
        event = get_object_or_404(Event, id=event_id, tenant=request.user.tenant)
    
    if event.status == Event.Status.CANCELLED:
        messages.warning(request, 'El evento ya está cancelado.')
        return redirect('events:event_detail', event_id=event.id)
    
    event.status = Event.Status.CANCELLED
    event.save()
    
    messages.success(request, f'Evento "{event.name}" cancelado exitosamente.')
    return redirect('events:event_detail', event_id=event.id)

# Zone Management Views

@login_required
def zone_list(request, event_id):
    """Lista de zonas de un evento."""
    
    if request.user.is_admin_user:
        event = get_object_or_404(Event, id=event_id)
    else:
        event = get_object_or_404(Event, id=event_id, tenant=request.user.tenant)
    
    context = {
        'event': event,
    }
    
    return render(request, 'events/zone_list.html', context)


@login_required
def seat_management(request, zone_id):
    """Gestión de asientos de una zona."""
    
    from venezuelan_pos.apps.zones.models import Zone
    
    if request.user.is_admin_user:
        zone = get_object_or_404(Zone, id=zone_id)
    else:
        zone = get_object_or_404(Zone, id=zone_id, tenant=request.user.tenant)
    
    if zone.zone_type != Zone.ZoneType.NUMBERED:
        messages.error(request, 'La gestión de asientos solo está disponible para zonas numeradas.')
        return redirect('events:event_detail', event_id=zone.event.id)
    
    context = {
        'zone': zone,
    }
    
    return render(request, 'events/seat_management.html', context)
