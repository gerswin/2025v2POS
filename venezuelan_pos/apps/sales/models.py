import uuid
from decimal import Decimal
from django.db import models, transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db.models import F, Q
from venezuelan_pos.apps.tenants.models import TenantAwareModel
from venezuelan_pos.apps.events.models import Event
from venezuelan_pos.apps.zones.models import Zone, Seat
from venezuelan_pos.apps.customers.models import Customer


class FiscalSeriesManager(models.Manager):
    """Manager for fiscal series with consecutive numbering."""
    
    def get_next_series(self, tenant, event=None):
        """
        Get the next consecutive fiscal series number for a tenant.
        Uses select_for_update to prevent race conditions.
        """
        with transaction.atomic():
            # Get or create fiscal series counter for tenant
            # Use the base manager to avoid tenant filtering issues
            series_counter, created = self.model._base_manager.select_for_update().get_or_create(
                tenant=tenant,
                event=event,
                defaults={'current_series': 0}
            )
            
            # Increment and save
            series_counter.current_series = F('current_series') + 1
            series_counter.save(update_fields=['current_series'])
            
            # Refresh to get the actual value
            series_counter.refresh_from_db()
            
            # Format series number with tenant prefix if available
            prefix = tenant.fiscal_series_prefix or ''
            series_number = f"{prefix}{series_counter.current_series:08d}"
            
            return series_number


class FiscalSeriesCounter(TenantAwareModel):
    """
    Counter for consecutive fiscal series numbering.
    Ensures unique consecutive numbering per tenant and optionally per event.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='fiscal_counters',
        help_text="Event for series counter (null for global tenant counter)"
    )
    
    # Current series number
    current_series = models.PositiveIntegerField(
        default=0,
        help_text="Current fiscal series number"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    objects = FiscalSeriesManager()
    
    class Meta:
        db_table = 'fiscal_series_counters'
        verbose_name = 'Fiscal Series Counter'
        verbose_name_plural = 'Fiscal Series Counters'
        unique_together = ['tenant', 'event']
        indexes = [
            models.Index(fields=['tenant', 'event']),
        ]
    
    def __str__(self):
        if self.event:
            return f"{self.tenant.name} - {self.event.name}: {self.current_series}"
        return f"{self.tenant.name} - Global: {self.current_series}"


class TransactionManager(models.Manager):
    """Manager for Transaction model with business logic."""
    
    def create_transaction(self, tenant, event, customer, items_data, **kwargs):
        """
        Create a new transaction with items.
        Handles fiscal series generation and validation.
        """
        with transaction.atomic():
            # Create transaction without fiscal series first
            transaction_obj = self.create(
                tenant=tenant,
                event=event,
                customer=customer,
                status=Transaction.Status.PENDING,
                **kwargs
            )
            
            # Create transaction items
            total_amount = Decimal('0.00')
            for item_data in items_data:
                item = TransactionItem.objects.create(
                    tenant=tenant,
                    transaction=transaction_obj,
                    **item_data
                )
                total_amount += item.total_price
            
            # Update transaction total
            transaction_obj.total_amount = total_amount
            transaction_obj.save(update_fields=['total_amount'])
            
            return transaction_obj
    
    def complete_transaction(self, transaction_obj):
        """
        Complete a transaction by generating fiscal series.
        Only called when payment is fully completed.
        """
        with transaction.atomic():
            if transaction_obj.status == Transaction.Status.COMPLETED:
                return transaction_obj
            
            # Generate fiscal series
            fiscal_series = FiscalSeriesCounter.objects.get_next_series(
                tenant=transaction_obj.tenant,
                event=transaction_obj.event
            )
            
            # Update transaction
            transaction_obj.fiscal_series = fiscal_series
            transaction_obj.status = Transaction.Status.COMPLETED
            transaction_obj.completed_at = timezone.now()
            transaction_obj.save(update_fields=['fiscal_series', 'status', 'completed_at'])
            
            # Update seat statuses to SOLD
            for item in transaction_obj.items.all():
                if item.seat:
                    item.seat.status = Seat.Status.SOLD
                    item.seat.save(update_fields=['status'])
            
            return transaction_obj


class Transaction(TenantAwareModel):
    """
    Main transaction model for ticket sales.
    Represents a complete purchase transaction with fiscal compliance.
    """
    
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        RESERVED = 'reserved', 'Reserved (Partial Payment)'
        COMPLETED = 'completed', 'Completed'
        CANCELLED = 'cancelled', 'Cancelled'
        REFUNDED = 'refunded', 'Refunded'
    
    class TransactionType(models.TextChoices):
        ONLINE = 'online', 'Online Sale'
        OFFLINE = 'offline', 'Offline Sale'
        PARTIAL_PAYMENT = 'partial_payment', 'Partial Payment'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Relationships
    event = models.ForeignKey(
        Event,
        on_delete=models.PROTECT,
        related_name='transactions',
        help_text="Event this transaction is for"
    )
    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        related_name='transactions',
        help_text="Customer who made the purchase"
    )
    
    # Fiscal information
    fiscal_series = models.CharField(
        max_length=20,
        unique=True,
        null=True,
        blank=True,
        help_text="Consecutive fiscal series number (generated on completion)"
    )
    
    # Transaction details
    transaction_type = models.CharField(
        max_length=20,
        choices=TransactionType.choices,
        default=TransactionType.ONLINE,
        help_text="Type of transaction"
    )
    
    # Amounts
    subtotal_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Subtotal before taxes"
    )
    tax_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Total tax amount"
    )
    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Total transaction amount"
    )
    
    # Currency
    currency = models.CharField(
        max_length=3,
        default='USD',
        help_text="Transaction currency"
    )
    exchange_rate = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        default=Decimal('1.0000'),
        help_text="Exchange rate used for conversion"
    )
    
    # Status and timing
    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.PENDING,
        help_text="Current transaction status"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When transaction was completed"
    )
    updated_at = models.DateTimeField(auto_now=True)
    
    # Offline sync information
    offline_block_id = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text="Offline block ID for offline transactions"
    )
    sync_status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending Sync'),
            ('synced', 'Synced'),
            ('conflict', 'Sync Conflict'),
        ],
        default='synced',
        help_text="Synchronization status for offline transactions"
    )
    
    # Additional data
    notes = models.TextField(
        blank=True,
        help_text="Additional transaction notes"
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional transaction metadata"
    )
    
    objects = TransactionManager()
    
    class Meta:
        db_table = 'transactions'
        verbose_name = 'Transaction'
        verbose_name_plural = 'Transactions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', 'event', 'status']),
            models.Index(fields=['tenant', 'customer']),
            models.Index(fields=['fiscal_series']),
            models.Index(fields=['created_at']),
            models.Index(fields=['offline_block_id']),
        ]
    
    def __str__(self):
        if self.fiscal_series:
            return f"Transaction {self.fiscal_series} - {self.customer.full_name}"
        return f"Transaction {self.id} - {self.customer.full_name} (Pending)"
    
    def clean(self):
        """Validate transaction data."""
        super().clean()
        
        if self.total_amount < 0:
            raise ValidationError({'total_amount': 'Total amount cannot be negative'})
        
        if self.subtotal_amount < 0:
            raise ValidationError({'subtotal_amount': 'Subtotal amount cannot be negative'})
        
        if self.tax_amount < 0:
            raise ValidationError({'tax_amount': 'Tax amount cannot be negative'})
        
        if self.exchange_rate <= 0:
            raise ValidationError({'exchange_rate': 'Exchange rate must be positive'})
        
        # Validate fiscal series uniqueness
        if self.fiscal_series:
            existing = Transaction.objects.filter(
                fiscal_series=self.fiscal_series
            ).exclude(pk=self.pk)
            if existing.exists():
                raise ValidationError({
                    'fiscal_series': 'Fiscal series must be unique'
                })
    
    @property
    def is_completed(self):
        """Check if transaction is completed."""
        return self.status == self.Status.COMPLETED
    
    @property
    def is_pending(self):
        """Check if transaction is pending."""
        return self.status == self.Status.PENDING
    
    @property
    def is_reserved(self):
        """Check if transaction is reserved (partial payment)."""
        return self.status == self.Status.RESERVED
    
    @property
    def ticket_count(self):
        """Get total number of tickets in this transaction."""
        return self.items.count()
    
    def calculate_totals(self):
        """Recalculate transaction totals based on items."""
        items = self.items.all()
        
        subtotal = sum(item.subtotal_price for item in items)
        tax_total = sum(item.tax_amount for item in items)
        total = sum(item.total_price for item in items)
        
        self.subtotal_amount = subtotal
        self.tax_amount = tax_total
        self.total_amount = total
        
        return {
            'subtotal': subtotal,
            'tax': tax_total,
            'total': total
        }
    
    def can_be_completed(self):
        """Check if transaction can be completed."""
        return self.status in [self.Status.PENDING, self.Status.RESERVED]
    
    def complete(self):
        """Complete the transaction."""
        if not self.can_be_completed():
            raise ValidationError("Transaction cannot be completed in current status")
        
        return Transaction.objects.complete_transaction(self)


class TransactionItem(TenantAwareModel):
    """
    Individual ticket items within a transaction.
    Represents each ticket purchased in the transaction.
    """
    
    class ItemType(models.TextChoices):
        GENERAL_ADMISSION = 'general_admission', 'General Admission'
        NUMBERED_SEAT = 'numbered_seat', 'Numbered Seat'
        TABLE = 'table', 'Table'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Relationships
    transaction = models.ForeignKey(
        Transaction,
        on_delete=models.CASCADE,
        related_name='items',
        help_text="Transaction this item belongs to"
    )
    zone = models.ForeignKey(
        Zone,
        on_delete=models.PROTECT,
        related_name='transaction_items',
        help_text="Zone for this ticket"
    )
    seat = models.ForeignKey(
        Seat,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='transaction_items',
        help_text="Specific seat (for numbered zones only)"
    )
    
    # Item details
    item_type = models.CharField(
        max_length=20,
        choices=ItemType.choices,
        default=ItemType.GENERAL_ADMISSION,
        help_text="Type of ticket item"
    )
    quantity = models.PositiveIntegerField(
        default=1,
        help_text="Number of tickets (for general admission)"
    )
    
    # Pricing
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Price per unit before taxes"
    )
    subtotal_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Subtotal (unit_price * quantity)"
    )
    tax_rate = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=Decimal('0.0000'),
        help_text="Tax rate applied (as decimal, e.g., 0.1600 for 16%)"
    )
    tax_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Tax amount for this item"
    )
    total_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Total price including taxes"
    )
    
    # Additional data
    description = models.CharField(
        max_length=255,
        blank=True,
        help_text="Item description"
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional item metadata"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'transaction_items'
        verbose_name = 'Transaction Item'
        verbose_name_plural = 'Transaction Items'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['tenant', 'transaction']),
            models.Index(fields=['zone']),
            models.Index(fields=['seat']),
        ]
    
    def __str__(self):
        if self.seat:
            return f"{self.zone.name} - {self.seat.seat_label}"
        return f"{self.zone.name} - General Admission (x{self.quantity})"
    
    def clean(self):
        """Validate transaction item data."""
        super().clean()
        
        if self.unit_price < 0:
            raise ValidationError({'unit_price': 'Unit price cannot be negative'})
        
        if self.quantity <= 0:
            raise ValidationError({'quantity': 'Quantity must be positive'})
        
        if self.tax_rate < 0:
            raise ValidationError({'tax_rate': 'Tax rate cannot be negative'})
        
        # Validate seat assignment for numbered zones
        if self.zone and self.zone.zone_type == Zone.ZoneType.NUMBERED:
            if not self.seat:
                raise ValidationError({'seat': 'Numbered zones require seat assignment'})
            if self.seat.zone != self.zone:
                raise ValidationError({'seat': 'Seat must belong to the same zone'})
            if self.quantity != 1:
                raise ValidationError({'quantity': 'Numbered seat items must have quantity of 1'})
        
        # Validate general admission
        if self.zone and self.zone.zone_type == Zone.ZoneType.GENERAL:
            if self.seat:
                raise ValidationError({'seat': 'General zones cannot have seat assignment'})
    
    def save(self, *args, **kwargs):
        """Override save to calculate prices."""
        # Calculate subtotal
        self.subtotal_price = self.unit_price * self.quantity
        
        # Calculate tax amount
        self.tax_amount = self.subtotal_price * self.tax_rate
        
        # Calculate total
        self.total_price = self.subtotal_price + self.tax_amount
        
        super().save(*args, **kwargs)
    
    @property
    def is_numbered_seat(self):
        """Check if this is a numbered seat item."""
        return self.item_type == self.ItemType.NUMBERED_SEAT
    
    @property
    def is_general_admission(self):
        """Check if this is a general admission item."""
        return self.item_type == self.ItemType.GENERAL_ADMISSION


class ReservedTicket(TenantAwareModel):
    """
    Reserved ticket model for partial payment holds.
    Temporarily holds seats during the partial payment process.
    """
    
    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        EXPIRED = 'expired', 'Expired'
        COMPLETED = 'completed', 'Completed'
        CANCELLED = 'cancelled', 'Cancelled'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Relationships
    transaction = models.ForeignKey(
        Transaction,
        on_delete=models.CASCADE,
        related_name='reserved_tickets',
        help_text="Transaction this reservation belongs to"
    )
    seat = models.ForeignKey(
        Seat,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='reservations',
        help_text="Reserved seat (for numbered zones)"
    )
    zone = models.ForeignKey(
        Zone,
        on_delete=models.CASCADE,
        related_name='reservations',
        help_text="Zone for this reservation"
    )
    
    # Reservation details
    quantity = models.PositiveIntegerField(
        default=1,
        help_text="Number of reserved tickets (for general admission)"
    )
    
    # Timing
    reserved_until = models.DateTimeField(
        help_text="When this reservation expires"
    )
    
    # Status
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.ACTIVE,
        help_text="Current reservation status"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'reserved_tickets'
        verbose_name = 'Reserved Ticket'
        verbose_name_plural = 'Reserved Tickets'
        ordering = ['reserved_until']
        indexes = [
            models.Index(fields=['tenant', 'status', 'reserved_until']),
            models.Index(fields=['transaction']),
            models.Index(fields=['seat']),
            models.Index(fields=['zone']),
        ]
    
    def __str__(self):
        if self.seat:
            return f"Reserved: {self.seat.seat_label} until {self.reserved_until}"
        return f"Reserved: {self.zone.name} (x{self.quantity}) until {self.reserved_until}"
    
    def clean(self):
        """Validate reservation data."""
        super().clean()
        
        if self.quantity <= 0:
            raise ValidationError({'quantity': 'Quantity must be positive'})
        
        if self.reserved_until <= timezone.now():
            raise ValidationError({'reserved_until': 'Reservation must be in the future'})
        
        # Validate seat assignment for numbered zones
        if self.zone and self.zone.zone_type == Zone.ZoneType.NUMBERED:
            if not self.seat:
                raise ValidationError({'seat': 'Numbered zones require seat assignment'})
            if self.seat.zone != self.zone:
                raise ValidationError({'seat': 'Seat must belong to the same zone'})
            if self.quantity != 1:
                raise ValidationError({'quantity': 'Numbered seat reservations must have quantity of 1'})
        
        # Validate general admission
        if self.zone and self.zone.zone_type == Zone.ZoneType.GENERAL:
            if self.seat:
                raise ValidationError({'seat': 'General zones cannot have seat assignment'})
    
    @property
    def is_active(self):
        """Check if reservation is still active."""
        return (
            self.status == self.Status.ACTIVE and
            self.reserved_until > timezone.now()
        )
    
    @property
    def is_expired(self):
        """Check if reservation has expired."""
        return (
            self.status == self.Status.ACTIVE and
            self.reserved_until <= timezone.now()
        )
    
    def expire(self):
        """Mark reservation as expired and release seat."""
        with transaction.atomic():
            self.status = self.Status.EXPIRED
            self.save(update_fields=['status'])
            
            # Release seat if it's a numbered seat
            if self.seat:
                self.seat.status = Seat.Status.AVAILABLE
                self.seat.save(update_fields=['status'])
    
    def complete(self):
        """Mark reservation as completed."""
        self.status = self.Status.COMPLETED
        self.save(update_fields=['status'])
    
    def cancel(self):
        """Cancel reservation and release seat."""
        with transaction.atomic():
            self.status = self.Status.CANCELLED
            self.save(update_fields=['status'])
            
            # Release seat if it's a numbered seat
            if self.seat:
                self.seat.status = Seat.Status.AVAILABLE
                self.seat.save(update_fields=['status'])


class OfflineBlock(TenantAwareModel):
    """
    Offline block model for pre-assigned series numbers.
    Manages blocks of 50 consecutive series for offline operation.
    """
    
    class Status(models.TextChoices):
        ASSIGNED = 'assigned', 'Assigned'
        ACTIVE = 'active', 'Active'
        EXPIRED = 'expired', 'Expired'
        SYNCED = 'synced', 'Synced'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Block identification
    block_id = models.CharField(
        max_length=50,
        unique=True,
        help_text="Unique block identifier"
    )
    
    # Series range
    start_series = models.PositiveIntegerField(
        help_text="Starting series number for this block"
    )
    end_series = models.PositiveIntegerField(
        help_text="Ending series number for this block"
    )
    current_series = models.PositiveIntegerField(
        help_text="Current series number being used"
    )
    
    # Assignment details
    assigned_to = models.CharField(
        max_length=255,
        help_text="Terminal or user this block is assigned to"
    )
    
    # Timing
    assigned_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(
        help_text="When this block expires (8 hours from assignment)"
    )
    
    # Status
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.ASSIGNED,
        help_text="Current block status"
    )
    
    # Sync information
    synced_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this block was synced"
    )
    
    # Metadata
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional block metadata"
    )
    
    class Meta:
        db_table = 'offline_blocks'
        verbose_name = 'Offline Block'
        verbose_name_plural = 'Offline Blocks'
        ordering = ['-assigned_at']
        indexes = [
            models.Index(fields=['tenant', 'status']),
            models.Index(fields=['block_id']),
            models.Index(fields=['assigned_to']),
            models.Index(fields=['expires_at']),
        ]
    
    def __str__(self):
        return f"Block {self.block_id} ({self.start_series}-{self.end_series}) - {self.assigned_to}"
    
    def clean(self):
        """Validate offline block data."""
        super().clean()
        
        if self.start_series >= self.end_series:
            raise ValidationError({'end_series': 'End series must be greater than start series'})
        
        if self.current_series < self.start_series or self.current_series > self.end_series:
            raise ValidationError({
                'current_series': 'Current series must be within block range'
            })
        
        # Validate block size (should be 50)
        block_size = self.end_series - self.start_series + 1
        if block_size != 50:
            raise ValidationError({
                'end_series': 'Offline blocks must contain exactly 50 series numbers'
            })
    
    @property
    def is_active(self):
        """Check if block is still active."""
        return (
            self.status == self.Status.ACTIVE and
            self.expires_at > timezone.now()
        )
    
    @property
    def is_expired(self):
        """Check if block has expired."""
        return (
            self.status == self.Status.ACTIVE and
            self.expires_at <= timezone.now()
        )
    
    @property
    def remaining_series(self):
        """Get number of remaining series in this block."""
        return self.end_series - self.current_series
    
    @property
    def used_series(self):
        """Get number of used series in this block."""
        return self.current_series - self.start_series
    
    def get_next_series(self):
        """Get the next series number from this block."""
        if not self.is_active:
            raise ValidationError("Block is not active")
        
        if self.current_series >= self.end_series:
            raise ValidationError("Block is exhausted")
        
        with transaction.atomic():
            # Increment current series
            self.current_series = F('current_series') + 1
            self.save(update_fields=['current_series'])
            
            # Refresh to get actual value
            self.refresh_from_db()
            
            # Format series number with tenant prefix
            prefix = self.tenant.fiscal_series_prefix or ''
            series_number = f"{prefix}{self.current_series:08d}"
            
            return series_number
    
    def expire(self):
        """Mark block as expired."""
        self.status = self.Status.EXPIRED
        self.save(update_fields=['status'])
    
    def sync_complete(self):
        """Mark block as synced."""
        self.status = self.Status.SYNCED
        self.synced_at = timezone.now()
        self.save(update_fields=['status', 'synced_at'])
    
    @classmethod
    def create_block(cls, tenant, assigned_to, start_series=None):
        """Create a new offline block."""
        from datetime import timedelta
        
        if start_series is None:
            # Get next available series range
            last_block = cls.objects.filter(tenant=tenant).order_by('-end_series').first()
            start_series = (last_block.end_series + 1) if last_block else 1
        
        end_series = start_series + 49  # Block of 50
        block_id = f"{tenant.slug}-{start_series:08d}"
        expires_at = timezone.now() + timedelta(hours=8)
        
        return cls.objects.create(
            tenant=tenant,
            block_id=block_id,
            start_series=start_series,
            end_series=end_series,
            current_series=start_series - 1,  # Start before first number
            assigned_to=assigned_to,
            expires_at=expires_at,
            status=cls.Status.ACTIVE
        )