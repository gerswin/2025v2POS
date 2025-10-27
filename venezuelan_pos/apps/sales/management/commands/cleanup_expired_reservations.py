"""
Management command to clean up expired seat reservations.
This should be run periodically (e.g., every 5 minutes) via cron job.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction

from ...models import ReservedTicket, Transaction
from ...cache import sales_cache


class Command(BaseCommand):
    help = 'Clean up expired seat reservations and temporary transactions'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be cleaned up without actually doing it',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        now = timezone.now()
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))
        
        # Find expired reservations
        expired_reservations = ReservedTicket.objects.filter(
            status=ReservedTicket.Status.ACTIVE,
            reserved_until__lt=now
        ).select_related('seat', 'zone', 'transaction')
        
        expired_count = expired_reservations.count()
        
        if expired_count == 0:
            self.stdout.write(self.style.SUCCESS('No expired reservations found'))
            return
        
        self.stdout.write(f'Found {expired_count} expired reservations')
        
        if not dry_run:
            with transaction.atomic():
                # Update expired reservations
                updated = expired_reservations.update(
                    status=ReservedTicket.Status.EXPIRED
                )
                
                # Invalidate cache for affected seats/zones
                for reservation in expired_reservations:
                    if reservation.seat:
                        sales_cache.invalidate_seat_availability(str(reservation.seat.id))
                    else:
                        sales_cache.invalidate_zone_availability(str(reservation.zone.id))
                
                self.stdout.write(
                    self.style.SUCCESS(f'Successfully expired {updated} reservations')
                )
        
        # Clean up temporary transactions that have no active reservations
        temp_transactions = Transaction.objects.filter(
            fiscal_series__startswith='TEMP_',
            status=Transaction.Status.PENDING
        ).exclude(
            reserved_tickets__status=ReservedTicket.Status.ACTIVE
        )
        
        temp_count = temp_transactions.count()
        
        if temp_count > 0:
            self.stdout.write(f'Found {temp_count} temporary transactions to clean up')
            
            if not dry_run:
                # Delete temporary transactions (this will cascade to expired reservations)
                deleted_count, _ = temp_transactions.delete()
                self.stdout.write(
                    self.style.SUCCESS(f'Successfully cleaned up {deleted_count} temporary transactions')
                )
        else:
            self.stdout.write('No temporary transactions to clean up')
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN COMPLETE - Run without --dry-run to apply changes')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS('Cleanup completed successfully')
            )