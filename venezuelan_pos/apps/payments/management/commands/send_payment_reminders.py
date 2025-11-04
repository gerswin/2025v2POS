"""
Management command to send payment reminders for expiring payment plans.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from venezuelan_pos.apps.payments.services import PaymentReminderService


class Command(BaseCommand):
    help = 'Send payment reminders for expiring payment plans'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what reminders would be sent without actually sending them',
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
                f"Starting payment reminder processing at {timezone.now()}"
            )
        )
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING("DRY RUN MODE - No reminders will be sent")
            )
        
        try:
            if not dry_run:
                stats = PaymentReminderService.process_payment_reminders()
            else:
                # For dry run, just count what would be sent
                plans_needing_reminders = PaymentReminderService.get_payment_plans_needing_reminders()
                
                stats = {
                    'reminders_sent': plans_needing_reminders.count(),
                    'reminders_failed': 0
                }
                
                if verbose:
                    self.stdout.write("Payment plans needing reminders:")
                    for plan in plans_needing_reminders:
                        self.stdout.write(
                            f"  - Plan {plan.id}: {plan.customer.full_name} "
                            f"(expires: {plan.expires_at})"
                        )
            
            # Display results
            self.stdout.write(
                self.style.SUCCESS(
                    f"Reminder processing completed:"
                )
            )
            
            self.stdout.write(f"  - Reminders sent: {stats['reminders_sent']}")
            self.stdout.write(f"  - Reminders failed: {stats['reminders_failed']}")
            
            if verbose:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Processing finished at {timezone.now()}"
                    )
                )
        
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error during reminder processing: {str(e)}")
            )
            raise