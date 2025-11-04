from decimal import Decimal
import json

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from .models import Payment, PaymentPlan
from .fiscal_integration import FiscalCompletionService


class DecimalEncoder(json.JSONEncoder):
    """JSON encoder that handles Decimal objects."""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return str(obj)
        return super().default(obj)


def convert_decimals_to_str(obj):
    """Recursively convert Decimal objects to strings in dictionaries and lists."""
    if isinstance(obj, Decimal):
        return str(obj)
    elif isinstance(obj, dict):
        return {key: convert_decimals_to_str(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_decimals_to_str(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(convert_decimals_to_str(item) for item in obj)
    return obj


@receiver(pre_save, sender=Payment)
def calculate_payment_processing_fee(sender, instance, **kwargs):
    """Calculate processing fee before saving payment."""
    if not instance.processing_fee and instance.payment_method:
        instance.processing_fee = instance.payment_method.calculate_processing_fee(
            instance.amount
        )


@receiver(post_save, sender=Payment)
def handle_payment_completion(sender, instance, created, **kwargs):
    """Handle payment completion logic with fiscal validation."""
    if not created and instance.status == Payment.Status.COMPLETED:
        try:
            # Handle fiscal completion using fiscal integration service
            fiscal_result = FiscalCompletionService.handle_payment_completion_trigger(instance)

            # Store fiscal completion result in payment metadata if not already stored
            if not instance.metadata or 'fiscal_completion' not in instance.metadata:
                if instance.metadata is None:
                    instance.metadata = {}

                # Convert any Decimal objects to strings for JSON serialization
                fiscal_result_serializable = convert_decimals_to_str(fiscal_result)
                instance.metadata['fiscal_completion'] = fiscal_result_serializable

                # Use update to avoid triggering signals again
                Payment.objects.filter(pk=instance.pk).update(metadata=instance.metadata)
        except Exception:
            # Log error but don't fail the payment
            # In production, this should be logged properly
            pass


@receiver(post_save, sender=PaymentPlan)
def handle_payment_plan_creation(sender, instance, created, **kwargs):
    """Handle payment plan creation."""
    if created:
        # Update transaction status to reserved
        if instance.transaction.status == instance.transaction.Status.PENDING:
            instance.transaction.status = instance.transaction.Status.RESERVED
            instance.transaction.save(update_fields=['status'])


@receiver(post_save, sender=PaymentPlan)
def handle_payment_plan_completion(sender, instance, **kwargs):
    """Handle payment plan completion."""
    if instance.status == PaymentPlan.Status.COMPLETED:
        # Complete transaction if not already completed
        if instance.transaction.can_be_completed():
            instance.transaction.complete()
    
    elif instance.status in [PaymentPlan.Status.EXPIRED, PaymentPlan.Status.CANCELLED]:
        # Cancel transaction if it's still reserved
        if instance.transaction.status == instance.transaction.Status.RESERVED:
            instance.transaction.status = instance.transaction.Status.CANCELLED
            instance.transaction.save(update_fields=['status'])