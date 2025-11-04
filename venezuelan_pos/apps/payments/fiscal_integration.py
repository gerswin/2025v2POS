"""
Fiscal integration services for payment completion.
Handles fiscal series generation only when payments are fully completed.
"""

from decimal import Decimal
from django.db import transaction, models
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import Payment, PaymentPlan
from venezuelan_pos.apps.sales.models import Transaction


class FiscalPaymentValidator:
    """Validates payment completion for fiscal compliance."""
    
    @staticmethod
    def validate_payment_completion(transaction_obj):
        """
        Validate that a transaction is fully paid before fiscal series generation.
        
        Args:
            transaction_obj: Transaction instance
            
        Returns:
            tuple: (is_valid, message, payment_details)
            
        Raises:
            ValidationError: If validation fails
        """
        # Check if transaction has a payment plan
        payment_plan = getattr(transaction_obj, 'payment_plan', None)
        
        if payment_plan:
            return FiscalPaymentValidator._validate_payment_plan_completion(payment_plan)
        else:
            return FiscalPaymentValidator._validate_direct_payment_completion(transaction_obj)
    
    @staticmethod
    def _validate_payment_plan_completion(payment_plan):
        """Validate payment plan completion."""
        if not payment_plan.is_completed:
            return False, f"Payment plan is not completed. Remaining balance: {payment_plan.remaining_balance}", None
        
        # Verify all payments are completed
        incomplete_payments = payment_plan.payments.exclude(
            status=Payment.Status.COMPLETED
        )
        
        if incomplete_payments.exists():
            return False, "Payment plan has incomplete payments", None
        
        # Calculate total paid amount
        total_paid = payment_plan.payments.filter(
            status=Payment.Status.COMPLETED
        ).aggregate(
            total=models.Sum('amount')
        )['total'] or Decimal('0.00')
        
        if total_paid < payment_plan.total_amount:
            return False, f"Insufficient payment. Paid: {total_paid}, Required: {payment_plan.total_amount}", None
        
        payment_details = {
            'payment_plan_id': payment_plan.id,
            'total_amount': payment_plan.total_amount,
            'paid_amount': total_paid,
            'payment_count': payment_plan.payments.filter(status=Payment.Status.COMPLETED).count()
        }
        
        return True, "Payment plan fully completed", payment_details
    
    @staticmethod
    def _validate_direct_payment_completion(transaction_obj):
        """Validate direct payment completion (no payment plan)."""
        completed_payments = transaction_obj.payments.filter(
            status=Payment.Status.COMPLETED
        )
        
        if not completed_payments.exists():
            return False, "No completed payments found", None
        
        # Calculate total paid amount
        total_paid = completed_payments.aggregate(
            total=models.Sum('amount')
        )['total'] or Decimal('0.00')
        
        if total_paid < transaction_obj.total_amount:
            return False, f"Insufficient payment. Paid: {total_paid}, Required: {transaction_obj.total_amount}", None
        
        payment_details = {
            'total_amount': transaction_obj.total_amount,
            'paid_amount': total_paid,
            'payment_count': completed_payments.count()
        }
        
        return True, "Direct payment completed", payment_details
    
    @staticmethod
    def can_generate_fiscal_series(transaction_obj):
        """
        Check if fiscal series can be generated for a transaction.
        
        Args:
            transaction_obj: Transaction instance
            
        Returns:
            bool: True if fiscal series can be generated
        """
        # Transaction must be in correct status
        if not transaction_obj.can_be_completed():
            return False
        
        # Transaction must not already have fiscal series
        if transaction_obj.fiscal_series:
            return False
        
        # Validate payment completion
        is_valid, _, _ = FiscalPaymentValidator.validate_payment_completion(transaction_obj)
        return is_valid


class FiscalCompletionService:
    """Service for handling fiscal completion of transactions."""
    
    @staticmethod
    def complete_transaction_with_fiscal_validation(transaction_obj):
        """
        Complete a transaction with fiscal validation.

        Note: This method should be called within a transaction.atomic() block

        Args:
            transaction_obj: Transaction instance

        Returns:
            dict: Completion result with fiscal details

        Raises:
            ValidationError: If fiscal validation fails
        """
        # Validate payment completion
        is_valid, message, payment_details = FiscalPaymentValidator.validate_payment_completion(
            transaction_obj
        )

        if not is_valid:
            raise ValidationError(f"Cannot complete transaction: {message}")

        # Check if fiscal series can be generated
        if not FiscalPaymentValidator.can_generate_fiscal_series(transaction_obj):
            raise ValidationError("Transaction cannot generate fiscal series in current state")

        # Complete the transaction (this generates fiscal series)
        # Note: transaction.complete() also has an atomic block that needs to be removed
        completed_transaction = transaction_obj.complete()

        # Log fiscal completion
        fiscal_details = {
            'transaction_id': str(completed_transaction.id),
            'fiscal_series': completed_transaction.fiscal_series,
            'completed_at': completed_transaction.completed_at,
            'payment_details': payment_details,
            'total_amount': completed_transaction.total_amount,
            'customer_id': str(completed_transaction.customer.id)
        }

        return {
            'success': True,
            'transaction': completed_transaction,
            'fiscal_details': fiscal_details,
            'message': f"Transaction completed with fiscal series: {completed_transaction.fiscal_series}"
        }
    
    @staticmethod
    def handle_payment_completion_trigger(payment):
        """
        Handle fiscal completion when a payment is completed.
        This is called from payment completion signals/services.
        
        Args:
            payment: Payment instance that was just completed
            
        Returns:
            dict: Result of fiscal completion attempt
        """
        transaction_obj = payment.transaction
        
        try:
            # Check if transaction should be completed
            if payment.payment_plan:
                # For payment plans, only complete when plan is fully paid
                if payment.payment_plan.is_completed:
                    return FiscalCompletionService.complete_transaction_with_fiscal_validation(
                        transaction_obj
                    )
                else:
                    return {
                        'success': False,
                        'message': 'Payment plan not yet completed',
                        'remaining_balance': payment.payment_plan.remaining_balance
                    }
            else:
                # For direct payments, complete immediately if fully paid
                return FiscalCompletionService.complete_transaction_with_fiscal_validation(
                    transaction_obj
                )
        
        except ValidationError as e:
            return {
                'success': False,
                'error': str(e),
                'message': 'Fiscal validation failed'
            }
    
    @staticmethod
    def handle_payment_failure_trigger(payment):
        """
        Handle transaction status when a payment fails.
        
        Args:
            payment: Payment instance that failed
            
        Returns:
            dict: Result of failure handling
        """
        transaction_obj = payment.transaction
        
        # If transaction was completed, we need to handle the failure
        if transaction_obj.status == Transaction.Status.COMPLETED:
            # This is a complex scenario - a payment failed after transaction completion
            # In a real system, this might require manual intervention or refund processing
            return {
                'success': False,
                'message': 'Payment failed after transaction completion - manual review required',
                'requires_manual_review': True,
                'transaction_id': str(transaction_obj.id),
                'fiscal_series': transaction_obj.fiscal_series
            }
        
        # For non-completed transactions, just update status if needed
        if payment.payment_plan:
            # Payment plan exists - check if we should cancel the transaction
            active_payments = payment.payment_plan.payments.filter(
                status__in=[Payment.Status.PENDING, Payment.Status.PROCESSING]
            )
            
            if not active_payments.exists():
                # No more active payments - consider cancelling if no successful payments
                successful_payments = payment.payment_plan.payments.filter(
                    status=Payment.Status.COMPLETED
                )
                
                if not successful_payments.exists():
                    # No successful payments - can cancel transaction
                    transaction_obj.status = Transaction.Status.CANCELLED
                    transaction_obj.save(update_fields=['status'])
                    
                    return {
                        'success': True,
                        'message': 'Transaction cancelled due to payment failure',
                        'transaction_cancelled': True
                    }
        
        return {
            'success': True,
            'message': 'Payment failure handled',
            'transaction_cancelled': False
        }


class FiscalAuditService:
    """Service for fiscal audit and compliance tracking."""
    
    @staticmethod
    def get_fiscal_completion_audit(transaction_obj):
        """
        Get fiscal completion audit information for a transaction.
        
        Args:
            transaction_obj: Transaction instance
            
        Returns:
            dict: Audit information
        """
        audit_info = {
            'transaction_id': str(transaction_obj.id),
            'fiscal_series': transaction_obj.fiscal_series,
            'status': transaction_obj.status,
            'completed_at': transaction_obj.completed_at,
            'total_amount': transaction_obj.total_amount,
            'payment_summary': {}
        }
        
        # Payment summary
        payments = transaction_obj.payments.all()
        payment_summary = {
            'total_payments': payments.count(),
            'completed_payments': payments.filter(status=Payment.Status.COMPLETED).count(),
            'failed_payments': payments.filter(status=Payment.Status.FAILED).count(),
            'total_paid': payments.filter(status=Payment.Status.COMPLETED).aggregate(
                total=models.Sum('amount')
            )['total'] or Decimal('0.00')
        }
        
        audit_info['payment_summary'] = payment_summary
        
        # Payment plan information
        if hasattr(transaction_obj, 'payment_plan'):
            payment_plan = transaction_obj.payment_plan
            audit_info['payment_plan'] = {
                'plan_type': payment_plan.plan_type,
                'total_amount': payment_plan.total_amount,
                'paid_amount': payment_plan.paid_amount,
                'remaining_balance': payment_plan.remaining_balance,
                'status': payment_plan.status,
                'expires_at': payment_plan.expires_at,
                'completed_at': payment_plan.completed_at
            }
        
        # Fiscal validation status
        is_valid, message, _ = FiscalPaymentValidator.validate_payment_completion(transaction_obj)
        audit_info['fiscal_validation'] = {
            'is_valid': is_valid,
            'message': message,
            'can_generate_series': FiscalPaymentValidator.can_generate_fiscal_series(transaction_obj)
        }
        
        return audit_info
    
    @staticmethod
    def validate_fiscal_integrity(tenant=None):
        """
        Validate fiscal integrity across transactions.
        
        Args:
            tenant: Optional tenant to filter by
            
        Returns:
            dict: Integrity validation results
        """
        from django.db import models
        
        # Base queryset
        transactions = Transaction.objects.all()
        if tenant:
            transactions = transactions.filter(tenant=tenant)
        
        # Find transactions with fiscal series but incomplete payments
        completed_transactions = transactions.filter(
            status=Transaction.Status.COMPLETED,
            fiscal_series__isnull=False
        )
        
        integrity_issues = []
        
        for transaction_obj in completed_transactions:
            try:
                is_valid, message, _ = FiscalPaymentValidator.validate_payment_completion(transaction_obj)
                if not is_valid:
                    integrity_issues.append({
                        'transaction_id': str(transaction_obj.id),
                        'fiscal_series': transaction_obj.fiscal_series,
                        'issue': message,
                        'severity': 'high'
                    })
            except Exception as e:
                integrity_issues.append({
                    'transaction_id': str(transaction_obj.id),
                    'fiscal_series': transaction_obj.fiscal_series,
                    'issue': f"Validation error: {str(e)}",
                    'severity': 'critical'
                })
        
        return {
            'total_transactions_checked': completed_transactions.count(),
            'integrity_issues': integrity_issues,
            'issues_count': len(integrity_issues),
            'is_valid': len(integrity_issues) == 0
        }