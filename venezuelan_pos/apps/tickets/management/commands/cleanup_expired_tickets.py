"""
Management command to clean up expired tickets and validation logs.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from datetime import timedelta
from venezuelan_pos.apps.tickets.models import DigitalTicket, TicketValidationLog


class Command(BaseCommand):
    """Clean up expired tickets and old validation logs."""
    
    help = 'Clean up expired tickets and old validation logs'
    
    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be cleaned up without actually doing it'
        )
        parser.add_argument(
            '--ticket-expiry-days',
            type=int,
            default=30,
            help='Mark tickets as expired if they are older than this many days (default: 30)'
        )
        parser.add_argument(
            '--log-retention-days',
            type=int,
            default=90,
            help='Delete validation logs older than this many days (default: 90)'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=1000,
            help='Process records in batches of this size (default: 1000)'
        )
    
    def handle(self, *args, **options):
        """Execute the cleanup command."""
        dry_run = options['dry_run']
        ticket_expiry_days = options['ticket_expiry_days']
        log_retention_days = options['log_retention_days']
        batch_size = options['batch_size']
        
        self.stdout.write(
            self.style.SUCCESS(
                f"Starting ticket cleanup (dry_run={dry_run})"
            )
        )
        
        # Calculate cutoff dates
        now = timezone.now()
        ticket_expiry_cutoff = now - timedelta(days=ticket_expiry_days)
        log_retention_cutoff = now - timedelta(days=log_retention_days)
        
        # Clean up expired tickets
        expired_count = self._cleanup_expired_tickets(
            ticket_expiry_cutoff, dry_run, batch_size
        )
        
        # Clean up old validation logs
        log_cleanup_count = self._cleanup_old_logs(
            log_retention_cutoff, dry_run, batch_size
        )
        
        # Summary
        self.stdout.write(
            self.style.SUCCESS(
                f"Cleanup completed:\n"
                f"  - Expired tickets processed: {expired_count}\n"
                f"  - Old validation logs deleted: {log_cleanup_count}"
            )
        )
    
    def _cleanup_expired_tickets(self, cutoff_date, dry_run, batch_size):
        """Mark expired tickets as expired."""
        # Find tickets that should be expired
        expired_tickets = DigitalTicket.objects.filter(
            status=DigitalTicket.Status.ACTIVE,
            valid_until__lt=cutoff_date
        )
        
        total_count = expired_tickets.count()
        
        if total_count == 0:
            self.stdout.write("No expired tickets found")
            return 0
        
        self.stdout.write(f"Found {total_count} expired tickets")
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"DRY RUN: Would mark {total_count} tickets as expired"
                )
            )
            return total_count
        
        # Process in batches
        processed_count = 0
        
        while True:
            batch = list(expired_tickets[:batch_size])
            if not batch:
                break
            
            with transaction.atomic():
                # Update tickets in batch
                ticket_ids = [ticket.id for ticket in batch]
                DigitalTicket.objects.filter(
                    id__in=ticket_ids
                ).update(status=DigitalTicket.Status.EXPIRED)
                
                processed_count += len(batch)
                
                self.stdout.write(
                    f"Marked {processed_count}/{total_count} tickets as expired"
                )
        
        return processed_count
    
    def _cleanup_old_logs(self, cutoff_date, dry_run, batch_size):
        """Delete old validation logs."""
        old_logs = TicketValidationLog.objects.filter(
            validated_at__lt=cutoff_date
        )
        
        total_count = old_logs.count()
        
        if total_count == 0:
            self.stdout.write("No old validation logs found")
            return 0
        
        self.stdout.write(f"Found {total_count} old validation logs")
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"DRY RUN: Would delete {total_count} validation logs"
                )
            )
            return total_count
        
        # Delete in batches to avoid memory issues
        deleted_count = 0
        
        while True:
            batch_ids = list(
                old_logs.values_list('id', flat=True)[:batch_size]
            )
            if not batch_ids:
                break
            
            with transaction.atomic():
                batch_deleted = TicketValidationLog.objects.filter(
                    id__in=batch_ids
                ).delete()[0]
                
                deleted_count += batch_deleted
                
                self.stdout.write(
                    f"Deleted {deleted_count}/{total_count} validation logs"
                )
        
        return deleted_count