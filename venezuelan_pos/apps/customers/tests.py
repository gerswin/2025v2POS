from django.test import TestCase
from django.core.exceptions import ValidationError
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from venezuelan_pos.apps.tenants.models import Tenant, User
from .models import Customer, CustomerPreferences


class CustomerModelTest(TestCase):
    """Test cases for Customer model."""
    
    def setUp(self):
        """Set up test data."""
        self.tenant = Tenant.objects.create(
            name="Test Tenant",
            slug="test-tenant"
        )
    
    def test_create_customer_with_phone(self):
        """Test creating customer with phone number."""
        customer = Customer.objects.create(
            tenant=self.tenant,
            name="Juan",
            surname="Pérez",
            phone="+584121234567"
        )
        
        self.assertEqual(customer.full_name, "Juan Pérez")
        self.assertEqual(str(customer.phone), "+584121234567")
        self.assertTrue(customer.is_active)
        
        # Check that preferences were created automatically
        self.assertTrue(hasattr(customer, 'preferences'))
        self.assertIsInstance(customer.preferences, CustomerPreferences)
    
    def test_create_customer_with_email(self):
        """Test creating customer with email."""
        customer = Customer.objects.create(
            tenant=self.tenant,
            name="María",
            surname="González",
            email="maria@example.com"
        )
        
        self.assertEqual(customer.primary_contact, "maria@example.com")
        self.assertEqual(customer.display_identification, "N/A")
    
    def test_create_customer_with_cedula(self):
        """Test creating customer with Venezuelan cédula."""
        customer = Customer.objects.create(
            tenant=self.tenant,
            name="Carlos",
            surname="Rodríguez",
            phone="+584121234567",
            identification="V-12345678"
        )
        
        self.assertEqual(customer.identification, "V-12345678")
        self.assertEqual(customer.display_identification, "V-12345678")
    
    def test_customer_validation_no_contact(self):
        """Test that customer requires at least phone or email."""
        with self.assertRaises(ValidationError):
            customer = Customer(
                tenant=self.tenant,
                name="Test",
                surname="User"
            )
            customer.full_clean()
    
    def test_customer_validation_empty_name(self):
        """Test that customer requires non-empty name."""
        with self.assertRaises(ValidationError):
            customer = Customer(
                tenant=self.tenant,
                name="",
                surname="User",
                phone="+584121234567"
            )
            customer.full_clean()
    
    def test_cedula_validation_valid(self):
        """Test valid cédula formats."""
        valid_cedulas = ["V-12345678", "E-87654321", "v-1234567", "e-12345678"]
        
        for cedula in valid_cedulas:
            customer = Customer(
                tenant=self.tenant,
                name="Test",
                surname="User",
                phone="+584121234567",
                identification=cedula
            )
            try:
                customer.full_clean()
            except ValidationError:
                self.fail(f"Valid cédula {cedula} should not raise ValidationError")
    
    def test_cedula_validation_invalid(self):
        """Test invalid cédula formats."""
        invalid_cedulas = ["12345678", "V12345678", "V-123", "X-12345678", "V-123456789"]
        
        for cedula in invalid_cedulas:
            customer = Customer(
                tenant=self.tenant,
                name="Test",
                surname="User",
                phone="+584121234567",
                identification=cedula
            )
            with self.assertRaises(ValidationError):
                customer.full_clean()
    
    def test_customer_search(self):
        """Test customer search functionality."""
        customer1 = Customer.objects.create(
            tenant=self.tenant,
            name="Juan",
            surname="Pérez",
            phone="+584121234567",
            identification="V-12345678"
        )
        
        customer2 = Customer.objects.create(
            tenant=self.tenant,
            name="María",
            surname="González",
            email="maria@example.com"
        )
        
        # Search by name
        results = Customer.objects.search("Juan")
        self.assertIn(customer1, results)
        self.assertNotIn(customer2, results)
        
        # Search by surname
        results = Customer.objects.search("González")
        self.assertIn(customer2, results)
        self.assertNotIn(customer1, results)
        
        # Search by phone
        results = Customer.objects.search("4121234567")
        self.assertIn(customer1, results)
        
        # Search by email
        results = Customer.objects.search("maria@example.com")
        self.assertIn(customer2, results)
        
        # Search by identification
        results = Customer.objects.search("V-12345678")
        self.assertIn(customer1, results)


class CustomerPreferencesModelTest(TestCase):
    """Test cases for CustomerPreferences model."""
    
    def setUp(self):
        """Set up test data."""
        self.tenant = Tenant.objects.create(
            name="Test Tenant",
            slug="test-tenant"
        )
        self.customer = Customer.objects.create(
            tenant=self.tenant,
            name="Test",
            surname="User",
            phone="+584121234567"
        )
    
    def test_default_preferences_created(self):
        """Test that default preferences are created automatically."""
        self.assertTrue(hasattr(self.customer, 'preferences'))
        prefs = self.customer.preferences
        
        # Check default values
        self.assertTrue(prefs.email_enabled)
        self.assertTrue(prefs.sms_enabled)
        self.assertTrue(prefs.whatsapp_enabled)
        self.assertFalse(prefs.phone_enabled)
        self.assertTrue(prefs.purchase_confirmations)
        self.assertTrue(prefs.payment_reminders)
        self.assertTrue(prefs.event_reminders)
        self.assertFalse(prefs.promotional_messages)
        self.assertTrue(prefs.system_updates)
    
    def test_can_receive_notification(self):
        """Test notification permission checking."""
        prefs = self.customer.preferences
        
        # Test enabled channel and notification type
        self.assertTrue(prefs.can_receive_notification(
            CustomerPreferences.CommunicationChannel.EMAIL,
            CustomerPreferences.NotificationType.PURCHASE_CONFIRMATION
        ))
        
        # Test disabled channel
        self.assertFalse(prefs.can_receive_notification(
            CustomerPreferences.CommunicationChannel.PHONE,
            CustomerPreferences.NotificationType.PURCHASE_CONFIRMATION
        ))
        
        # Test disabled notification type
        self.assertFalse(prefs.can_receive_notification(
            CustomerPreferences.CommunicationChannel.EMAIL,
            CustomerPreferences.NotificationType.PROMOTIONAL
        ))
    
    def test_get_enabled_channels(self):
        """Test getting enabled communication channels."""
        prefs = self.customer.preferences
        channels = prefs.get_enabled_channels()
        
        expected_channels = [
            CustomerPreferences.CommunicationChannel.EMAIL,
            CustomerPreferences.CommunicationChannel.SMS,
            CustomerPreferences.CommunicationChannel.WHATSAPP,
        ]
        
        self.assertEqual(set(channels), set(expected_channels))


class CustomerAPITest(APITestCase):
    """Test cases for Customer API endpoints."""
    
    def setUp(self):
        """Set up test data."""
        self.tenant = Tenant.objects.create(
            name="Test Tenant",
            slug="test-tenant"
        )
        self.user = User.objects.create_user(
            username="testuser",
            password="testpass123",
            tenant=self.tenant,
            role=User.Role.TENANT_ADMIN
        )
        self.client.force_authenticate(user=self.user)
    
    def test_create_customer(self):
        """Test creating customer via API."""
        data = {
            'name': 'Juan',
            'surname': 'Pérez',
            'phone': '+584121234567',
            'email': 'juan@example.com',
            'identification': 'V-12345678'
        }
        
        url = reverse('customers:customer-list-create')
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Customer.objects.count(), 1)
        
        customer = Customer.objects.first()
        self.assertEqual(customer.name, 'Juan')
        self.assertEqual(customer.surname, 'Pérez')
        self.assertEqual(customer.tenant, self.tenant)
    
    def test_create_customer_invalid_data(self):
        """Test creating customer with invalid data."""
        data = {
            'name': '',  # Empty name
            'surname': 'Pérez',
            # No phone or email
        }
        
        url = reverse('customers:customer-list-create')
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Customer.objects.count(), 0)
    
    def test_list_customers(self):
        """Test listing customers via API."""
        Customer.objects.create(
            tenant=self.tenant,
            name="Juan",
            surname="Pérez",
            phone="+584121234567"
        )
        Customer.objects.create(
            tenant=self.tenant,
            name="María",
            surname="González",
            email="maria@example.com"
        )
        
        url = reverse('customers:customer-list-create')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)
    
    def test_customer_search(self):
        """Test customer search endpoint."""
        customer = Customer.objects.create(
            tenant=self.tenant,
            name="Juan",
            surname="Pérez",
            phone="+584121234567"
        )
        
        url = reverse('customers:customer-search')
        data = {'query': 'Juan'}
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], str(customer.id))
    
    def test_customer_lookup(self):
        """Test customer lookup by identification."""
        customer = Customer.objects.create(
            tenant=self.tenant,
            name="Juan",
            surname="Pérez",
            phone="+584121234567",
            identification="V-12345678"
        )
        
        url = reverse('customers:customer-lookup')
        data = {'identification': 'V-12345678'}
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], str(customer.id))
    
    def test_customer_lookup_not_found(self):
        """Test customer lookup with non-existent identification."""
        url = reverse('customers:customer-lookup')
        data = {'identification': 'V-99999999'}
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_update_customer_preferences(self):
        """Test updating customer preferences."""
        customer = Customer.objects.create(
            tenant=self.tenant,
            name="Juan",
            surname="Pérez",
            phone="+584121234567"
        )
        
        url = reverse('customers:customer-preferences', kwargs={'customer_id': customer.id})
        data = {
            'promotional_messages': True,
            'preferred_language': 'en'
        }
        response = self.client.patch(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Refresh preferences
        customer.preferences.refresh_from_db()
        self.assertTrue(customer.preferences.promotional_messages)
        self.assertEqual(customer.preferences.preferred_language, 'en')
    
    def test_customer_statistics(self):
        """Test customer statistics endpoint."""
        Customer.objects.create(
            tenant=self.tenant,
            name="Juan",
            surname="Pérez",
            phone="+584121234567"
        )
        Customer.objects.create(
            tenant=self.tenant,
            name="María",
            surname="González",
            email="maria@example.com",
            is_active=False
        )
        
        url = reverse('customers:customer-statistics')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_customers'], 2)
        self.assertEqual(response.data['active_customers'], 1)
        self.assertEqual(response.data['inactive_customers'], 1)


class CustomerServiceTest(TestCase):
    """Test cases for Customer services."""
    
    def setUp(self):
        """Set up test data."""
        self.tenant = Tenant.objects.create(
            name="Test Tenant",
            slug="test-tenant"
        )
    
    def test_create_customer_from_sales_data(self):
        """Test creating customer from sales data."""
        from .services import CustomerService
        
        sales_data = {
            'customer_name': 'Juan',
            'customer_surname': 'Pérez',
            'customer_phone': '+584121234567',
            'customer_email': 'juan@example.com',
            'customer_identification': 'V-12345678'
        }
        
        # Mock tenant context
        from venezuelan_pos.apps.tenants.middleware import set_current_tenant
        set_current_tenant(self.tenant)
        
        customer = CustomerService.create_customer_from_sales_data(sales_data)
        
        self.assertEqual(customer.name, 'Juan')
        self.assertEqual(customer.surname, 'Pérez')
        self.assertEqual(customer.tenant, self.tenant)
        self.assertTrue(hasattr(customer, 'preferences'))
    
    def test_find_or_create_customer_existing(self):
        """Test finding existing customer."""
        from .services import CustomerService
        
        # Create existing customer
        existing_customer = Customer.objects.create(
            tenant=self.tenant,
            name="María",
            surname="González",
            email="maria@example.com",
            identification="V-87654321"
        )
        
        sales_data = {
            'customer_name': 'María',
            'customer_surname': 'González',
            'customer_identification': 'V-87654321',
            'customer_email': 'maria@example.com'
        }
        
        # Mock tenant context
        from venezuelan_pos.apps.tenants.middleware import set_current_tenant
        set_current_tenant(self.tenant)
        
        customer = CustomerService.find_or_create_customer(sales_data)
        
        self.assertEqual(customer.id, existing_customer.id)
        self.assertEqual(Customer.objects.count(), 1)  # No new customer created
    
    def test_validate_customer_for_purchase(self):
        """Test customer validation for purchase."""
        from .services import CustomerService
        
        # Valid customer
        customer = Customer.objects.create(
            tenant=self.tenant,
            name="Carlos",
            surname="Rodríguez",
            phone="+584121234567",
            email="carlos@example.com"
        )
        
        validation = CustomerService.validate_customer_for_purchase(customer)
        self.assertTrue(validation['is_valid'])
        self.assertEqual(len(validation['errors']), 0)
        
        # Invalid customer (no contact info)
        invalid_customer = Customer(
            tenant=self.tenant,
            name="Test",
            surname="User"
        )
        # Bypass model validation for testing
        invalid_customer.save = lambda: None
        
        validation = CustomerService.validate_customer_for_purchase(invalid_customer)
        self.assertFalse(validation['is_valid'])
        self.assertGreater(len(validation['errors']), 0)
    
    def test_customer_lookup_service(self):
        """Test customer lookup service."""
        from .services import CustomerLookupService
        
        customer = Customer.objects.create(
            tenant=self.tenant,
            name="Ana",
            surname="Martínez",
            phone="+584129876543",
            email="ana@example.com",
            identification="V-11111111"
        )
        
        # Test lookup by identification
        found = CustomerLookupService.lookup_by_identification("V-11111111")
        self.assertEqual(found.id, customer.id)
        
        # Test lookup by email
        found = CustomerLookupService.lookup_by_email("ana@example.com")
        self.assertEqual(found.id, customer.id)
        
        # Test quick lookup
        found = CustomerLookupService.quick_lookup("V-11111111")
        self.assertEqual(found.id, customer.id)
        
        found = CustomerLookupService.quick_lookup("ana@example.com")
        self.assertEqual(found.id, customer.id)
    
    def test_customer_validation_service(self):
        """Test customer validation service."""
        from .services import CustomerValidationService
        
        # Valid data
        valid_data = {
            'customer_name': 'Pedro',
            'customer_surname': 'López',
            'customer_phone': '+584121234567',
            'customer_email': 'pedro@example.com',
            'customer_identification': 'V-22222222'
        }
        
        result = CustomerValidationService.validate_customer_data_for_sales(valid_data)
        self.assertTrue(result['is_valid'])
        self.assertEqual(len(result['errors']), 0)
        
        # Invalid data (missing required fields)
        invalid_data = {
            'customer_name': '',
            'customer_surname': 'López'
        }
        
        result = CustomerValidationService.validate_customer_data_for_sales(invalid_data)
        self.assertFalse(result['is_valid'])
        self.assertGreater(len(result['errors']), 0)
        
        # Test normalization
        data_to_normalize = {
            'customer_name': '  Pedro  ',
            'customer_identification': 'v-22222222',
            'customer_email': '  pedro@example.com  '
        }
        
        normalized = CustomerValidationService.normalize_customer_data(data_to_normalize)
        self.assertEqual(normalized['customer_name'], 'Pedro')
        self.assertEqual(normalized['customer_identification'], 'V-22222222')
        self.assertEqual(normalized['customer_email'], 'pedro@example.com')