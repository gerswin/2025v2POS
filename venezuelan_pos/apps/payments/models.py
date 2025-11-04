import uuid
from decimal import Decimal
from django.db import models, transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db.models import F, Q, Sum
from venezuelan_pos.apps.tenants.models import TenantAwareModel
from venezuelan_pos.apps.sales.models import Transaction
from venezuelan_pos.apps.customers.models import Customer


class PaymentMethodManager(models.Manager):
    """Manager for PaymentMethod model."""
    
    def active_for_tenant(self, tenant):
        """Get active payment methods for a tenant."""
        return self.filter(tenant=tenant, is_active=True)
    
    def by_type(self, method_type):
        """Get payment methods by type."""
        return self.filter(method_type=method_type, is_active=True)


class PaymentMethod(TenantAwareModel):
    """
    Payment method configuration model.
    Defines available payment methods for each tenant.
    """
    
    class MethodType(models.TextChoices):
        CASH = 'cash', 'Cash'
        CREDIT_CARD = 'credit_card', 'Credit Card'
        DEBIT_CARD = 'debit_card', 'Debit Card'
        BANK_TRANSFER = 'bank_transfer', 'Bank Transfer'
        PAGO_MOVIL = 'pago_movil', 'Pago Móvil'
        ZELLE = 'zelle', 'Zelle'
        PAYPAL = 'paypal', 'PayPal'
        OTHER = 'other', 'Other'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Method details
    method_type = models.CharField(
        max_length=20,
        choices=MethodType.choices,
        help_text="Type of payment method"
    )
    name = models.CharField(
        max_length=100,
        help_text="Display name for this payment method"
    )
    description = models.TextField(
        blank=True,
        help_text="Description of the payment method"
    )
    
    # Configuration
    requires_reference = models.BooleanField(
        default=False,
        help_text="Whether this method requires a reference number"
    )
    allows_partial = models.BooleanField(
        default=True,
        help_text="Whether this method allows partial payments"
    )
    processing_fee_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=Decimal('0.0000'),
        help_text="Processing fee as percentage (e.g., 0.0300 for 3%)"
    )
    processing_fee_fixed = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Fixed processing fee amount"
    )
    
    # Status and ordering
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this payment method is active"
    )
    sort_order = models.PositiveIntegerField(
        default=0,
        help_text="Display order for this payment method"
    )
    
    # Configuration data
    configuration = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional configuration data (API keys, account info, etc.)"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    objects = PaymentMethodManager()
    
    class Meta:
        db_table = 'payment_methods'
        verbose_name = 'Payment Method'
        verbose_name_plural = 'Payment Methods'
        ordering = ['sort_order', 'name']
        unique_together = ['tenant', 'method_type', 'name']
        indexes = [
            models.Index(fields=['tenant', 'is_active']),
            models.Index(fields=['method_type']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.get_method_type_display()})"
    
    def clean(self):
        """Validate payment method data."""
        super().clean()
        
        if self.processing_fee_percentage < 0:
            raise ValidationError({
                'processing_fee_percentage': 'Processing fee percentage cannot be negative'
            })
        
        if self.processing_fee_fixed < 0:
            raise ValidationError({
                'processing_fee_fixed': 'Fixed processing fee cannot be negative'
            })
    
    def calculate_processing_fee(self, amount):
        """Calculate processing fee for given amount."""
        percentage_fee = amount * self.processing_fee_percentage
        total_fee = percentage_fee + self.processing_fee_fixed
        return total_fee


class PaymentPlanManager(models.Manager):
    """Manager for PaymentPlan model."""
    
    def active_plans(self):
        """Get active payment plans."""
        return self.filter(status=PaymentPlan.Status.ACTIVE)
    
    def expired_plans(self):
        """Get expired payment plans."""
        return self.filter(
            status=PaymentPlan.Status.ACTIVE,
            expires_at__lte=timezone.now()
        )
    
    def for_transaction(self, transaction):
        """Get payment plan for a transaction."""
        return self.filter(transaction=transaction).first()


class PaymentPlan(TenantAwareModel):
    """
    Payment plan model for installments and flexible payments.
    Manages partial payment structures for transactions.
    """
    
    class PlanType(models.TextChoices):
        INSTALLMENT = 'installment', 'Installment Plan'
        FLEXIBLE = 'flexible', 'Flexible Payment'
    
    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        COMPLETED = 'completed', 'Completed'
        EXPIRED = 'expired', 'Expired'
        CANCELLED = 'cancelled', 'Cancelled'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Relationships
    transaction = models.OneToOneField(
        Transaction,
        on_delete=models.CASCADE,
        related_name='payment_plan',
        help_text="Transaction this payment plan is for"
    )
    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        related_name='payment_plans',
        help_text="Customer who owns this payment plan"
    )
    
    # Plan details
    plan_type = models.CharField(
        max_length=15,
        choices=PlanType.choices,
        help_text="Type of payment plan"
    )
    
    # Amounts
    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Total amount to be paid"
    )
    paid_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Amount already paid"
    )
    remaining_balance = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Remaining balance to be paid"
    )
    
    # Installment plan specific fields
    installment_count = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Number of installments (for installment plans)"
    )
    installment_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Amount per installment (for installment plans)"
    )
    
    # Timing
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(
        help_text="When this payment plan expires"
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When payment plan was completed"
    )
    
    # Status
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.ACTIVE,
        help_text="Current payment plan status"
    )
    
    # Configuration
    configuration = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional plan configuration (due dates, reminders, etc.)"
    )
    
    # Metadata
    notes = models.TextField(
        blank=True,
        help_text="Additional notes about the payment plan"
    )
    
    objects = PaymentPlanManager()
    
    class Meta:
        db_table = 'payment_plans'
        verbose_name = 'Payment Plan'
        verbose_name_plural = 'Payment Plans'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', 'status']),
            models.Index(fields=['transaction']),
            models.Index(fields=['customer']),
            models.Index(fields=['expires_at']),
        ]
    
    def __str__(self):
        return f"{self.get_plan_type_display()} - {self.customer.full_name} ({self.status})"
    
    def clean(self):
        """Validate payment plan data."""
        super().clean()
        
        if self.total_amount <= 0:
            raise ValidationError({'total_amount': 'Total amount must be positive'})
        
        if self.paid_amount < 0:
            raise ValidationError({'paid_amount': 'Paid amount cannot be negative'})
        
        if self.paid_amount > self.total_amount:
            raise ValidationError({'paid_amount': 'Paid amount cannot exceed total amount'})
        
        # Validate installment plan fields
        if self.plan_type == self.PlanType.INSTALLMENT:
            if not self.installment_count or self.installment_count <= 0:
                raise ValidationError({
                    'installment_count': 'Installment count is required for installment plans'
                })
            
            if not self.installment_amount or self.installment_amount <= 0:
                raise ValidationError({
                    'installment_amount': 'Installment amount is required for installment plans'
                })
    
    def save(self, *args, **kwargs):
        """Override save to calculate remaining balance."""
        self.remaining_balance = self.total_amount - self.paid_amount
        super().save(*args, **kwargs)
    
    @property
    def is_active(self):
        """Check if payment plan is active."""
        return self.status == self.Status.ACTIVE
    
    @property
    def is_completed(self):
        """Check if payment plan is completed."""
        return self.status == self.Status.COMPLETED
    
    @property
    def is_expired(self):
        """Check if payment plan has expired."""
        return (
            self.status == self.Status.ACTIVE and
            self.expires_at <= timezone.now()
        )
    
    @property
    def completion_percentage(self):
        """Get completion percentage."""
        if self.total_amount == 0:
            return Decimal('0.00')
        return (self.paid_amount / self.total_amount) * 100
    
    @property
    def next_installment_amount(self):
        """Get next installment amount for installment plans."""
        if self.plan_type != self.PlanType.INSTALLMENT:
            return None
        
        if self.remaining_balance <= self.installment_amount:
            return self.remaining_balance
        
        return self.installment_amount
    
    @property
    def installments_paid(self):
        """Get number of installments paid."""
        if self.plan_type != self.PlanType.INSTALLMENT or not self.installment_amount:
            return 0
        
        return int(self.paid_amount // self.installment_amount)
    
    @property
    def installments_remaining(self):
        """Get number of installments remaining."""
        if self.plan_type != self.PlanType.INSTALLMENT:
            return 0
        
        return self.installment_count - self.installments_paid
    
    def can_accept_payment(self, amount):
        """Check if plan can accept a payment of given amount."""
        if not self.is_active:
            return False, "Payment plan is not active"

        if self.is_expired:
            return False, "Payment plan has expired"

        if amount <= 0:
            return False, "Payment amount must be positive"

        if amount > self.remaining_balance:
            return False, "Payment amount exceeds remaining balance"

        # For installment plans, validate amount matches installment
        # BUT: be flexible with the initial payment (when paid_amount is 0)
        if self.plan_type == self.PlanType.INSTALLMENT and self.paid_amount > 0:
            expected_amount = self.next_installment_amount
            if amount != expected_amount:
                return False, f"Payment amount must be {expected_amount} for installment plan"

        return True, "Payment can be accepted"
    
    def add_payment(self, amount):
        """
        Add a payment to this plan.

        Note: This method validates and updates the payment plan.
        Should be called within a transaction.atomic() block from payment completion.
        """
        can_pay, message = self.can_accept_payment(amount)
        if not can_pay:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Payment validation failed: {message}. Amount: {amount}, Plan: {self.id}, Type: {self.plan_type}, Paid: {self.paid_amount}, Remaining: {self.remaining_balance}")
            raise ValidationError(message)

        self.paid_amount += amount
        self.remaining_balance = self.total_amount - self.paid_amount

        # Check if plan is completed
        if self.remaining_balance <= Decimal('0.00'):
            self.status = self.Status.COMPLETED
            self.completed_at = timezone.now()

        self.save(update_fields=['paid_amount', 'remaining_balance', 'status', 'completed_at'])
    
    def expire(self):
        """Mark payment plan as expired."""
        with transaction.atomic():
            self.status = self.Status.EXPIRED
            self.save(update_fields=['status'])
            
            # Release reserved tickets
            for reservation in self.transaction.reserved_tickets.filter(
                status='active'
            ):
                reservation.expire()
    
    def cancel(self):
        """Cancel payment plan."""
        with transaction.atomic():
            self.status = self.Status.CANCELLED
            self.save(update_fields=['status'])
            
            # Release reserved tickets
            for reservation in self.transaction.reserved_tickets.filter(
                status='active'
            ):
                reservation.cancel()
    
    @classmethod
    def create_installment_plan(cls, transaction, customer, installment_count, expires_at):
        """Create an installment payment plan."""
        installment_amount = transaction.total_amount / installment_count
        
        return cls.objects.create(
            tenant=transaction.tenant,
            transaction=transaction,
            customer=customer,
            plan_type=cls.PlanType.INSTALLMENT,
            total_amount=transaction.total_amount,
            installment_count=installment_count,
            installment_amount=installment_amount,
            expires_at=expires_at
        )
    
    @classmethod
    def create_flexible_plan(cls, transaction, customer, expires_at):
        """Create a flexible payment plan."""
        return cls.objects.create(
            tenant=transaction.tenant,
            transaction=transaction,
            customer=customer,
            plan_type=cls.PlanType.FLEXIBLE,
            total_amount=transaction.total_amount,
            expires_at=expires_at
        )


class PaymentManager(models.Manager):
    """Manager for Payment model."""
    
    def for_transaction(self, transaction):
        """Get payments for a transaction."""
        return self.filter(transaction=transaction)
    
    def successful_payments(self):
        """Get successful payments."""
        return self.filter(status=Payment.Status.COMPLETED)
    
    def pending_payments(self):
        """Get pending payments."""
        return self.filter(status=Payment.Status.PENDING)
    
    def failed_payments(self):
        """Get failed payments."""
        return self.filter(status=Payment.Status.FAILED)


class Payment(TenantAwareModel):
    """
    Individual payment record model.
    Represents each payment made towards a transaction.
    """
    
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        PROCESSING = 'processing', 'Processing'
        COMPLETED = 'completed', 'Completed'
        FAILED = 'failed', 'Failed'
        CANCELLED = 'cancelled', 'Cancelled'
        REFUNDED = 'refunded', 'Refunded'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Relationships
    transaction = models.ForeignKey(
        Transaction,
        on_delete=models.PROTECT,
        related_name='payments',
        help_text="Transaction this payment is for"
    )
    payment_method = models.ForeignKey(
        PaymentMethod,
        on_delete=models.PROTECT,
        related_name='payments',
        help_text="Payment method used"
    )
    payment_plan = models.ForeignKey(
        PaymentPlan,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='payments',
        help_text="Payment plan this payment belongs to (if any)"
    )
    
    # Payment details
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Payment amount"
    )
    processing_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Processing fee charged"
    )
    net_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Net amount after processing fees"
    )
    
    # Currency
    currency = models.CharField(
        max_length=3,
        default='USD',
        help_text="Payment currency"
    )
    exchange_rate = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        default=Decimal('1.0000'),
        help_text="Exchange rate used"
    )
    
    # Reference information
    reference_number = models.CharField(
        max_length=100,
        blank=True,
        help_text="External reference number (bank ref, card auth, etc.)"
    )
    external_transaction_id = models.CharField(
        max_length=100,
        blank=True,
        help_text="External transaction ID from payment processor"
    )
    
    # Status and timing
    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.PENDING,
        help_text="Current payment status"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When payment was processed"
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When payment was completed"
    )
    
    # Additional data
    processor_response = models.JSONField(
        default=dict,
        blank=True,
        help_text="Response data from payment processor"
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional payment metadata"
    )
    notes = models.TextField(
        blank=True,
        help_text="Additional payment notes"
    )
    
    objects = PaymentManager()
    
    class Meta:
        db_table = 'payments'
        verbose_name = 'Payment'
        verbose_name_plural = 'Payments'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', 'status']),
            models.Index(fields=['transaction']),
            models.Index(fields=['payment_method']),
            models.Index(fields=['payment_plan']),
            models.Index(fields=['reference_number']),
            models.Index(fields=['external_transaction_id']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"Payment {self.amount} {self.currency} - {self.get_status_display()}"
    
    def clean(self):
        """Validate payment data."""
        super().clean()
        
        if self.amount <= 0:
            raise ValidationError({'amount': 'Payment amount must be positive'})
        
        if self.processing_fee < 0:
            raise ValidationError({'processing_fee': 'Processing fee cannot be negative'})
        
        if self.exchange_rate <= 0:
            raise ValidationError({'exchange_rate': 'Exchange rate must be positive'})
        
        # Validate payment method requires reference
        if (self.payment_method and 
            self.payment_method.requires_reference and 
            not self.reference_number):
            raise ValidationError({
                'reference_number': 'Reference number is required for this payment method'
            })
    
    def save(self, *args, **kwargs):
        """Override save to calculate net amount."""
        if not self.processing_fee:
            self.processing_fee = self.payment_method.calculate_processing_fee(self.amount)
        
        self.net_amount = self.amount - self.processing_fee
        super().save(*args, **kwargs)
    
    @property
    def is_completed(self):
        """Check if payment is completed."""
        return self.status == self.Status.COMPLETED
    
    @property
    def is_pending(self):
        """Check if payment is pending."""
        return self.status == self.Status.PENDING
    
    @property
    def is_failed(self):
        """Check if payment failed."""
        return self.status == self.Status.FAILED
    
    def mark_processing(self):
        """Mark payment as processing."""
        self.status = self.Status.PROCESSING
        self.processed_at = timezone.now()
        self.save(update_fields=['status', 'processed_at'])
    
    def mark_completed(self, external_transaction_id=None, processor_response=None):
        """
        Mark payment as completed.

        Note: This method should be called within a transaction.atomic() block
        """
        self.status = self.Status.COMPLETED
        self.completed_at = timezone.now()

        if external_transaction_id:
            self.external_transaction_id = external_transaction_id

        if processor_response:
            self.processor_response = processor_response

        self.save(update_fields=[
            'status', 'completed_at', 'external_transaction_id', 'processor_response'
        ])

        # Update payment plan if exists
        if self.payment_plan:
            self.payment_plan.add_payment(self.amount)

            # Check if transaction should be completed
            if self.payment_plan.is_completed:
                self.transaction.complete()
            else:
                # Send payment received notification for partial payments
                self._send_payment_received_notification()
        else:
            # For direct payments, transaction completion will handle purchase confirmation
            pass
    
    def _send_payment_received_notification(self):
        """Send payment received notification for partial payments."""
        try:
            from venezuelan_pos.apps.notifications.services import NotificationService
            
            # Only send if payment plan exists and customer has preferences enabled
            if self.payment_plan and self.transaction.customer:
                customer = self.transaction.customer
                prefs = getattr(customer, 'notification_preferences', None)
                
                if not prefs or prefs.payment_reminders:
                    context = {
                        'customer': customer,
                        'payment': self,
                        'payment_plan': self.payment_plan,
                        'transaction': self.transaction,
                        'event': self.transaction.event,
                        'amount_paid': self.amount,
                        'remaining_balance': self.payment_plan.remaining_balance,
                    }
                    
                    # Send email if available and enabled
                    if customer.email and (not prefs or prefs.email_enabled):
                        NotificationService.send_notification(
                            tenant=self.tenant,
                            template_name='payment_received',
                            recipient=customer.email,
                            channel='email',
                            context=context,
                            customer=customer,
                            transaction=self.transaction
                        )
        except Exception as e:
            # Log error but don't fail payment completion
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to send payment received notification for payment {self.id}: {e}")
    
    def mark_failed(self, error_message=None, processor_response=None):
        """Mark payment as failed."""
        self.status = self.Status.FAILED
        
        if error_message:
            self.notes = error_message
        
        if processor_response:
            self.processor_response = processor_response
        
        self.save(update_fields=['status', 'notes', 'processor_response'])
    
    def cancel(self):
        """Cancel payment."""
        if self.status not in [self.Status.PENDING, self.Status.PROCESSING]:
            raise ValidationError("Cannot cancel payment in current status")
        
        self.status = self.Status.CANCELLED
        self.save(update_fields=['status'])
    
    def refund(self, refund_amount=None, reason=None):
        """Process refund for this payment."""
        if not self.is_completed:
            raise ValidationError("Can only refund completed payments")
        
        refund_amount = refund_amount or self.amount
        
        if refund_amount > self.amount:
            raise ValidationError("Refund amount cannot exceed payment amount")
        
        # Create refund record (could be separate model in future)
        self.status = self.Status.REFUNDED
        self.notes = f"Refunded: {refund_amount} {self.currency}. Reason: {reason or 'N/A'}"
        self.save(update_fields=['status', 'notes'])


class PaymentReconciliation(TenantAwareModel):
    """
    Payment reconciliation model for audit trail and reporting.
    Tracks payment reconciliation activities and discrepancies.
    """
    
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        IN_PROGRESS = 'in_progress', 'In Progress'
        COMPLETED = 'completed', 'Completed'
        DISCREPANCY = 'discrepancy', 'Discrepancy Found'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Reconciliation period
    reconciliation_date = models.DateField(
        help_text="Date of reconciliation"
    )
    start_datetime = models.DateTimeField(
        help_text="Start of reconciliation period"
    )
    end_datetime = models.DateTimeField(
        help_text="End of reconciliation period"
    )
    
    # Payment method being reconciled
    payment_method = models.ForeignKey(
        PaymentMethod,
        on_delete=models.PROTECT,
        related_name='reconciliations',
        help_text="Payment method being reconciled"
    )
    
    # Reconciliation amounts
    system_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Total amount according to system records"
    )
    external_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Total amount according to external records (bank, processor)"
    )
    discrepancy_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Difference between system and external totals"
    )
    
    # Transaction counts
    system_transaction_count = models.PositiveIntegerField(
        help_text="Number of transactions in system"
    )
    external_transaction_count = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Number of transactions in external records"
    )
    
    # Status and timing
    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.PENDING,
        help_text="Reconciliation status"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When reconciliation was completed"
    )
    
    # Additional data
    reconciliation_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Detailed reconciliation data and findings"
    )
    notes = models.TextField(
        blank=True,
        help_text="Reconciliation notes and comments"
    )
    
    class Meta:
        db_table = 'payment_reconciliations'
        verbose_name = 'Payment Reconciliation'
        verbose_name_plural = 'Payment Reconciliations'
        ordering = ['-reconciliation_date', '-created_at']
        unique_together = ['tenant', 'payment_method', 'reconciliation_date']
        indexes = [
            models.Index(fields=['tenant', 'reconciliation_date']),
            models.Index(fields=['payment_method', 'status']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"Reconciliation {self.reconciliation_date} - {self.payment_method.name}"
    
    def clean(self):
        """Validate reconciliation data."""
        super().clean()
        
        if self.start_datetime >= self.end_datetime:
            raise ValidationError({
                'end_datetime': 'End datetime must be after start datetime'
            })
        
        if self.system_total < 0:
            raise ValidationError({'system_total': 'System total cannot be negative'})
        
        if self.external_total is not None and self.external_total < 0:
            raise ValidationError({'external_total': 'External total cannot be negative'})
    
    def save(self, *args, **kwargs):
        """Override save to calculate discrepancy."""
        if self.external_total is not None:
            self.discrepancy_amount = abs(self.system_total - self.external_total)
        
        super().save(*args, **kwargs)
    
    @property
    def has_discrepancy(self):
        """Check if there's a discrepancy."""
        return self.discrepancy_amount > Decimal('0.00')
    
    @property
    def is_completed(self):
        """Check if reconciliation is completed."""
        return self.status == self.Status.COMPLETED
    
    def calculate_system_totals(self):
        """Calculate totals from system records."""
        payments = Payment.objects.filter(
            tenant=self.tenant,
            payment_method=self.payment_method,
            status=Payment.Status.COMPLETED,
            completed_at__range=[self.start_datetime, self.end_datetime]
        )
        
        totals = payments.aggregate(
            total_amount=Sum('amount'),
            count=models.Count('id')
        )
        
        self.system_total = totals['total_amount'] or Decimal('0.00')
        self.system_transaction_count = totals['count'] or 0
        
        return {
            'total': self.system_total,
            'count': self.system_transaction_count,
            'payments': payments
        }
    
    def complete_reconciliation(self, external_total=None, external_count=None, notes=None):
        """Complete the reconciliation process."""
        with transaction.atomic():
            if external_total is not None:
                self.external_total = external_total
            
            if external_count is not None:
                self.external_transaction_count = external_count
            
            if notes:
                self.notes = notes
            
            # Determine status based on discrepancy
            if self.has_discrepancy:
                self.status = self.Status.DISCREPANCY
            else:
                self.status = self.Status.COMPLETED
            
            self.completed_at = timezone.now()
            self.save()
    
    @classmethod
    def create_daily_reconciliation(cls, tenant, payment_method, reconciliation_date):
        """Create a daily reconciliation record."""
        from datetime import datetime, time
        
        start_datetime = datetime.combine(reconciliation_date, time.min)
        end_datetime = datetime.combine(reconciliation_date, time.max)
        
        reconciliation = cls.objects.create(
            tenant=tenant,
            payment_method=payment_method,
            reconciliation_date=reconciliation_date,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            system_total=Decimal('0.00'),
            system_transaction_count=0
        )
        
        # Calculate system totals
        reconciliation.calculate_system_totals()
        reconciliation.save()
        
        return reconciliation