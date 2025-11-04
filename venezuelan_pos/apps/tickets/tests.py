from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase
from rest_framework import status
from decimal import Decimal
from unittest.mock import patch, MagicMock
from venezuelan_pos.apps.tenants.models import Tenant, User
from venezuelan_pos.apps.events.models import Event, Venue
from venezuelan_pos.apps.zones.models import Zone, Seat
from venezuelan_pos.apps.customers.models import Customer
from venezuelan_pos.apps.sales.models import Transaction, TransactionItem
from .models import DigitalTicket, TicketTemplate, TicketValidationLog
from .services import TicketPDFService, TicketValidationService


class DigitalTicketModelTest(TestCase):
    """Test cases for DigitalTicket model."""
    
    def setUp(self):
        """Set up test data."""
        # Create tenant
        self.tenant = Tenant.objects.create(
            name="Test Tenant",
            slug="test-tenant"
        )
        
        # Create venue
        self.venue = Venue.objects.create(
            tenant=self.tenant,
            name="Test Venue",
            address="123 Test St"
        )
        
        # Create event
        self.event = Event.objects.create(
            tenant=self.tenant,
            name="Test Event",
            venue=self.venue,
            start_date=timezone.now() + timezone.timedelta(days=7),
            end_date=timezone.now() + timezone.timedelta(days=7, hours=3)
        )
        
        # Create zone
        self.zone = Zone.objects.create(
            tenant=self.tenant,
            event=self.event,
            name="Test Zone",
            zone_type=Zone.ZoneType.GENERAL,
            capacity=100,
            base_price=Decimal('50.00')
        )
        
        # Create customer
        self.customer = Customer.objects.create(
            tenant=self.tenant,
            name="John",
            surname="Doe",
            email="john.doe@example.com",
            phone="+584121234567"
        )
        
        # Create transaction
        self.transaction = Transaction.objects.create(
            tenant=self.tenant,
            event=self.event,
            customer=self.customer,
            fiscal_series="TEST00000001",
            total_amount=Decimal('50.00'),
            status=Transaction.Status.COMPLETED
        )
        
        # Create transaction item
        self.transaction_item = TransactionItem.objects.create(
            tenant=self.tenant,
            transaction=self.transaction,
            zone=self.zone,
            unit_price=Decimal('50.00'),
            quantity=1
        )
    
    def test_digital_ticket_creation(self):
        """Test creating a digital ticket."""
        ticket = DigitalTicket.objects.create(
            tenant=self.tenant,
            transaction=self.transaction,
            transaction_item=self.transaction_item,
            event=self.event,
            customer=self.customer,
            ticket_number="TEST00000001-01-01",
            zone=self.zone,
            unit_price=Decimal('50.00'),
            total_price=Decimal('50.00')
        )
        
        self.assertEqual(ticket.tenant, self.tenant)
        self.assertEqual(ticket.ticket_number, "TEST00000001-01-01")
        self.assertEqual(ticket.status, DigitalTicket.Status.ACTIVE)
        self.assertTrue(ticket.is_valid)
        self.assertTrue(ticket.can_be_used)
        self.assertEqual(ticket.remaining_uses, 1)
    
    def test_qr_code_generation(self):
        """Test QR code generation."""
        ticket = DigitalTicket.objects.create(
            tenant=self.tenant,
            transaction=self.transaction,
            transaction_item=self.transaction_item,
            event=self.event,
            customer=self.customer,
            ticket_number="TEST00000001-01-01",
            zone=self.zone,
            unit_price=Decimal('50.00'),
            total_price=Decimal('50.00')
        )
        
        # Generate QR code
        with patch('venezuelan_pos.apps.tickets.models.settings') as mock_settings:
            mock_settings.TICKET_ENCRYPTION_KEY = b'test_key_32_bytes_long_for_fernet'
            ticket.generate_qr_code()
        
        self.assertIsNotNone(ticket.qr_code_data)
        self.assertIsNotNone(ticket.validation_hash)
    
    def test_ticket_validation_and_use(self):
        """Test ticket validation and usage."""
        ticket = DigitalTicket.objects.create(
            tenant=self.tenant,
            transaction=self.transaction,
            transaction_item=self.transaction_item,
            event=self.event,
            customer=self.customer,
            ticket_number="TEST00000001-01-01",
            zone=self.zone,
            unit_price=Decimal('50.00'),
            total_price=Decimal('50.00')
        )
        
        # Validate and use ticket
        result = ticket.validate_and_use("test_system")
        
        self.assertTrue(result['valid'])
        self.assertEqual(result['usage_count'], 1)
        self.assertEqual(result['remaining_uses'], 0)
        
        # Refresh ticket
        ticket.refresh_from_db()
        self.assertEqual(ticket.usage_count, 1)
        self.assertEqual(ticket.status, DigitalTicket.Status.USED)
        self.assertIsNotNone(ticket.first_used_at)
        self.assertIsNotNone(ticket.last_used_at)
    
    def test_multi_entry_ticket(self):
        """Test multi-entry ticket functionality."""
        ticket = DigitalTicket.objects.create(
            tenant=self.tenant,
            transaction=self.transaction,
            transaction_item=self.transaction_item,
            event=self.event,
            customer=self.customer,
            ticket_number="TEST00000001-01-01",
            zone=self.zone,
            unit_price=Decimal('50.00'),
            total_price=Decimal('50.00'),
            ticket_type=DigitalTicket.TicketType.MULTI_ENTRY,
            max_usage_count=3
        )
        
        # Use ticket multiple times
        for i in range(3):
            result = ticket.validate_and_use("test_system")
            self.assertTrue(result['valid'])
            self.assertEqual(result['usage_count'], i + 1)
        
        # Try to use again (should fail)
        result = ticket.validate_and_use("test_system")
        self.assertFalse(result['valid'])
    
    def test_generate_tickets_for_transaction(self):
        """Test generating tickets for a transaction."""
        tickets = DigitalTicket.objects.generate_for_transaction(self.transaction)
        
        self.assertEqual(len(tickets), 1)
        self.assertEqual(tickets[0].transaction, self.transaction)
        self.assertEqual(tickets[0].ticket_number, "TEST00000001-01-01")


class TicketTemplateModelTest(TestCase):
    """Test cases for TicketTemplate model."""
    
    def setUp(self):
        """Set up test data."""
        self.tenant = Tenant.objects.create(
            name="Test Tenant",
            slug="test-tenant"
        )
    
    def test_template_creation(self):
        """Test creating a ticket template."""
        template = TicketTemplate.objects.create(
            tenant=self.tenant,
            name="Test Template",
            template_type=TicketTemplate.TemplateType.PDF,
            html_content="<h1>Test Template</h1>",
            css_styles="h1 { color: blue; }"
        )
        
        self.assertEqual(template.name, "Test Template")
        self.assertEqual(template.template_type, TicketTemplate.TemplateType.PDF)
        self.assertTrue(template.is_active)
        self.assertFalse(template.is_default)
    
    def test_create_default_templates(self):
        """Test creating default templates for a tenant."""
        templates = TicketTemplate.create_default_templates(self.tenant)
        
        self.assertEqual(len(templates), 2)  # PDF and Email templates
        
        pdf_template = next(t for t in templates if t.template_type == TicketTemplate.TemplateType.PDF)
        email_template = next(t for t in templates if t.template_type == TicketTemplate.TemplateType.EMAIL)
        
        self.assertTrue(pdf_template.is_default)
        self.assertTrue(email_template.is_default)


class DigitalTicketAPITest(APITestCase):
    """Test cases for Digital Ticket API endpoints."""
    
    def setUp(self):
        """Set up test data."""
        # Create tenant
        self.tenant = Tenant.objects.create(
            name="Test Tenant",
            slug="test-tenant"
        )
        
        # Create user
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            tenant=self.tenant
        )
        
        # Create test data (similar to model tests)
        self.venue = Venue.objects.create(
            tenant=self.tenant,
            name="Test Venue"
        )
        
        self.event = Event.objects.create(
            tenant=self.tenant,
            name="Test Event",
            venue=self.venue,
            start_date=timezone.now() + timezone.timedelta(days=7),
            end_date=timezone.now() + timezone.timedelta(days=7, hours=3)
        )
        
        self.zone = Zone.objects.create(
            tenant=self.tenant,
            event=self.event,
            name="Test Zone",
            zone_type=Zone.ZoneType.GENERAL,
            capacity=100,
            base_price=Decimal('50.00')
        )
        
        self.customer = Customer.objects.create(
            tenant=self.tenant,
            name="John",
            surname="Doe",
            email="john.doe@example.com"
        )
        
        self.transaction = Transaction.objects.create(
            tenant=self.tenant,
            event=self.event,
            customer=self.customer,
            fiscal_series="TEST00000001",
            total_amount=Decimal('50.00'),
            status=Transaction.Status.COMPLETED
        )
        
        self.transaction_item = TransactionItem.objects.create(
            tenant=self.tenant,
            transaction=self.transaction,
            zone=self.zone,
            unit_price=Decimal('50.00'),
            quantity=1
        )
        
        self.ticket = DigitalTicket.objects.create(
            tenant=self.tenant,
            transaction=self.transaction,
            transaction_item=self.transaction_item,
            event=self.event,
            customer=self.customer,
            ticket_number="TEST00000001-01-01",
            zone=self.zone,
            unit_price=Decimal('50.00'),
            total_price=Decimal('50.00')
        )
        
        # Authenticate user
        self.client.force_authenticate(user=self.user)
    
    def test_list_tickets(self):
        """Test listing digital tickets."""
        url = reverse('tickets:digitalticket-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['ticket_number'], "TEST00000001-01-01")
    
    def test_ticket_detail(self):
        """Test retrieving ticket details."""
        url = reverse('tickets:digitalticket-detail', kwargs={'pk': self.ticket.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['ticket_number'], "TEST00000001-01-01")
        self.assertEqual(response.data['customer_name'], "John Doe")
    
    def test_validate_ticket(self):
        """Test ticket validation endpoint."""
        url = reverse('tickets:digitalticket-validate-ticket')
        data = {
            'ticket_number': self.ticket.ticket_number,
            'validation_system_id': 'test_system',
            'mark_as_used': True
        }
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['valid'])
        self.assertEqual(response.data['ticket_number'], self.ticket.ticket_number)
        
        # Check that ticket was marked as used
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.usage_count, 1)
    
    def test_validate_invalid_ticket(self):
        """Test validation of invalid ticket."""
        url = reverse('tickets:digitalticket-validate-ticket')
        data = {
            'ticket_number': 'INVALID_TICKET',
            'validation_system_id': 'test_system'
        }
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(response.data['valid'])
        self.assertEqual(response.data['reason'], 'Ticket not found')
    
    def test_ticket_lookup(self):
        """Test ticket lookup endpoint."""
        url = reverse('tickets:digitalticket-lookup')
        data = {
            'customer_email': self.customer.email
        }
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['ticket_number'], self.ticket.ticket_number)
    
    def test_generate_tickets(self):
        """Test ticket generation endpoint."""
        # Delete existing ticket
        self.ticket.delete()
        
        url = reverse('tickets:digitalticket-generate')
        data = {
            'transaction_id': str(self.transaction.id)
        }
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('Generated 1 digital tickets', response.data['message'])
        self.assertEqual(len(response.data['tickets']), 1)
    
    def test_usage_stats(self):
        """Test usage statistics endpoint."""
        url = reverse('tickets:digitalticket-usage-stats')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_tickets'], 1)
        self.assertEqual(response.data['active_tickets'], 1)
        self.assertEqual(response.data['used_tickets'], 0)


class TicketPDFServiceTest(TestCase):
    """Test cases for TicketPDFService."""
    
    def setUp(self):
        """Set up test data."""
        # Create minimal test data
        self.tenant = Tenant.objects.create(name="Test Tenant", slug="test-tenant")
        self.venue = Venue.objects.create(tenant=self.tenant, name="Test Venue")
        self.event = Event.objects.create(
            tenant=self.tenant,
            name="Test Event",
            venue=self.venue,
            start_date=timezone.now() + timezone.timedelta(days=7),
            end_date=timezone.now() + timezone.timedelta(days=7, hours=3)
        )
        self.zone = Zone.objects.create(
            tenant=self.tenant,
            event=self.event,
            name="Test Zone",
            zone_type=Zone.ZoneType.GENERAL,
            capacity=100,
            base_price=Decimal('50.00')
        )
        self.customer = Customer.objects.create(
            tenant=self.tenant,
            name="John",
            surname="Doe",
            email="john.doe@example.com"
        )
        self.transaction = Transaction.objects.create(
            tenant=self.tenant,
            event=self.event,
            customer=self.customer,
            fiscal_series="TEST00000001",
            total_amount=Decimal('50.00'),
            status=Transaction.Status.COMPLETED
        )
        self.transaction_item = TransactionItem.objects.create(
            tenant=self.tenant,
            transaction=self.transaction,
            zone=self.zone,
            unit_price=Decimal('50.00'),
            quantity=1
        )
        self.ticket = DigitalTicket.objects.create(
            tenant=self.tenant,
            transaction=self.transaction,
            transaction_item=self.transaction_item,
            event=self.event,
            customer=self.customer,
            ticket_number="TEST00000001-01-01",
            zone=self.zone,
            unit_price=Decimal('50.00'),
            total_price=Decimal('50.00')
        )
    
    def test_generate_default_pdf(self):
        """Test generating PDF with default layout."""
        pdf_content = TicketPDFService.generate_pdf_ticket(self.ticket)
        
        self.assertIsInstance(pdf_content, bytes)
        self.assertTrue(len(pdf_content) > 0)
        # PDF should start with PDF header
        self.assertTrue(pdf_content.startswith(b'%PDF'))


class TicketValidationServiceTest(TestCase):
    """Test cases for TicketValidationService."""
    
    def setUp(self):
        """Set up test data."""
        # Create minimal test data (similar to PDF service test)
        self.tenant = Tenant.objects.create(name="Test Tenant", slug="test-tenant")
        self.venue = Venue.objects.create(tenant=self.tenant, name="Test Venue")
        self.event = Event.objects.create(
            tenant=self.tenant,
            name="Test Event",
            venue=self.venue,
            start_date=timezone.now() + timezone.timedelta(days=7),
            end_date=timezone.now() + timezone.timedelta(days=7, hours=3)
        )
        self.zone = Zone.objects.create(
            tenant=self.tenant,
            event=self.event,
            name="Test Zone",
            zone_type=Zone.ZoneType.GENERAL,
            capacity=100,
            base_price=Decimal('50.00')
        )
        self.customer = Customer.objects.create(
            tenant=self.tenant,
            name="John",
            surname="Doe",
            email="john.doe@example.com"
        )
        self.transaction = Transaction.objects.create(
            tenant=self.tenant,
            event=self.event,
            customer=self.customer,
            fiscal_series="TEST00000001",
            total_amount=Decimal('50.00'),
            status=Transaction.Status.COMPLETED
        )
        self.transaction_item = TransactionItem.objects.create(
            tenant=self.tenant,
            transaction=self.transaction,
            zone=self.zone,
            unit_price=Decimal('50.00'),
            quantity=1
        )
        self.ticket = DigitalTicket.objects.create(
            tenant=self.tenant,
            transaction=self.transaction,
            transaction_item=self.transaction_item,
            event=self.event,
            customer=self.customer,
            ticket_number="TEST00000001-01-01",
            zone=self.zone,
            unit_price=Decimal('50.00'),
            total_price=Decimal('50.00')
        )
    
    def test_validate_ticket_number(self):
        """Test validating ticket by ticket number."""
        result = TicketValidationService.validate_ticket_number(
            self.ticket.ticket_number,
            "test_system"
        )
        
        self.assertTrue(result['valid'])
        self.assertEqual(result['ticket_number'], self.ticket.ticket_number)
        self.assertEqual(result['usage_count'], 1)
    
    def test_validate_invalid_ticket_number(self):
        """Test validating invalid ticket number."""
        result = TicketValidationService.validate_ticket_number(
            "INVALID_TICKET",
            "test_system"
        )
        
        self.assertFalse(result['valid'])
        self.assertEqual(result['reason'], 'Ticket not found')
    
    def test_get_validation_stats(self):
        """Test getting validation statistics."""
        # Create some validation logs
        TicketValidationLog.objects.create(
            tenant=self.tenant,
            ticket=self.ticket,
            validation_system_id="test_system",
            validation_result=True,
            usage_count_after=1
        )
        
        TicketValidationLog.objects.create(
            tenant=self.tenant,
            ticket=self.ticket,
            validation_system_id="test_system",
            validation_result=False,
            usage_count_after=1
        )
        
        stats = TicketValidationService.get_validation_stats(self.tenant)
        
        self.assertEqual(stats['total_validations'], 2)
        self.assertEqual(stats['successful_validations'], 1)
        self.assertEqual(stats['failed_validations'], 1)
        self.assertEqual(stats['success_rate'], 50.0)