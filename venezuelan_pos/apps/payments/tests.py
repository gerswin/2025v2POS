from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta

from venezuelan_pos.apps.tenants.models import Tenant
from venezuelan_pos.apps.customers.models import Customer
from venezuelan_pos.apps.events.models import Event, Venue
from venezuelan_pos.apps.sales.models import Transaction
from .models import PaymentMethod, PaymentPlan, Payment, PaymentReconciliation
from .services import PaymentPlanService
from venezuelan_pos.apps.events.models import EventConfiguration


class PaymentMethodTestCase(TestCase):
    """Test cases for PaymentMethod model."""
    
    def setUp(self):
        """Set up test data."""
        self.tenant = Tenant.objects.create(
            name="Test Tenant",
            slug="test-tenant"
        )
    
    def test_create_payment_method(self):
        """Test creating a payment method."""
        payment_method = PaymentMethod.objects.create(
            tenant=self.tenant,
            method_type=PaymentMethod.MethodType.CASH,
            name="Cash Payment",
            description="Cash payment method"
        )
        
        self.assertEqual(payment_method.name, "Cash Payment")
        self.assertEqual(payment_method.method_type, PaymentMethod.MethodType.CASH)
        self.assertTrue(payment_method.is_active)
        self.assertTrue(payment_method.allows_partial)
    
    def test_processing_fee_calculation(self):
        """Test processing fee calculation."""
        payment_method = PaymentMethod.objects.create(
            tenant=self.tenant,
            method_type=PaymentMethod.MethodType.CREDIT_CARD,
            name="Credit Card",
            processing_fee_percentage=Decimal('0.0300'),  # 3%
            processing_fee_fixed=Decimal('0.50')
        )
        
        amount = Decimal('100.00')
        fee = payment_method.calculate_processing_fee(amount)
        expected_fee = (amount * Decimal('0.0300')) + Decimal('0.50')
        
        self.assertEqual(fee, expected_fee)
    
    def test_validation_negative_fees(self):
        """Test validation of negative processing fees."""
        with self.assertRaises(ValidationError):
            payment_method = PaymentMethod(
                tenant=self.tenant,
                method_type=PaymentMethod.MethodType.CASH,
                name="Invalid Method",
                processing_fee_percentage=Decimal('-0.01')
            )
            payment_method.full_clean()


class PaymentPlanTestCase(TestCase):
    """Test cases for PaymentPlan model."""
    
    def setUp(self):
        """Set up test data."""
        self.tenant = Tenant.objects.create(
            name="Test Tenant",
            slug="test-tenant"
        )
        
        self.customer = Customer.objects.create(
            tenant=self.tenant,
            name="John",
            surname="Doe",
            email="john@example.com",
            phone="+584121234567"
        )
        
        self.venue = Venue.objects.create(
            tenant=self.tenant,
            name="Test Venue",
            address="Test Address"
        )
        
        self.event = Event.objects.create(
            tenant=self.tenant,
            name="Test Event",
            venue=self.venue,
            start_date=timezone.now() + timedelta(days=30),
            end_date=timezone.now() + timedelta(days=30, hours=3)
        )
        
        self.transaction = Transaction.objects.create(
            tenant=self.tenant,
            event=self.event,
            customer=self.customer,
            total_amount=Decimal('200.00')
        )
        
        self.event_config = EventConfiguration.objects.create(
            tenant=self.tenant,
            event=self.event,
            partial_payments_enabled=True,
            installment_plans_enabled=True,
            flexible_payments_enabled=True,
            max_installments=6,
            min_down_payment_percentage=Decimal('10.00'),
            payment_plan_expiry_days=10
        )
        
        self.payment_method = PaymentMethod.objects.create(
            tenant=self.tenant,
            method_type=PaymentMethod.MethodType.CASH,
            name="Caja",
            allows_partial=True
        )
    
    def test_create_installment_plan(self):
        """Test creating an installment payment plan."""
        expires_at = timezone.now() + timedelta(days=30)
        
        payment_plan = PaymentPlan.create_installment_plan(
            transaction=self.transaction,
            customer=self.customer,
            installment_count=4,
            expires_at=expires_at
        )
        
        self.assertEqual(payment_plan.plan_type, PaymentPlan.PlanType.INSTALLMENT)
        self.assertEqual(payment_plan.installment_count, 4)
        self.assertEqual(payment_plan.installment_amount, Decimal('50.00'))
        self.assertEqual(payment_plan.total_amount, Decimal('200.00'))
        self.assertEqual(payment_plan.remaining_balance, Decimal('200.00'))
    
    def test_create_flexible_plan(self):
        """Test creating a flexible payment plan."""
        expires_at = timezone.now() + timedelta(days=30)
        
        payment_plan = PaymentPlan.create_flexible_plan(
            transaction=self.transaction,
            customer=self.customer,
            expires_at=expires_at
        )
        
        self.assertEqual(payment_plan.plan_type, PaymentPlan.PlanType.FLEXIBLE)
        self.assertIsNone(payment_plan.installment_count)
        self.assertIsNone(payment_plan.installment_amount)
        self.assertEqual(payment_plan.total_amount, Decimal('200.00'))
    
    def test_add_payment_to_plan(self):
        """Test adding payment to a payment plan."""
        expires_at = timezone.now() + timedelta(days=30)
        
        payment_plan = PaymentPlan.create_flexible_plan(
            transaction=self.transaction,
            customer=self.customer,
            expires_at=expires_at
        )
        
        # Add partial payment
        payment_plan.add_payment(Decimal('50.00'))
        
        self.assertEqual(payment_plan.paid_amount, Decimal('50.00'))
        self.assertEqual(payment_plan.remaining_balance, Decimal('150.00'))
        self.assertEqual(payment_plan.status, PaymentPlan.Status.ACTIVE)
        
        # Complete payment
        payment_plan.add_payment(Decimal('150.00'))
        
        self.assertEqual(payment_plan.paid_amount, Decimal('200.00'))
        self.assertEqual(payment_plan.remaining_balance, Decimal('0.00'))
        self.assertEqual(payment_plan.status, PaymentPlan.Status.COMPLETED)
    
    def test_service_installment_plan_requires_configuration(self):
        """Service should respect event configuration flags."""
        self.event_config.partial_payments_enabled = False
        self.event_config.save()
        
        with self.assertRaises(ValidationError):
            PaymentPlanService.create_installment_plan(
                transaction_obj=self.transaction,
                installment_count=2
            )
    
    def test_service_installment_plan_records_initial_payment(self):
        """Ensure initial payment is recorded and remaining balance updates."""
        initial_payment = Decimal('100.00')  # First installment

        payment_plan = PaymentPlanService.create_installment_plan(
            transaction_obj=self.transaction,
            installment_count=2,
            initial_payment_amount=initial_payment,
            initial_payment_method=self.payment_method
        )
        
        self.transaction.refresh_from_db()
        payment_plan.refresh_from_db()
        self.assertEqual(payment_plan.paid_amount, initial_payment)
        self.assertEqual(payment_plan.remaining_balance, Decimal('180.00'))
        self.assertEqual(payment_plan.status, PaymentPlan.Status.ACTIVE)
        self.assertEqual(self.transaction.status, Transaction.Status.RESERVED)
        self.assertEqual(self.transaction.transaction_type, Transaction.TransactionType.PARTIAL_PAYMENT)
    
    def test_installment_plan_validation(self):
        """Test installment plan payment validation."""
        expires_at = timezone.now() + timedelta(days=30)
        
        payment_plan = PaymentPlan.create_installment_plan(
            transaction=self.transaction,
            customer=self.customer,
            installment_count=4,
            expires_at=expires_at
        )
        
        # Test correct installment amount
        can_pay, message = payment_plan.can_accept_payment(Decimal('50.00'))
        self.assertTrue(can_pay)
        
        # Test incorrect installment amount
        can_pay, message = payment_plan.can_accept_payment(Decimal('30.00'))
        self.assertFalse(can_pay)
        self.assertIn("Payment amount must be", message)


class PaymentTestCase(TestCase):
    """Test cases for Payment model."""
    
    def setUp(self):
        """Set up test data."""
        self.tenant = Tenant.objects.create(
            name="Test Tenant",
            slug="test-tenant"
        )
        
        self.customer = Customer.objects.create(
            tenant=self.tenant,
            name="John",
            surname="Doe",
            email="john@example.com",
            phone="+584121234567"
        )
        
        self.venue = Venue.objects.create(
            tenant=self.tenant,
            name="Test Venue",
            address="Test Address"
        )
        
        self.event = Event.objects.create(
            tenant=self.tenant,
            name="Test Event",
            venue=self.venue,
            start_date=timezone.now() + timedelta(days=30),
            end_date=timezone.now() + timedelta(days=30, hours=3)
        )
        
        self.transaction = Transaction.objects.create(
            tenant=self.tenant,
            event=self.event,
            customer=self.customer,
            total_amount=Decimal('100.00')
        )
        
        self.payment_method = PaymentMethod.objects.create(
            tenant=self.tenant,
            method_type=PaymentMethod.MethodType.CASH,
            name="Cash Payment"
        )
    
    def test_create_payment(self):
        """Test creating a payment."""
        payment = Payment.objects.create(
            tenant=self.tenant,
            transaction=self.transaction,
            payment_method=self.payment_method,
            amount=Decimal('100.00')
        )
        
        self.assertEqual(payment.amount, Decimal('100.00'))
        self.assertEqual(payment.status, Payment.Status.PENDING)
        self.assertEqual(payment.net_amount, Decimal('100.00'))  # No processing fee
    
    def test_payment_with_processing_fee(self):
        """Test payment with processing fee."""
        # Create payment method with fee
        card_method = PaymentMethod.objects.create(
            tenant=self.tenant,
            method_type=PaymentMethod.MethodType.CREDIT_CARD,
            name="Credit Card",
            processing_fee_percentage=Decimal('0.0300'),
            processing_fee_fixed=Decimal('0.50')
        )
        
        payment = Payment.objects.create(
            tenant=self.tenant,
            transaction=self.transaction,
            payment_method=card_method,
            amount=Decimal('100.00')
        )
        
        expected_fee = Decimal('3.50')  # 3% + $0.50
        expected_net = Decimal('96.50')
        
        self.assertEqual(payment.processing_fee, expected_fee)
        self.assertEqual(payment.net_amount, expected_net)
    
    def test_payment_completion(self):
        """Test payment completion."""
        payment = Payment.objects.create(
            tenant=self.tenant,
            transaction=self.transaction,
            payment_method=self.payment_method,
            amount=Decimal('100.00')
        )
        
        # Mark as completed
        payment.mark_completed(
            external_transaction_id="EXT123",
            processor_response={"status": "success"}
        )
        
        self.assertEqual(payment.status, Payment.Status.COMPLETED)
        self.assertEqual(payment.external_transaction_id, "EXT123")
        self.assertIsNotNone(payment.completed_at)
    
    def test_payment_failure(self):
        """Test payment failure."""
        payment = Payment.objects.create(
            tenant=self.tenant,
            transaction=self.transaction,
            payment_method=self.payment_method,
            amount=Decimal('100.00')
        )
        
        # Mark as failed
        payment.mark_failed(
            error_message="Card declined",
            processor_response={"error": "insufficient_funds"}
        )
        
        self.assertEqual(payment.status, Payment.Status.FAILED)
        self.assertEqual(payment.notes, "Card declined")


class PaymentReconciliationTestCase(TestCase):
    """Test cases for PaymentReconciliation model."""
    
    def setUp(self):
        """Set up test data."""
        self.tenant = Tenant.objects.create(
            name="Test Tenant",
            slug="test-tenant"
        )
        
        self.payment_method = PaymentMethod.objects.create(
            tenant=self.tenant,
            method_type=PaymentMethod.MethodType.CASH,
            name="Cash Payment"
        )
    
    def test_create_daily_reconciliation(self):
        """Test creating daily reconciliation."""
        reconciliation_date = timezone.now().date()
        
        reconciliation = PaymentReconciliation.create_daily_reconciliation(
            tenant=self.tenant,
            payment_method=self.payment_method,
            reconciliation_date=reconciliation_date
        )
        
        self.assertEqual(reconciliation.reconciliation_date, reconciliation_date)
        self.assertEqual(reconciliation.payment_method, self.payment_method)
        self.assertEqual(reconciliation.status, PaymentReconciliation.Status.PENDING)
    
    def test_reconciliation_discrepancy_calculation(self):
        """Test discrepancy calculation."""
        reconciliation_date = timezone.now().date()
        
        reconciliation = PaymentReconciliation.create_daily_reconciliation(
            tenant=self.tenant,
            payment_method=self.payment_method,
            reconciliation_date=reconciliation_date
        )
        
        # Set system and external totals
        reconciliation.system_total = Decimal('1000.00')
        reconciliation.external_total = Decimal('950.00')
        reconciliation.save()
        
        self.assertEqual(reconciliation.discrepancy_amount, Decimal('50.00'))
        self.assertTrue(reconciliation.has_discrepancy)
    
    def test_complete_reconciliation(self):
        """Test completing reconciliation."""
        reconciliation_date = timezone.now().date()
        
        reconciliation = PaymentReconciliation.create_daily_reconciliation(
            tenant=self.tenant,
            payment_method=self.payment_method,
            reconciliation_date=reconciliation_date
        )
        
        # Complete with matching totals (system total is 0.00 since no payments exist)
        reconciliation.complete_reconciliation(
            external_total=reconciliation.system_total,  # Match system total
            external_count=reconciliation.system_transaction_count,
            notes="Reconciliation completed successfully"
        )
        
        self.assertEqual(reconciliation.status, PaymentReconciliation.Status.COMPLETED)
        self.assertIsNotNone(reconciliation.completed_at)
        self.assertFalse(reconciliation.has_discrepancy)
