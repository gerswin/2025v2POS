import io
import os
from django.conf import settings
from django.template.loader import render_to_string
from django.core.files.base import ContentFile
from django.utils import timezone
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from .models import DigitalTicket, TicketTemplate


class TicketPDFService:
    """Service for generating PDF tickets."""
    
    @classmethod
    def generate_pdf_ticket(cls, ticket, template=None):
        """
        Generate PDF ticket using template or default layout.
        Returns PDF content as bytes.
        """
        if not template:
            template = TicketTemplate.get_default_template(
                ticket.tenant,
                TicketTemplate.TemplateType.PDF
            )
        
        if template:
            return cls._generate_from_template(ticket, template)
        else:
            return cls._generate_default_pdf(ticket)
    
    @classmethod
    def _generate_from_template(cls, ticket, template):
        """Generate PDF from HTML template using weasyprint."""
        try:
            import weasyprint
            
            # Render HTML content
            html_content = template.render_ticket(ticket)
            
            # Add CSS styles
            css_content = template.css_styles or cls._get_default_css()
            
            # Create HTML document
            html_doc = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <style>
                    {css_content}
                </style>
            </head>
            <body>
                {html_content}
            </body>
            </html>
            """
            
            # Generate PDF
            pdf_bytes = weasyprint.HTML(string=html_doc).write_pdf()
            return pdf_bytes
            
        except ImportError:
            # Fallback to reportlab if weasyprint is not available
            return cls._generate_default_pdf(ticket)
        except Exception as e:
            # Log error and fallback
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to generate PDF from template: {e}")
            return cls._generate_default_pdf(ticket)
    
    @classmethod
    def _generate_default_pdf(cls, ticket):
        """Generate PDF using reportlab with default layout."""
        buffer = io.BytesIO()
        
        # Create PDF document
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18
        )
        
        # Build content
        story = []
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.darkblue
        )
        
        header_style = ParagraphStyle(
            'CustomHeader',
            parent=styles['Heading2'],
            fontSize=16,
            spaceAfter=12,
            textColor=colors.darkblue
        )
        
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=12,
            spaceAfter=6
        )
        
        # Title
        story.append(Paragraph(ticket.event.name, title_style))
        story.append(Spacer(1, 12))
        
        # Ticket number
        story.append(Paragraph(f"Ticket #{ticket.ticket_number}", header_style))
        story.append(Spacer(1, 12))
        
        # Event details table
        event_data = [
            ['Event:', ticket.event.name],
            ['Venue:', ticket.event.venue.name],
            ['Date:', ticket.event.start_date.strftime('%B %d, %Y')],
            ['Time:', ticket.event.start_date.strftime('%I:%M %p')],
        ]
        
        if ticket.event.venue.address:
            event_data.append(['Address:', ticket.event.venue.address])
        
        event_table = Table(event_data, colWidths=[1.5*inch, 4*inch])
        event_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        
        story.append(event_table)
        story.append(Spacer(1, 20))
        
        # Customer information
        story.append(Paragraph("Customer Information", header_style))
        
        customer_data = [
            ['Name:', ticket.customer.full_name],
        ]
        
        if ticket.customer.identification:
            customer_data.append(['ID:', ticket.customer.identification])
        
        if ticket.customer.email:
            customer_data.append(['Email:', ticket.customer.email])
        
        if ticket.customer.phone:
            customer_data.append(['Phone:', str(ticket.customer.phone)])
        
        customer_table = Table(customer_data, colWidths=[1.5*inch, 4*inch])
        customer_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        
        story.append(customer_table)
        story.append(Spacer(1, 20))
        
        # Seating information
        story.append(Paragraph("Seating Information", header_style))
        
        seating_data = [
            ['Zone:', ticket.zone.name],
        ]
        
        if ticket.seat:
            seating_data.append(['Seat:', ticket.seat.seat_label])
        else:
            seating_data.append(['Type:', 'General Admission'])
        
        seating_data.append(['Price:', f"{ticket.currency} {ticket.total_price}"])
        
        seating_table = Table(seating_data, colWidths=[1.5*inch, 4*inch])
        seating_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        
        story.append(seating_table)
        story.append(Spacer(1, 30))
        
        # QR Code
        if ticket.qr_code_image:
            try:
                # Add QR code image
                qr_image = Image(ticket.qr_code_image.path, width=2*inch, height=2*inch)
                qr_image.hAlign = 'CENTER'
                story.append(qr_image)
                story.append(Spacer(1, 12))
                
                story.append(Paragraph(
                    "Present this QR code for entry",
                    ParagraphStyle(
                        'QRText',
                        parent=styles['Normal'],
                        fontSize=10,
                        alignment=TA_CENTER,
                        textColor=colors.grey
                    )
                ))
            except Exception:
                # QR code image not available
                pass
        
        story.append(Spacer(1, 30))
        
        # Terms and conditions
        terms_text = """
        <b>Terms and Conditions:</b><br/>
        • This ticket is valid for one-time entry only<br/>
        • Ticket must be presented at entry<br/>
        • No refunds or exchanges<br/>
        • Event organizer reserves the right to refuse entry<br/>
        • Keep this ticket safe - lost tickets cannot be replaced
        """
        
        story.append(Paragraph(
            terms_text,
            ParagraphStyle(
                'Terms',
                parent=styles['Normal'],
                fontSize=9,
                textColor=colors.grey,
                leftIndent=20
            )
        ))
        
        # Build PDF
        doc.build(story)
        
        # Get PDF content
        pdf_content = buffer.getvalue()
        buffer.close()
        
        return pdf_content
    
    @classmethod
    def _get_default_css(cls):
        """Get default CSS for HTML templates."""
        return """
        body {
            font-family: Arial, sans-serif;
            margin: 20px;
            color: #333;
        }
        
        .ticket {
            max-width: 600px;
            margin: 0 auto;
            border: 2px solid #333;
            border-radius: 10px;
            padding: 30px;
        }
        
        .header {
            text-align: center;
            border-bottom: 2px solid #ccc;
            padding-bottom: 20px;
            margin-bottom: 20px;
        }
        
        .header h1 {
            margin: 0;
            font-size: 28px;
            color: #333;
        }
        
        .ticket-number {
            font-size: 16px;
            color: #666;
            margin-top: 10px;
        }
        
        .section {
            margin-bottom: 20px;
        }
        
        .section h2 {
            font-size: 18px;
            color: #333;
            border-bottom: 1px solid #ccc;
            padding-bottom: 5px;
            margin-bottom: 10px;
        }
        
        .info-row {
            display: flex;
            margin-bottom: 8px;
        }
        
        .info-label {
            font-weight: bold;
            width: 120px;
        }
        
        .info-value {
            flex: 1;
        }
        
        .qr-code {
            text-align: center;
            margin: 30px 0;
        }
        
        .qr-code img {
            max-width: 200px;
            height: auto;
        }
        
        .footer {
            border-top: 2px solid #ccc;
            padding-top: 20px;
            text-align: center;
            font-size: 12px;
            color: #666;
        }
        
        .terms {
            font-size: 10px;
            color: #888;
            margin-top: 20px;
            line-height: 1.4;
        }
        """
    
    @classmethod
    def save_pdf_to_file(cls, ticket, pdf_content):
        """Save PDF content to ticket's file field (if implemented)."""
        filename = f"ticket_{ticket.ticket_number}.pdf"
        
        # If ticket model has a pdf_file field, save it there
        if hasattr(ticket, 'pdf_file'):
            ticket.pdf_file.save(
                filename,
                ContentFile(pdf_content),
                save=True
            )
        
        return filename


class TicketDeliveryService:
    """Service for delivering tickets to customers."""
    
    @classmethod
    def send_ticket_email(cls, ticket, custom_message=None):
        """Send ticket via email."""
        from venezuelan_pos.apps.notifications.services import NotificationService
        
        # Generate PDF
        pdf_content = TicketPDFService.generate_pdf_ticket(ticket)
        
        # Prepare email data
        email_data = {
            'customer': ticket.customer,
            'ticket': ticket,
            'event': ticket.event,
            'pdf_content': pdf_content,
            'custom_message': custom_message
        }
        
        # Send email with PDF attachment
        return NotificationService.send_ticket_delivery_email(email_data)
    
    @classmethod
    def send_ticket_sms(cls, ticket, custom_message=None):
        """Send ticket information via SMS."""
        from venezuelan_pos.apps.notifications.services import NotificationService
        
        # Prepare SMS message
        message = f"""
Your ticket for {ticket.event.name}
Ticket: {ticket.ticket_number}
Date: {ticket.event.start_date.strftime('%b %d, %Y %I:%M %p')}
Venue: {ticket.event.venue.name}
Seat: {ticket.seat_label}
        """.strip()
        
        if custom_message:
            message = f"{custom_message}\n\n{message}"
        
        return NotificationService.send_sms(
            ticket.customer.phone,
            message
        )
    
    @classmethod
    def send_ticket_whatsapp(cls, ticket, custom_message=None):
        """Send ticket information via WhatsApp."""
        from venezuelan_pos.apps.notifications.services import NotificationService
        
        # Prepare WhatsApp message
        message = f"""
🎫 *Your Digital Ticket*

*Event:* {ticket.event.name}
*Ticket:* {ticket.ticket_number}
*Date:* {ticket.event.start_date.strftime('%B %d, %Y')}
*Time:* {ticket.event.start_date.strftime('%I:%M %p')}
*Venue:* {ticket.event.venue.name}
*Seat:* {ticket.seat_label}

Present this message and your ID for entry.
        """.strip()
        
        if custom_message:
            message = f"{custom_message}\n\n{message}"
        
        return NotificationService.send_whatsapp(
            ticket.customer.phone,
            message
        )


class TicketValidationService:
    """Service for ticket validation and entry control."""
    
    @classmethod
    def validate_qr_code(cls, qr_code_data, validation_system_id, mark_as_used=True):
        """Validate ticket by QR code data."""
        try:
            # Find ticket by QR code
            ticket = cls._decrypt_qr_code(qr_code_data)
            if not ticket:
                return {
                    'valid': False,
                    'reason': 'Invalid QR code',
                    'timestamp': timezone.now()
                }
            
            # Validate and optionally use ticket
            if mark_as_used:
                return ticket.validate_and_use(validation_system_id)
            else:
                return ticket.check_validation_only()
                
        except Exception as e:
            return {
                'valid': False,
                'reason': f'Validation error: {str(e)}',
                'timestamp': timezone.now()
            }
    
    @classmethod
    def validate_ticket_number(cls, ticket_number, validation_system_id, mark_as_used=True):
        """Validate ticket by ticket number."""
        try:
            ticket = DigitalTicket.objects.get(ticket_number=ticket_number)
            
            # Validate and optionally use ticket
            if mark_as_used:
                return ticket.validate_and_use(validation_system_id)
            else:
                return ticket.check_validation_only()
                
        except DigitalTicket.DoesNotExist:
            return {
                'valid': False,
                'reason': 'Ticket not found',
                'timestamp': timezone.now()
            }
        except Exception as e:
            return {
                'valid': False,
                'reason': f'Validation error: {str(e)}',
                'timestamp': timezone.now()
            }
    
    @classmethod
    def _decrypt_qr_code(cls, qr_code_data):
        """Decrypt QR code data to find ticket."""
        try:
            import json
            import base64
            from cryptography.fernet import Fernet
            
            # Get encryption key
            key = getattr(settings, 'TICKET_ENCRYPTION_KEY', None)
            if not key:
                return None
            
            if isinstance(key, str):
                key = key.encode()
            
            # Decrypt data
            fernet = Fernet(key)
            encrypted_data = base64.b64decode(qr_code_data.encode())
            decrypted = fernet.decrypt(encrypted_data)
            validation_data = json.loads(decrypted.decode())
            
            # Find ticket by ID
            ticket_id = validation_data.get('ticket_id')
            if ticket_id:
                return DigitalTicket.objects.get(id=ticket_id)
            
        except Exception:
            pass
        
        return None
    
    @classmethod
    def get_validation_stats(cls, tenant, date_from=None, date_to=None):
        """Get validation statistics for a tenant."""
        from .models import TicketValidationLog
        
        queryset = TicketValidationLog.objects.filter(tenant=tenant)
        
        if date_from:
            queryset = queryset.filter(validated_at__gte=date_from)
        if date_to:
            queryset = queryset.filter(validated_at__lte=date_to)
        
        total_validations = queryset.count()
        successful_validations = queryset.filter(validation_result=True).count()
        failed_validations = queryset.filter(validation_result=False).count()
        
        return {
            'total_validations': total_validations,
            'successful_validations': successful_validations,
            'failed_validations': failed_validations,
            'success_rate': (successful_validations / total_validations * 100) if total_validations > 0 else 0
        }