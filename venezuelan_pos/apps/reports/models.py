import uuid
from decimal import Decimal
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db.models import Sum, Count, Avg, Q, F
from venezuelan_pos.apps.tenants.models import TenantAwareModel
from venezuelan_pos.apps.events.models import Event
from venezuelan_pos.apps.zones.models import Zone
from venezuelan_pos.apps.tenants.models import User


class SalesReportManager(models.Manager):
    """Manager for SalesReport with business logic."""
    
    def create_sales_report(self, tenant, report_type, filters=None, **kwargs):
        """
        Create a new sales report with calculated data.
        """
        from venezuelan_pos.apps.sales.models import Transaction, TransactionItem
        
        # Default filters
        if filters is None:
            filters = {}
        
        # Base queryset for transactions
        transactions_qs = Transaction.objects.filter(
            tenant=tenant,
            status=Transaction.Status.COMPLETED
        )
        
        # Apply filters
        if filters.get('start_date'):
            transactions_qs = transactions_qs.filter(completed_at__gte=filters['start_date'])
        if filters.get('end_date'):
            transactions_qs = transactions_qs.filter(completed_at__lte=filters['end_date'])
        if filters.get('event_id'):
            transactions_qs = transactions_qs.filter(event_id=filters['event_id'])
        if filters.get('zone_id'):
            transactions_qs = transactions_qs.filter(items__zone_id=filters['zone_id'])
        if filters.get('operator_id'):
            transactions_qs = transactions_qs.filter(created_by_id=filters['operator_id'])
        
        # Calculate aggregated data
        aggregated_data = transactions_qs.aggregate(
            total_transactions=Count('id'),
            total_revenue=Sum('total_amount'),
            total_tickets=Sum('items__quantity'),
            average_ticket_price=Avg('total_amount')
        )
        
        # Handle None values
        for key, value in aggregated_data.items():
            if value is None:
                aggregated_data[key] = 0 if 'total_' in key or 'average_' in key else 0
        
        # Create report
        report = self.create(
            tenant=tenant,
            report_type=report_type,
            filters=filters,
            total_transactions=aggregated_data['total_transactions'],
            total_revenue=aggregated_data['total_revenue'] or Decimal('0.00'),
            total_tickets=aggregated_data['total_tickets'] or 0,
            average_ticket_price=aggregated_data['average_ticket_price'] or Decimal('0.00'),
            **kwargs
        )
        
        return report


class SalesReport(TenantAwareModel):
    """
    Sales report model with flexible filtering.
    Stores generated sales reports with aggregated data.
    """
    
    class ReportType(models.TextChoices):
        DAILY = 'daily', 'Daily Report'
        WEEKLY = 'weekly', 'Weekly Report'
        MONTHLY = 'monthly', 'Monthly Report'
        CUSTOM = 'custom', 'Custom Period Report'
        EVENT = 'event', 'Event Report'
        ZONE = 'zone', 'Zone Report'
        OPERATOR = 'operator', 'Operator Report'
    
    class Status(models.TextChoices):
        GENERATING = 'generating', 'Generating'
        COMPLETED = 'completed', 'Completed'
        FAILED = 'failed', 'Failed'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Report identification
    name = models.CharField(
        max_length=255,
        help_text="Report name or title"
    )
    report_type = models.CharField(
        max_length=20,
        choices=ReportType.choices,
        help_text="Type of report"
    )
    
    # Report filters (stored as JSON)
    filters = models.JSONField(
        default=dict,
        blank=True,
        help_text="Filters applied to generate this report"
    )
    
    # Aggregated data
    total_transactions = models.PositiveIntegerField(
        default=0,
        help_text="Total number of transactions"
    )
    total_revenue = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Total revenue amount"
    )
    total_tickets = models.PositiveIntegerField(
        default=0,
        help_text="Total number of tickets sold"
    )
    average_ticket_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Average price per ticket"
    )
    
    # Report period
    period_start = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Start of report period"
    )
    period_end = models.DateTimeField(
        null=True,
        blank=True,
        help_text="End of report period"
    )
    
    # Report status
    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.GENERATING,
        help_text="Current report status"
    )
    
    # Generated by
    generated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='generated_reports',
        help_text="User who generated this report"
    )
    
    # Export information
    export_formats = models.JSONField(
        default=list,
        blank=True,
        help_text="Available export formats for this report"
    )
    
    # Additional data
    detailed_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Detailed report data (breakdowns, charts data, etc.)"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When report generation was completed"
    )
    updated_at = models.DateTimeField(auto_now=True)
    
    objects = SalesReportManager()
    
    class Meta:
        db_table = 'sales_reports'
        verbose_name = 'Sales Report'
        verbose_name_plural = 'Sales Reports'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', 'report_type', 'status']),
            models.Index(fields=['tenant', 'period_start', 'period_end']),
            models.Index(fields=['generated_by']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.get_report_type_display()})"
    
    def clean(self):
        """Validate sales report data."""
        super().clean()
        
        if not self.name.strip():
            raise ValidationError({'name': 'Report name cannot be empty'})
        
        if self.period_start and self.period_end:
            if self.period_start >= self.period_end:
                raise ValidationError({
                    'period_end': 'End date must be after start date'
                })
        
        if self.total_revenue < 0:
            raise ValidationError({'total_revenue': 'Total revenue cannot be negative'})
        
        if self.average_ticket_price < 0:
            raise ValidationError({'average_ticket_price': 'Average ticket price cannot be negative'})
    
    @property
    def is_completed(self):
        """Check if report generation is completed."""
        return self.status == self.Status.COMPLETED
    
    @property
    def is_failed(self):
        """Check if report generation failed."""
        return self.status == self.Status.FAILED
    
    @property
    def duration_display(self):
        """Get human-readable duration for the report period."""
        if not self.period_start or not self.period_end:
            return "N/A"
        
        duration = self.period_end - self.period_start
        days = duration.days
        
        if days == 0:
            return "Same day"
        elif days == 1:
            return "1 day"
        elif days <= 7:
            return f"{days} days"
        elif days <= 31:
            weeks = days // 7
            return f"{weeks} week{'s' if weeks > 1 else ''}"
        else:
            months = days // 30
            return f"{months} month{'s' if months > 1 else ''}"
    
    def mark_completed(self):
        """Mark report as completed."""
        self.status = self.Status.COMPLETED
        self.completed_at = timezone.now()
        self.save(update_fields=['status', 'completed_at'])
    
    def mark_failed(self):
        """Mark report as failed."""
        self.status = self.Status.FAILED
        self.save(update_fields=['status'])


class OccupancyAnalysisManager(models.Manager):
    """Manager for OccupancyAnalysis with business logic."""
    
    def create_occupancy_analysis(self, tenant, event=None, zone=None, **kwargs):
        """
        Create occupancy analysis for event or zone.
        """
        from venezuelan_pos.apps.sales.models import TransactionItem
        from venezuelan_pos.apps.zones.models import Seat
        
        # Base queryset for sold items
        items_qs = TransactionItem.objects.filter(
            tenant=tenant,
            transaction__status='completed'
        )
        
        if event:
            items_qs = items_qs.filter(transaction__event=event)
        if zone:
            items_qs = items_qs.filter(zone=zone)
        
        # Calculate occupancy metrics
        if zone:
            # Zone-specific analysis
            total_capacity = zone.capacity
            sold_tickets = items_qs.filter(zone=zone).aggregate(
                total_sold=Sum('quantity')
            )['total_sold'] or 0
            
            # Calculate fill rate
            fill_rate = (sold_tickets / total_capacity * 100) if total_capacity > 0 else 0
            
            # Calculate sales velocity (tickets per day)
            if event and event.start_date and event.sales_start_date:
                sales_period = (event.start_date - event.sales_start_date).days
                sales_velocity = sold_tickets / sales_period if sales_period > 0 else 0
            else:
                sales_velocity = 0
            
            # Generate heat map data for numbered zones
            heat_map_data = {}
            if zone.zone_type == Zone.ZoneType.NUMBERED:
                sold_seats = Seat.objects.filter(
                    zone=zone,
                    status__in=[Seat.Status.SOLD, Seat.Status.RESERVED]
                )
                
                for seat in sold_seats:
                    row_key = f"row_{seat.row_number}"
                    if row_key not in heat_map_data:
                        heat_map_data[row_key] = {}
                    heat_map_data[row_key][f"seat_{seat.seat_number}"] = {
                        'status': seat.status,
                        'price': float(seat.calculated_price)
                    }
        
        else:
            # Event-wide analysis
            total_capacity = sum(z.capacity for z in event.zones.all()) if event else 0
            sold_tickets = items_qs.aggregate(
                total_sold=Sum('quantity')
            )['total_sold'] or 0
            
            fill_rate = (sold_tickets / total_capacity * 100) if total_capacity > 0 else 0
            sales_velocity = 0  # Would need more complex calculation for event-wide
            heat_map_data = {}
        
        # Create analysis
        analysis = self.create(
            tenant=tenant,
            event=event,
            zone=zone,
            total_capacity=total_capacity,
            sold_tickets=sold_tickets,
            fill_rate=fill_rate,
            sales_velocity=sales_velocity,
            heat_map_data=heat_map_data,
            **kwargs
        )
        
        return analysis


class OccupancyAnalysis(TenantAwareModel):
    """
    Occupancy analysis model for zone performance tracking.
    Stores heat map and statistical data for zones.
    """
    
    class AnalysisType(models.TextChoices):
        ZONE = 'zone', 'Zone Analysis'
        EVENT = 'event', 'Event Analysis'
        COMPARATIVE = 'comparative', 'Comparative Analysis'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Analysis scope
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='occupancy_analyses',
        help_text="Event for this analysis (null for cross-event analysis)"
    )
    zone = models.ForeignKey(
        Zone,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='occupancy_analyses',
        help_text="Zone for this analysis (null for event-wide analysis)"
    )
    
    # Analysis identification
    name = models.CharField(
        max_length=255,
        help_text="Analysis name or title"
    )
    analysis_type = models.CharField(
        max_length=15,
        choices=AnalysisType.choices,
        default=AnalysisType.ZONE,
        help_text="Type of analysis"
    )
    
    # Occupancy metrics
    total_capacity = models.PositiveIntegerField(
        default=0,
        help_text="Total capacity analyzed"
    )
    sold_tickets = models.PositiveIntegerField(
        default=0,
        help_text="Number of tickets sold"
    )
    fill_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Fill rate percentage (0-100)"
    )
    sales_velocity = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Sales velocity (tickets per day)"
    )
    
    # Heat map data
    heat_map_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Heat map data for visualization"
    )
    
    # Performance metrics
    performance_metrics = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional performance metrics and rankings"
    )
    
    # Analysis period
    analysis_start = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Start of analysis period"
    )
    analysis_end = models.DateTimeField(
        null=True,
        blank=True,
        help_text="End of analysis period"
    )
    
    # Generated by
    generated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='generated_analyses',
        help_text="User who generated this analysis"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    objects = OccupancyAnalysisManager()
    
    class Meta:
        db_table = 'occupancy_analyses'
        verbose_name = 'Occupancy Analysis'
        verbose_name_plural = 'Occupancy Analyses'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', 'analysis_type']),
            models.Index(fields=['event', 'zone']),
            models.Index(fields=['generated_by']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        if self.zone:
            return f"Occupancy Analysis: {self.zone.name}"
        elif self.event:
            return f"Occupancy Analysis: {self.event.name}"
        return f"Occupancy Analysis: {self.name}"
    
    def clean(self):
        """Validate occupancy analysis data."""
        super().clean()
        
        if not self.name.strip():
            raise ValidationError({'name': 'Analysis name cannot be empty'})
        
        if self.fill_rate < 0 or self.fill_rate > 100:
            raise ValidationError({'fill_rate': 'Fill rate must be between 0 and 100'})
        
        if self.sales_velocity < 0:
            raise ValidationError({'sales_velocity': 'Sales velocity cannot be negative'})
        
        if self.analysis_start and self.analysis_end:
            if self.analysis_start >= self.analysis_end:
                raise ValidationError({
                    'analysis_end': 'End date must be after start date'
                })
    
    @property
    def available_capacity(self):
        """Get available capacity."""
        return self.total_capacity - self.sold_tickets
    
    @property
    def occupancy_status(self):
        """Get occupancy status description."""
        if self.fill_rate >= 95:
            return "Sold Out"
        elif self.fill_rate >= 80:
            return "High Occupancy"
        elif self.fill_rate >= 50:
            return "Moderate Occupancy"
        elif self.fill_rate >= 20:
            return "Low Occupancy"
        else:
            return "Very Low Occupancy"
    
    @property
    def performance_rating(self):
        """Get performance rating based on fill rate and velocity."""
        # Simple rating algorithm - can be enhanced
        fill_score = min(float(self.fill_rate) / 100, 1.0)  # Normalize to 0-1
        velocity_score = min(float(self.sales_velocity) / 10, 1.0)  # Normalize assuming 10 tickets/day is excellent
        
        combined_score = (fill_score * 0.7) + (velocity_score * 0.3)
        
        if combined_score >= 0.8:
            return "Excellent"
        elif combined_score >= 0.6:
            return "Good"
        elif combined_score >= 0.4:
            return "Average"
        elif combined_score >= 0.2:
            return "Below Average"
        else:
            return "Poor"


class ReportSchedule(TenantAwareModel):
    """
    Report schedule model for automated report generation.
    Allows scheduling of recurring reports.
    """
    
    class Frequency(models.TextChoices):
        DAILY = 'daily', 'Daily'
        WEEKLY = 'weekly', 'Weekly'
        MONTHLY = 'monthly', 'Monthly'
        QUARTERLY = 'quarterly', 'Quarterly'
    
    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        PAUSED = 'paused', 'Paused'
        INACTIVE = 'inactive', 'Inactive'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Schedule identification
    name = models.CharField(
        max_length=255,
        help_text="Schedule name"
    )
    description = models.TextField(
        blank=True,
        help_text="Schedule description"
    )
    
    # Report configuration
    report_type = models.CharField(
        max_length=20,
        choices=SalesReport.ReportType.choices,
        help_text="Type of report to generate"
    )
    report_filters = models.JSONField(
        default=dict,
        blank=True,
        help_text="Default filters for generated reports"
    )
    
    # Schedule configuration
    frequency = models.CharField(
        max_length=15,
        choices=Frequency.choices,
        help_text="How often to generate reports"
    )
    
    # Timing
    next_run = models.DateTimeField(
        help_text="When to generate the next report"
    )
    last_run = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the last report was generated"
    )
    
    # Status
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.ACTIVE,
        help_text="Current schedule status"
    )
    
    # Recipients
    email_recipients = models.JSONField(
        default=list,
        blank=True,
        help_text="Email addresses to send reports to"
    )
    
    # Export configuration
    export_formats = models.JSONField(
        default=list,
        blank=True,
        help_text="Formats to export reports in"
    )
    
    # Created by
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_schedules',
        help_text="User who created this schedule"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'report_schedules'
        verbose_name = 'Report Schedule'
        verbose_name_plural = 'Report Schedules'
        ordering = ['next_run']
        indexes = [
            models.Index(fields=['tenant', 'status', 'next_run']),
            models.Index(fields=['frequency']),
            models.Index(fields=['created_by']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.get_frequency_display()})"
    
    def clean(self):
        """Validate report schedule data."""
        super().clean()
        
        if not self.name.strip():
            raise ValidationError({'name': 'Schedule name cannot be empty'})
        
        if self.next_run <= timezone.now():
            raise ValidationError({'next_run': 'Next run must be in the future'})
    
    @property
    def is_active(self):
        """Check if schedule is active."""
        return self.status == self.Status.ACTIVE
    
    @property
    def is_due(self):
        """Check if schedule is due for execution."""
        return self.is_active and self.next_run <= timezone.now()
    
    def calculate_next_run(self):
        """Calculate the next run time based on frequency."""
        from datetime import timedelta
        
        if self.frequency == self.Frequency.DAILY:
            return self.next_run + timedelta(days=1)
        elif self.frequency == self.Frequency.WEEKLY:
            return self.next_run + timedelta(weeks=1)
        elif self.frequency == self.Frequency.MONTHLY:
            # Approximate monthly as 30 days
            return self.next_run + timedelta(days=30)
        elif self.frequency == self.Frequency.QUARTERLY:
            # Approximate quarterly as 90 days
            return self.next_run + timedelta(days=90)
        else:
            return self.next_run + timedelta(days=1)
    
    def execute(self):
        """Execute the scheduled report generation."""
        # This would be called by a Celery task
        try:
            # Generate the report
            report = SalesReport.objects.create_sales_report(
                tenant=self.tenant,
                report_type=self.report_type,
                filters=self.report_filters,
                name=f"{self.name} - {timezone.now().strftime('%Y-%m-%d')}",
                generated_by=self.created_by
            )
            
            # Update schedule
            self.last_run = timezone.now()
            self.next_run = self.calculate_next_run()
            self.save(update_fields=['last_run', 'next_run'])
            
            return report
            
        except Exception as e:
            # Log error but don't fail the schedule
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to execute scheduled report {self.id}: {e}")
            return None