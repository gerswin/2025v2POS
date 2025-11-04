"""
Payment processing services.
Handles payment plan creation, payment processing, and reservation management.
"""

from decimal import Decimal
from datetime import timedelta
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError

from .models import PaymentMethod, PaymentPlan, Payment
from venezuelan_pos.apps.sales.models import Transaction, ReservedTicket
from venezuelan_pos.apps.events.models import EventConfiguration
from .fiscal_integration import FiscalCompletionService


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


class PaymentPlanService:
    """Service for managing payment plans."""
    
    @staticmethod
    def _validate_event_allows_partial_payments(transaction_obj):
        """Ensure event configuration permits partial or installment payments."""
        try:
            event_config = EventConfiguration.objects.get(event=transaction_obj.event)
        except EventConfiguration.DoesNotExist:
            raise ValidationError("Event configuration not found; partial payments are disabled.")

        if not event_config.partial_payments_enabled:
            raise ValidationError("Partial payments are not enabled for this event.")

        return event_config

    @staticmethod
    def _coerce_expiry(expires_at, event_config):
        """Return an expiry datetime, defaulting to event configuration days."""
        if expires_at:
            return expires_at

        expiry_days = event_config.payment_plan_expiry_days or 1
        return timezone.now() + timedelta(days=expiry_days)

    @staticmethod
    def _validate_down_payment(amount, transaction_obj, event_config):
        """Validate that the down payment meets minimum threshold if configured."""
        if amount is None:
            return

        min_percentage = event_config.min_down_payment_percentage or Decimal('0.00')
        if not isinstance(min_percentage, Decimal):
            min_percentage = Decimal(str(min_percentage))

        min_required = transaction_obj.total_amount * (min_percentage / Decimal('100')) if min_percentage > 0 else Decimal('0.00')

        if amount < min_required:
            raise ValidationError(
                f"Initial payment must be at least {min_percentage}% of the total ({min_required:.2f})."
            )
        if amount > transaction_obj.total_amount:
            raise ValidationError("Initial payment cannot exceed the transaction total.")

    @staticmethod
    def _validate_installment_count(installment_count, event_config):
        """Validate installment count respects event configuration limits."""
        max_installments = event_config.max_installments or 1
        if installment_count < 1:
            raise ValidationError("Installment plans require at least one installment.")
        if installment_count > max_installments:
            raise ValidationError(
                f"Installment count exceeds allowed maximum ({max_installments})."
            )

    @staticmethod
    def create_installment_plan(
        transaction_obj,
        installment_count,
        expires_at=None,
        notes=None,
        initial_payment_amount=None,
        initial_payment_method=None
    ):
        """
        Create an installment payment plan for a transaction.

        Note: This method should be called within a transaction.atomic() block

        Args:
            transaction_obj: Transaction instance
            installment_count: Number of installments
            expires_at: When the payment plan expires
            notes: Optional notes

        Returns:
            PaymentPlan instance

        Raises:
            ValidationError: If transaction already has a payment plan or other validation errors
        """
        if hasattr(transaction_obj, 'payment_plan'):
            raise ValidationError("Transaction already has a payment plan")

        if transaction_obj.status != Transaction.Status.PENDING:
            raise ValidationError("Can only create payment plans for pending transactions")

        event_config = PaymentPlanService._validate_event_allows_partial_payments(transaction_obj)
        if not event_config.installment_plans_enabled:
            raise ValidationError("Installment plans are not enabled for this event.")

        PaymentPlanService._validate_installment_count(installment_count, event_config)
        expires_at = PaymentPlanService._coerce_expiry(expires_at, event_config)
        PaymentPlanService._validate_down_payment(initial_payment_amount, transaction_obj, event_config)

        # Create payment plan
        payment_plan = PaymentPlan.create_installment_plan(
            transaction=transaction_obj,
            customer=transaction_obj.customer,
            installment_count=installment_count,
            expires_at=expires_at
        )

        if notes:
            payment_plan.notes = notes
            payment_plan.save(update_fields=['notes'])

        # Update transaction status to reserved
        transaction_obj.status = Transaction.Status.RESERVED
        transaction_obj.transaction_type = Transaction.TransactionType.PARTIAL_PAYMENT
        transaction_obj.save(update_fields=['status', 'transaction_type'])

        # Create reserved tickets for numbered seats
        PaymentPlanService._create_reserved_tickets(transaction_obj, expires_at)

        if initial_payment_amount:
            PaymentPlanService._record_initial_payment(
                transaction_obj=transaction_obj,
                payment_plan=payment_plan,
                amount=initial_payment_amount,
                event_config=event_config,
                payment_method=initial_payment_method
            )

        return payment_plan

    @staticmethod
    def create_flexible_plan(
        transaction_obj,
        expires_at=None,
        notes=None,
        initial_payment_amount=None,
        initial_payment_method=None
    ):
        """
        Create a flexible payment plan for a transaction.

        Note: This method should be called within a transaction.atomic() block

        Args:
            transaction_obj: Transaction instance
            expires_at: When the payment plan expires
            notes: Optional notes

        Returns:
            PaymentPlan instance

        Raises:
            ValidationError: If transaction already has a payment plan or other validation errors
        """
        if hasattr(transaction_obj, 'payment_plan'):
            raise ValidationError("Transaction already has a payment plan")

        if transaction_obj.status != Transaction.Status.PENDING:
            raise ValidationError("Can only create payment plans for pending transactions")

        event_config = PaymentPlanService._validate_event_allows_partial_payments(transaction_obj)
        if not event_config.flexible_payments_enabled:
            raise ValidationError("Flexible plans are not enabled for this event.")

        expires_at = PaymentPlanService._coerce_expiry(expires_at, event_config)
        PaymentPlanService._validate_down_payment(initial_payment_amount, transaction_obj, event_config)

        # Create payment plan
        payment_plan = PaymentPlan.create_flexible_plan(
            transaction=transaction_obj,
            customer=transaction_obj.customer,
            expires_at=expires_at
        )

        if notes:
            payment_plan.notes = notes
            payment_plan.save(update_fields=['notes'])

        # Update transaction status to reserved
        transaction_obj.status = Transaction.Status.RESERVED
        transaction_obj.transaction_type = Transaction.TransactionType.PARTIAL_PAYMENT
        transaction_obj.save(update_fields=['status', 'transaction_type'])

        # Create reserved tickets for numbered seats
        PaymentPlanService._create_reserved_tickets(transaction_obj, expires_at)

        if initial_payment_amount:
            PaymentPlanService._record_initial_payment(
                transaction_obj=transaction_obj,
                payment_plan=payment_plan,
                amount=initial_payment_amount,
                event_config=event_config,
                payment_method=initial_payment_method
            )

        return payment_plan

    @staticmethod
    def _record_initial_payment(transaction_obj, payment_plan, amount, event_config, payment_method=None):
        """Create and complete the initial payment for the plan."""
        if amount <= 0:
            raise ValidationError("Initial payment amount must be positive.")

        payment_method = payment_method or PaymentMethod.objects.filter(
            tenant=transaction_obj.tenant,
            allows_partial=True,
            is_active=True
        ).order_by('sort_order').first()

        if not payment_method:
            raise ValidationError("No payment method configured to allow partial payments.")
        if not payment_method.allows_partial:
            raise ValidationError("Selected payment method does not allow partial payments.")

        # Create payment using the standard service
        # The validation in can_accept_payment is now flexible for initial payments
        payment = PaymentProcessingService.create_payment(
            transaction_obj=transaction_obj,
            payment_method=payment_method,
            amount=amount,
            currency=transaction_obj.currency,
            notes="Initial deposit for payment plan",
        )

        PaymentProcessingService.process_payment(payment)
    
    @staticmethod
    def _create_reserved_tickets(transaction_obj, expires_at):
        """Create reserved tickets for transaction items."""
        for item in transaction_obj.items.all():
            if item.seat:
                # Numbered seat - create individual reservation
                ReservedTicket.objects.create(
                    tenant=transaction_obj.tenant,
                    transaction=transaction_obj,
                    seat=item.seat,
                    zone=item.zone,
                    quantity=1,
                    reserved_until=expires_at
                )
                
                # Update seat status to reserved
                item.seat.status = 'reserved'
                item.seat.save(update_fields=['status'])
            
            else:
                # General admission - create zone reservation
                ReservedTicket.objects.create(
                    tenant=transaction_obj.tenant,
                    transaction=transaction_obj,
                    zone=item.zone,
                    quantity=item.quantity,
                    reserved_until=expires_at
                )
    
    @staticmethod
    def expire_payment_plan(payment_plan):
        """
        Expire a payment plan and release reserved tickets.
        
        Args:
            payment_plan: PaymentPlan instance
        """
        with transaction.atomic():
            payment_plan.expire()
            
            # Release all reserved tickets
            for reservation in payment_plan.transaction.reserved_tickets.filter(
                status=ReservedTicket.Status.ACTIVE
            ):
                reservation.expire()
    
    @staticmethod
    def cancel_payment_plan(payment_plan):
        """
        Cancel a payment plan and release reserved tickets.
        
        Args:
            payment_plan: PaymentPlan instance
        """
        with transaction.atomic():
            payment_plan.cancel()
            
            # Release all reserved tickets
            for reservation in payment_plan.transaction.reserved_tickets.filter(
                status=ReservedTicket.Status.ACTIVE
            ):
                reservation.cancel()


class PaymentProcessingService:
    """Service for processing payments."""
    
    @staticmethod
    def create_payment(transaction_obj, payment_method, amount, **kwargs):
        """
        Create a new payment for a transaction.
        
        Args:
            transaction_obj: Transaction instance
            payment_method: PaymentMethod instance
            amount: Payment amount
            **kwargs: Additional payment data
            
        Returns:
            Payment instance
            
        Raises:
            ValidationError: If payment validation fails
        """
        # Get payment plan if exists
        payment_plan = getattr(transaction_obj, 'payment_plan', None)
        
        # Validate payment amount
        if payment_plan:
            can_pay, message = payment_plan.can_accept_payment(amount)
            if not can_pay:
                raise ValidationError(message)
        else:
            # For transactions without payment plans, amount should match total
            if amount != transaction_obj.total_amount:
                raise ValidationError("Payment amount must match transaction total")
        
        # Create payment
        payment = Payment.objects.create(
            tenant=transaction_obj.tenant,
            transaction=transaction_obj,
            payment_method=payment_method,
            payment_plan=payment_plan,
            amount=amount,
            currency=kwargs.get('currency', 'USD'),
            exchange_rate=kwargs.get('exchange_rate', Decimal('1.0000')),
            reference_number=kwargs.get('reference_number', ''),
            notes=kwargs.get('notes', '')
        )
        
        return payment
    
    @staticmethod
    def process_payment(payment, external_transaction_id=None, processor_response=None):
        """
        Process a payment and handle completion logic.

        Args:
            payment: Payment instance
            external_transaction_id: External transaction ID
            processor_response: Response from payment processor

        Returns:
            Payment instance

        Note: This method should be called within a transaction.atomic() block
        """
        try:
            # Mark payment as completed
            payment.mark_completed(
                external_transaction_id=external_transaction_id,
                processor_response=processor_response
            )

            # Handle fiscal completion using fiscal integration service
            fiscal_result = FiscalCompletionService.handle_payment_completion_trigger(payment)

            # Store fiscal completion result in payment metadata
            if payment.metadata is None:
                payment.metadata = {}
            # Convert Decimal objects to strings for JSON serialization
            payment.metadata['fiscal_completion'] = convert_decimals_to_str(fiscal_result)
            payment.save(update_fields=['metadata'])

            return payment
        except ValidationError as e:
            # Re-raise validation errors from payment plan
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Payment processing validation error: {e}")
            raise
    
    @staticmethod
    def _complete_transaction(transaction_obj):
        """Complete a transaction and generate fiscal series with validation."""
        # Use fiscal completion service for proper validation
        return FiscalCompletionService.complete_transaction_with_fiscal_validation(transaction_obj)
    
    @staticmethod
    def fail_payment(payment, error_message=None, processor_response=None):
        """
        Mark a payment as failed and handle fiscal implications.
        
        Args:
            payment: Payment instance
            error_message: Error message
            processor_response: Response from payment processor
        """
        with transaction.atomic():
            payment.mark_failed(
                error_message=error_message,
                processor_response=processor_response
            )
            
            # Handle fiscal implications of payment failure
            fiscal_result = FiscalCompletionService.handle_payment_failure_trigger(payment)

            # Store fiscal failure result in payment metadata
            if payment.metadata is None:
                payment.metadata = {}
            # Convert Decimal objects to strings for JSON serialization
            payment.metadata['fiscal_failure'] = convert_decimals_to_str(fiscal_result)
            payment.save(update_fields=['metadata'])
    
    @staticmethod
    def refund_payment(payment, refund_amount=None, reason=None):
        """
        Process a payment refund.
        
        Args:
            payment: Payment instance
            refund_amount: Amount to refund (defaults to full amount)
            reason: Refund reason
            
        Returns:
            Payment instance
        """
        with transaction.atomic():
            payment.refund(refund_amount=refund_amount, reason=reason)
            
            # If payment plan exists, adjust paid amount
            if payment.payment_plan:
                refund_amount = refund_amount or payment.amount
                payment.payment_plan.paid_amount -= refund_amount
                payment.payment_plan.remaining_balance += refund_amount
                
                # Reactivate payment plan if it was completed
                if payment.payment_plan.status == PaymentPlan.Status.COMPLETED:
                    payment.payment_plan.status = PaymentPlan.Status.ACTIVE
                    payment.payment_plan.completed_at = None
                
                payment.payment_plan.save(update_fields=[
                    'paid_amount', 'remaining_balance', 'status', 'completed_at'
                ])
            
            return payment


class ReservationService:
    """Service for managing ticket reservations."""
    
    @staticmethod
    def cleanup_expired_reservations():
        """
        Clean up expired reservations and payment plans.
        This should be run periodically (e.g., via Celery task).
        
        Returns:
            dict: Statistics about cleaned up reservations
        """
        now = timezone.now()
        stats = {
            'expired_reservations': 0,
            'expired_payment_plans': 0,
            'released_seats': 0
        }
        
        with transaction.atomic():
            # Find expired reservations
            expired_reservations = ReservedTicket.objects.filter(
                status=ReservedTicket.Status.ACTIVE,
                reserved_until__lte=now
            )
            
            for reservation in expired_reservations:
                reservation.expire()
                stats['expired_reservations'] += 1
                
                if reservation.seat:
                    stats['released_seats'] += 1
            
            # Find expired payment plans
            expired_plans = PaymentPlan.objects.filter(
                status=PaymentPlan.Status.ACTIVE,
                expires_at__lte=now
            )
            
            for plan in expired_plans:
                PaymentPlanService.expire_payment_plan(plan)
                stats['expired_payment_plans'] += 1
        
        return stats
    
    @staticmethod
    def extend_reservation(reservation, new_expiry_time):
        """
        Extend a reservation's expiry time.
        
        Args:
            reservation: ReservedTicket instance
            new_expiry_time: New expiry datetime
            
        Returns:
            ReservedTicket instance
        """
        if not reservation.is_active:
            raise ValidationError("Cannot extend inactive reservation")
        
        if new_expiry_time <= timezone.now():
            raise ValidationError("New expiry time must be in the future")
        
        reservation.reserved_until = new_expiry_time
        reservation.save(update_fields=['reserved_until'])
        
        # Also extend payment plan if exists
        if reservation.transaction.payment_plan:
            payment_plan = reservation.transaction.payment_plan
            if payment_plan.expires_at < new_expiry_time:
                payment_plan.expires_at = new_expiry_time
                payment_plan.save(update_fields=['expires_at'])
        
        return reservation


class PaymentReminderService:
    """Service for managing payment reminders."""
    
    @staticmethod
    def get_payment_plans_needing_reminders():
        """
        Get payment plans that need reminders.
        
        Returns:
            QuerySet: PaymentPlan instances needing reminders
        """
        # Plans expiring in the next 24 hours
        reminder_threshold = timezone.now() + timedelta(hours=24)
        
        return PaymentPlan.objects.filter(
            status=PaymentPlan.Status.ACTIVE,
            expires_at__lte=reminder_threshold,
            expires_at__gt=timezone.now()
        ).select_related('transaction', 'customer')
    
    @staticmethod
    def send_payment_reminder(payment_plan):
        """
        Send payment reminder for a payment plan.
        This would integrate with the notification system.
        
        Args:
            payment_plan: PaymentPlan instance
            
        Returns:
            bool: True if reminder was sent successfully
        """
        # This would integrate with the notification system
        # For now, just return True as a placeholder
        
        # Example integration:
        # from venezuelan_pos.apps.notifications.services import NotificationService
        # 
        # NotificationService.send_payment_reminder(
        #     customer=payment_plan.customer,
        #     payment_plan=payment_plan,
        #     channels=['email', 'sms']
        # )
        
        return True
    
    @staticmethod
    def process_payment_reminders():
        """
        Process all payment reminders that need to be sent.
        
        Returns:
            dict: Statistics about reminders sent
        """
        plans_needing_reminders = PaymentReminderService.get_payment_plans_needing_reminders()
        
        stats = {
            'reminders_sent': 0,
            'reminders_failed': 0
        }
        
        for plan in plans_needing_reminders:
            try:
                if PaymentReminderService.send_payment_reminder(plan):
                    stats['reminders_sent'] += 1
                else:
                    stats['reminders_failed'] += 1
            except Exception:
                stats['reminders_failed'] += 1
        
        return stats
