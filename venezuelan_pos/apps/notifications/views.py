"""
API views for notification system.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404

from venezuelan_pos.apps.tenants.mixins import TenantViewMixin
from .models import NotificationTemplate, NotificationLog, NotificationPreference
from .serializers import (
    NotificationTemplateSerializer,
    NotificationLogSerializer,
    NotificationPreferenceSerializer,
    SendNotificationSerializer,
    NotificationStatsSerializer
)
from .services import NotificationService


class NotificationTemplateViewSet(TenantViewMixin, viewsets.ModelViewSet):
    """ViewSet for managing notification templates."""
    
    serializer_class = NotificationTemplateSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['template_type', 'is_active']
    search_fields = ['name', 'subject', 'content']
    ordering = ['-created_at']
    
    def get_queryset(self):
        return NotificationTemplate.objects.filter(
            tenant=self.request.user.tenant
        )
    
    @action(detail=True, methods=['post'])
    def test_template(self, request, pk=None):
        """Test a notification template by sending a test notification."""
        template = self.get_object()
        
        test_context = {
            'customer': {'name': 'Test', 'surname': 'User'},
            'event': {'name': 'Test Event'},
            'test_message': 'This is a test notification'
        }
        
        # Get test recipient from request
        recipient = request.data.get('recipient')
        if not recipient:
            return Response(
                {'error': 'Recipient is required for testing'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            log = NotificationService.send_notification(
                tenant=request.user.tenant,
                template_name=template.name,
                recipient=recipient,
                channel=template.template_type,
                context=test_context
            )
            
            return Response({
                'message': 'Test notification sent successfully',
                'log_id': log.id,
                'task_id': log.task_id
            })
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class NotificationLogViewSet(TenantViewMixin, viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing notification logs."""
    
    serializer_class = NotificationLogSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['channel', 'status', 'template']
    search_fields = ['recipient', 'subject', 'content']
    ordering = ['-created_at']
    
    def get_queryset(self):
        return NotificationLog.objects.filter(
            tenant=self.request.user.tenant
        ).select_related('template', 'customer', 'transaction', 'event')
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get notification statistics."""
        days = int(request.query_params.get('days', 30))
        
        stats = NotificationService.get_notification_stats(
            tenant=request.user.tenant,
            days=days
        )
        stats['period_days'] = days
        
        serializer = NotificationStatsSerializer(stats)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def retry(self, request, pk=None):
        """Retry a failed notification."""
        log = self.get_object()
        
        if log.status != 'failed':
            return Response(
                {'error': 'Only failed notifications can be retried'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Create new notification with same parameters
            new_log = NotificationService.send_notification(
                tenant=log.tenant,
                template_name=log.template.name if log.template else 'manual',
                recipient=log.recipient,
                channel=log.channel,
                context={},  # Use empty context for retry
                customer=log.customer,
                transaction=log.transaction,
                event=log.event
            )
            
            return Response({
                'message': 'Notification retry queued successfully',
                'new_log_id': new_log.id,
                'task_id': new_log.task_id
            })
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class NotificationPreferenceViewSet(TenantViewMixin, viewsets.ModelViewSet):
    """ViewSet for managing notification preferences."""
    
    serializer_class = NotificationPreferenceSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = [
        'email_enabled', 'sms_enabled', 'whatsapp_enabled',
        'purchase_confirmations', 'payment_reminders', 'event_reminders'
    ]
    
    def get_queryset(self):
        return NotificationPreference.objects.filter(
            tenant=self.request.user.tenant
        ).select_related('customer')


class NotificationViewSet(TenantViewMixin, viewsets.GenericViewSet):
    """ViewSet for sending notifications."""
    
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def send(self, request):
        """Send a notification using a template."""
        serializer = SendNotificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        
        # Get optional related objects
        customer = None
        transaction = None
        event = None
        
        if data.get('customer_id'):
            from venezuelan_pos.apps.customers.models import Customer
            customer = get_object_or_404(
                Customer,
                id=data['customer_id'],
                tenant=request.user.tenant
            )
        
        if data.get('transaction_id'):
            from venezuelan_pos.apps.sales.models import Transaction
            transaction = get_object_or_404(
                Transaction,
                id=data['transaction_id'],
                tenant=request.user.tenant
            )
        
        if data.get('event_id'):
            from venezuelan_pos.apps.events.models import Event
            event = get_object_or_404(
                Event,
                id=data['event_id'],
                tenant=request.user.tenant
            )
        
        try:
            log = NotificationService.send_notification(
                tenant=request.user.tenant,
                template_name=data['template_name'],
                recipient=data['recipient'],
                channel=data['channel'],
                context=data['context'],
                customer=customer,
                transaction=transaction,
                event=event
            )
            
            return Response({
                'message': 'Notification sent successfully',
                'log_id': log.id,
                'task_id': log.task_id
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['post'])
    def send_bulk(self, request):
        """Send bulk notifications."""
        notifications = request.data.get('notifications', [])
        
        if not notifications:
            return Response(
                {'error': 'No notifications provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate each notification
        for notification in notifications:
            serializer = SendNotificationSerializer(data=notification)
            serializer.is_valid(raise_exception=True)
        
        # Send notifications
        results = []
        for notification_data in notifications:
            try:
                log = NotificationService.send_notification(
                    tenant=request.user.tenant,
                    template_name=notification_data['template_name'],
                    recipient=notification_data['recipient'],
                    channel=notification_data['channel'],
                    context=notification_data.get('context', {})
                )
                
                results.append({
                    'recipient': notification_data['recipient'],
                    'status': 'queued',
                    'log_id': log.id,
                    'task_id': log.task_id
                })
                
            except Exception as e:
                results.append({
                    'recipient': notification_data['recipient'],
                    'status': 'error',
                    'error': str(e)
                })
        
        return Response({
            'message': f'Processed {len(notifications)} notifications',
            'results': results
        }, status=status.HTTP_201_CREATED)