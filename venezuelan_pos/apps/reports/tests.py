from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status
from venezuelan_pos.apps.tenants.models import Tenant, User
from venezuelan_pos.apps.events.models import Event, Venue
from venezuelan_pos.apps.zones.models import Zone
from venezuelan_pos.apps.customers.models import Customer
from venezuelan_pos.apps.sales.models import Transaction, TransactionItem
from .models import SalesReport, OccupancyAnalysis, ReportSchedule
from .services import ReportService


class SalesReportModelTest(TestCase):
    """Test cases for SalesReport model."""
    
    def setUp(self):
        """Set up test data."""
        self.tenant = Tenant.objects.create(
            name="Test Tenant",
            slug="test-tenant"
        )
        
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            tenant=self.tenant
        )
    
    def test_create_sales_report(self):
        """Test creating a sales report."""
        report = SalesReport.objects.create(
            tenant=self.tenant,
            name="Test Report",
            report_type=SalesReport.ReportType.DAILY,
            status=SalesReport.Status.COMPLETED,
            total_transactions=10,
            total_revenue=Decimal('1000.00'),
            total_tickets=25,
            average_ticket_price=Decimal('40.00'),
            generated_by=self.user
        )
        
        self.assertEqual(report.name, "Test Report")
        self.assertEqual(report.report_type, SalesReport.ReportType.DAILY)
        self.assertEqual(report.total_transactions, 10)
        self.assertEqual(report.total_revenue, Decimal('1000.00'))
        self.assertTrue(report.is_completed)
    
    def test_sales_report_validation(self):
        """Test sales report validation."""
        # Test negative revenue validation
        with self.assertRaises(Exception):
            report = SalesReport(
                tenant=self.tenant,
                name="Invalid Report",
                total_revenue=Decimal('-100.00')
            )
            report.full_clean()
    
    def test_duration_display(self):
        """Test duration display property."""
        start_date = timezone.now()
        end_date = start_date + timezone.timedelta(days=7)
        
        report = SalesReport.objects.create(
            tenant=self.tenant,
            name="Weekly Report",
            report_type=SalesReport.ReportType.WEEKLY,
            period_start=start_date,
            period_end=end_date,
            generated_by=self.user
        )
        
        self.assertIn("day", report.duration_display.lower())


class OccupancyAnalysisModelTest(TestCase):
    """Test cases for OccupancyAnalysis model."""
    
    def setUp(self):
        """Set up test data."""
        self.tenant = Tenant.objects.create(
            name="Test Tenant",
            slug="test-tenant"
        )
        
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            tenant=self.tenant
        )
        
        # Create venue and event
        self.venue = Venue.objects.create(
            tenant=self.tenant,
            name="Test Venue"
        )
        
        self.event = Event.objects.create(
            tenant=self.tenant,
            name="Test Event",
            venue=self.venue,
            start_date=timezone.now() + timezone.timedelta(days=1),
            end_date=timezone.now() + timezone.timedelta(days=2)
        )
        
        self.zone = Zone.objects.create(
            tenant=self.tenant,
            event=self.event,
            name="Test Zone",
            zone_type=Zone.ZoneType.GENERAL,
            capacity=100,
            base_price=Decimal('50.00')
        )
    
    def test_create_occupancy_analysis(self):
        """Test creating an occupancy analysis."""
        analysis = OccupancyAnalysis.objects.create(
            tenant=self.tenant,
            event=self.event,
            zone=self.zone,
            name="Test Analysis",
            analysis_type=OccupancyAnalysis.AnalysisType.ZONE,
            total_capacity=100,
            sold_tickets=75,
            fill_rate=Decimal('75.00'),
            sales_velocity=Decimal('5.00'),
            generated_by=self.user
        )
        
        self.assertEqual(analysis.name, "Test Analysis")
        self.assertEqual(analysis.total_capacity, 100)
        self.assertEqual(analysis.sold_tickets, 75)
        self.assertEqual(analysis.available_capacity, 25)
        self.assertEqual(analysis.occupancy_status, "Moderate Occupancy")
    
    def test_performance_rating(self):
        """Test performance rating calculation."""
        # High performance analysis
        high_analysis = OccupancyAnalysis.objects.create(
            tenant=self.tenant,
            zone=self.zone,
            name="High Performance",
            fill_rate=Decimal('95.00'),
            sales_velocity=Decimal('10.00'),
            generated_by=self.user
        )
        
        self.assertEqual(high_analysis.performance_rating, "Excellent")
        
        # Low performance analysis
        low_analysis = OccupancyAnalysis.objects.create(
            tenant=self.tenant,
            zone=self.zone,
            name="Low Performance",
            fill_rate=Decimal('15.00'),
            sales_velocity=Decimal('0.50'),
            generated_by=self.user
        )
        
        self.assertEqual(low_analysis.performance_rating, "Poor")


class ReportScheduleModelTest(TestCase):
    """Test cases for ReportSchedule model."""
    
    def setUp(self):
        """Set up test data."""
        self.tenant = Tenant.objects.create(
            name="Test Tenant",
            slug="test-tenant"
        )
        
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            tenant=self.tenant
        )
    
    def test_create_report_schedule(self):
        """Test creating a report schedule."""
        next_run = timezone.now() + timezone.timedelta(hours=1)
        
        schedule = ReportSchedule.objects.create(
            tenant=self.tenant,
            name="Daily Sales Report",
            report_type=SalesReport.ReportType.DAILY,
            frequency=ReportSchedule.Frequency.DAILY,
            next_run=next_run,
            created_by=self.user
        )
        
        self.assertEqual(schedule.name, "Daily Sales Report")
        self.assertEqual(schedule.frequency, ReportSchedule.Frequency.DAILY)
        self.assertTrue(schedule.is_active)
        self.assertFalse(schedule.is_due)
    
    def test_calculate_next_run(self):
        """Test next run calculation."""
        current_time = timezone.now()
        
        schedule = ReportSchedule.objects.create(
            tenant=self.tenant,
            name="Weekly Report",
            frequency=ReportSchedule.Frequency.WEEKLY,
            next_run=current_time,
            created_by=self.user
        )
        
        next_run = schedule.calculate_next_run()
        expected_next_run = current_time + timezone.timedelta(weeks=1)
        
        # Allow for small time differences
        self.assertAlmostEqual(
            next_run.timestamp(),
            expected_next_run.timestamp(),
            delta=1  # 1 second tolerance
        )


class SalesReportAPITest(APITestCase):
    """Test cases for SalesReport API endpoints."""
    
    def setUp(self):
        """Set up test data."""
        self.tenant = Tenant.objects.create(
            name="Test Tenant",
            slug="test-tenant"
        )
        
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            tenant=self.tenant
        )
        
        # Authenticate user
        self.client.force_authenticate(user=self.user)
    
    def test_list_sales_reports(self):
        """Test listing sales reports."""
        # Create test reports
        SalesReport.objects.create(
            tenant=self.tenant,
            name="Report 1",
            report_type=SalesReport.ReportType.DAILY,
            generated_by=self.user
        )
        
        SalesReport.objects.create(
            tenant=self.tenant,
            name="Report 2",
            report_type=SalesReport.ReportType.WEEKLY,
            generated_by=self.user
        )
        
        url = '/api/reports/sales-reports/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)
    
    def test_create_sales_report(self):
        """Test creating a sales report via API."""
        url = '/api/reports/sales-reports/'
        data = {
            'name': 'API Test Report',
            'report_type': 'daily',
            'export_formats': ['json', 'csv']
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(SalesReport.objects.count(), 1)
        
        report = SalesReport.objects.first()
        self.assertEqual(report.name, 'API Test Report')
        self.assertEqual(report.generated_by, self.user)
    
    def test_filter_sales_reports(self):
        """Test filtering sales reports."""
        # Create reports with different types
        SalesReport.objects.create(
            tenant=self.tenant,
            name="Daily Report",
            report_type=SalesReport.ReportType.DAILY,
            generated_by=self.user
        )
        
        SalesReport.objects.create(
            tenant=self.tenant,
            name="Weekly Report",
            report_type=SalesReport.ReportType.WEEKLY,
            generated_by=self.user
        )
        
        # Filter by report type
        url = '/api/reports/sales-reports/?report_type=daily'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['report_type'], 'daily')
    
    def test_sales_report_summary(self):
        """Test sales report summary endpoint."""
        # Create test reports
        SalesReport.objects.create(
            tenant=self.tenant,
            name="Completed Report",
            status=SalesReport.Status.COMPLETED,
            generated_by=self.user
        )
        
        SalesReport.objects.create(
            tenant=self.tenant,
            name="Failed Report",
            status=SalesReport.Status.FAILED,
            generated_by=self.user
        )
        
        url = '/api/reports/sales-reports/summary/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_reports'], 2)
        self.assertEqual(response.data['completed_reports'], 1)
        self.assertEqual(response.data['failed_reports'], 1)


class ReportServiceTest(TestCase):
    """Test cases for ReportService."""
    
    def setUp(self):
        """Set up test data."""
        self.tenant = Tenant.objects.create(
            name="Test Tenant",
            slug="test-tenant"
        )
        
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            tenant=self.tenant
        )
        
        # Create venue and event
        self.venue = Venue.objects.create(
            tenant=self.tenant,
            name="Test Venue"
        )
        
        self.event = Event.objects.create(
            tenant=self.tenant,
            name="Test Event",
            venue=self.venue,
            start_date=timezone.now() + timezone.timedelta(days=1),
            end_date=timezone.now() + timezone.timedelta(days=2)
        )
        
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
            name="Test",
            surname="Customer",
            email="customer@example.com",
            phone="+584121234567"
        )
    
    def test_generate_sales_report_data(self):
        """Test generating sales report data."""
        # Create test transaction
        transaction = Transaction.objects.create(
            tenant=self.tenant,
            event=self.event,
            customer=self.customer,
            status=Transaction.Status.COMPLETED,
            total_amount=Decimal('100.00'),
            completed_at=timezone.now()
        )
        
        TransactionItem.objects.create(
            tenant=self.tenant,
            transaction=transaction,
            zone=self.zone,
            quantity=2,
            unit_price=Decimal('50.00'),
            subtotal_price=Decimal('100.00'),
            total_price=Decimal('100.00')
        )
        
        # Generate report data
        report_data = ReportService.generate_sales_report_data(self.tenant)
        
        self.assertEqual(report_data['base_statistics']['total_transactions'], 1)
        self.assertEqual(float(report_data['base_statistics']['total_revenue']), 100.00)
        self.assertEqual(report_data['base_statistics']['total_tickets'], 2)
        
        # Check breakdowns exist
        self.assertIn('breakdowns', report_data)
        self.assertIn('by_event', report_data['breakdowns'])
        self.assertIn('by_zone', report_data['breakdowns'])
    
    def test_calculate_zone_performance_metrics(self):
        """Test calculating zone performance metrics."""
        # Create test transaction
        transaction = Transaction.objects.create(
            tenant=self.tenant,
            event=self.event,
            customer=self.customer,
            status=Transaction.Status.COMPLETED,
            total_amount=Decimal('250.00'),
            completed_at=timezone.now()
        )
        
        TransactionItem.objects.create(
            tenant=self.tenant,
            transaction=transaction,
            zone=self.zone,
            quantity=5,
            unit_price=Decimal('50.00'),
            subtotal_price=Decimal('250.00'),
            total_price=Decimal('250.00')
        )
        
        # Calculate metrics
        metrics = ReportService.calculate_zone_performance_metrics(self.zone)
        
        self.assertEqual(metrics['zone_name'], "Test Zone")
        self.assertEqual(metrics['capacity'], 100)
        self.assertEqual(metrics['total_sold'], 5)
        self.assertEqual(metrics['fill_rate'], 5.0)  # 5/100 * 100
        self.assertGreater(metrics['performance_score'], 0)