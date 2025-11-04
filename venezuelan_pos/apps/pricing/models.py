import uuid
from decimal import Decimal
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from venezuelan_pos.apps.tenants.models import TenantAwareModel
from venezuelan_pos.apps.events.models import Event


class PriceStage(TenantAwareModel):
    """
    Hybrid pricing periods with both time-based and quantity-based transitions.
    Supports event-wide or zone-specific pricing with automatic stage transitions.
    """
    
    class ModifierType(models.TextChoices):
        PERCENTAGE = 'percentage', 'Percentage'
        FIXED_AMOUNT = 'fixed_amount', 'Fixed Amount'
    
    class StageScope(models.TextChoices):
        EVENT_WIDE = 'event', 'Event-wide'
        ZONE_SPECIFIC = 'zone', 'Zone-specific'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name='price_stages',
        help_text="Event this price stage belongs to"
    )
    zone = models.ForeignKey(
        'zones.Zone',
        on_delete=models.CASCADE,
        related_name='price_stages',
        null=True,
        blank=True,
        help_text="Zone this stage applies to (null for event-wide stages)"
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
    
    # Hybrid pricing configuration - quantity limits
    quantity_limit = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Maximum tickets that can be sold at this stage before auto-transition"
    )
    
    # Pricing configuration
    modifier_type = models.CharField(
        max_length=15,
        choices=ModifierType.choices,
        default=ModifierType.PERCENTAGE,
        help_text="Type of price modifier (percentage or fixed amount)"
    )
    modifier_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Modifier value (percentage like 15.00 for 15% or fixed amount like 25.00)"
    )
    
    # Stage scope configuration
    scope = models.CharField(
        max_length=10,
        choices=StageScope.choices,
        default=StageScope.EVENT_WIDE,
        help_text="Whether this stage applies event-wide or to specific zones"
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
    
    # Auto-transition configuration
    auto_transition = models.BooleanField(
        default=True,
        help_text="Whether to automatically transition when date expires or quantity reached"
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
            models.Index(fields=['tenant', 'event', 'is_active']),
            models.Index(fields=['tenant', 'zone', 'is_active']),
            models.Index(fields=['event', 'start_date', 'end_date']),
            models.Index(fields=['start_date', 'end_date']),
            models.Index(fields=['scope', 'is_active']),
            models.Index(fields=['stage_order']),
        ]
    
    def __str__(self):
        return f"{self.event.name} - {self.name}"
    
    def clean(self):
        """Validate price stage data with hybrid pricing validation."""
        super().clean()
        
        if not self.name.strip():
            raise ValidationError({'name': 'Price stage name cannot be empty'})
        
        if self.start_date and self.end_date:
            if self.start_date >= self.end_date:
                raise ValidationError({
                    'end_date': 'End date must be after start date'
                })
        
        if self.modifier_value < 0:
            raise ValidationError({
                'modifier_value': 'Modifier value cannot be negative'
            })
        
        # Validate scope and zone relationship
        if self.scope == self.StageScope.ZONE_SPECIFIC and not self.zone:
            raise ValidationError({
                'zone': 'Zone must be specified for zone-specific stages'
            })
        
        if self.scope == self.StageScope.EVENT_WIDE and self.zone:
            raise ValidationError({
                'zone': 'Zone should not be specified for event-wide stages'
            })
        
        # Validate quantity limit against zone/event capacity
        if self.quantity_limit:
            if self.scope == self.StageScope.ZONE_SPECIFIC and self.zone:
                if self.quantity_limit > self.zone.capacity:
                    raise ValidationError({
                        'quantity_limit': f'Quantity limit cannot exceed zone capacity ({self.zone.capacity})'
                    })
            elif self.scope == self.StageScope.EVENT_WIDE and self.event:
                # Calculate total event capacity
                total_capacity = sum(zone.capacity for zone in self.event.zones.all())
                if total_capacity > 0 and self.quantity_limit > total_capacity:
                    raise ValidationError({
                        'quantity_limit': f'Quantity limit cannot exceed event capacity ({total_capacity})'
                    })
        
        # Validate non-overlapping sequential date ranges within same scope
        if self.event_id and self.start_date and self.end_date:
            overlapping_stages = PriceStage.objects.filter(
                event=self.event,
                is_active=True,
                scope=self.scope
            ).exclude(pk=self.pk)
            
            # For zone-specific stages, only check within the same zone
            if self.scope == self.StageScope.ZONE_SPECIFIC and self.zone:
                overlapping_stages = overlapping_stages.filter(zone=self.zone)
            
            for stage in overlapping_stages:
                if stage.start_date and stage.end_date:
                    # Check for overlap
                    if (self.start_date < stage.end_date and 
                        self.end_date > stage.start_date):
                        scope_desc = f"zone {self.zone.name}" if self.zone else "event"
                        raise ValidationError({
                            'start_date': f'Date range overlaps with "{stage.name}" stage in {scope_desc}',
                            'end_date': f'Date range overlaps with "{stage.name}" stage in {scope_desc}'
                        })
    
    @property
    def is_current(self):
        """Check if this price stage is currently active based on date and quantity."""
        now = timezone.now()
        
        # Check date range
        date_active = (self.is_active and 
                      self.start_date <= now <= self.end_date)
        
        if not date_active:
            return False
        
        # Check quantity limit if specified
        if self.quantity_limit:
            sold_quantity = self.get_sold_quantity()
            if sold_quantity >= self.quantity_limit:
                return False
        
        return True
    
    @property
    def is_upcoming(self):
        """Check if this price stage is upcoming."""
        return self.is_active and timezone.now() < self.start_date
    
    @property
    def is_past(self):
        """Check if this price stage has ended."""
        now = timezone.now()
        
        # Past if date has expired
        if now > self.end_date:
            return True
        
        # Past if quantity limit reached
        if self.quantity_limit:
            sold_quantity = self.get_sold_quantity()
            if sold_quantity >= self.quantity_limit:
                return True
        
        return False
    
    @property
    def remaining_quantity(self):
        """Get remaining quantity available at this stage."""
        if not self.quantity_limit:
            return None
        
        sold_quantity = self.get_sold_quantity()
        return max(0, self.quantity_limit - sold_quantity)
    
    @property
    def days_remaining(self):
        """Get days remaining until stage expires."""
        now = timezone.now()
        if now >= self.end_date:
            return 0
        
        delta = self.end_date - now
        return delta.days
    
    @property
    def hours_remaining(self):
        """Get hours remaining until stage expires."""
        now = timezone.now()
        if now >= self.end_date:
            return 0
        
        delta = self.end_date - now
        return int(delta.total_seconds() / 3600)
    
    def get_sold_quantity(self):
        """Get the number of tickets sold for this stage's scope."""
        # Import here to avoid circular imports
        from venezuelan_pos.apps.sales.models import TransactionItem
        
        if self.scope == self.StageScope.ZONE_SPECIFIC and self.zone:
            # Count tickets sold in this specific zone
            return TransactionItem.objects.filter(
                transaction__event=self.event,
                seat__zone=self.zone,
                transaction__status='completed'
            ).count()
        else:
            # Count tickets sold for entire event
            return TransactionItem.objects.filter(
                transaction__event=self.event,
                transaction__status='completed'
            ).count()
    
    def should_transition(self):
        """Check if this stage should transition to the next stage."""
        if not self.auto_transition:
            return False, None
        
        now = timezone.now()
        
        # Check date expiration
        if now > self.end_date:
            return True, 'date_expired'
        
        # Check quantity limit
        if self.quantity_limit:
            sold_quantity = self.get_sold_quantity()
            if sold_quantity >= self.quantity_limit:
                return True, 'quantity_reached'
        
        return False, None
    
    def get_next_stage(self):
        """Get the next stage in sequence."""
        return PriceStage.objects.filter(
            event=self.event,
            scope=self.scope,
            zone=self.zone,
            stage_order__gt=self.stage_order,
            is_active=True
        ).order_by('stage_order').first()
    
    def calculate_modifier_amount(self, base_price):
        """Calculate the modifier amount for a given base price."""
        if not base_price:
            return Decimal('0.00')
        
        if self.modifier_type == self.ModifierType.PERCENTAGE:
            modifier_decimal = self.modifier_value / 100
            return base_price * modifier_decimal
        else:  # Fixed amount
            return self.modifier_value
    
    def calculate_final_price(self, base_price):
        """Calculate the final price with modifier applied."""
        if not base_price:
            return Decimal('0.00')
        
        modifier_amount = self.calculate_modifier_amount(base_price)
        return base_price + modifier_amount
    
    # Backward compatibility methods
    @property
    def percentage_markup(self):
        """Backward compatibility property."""
        if self.modifier_type == self.ModifierType.PERCENTAGE:
            return self.modifier_value
        return Decimal('0.00')
    
    def calculate_markup_amount(self, base_price):
        """Backward compatibility method."""
        return self.calculate_modifier_amount(base_price)


class StageTransition(TenantAwareModel):
    """
    Audit log for automatic stage transitions.
    Records when and why stages transition for analysis and debugging.
    """
    
    class TriggerReason(models.TextChoices):
        DATE_EXPIRED = 'date_expired', 'Date Expired'
        QUANTITY_REACHED = 'quantity_reached', 'Quantity Limit Reached'
        MANUAL = 'manual', 'Manual Transition'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name='stage_transitions',
        help_text="Event this transition belongs to"
    )
    zone = models.ForeignKey(
        'zones.Zone',
        on_delete=models.CASCADE,
        related_name='stage_transitions',
        null=True,
        blank=True,
        help_text="Zone this transition applies to (null for event-wide)"
    )
    
    # Transition details
    stage_from = models.ForeignKey(
        PriceStage,
        on_delete=models.CASCADE,
        related_name='transitions_from',
        help_text="Stage transitioning from"
    )
    stage_to = models.ForeignKey(
        PriceStage,
        on_delete=models.CASCADE,
        related_name='transitions_to',
        null=True,
        blank=True,
        help_text="Stage transitioning to (null if no next stage)"
    )
    
    # Transition context
    trigger_reason = models.CharField(
        max_length=20,
        choices=TriggerReason.choices,
        help_text="What triggered this transition"
    )
    sold_quantity = models.PositiveIntegerField(
        help_text="Number of tickets sold when transition occurred"
    )
    transition_at = models.DateTimeField(
        default=timezone.now,
        help_text="When the transition occurred"
    )
    
    # Additional metadata
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional transition metadata and context"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'stage_transitions'
        verbose_name = 'Stage Transition'
        verbose_name_plural = 'Stage Transitions'
        ordering = ['-transition_at']
        indexes = [
            models.Index(fields=['tenant', 'event', 'transition_at']),
            models.Index(fields=['tenant', 'zone', 'transition_at']),
            models.Index(fields=['event', 'transition_at']),
            models.Index(fields=['zone', 'transition_at']),
            models.Index(fields=['stage_from', 'transition_at']),
            models.Index(fields=['trigger_reason']),
        ]
    
    def __str__(self):
        scope = f"Zone {self.zone.name}" if self.zone else "Event-wide"
        stage_to_name = self.stage_to.name if self.stage_to else "Final Stage"
        return f"{self.event.name} - {scope}: {self.stage_from.name} → {stage_to_name}"


class StageSales(TenantAwareModel):
    """
    Real-time quantity tracking per stage and zone.
    Tracks sales performance and remaining capacity for each pricing stage.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    stage = models.ForeignKey(
        PriceStage,
        on_delete=models.CASCADE,
        related_name='stage_sales',
        help_text="Price stage this sales record belongs to"
    )
    zone = models.ForeignKey(
        'zones.Zone',
        on_delete=models.CASCADE,
        related_name='stage_sales',
        null=True,
        blank=True,
        help_text="Zone this sales record applies to (null for event-wide stages)"
    )
    
    # Sales tracking
    sales_date = models.DateField(
        default=timezone.now,
        help_text="Date of sales activity"
    )
    tickets_sold = models.PositiveIntegerField(
        default=0,
        help_text="Number of tickets sold on this date"
    )
    revenue_generated = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Revenue generated on this date"
    )
    
    # Real-time tracking
    cumulative_tickets_sold = models.PositiveIntegerField(
        default=0,
        help_text="Total tickets sold for this stage up to this date"
    )
    cumulative_revenue = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Total revenue for this stage up to this date"
    )
    
    # Timestamps
    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'stage_sales'
        verbose_name = 'Stage Sales'
        verbose_name_plural = 'Stage Sales'
        ordering = ['-sales_date']
        unique_together = ['stage', 'zone', 'sales_date']
        indexes = [
            models.Index(fields=['tenant', 'stage', 'sales_date']),
            models.Index(fields=['tenant', 'zone', 'sales_date']),
            models.Index(fields=['stage', 'sales_date']),
            models.Index(fields=['zone', 'sales_date']),
            models.Index(fields=['sales_date']),
        ]
    
    def __str__(self):
        scope = f"Zone {self.zone.name}" if self.zone else "Event-wide"
        return f"{self.stage.name} - {scope} - {self.sales_date}: {self.tickets_sold} tickets"
    
    @classmethod
    def update_sales_for_stage(cls, stage, zone=None, tickets_count=1, revenue_amount=None):
        """
        Update sales tracking for a specific stage and zone.
        Creates or updates the sales record for today.
        """
        from django.db import transaction
        
        today = timezone.now().date()
        
        with transaction.atomic():
            # Get or create today's sales record
            sales_record, created = cls.objects.get_or_create(
                stage=stage,
                zone=zone,
                sales_date=today,
                defaults={
                    'tenant': stage.tenant,
                    'tickets_sold': 0,
                    'revenue_generated': Decimal('0.00'),
                    'cumulative_tickets_sold': 0,
                    'cumulative_revenue': Decimal('0.00'),
                }
            )
            
            # Update daily totals
            sales_record.tickets_sold += tickets_count
            if revenue_amount:
                sales_record.revenue_generated += revenue_amount
            
            # Calculate cumulative totals
            previous_records = cls.objects.filter(
                stage=stage,
                zone=zone,
                sales_date__lt=today
            ).aggregate(
                total_tickets=models.Sum('tickets_sold'),
                total_revenue=models.Sum('revenue_generated')
            )
            
            sales_record.cumulative_tickets_sold = (
                (previous_records['total_tickets'] or 0) + sales_record.tickets_sold
            )
            sales_record.cumulative_revenue = (
                (previous_records['total_revenue'] or Decimal('0.00')) + sales_record.revenue_generated
            )
            
            sales_record.save()
            
            return sales_record
    
    @classmethod
    def get_stage_totals(cls, stage, zone=None):
        """Get total sales for a stage across all dates."""
        queryset = cls.objects.filter(stage=stage)
        if zone:
            queryset = queryset.filter(zone=zone)
        
        totals = queryset.aggregate(
            total_tickets=models.Sum('tickets_sold'),
            total_revenue=models.Sum('revenue_generated')
        )
        
        return {
            'tickets_sold': totals['total_tickets'] or 0,
            'revenue_generated': totals['total_revenue'] or Decimal('0.00')
        }


class RowPricing(TenantAwareModel):
    """
    Row-specific pricing modifiers within numbered zones.
    Supports percentage markups based on row position.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    zone = models.ForeignKey(
        'zones.Zone',
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
            models.Index(fields=['tenant', 'zone', 'is_active']),
            models.Index(fields=['zone', 'row_number']),
            models.Index(fields=['is_active']),
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
        
        if zone and zone.zone_type != zone.ZoneType.NUMBERED:
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
        'zones.Zone',
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
            models.Index(fields=['tenant', 'event', 'calculation_date']),
            models.Index(fields=['tenant', 'zone', 'calculation_date']),
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