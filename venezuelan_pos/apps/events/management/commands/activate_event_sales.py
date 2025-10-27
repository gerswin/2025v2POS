"""
Management command to activate sales for events.
Useful for enabling sales immediately or adjusting sales periods.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction

from ...models import Event


class Command(BaseCommand):
    help = 'Activate sales for events by adjusting sales start/end dates'

    def add_arguments(self, parser):
        parser.add_argument(
            'event_id',
            type=str,
            help='Event ID to activate sales for',
        )
        parser.add_argument(
            '--start-now',
            action='store_true',
            help='Set sales start date to now (1 hour ago)',
        )
        parser.add_argument(
            '--end-days',
            type=int,
            default=7,
            help='Number of days from now when sales should end (default: 7)',
        )
        parser.add_argument(
            '--remove-restrictions',
            action='store_true',
            help='Remove all sales date restrictions (set both dates to None)',
        )

    def handle(self, *args, **options):
        event_id = options['event_id']
        start_now = options['start_now']
        end_days = options['end_days']
        remove_restrictions = options['remove_restrictions']
        
        try:
            event = Event.objects.get(id=event_id)
        except Event.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'Event with ID {event_id} not found')
            )
            return
        
        self.stdout.write(f'Event: {event.name}')
        self.stdout.write(f'Current status: {event.status}')
        self.stdout.write(f'Current sales active: {event.is_sales_active}')
        
        if event.sales_start_date:
            self.stdout.write(f'Current sales start: {event.sales_start_date}')
        if event.sales_end_date:
            self.stdout.write(f'Current sales end: {event.sales_end_date}')
        
        # Check if event can have sales activated
        if event.status != Event.Status.ACTIVE:
            self.stdout.write(
                self.style.WARNING(f'Event status is {event.status}, not ACTIVE. Consider activating the event first.')
            )
        
        # Update sales dates
        with transaction.atomic():
            if remove_restrictions:
                event.sales_start_date = None
                event.sales_end_date = None
                self.stdout.write(
                    self.style.SUCCESS('Removed all sales date restrictions')
                )
            else:
                now = timezone.now()
                
                if start_now:
                    # Set start date to 1 hour ago to ensure it's active
                    event.sales_start_date = now - timezone.timedelta(hours=1)
                
                # Set end date
                event.sales_end_date = now + timezone.timedelta(days=end_days)
                
                self.stdout.write(
                    self.style.SUCCESS(f'Updated sales dates:')
                )
                if start_now:
                    self.stdout.write(f'  Start: {event.sales_start_date}')
                self.stdout.write(f'  End: {event.sales_end_date}')
            
            event.save()
        
        # Verify the result
        event.refresh_from_db()
        self.stdout.write(f'\nResult: Sales active = {event.is_sales_active}')
        
        if event.is_sales_active:
            self.stdout.write(
                self.style.SUCCESS(f'✅ Sales are now active for event: {event.name}')
            )
            self.stdout.write(f'Sales URL: /sales/events/{event.id}/select-seats/')
        else:
            self.stdout.write(
                self.style.WARNING('⚠️  Sales are still not active. Check event status and dates.')
            )