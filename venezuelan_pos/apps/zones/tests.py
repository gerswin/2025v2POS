from decimal import Decimal
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from venezuelan_pos.apps.tenants.models import Tenant, User
from venezuelan_pos.apps.events.models import Event, Venue
from .models import Zone, Seat, Table, TableSeat


class ZoneModelTest(TestCase):
    """Test Zone model functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.tenant = Tenant.objects.create(
            name="Test Tenant",
            slug="test-tenant",
            configuration={}
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
            start_date="2025-12-01T20:00:00Z",
            end_date="2025-12-01T23:00:00Z",
            event_type=Event.EventType.NUMBERED_SEAT
        )
    
    def test_general_zone_creation(self):
        """Test creating a general zone."""
        zone = Zone.objects.create(
            tenant=self.tenant,
            event=self.event,
            name="General Admission",
            zone_type=Zone.ZoneType.GENERAL,
            capacity=500,
            base_price=Decimal('50.00')
        )
        
        self.assertEqual(zone.zone_type, Zone.ZoneType.GENERAL)
        self.assertEqual(zone.capacity, 500)
        self.assertEqual(zone.available_capacity, 500)
        self.assertEqual(zone.seats.count(), 0)  # No seats for general zones
    
    def test_numbered_zone_creation(self):
        """Test creating a numbered zone with automatic seat generation."""
        zone = Zone.objects.create(
            tenant=self.tenant,
            event=self.event,
            name="VIP Section",
            zone_type=Zone.ZoneType.NUMBERED,
            capacity=100,
            rows=10,
            seats_per_row=10,
            base_price=Decimal('100.00')
        )
        
        self.assertEqual(zone.zone_type, Zone.ZoneType.NUMBERED)
        self.assertEqual(zone.capacity, 100)
        
        # Seats should be generated automatically
        self.assertEqual(zone.seats.count(), 100)
        
        # Check first and last seats
        first_seat = zone.seats.order_by('row_number', 'seat_number').first()
        self.assertEqual(first_seat.row_number, 1)
        self.assertEqual(first_seat.seat_number, 1)
        
        last_seat = zone.seats.order_by('row_number', 'seat_number').last()
        self.assertEqual(last_seat.row_number, 10)
        self.assertEqual(last_seat.seat_number, 10)
    
    def test_numbered_zone_capacity_validation(self):
        """Test that numbered zone capacity must match rows × seats_per_row."""
        with self.assertRaises(ValidationError):
            zone = Zone(
                tenant=self.tenant,
                event=self.event,
                name="Invalid Zone",
                zone_type=Zone.ZoneType.NUMBERED,
                capacity=50,  # Should be 100 (10 × 10)
                rows=10,
                seats_per_row=10,
                base_price=Decimal('100.00')
            )
            zone.clean()
    
    def test_zone_string_representation(self):
        """Test zone string representation."""
        zone = Zone.objects.create(
            tenant=self.tenant,
            event=self.event,
            name="Test Zone",
            zone_type=Zone.ZoneType.GENERAL,
            capacity=100,
            base_price=Decimal('50.00')
        )
        
        expected = f"{self.event.name} - Test Zone"
        self.assertEqual(str(zone), expected)


class SeatModelTest(TestCase):
    """Test Seat model functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.tenant = Tenant.objects.create(
            name="Test Tenant",
            slug="test-tenant",
            configuration={}
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
            start_date="2025-12-01T20:00:00Z",
            end_date="2025-12-01T23:00:00Z",
            event_type=Event.EventType.NUMBERED_SEAT
        )
        
        self.zone = Zone.objects.create(
            tenant=self.tenant,
            event=self.event,
            name="Test Zone",
            zone_type=Zone.ZoneType.NUMBERED,
            capacity=20,
            rows=4,
            seats_per_row=5,
            base_price=Decimal('100.00')
        )
    
    def test_seat_price_calculation(self):
        """Test seat price calculation with modifier."""
        seat = self.zone.seats.first()
        
        # Test base price (no modifier)
        self.assertEqual(seat.calculated_price, Decimal('100.00'))
        
        # Test with 10% increase
        seat.price_modifier = Decimal('10.00')
        seat.save()
        self.assertEqual(seat.calculated_price, Decimal('110.00'))
        
        # Test with 25% decrease
        seat.price_modifier = Decimal('-25.00')
        seat.save()
        self.assertEqual(seat.calculated_price, Decimal('75.00'))
    
    def test_seat_availability(self):
        """Test seat availability checking."""
        seat = self.zone.seats.first()
        
        # Initially available
        self.assertTrue(seat.is_available)
        
        # Mark as sold
        seat.status = Seat.Status.SOLD
        seat.save()
        self.assertFalse(seat.is_available)
        
        # Mark as reserved
        seat.status = Seat.Status.RESERVED
        seat.save()
        self.assertFalse(seat.is_available)
    
    def test_seat_label(self):
        """Test seat label generation."""
        seat = self.zone.seats.filter(row_number=2, seat_number=3).first()
        self.assertEqual(seat.seat_label, "Row 2, Seat 3")


class TableModelTest(TestCase):
    """Test Table model functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.tenant = Tenant.objects.create(
            name="Test Tenant",
            slug="test-tenant",
            configuration={}
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
            start_date="2025-12-01T20:00:00Z",
            end_date="2025-12-01T23:00:00Z",
            event_type=Event.EventType.NUMBERED_SEAT
        )
        
        self.zone = Zone.objects.create(
            tenant=self.tenant,
            event=self.event,
            name="Test Zone",
            zone_type=Zone.ZoneType.NUMBERED,
            capacity=20,
            rows=4,
            seats_per_row=5,
            base_price=Decimal('100.00')
        )
        
        self.table = Table.objects.create(
            tenant=self.tenant,
            zone=self.zone,
            name="Table 1",
            sale_mode=Table.SaleMode.COMPLETE_ONLY
        )
    
    def test_table_seat_assignment(self):
        """Test assigning seats to a table."""
        # Get first 4 seats
        seats = list(self.zone.seats.all()[:4])
        
        # Assign seats to table
        for i, seat in enumerate(seats):
            TableSeat.objects.create(
                tenant=self.tenant,
                table=self.table,
                seat=seat,
                position=i
            )
        
        self.assertEqual(self.table.seat_count, 4)
        self.assertEqual(self.table.available_seats.count(), 4)
        self.assertEqual(self.table.sold_seats.count(), 0)
        self.assertTrue(self.table.is_available)
        self.assertFalse(self.table.is_sold_out)
    
    def test_table_availability_complete_only(self):
        """Test table availability for complete-only sale mode."""
        seats = list(self.zone.seats.all()[:4])
        
        # Assign seats to table
        for i, seat in enumerate(seats):
            TableSeat.objects.create(
                tenant=self.tenant,
                table=self.table,
                seat=seat,
                position=i
            )
        
        # All seats available - table should be available
        self.assertTrue(self.table.is_available)
        
        # Mark one seat as sold
        seats[0].status = Seat.Status.SOLD
        seats[0].save()
        
        # Table should not be available for complete-only mode
        self.assertFalse(self.table.is_available)
    
    def test_table_availability_individual_allowed(self):
        """Test table availability for individual-allowed sale mode."""
        self.table.sale_mode = Table.SaleMode.INDIVIDUAL_ALLOWED
        self.table.save()
        
        seats = list(self.zone.seats.all()[:4])
        
        # Assign seats to table
        for i, seat in enumerate(seats):
            TableSeat.objects.create(
                tenant=self.tenant,
                table=self.table,
                seat=seat,
                position=i
            )
        
        # All seats available - table should be available
        self.assertTrue(self.table.is_available)
        
        # Mark three seats as sold
        for seat in seats[:3]:
            seat.status = Seat.Status.SOLD
            seat.save()
        
        # Table should still be available (one seat remaining)
        self.assertTrue(self.table.is_available)
        
        # Mark last seat as sold
        seats[3].status = Seat.Status.SOLD
        seats[3].save()
        
        # Now table should not be available
        self.assertFalse(self.table.is_available)
        self.assertTrue(self.table.is_sold_out)


class ZoneAPITest(APITestCase):
    """Test Zone API endpoints."""
    
    def setUp(self):
        """Set up test data."""
        self.tenant = Tenant.objects.create(
            name="Test Tenant",
            slug="test-tenant",
            configuration={}
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
            start_date="2025-12-01T20:00:00Z",
            end_date="2025-12-01T23:00:00Z",
            event_type=Event.EventType.NUMBERED_SEAT
        )
        
        self.client.force_authenticate(user=self.user)
    
    def test_create_general_zone(self):
        """Test creating a general zone via API."""
        url = reverse('zones:zone-list')
        data = {
            'event': str(self.event.id),
            'name': 'General Admission',
            'zone_type': 'general',
            'capacity': 500,
            'base_price': '50.00'
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        zone = Zone.objects.get(id=response.data['id'])
        self.assertEqual(zone.name, 'General Admission')
        self.assertEqual(zone.zone_type, Zone.ZoneType.GENERAL)
        self.assertEqual(zone.capacity, 500)
    
    def test_create_numbered_zone(self):
        """Test creating a numbered zone via API."""
        url = reverse('zones:zone-list')
        data = {
            'event': str(self.event.id),
            'name': 'VIP Section',
            'zone_type': 'numbered',
            'capacity': 100,
            'rows': 10,
            'seats_per_row': 10,
            'base_price': '100.00'
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        zone = Zone.objects.get(id=response.data['id'])
        self.assertEqual(zone.name, 'VIP Section')
        self.assertEqual(zone.zone_type, Zone.ZoneType.NUMBERED)
        self.assertEqual(zone.seats.count(), 100)
    
    def test_zone_seat_availability_check(self):
        """Test checking seat availability for a zone."""
        zone = Zone.objects.create(
            tenant=self.tenant,
            event=self.event,
            name="Test Zone",
            zone_type=Zone.ZoneType.NUMBERED,
            capacity=20,
            rows=4,
            seats_per_row=5,
            base_price=Decimal('100.00')
        )
        
        # Get some seat IDs
        seat_ids = list(zone.seats.values_list('id', flat=True)[:3])
        
        url = reverse('zones:zone-check-availability', kwargs={'pk': zone.id})
        data = {
            'zone_id': str(zone.id),
            'seat_ids': [str(sid) for sid in seat_ids]
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['zone_type'], 'numbered')
        self.assertEqual(len(response.data['seats']), 3)
        self.assertTrue(response.data['all_available'])
    
    def test_zone_list_filtering(self):
        """Test filtering zones by event and type."""
        # Create zones
        Zone.objects.create(
            tenant=self.tenant,
            event=self.event,
            name="General Zone",
            zone_type=Zone.ZoneType.GENERAL,
            capacity=500,
            base_price=Decimal('50.00')
        )
        
        Zone.objects.create(
            tenant=self.tenant,
            event=self.event,
            name="VIP Zone",
            zone_type=Zone.ZoneType.NUMBERED,
            capacity=100,
            rows=10,
            seats_per_row=10,
            base_price=Decimal('100.00')
        )
        
        # Test filtering by event
        url = reverse('zones:zone-list')
        response = self.client.get(url, {'event': str(self.event.id)})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)
        
        # Test filtering by zone type
        response = self.client.get(url, {'zone_type': 'general'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['name'], 'General Zone')