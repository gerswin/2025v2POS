"""
Notification service layer for Venezuelan POS System.
"""

from django.template import Template, Context
from django.utils import timezone
from .models import NotificationTemplate, NotificationLog, NotificationPreference
from .tasks import (
    send_email_notification,
    send_sms_notification,
    send_whatsapp_notification,
    send_bulk_notifications
)
import logging

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for sending notifications through various channels."""
    
    @staticmethod
    def send_notification(
        tenant,
        template_name,
        recipient,
        channel,
        context=None,
        customer=None,
        transaction=None,
        event=None
    ):
        """
        Send a notification using a template.
        
        Args:
            tenant: Tenant instance
            template_name: Name of the notification template
            recipient: Email address or phone number
            channel: 'email', 'sms', or 'whatsapp'
            context: Template context variables
            customer: Optional customer instance
            transaction: Optional transaction instance
            event: Optional event instance
        
        Returns:
            NotificationLog instance
        """
        context = context or {}
        
        try:
            # Get template
            template = NotificationTemplate.objects.get(
                tenant=tenant,
                name=template_name,
                template_type=channel,
                is_active=True
            )
            
            # Render content
            content_template = Template(template.content)
            rendered_content = content_template.render(Context(context))
            
            subject = ''
            if template.subject:
                subject_template = Template(template.subject)
                subject = subject_template.render(Context(context))
            
            # Create log entry
            log = NotificationLog.objects.create(
                tenant=tenant,
                template=template,
                channel=channel,
                recipient=recipient,
                subject=subject,
                content=rendered_content,
                customer=customer,
                transaction=transaction,
                event=event
            )
            
            # Send notification based on channel
            if channel == 'email':
                task = send_email_notification.delay(
                    recipient_email=recipient,
                    template_name=template_name,
                    context=context,
                    subject=subject,
                    log_id=str(log.id)
                )
            elif channel == 'sms':
                task = send_sms_notification.delay(
                    phone_number=recipient,
                    message=rendered_content,
                    log_id=str(log.id)
                )
            elif channel == 'whatsapp':
                task = send_whatsapp_notification.delay(
                    phone_number=recipient,
                    message=rendered_content,
                    log_id=str(log.id)
                )
            else:
                raise ValueError(f"Unsupported channel: {channel}")
            
            # Update log with task ID
            log.task_id = task.id
            log.save(update_fields=['task_id'])
            
            logger.info(f"Notification queued: {channel} to {recipient}")
            return log
            
        except NotificationTemplate.DoesNotExist:
            logger.error(f"Template not found: {template_name} ({channel})")
            raise
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
            raise
    
    @staticmethod
    def send_purchase_confirmation(transaction):
        """Send purchase confirmation notification."""
        customer = transaction.customer
        if not customer:
            return
        
        # Check customer preferences
        prefs = getattr(customer, 'notification_preferences', None)
        if prefs and not prefs.purchase_confirmations:
            return
        
        context = {
            'customer': customer,
            'transaction': transaction,
            'event': transaction.event,
            'items': transaction.items.all(),
            'total_amount': transaction.total_amount,
        }
        
        notifications_sent = []
        
        # Send email if customer has email and email is enabled
        if customer.email and (not prefs or prefs.email_enabled):
            try:
                log = NotificationService.send_notification(
                    tenant=transaction.tenant,
                    template_name='purchase_confirmation',
                    recipient=customer.email,
                    channel='email',
                    context=context,
                    customer=customer,
                    transaction=transaction,
                    event=transaction.event
                )
                notifications_sent.append(log)
            except Exception as e:
                logger.error(f"Failed to send purchase confirmation email: {e}")
        
        # Send SMS if customer has phone and SMS is enabled
        if customer.phone and (not prefs or prefs.sms_enabled):
            try:
                log = NotificationService.send_notification(
                    tenant=transaction.tenant,
                    template_name='purchase_confirmation',
                    recipient=customer.phone,
                    channel='sms',
                    context=context,
                    customer=customer,
                    transaction=transaction,
                    event=transaction.event
                )
                notifications_sent.append(log)
            except Exception as e:
                logger.error(f"Failed to send purchase confirmation SMS: {e}")
        
        return notifications_sent
    
    @staticmethod
    def send_payment_reminder(payment_plan):
        """Send payment reminder notification."""
        customer = payment_plan.transaction.customer
        if not customer:
            return
        
        # Check customer preferences
        prefs = getattr(customer, 'notification_preferences', None)
        if prefs and not prefs.payment_reminders:
            return
        
        context = {
            'customer': customer,
            'payment_plan': payment_plan,
            'transaction': payment_plan.transaction,
            'event': payment_plan.transaction.event,
            'remaining_balance': payment_plan.remaining_balance,
            'next_payment_date': payment_plan.next_payment_date,
        }
        
        notifications_sent = []
        
        # Send email if available and enabled
        if customer.email and (not prefs or prefs.email_enabled):
            try:
                log = NotificationService.send_notification(
                    tenant=payment_plan.transaction.tenant,
                    template_name='payment_reminder',
                    recipient=customer.email,
                    channel='email',
                    context=context,
                    customer=customer,
                    transaction=payment_plan.transaction
                )
                notifications_sent.append(log)
            except Exception as e:
                logger.error(f"Failed to send payment reminder email: {e}")
        
        return notifications_sent
    
    @staticmethod
    def send_event_reminder(event, customer):
        """Send event reminder notification."""
        # Check customer preferences
        prefs = getattr(customer, 'notification_preferences', None)
        if prefs and not prefs.event_reminders:
            return
        
        context = {
            'customer': customer,
            'event': event,
            'event_date': event.start_date,
            'venue': event.venue,
        }
        
        notifications_sent = []
        
        # Send email if available and enabled
        if customer.email and (not prefs or prefs.email_enabled):
            try:
                log = NotificationService.send_notification(
                    tenant=event.tenant,
                    template_name='event_reminder',
                    recipient=customer.email,
                    channel='email',
                    context=context,
                    customer=customer,
                    event=event
                )
                notifications_sent.append(log)
            except Exception as e:
                logger.error(f"Failed to send event reminder email: {e}")
        
        return notifications_sent
    
    @staticmethod
    def send_ticket_delivery(transaction):
        """Send digital ticket delivery notification."""
        customer = transaction.customer
        if not customer or not customer.email:
            return
        
        # Check customer preferences
        prefs = getattr(customer, 'notification_preferences', None)
        if prefs and not prefs.purchase_confirmations:
            return
        
        # Only send if email is enabled
        if prefs and not prefs.email_enabled:
            return
        
        context = {
            'customer': customer,
            'transaction': transaction,
            'event': transaction.event,
            'items': transaction.items.all(),
            'ticket_count': transaction.items.count(),
        }
        
        try:
            log = NotificationService.send_notification(
                tenant=transaction.tenant,
                template_name='ticket_delivery',
                recipient=customer.email,
                channel='email',
                context=context,
                customer=customer,
                transaction=transaction,
                event=transaction.event
            )
            logger.info(f"Ticket delivery notification sent for transaction {transaction.id}")
            return log
        except Exception as e:
            logger.error(f"Failed to send ticket delivery notification: {e}")
            return None
    
    @staticmethod
    def get_notification_stats(tenant, days=30):
        """Get notification statistics for the tenant."""
        from datetime import timedelta
        
        cutoff_date = timezone.now() - timedelta(days=days)
        
        logs = NotificationLog.objects.filter(
            tenant=tenant,
            created_at__gte=cutoff_date
        )
        
        stats = {
            'total_sent': logs.count(),
            'by_channel': {},
            'by_status': {},
            'success_rate': 0,
        }
        
        # Group by channel
        for channel, _ in NotificationLog.CHANNEL_CHOICES:
            count = logs.filter(channel=channel).count()
            stats['by_channel'][channel] = count
        
        # Group by status
        for status, _ in NotificationLog.STATUS_CHOICES:
            count = logs.filter(status=status).count()
            stats['by_status'][status] = count
        
        # Calculate success rate
        sent_count = stats['by_status'].get('sent', 0)
        if stats['total_sent'] > 0:
            stats['success_rate'] = (sent_count / stats['total_sent']) * 100
        
        return stats