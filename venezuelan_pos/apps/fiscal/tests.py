"""
Tests for Fiscal Compliance System.
"""

import pytz
from decimal import Decimal
from datetime import datetime, date, timedelta
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from rest_framework.test import APITestCase
from rest_framework import status

from venezuelan_pos.apps.tenants.models import Tenant
from venezuelan_pos.apps.events.models import Event
from .models import (
    FiscalSeries, FiscalSeriesCounter, FiscalDay, FiscalReport,
    AuditLog, TaxConfiguration, TaxCalculationHistory
)
from .services import (
    FiscalSeriesService, FiscalDayService, FiscalReportService,
    TaxCalculationService, FiscalComplianceService
)

User = get_user_model()


class FiscalSeriesModelTest(TestCase):
    """Test FiscalSeries model functionality"""
    
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name="Test Tenant",
            slug="test-tenant",
            configuration={}
        )
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
    
    def test_fiscal_series_creation(self):
        """Test fiscal series creation with consecutive numbering"""
        # Generate first series
        series1 = FiscalSeriesService.generate_fiscal_series(
            tenant=self.tenant,
            user=self.user
        )
        
        self.assertEqual(series1.series_number, 1)
        self.assertEqual(series1.tenant, self.tenant)
        self.assertEqual(series1.issued_by, self.user)
        self.assertFalse(series1.is_voided)
        
        # Generate second series
        series2 = FiscalSeriesService.generate_fiscal_series(
            tenant=self.tenant,
            user=self.user
        )
        
        self.assertEqual(series2.series_number, 2)
        
        # Verify counter is updated
        counter = self.tenant.fiscal_series_counter
        self.assertEqual(counter.current_series, 2)
    
    def test_fiscal_series_timezone_enforcement(self):
        """Test America/Caracas timezone enforcement"""
        series = FiscalSeriesService.generate_fiscal_series(
            tenant=self.tenant,
            user=self.user
        )
        
        # Check timezone is America/Caracas
        caracas_tz = pytz.timezone('America/Caracas')
        self.assertEqual(series.issued_at.tzinfo.zone, caracas_tz.zone)
    
    def test_fiscal_series_void(self):
        """Test fiscal series voiding functionality"""
        series = FiscalSeriesService.generate_fiscal_series(
            tenant=self.tenant,
            user=self.user
        )
        
        # Void the series
        reason = "Test void reason"
        voided_series = FiscalSeriesService.void_fiscal_series(
            fiscal_series_id=series.id,
            user=self.user,
            reason=reason
        )
        
        self.assertTrue(voided_series.is_voided)
        self.assertEqual(voided_series.void_reason, reason)
        self.assertEqual(voided_series.voided_by, self.user)
        self.assertIsNotNone(voided_series.voided_at)
        
        # Test double void prevention
        with self.assertRaises(ValidationError):
            FiscalSeriesService.void_fiscal_series(
                fiscal_series_id=series.id,
                user=self.user,
                reason="Another reason"
            )


class FiscalDayModelTest(TestCase):
    """Test FiscalDay model functionality"""
    
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name="Test Tenant",
            slug="test-tenant",
            configuration={}
        )
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
    
    def test_fiscal_day_creation(self):
        """Test fiscal day creation and management"""
        fiscal_day = FiscalDayService.get_current_fiscal_day(
            tenant=self.tenant,
            user=self.user
        )
        
        caracas_tz = pytz.timezone('America/Caracas')
        today = timezone.now().astimezone(caracas_tz).date()
        
        self.assertEqual(fiscal_day.fiscal_date, today)
        self.assertEqual(fiscal_day.tenant, self.tenant)
        self.assertEqual(fiscal_day.user, self.user)
        self.assertFalse(fiscal_day.is_closed)
        self.assertTrue(fiscal_day.can_process_sales())
    
    def test_fiscal_day_closure(self):
        """Test fiscal day closure functionality"""
        fiscal_day, z_report = FiscalDayService.close_fiscal_day(
            tenant=self.tenant,
            user=self.user
        )
        
        self.assertTrue(fiscal_day.is_closed)
        self.assertIsNotNone(fiscal_day.closed_at)
        self.assertIsNotNone(fiscal_day.z_report)
        self.assertEqual(z_report.report_type, 'Z')
        self.assertFalse(fiscal_day.can_process_sales())
        
        # Test double closure prevention
        with self.assertRaises(ValidationError):
            FiscalDayService.close_fiscal_day(
                tenant=self.tenant,
                user=self.user
            )


class TaxConfigurationModelTest(TestCase):
    """Test TaxConfiguration model functionality"""
    
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name="Test Tenant",
            slug="test-tenant",
            configuration={}
        )
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
        self.event = Event.objects.create(
            tenant=self.tenant,
            name="Test Event",
            start_date=timezone.now() + timedelta(days=1),
            end_date=timezone.now() + timedelta(days=2)
        )
    
    def test_percentage_tax_calculation(self):
        """Test percentage-based tax calculation"""
        tax_config = TaxConfiguration.objects.create(
            tenant=self.tenant,
            name="VAT",
            tax_type='PERCENTAGE',
            scope='TENANT',
            rate=Decimal('0.16'),  # 16%
            effective_from=timezone.now(),
            created_by=self.user
        )
        
        base_amount = Decimal('100.00')
        tax_amount = tax_config.calculate_tax(base_amount)
        
        # Should be 16.00 (100 * 0.16)
        self.assertEqual(tax_amount, Decimal('16.00'))
    
    def test_fixed_tax_calculation(self):
        """Test fixed amount tax calculation"""
        tax_config = TaxConfiguration.objects.create(
            tenant=self.tenant,
            name="Service Fee",
            tax_type='FIXED',
            scope='TENANT',
            rate=Decimal('0.00'),
            fixed_amount=Decimal('5.00'),
            effective_from=timezone.now(),
            created_by=self.user
        )
        
        base_amount = Decimal('100.00')
        tax_amount = tax_config.calculate_tax(base_amount)
        
        # Should be 5.00 regardless of base amount
        self.assertEqual(tax_amount, Decimal('5.00'))
    
    def test_compound_tax_calculation(self):
        """Test compound tax calculation"""
        tax_config = TaxConfiguration.objects.create(
            tenant=self.tenant,
            name="Compound Tax",
            tax_type='COMPOUND',
            scope='TENANT',
            rate=Decimal('0.10'),  # 10%
            effective_from=timezone.now(),
            created_by=self.user
        )
        
        base_amount = Decimal('100.00')
        tax_amount = tax_config.calculate_tax(base_amount)
        
        # Should be 11.00 (10% + 10% of 10% = 10 + 1)
        self.assertEqual(tax_amount, Decimal('11.00'))
    
    def test_deterministic_round_up(self):
        """Test deterministic round-up methodology"""
        tax_config = TaxConfiguration.objects.create(
            tenant=self.tenant,
            name="VAT",
            tax_type='PERCENTAGE',
            scope='TENANT',
            rate=Decimal('0.16'),
            effective_from=timezone.now(),
            created_by=self.user
        )
        
        # Test amount that results in fractional cents
        base_amount = Decimal('10.33')  # 16% = 1.6528
        tax_amount = tax_config.calculate_tax(base_amount)
        
        # Should round up to 1.66
        self.assertEqual(tax_amount, Decimal('1.66'))


class TaxCalculationServiceTest(TestCase):
    """Test TaxCalculationService functionality"""
    
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name="Test Tenant",
            slug="test-tenant",
            configuration={}
        )
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
        self.event = Event.objects.create(
            tenant=self.tenant,
            name="Test Event",
            start_date=timezone.now() + timedelta(days=1),
            end_date=timezone.now() + timedelta(days=2)
        )
    
    def test_multiple_tax_calculation(self):
        """Test calculation with multiple tax configurations"""
        # Create tenant-level tax
        TaxConfiguration.objects.create(
            tenant=self.tenant,
            name="VAT",
            tax_type='PERCENTAGE',
            scope='TENANT',
            rate=Decimal('0.16'),
            effective_from=timezone.now(),
            created_by=self.user
        )
        
        # Create event-level tax
        TaxConfiguration.objects.create(
            tenant=self.tenant,
            event=self.event,
            name="Event Tax",
            tax_type='FIXED',
            scope='EVENT',
            rate=Decimal('0.00'),
            fixed_amount=Decimal('2.00'),
            effective_from=timezone.now(),
            created_by=self.user
        )
        
        base_amount = Decimal('100.00')
        tax_amount, tax_details, tax_history = TaxCalculationService.calculate_taxes(
            base_amount=base_amount,
            tenant=self.tenant,
            event=self.event,
            user=self.user
        )
        
        # Should be 18.00 (16.00 VAT + 2.00 Event Tax)
        self.assertEqual(tax_amount, Decimal('18.00'))
        self.assertEqual(len(tax_details), 2)
        self.assertEqual(len(tax_history), 2)
    
    def test_tax_configuration_validation(self):
        """Test tax configuration validation"""
        # Test overlapping date ranges
        TaxConfiguration.objects.create(
            tenant=self.tenant,
            name="Tax 1",
            tax_type='PERCENTAGE',
            scope='TENANT',
            rate=Decimal('0.16'),
            effective_from=timezone.now(),
            effective_until=timezone.now() + timedelta(days=30),
            created_by=self.user
        )
        
        # This should fail due to overlapping dates
        overlapping_config = TaxConfiguration(
            tenant=self.tenant,
            name="Tax 2",
            tax_type='PERCENTAGE',
            scope='TENANT',
            rate=Decimal('0.10'),
            effective_from=timezone.now() + timedelta(days=15),
            effective_until=timezone.now() + timedelta(days=45),
            created_by=self.user
        )
        
        with self.assertRaises(ValidationError):
            TaxCalculationService.validate_tax_configuration(overlapping_config)


class FiscalReportServiceTest(TestCase):
    """Test FiscalReportService functionality"""
    
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name="Test Tenant",
            slug="test-tenant",
            configuration={}
        )
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
    
    def test_x_report_generation(self):
        """Test X-Report generation"""
        report = FiscalReportService.generate_x_report(
            tenant=self.tenant,
            user=self.user
        )
        
        self.assertEqual(report.report_type, 'X')
        self.assertEqual(report.tenant, self.tenant)
        self.assertEqual(report.user, self.user)
        self.assertEqual(report.report_number, 1)
        self.assertIsNotNone(report.report_data)
    
    def test_z_report_generation(self):
        """Test Z-Report generation"""
        report = FiscalReportService.generate_z_report(
            tenant=self.tenant,
            user=self.user
        )
        
        self.assertEqual(report.report_type, 'Z')
        self.assertEqual(report.tenant, self.tenant)
        self.assertEqual(report.user, self.user)
        self.assertEqual(report.report_number, 1)
        self.assertIsNotNone(report.report_data)
    
    def test_report_numbering(self):
        """Test automatic report numbering"""
        # Generate multiple reports
        x_report1 = FiscalReportService.generate_x_report(
            tenant=self.tenant,
            user=self.user
        )
        x_report2 = FiscalReportService.generate_x_report(
            tenant=self.tenant,
            user=self.user
        )
        z_report1 = FiscalReportService.generate_z_report(
            tenant=self.tenant,
            user=self.user
        )
        
        # X-Reports should be numbered separately from Z-Reports
        self.assertEqual(x_report1.report_number, 1)
        self.assertEqual(x_report2.report_number, 2)
        self.assertEqual(z_report1.report_number, 1)


class AuditLogModelTest(TestCase):
    """Test AuditLog model functionality"""
    
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name="Test Tenant",
            slug="test-tenant",
            configuration={}
        )
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
    
    def test_audit_log_immutability(self):
        """Test that audit logs are immutable"""
        from .services import AuditLogService
        
        audit_log = AuditLogService.log_action(
            tenant=self.tenant,
            user=self.user,
            action_type='CREATE',
            object_type='TestObject',
            object_id='123',
            description="Test audit log"
        )
        
        # Try to modify the audit log
        with self.assertRaises(ValidationError):
            audit_log.description = "Modified description"
            audit_log.save()
    
    def test_audit_log_timezone(self):
        """Test audit log timezone enforcement"""
        from .services import AuditLogService
        
        audit_log = AuditLogService.log_action(
            tenant=self.tenant,
            user=self.user,
            action_type='CREATE',
            object_type='TestObject',
            object_id='123'
        )
        
        # Check timezone is America/Caracas
        caracas_tz = pytz.timezone('America/Caracas')
        self.assertEqual(audit_log.timestamp.tzinfo.zone, caracas_tz.zone)


class FiscalComplianceAPITest(APITestCase):
    """Test Fiscal Compliance API endpoints"""
    
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name="Test Tenant",
            slug="test-tenant",
            configuration={}
        )
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
        self.user.tenant = self.tenant
        self.user.save()
        
        # Authenticate user
        self.client.force_authenticate(user=self.user)
    
    def test_fiscal_status_endpoint(self):
        """Test fiscal status API endpoint"""
        url = '/api/fiscal/compliance/status/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('fiscal_day', response.data)
        self.assertIn('today_stats', response.data)
        self.assertIn('can_process_sales', response.data)
    
    def test_tax_calculation_endpoint(self):
        """Test tax calculation API endpoint"""
        # Create tax configuration
        TaxConfiguration.objects.create(
            tenant=self.tenant,
            name="VAT",
            tax_type='PERCENTAGE',
            scope='TENANT',
            rate=Decimal('0.16'),
            effective_from=timezone.now(),
            created_by=self.user
        )
        
        url = '/api/fiscal/tax-configurations/calculate/'
        data = {
            'base_amount': '100.00'
        }
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['base_amount'], '100.00')
        self.assertEqual(response.data['tax_amount'], '16.00')
        self.assertEqual(response.data['total_amount'], '116.00')
    
    def test_fiscal_day_closure_endpoint(self):
        """Test fiscal day closure API endpoint"""
        url = '/api/fiscal/days/close/'
        data = {
            'confirm': True
        }
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['is_closed'])
    
    def test_report_generation_endpoint(self):
        """Test report generation API endpoint"""
        url = '/api/fiscal/reports/generate/'
        data = {
            'report_type': 'X'
        }
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['report_type'], 'X')
        self.assertEqual(response.data['report_number'], 1)