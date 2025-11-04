"""
Celery tasks for notification system.
"""

from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def send_email_notification(self, recipient_email, template_name, context, subject, log_id=None):
    """
    Send email notification using template.
    
    Args:
        recipient_email (str): Email address to send to
        template_name (str): Template name for email content
        context (dict): Template context variables
        subject (str): Email subject
        log_id (str): Optional NotificationLog ID for tracking
    """
    from .models import NotificationLog
    
    try:
        # Render email content from template
        html_content = render_to_string(f'notifications/email/{template_name}.html', context)
        text_content = render_to_string(f'notifications/email/{template_name}.txt', context)
        
        # Send email
        send_mail(
            subject=subject,
            message=text_content,
            html_message=html_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient_email],
            fail_silently=False,
        )
        
        # Update log if provided
        if log_id:
            try:
                log = NotificationLog.objects.get(id=log_id)
                log.mark_sent()
            except NotificationLog.DoesNotExist:
                pass
        
        logger.info(f"Email sent successfully to {recipient_email}")
        return {"status": "success", "recipient": recipient_email}
        
    except Exception as exc:
        # Update log with error if provided
        if log_id:
            try:
                log = NotificationLog.objects.get(id=log_id)
                log.mark_failed(str(exc))
            except NotificationLog.DoesNotExist:
                pass
        
        logger.error(f"Email sending failed: {exc}")
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@shared_task(bind=True, max_retries=3)
def send_sms_notification(self, phone_number, message, log_id=None):
    """
    Send SMS notification.
    
    Args:
        phone_number (str): Phone number to send SMS to
        message (str): SMS message content
        log_id (str): Optional NotificationLog ID for tracking
    """
    from .models import NotificationLog
    
    try:
        # TODO: Integrate with SMS provider (Twilio, AWS SNS, etc.)
        # For now, log the SMS
        logger.info(f"SMS to {phone_number}: {message}")
        
        # Placeholder for actual SMS sending
        # Example integration:
        # from twilio.rest import Client
        # client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        # client.messages.create(
        #     body=message,
        #     from_=settings.TWILIO_PHONE_NUMBER,
        #     to=phone_number
        # )
        
        # Update log if provided
        if log_id:
            try:
                log = NotificationLog.objects.get(id=log_id)
                log.mark_sent()
            except NotificationLog.DoesNotExist:
                pass
        
        return {"status": "success", "phone": phone_number}
        
    except Exception as exc:
        # Update log with error if provided
        if log_id:
            try:
                log = NotificationLog.objects.get(id=log_id)
                log.mark_failed(str(exc))
            except NotificationLog.DoesNotExist:
                pass
        
        logger.error(f"SMS sending failed: {exc}")
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@shared_task(bind=True, max_retries=3)
def send_whatsapp_notification(self, phone_number, message, log_id=None):
    """
    Send WhatsApp notification.
    
    Args:
        phone_number (str): Phone number to send WhatsApp message to
        message (str): WhatsApp message content
        log_id (str): Optional NotificationLog ID for tracking
    """
    from .models import NotificationLog
    
    try:
        # TODO: Integrate with WhatsApp Business API
        # For now, log the WhatsApp message
        logger.info(f"WhatsApp to {phone_number}: {message}")
        
        # Placeholder for actual WhatsApp sending
        # Example integration:
        # from whatsapp_business_api import WhatsAppClient
        # client = WhatsAppClient(settings.WHATSAPP_ACCESS_TOKEN)
        # client.send_message(
        #     to=phone_number,
        #     text=message
        # )
        
        # Update log if provided
        if log_id:
            try:
                log = NotificationLog.objects.get(id=log_id)
                log.mark_sent()
            except NotificationLog.DoesNotExist:
                pass
        
        return {"status": "success", "phone": phone_number}
        
    except Exception as exc:
        # Update log with error if provided
        if log_id:
            try:
                log = NotificationLog.objects.get(id=log_id)
                log.mark_failed(str(exc))
            except NotificationLog.DoesNotExist:
                pass
        
        logger.error(f"WhatsApp sending failed: {exc}")
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@shared_task
def send_bulk_notifications(notification_data_list):
    """
    Send bulk notifications efficiently.
    
    Args:
        notification_data_list (list): List of notification data dictionaries
    """
    results = []
    
    for notification_data in notification_data_list:
        notification_type = notification_data.get('type')
        
        if notification_type == 'email':
            task = send_email_notification.delay(
                notification_data['recipient_email'],
                notification_data['template_name'],
                notification_data['context'],
                notification_data['subject']
            )
        elif notification_type == 'sms':
            task = send_sms_notification.delay(
                notification_data['phone_number'],
                notification_data['message']
            )
        elif notification_type == 'whatsapp':
            task = send_whatsapp_notification.delay(
                notification_data['phone_number'],
                notification_data['message']
            )
        else:
            logger.error(f"Unknown notification type: {notification_type}")
            continue
            
        results.append({
            'task_id': task.id,
            'type': notification_type,
            'recipient': notification_data.get('recipient_email') or notification_data.get('phone_number')
        })
    
    return results


@shared_task
def cleanup_old_notification_logs():
    """
    Clean up old notification logs (older than 30 days).
    """
    from .models import NotificationLog
    from datetime import timedelta
    
    cutoff_date = timezone.now() - timedelta(days=30)
    deleted_count = NotificationLog.objects.filter(created_at__lt=cutoff_date).delete()[0]
    
    logger.info(f"Cleaned up {deleted_count} old notification logs")
    return {"deleted_count": deleted_count}


@shared_task
def send_payment_reminder_notifications():
    """
    Send payment reminder notifications for overdue payments.
    """
    from venezuelan_pos.apps.payments.models import PaymentPlan
    from .services import NotificationService
    from datetime import timedelta
    
    # Find overdue payment plans
    overdue_plans = PaymentPlan.objects.filter(
        status='active',
        expires_at__lt=timezone.now() + timedelta(days=1)  # Due within 24 hours
    ).select_related('transaction__customer', 'transaction__event')
    
    notifications_sent = 0
    
    for plan in overdue_plans:
        try:
            notifications = NotificationService.send_payment_reminder(plan)
            if notifications:
                notifications_sent += len(notifications)
        except Exception as e:
            logger.error(f"Failed to send payment reminder for plan {plan.id}: {e}")
    
    logger.info(f"Sent {notifications_sent} payment reminder notifications")
    return {"notifications_sent": notifications_sent}


@shared_task
def send_event_reminder_notifications():
    """
    Send event reminder notifications 24 hours before events.
    """
    from venezuelan_pos.apps.events.models import Event
    from venezuelan_pos.apps.sales.models import Transaction
    from .services import NotificationService
    from datetime import timedelta
    
    # Find events starting in 24 hours
    tomorrow = timezone.now() + timedelta(hours=24)
    upcoming_events = Event.objects.filter(
        start_date__date=tomorrow.date(),
        status='active'
    )
    
    notifications_sent = 0
    
    for event in upcoming_events:
        # Get all customers with tickets for this event
        transactions = Transaction.objects.filter(
            event=event,
            status=Transaction.Status.COMPLETED
        ).select_related('customer').distinct('customer')
        
        for transaction in transactions:
            customer = transaction.customer
            if customer:
                try:
                    notifications = NotificationService.send_event_reminder(event, customer)
                    if notifications:
                        notifications_sent += len(notifications)
                except Exception as e:
                    logger.error(f"Failed to send event reminder for customer {customer.id}: {e}")
    
    logger.info(f"Sent {notifications_sent} event reminder notifications")
    return {"notifications_sent": notifications_sent}