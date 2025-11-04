"""
Management command to regenerate QR codes for digital tickets.
Useful when encryption keys change or QR codes become corrupted.
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from venezuelan_pos.apps.tickets.models import DigitalTicket
from venezuelan_pos.apps.tenants.models import Tenant


class Command(BaseCommand):
    """Regenerate QR codes for digital tickets."""
    
    help = 'Regenerate QR codes for digital tickets'
    
    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument(
            '--tenant',
            type=str,
            help='Regenerate QR codes for specific tenant (slug)'
        )
        parser.add_argument(
            '--event',
            type=str,
            help='Regenerate QR codes for specific event ID'
        )
        parser.add_argument(
            '--ticket',
            type=str,
            help='Regenerate QR code for specific ticket ID'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be regenerated without actually doing it'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            help='Process tickets in batches of this size (default: 100)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Regenerate QR codes even if they already exist'
        )
    
    def handle(self, *args, **options):
        """Execute the QR code regeneration command."""
        dry_run = options['dry_run']
        batch_size = options['batch_size']
        force = options['force']
        
        self.stdout.write(
            self.style.SUCCESS(
                f"Starting QR code regeneration (dry_run={dry_run}, force={force})"
            )
        )
        
        # Build queryset based on filters
        queryset = DigitalTicket.objects.all()
        
        if options['tenant']:
            try:
                tenant = Tenant.objects.get(slug=options['tenant'])
                queryset = queryset.filter(tenant=tenant)
                self.stdout.write(f"Filtering by tenant: {tenant.name}")
            except Tenant.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f"Tenant not found: {options['tenant']}")
                )
                return
        
        if options['event']:
            queryset = queryset.filter(event_id=options['event'])
            self.stdout.write(f"Filtering by event ID: {options['event']}")
        
        if options['ticket']:
            queryset = queryset.filter(id=options['ticket'])
            self.stdout.write(f"Filtering by ticket ID: {options['ticket']}")
        
        # Filter tickets that need QR code regeneration
        if not force:
            # Only regenerate for tickets without QR codes
            queryset = queryset.filter(qr_code_data='')
            self.stdout.write("Only processing tickets without QR codes")
        else:
            self.stdout.write("Processing all matching tickets (force mode)")
        
        total_count = queryset.count()
        
        if total_count == 0:
            self.stdout.write("No tickets found matching criteria")
            return
        
        self.stdout.write(f"Found {total_count} tickets to process")
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"DRY RUN: Would regenerate QR codes for {total_count} tickets"
                )
            )
            
            # Show sample of tickets that would be processed
            sample_tickets = queryset[:5]
            for ticket in sample_tickets:
                self.stdout.write(f"  - {ticket.ticket_number} ({ticket.event.name})")
            
            if total_count > 5:
                self.stdout.write(f"  ... and {total_count - 5} more")
            
            return
        
        # Process tickets in batches
        processed_count = 0
        error_count = 0
        
        # Use iterator to avoid loading all tickets into memory
        for ticket in queryset.iterator(chunk_size=batch_size):
            try:
                with transaction.atomic():
                    # Generate QR code
                    ticket.generate_qr_code()
                    processed_count += 1
                    
                    if processed_count % batch_size == 0:
                        self.stdout.write(
                            f"Processed {processed_count}/{total_count} tickets"
                        )
                        
            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(
                        f"Error processing ticket {ticket.ticket_number}: {e}"
                    )
                )
                
                # Continue processing other tickets
                continue
        
        # Final summary
        self.stdout.write(
            self.style.SUCCESS(
                f"QR code regeneration completed:\n"
                f"  - Successfully processed: {processed_count}\n"
                f"  - Errors: {error_count}\n"
                f"  - Total: {total_count}"
            )
        )
        
        if error_count > 0:
            self.stdout.write(
                self.style.WARNING(
                    f"There were {error_count} errors during processing. "
                    "Check the error messages above for details."
                )
            )