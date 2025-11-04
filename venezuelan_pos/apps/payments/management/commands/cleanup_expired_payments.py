"""
Management command to clean up expired payment plans and reservations.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from venezuelan_pos.apps.payments.services import ReservationService


class Command(BaseCommand):
    help = 'Clean up expired payment plans and reservations'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be cleaned up without actually doing it',
        )
        
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed output',
        )
    
    def handle(self, *args, **options):
        dry_run = options['dry_run']
        verbose = options['verbose']
        
        self.stdout.write(
            self.style.SUCCESS(
                f"Starting cleanup of expired payments at {timezone.now()}"
            )
        )
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING("DRY RUN MODE - No changes will be made")
            )
        
        try:
            if not dry_run:
                stats = ReservationService.cleanup_expired_reservations()
            else:
                # For dry run, just count what would be cleaned up
                from venezuelan_pos.apps.payments.models import PaymentPlan
                from venezuelan_pos.apps.sales.models import ReservedTicket
                
                now = timezone.now()
                
                expired_reservations = ReservedTicket.objects.filter(
                    status=ReservedTicket.Status.ACTIVE,
                    reserved_until__lte=now
                ).count()
                
                expired_plans = PaymentPlan.objects.filter(
                    status=PaymentPlan.Status.ACTIVE,
                    expires_at__lte=now
                ).count()
                
                released_seats = ReservedTicket.objects.filter(
                    status=ReservedTicket.Status.ACTIVE,
                    reserved_until__lte=now,
                    seat__isnull=False
                ).count()
                
                stats = {
                    'expired_reservations': expired_reservations,
                    'expired_payment_plans': expired_plans,
                    'released_seats': released_seats
                }
            
            # Display results
            self.stdout.write(
                self.style.SUCCESS(
                    f"Cleanup completed successfully:"
                )
            )
            
            self.stdout.write(f"  - Expired reservations: {stats['expired_reservations']}")
            self.stdout.write(f"  - Expired payment plans: {stats['expired_payment_plans']}")
            self.stdout.write(f"  - Released seats: {stats['released_seats']}")
            
            if verbose:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Cleanup finished at {timezone.now()}"
                    )
                )
        
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error during cleanup: {str(e)}")
            )
            raise