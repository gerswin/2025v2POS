import uuid
from decimal import Decimal
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from venezuelan_pos.apps.tenants.models import TenantAwareModel
from venezuelan_pos.apps.events.models import Event
from venezuelan_pos.apps.zones.models import Zone


class PriceStage(TenantAwareModel):
    """
    Time-based pricing periods with percentage markups.
    Supports sequential date ranges for early bird and progressive pricing.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name='price_stages',
        help_text="Event this price stage belongs to"
    )
    
    # Stage identification
    name = models.CharField(
        max_length=255,
        help_text="Price stage name (e.g., 'Early Bird', 'Regular', 'Last Minute')"
    )
    description = models.TextField(
        blank=True,
        help_text="Description of this pricing stage"
    )
    
    # Date range for this stage
    start_date = models.DateTimeField(
        help_text="When this pricing stage becomes active"
    )
    end_date = models.DateTimeField(
        help_text="When this pricing stage ends"
    )
    
    # Pricing configuration
    percentage_markup = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Percentage markup over base price (e.g., 15.00 for 15% increase)"
    )
    
    # Stage order and status
    stage_order = models.PositiveIntegerField(
        default=0,
        help_text="Order of this stage in the pricing sequence"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this price stage is active"
    )
    
    # Configuration
    configuration = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional stage-specific configuration"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'price_stages'
        verbose_name = 'Price Stage'
        verbose_name_plural = 'Price Stages'
        ordering = ['stage_order', 'start_date']
        unique_together = ['event', 'name']
        indexes = [
            models.Index(fields=['event', 'start_date', 'end_date']),
            models.Index(fields=['start_date', 'end_date']),
        ]
    
    def __str__(self):
        return f"{self.event.name} - {self.name}"
    
    def clean(self):
        """Validate price stage data with sequential date validation."""
        super().clean()
        
        if not self.name.strip():
            raise ValidationError({'name': 'Price stage name cannot be empty'})
        
        if self.start_date and self.end_date:
            if self.start_date >= self.end_date:
                raise ValidationError({
                    'end_date': 'End date must be after start date'
                })
        
        if self.percentage_markup < 0:
            raise ValidationError({
                'percentage_markup': 'Percentage markup cannot be negative'
            })
        
        # Validate non-overlapping sequential date ranges
        if self.event_id and self.start_date and self.end_date:
            overlapping_stages = PriceStage.objects.filter(
                event=self.event,
                is_active=True
            ).exclude(pk=self.pk)
            
            for stage in overlapping_stages:
                if stage.start_date and stage.end_date:
                    # Check for overlap
                    if (self.start_date < stage.end_date and 
                        self.end_date > stage.start_date):
                        raise ValidationError({
                            'start_date': f'Date range overlaps with "{stage.name}" stage',
                            'end_date': f'Date range overlaps with "{stage.name}" stage'
                        })
    
    @property
    def is_current(self):
        """Check if this price stage is currently active."""
        now = timezone.now()
        return (self.is_active and 
                self.start_date <= now <= self.end_date)
    
    @property
    def is_upcoming(self):
        """Check if this price stage is upcoming."""
        return self.is_active and timezone.now() < self.start_date
    
    @property
    def is_past(self):
        """Check if this price stage has ended."""
        return timezone.now() > self.end_date
    
    def calculate_markup_amount(self, base_price):
        """Calculate the markup amount for a given base price."""
        if not base_price:
            return Decimal('0.00')
        
        markup_decimal = self.percentage_markup / 100
        return base_price * markup_decimal
    
    def calculate_final_price(self, base_price):
        """Calculate the final price with markup applied."""
        if not base_price:
            return Decimal('0.00')
        
        markup_amount = self.calculate_markup_amount(base_price)
        return base_price + markup_amount


class RowPricing(TenantAwareModel):
    """
    Row-specific pricing modifiers within numbered zones.
    Supports percentage markups based on row position.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    zone = models.ForeignKey(
        Zone,
        on_delete=models.CASCADE,
        related_name='row_pricing',
        help_text="Zone this row pricing belongs to"
    )
    
    # Row identification
    row_number = models.PositiveIntegerField(
        help_text="Row number within the zone"
    )
    
    # Pricing configuration
    percentage_markup = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Percentage markup over zone base price (e.g., 25.00 for 25% increase)"
    )
    
    # Configuration
    name = models.CharField(
        max_length=255,
        blank=True,
        help_text="Optional name for this row pricing (e.g., 'VIP Row', 'Premium')"
    )
    description = models.TextField(
        blank=True,
        help_text="Description of this row pricing"
    )
    
    # Status
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this row pricing is active"
    )
    
    # Configuration
    configuration = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional row-specific pricing configuration"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'row_pricing'
        verbose_name = 'Row Pricing'
        verbose_name_plural = 'Row Pricing'
        ordering = ['row_number']
        unique_together = ['zone', 'row_number']
        indexes = [
            models.Index(fields=['zone', 'row_number']),
        ]
    
    def __str__(self):
        display_name = self.name or f"Row {self.row_number}"
        return f"{self.zone.name} - {display_name}"
    
    def clean(self):
        """Validate row pricing data."""
        super().clean()
        
        # Only validate zone-related fields if zone is set
        # This prevents errors during form validation before zone assignment
        zone = None
        if hasattr(self, 'zone_id') and self.zone_id:
            try:
                zone = self.zone
            except Zone.DoesNotExist:
                # Zone not found, will be handled by foreign key validation
                pass
        
        if zone and zone.zone_type != Zone.ZoneType.NUMBERED:
            raise ValidationError({
                'zone': 'Row pricing can only be applied to numbered zones'
            })
        
        if self.row_number and self.row_number <= 0:
            raise ValidationError({
                'row_number': 'Row number must be positive'
            })
        
        if zone and zone.rows and self.row_number and self.row_number > zone.rows:
            raise ValidationError({
                'row_number': f'Row number cannot exceed zone rows ({zone.rows})'
            })
        
        if self.percentage_markup is not None and self.percentage_markup < 0:
            raise ValidationError({
                'percentage_markup': 'Percentage markup cannot be negative'
            })
    
    def calculate_markup_amount(self, base_price):
        """Calculate the markup amount for a given base price."""
        if not base_price:
            return Decimal('0.00')
        
        markup_decimal = self.percentage_markup / 100
        return base_price * markup_decimal
    
    def calculate_final_price(self, base_price):
        """Calculate the final price with row markup applied."""
        if not base_price:
            return Decimal('0.00')
        
        markup_amount = self.calculate_markup_amount(base_price)
        return base_price + markup_amount


class PriceHistory(TenantAwareModel):
    """
    Price history tracking for audit purposes.
    Records all price calculations and changes over time.
    """
    
    class PriceType(models.TextChoices):
        ZONE_BASE = 'zone_base', 'Zone Base Price'
        STAGE_MARKUP = 'stage_markup', 'Price Stage Markup'
        ROW_MARKUP = 'row_markup', 'Row Pricing Markup'
        FINAL_CALCULATED = 'final_calculated', 'Final Calculated Price'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Related objects
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name='price_history',
        help_text="Event this price history belongs to"
    )
    zone = models.ForeignKey(
        Zone,
        on_delete=models.CASCADE,
        related_name='price_history',
        null=True,
        blank=True,
        help_text="Zone this price history belongs to (if applicable)"
    )
    price_stage = models.ForeignKey(
        PriceStage,
        on_delete=models.CASCADE,
        related_name='price_history',
        null=True,
        blank=True,
        help_text="Price stage used in calculation (if applicable)"
    )
    row_pricing = models.ForeignKey(
        RowPricing,
        on_delete=models.CASCADE,
        related_name='price_history',
        null=True,
        blank=True,
        help_text="Row pricing used in calculation (if applicable)"
    )
    
    # Price information
    price_type = models.CharField(
        max_length=20,
        choices=PriceType.choices,
        help_text="Type of price being recorded"
    )
    base_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Base price used in calculation"
    )
    markup_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Markup percentage applied"
    )
    markup_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Calculated markup amount"
    )
    final_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Final calculated price"
    )
    
    # Context information
    calculation_date = models.DateTimeField(
        default=timezone.now,
        help_text="When this price calculation was performed"
    )
    row_number = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Row number (if applicable)"
    )
    seat_number = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Seat number (if applicable)"
    )
    
    # Calculation details
    calculation_details = models.JSONField(
        default=dict,
        blank=True,
        help_text="Detailed calculation breakdown"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'price_history'
        verbose_name = 'Price History'
        verbose_name_plural = 'Price History'
        ordering = ['-calculation_date', '-created_at']
        indexes = [
            models.Index(fields=['event', 'calculation_date']),
            models.Index(fields=['zone', 'calculation_date']),
            models.Index(fields=['price_type', 'calculation_date']),
        ]
    
    def __str__(self):
        context = f"{self.event.name}"
        if self.zone:
            context += f" - {self.zone.name}"
        if self.row_number:
            context += f" - Row {self.row_number}"
        if self.seat_number:
            context += f", Seat {self.seat_number}"
        
        return f"{context} - {self.get_price_type_display()}: ${self.final_price}"