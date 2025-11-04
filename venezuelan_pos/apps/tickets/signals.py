from django.db.models.signals import post_save
from django.dispatch import receiver
from venezuelan_pos.apps.sales.models import Transaction
from .models import DigitalTicket
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Transaction)
def generate_digital_tickets_on_completion(sender, instance, created, **kwargs):
    """
    Generate digital tickets when a transaction is completed.
    This signal is triggered when a transaction status changes to COMPLETED.
    """
    # Only generate tickets for completed transactions with fiscal series
    if (instance.status == Transaction.Status.COMPLETED and 
        instance.fiscal_series and 
        not instance.digital_tickets.exists()):
        
        try:
            # Check if event has digital tickets enabled
            if hasattr(instance.event, 'event_configuration'):
                config = instance.event.event_configuration
                if not config.digital_tickets_enabled:
                    logger.info(f"Digital tickets disabled for event {instance.event.id}")
                    return
            
            # Generate digital tickets
            tickets = DigitalTicket.objects.generate_for_transaction(instance)
            logger.info(f"Generated {len(tickets)} digital tickets for transaction {instance.id}")
            
            # Send ticket delivery notification
            try:
                from venezuelan_pos.apps.notifications.services import NotificationService
                NotificationService.send_ticket_delivery(instance)
                logger.info(f"Sent ticket delivery notification for transaction {instance.id}")
            except Exception as e:
                logger.error(f"Failed to send ticket delivery notification for transaction {instance.id}: {e}")
            
        except Exception as e:
            # Log error but don't fail transaction completion
            logger.error(f"Failed to generate digital tickets for transaction {instance.id}: {e}")


@receiver(post_save, sender=DigitalTicket)
def generate_qr_code_on_creation(sender, instance, created, **kwargs):
    """
    Generate QR code when a digital ticket is created.
    This ensures every ticket has a QR code for validation.
    """
    if created and not instance.qr_code_data:
        try:
            instance.generate_qr_code()
            logger.info(f"Generated QR code for ticket {instance.ticket_number}")
        except Exception as e:
            logger.error(f"Failed to generate QR code for ticket {instance.ticket_number}: {e}")