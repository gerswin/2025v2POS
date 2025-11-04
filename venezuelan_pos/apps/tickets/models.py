import uuid
import qrcode
import hashlib
import secrets
from io import BytesIO
from decimal import Decimal
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.core.files.base import ContentFile
from django.conf import settings
from cryptography.fernet import Fernet
import base64
import json
from venezuelan_pos.apps.tenants.models import TenantAwareModel
from venezuelan_pos.apps.sales.models import Transaction, TransactionItem
from venezuelan_pos.apps.events.models import Event
from venezuelan_pos.apps.customers.models import Customer


class DigitalTicketManager(models.Manager):
    """Manager for DigitalTicket model with business logic."""
    
    def generate_for_transaction(self, transaction):
        """
        Generate digital tickets for all items in a completed transaction.
        Only creates tickets for completed transactions with fiscal series.
        """
        if not transaction.is_completed or not transaction.fiscal_series:
            raise ValidationError("Can only generate tickets for completed transactions")
        
        tickets = []
        for item in transaction.items.all():
            # Generate individual tickets based on quantity
            for i in range(item.quantity):
                ticket = self.create_ticket_for_item(transaction, item, i + 1)
                tickets.append(ticket)
        
        return tickets
    
    def create_ticket_for_item(self, transaction, item, sequence_number=1):
        """Create a single digital ticket for a transaction item."""
        # Generate unique ticket number
        ticket_number = self._generate_ticket_number(transaction, item, sequence_number)
        
        # Create the ticket
        ticket = self.create(
            tenant=transaction.tenant,
            transaction=transaction,
            transaction_item=item,
            event=transaction.event,
            customer=transaction.customer,
            ticket_number=ticket_number,
            sequence_number=sequence_number,
            zone=item.zone,
            seat=item.seat,
            ticket_type=self._determine_ticket_type(item),
            unit_price=item.unit_price,
            total_price=item.total_price / item.quantity,  # Price per ticket
            currency=transaction.currency,
            status=DigitalTicket.Status.ACTIVE
        )
        
        # Generate QR code after creation
        ticket.generate_qr_code()
        
        return ticket
    
    def _generate_ticket_number(self, transaction, item, sequence_number):
        """Generate unique ticket number."""
        # Format: FISCAL_SERIES-ITEM_INDEX-SEQUENCE
        item_index = list(transaction.items.all()).index(item) + 1
        return f"{transaction.fiscal_series}-{item_index:02d}-{sequence_number:02d}"
    
    def _determine_ticket_type(self, item):
        """Determine ticket type based on transaction item."""
        if item.seat:
            return DigitalTicket.TicketType.NUMBERED_SEAT
        elif item.zone.zone_type == 'general':
            return DigitalTicket.TicketType.GENERAL_ADMISSION
        else:
            return DigitalTicket.TicketType.GENERAL_ADMISSION


class DigitalTicket(TenantAwareModel):
    """
    Digital ticket model with QR code generation and validation.
    Represents individual tickets with encrypted validation data.
    """
    
    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        USED = 'used', 'Used'
        EXPIRED = 'expired', 'Expired'
        CANCELLED = 'cancelled', 'Cancelled'
        REFUNDED = 'refunded', 'Refunded'
    
    class TicketType(models.TextChoices):
        GENERAL_ADMISSION = 'general_admission', 'General Admission'
        NUMBERED_SEAT = 'numbered_seat', 'Numbered Seat'
        MULTI_ENTRY = 'multi_entry', 'Multi Entry'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Relationships
    transaction = models.ForeignKey(
        Transaction,
        on_delete=models.PROTECT,
        related_name='digital_tickets',
        help_text="Transaction this ticket belongs to"
    )
    transaction_item = models.ForeignKey(
        TransactionItem,
        on_delete=models.PROTECT,
        related_name='digital_tickets',
        help_text="Specific transaction item this ticket represents"
    )
    event = models.ForeignKey(
        Event,
        on_delete=models.PROTECT,
        related_name='digital_tickets',
        help_text="Event this ticket is for"
    )
    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        related_name='digital_tickets',
        help_text="Customer who owns this ticket"
    )
    
    # Ticket identification
    ticket_number = models.CharField(
        max_length=50,
        unique=True,
        help_text="Unique ticket number"
    )
    sequence_number = models.PositiveIntegerField(
        default=1,
        help_text="Sequence number for multiple tickets from same item"
    )
    
    # Ticket details
    ticket_type = models.CharField(
        max_length=20,
        choices=TicketType.choices,
        default=TicketType.GENERAL_ADMISSION,
        help_text="Type of ticket"
    )
    
    # Seating information (from transaction item)
    zone = models.ForeignKey(
        'zones.Zone',
        on_delete=models.PROTECT,
        related_name='digital_tickets',
        help_text="Zone for this ticket"
    )
    seat = models.ForeignKey(
        'zones.Seat',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='digital_tickets',
        help_text="Specific seat (for numbered tickets only)"
    )
    
    # Pricing information
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Original unit price for this ticket"
    )
    total_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Total price for this individual ticket"
    )
    currency = models.CharField(
        max_length=3,
        default='USD',
        help_text="Currency for pricing"
    )
    
    # QR Code and validation
    qr_code_data = models.TextField(
        blank=True,
        help_text="Encrypted QR code data for validation"
    )
    qr_code_image = models.ImageField(
        upload_to='tickets/qr_codes/',
        blank=True,
        null=True,
        help_text="Generated QR code image"
    )
    validation_hash = models.CharField(
        max_length=64,
        blank=True,
        help_text="SHA-256 hash for ticket validation"
    )
    
    # Usage tracking
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.ACTIVE,
        help_text="Current ticket status"
    )
    usage_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of times ticket has been used"
    )
    max_usage_count = models.PositiveIntegerField(
        default=1,
        help_text="Maximum number of times ticket can be used"
    )
    
    # Validity period
    valid_from = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When ticket becomes valid (defaults to event start)"
    )
    valid_until = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When ticket expires (defaults to event end)"
    )
    
    # Usage history
    first_used_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When ticket was first used"
    )
    last_used_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When ticket was last used"
    )
    
    # Additional data
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional ticket metadata"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    objects = DigitalTicketManager()
    
    class Meta:
        db_table = 'digital_tickets'
        verbose_name = 'Digital Ticket'
        verbose_name_plural = 'Digital Tickets'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', 'event', 'status']),
            models.Index(fields=['tenant', 'customer']),
            models.Index(fields=['ticket_number']),
            models.Index(fields=['validation_hash']),
            models.Index(fields=['transaction']),
        ]
    
    def __str__(self):
        if self.seat:
            return f"Ticket {self.ticket_number} - {self.zone.name} {self.seat.seat_label}"
        return f"Ticket {self.ticket_number} - {self.zone.name}"
    
    def clean(self):
        """Validate digital ticket data."""
        super().clean()
        
        if self.usage_count > self.max_usage_count:
            raise ValidationError({
                'usage_count': 'Usage count cannot exceed maximum usage count'
            })
        
        if self.valid_from and self.valid_until:
            if self.valid_from >= self.valid_until:
                raise ValidationError({
                    'valid_until': 'Valid until must be after valid from'
                })
        
        # Validate seat assignment for numbered tickets
        if self.ticket_type == self.TicketType.NUMBERED_SEAT:
            if not self.seat:
                raise ValidationError({
                    'seat': 'Numbered seat tickets must have seat assignment'
                })
        
        # Validate general admission tickets don't have seats
        if self.ticket_type == self.TicketType.GENERAL_ADMISSION:
            if self.seat:
                raise ValidationError({
                    'seat': 'General admission tickets cannot have seat assignment'
                })
    
    def save(self, *args, **kwargs):
        """Override save to set default validity periods."""
        # Set default validity periods from event
        if not self.valid_from:
            self.valid_from = self.event.start_date
        if not self.valid_until:
            self.valid_until = self.event.end_date
        
        super().save(*args, **kwargs)
    
    def generate_qr_code(self):
        """Generate QR code with encrypted validation data."""
        # Create validation data
        validation_data = {
            'ticket_id': str(self.id),
            'ticket_number': self.ticket_number,
            'event_id': str(self.event.id),
            'customer_id': str(self.customer.id),
            'zone_id': str(self.zone.id),
            'seat_id': str(self.seat.id) if self.seat else None,
            'valid_from': self.valid_from.isoformat() if self.valid_from else None,
            'valid_until': self.valid_until.isoformat() if self.valid_until else None,
            'max_usage': self.max_usage_count,
            'created_at': self.created_at.isoformat(),
        }
        
        # Encrypt the data
        encrypted_data = self._encrypt_validation_data(validation_data)
        self.qr_code_data = encrypted_data
        
        # Generate validation hash
        self.validation_hash = hashlib.sha256(
            f"{self.ticket_number}{self.event.id}{self.customer.id}".encode()
        ).hexdigest()
        
        # Generate QR code image
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(encrypted_data)
        qr.make(fit=True)
        
        # Create QR code image
        qr_image = qr.make_image(fill_color="black", back_color="white")
        
        # Save to ImageField
        buffer = BytesIO()
        qr_image.save(buffer, format='PNG')
        buffer.seek(0)
        
        filename = f"qr_{self.ticket_number}.png"
        self.qr_code_image.save(
            filename,
            ContentFile(buffer.getvalue()),
            save=False
        )
        
        # Save the model with updated QR data
        self.save(update_fields=['qr_code_data', 'validation_hash', 'qr_code_image'])
    
    def _encrypt_validation_data(self, data):
        """Encrypt validation data for QR code."""
        # Get or create encryption key (in production, this should be in settings)
        key = getattr(settings, 'TICKET_ENCRYPTION_KEY', None)
        if not key:
            # Generate a key for development (should be in settings for production)
            key = Fernet.generate_key()
        
        if isinstance(key, str):
            key = key.encode()
        
        fernet = Fernet(key)
        json_data = json.dumps(data, sort_keys=True)
        encrypted = fernet.encrypt(json_data.encode())
        return base64.b64encode(encrypted).decode()
    
    def decrypt_validation_data(self):
        """Decrypt validation data from QR code."""
        if not self.qr_code_data:
            return None
        
        try:
            key = getattr(settings, 'TICKET_ENCRYPTION_KEY', None)
            if not key:
                return None
            
            if isinstance(key, str):
                key = key.encode()
            
            fernet = Fernet(key)
            encrypted_data = base64.b64decode(self.qr_code_data.encode())
            decrypted = fernet.decrypt(encrypted_data)
            return json.loads(decrypted.decode())
        except Exception:
            return None
    
    @property
    def is_valid(self):
        """Check if ticket is currently valid."""
        now = timezone.now()
        
        # Check status
        if self.status != self.Status.ACTIVE:
            return False
        
        # Check validity period
        if self.valid_from and now < self.valid_from:
            return False
        if self.valid_until and now > self.valid_until:
            return False
        
        # Check usage count
        if self.usage_count >= self.max_usage_count:
            return False
        
        return True
    
    @property
    def can_be_used(self):
        """Check if ticket can be used (validated)."""
        return self.is_valid and self.usage_count < self.max_usage_count
    
    @property
    def remaining_uses(self):
        """Get remaining number of uses for this ticket."""
        return max(0, self.max_usage_count - self.usage_count)
    
    @property
    def seat_label(self):
        """Get seat label for display."""
        if self.seat:
            return self.seat.seat_label
        return f"{self.zone.name} - General Admission"
    
    def validate_and_use(self, validation_system_id=None):
        """
        Validate and mark ticket as used.
        Returns validation result and updates usage count.
        """
        if not self.can_be_used:
            return {
                'valid': False,
                'reason': 'Ticket cannot be used',
                'status': self.status,
                'usage_count': self.usage_count,
                'max_usage': self.max_usage_count
            }
        
        # Mark as used
        self.usage_count += 1
        if not self.first_used_at:
            self.first_used_at = timezone.now()
        self.last_used_at = timezone.now()
        
        # Update status if fully used
        if self.usage_count >= self.max_usage_count:
            self.status = self.Status.USED
        
        self.save(update_fields=[
            'usage_count', 'first_used_at', 'last_used_at', 'status'
        ])
        
        # Log validation
        TicketValidationLog.objects.create(
            tenant=self.tenant,
            ticket=self,
            validation_system_id=validation_system_id or 'unknown',
            validation_result=True,
            usage_count_after=self.usage_count
        )
        
        return {
            'valid': True,
            'ticket_number': self.ticket_number,
            'customer_name': self.customer.full_name,
            'event_name': self.event.name,
            'seat_label': self.seat_label,
            'usage_count': self.usage_count,
            'max_usage': self.max_usage_count,
            'remaining_uses': self.remaining_uses
        }
    
    def check_validation_only(self):
        """Check validation without marking as used."""
        return {
            'valid': self.can_be_used,
            'ticket_number': self.ticket_number,
            'customer_name': self.customer.full_name,
            'event_name': self.event.name,
            'seat_label': self.seat_label,
            'status': self.status,
            'usage_count': self.usage_count,
            'max_usage': self.max_usage_count,
            'remaining_uses': self.remaining_uses,
            'valid_from': self.valid_from,
            'valid_until': self.valid_until
        }


class TicketTemplate(TenantAwareModel):
    """
    Ticket template system for customizable layouts.
    Allows tenants to customize the appearance of their digital tickets.
    """
    
    class TemplateType(models.TextChoices):
        PDF = 'pdf', 'PDF Template'
        EMAIL = 'email', 'Email Template'
        MOBILE = 'mobile', 'Mobile Template'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Template identification
    name = models.CharField(
        max_length=255,
        help_text="Template name"
    )
    template_type = models.CharField(
        max_length=10,
        choices=TemplateType.choices,
        default=TemplateType.PDF,
        help_text="Type of template"
    )
    
    # Template content
    html_content = models.TextField(
        help_text="HTML template content with placeholders"
    )
    css_styles = models.TextField(
        blank=True,
        help_text="CSS styles for the template"
    )
    
    # Template configuration
    page_size = models.CharField(
        max_length=10,
        choices=[
            ('A4', 'A4'),
            ('Letter', 'Letter'),
            ('A5', 'A5'),
            ('Custom', 'Custom'),
        ],
        default='A4',
        help_text="Page size for PDF templates"
    )
    orientation = models.CharField(
        max_length=10,
        choices=[
            ('portrait', 'Portrait'),
            ('landscape', 'Landscape'),
        ],
        default='portrait',
        help_text="Page orientation"
    )
    
    # Template settings
    include_qr_code = models.BooleanField(
        default=True,
        help_text="Include QR code in template"
    )
    include_barcode = models.BooleanField(
        default=False,
        help_text="Include barcode in template"
    )
    include_logo = models.BooleanField(
        default=True,
        help_text="Include tenant logo in template"
    )
    
    # Status
    is_active = models.BooleanField(
        default=True,
        help_text="Whether template is active"
    )
    is_default = models.BooleanField(
        default=False,
        help_text="Whether this is the default template for the tenant"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'ticket_templates'
        verbose_name = 'Ticket Template'
        verbose_name_plural = 'Ticket Templates'
        ordering = ['name']
        unique_together = ['tenant', 'name', 'template_type']
    
    def __str__(self):
        return f"{self.name} ({self.template_type})"
    
    def clean(self):
        """Validate ticket template."""
        super().clean()
        
        if not self.name.strip():
            raise ValidationError({'name': 'Template name cannot be empty'})
        
        if not self.html_content.strip():
            raise ValidationError({'html_content': 'Template content cannot be empty'})
    
    def render_ticket(self, ticket):
        """Render template with ticket data."""
        from django.template import Template, Context
        
        # Prepare context data
        context_data = {
            'ticket': ticket,
            'event': ticket.event,
            'customer': ticket.customer,
            'zone': ticket.zone,
            'seat': ticket.seat,
            'transaction': ticket.transaction,
            'venue': ticket.event.venue,
            'tenant': ticket.tenant,
        }
        
        # Render HTML content
        template = Template(self.html_content)
        context = Context(context_data)
        rendered_html = template.render(context)
        
        return rendered_html
    
    @classmethod
    def get_default_template(cls, tenant, template_type):
        """Get default template for tenant and type."""
        try:
            return cls.objects.filter(
                tenant=tenant,
                template_type=template_type,
                is_default=True,
                is_active=True
            ).first()
        except cls.DoesNotExist:
            return None
    
    @classmethod
    def create_default_templates(cls, tenant):
        """Create default templates for a new tenant."""
        templates = []
        
        # Default PDF template
        pdf_template = cls.objects.create(
            tenant=tenant,
            name="Default PDF Ticket",
            template_type=cls.TemplateType.PDF,
            html_content=cls._get_default_pdf_template(),
            css_styles=cls._get_default_css_styles(),
            is_default=True
        )
        templates.append(pdf_template)
        
        # Default email template
        email_template = cls.objects.create(
            tenant=tenant,
            name="Default Email Ticket",
            template_type=cls.TemplateType.EMAIL,
            html_content=cls._get_default_email_template(),
            css_styles=cls._get_default_css_styles(),
            is_default=True
        )
        templates.append(email_template)
        
        return templates
    
    @staticmethod
    def _get_default_pdf_template():
        """Get default PDF template HTML."""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>{{ event.name }} - Ticket</title>
        </head>
        <body>
            <div class="ticket">
                <div class="header">
                    <h1>{{ event.name }}</h1>
                    <div class="ticket-number">Ticket #{{ ticket.ticket_number }}</div>
                </div>
                
                <div class="event-details">
                    <div class="venue">{{ event.venue.name }}</div>
                    <div class="date">{{ event.start_date|date:"F d, Y" }}</div>
                    <div class="time">{{ event.start_date|time:"g:i A" }}</div>
                </div>
                
                <div class="customer-info">
                    <div class="customer-name">{{ customer.full_name }}</div>
                    {% if customer.identification %}
                    <div class="customer-id">ID: {{ customer.identification }}</div>
                    {% endif %}
                </div>
                
                <div class="seating-info">
                    <div class="zone">Zone: {{ zone.name }}</div>
                    {% if seat %}
                    <div class="seat">{{ seat.seat_label }}</div>
                    {% else %}
                    <div class="seat">General Admission</div>
                    {% endif %}
                </div>
                
                <div class="pricing">
                    <div class="price">{{ ticket.currency }} {{ ticket.total_price }}</div>
                </div>
                
                {% if ticket.qr_code_image %}
                <div class="qr-code">
                    <img src="{{ ticket.qr_code_image.url }}" alt="QR Code">
                </div>
                {% endif %}
                
                <div class="footer">
                    <div class="terms">Present this ticket for entry. Valid for one use only.</div>
                </div>
            </div>
        </body>
        </html>
        """
    
    @staticmethod
    def _get_default_email_template():
        """Get default email template HTML."""
        return """
        <div style="max-width: 600px; margin: 0 auto; font-family: Arial, sans-serif;">
            <div style="background: #f8f9fa; padding: 20px; text-align: center;">
                <h1 style="color: #333;">{{ event.name }}</h1>
                <p style="color: #666;">Your Digital Ticket</p>
            </div>
            
            <div style="padding: 20px; background: white;">
                <h2>Event Details</h2>
                <p><strong>Venue:</strong> {{ event.venue.name }}</p>
                <p><strong>Date:</strong> {{ event.start_date|date:"F d, Y" }}</p>
                <p><strong>Time:</strong> {{ event.start_date|time:"g:i A" }}</p>
                
                <h2>Ticket Information</h2>
                <p><strong>Ticket Number:</strong> {{ ticket.ticket_number }}</p>
                <p><strong>Customer:</strong> {{ customer.full_name }}</p>
                <p><strong>Zone:</strong> {{ zone.name }}</p>
                {% if seat %}
                <p><strong>Seat:</strong> {{ seat.seat_label }}</p>
                {% else %}
                <p><strong>Type:</strong> General Admission</p>
                {% endif %}
                <p><strong>Price:</strong> {{ ticket.currency }} {{ ticket.total_price }}</p>
                
                {% if ticket.qr_code_image %}
                <div style="text-align: center; margin: 20px 0;">
                    <img src="{{ ticket.qr_code_image.url }}" alt="QR Code" style="max-width: 200px;">
                    <p style="font-size: 12px; color: #666;">Present this QR code for entry</p>
                </div>
                {% endif %}
            </div>
            
            <div style="background: #f8f9fa; padding: 20px; text-align: center; font-size: 12px; color: #666;">
                <p>This is your digital ticket. Please save this email or take a screenshot for entry.</p>
            </div>
        </div>
        """
    
    @staticmethod
    def _get_default_css_styles():
        """Get default CSS styles."""
        return """
        .ticket {
            width: 100%;
            max-width: 400px;
            margin: 0 auto;
            border: 2px solid #333;
            border-radius: 10px;
            padding: 20px;
            font-family: Arial, sans-serif;
        }
        
        .header {
            text-align: center;
            border-bottom: 1px solid #ccc;
            padding-bottom: 15px;
            margin-bottom: 15px;
        }
        
        .header h1 {
            margin: 0;
            font-size: 24px;
            color: #333;
        }
        
        .ticket-number {
            font-size: 14px;
            color: #666;
            margin-top: 5px;
        }
        
        .event-details, .customer-info, .seating-info, .pricing {
            margin-bottom: 15px;
        }
        
        .qr-code {
            text-align: center;
            margin: 20px 0;
        }
        
        .qr-code img {
            max-width: 150px;
            height: auto;
        }
        
        .footer {
            border-top: 1px solid #ccc;
            padding-top: 15px;
            text-align: center;
            font-size: 12px;
            color: #666;
        }
        """


class TicketValidationLog(TenantAwareModel):
    """
    Audit trail for ticket validation attempts.
    Logs all validation attempts for security and analytics.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Relationships
    ticket = models.ForeignKey(
        DigitalTicket,
        on_delete=models.PROTECT,
        related_name='validation_logs',
        help_text="Ticket that was validated"
    )
    
    # Validation details
    validation_system_id = models.CharField(
        max_length=255,
        help_text="ID of the system that performed validation"
    )
    validation_result = models.BooleanField(
        help_text="Whether validation was successful"
    )
    validation_method = models.CharField(
        max_length=50,
        choices=[
            ('qr_code', 'QR Code Scan'),
            ('ticket_number', 'Ticket Number Entry'),
            ('manual', 'Manual Validation'),
        ],
        default='qr_code',
        help_text="Method used for validation"
    )
    
    # Usage tracking
    usage_count_before = models.PositiveIntegerField(
        default=0,
        help_text="Usage count before this validation"
    )
    usage_count_after = models.PositiveIntegerField(
        default=0,
        help_text="Usage count after this validation"
    )
    
    # Location and context
    validation_location = models.CharField(
        max_length=255,
        blank=True,
        help_text="Location where validation occurred"
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="IP address of validation system"
    )
    user_agent = models.TextField(
        blank=True,
        help_text="User agent of validation system"
    )
    
    # Additional data
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional validation metadata"
    )
    
    # Timestamps
    validated_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'ticket_validation_logs'
        verbose_name = 'Ticket Validation Log'
        verbose_name_plural = 'Ticket Validation Logs'
        ordering = ['-validated_at']
        indexes = [
            models.Index(fields=['tenant', 'ticket', 'validated_at']),
            models.Index(fields=['validation_system_id']),
            models.Index(fields=['validation_result']),
            models.Index(fields=['validated_at']),
        ]
    
    def __str__(self):
        result = "SUCCESS" if self.validation_result else "FAILED"
        return f"{self.ticket.ticket_number} - {result} - {self.validated_at}"


# Signal to automatically generate digital tickets when transaction is completed
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=Transaction)
def generate_digital_tickets(sender, instance, **kwargs):
    """Automatically generate digital tickets when transaction is completed."""
    if (instance.status == Transaction.Status.COMPLETED and 
        instance.fiscal_series and 
        not instance.digital_tickets.exists()):
        
        try:
            # Check if event has digital tickets enabled
            if hasattr(instance.event, 'event_configuration'):
                config = instance.event.event_configuration
                if not config.digital_tickets_enabled:
                    return
            
            # Generate digital tickets
            DigitalTicket.objects.generate_for_transaction(instance)
            
        except Exception as e:
            # Log error but don't fail transaction completion
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to generate digital tickets for transaction {instance.id}: {e}")