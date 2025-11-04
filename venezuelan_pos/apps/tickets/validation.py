"""
Ticket validation system for entry control and usage tracking.
Provides comprehensive validation logic for digital tickets.
"""

import json
import base64
from datetime import datetime, timedelta
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db import transaction
from django.conf import settings
from cryptography.fernet import Fernet
from .models import DigitalTicket, TicketValidationLog


class TicketValidator:
    """
    Main ticket validation class with comprehensive validation logic.
    Handles QR code decryption, ticket authenticity, and usage tracking.
    """
    
    def __init__(self):
        """Initialize validator with encryption key."""
        self.encryption_key = getattr(settings, 'TICKET_ENCRYPTION_KEY', None)
        if self.encryption_key and isinstance(self.encryption_key, str):
            self.encryption_key = self.encryption_key.encode()
    
    def validate_qr_code(self, qr_code_data, validation_context=None):
        """
        Validate ticket by QR code data.
        
        Args:
            qr_code_data (str): Encrypted QR code data
            validation_context (dict): Additional validation context
            
        Returns:
            dict: Validation result with ticket information
        """
        try:
            # Decrypt QR code data
            ticket_data = self._decrypt_qr_data(qr_code_data)
            if not ticket_data:
                return self._validation_failed("Invalid QR code format")
            
            # Find ticket by ID
            try:
                ticket = DigitalTicket.objects.get(id=ticket_data.get('ticket_id'))
            except DigitalTicket.DoesNotExist:
                return self._validation_failed("Ticket not found")
            
            # Validate ticket authenticity
            authenticity_result = self._validate_authenticity(ticket, ticket_data)
            if not authenticity_result['valid']:
                return authenticity_result
            
            # Validate ticket status and usage
            return self._validate_ticket_usage(ticket, validation_context)
            
        except Exception as e:
            return self._validation_failed(f"Validation error: {str(e)}")
    
    def validate_ticket_number(self, ticket_number, validation_context=None):
        """
        Validate ticket by ticket number.
        
        Args:
            ticket_number (str): Ticket number to validate
            validation_context (dict): Additional validation context
            
        Returns:
            dict: Validation result with ticket information
        """
        try:
            ticket = DigitalTicket.objects.get(ticket_number=ticket_number)
            return self._validate_ticket_usage(ticket, validation_context)
        except DigitalTicket.DoesNotExist:
            return self._validation_failed("Ticket not found")
        except Exception as e:
            return self._validation_failed(f"Validation error: {str(e)}")
    
    def validate_and_use_ticket(self, ticket_identifier, validation_context=None):
        """
        Validate ticket and mark as used if valid.
        
        Args:
            ticket_identifier (str): QR code data or ticket number
            validation_context (dict): Validation context with system info
            
        Returns:
            dict: Validation result with usage information
        """
        # Determine if identifier is QR code or ticket number
        if self._is_qr_code_data(ticket_identifier):
            result = self.validate_qr_code(ticket_identifier, validation_context)
        else:
            result = self.validate_ticket_number(ticket_identifier, validation_context)
        
        # If validation passed and ticket can be used, mark as used
        if result.get('valid') and result.get('can_be_used'):
            ticket_id = result.get('ticket_id')
            if ticket_id:
                try:
                    ticket = DigitalTicket.objects.get(id=ticket_id)
                    system_id = validation_context.get('system_id', 'unknown') if validation_context else 'unknown'
                    use_result = ticket.validate_and_use(system_id)
                    
                    # Log validation attempt
                    self._log_validation(
                        ticket=ticket,
                        result=True,
                        context=validation_context,
                        method='qr_code' if self._is_qr_code_data(ticket_identifier) else 'ticket_number'
                    )
                    
                    return use_result
                except Exception as e:
                    return self._validation_failed(f"Failed to mark ticket as used: {str(e)}")
        
        # Log failed validation
        self._log_validation(
            ticket=None,
            result=False,
            context=validation_context,
            method='qr_code' if self._is_qr_code_data(ticket_identifier) else 'ticket_number',
            error=result.get('reason', 'Unknown error')
        )
        
        return result
    
    def check_ticket_status(self, ticket_identifier):
        """
        Check ticket status without marking as used.
        
        Args:
            ticket_identifier (str): QR code data or ticket number
            
        Returns:
            dict: Ticket status information
        """
        # Determine if identifier is QR code or ticket number
        if self._is_qr_code_data(ticket_identifier):
            result = self.validate_qr_code(ticket_identifier)
        else:
            result = self.validate_ticket_number(ticket_identifier)
        
        if result.get('valid'):
            ticket_id = result.get('ticket_id')
            if ticket_id:
                try:
                    ticket = DigitalTicket.objects.get(id=ticket_id)
                    return ticket.check_validation_only()
                except DigitalTicket.DoesNotExist:
                    pass
        
        return result
    
    def validate_multi_entry_ticket(self, ticket_identifier, validation_context=None):
        """
        Special validation for multi-entry tickets with check-in/check-out.
        
        Args:
            ticket_identifier (str): QR code data or ticket number
            validation_context (dict): Validation context
            
        Returns:
            dict: Validation result with entry/exit information
        """
        # Get ticket
        if self._is_qr_code_data(ticket_identifier):
            ticket_data = self._decrypt_qr_data(ticket_identifier)
            if not ticket_data:
                return self._validation_failed("Invalid QR code format")
            
            try:
                ticket = DigitalTicket.objects.get(id=ticket_data.get('ticket_id'))
            except DigitalTicket.DoesNotExist:
                return self._validation_failed("Ticket not found")
        else:
            try:
                ticket = DigitalTicket.objects.get(ticket_number=ticket_identifier)
            except DigitalTicket.DoesNotExist:
                return self._validation_failed("Ticket not found")
        
        # Check if it's a multi-entry ticket
        if ticket.ticket_type != DigitalTicket.TicketType.MULTI_ENTRY:
            return self._validation_failed("Not a multi-entry ticket")
        
        # Validate basic ticket properties
        if not ticket.is_valid:
            return self._validation_failed("Ticket is not valid")
        
        # Check if ticket can be used again
        if ticket.usage_count >= ticket.max_usage_count:
            return self._validation_failed("Ticket usage limit exceeded")
        
        # For multi-entry, we track check-ins and check-outs
        action = validation_context.get('action', 'check_in') if validation_context else 'check_in'
        
        if action == 'check_in':
            # Mark as used (increment usage count)
            system_id = validation_context.get('system_id', 'unknown') if validation_context else 'unknown'
            result = ticket.validate_and_use(system_id)
            result['action'] = 'check_in'
            result['message'] = f"Check-in successful. Remaining uses: {ticket.remaining_uses}"
        else:
            # Check-out (don't increment usage count)
            result = {
                'valid': True,
                'action': 'check_out',
                'ticket_number': ticket.ticket_number,
                'customer_name': ticket.customer.full_name,
                'event_name': ticket.event.name,
                'seat_label': ticket.seat_label,
                'usage_count': ticket.usage_count,
                'max_usage': ticket.max_usage_count,
                'remaining_uses': ticket.remaining_uses,
                'message': 'Check-out recorded'
            }
        
        # Log the multi-entry validation
        self._log_validation(
            ticket=ticket,
            result=True,
            context=validation_context,
            method='multi_entry',
            metadata={'action': action}
        )
        
        return result
    
    def _decrypt_qr_data(self, qr_code_data):
        """Decrypt QR code data to extract ticket information."""
        if not self.encryption_key:
            return None
        
        try:
            fernet = Fernet(self.encryption_key)
            encrypted_data = base64.b64decode(qr_code_data.encode())
            decrypted = fernet.decrypt(encrypted_data)
            return json.loads(decrypted.decode())
        except Exception:
            return None
    
    def _validate_authenticity(self, ticket, qr_data):
        """Validate ticket authenticity against QR code data."""
        # Check if ticket ID matches
        if str(ticket.id) != qr_data.get('ticket_id'):
            return self._validation_failed("Ticket ID mismatch")
        
        # Check if ticket number matches
        if ticket.ticket_number != qr_data.get('ticket_number'):
            return self._validation_failed("Ticket number mismatch")
        
        # Check if event ID matches
        if str(ticket.event.id) != qr_data.get('event_id'):
            return self._validation_failed("Event ID mismatch")
        
        # Check if customer ID matches
        if str(ticket.customer.id) != qr_data.get('customer_id'):
            return self._validation_failed("Customer ID mismatch")
        
        # Check creation timestamp (prevent old QR codes)
        qr_created = qr_data.get('created_at')
        if qr_created:
            try:
                qr_created_dt = datetime.fromisoformat(qr_created.replace('Z', '+00:00'))
                ticket_created_dt = ticket.created_at
                
                # Allow small time difference (1 minute) for clock skew
                time_diff = abs((qr_created_dt - ticket_created_dt).total_seconds())
                if time_diff > 60:  # More than 1 minute difference
                    return self._validation_failed("QR code timestamp mismatch")
            except (ValueError, TypeError):
                return self._validation_failed("Invalid QR code timestamp")
        
        return {'valid': True}
    
    def _validate_ticket_usage(self, ticket, validation_context=None):
        """Validate ticket usage rules and constraints."""
        # Check basic validity
        if not ticket.is_valid:
            reasons = []
            
            if ticket.status != DigitalTicket.Status.ACTIVE:
                reasons.append(f"Ticket status is {ticket.get_status_display()}")
            
            now = timezone.now()
            if ticket.valid_from and now < ticket.valid_from:
                reasons.append(f"Ticket not valid until {ticket.valid_from}")
            
            if ticket.valid_until and now > ticket.valid_until:
                reasons.append(f"Ticket expired on {ticket.valid_until}")
            
            if ticket.usage_count >= ticket.max_usage_count:
                reasons.append("Ticket usage limit exceeded")
            
            return self._validation_failed("; ".join(reasons) if reasons else "Ticket is not valid")
        
        # Check event timing (if validation context includes timing checks)
        if validation_context and validation_context.get('check_event_timing', True):
            now = timezone.now()
            
            # Check if event has started (allow entry 1 hour before)
            event_start = ticket.event.start_date
            if event_start and now < (event_start - timedelta(hours=1)):
                return self._validation_failed(f"Event has not started yet. Starts at {event_start}")
            
            # Check if event has ended (allow entry until 2 hours after start)
            if event_start and now > (event_start + timedelta(hours=2)):
                return self._validation_failed("Entry period has ended")
        
        # Return successful validation with ticket information
        return {
            'valid': True,
            'can_be_used': ticket.can_be_used,
            'ticket_id': str(ticket.id),
            'ticket_number': ticket.ticket_number,
            'customer_name': ticket.customer.full_name,
            'event_name': ticket.event.name,
            'seat_label': ticket.seat_label,
            'status': ticket.status,
            'usage_count': ticket.usage_count,
            'max_usage': ticket.max_usage_count,
            'remaining_uses': ticket.remaining_uses,
            'valid_from': ticket.valid_from,
            'valid_until': ticket.valid_until,
            'event_start': ticket.event.start_date,
            'venue_name': ticket.event.venue.name
        }
    
    def _is_qr_code_data(self, identifier):
        """Check if identifier is QR code data (base64 encoded) or ticket number."""
        try:
            # QR code data should be base64 encoded and longer than typical ticket numbers
            if len(identifier) > 50:  # Ticket numbers are typically shorter
                base64.b64decode(identifier.encode())
                return True
        except Exception:
            pass
        return False
    
    def _validation_failed(self, reason):
        """Return standardized validation failure response."""
        return {
            'valid': False,
            'can_be_used': False,
            'reason': reason,
            'timestamp': timezone.now()
        }
    
    def _log_validation(self, ticket, result, context=None, method='unknown', metadata=None, error=None):
        """Log validation attempt for audit trail."""
        try:
            log_data = {
                'validation_result': result,
                'validation_method': method,
                'validation_system_id': context.get('system_id', 'unknown') if context else 'unknown',
                'validation_location': context.get('location', '') if context else '',
                'ip_address': context.get('ip_address', '') if context else '',
                'user_agent': context.get('user_agent', '') if context else '',
                'metadata': metadata or {}
            }
            
            if error:
                log_data['metadata']['error'] = error
            
            if ticket:
                log_data.update({
                    'tenant': ticket.tenant,
                    'ticket': ticket,
                    'usage_count_before': ticket.usage_count,
                    'usage_count_after': ticket.usage_count + (1 if result and method != 'check_only' else 0)
                })
            else:
                # For failed validations where ticket wasn't found
                log_data.update({
                    'tenant': None,
                    'ticket': None,
                    'usage_count_before': 0,
                    'usage_count_after': 0
                })
            
            TicketValidationLog.objects.create(**log_data)
            
        except Exception as e:
            # Don't fail validation if logging fails
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to log validation attempt: {e}")


class ValidationContextBuilder:
    """Helper class to build validation context from request data."""
    
    @staticmethod
    def from_request(request, system_id=None, location=None):
        """Build validation context from Django request."""
        return {
            'system_id': system_id or 'web_interface',
            'location': location or '',
            'ip_address': ValidationContextBuilder._get_client_ip(request),
            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
            'timestamp': timezone.now(),
            'check_event_timing': True
        }
    
    @staticmethod
    def from_api_data(data):
        """Build validation context from API request data."""
        return {
            'system_id': data.get('validation_system_id', 'api'),
            'location': data.get('validation_location', ''),
            'ip_address': data.get('ip_address', ''),
            'user_agent': data.get('user_agent', ''),
            'timestamp': timezone.now(),
            'check_event_timing': data.get('check_event_timing', True),
            'action': data.get('action', 'check_in')  # For multi-entry tickets
        }
    
    @staticmethod
    def _get_client_ip(request):
        """Extract client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip or ''


# Convenience functions for common validation scenarios
def validate_ticket_for_entry(ticket_identifier, validation_context=None):
    """Validate ticket for entry and mark as used."""
    validator = TicketValidator()
    return validator.validate_and_use_ticket(ticket_identifier, validation_context)


def check_ticket_status_only(ticket_identifier):
    """Check ticket status without marking as used."""
    validator = TicketValidator()
    return validator.check_ticket_status(ticket_identifier)


def validate_multi_entry_ticket(ticket_identifier, action='check_in', validation_context=None):
    """Validate multi-entry ticket with check-in/check-out support."""
    if validation_context:
        validation_context['action'] = action
    else:
        validation_context = {'action': action}
    
    validator = TicketValidator()
    return validator.validate_multi_entry_ticket(ticket_identifier, validation_context)