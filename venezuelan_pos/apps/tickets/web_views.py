"""
Web views for digital ticket management.
Provides Django template-based interfaces for ticket management.
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.urls import reverse_lazy
from django.db.models import Q, Count, Case, When, IntegerField
from django.utils import timezone
from django.core.paginator import Paginator
from django.db import transaction
from venezuelan_pos.apps.tenants.mixins import TenantViewMixin
from venezuelan_pos.apps.events.models import Event
from venezuelan_pos.apps.customers.models import Customer
from .models import DigitalTicket, TicketTemplate, TicketValidationLog
from .validation import TicketValidator, ValidationContextBuilder
from .services import TicketPDFService
import json


@method_decorator(login_required, name='dispatch')
class TicketDashboardView(TenantViewMixin, ListView):
    """Dashboard view for digital ticket management."""
    
    model = DigitalTicket
    template_name = 'tickets/dashboard.html'
    context_object_name = 'tickets'
    paginate_by = 20
    
    def get_queryset(self):
        """Get tickets for current tenant with search and filters."""
        queryset = DigitalTicket.objects.filter(
            tenant=self.request.user.tenant
        ).select_related(
            'customer', 'event', 'zone', 'seat', 'transaction'
        ).order_by('-created_at')
        
        # Search functionality
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(ticket_number__icontains=search) |
                Q(customer__name__icontains=search) |
                Q(customer__surname__icontains=search) |
                Q(customer__email__icontains=search) |
                Q(event__name__icontains=search)
            )
        
        # Status filter
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        # Event filter
        event_id = self.request.GET.get('event')
        if event_id:
            queryset = queryset.filter(event_id=event_id)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        """Add additional context for dashboard."""
        context = super().get_context_data(**kwargs)
        
        # Get statistics
        tenant_tickets = DigitalTicket.objects.filter(tenant=self.request.user.tenant)
        
        context.update({
            'total_tickets': tenant_tickets.count(),
            'active_tickets': tenant_tickets.filter(status=DigitalTicket.Status.ACTIVE).count(),
            'used_tickets': tenant_tickets.filter(status=DigitalTicket.Status.USED).count(),
            'expired_tickets': tenant_tickets.filter(status=DigitalTicket.Status.EXPIRED).count(),
            'events': Event.objects.filter(tenant=self.request.user.tenant, status='active'),
            'status_choices': DigitalTicket.Status.choices,
        })
        
        return context


@method_decorator(login_required, name='dispatch')
class TicketDetailView(TenantViewMixin, DetailView):
    """Detail view for individual tickets."""
    
    model = DigitalTicket
    template_name = 'tickets/ticket_detail.html'
    context_object_name = 'ticket'
    
    def get_queryset(self):
        """Get tickets for current tenant."""
        return DigitalTicket.objects.filter(
            tenant=self.request.user.tenant
        ).select_related(
            'customer', 'event', 'zone', 'seat', 'transaction'
        )
    
    def get_context_data(self, **kwargs):
        """Add validation history to context."""
        context = super().get_context_data(**kwargs)
        
        # Get validation history
        validation_logs = self.object.validation_logs.all().order_by('-validated_at')[:10]
        
        context.update({
            'validation_logs': validation_logs,
            'can_regenerate_qr': True,
        })
        
        return context


@method_decorator(login_required, name='dispatch')
class ValidationDashboardView(TenantViewMixin, ListView):
    """Dashboard for ticket validation and entry control."""
    
    model = TicketValidationLog
    template_name = 'tickets/validation_dashboard.html'
    context_object_name = 'validation_logs'
    paginate_by = 50
    
    def get_queryset(self):
        """Get validation logs for current tenant."""
        return TicketValidationLog.objects.filter(
            tenant=self.request.user.tenant
        ).select_related(
            'ticket', 'ticket__customer', 'ticket__event'
        ).order_by('-validated_at')
    
    def get_context_data(self, **kwargs):
        """Add validation statistics to context."""
        context = super().get_context_data(**kwargs)
        
        # Get validation statistics
        logs = TicketValidationLog.objects.filter(tenant=self.request.user.tenant)
        
        # Today's stats
        today = timezone.now().date()
        today_logs = logs.filter(validated_at__date=today)
        
        context.update({
            'total_validations': logs.count(),
            'successful_validations': logs.filter(validation_result=True).count(),
            'failed_validations': logs.filter(validation_result=False).count(),
            'today_validations': today_logs.count(),
            'today_successful': today_logs.filter(validation_result=True).count(),
            'today_failed': today_logs.filter(validation_result=False).count(),
        })
        
        return context


@method_decorator(login_required, name='dispatch')
class TicketTemplateListView(TenantViewMixin, ListView):
    """List view for ticket templates."""
    
    model = TicketTemplate
    template_name = 'tickets/template_list.html'
    context_object_name = 'templates'
    
    def get_queryset(self):
        """Get templates for current tenant."""
        return TicketTemplate.objects.filter(
            tenant=self.request.user.tenant
        ).order_by('template_type', 'name')


@method_decorator(login_required, name='dispatch')
class TicketTemplateDetailView(TenantViewMixin, DetailView):
    """Detail view for ticket templates."""
    
    model = TicketTemplate
    template_name = 'tickets/template_detail.html'
    context_object_name = 'template'
    
    def get_queryset(self):
        """Get templates for current tenant."""
        return TicketTemplate.objects.filter(tenant=self.request.user.tenant)


@method_decorator(login_required, name='dispatch')
class TicketTemplateCreateView(TenantViewMixin, CreateView):
    """Create view for ticket templates."""
    
    model = TicketTemplate
    template_name = 'tickets/template_form.html'
    fields = [
        'name', 'template_type', 'html_content', 'css_styles',
        'page_size', 'orientation', 'include_qr_code', 'include_barcode',
        'include_logo', 'is_active', 'is_default'
    ]
    success_url = reverse_lazy('tickets:template_list')
    
    def form_valid(self, form):
        """Set tenant when creating template."""
        form.instance.tenant = self.request.user.tenant
        
        # If setting as default, remove default from other templates of same type
        if form.instance.is_default:
            TicketTemplate.objects.filter(
                tenant=self.request.user.tenant,
                template_type=form.instance.template_type
            ).update(is_default=False)
        
        messages.success(self.request, f'Template "{form.instance.name}" created successfully.')
        return super().form_valid(form)


@method_decorator(login_required, name='dispatch')
class TicketTemplateUpdateView(TenantViewMixin, UpdateView):
    """Update view for ticket templates."""
    
    model = TicketTemplate
    template_name = 'tickets/template_form.html'
    fields = [
        'name', 'template_type', 'html_content', 'css_styles',
        'page_size', 'orientation', 'include_qr_code', 'include_barcode',
        'include_logo', 'is_active', 'is_default'
    ]
    success_url = reverse_lazy('tickets:template_list')
    
    def get_queryset(self):
        """Get templates for current tenant."""
        return TicketTemplate.objects.filter(tenant=self.request.user.tenant)
    
    def form_valid(self, form):
        """Handle default template logic."""
        # If setting as default, remove default from other templates of same type
        if form.instance.is_default:
            TicketTemplate.objects.filter(
                tenant=self.request.user.tenant,
                template_type=form.instance.template_type
            ).exclude(pk=form.instance.pk).update(is_default=False)
        
        messages.success(self.request, f'Template "{form.instance.name}" updated successfully.')
        return super().form_valid(form)


@login_required
def validate_ticket_view(request):
    """Web interface for ticket validation."""
    if request.method == 'POST':
        ticket_identifier = request.POST.get('ticket_identifier', '').strip()
        action = request.POST.get('action', 'validate')
        
        if not ticket_identifier:
            messages.error(request, 'Please enter a ticket number or scan QR code.')
            return render(request, 'tickets/validate_ticket.html')
        
        # Build validation context
        validation_context = ValidationContextBuilder.from_request(
            request,
            system_id='web_interface',
            location='Web Dashboard'
        )
        
        validator = TicketValidator()
        
        try:
            if action == 'check_only':
                result = validator.check_ticket_status(ticket_identifier)
            elif action == 'validate_use':
                result = validator.validate_and_use_ticket(ticket_identifier, validation_context)
            else:
                result = validator.check_ticket_status(ticket_identifier)
            
            if result.get('valid'):
                if action == 'validate_use' and result.get('usage_count', 0) > 0:
                    messages.success(
                        request,
                        f'Ticket {result.get("ticket_number")} validated successfully. '
                        f'Customer: {result.get("customer_name")}'
                    )
                else:
                    messages.info(
                        request,
                        f'Ticket {result.get("ticket_number")} is valid. '
                        f'Customer: {result.get("customer_name")}, '
                        f'Remaining uses: {result.get("remaining_uses", 0)}'
                    )
            else:
                messages.error(
                    request,
                    f'Ticket validation failed: {result.get("reason", "Unknown error")}'
                )
            
            return render(request, 'tickets/validate_ticket.html', {
                'validation_result': result,
                'ticket_identifier': ticket_identifier
            })
            
        except Exception as e:
            messages.error(request, f'Validation error: {str(e)}')
    
    return render(request, 'tickets/validate_ticket.html')


@login_required
@require_http_methods(["POST"])
def regenerate_qr_code(request, ticket_id):
    """Regenerate QR code for a specific ticket."""
    ticket = get_object_or_404(
        DigitalTicket,
        id=ticket_id,
        tenant=request.user.tenant
    )
    
    try:
        ticket.generate_qr_code()
        messages.success(request, f'QR code regenerated for ticket {ticket.ticket_number}')
    except Exception as e:
        messages.error(request, f'Failed to regenerate QR code: {str(e)}')
    
    return redirect('tickets:ticket_detail', pk=ticket.pk)


@login_required
def download_ticket_pdf(request, ticket_id):
    """Download PDF ticket."""
    ticket = get_object_or_404(
        DigitalTicket,
        id=ticket_id,
        tenant=request.user.tenant
    )
    
    try:
        # Generate PDF
        pdf_content = TicketPDFService.generate_pdf_ticket(ticket)
        
        # Create response
        response = HttpResponse(pdf_content, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="ticket_{ticket.ticket_number}.pdf"'
        
        return response
        
    except Exception as e:
        messages.error(request, f'Failed to generate PDF: {str(e)}')
        return redirect('tickets:ticket_detail', pk=ticket.pk)


@login_required
def resend_ticket(request, ticket_id):
    """Resend ticket to customer."""
    ticket = get_object_or_404(
        DigitalTicket,
        id=ticket_id,
        tenant=request.user.tenant
    )
    
    if request.method == 'POST':
        delivery_method = request.POST.get('delivery_method', 'email')
        custom_message = request.POST.get('custom_message', '')
        
        try:
            from .services import TicketDeliveryService
            
            if delivery_method == 'email':
                TicketDeliveryService.send_ticket_email(ticket, custom_message)
                messages.success(request, f'Ticket sent via email to {ticket.customer.email}')
            elif delivery_method == 'sms':
                TicketDeliveryService.send_ticket_sms(ticket, custom_message)
                messages.success(request, f'Ticket sent via SMS to {ticket.customer.phone}')
            elif delivery_method == 'whatsapp':
                TicketDeliveryService.send_ticket_whatsapp(ticket, custom_message)
                messages.success(request, f'Ticket sent via WhatsApp to {ticket.customer.phone}')
            
        except Exception as e:
            messages.error(request, f'Failed to send ticket: {str(e)}')
    
    return render(request, 'tickets/resend_ticket.html', {'ticket': ticket})


@login_required
def ticket_analytics(request):
    """Ticket analytics and reporting dashboard."""
    tenant = request.user.tenant
    
    # Get date range from request
    from datetime import datetime, timedelta
    end_date = timezone.now()
    start_date = end_date - timedelta(days=30)  # Default to last 30 days
    
    if request.GET.get('start_date'):
        start_date = datetime.strptime(request.GET['start_date'], '%Y-%m-%d')
        start_date = timezone.make_aware(start_date)
    
    if request.GET.get('end_date'):
        end_date = datetime.strptime(request.GET['end_date'], '%Y-%m-%d')
        end_date = timezone.make_aware(end_date)
    
    # Ticket statistics
    tickets = DigitalTicket.objects.filter(
        tenant=tenant,
        created_at__range=[start_date, end_date]
    )
    
    ticket_stats = {
        'total': tickets.count(),
        'active': tickets.filter(status=DigitalTicket.Status.ACTIVE).count(),
        'used': tickets.filter(status=DigitalTicket.Status.USED).count(),
        'expired': tickets.filter(status=DigitalTicket.Status.EXPIRED).count(),
        'cancelled': tickets.filter(status=DigitalTicket.Status.CANCELLED).count(),
    }
    
    # Validation statistics
    validations = TicketValidationLog.objects.filter(
        tenant=tenant,
        validated_at__range=[start_date, end_date]
    )
    
    validation_stats = {
        'total': validations.count(),
        'successful': validations.filter(validation_result=True).count(),
        'failed': validations.filter(validation_result=False).count(),
    }
    
    # Usage by event
    event_usage = tickets.values(
        'event__name'
    ).annotate(
        total_tickets=Count('id'),
        used_tickets=Count(Case(When(status=DigitalTicket.Status.USED, then=1)))
    ).order_by('-total_tickets')[:10]
    
    # Usage by method
    method_usage = validations.values('validation_method').annotate(
        count=Count('id')
    ).order_by('-count')
    
    context = {
        'start_date': start_date.date(),
        'end_date': end_date.date(),
        'ticket_stats': ticket_stats,
        'validation_stats': validation_stats,
        'event_usage': event_usage,
        'method_usage': method_usage,
    }
    
    return render(request, 'tickets/analytics.html', context)


@login_required
@csrf_exempt
def ajax_validate_ticket(request):
    """AJAX endpoint for ticket validation."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        ticket_identifier = data.get('ticket_identifier', '').strip()
        action = data.get('action', 'check')
        
        if not ticket_identifier:
            return JsonResponse({
                'valid': False,
                'error': 'Ticket identifier is required'
            })
        
        # Build validation context
        validation_context = ValidationContextBuilder.from_request(
            request,
            system_id='ajax_interface',
            location='Web Dashboard'
        )
        
        validator = TicketValidator()
        
        if action == 'validate_use':
            result = validator.validate_and_use_ticket(ticket_identifier, validation_context)
        else:
            result = validator.check_ticket_status(ticket_identifier)
        
        # Format response for frontend
        response_data = {
            'valid': result.get('valid', False),
            'ticket_number': result.get('ticket_number', ''),
            'customer_name': result.get('customer_name', ''),
            'event_name': result.get('event_name', ''),
            'seat_label': result.get('seat_label', ''),
            'status': result.get('status', ''),
            'usage_count': result.get('usage_count', 0),
            'max_usage': result.get('max_usage', 1),
            'remaining_uses': result.get('remaining_uses', 0),
            'reason': result.get('reason', ''),
            'timestamp': timezone.now().isoformat()
        }
        
        return JsonResponse(response_data)
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)