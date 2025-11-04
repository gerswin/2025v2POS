from decimal import Decimal
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta
from venezuelan_pos.apps.tenants.models import Tenant
from venezuelan_pos.apps.events.models import Event, Venue
from venezuelan_pos.apps.zones.models import Zone, Seat
from venezuelan_pos.apps.customers.models import Customer
from .models import (
    FiscalSeriesCounter,
    Transaction,
    TransactionItem,
    ReservedTicket,
    OfflineBlock
)


class SalesModelsTestCase(TestCase):
    """Test case for sales models."""
    
    def setUp(self):
        """Set up test data."""
        # Create tenant
        self.tenant = Tenant.objects.create(
            name="Test Tenant",
            slug="test-tenant",
            fiscal_series_prefix="TT"
        )
        
        # Create venue
        self.venue = Venue.objects.create(
            tenant=self.tenant,
            name="Test Venue",
            capacity=1000
        )
        
        # Create event
        self.event = Event.objects.create(
            tenant=self.tenant,
            name="Test Event",
            venue=self.venue,
            start_date=timezone.now() + timedelta(days=30),
            end_date=timezone.now() + timedelta(days=30, hours=3),
            event_type=Event.EventType.NUMBERED_SEAT
        )
        
        # Create zone
        self.zone = Zone.objects.create(
            tenant=self.tenant,
            event=self.event,
            name="VIP Zone",
            zone_type=Zone.ZoneType.NUMBERED,
            capacity=20,
            rows=4,
            seats_per_row=5,
            base_price=Decimal('100.00')
        )
        
        # Create customer
        self.customer = Customer.objects.create(
            tenant=self.tenant,
            name="John",
            surname="Doe",
            email="john.doe@example.com",
            phone="+584121234567"
        )
        
        # Get a seat for testing
        self.seat = Seat.objects.filter(zone=self.zone).first()
    
    def test_fiscal_series_counter_creation(self):
        """Test fiscal series counter creation and increment."""
        from django.db import transaction

        # Test getting next series
        with transaction.atomic():
            series1 = FiscalSeriesCounter.objects.get_next_series(self.tenant, self.event)
        self.assertEqual(series1, "TT00000001")

        with transaction.atomic():
            series2 = FiscalSeriesCounter.objects.get_next_series(self.tenant, self.event)
        self.assertEqual(series2, "TT00000002")

        # Check counter was created
        counter = FiscalSeriesCounter.objects.get(tenant=self.tenant, event=self.event)
        self.assertEqual(counter.current_series, 2)
    
    def test_transaction_creation(self):
        """Test transaction creation with items."""
        # Create transaction items data
        items_data = [{
            'zone': self.zone,
            'seat': self.seat,
            'item_type': TransactionItem.ItemType.NUMBERED_SEAT,
            'unit_price': Decimal('100.00'),
            'tax_rate': Decimal('0.1600')  # 16% tax
        }]
        
        # Create transaction
        transaction = Transaction.objects.create_transaction(
            tenant=self.tenant,
            event=self.event,
            customer=self.customer,
            items_data=items_data,
            transaction_type=Transaction.TransactionType.ONLINE
        )
        
        # Verify transaction
        self.assertEqual(transaction.status, Transaction.Status.PENDING)
        self.assertEqual(transaction.items.count(), 1)
        self.assertEqual(transaction.total_amount, Decimal('116.00'))  # 100 + 16% tax
        self.assertIsNone(transaction.fiscal_series)
        
        # Verify transaction item
        item = transaction.items.first()
        self.assertEqual(item.zone, self.zone)
        self.assertEqual(item.seat, self.seat)
        self.assertEqual(item.unit_price, Decimal('100.00'))
        self.assertEqual(item.tax_amount, Decimal('16.00'))
        self.assertEqual(item.total_price, Decimal('116.00'))
    
    def test_transaction_completion(self):
        """Test transaction completion with fiscal series generation."""
        # Create transaction
        items_data = [{
            'zone': self.zone,
            'seat': self.seat,
            'item_type': TransactionItem.ItemType.NUMBERED_SEAT,
            'unit_price': Decimal('100.00'),
            'tax_rate': Decimal('0.1600')
        }]
        
        transaction = Transaction.objects.create_transaction(
            tenant=self.tenant,
            event=self.event,
            customer=self.customer,
            items_data=items_data
        )
        
        # Complete transaction
        completed_transaction = transaction.complete()
        
        # Verify completion
        self.assertEqual(completed_transaction.status, Transaction.Status.COMPLETED)
        self.assertEqual(completed_transaction.fiscal_series, "TT00000001")
        self.assertIsNotNone(completed_transaction.completed_at)
        
        # Verify seat status updated
        self.seat.refresh_from_db()
        self.assertEqual(self.seat.status, Seat.Status.SOLD)
    
    def test_reserved_ticket_creation(self):
        """Test reserved ticket creation and expiration."""
        # Create transaction
        transaction = Transaction.objects.create(
            tenant=self.tenant,
            event=self.event,
            customer=self.customer,
            status=Transaction.Status.RESERVED,
            total_amount=Decimal('100.00')
        )
        
        # Create reservation
        reservation = ReservedTicket.objects.create(
            tenant=self.tenant,
            transaction=transaction,
            zone=self.zone,
            seat=self.seat,
            reserved_until=timezone.now() + timedelta(hours=2)
        )
        
        # Verify reservation
        self.assertTrue(reservation.is_active)
        self.assertFalse(reservation.is_expired)
        
        # Test expiration
        reservation.reserved_until = timezone.now() - timedelta(minutes=1)
        reservation.save()
        self.assertTrue(reservation.is_expired)
        
        # Test expire method
        reservation.expire()
        self.assertEqual(reservation.status, ReservedTicket.Status.EXPIRED)
        
        # Verify seat was released
        self.seat.refresh_from_db()
        self.assertEqual(self.seat.status, Seat.Status.AVAILABLE)
    
    def test_offline_block_creation(self):
        """Test offline block creation and series generation."""
        # Create offline block
        block = OfflineBlock.create_block(
            tenant=self.tenant,
            assigned_to="Terminal-001"
        )
        
        # Verify block
        self.assertEqual(block.start_series, 1)
        self.assertEqual(block.end_series, 50)
        self.assertEqual(block.current_series, 0)
        self.assertTrue(block.is_active)
        self.assertEqual(block.remaining_series, 50)
        
        # Test getting next series
        series1 = block.get_next_series()
        self.assertEqual(series1, "TT00000001")
        self.assertEqual(block.remaining_series, 49)
        
        series2 = block.get_next_series()
        self.assertEqual(series2, "TT00000002")
        self.assertEqual(block.remaining_series, 48)
    
    def test_transaction_item_validation(self):
        """Test transaction item validation rules."""
        # Create transaction
        transaction = Transaction.objects.create(
            tenant=self.tenant,
            event=self.event,
            customer=self.customer,
            total_amount=Decimal('100.00')
        )
        
        # Test numbered seat validation - should require seat
        with self.assertRaises(ValidationError):
            item = TransactionItem(
                tenant=self.tenant,
                transaction=transaction,
                zone=self.zone,  # Numbered zone
                seat=None,  # No seat provided
                item_type=TransactionItem.ItemType.NUMBERED_SEAT,
                unit_price=Decimal('100.00')
            )
            item.full_clean()
        
        # Test general admission validation - should not have seat
        general_zone = Zone.objects.create(
            tenant=self.tenant,
            event=self.event,
            name="General Zone",
            zone_type=Zone.ZoneType.GENERAL,
            capacity=100,
            base_price=Decimal('50.00')
        )
        
        with self.assertRaises(ValidationError):
            item = TransactionItem(
                tenant=self.tenant,
                transaction=transaction,
                zone=general_zone,  # General zone
                seat=self.seat,  # Seat provided
                item_type=TransactionItem.ItemType.GENERAL_ADMISSION,
                unit_price=Decimal('50.00')
            )
            item.full_clean()
    
    def test_fiscal_series_uniqueness(self):
        """Test fiscal series uniqueness constraint."""
        from django.db import IntegrityError
        
        # Create first transaction and complete it
        items_data = [{
            'zone': self.zone,
            'seat': self.seat,
            'item_type': TransactionItem.ItemType.NUMBERED_SEAT,
            'unit_price': Decimal('100.00')
        }]
        
        transaction1 = Transaction.objects.create_transaction(
            tenant=self.tenant,
            event=self.event,
            customer=self.customer,
            items_data=items_data
        )
        transaction1.complete()
        
        # Try to create another transaction with same fiscal series
        # This should raise IntegrityError due to database constraint
        with self.assertRaises(IntegrityError):
            Transaction.objects.create(
                tenant=self.tenant,
                event=self.event,
                customer=self.customer,
                fiscal_series=transaction1.fiscal_series,  # Same series
                total_amount=Decimal('100.00')
            )
    
    def test_transaction_totals_calculation(self):
        """Test transaction totals calculation."""
        # Create transaction
        transaction = Transaction.objects.create(
            tenant=self.tenant,
            event=self.event,
            customer=self.customer,
            total_amount=Decimal('0.00')
        )
        
        # Create multiple items
        item1 = TransactionItem.objects.create(
            tenant=self.tenant,
            transaction=transaction,
            zone=self.zone,
            seat=self.seat,
            item_type=TransactionItem.ItemType.NUMBERED_SEAT,
            unit_price=Decimal('100.00'),
            tax_rate=Decimal('0.1600')
        )
        
        # Get another seat
        seat2 = Seat.objects.filter(zone=self.zone).exclude(pk=self.seat.pk).first()
        item2 = TransactionItem.objects.create(
            tenant=self.tenant,
            transaction=transaction,
            zone=self.zone,
            seat=seat2,
            item_type=TransactionItem.ItemType.NUMBERED_SEAT,
            unit_price=Decimal('150.00'),
            tax_rate=Decimal('0.1600')
        )
        
        # Calculate totals
        totals = transaction.calculate_totals()
        
        # Verify calculations
        expected_subtotal = Decimal('250.00')  # 100 + 150
        expected_tax = Decimal('40.00')  # 16 + 24
        expected_total = Decimal('290.00')  # 250 + 40
        
        self.assertEqual(totals['subtotal'], expected_subtotal)
        self.assertEqual(totals['tax'], expected_tax)
        self.assertEqual(totals['total'], expected_total)
        
        # Verify transaction was updated
        self.assertEqual(transaction.subtotal_amount, expected_subtotal)
        self.assertEqual(transaction.tax_amount, expected_tax)
        self.assertEqual(transaction.total_amount, expected_total)