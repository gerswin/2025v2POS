from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta

from venezuelan_pos.apps.tenants.models import Tenant, User
from .models import Venue, Event, EventConfiguration


class VenueModelTest(TestCase):
    """Test cases for Venue model."""
    
    def setUp(self):
        """Set up test data."""
        self.tenant = Tenant.objects.create(
            name="Test Tenant",
            slug="test-tenant"
        )
    
    def test_venue_creation(self):
        """Test basic venue creation."""
        venue = Venue.objects.create(
            tenant=self.tenant,
            name="Test Venue",
            city="Caracas",
            state="Distrito Capital",
            capacity=1000,
            venue_type="physical"
        )
        
        self.assertEqual(venue.name, "Test Venue")
        self.assertEqual(venue.city, "Caracas")
        self.assertEqual(venue.capacity, 1000)
        self.assertEqual(venue.venue_type, "physical")
        self.assertTrue(venue.is_active)
    
    def test_venue_str_representation(self):
        """Test venue string representation."""
        venue = Venue.objects.create(
            tenant=self.tenant,
            name="Test Venue",
            city="Caracas"
        )
        
        self.assertEqual(str(venue), "Test Venue (Caracas)")
    
    def test_venue_name_validation(self):
        """Test venue name cannot be empty."""
        venue = Venue(
            tenant=self.tenant,
            name="   ",  # Empty name with spaces
            city="Caracas"
        )
        
        with self.assertRaises(ValidationError):
            venue.full_clean()


class EventModelTest(TestCase):
    """Test cases for Event model."""
    
    def setUp(self):
        """Set up test data."""
        self.tenant = Tenant.objects.create(
            name="Test Tenant",
            slug="test-tenant"
        )
        
        self.venue = Venue.objects.create(
            tenant=self.tenant,
            name="Test Venue",
            city="Caracas",
            capacity=1000
        )
        
        self.start_date = timezone.now() + timedelta(days=30)
        self.end_date = self.start_date + timedelta(hours=3)
    
    def test_event_creation(self):
        """Test basic event creation."""
        event = Event.objects.create(
            tenant=self.tenant,
            name="Test Event",
            venue=self.venue,
            start_date=self.start_date,
            end_date=self.end_date,
            event_type=Event.EventType.GENERAL_ASSIGNMENT
        )
        
        self.assertEqual(event.name, "Test Event")
        self.assertEqual(event.venue, self.venue)
        self.assertEqual(event.event_type, Event.EventType.GENERAL_ASSIGNMENT)
        self.assertEqual(event.status, Event.Status.DRAFT)
        self.assertEqual(event.base_currency, "USD")
        self.assertEqual(event.currency_conversion_rate, Decimal('1.0000'))
    
    def test_event_str_representation(self):
        """Test event string representation."""
        event = Event.objects.create(
            tenant=self.tenant,
            name="Test Event",
            venue=self.venue,
            start_date=self.start_date,
            end_date=self.end_date
        )
        
        expected = f"Test Event - {self.start_date.strftime('%Y-%m-%d')}"
        self.assertEqual(str(event), expected)
    
    def test_event_date_validation(self):
        """Test event date validation."""
        # End date before start date should fail
        event = Event(
            tenant=self.tenant,
            name="Test Event",
            venue=self.venue,
            start_date=self.end_date,  # Swapped dates
            end_date=self.start_date
        )
        
        with self.assertRaises(ValidationError):
            event.full_clean()
    
    def test_sales_date_validation(self):
        """Test sales date validation."""
        # Sales end after event start should fail
        sales_end = self.start_date + timedelta(hours=1)
        
        event = Event(
            tenant=self.tenant,
            name="Test Event",
            venue=self.venue,
            start_date=self.start_date,
            end_date=self.end_date,
            sales_start_date=self.start_date - timedelta(days=10),
            sales_end_date=sales_end  # After event start
        )
        
        with self.assertRaises(ValidationError):
            event.full_clean()
    
    def test_currency_conversion_rate_validation(self):
        """Test currency conversion rate must be positive."""
        event = Event(
            tenant=self.tenant,
            name="Test Event",
            venue=self.venue,
            start_date=self.start_date,
            end_date=self.end_date,
            currency_conversion_rate=Decimal('-1.0')  # Negative rate
        )
        
        with self.assertRaises(ValidationError):
            event.full_clean()
    
    def test_is_sales_active_property(self):
        """Test is_sales_active property."""
        # Create active event with sales dates
        now = timezone.now()
        event = Event.objects.create(
            tenant=self.tenant,
            name="Test Event",
            venue=self.venue,
            start_date=now + timedelta(days=30),
            end_date=now + timedelta(days=30, hours=3),
            sales_start_date=now - timedelta(days=1),
            sales_end_date=now + timedelta(days=29),
            status=Event.Status.ACTIVE
        )
        
        self.assertTrue(event.is_sales_active)
        
        # Test inactive status
        event.status = Event.Status.DRAFT
        event.save()
        self.assertFalse(event.is_sales_active)
    
    def test_event_time_properties(self):
        """Test event timing properties."""
        now = timezone.now()
        
        # Future event
        future_event = Event.objects.create(
            tenant=self.tenant,
            name="Future Event",
            venue=self.venue,
            start_date=now + timedelta(days=1),
            end_date=now + timedelta(days=1, hours=3)
        )
        
        self.assertTrue(future_event.is_upcoming)
        self.assertFalse(future_event.is_ongoing)
        self.assertFalse(future_event.is_past)
        
        # Past event
        past_event = Event.objects.create(
            tenant=self.tenant,
            name="Past Event",
            venue=self.venue,
            start_date=now - timedelta(days=1, hours=3),
            end_date=now - timedelta(days=1)
        )
        
        self.assertFalse(past_event.is_upcoming)
        self.assertFalse(past_event.is_ongoing)
        self.assertTrue(past_event.is_past)


class EventConfigurationModelTest(TestCase):
    """Test cases for EventConfiguration model."""
    
    def setUp(self):
        """Set up test data."""
        self.tenant = Tenant.objects.create(
            name="Test Tenant",
            slug="test-tenant"
        )
        
        self.venue = Venue.objects.create(
            tenant=self.tenant,
            name="Test Venue",
            city="Caracas"
        )
        
        self.event = Event.objects.create(
            tenant=self.tenant,
            name="Test Event",
            venue=self.venue,
            start_date=timezone.now() + timedelta(days=30),
            end_date=timezone.now() + timedelta(days=30, hours=3)
        )
    
    def test_configuration_creation(self):
        """Test basic configuration creation."""
        config = EventConfiguration.objects.create(
            tenant=self.tenant,
            event=self.event,
            partial_payments_enabled=True,
            max_installments=3,
            min_down_payment_percentage=Decimal('25.00')
        )
        
        self.assertEqual(config.event, self.event)
        self.assertTrue(config.partial_payments_enabled)
        self.assertEqual(config.max_installments, 3)
        self.assertEqual(config.min_down_payment_percentage, Decimal('25.00'))
        self.assertTrue(config.notifications_enabled)
        self.assertTrue(config.digital_tickets_enabled)
    
    def test_configuration_str_representation(self):
        """Test configuration string representation."""
        config = EventConfiguration.objects.create(
            tenant=self.tenant,
            event=self.event
        )
        
        self.assertEqual(str(config), f"Configuration for {self.event.name}")
    
    def test_down_payment_percentage_validation(self):
        """Test down payment percentage validation."""
        # Test negative percentage
        config = EventConfiguration(
            tenant=self.tenant,
            event=self.event,
            min_down_payment_percentage=Decimal('-10.00')
        )
        
        with self.assertRaises(ValidationError):
            config.full_clean()
        
        # Test percentage over 100
        config.min_down_payment_percentage = Decimal('150.00')
        
        with self.assertRaises(ValidationError):
            config.full_clean()
    
    def test_max_installments_validation(self):
        """Test max installments validation."""
        config = EventConfiguration(
            tenant=self.tenant,
            event=self.event,
            max_installments=0  # Should be at least 1
        )
        
        with self.assertRaises(ValidationError):
            config.full_clean()
    
    def test_payment_plan_expiry_validation(self):
        """Test payment plan expiry validation."""
        config = EventConfiguration(
            tenant=self.tenant,
            event=self.event,
            payment_plan_expiry_days=0  # Should be at least 1
        )
        
        with self.assertRaises(ValidationError):
            config.full_clean()