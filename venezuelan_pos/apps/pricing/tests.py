"""
Tests for pricing models, services, and API endpoints.
"""

from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from django.core.exceptions import ValidationError
from rest_framework.test import APITestCase
from rest_framework import status
from datetime import timedelta

from .models import PriceStage, RowPricing, PriceHistory
from .services import PricingCalculationService
from venezuelan_pos.apps.tenants.models import Tenant, User
from venezuelan_pos.apps.events.models import Event, Venue
from venezuelan_pos.apps.zones.models import Zone, Seat


class PriceStageModelTest(TestCase):
    """Test PriceStage model functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.tenant = Tenant.objects.create(
            name="Test Tenant",
            slug="test-tenant",
            is_active=True
        )
        
        self.venue = Venue.objects.create(
            tenant=self.tenant,
            name="Test Venue",
            capacity=1000
        )
        
        self.event = Event.objects.create(
            tenant=self.tenant,
            name="Test Event",
            venue=self.venue,
            start_date=timezone.now() + timedelta(days=30),
            end_date=timezone.now() + timedelta(days=30, hours=4)
        )
    
    def test_price_stage_creation(self):
        """Test creating a price stage."""
        stage = PriceStage.objects.create(
            tenant=self.tenant,
            event=self.event,
            name="Early Bird",
            start_date=timezone.now(),
            end_date=timezone.now() + timedelta(days=7),
            modifier_type=PriceStage.ModifierType.PERCENTAGE,
            modifier_value=Decimal('10.00')
        )
        
        self.assertEqual(stage.name, "Early Bird")
        self.assertEqual(stage.modifier_value, Decimal('10.00'))
        self.assertTrue(stage.is_active)
    
    def test_price_stage_validation(self):
        """Test price stage validation."""
        # Test invalid date range
        with self.assertRaises(ValidationError):
            stage = PriceStage(
                tenant=self.tenant,
                event=self.event,
                name="Invalid Stage",
                start_date=timezone.now() + timedelta(days=7),
                end_date=timezone.now(),  # End before start
                modifier_type=PriceStage.ModifierType.PERCENTAGE,
                modifier_value=Decimal('10.00')
            )
            stage.clean()
    
    def test_overlapping_stages_validation(self):
        """Test validation of overlapping price stages."""
        # Create first stage
        PriceStage.objects.create(
            tenant=self.tenant,
            event=self.event,
            name="Stage 1",
            start_date=timezone.now(),
            end_date=timezone.now() + timedelta(days=7),
            modifier_type=PriceStage.ModifierType.PERCENTAGE,
            modifier_value=Decimal('10.00')
        )
        
        # Try to create overlapping stage
        with self.assertRaises(ValidationError):
            stage = PriceStage(
                tenant=self.tenant,
                event=self.event,
                name="Stage 2",
                start_date=timezone.now() + timedelta(days=3),
                end_date=timezone.now() + timedelta(days=10),
                modifier_type=PriceStage.ModifierType.PERCENTAGE,
                modifier_value=Decimal('15.00')
            )
            stage.clean()
    
    def test_price_calculation_methods(self):
        """Test price calculation methods."""
        stage = PriceStage.objects.create(
            tenant=self.tenant,
            event=self.event,
            name="Test Stage",
            start_date=timezone.now(),
            end_date=timezone.now() + timedelta(days=7),
            modifier_type=PriceStage.ModifierType.PERCENTAGE,
            modifier_value=Decimal('20.00')
        )
        
        base_price = Decimal('100.00')
        markup_amount = stage.calculate_modifier_amount(base_price)
        final_price = stage.calculate_final_price(base_price)
        
        self.assertEqual(markup_amount, Decimal('20.00'))
        self.assertEqual(final_price, Decimal('120.00'))


class RowPricingModelTest(TestCase):
    """Test RowPricing model functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.tenant = Tenant.objects.create(
            name="Test Tenant",
            slug="test-tenant",
            is_active=True
        )
        
        self.venue = Venue.objects.create(
            tenant=self.tenant,
            name="Test Venue",
            capacity=1000
        )
        
        self.event = Event.objects.create(
            tenant=self.tenant,
            name="Test Event",
            venue=self.venue,
            start_date=timezone.now() + timedelta(days=30),
            end_date=timezone.now() + timedelta(days=30, hours=4)
        )
        
        self.zone = Zone.objects.create(
            tenant=self.tenant,
            event=self.event,
            name="VIP Zone",
            zone_type=Zone.ZoneType.NUMBERED,
            capacity=100,
            rows=10,
            seats_per_row=10,
            base_price=Decimal('50.00')
        )
    
    def test_row_pricing_creation(self):
        """Test creating row pricing."""
        row_pricing = RowPricing.objects.create(
            tenant=self.tenant,
            zone=self.zone,
            row_number=1,
            percentage_markup=Decimal('25.00'),
            name="Front Row Premium"
        )
        
        self.assertEqual(row_pricing.row_number, 1)
        self.assertEqual(row_pricing.percentage_markup, Decimal('25.00'))
        self.assertEqual(row_pricing.name, "Front Row Premium")
    
    def test_row_pricing_validation(self):
        """Test row pricing validation."""
        # Test invalid zone type
        general_zone = Zone.objects.create(
            tenant=self.tenant,
            event=self.event,
            name="General Zone",
            zone_type=Zone.ZoneType.GENERAL,
            capacity=500,
            base_price=Decimal('30.00')
        )
        
        with self.assertRaises(ValidationError):
            row_pricing = RowPricing(
                tenant=self.tenant,
                zone=general_zone,
                row_number=1,
                percentage_markup=Decimal('10.00')
            )
            row_pricing.clean()
    
    def test_row_pricing_calculation(self):
        """Test row pricing calculation methods."""
        row_pricing = RowPricing.objects.create(
            tenant=self.tenant,
            zone=self.zone,
            row_number=1,
            percentage_markup=Decimal('30.00')
        )
        
        base_price = Decimal('50.00')
        markup_amount = row_pricing.calculate_markup_amount(base_price)
        final_price = row_pricing.calculate_final_price(base_price)
        
        self.assertEqual(markup_amount, Decimal('15.00'))
        self.assertEqual(final_price, Decimal('65.00'))


class PricingCalculationServiceTest(TestCase):
    """Test PricingCalculationService functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.tenant = Tenant.objects.create(
            name="Test Tenant",
            slug="test-tenant",
            is_active=True
        )
        
        self.venue = Venue.objects.create(
            tenant=self.tenant,
            name="Test Venue",
            capacity=1000
        )
        
        self.event = Event.objects.create(
            tenant=self.tenant,
            name="Test Event",
            venue=self.venue,
            start_date=timezone.now() + timedelta(days=30),
            end_date=timezone.now() + timedelta(days=30, hours=4)
        )
        
        self.zone = Zone.objects.create(
            tenant=self.tenant,
            event=self.event,
            name="VIP Zone",
            zone_type=Zone.ZoneType.NUMBERED,
            capacity=20,
            rows=2,
            seats_per_row=10,
            base_price=Decimal('100.00')
        )
        
        # Create price stage
        self.price_stage = PriceStage.objects.create(
            tenant=self.tenant,
            event=self.event,
            name="Early Bird",
            start_date=timezone.now() - timedelta(days=1),
            end_date=timezone.now() + timedelta(days=7),
            modifier_type=PriceStage.ModifierType.PERCENTAGE,
            modifier_value=Decimal('15.00')
        )
        
        # Create row pricing
        self.row_pricing = RowPricing.objects.create(
            tenant=self.tenant,
            zone=self.zone,
            row_number=1,
            percentage_markup=Decimal('20.00'),
            name="Front Row"
        )
        
        self.service = PricingCalculationService()
    
    def test_get_current_price_stage(self):
        """Test getting current price stage."""
        current_stage = self.service.get_current_price_stage(self.event)
        self.assertEqual(current_stage, self.price_stage)
    
    def test_get_row_pricing(self):
        """Test getting row pricing."""
        row_pricing = self.service.get_row_pricing(self.zone, 1)
        self.assertEqual(row_pricing, self.row_pricing)
        
        # Test non-existent row
        no_pricing = self.service.get_row_pricing(self.zone, 2)
        self.assertIsNone(no_pricing)
    
    def test_calculate_zone_price(self):
        """Test zone price calculation."""
        final_price, details = self.service.calculate_zone_price(
            self.zone, create_history=False
        )
        
        # Base price: 100.00
        # Stage markup (15%): 15.00
        # Expected final: 115.00
        self.assertEqual(final_price, Decimal('115.00'))
        self.assertEqual(details['base_price'], Decimal('100.00'))
        self.assertEqual(details['total_markup_amount'], Decimal('15.00'))
    
    def test_calculate_zone_price_with_row(self):
        """Test zone price calculation with row pricing."""
        final_price, details = self.service.calculate_zone_price(
            self.zone, row_number=1, create_history=False
        )
        
        # Base price: 100.00
        # Stage markup (15%): 15.00 -> 115.00
        # Row markup (20% of 115.00): 23.00
        # Expected final: 138.00
        self.assertEqual(final_price, Decimal('138.00'))
        self.assertEqual(details['total_markup_amount'], Decimal('38.00'))
    
    def test_calculate_seat_price(self):
        """Test seat price calculation."""
        # Get a seat from the zone
        seat = self.zone.seats.first()
        
        final_price, details = self.service.calculate_seat_price(
            seat, create_history=False
        )
        
        if seat.row_number == 1:
            # Front row with row pricing
            # Base: 100.00 -> Stage: 115.00 -> Row: 138.00
            self.assertEqual(final_price, Decimal('138.00'))
        else:
            # Back row without row pricing
            # Base: 100.00 -> Stage: 115.00
            self.assertEqual(final_price, Decimal('115.00'))


class PricingAPITest(APITestCase):
    """Test pricing API endpoints."""
    
    def setUp(self):
        """Set up test data."""
        self.tenant = Tenant.objects.create(
            name="Test Tenant",
            slug="test-tenant",
            is_active=True
        )
        
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            tenant=self.tenant
        )
        
        self.venue = Venue.objects.create(
            tenant=self.tenant,
            name="Test Venue",
            capacity=1000
        )
        
        self.event = Event.objects.create(
            tenant=self.tenant,
            name="Test Event",
            venue=self.venue,
            start_date=timezone.now() + timedelta(days=30),
            end_date=timezone.now() + timedelta(days=30, hours=4)
        )
        
        self.zone = Zone.objects.create(
            tenant=self.tenant,
            event=self.event,
            name="Test Zone",
            zone_type=Zone.ZoneType.NUMBERED,
            capacity=20,
            rows=2,
            seats_per_row=10,
            base_price=Decimal('50.00')
        )
        
        self.client.force_authenticate(user=self.user)
    
    def test_create_price_stage(self):
        """Test creating price stage via API."""
        data = {
            'event': str(self.event.id),
            'name': 'Early Bird',
            'start_date': timezone.now().isoformat(),
            'end_date': (timezone.now() + timedelta(days=7)).isoformat(),
            'modifier_type': 'percentage',
            'modifier_value': '15.00',
            'stage_order': 1
        }
        
        response = self.client.post('/api/v1/pricing/stages/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'Early Bird')
    
    def test_create_row_pricing(self):
        """Test creating row pricing via API."""
        data = {
            'zone': str(self.zone.id),
            'row_number': 1,
            'percentage_markup': '25.00',
            'name': 'Front Row Premium'
        }
        
        response = self.client.post('/api/v1/pricing/row-pricing/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'Front Row Premium')
    
    def test_price_calculation(self):
        """Test price calculation API."""
        # Create price stage and row pricing
        PriceStage.objects.create(
            tenant=self.tenant,
            event=self.event,
            name="Test Stage",
            start_date=timezone.now() - timedelta(hours=1),
            end_date=timezone.now() + timedelta(days=7),
            modifier_type=PriceStage.ModifierType.PERCENTAGE,
            modifier_value=Decimal('10.00')
        )
        
        RowPricing.objects.create(
            tenant=self.tenant,
            zone=self.zone,
            row_number=1,
            percentage_markup=Decimal('20.00')
        )
        
        data = {
            'event_id': str(self.event.id),
            'zone_id': str(self.zone.id),
            'row_number': 1
        }
        
        response = self.client.post('/api/v1/pricing/calculations/calculate/', data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Base: 50.00 -> Stage (10%): 55.00 -> Row (20%): 66.00
        self.assertEqual(Decimal(response.data['final_price']), Decimal('66.00'))
    
    def test_bulk_price_calculation(self):
        """Test bulk price calculation API."""
        data = {
            'calculations': [
                {
                    'event_id': str(self.event.id),
                    'zone_id': str(self.zone.id)
                }
            ]
        }
        
        response = self.client.post('/api/v1/pricing/calculations/bulk_calculate/', data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_price_breakdown(self):
        """Test price breakdown API."""
        data = {
            'event_id': str(self.event.id),
            'zone_id': str(self.zone.id)
        }
        
        response = self.client.post('/api/v1/pricing/calculations/breakdown/', data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('base_price', response.data)
        self.assertIn('final_price', response.data)