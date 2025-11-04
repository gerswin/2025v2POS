from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q, Count, Case, When, IntegerField
from django.utils import timezone
from django.core.exceptions import ValidationError
from venezuelan_pos.apps.tenants.mixins import TenantViewMixin
from venezuelan_pos.apps.sales.models import Transaction
from .models import DigitalTicket, TicketTemplate, TicketValidationLog
from .serializers import (
    DigitalTicketSerializer, TicketValidationSerializer,
    TicketValidationResponseSerializer, TicketValidationLogSerializer,
    TicketTemplateSerializer, TicketGenerationSerializer,
    TicketLookupSerializer, TicketResendSerializer,
    TicketUsageStatsSerializer
)
from .validation import TicketValidator, ValidationContextBuilder
import json
import base64
from cryptography.fernet import Fernet
from django.conf import settings


class DigitalTicketViewSet(TenantViewMixin, viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for Digital Tickets.
    Provides read-only access to digital tickets with validation endpoints.
    """
    
    serializer_class = DigitalTicketSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['status', 'ticket_type', 'event', 'customer']
    search_fields = ['ticket_number', 'customer__name', 'customer__surname']
    ordering_fields = ['created_at', 'ticket_number', 'status']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Get tickets for current tenant."""
        return DigitalTicket.objects.filter(
            tenant=self.request.user.tenant
        ).select_related(
            'customer', 'event', 'zone', 'seat', 'transaction'
        )
    
    @action(detail=False, methods=['post'])
    def validate_ticket(self, request):
        """
        Validate a ticket by QR code or ticket number.
        Can optionally mark ticket as used.
        """
        serializer = TicketValidationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        data = serializer.validated_data
        
        # Build validation context
        validation_context = ValidationContextBuilder.from_api_data({
            'validation_system_id': data['validation_system_id'],
            'validation_location': data.get('validation_location', ''),
            'ip_address': self._get_client_ip(request),
            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
            'check_event_timing': True
        })
        
        # Use the enhanced validation system
        validator = TicketValidator()
        
        # Determine ticket identifier
        ticket_identifier = data.get('qr_code_data') or data.get('ticket_number')
        
        if data.get('mark_as_used', True):
            result = validator.validate_and_use_ticket(ticket_identifier, validation_context)
        else:
            result = validator.check_ticket_status(ticket_identifier)
        
        result['validation_timestamp'] = timezone.now()
        
        # Return appropriate status code
        if result.get('valid'):
            response_serializer = TicketValidationResponseSerializer(result)
            return Response(response_serializer.data)
        else:
            response_serializer = TicketValidationResponseSerializer(result)
            return Response(
                response_serializer.data,
                status=status.HTTP_404_NOT_FOUND if 'not found' in result.get('reason', '').lower() else status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def mark_as_used(self, request, pk=None):
        """Mark a specific ticket as used."""
        ticket = self.get_object()
        
        validation_system_id = request.data.get('validation_system_id', 'manual')
        result = ticket.validate_and_use(validation_system_id=validation_system_id)
        
        response_serializer = TicketValidationResponseSerializer(result)
        return Response(response_serializer.data)
    
    @action(detail=False, methods=['post'])
    def validate_multi_entry(self, request):
        """
        Validate multi-entry ticket with check-in/check-out support.
        """
        serializer = TicketValidationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        data = serializer.validated_data
        action = request.data.get('action', 'check_in')  # check_in or check_out
        
        # Build validation context
        validation_context = ValidationContextBuilder.from_api_data({
            'validation_system_id': data['validation_system_id'],
            'validation_location': data.get('validation_location', ''),
            'ip_address': self._get_client_ip(request),
            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
            'action': action
        })
        
        # Use the enhanced validation system for multi-entry
        validator = TicketValidator()
        ticket_identifier = data.get('qr_code_data') or data.get('ticket_number')
        
        result = validator.validate_multi_entry_ticket(ticket_identifier, validation_context)
        result['validation_timestamp'] = timezone.now()
        
        response_serializer = TicketValidationResponseSerializer(result)
        return Response(response_serializer.data)
    
    @action(detail=False, methods=['post'])
    def check_status(self, request):
        """
        Check ticket status without marking as used.
        Enhanced status check with detailed information.
        """
        serializer = TicketValidationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        data = serializer.validated_data
        ticket_identifier = data.get('qr_code_data') or data.get('ticket_number')
        
        validator = TicketValidator()
        result = validator.check_ticket_status(ticket_identifier)
        result['validation_timestamp'] = timezone.now()
        
        response_serializer = TicketValidationResponseSerializer(result)
        return Response(response_serializer.data)
    
    @action(detail=True, methods=['get'])
    def validation_history(self, request, pk=None):
        """Get validation history for a specific ticket."""
        ticket = self.get_object()
        logs = ticket.validation_logs.all().order_by('-validated_at')
        
        serializer = TicketValidationLogSerializer(logs, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def lookup(self, request):
        """Lookup tickets by various criteria."""
        serializer = TicketLookupSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        data = serializer.validated_data
        queryset = self.get_queryset()
        
        # Filter by criteria
        if data.get('ticket_number'):
            queryset = queryset.filter(ticket_number=data['ticket_number'])
        
        if data.get('customer_email'):
            queryset = queryset.filter(customer__email=data['customer_email'])
        
        if data.get('customer_phone'):
            queryset = queryset.filter(customer__phone=data['customer_phone'])
        
        if data.get('event_id'):
            queryset = queryset.filter(event_id=data['event_id'])
        
        # Serialize results
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def generate(self, request):
        """Generate digital tickets for a completed transaction."""
        serializer = TicketGenerationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        data = serializer.validated_data
        
        # Get transaction
        try:
            transaction = Transaction.objects.get(
                id=data['transaction_id'],
                tenant=request.user.tenant
            )
        except Transaction.DoesNotExist:
            return Response(
                {'error': 'Transaction not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if transaction is completed
        if not transaction.is_completed:
            return Response(
                {'error': 'Transaction must be completed to generate tickets'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if tickets already exist
        existing_tickets = transaction.digital_tickets.exists()
        if existing_tickets and not data.get('regenerate', False):
            return Response(
                {'error': 'Tickets already exist. Use regenerate=true to recreate.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Delete existing tickets if regenerating
        if data.get('regenerate', False):
            transaction.digital_tickets.all().delete()
        
        # Generate tickets
        try:
            tickets = DigitalTicket.objects.generate_for_transaction(transaction)
            serializer = self.get_serializer(tickets, many=True)
            return Response({
                'message': f'Generated {len(tickets)} digital tickets',
                'tickets': serializer.data
            })
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['post'])
    def resend(self, request):
        """Resend digital tickets to customers."""
        serializer = TicketResendSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        data = serializer.validated_data
        
        # Get tickets
        tickets = self.get_queryset().filter(
            id__in=data['ticket_ids']
        )
        
        if not tickets.exists():
            return Response(
                {'error': 'No tickets found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Resend tickets (implementation depends on notification system)
        try:
            from venezuelan_pos.apps.notifications.services import NotificationService
            
            resent_count = 0
            for ticket in tickets:
                # Send ticket based on delivery method
                if data['delivery_method'] == 'email':
                    NotificationService.send_ticket_delivery(
                        ticket.transaction,
                        custom_message=data.get('custom_message')
                    )
                elif data['delivery_method'] == 'sms':
                    NotificationService.send_sms_ticket(
                        ticket,
                        custom_message=data.get('custom_message')
                    )
                elif data['delivery_method'] == 'whatsapp':
                    NotificationService.send_whatsapp_ticket(
                        ticket,
                        custom_message=data.get('custom_message')
                    )
                
                resent_count += 1
            
            return Response({
                'message': f'Resent {resent_count} tickets via {data["delivery_method"]}'
            })
            
        except Exception as e:
            return Response(
                {'error': f'Failed to resend tickets: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def usage_stats(self, request):
        """Get ticket usage statistics."""
        serializer = TicketUsageStatsSerializer(data=request.query_params)
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        data = serializer.validated_data
        queryset = self.get_queryset()
        
        # Apply filters
        if data.get('event_id'):
            queryset = queryset.filter(event_id=data['event_id'])
        
        if data.get('zone_id'):
            queryset = queryset.filter(zone_id=data['zone_id'])
        
        if data.get('date_from'):
            queryset = queryset.filter(created_at__gte=data['date_from'])
        
        if data.get('date_to'):
            queryset = queryset.filter(created_at__lte=data['date_to'])
        
        # Calculate statistics
        stats = queryset.aggregate(
            total_tickets=Count('id'),
            active_tickets=Count(
                Case(When(status=DigitalTicket.Status.ACTIVE, then=1))
            ),
            used_tickets=Count(
                Case(When(status=DigitalTicket.Status.USED, then=1))
            ),
            expired_tickets=Count(
                Case(When(status=DigitalTicket.Status.EXPIRED, then=1))
            ),
            cancelled_tickets=Count(
                Case(When(status=DigitalTicket.Status.CANCELLED, then=1))
            )
        )
        
        # Calculate usage rate
        total = stats['total_tickets'] or 0
        used = stats['used_tickets'] or 0
        stats['usage_rate'] = (used / total * 100) if total > 0 else 0
        
        response_serializer = TicketUsageStatsSerializer(stats)
        return Response(response_serializer.data)
    
    def _find_ticket_by_qr_code(self, qr_code_data):
        """Find ticket by decrypting QR code data."""
        try:
            # Decrypt QR code data
            key = getattr(settings, 'TICKET_ENCRYPTION_KEY', None)
            if not key:
                return None
            
            if isinstance(key, str):
                key = key.encode()
            
            fernet = Fernet(key)
            encrypted_data = base64.b64decode(qr_code_data.encode())
            decrypted = fernet.decrypt(encrypted_data)
            validation_data = json.loads(decrypted.decode())
            
            # Find ticket by ID from decrypted data
            ticket_id = validation_data.get('ticket_id')
            if ticket_id:
                return self.get_queryset().get(id=ticket_id)
            
        except Exception:
            pass
        
        return None
    
    def _get_client_ip(self, request):
        """Get client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class TicketTemplateViewSet(TenantViewMixin, viewsets.ModelViewSet):
    """
    ViewSet for Ticket Templates.
    Allows CRUD operations on ticket templates.
    """
    
    serializer_class = TicketTemplateSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['template_type', 'is_active', 'is_default']
    search_fields = ['name']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
    
    def get_queryset(self):
        """Get templates for current tenant."""
        return TicketTemplate.objects.filter(
            tenant=self.request.user.tenant
        )
    
    def perform_create(self, serializer):
        """Set tenant when creating template."""
        serializer.save(tenant=self.request.user.tenant)
    
    @action(detail=True, methods=['post'])
    def make_default(self, request, pk=None):
        """Make this template the default for its type."""
        template = self.get_object()
        
        # Remove default flag from other templates of same type
        TicketTemplate.objects.filter(
            tenant=template.tenant,
            template_type=template.template_type
        ).update(is_default=False)
        
        # Set this template as default
        template.is_default = True
        template.save()
        
        return Response({
            'message': f'Template "{template.name}" is now the default {template.template_type} template'
        })
    
    @action(detail=True, methods=['post'])
    def preview(self, request, pk=None):
        """Preview template with sample data."""
        template = self.get_object()
        
        # Get a sample ticket for preview (or create mock data)
        sample_ticket = self.get_queryset().first()
        if not sample_ticket:
            return Response(
                {'error': 'No tickets available for preview'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        try:
            rendered_html = template.render_ticket(sample_ticket)
            return Response({
                'html_content': rendered_html,
                'css_styles': template.css_styles
            })
        except Exception as e:
            return Response(
                {'error': f'Template rendering failed: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['post'])
    def create_defaults(self, request):
        """Create default templates for the tenant."""
        tenant = request.user.tenant
        
        # Check if default templates already exist
        existing = TicketTemplate.objects.filter(
            tenant=tenant,
            is_default=True
        ).exists()
        
        if existing:
            return Response(
                {'error': 'Default templates already exist'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create default templates
        templates = TicketTemplate.create_default_templates(tenant)
        serializer = self.get_serializer(templates, many=True)
        
        return Response({
            'message': f'Created {len(templates)} default templates',
            'templates': serializer.data
        })


class TicketValidationLogViewSet(TenantViewMixin, viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for Ticket Validation Logs.
    Provides read-only access to validation audit trail.
    """
    
    serializer_class = TicketValidationLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['validation_result', 'validation_method', 'validation_system_id']
    search_fields = ['ticket__ticket_number', 'validation_system_id']
    ordering_fields = ['validated_at']
    ordering = ['-validated_at']
    
    def get_queryset(self):
        """Get validation logs for current tenant."""
        return TicketValidationLog.objects.filter(
            tenant=self.request.user.tenant
        ).select_related('ticket', 'ticket__customer', 'ticket__event')
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get validation statistics."""
        queryset = self.get_queryset()
        
        # Apply date filters if provided
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        
        if date_from:
            queryset = queryset.filter(validated_at__gte=date_from)
        if date_to:
            queryset = queryset.filter(validated_at__lte=date_to)
        
        # Calculate statistics
        stats = queryset.aggregate(
            total_validations=Count('id'),
            successful_validations=Count(
                Case(When(validation_result=True, then=1))
            ),
            failed_validations=Count(
                Case(When(validation_result=False, then=1))
            )
        )
        
        # Calculate success rate
        total = stats['total_validations'] or 0
        successful = stats['successful_validations'] or 0
        stats['success_rate'] = (successful / total * 100) if total > 0 else 0
        
        return Response(stats)
    
    @action(detail=False, methods=['post'])
    def bulk_validate(self, request):
        """
        Validate multiple tickets in a single request.
        Useful for batch processing at entry points.
        """
        ticket_identifiers = request.data.get('ticket_identifiers', [])
        validation_system_id = request.data.get('validation_system_id', 'bulk_validator')
        mark_as_used = request.data.get('mark_as_used', True)
        
        if not ticket_identifiers:
            return Response(
                {'error': 'No ticket identifiers provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if len(ticket_identifiers) > 100:  # Limit bulk operations
            return Response(
                {'error': 'Maximum 100 tickets can be validated at once'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Build validation context
        validation_context = ValidationContextBuilder.from_api_data({
            'validation_system_id': validation_system_id,
            'validation_location': request.data.get('validation_location', ''),
            'ip_address': self._get_client_ip(request),
            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
        })
        
        validator = TicketValidator()
        results = []
        
        for identifier in ticket_identifiers:
            if mark_as_used:
                result = validator.validate_and_use_ticket(identifier, validation_context)
            else:
                result = validator.check_ticket_status(identifier)
            
            result['identifier'] = identifier
            result['validation_timestamp'] = timezone.now()
            results.append(result)
        
        # Summary statistics
        total_tickets = len(results)
        valid_tickets = sum(1 for r in results if r.get('valid'))
        used_tickets = sum(1 for r in results if r.get('valid') and r.get('usage_count', 0) > 0)
        
        return Response({
            'results': results,
            'summary': {
                'total_tickets': total_tickets,
                'valid_tickets': valid_tickets,
                'invalid_tickets': total_tickets - valid_tickets,
                'used_tickets': used_tickets,
                'success_rate': (valid_tickets / total_tickets * 100) if total_tickets > 0 else 0
            }
        })
    
    @action(detail=False, methods=['get'])
    def validation_stats_detailed(self, request):
        """
        Get detailed validation statistics with breakdown by system, method, etc.
        """
        # Date filters
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        system_id = request.query_params.get('system_id')
        
        queryset = TicketValidationLog.objects.filter(tenant=request.user.tenant)
        
        if date_from:
            queryset = queryset.filter(validated_at__gte=date_from)
        if date_to:
            queryset = queryset.filter(validated_at__lte=date_to)
        if system_id:
            queryset = queryset.filter(validation_system_id=system_id)
        
        # Basic stats
        total_validations = queryset.count()
        successful_validations = queryset.filter(validation_result=True).count()
        failed_validations = queryset.filter(validation_result=False).count()
        
        # Breakdown by method
        method_stats = {}
        for method in ['qr_code', 'ticket_number', 'multi_entry', 'manual']:
            method_count = queryset.filter(validation_method=method).count()
            method_success = queryset.filter(
                validation_method=method, 
                validation_result=True
            ).count()
            method_stats[method] = {
                'total': method_count,
                'successful': method_success,
                'failed': method_count - method_success,
                'success_rate': (method_success / method_count * 100) if method_count > 0 else 0
            }
        
        # Breakdown by system
        system_stats = {}
        systems = queryset.values_list('validation_system_id', flat=True).distinct()
        for system in systems:
            system_count = queryset.filter(validation_system_id=system).count()
            system_success = queryset.filter(
                validation_system_id=system,
                validation_result=True
            ).count()
            system_stats[system] = {
                'total': system_count,
                'successful': system_success,
                'failed': system_count - system_success,
                'success_rate': (system_success / system_count * 100) if system_count > 0 else 0
            }
        
        # Recent activity (last 24 hours)
        from datetime import timedelta
        recent_cutoff = timezone.now() - timedelta(hours=24)
        recent_validations = queryset.filter(validated_at__gte=recent_cutoff).count()
        recent_successful = queryset.filter(
            validated_at__gte=recent_cutoff,
            validation_result=True
        ).count()
        
        return Response({
            'total_validations': total_validations,
            'successful_validations': successful_validations,
            'failed_validations': failed_validations,
            'success_rate': (successful_validations / total_validations * 100) if total_validations > 0 else 0,
            'method_breakdown': method_stats,
            'system_breakdown': system_stats,
            'recent_activity': {
                'total_24h': recent_validations,
                'successful_24h': recent_successful,
                'success_rate_24h': (recent_successful / recent_validations * 100) if recent_validations > 0 else 0
            }
        })