"""
Management command to warm up sales caches.
Useful for pre-loading popular events and improving performance.
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from venezuelan_pos.apps.events.models import Event
from venezuelan_pos.apps.sales.cache import sales_cache


class Command(BaseCommand):
    help = 'Warm up sales caches for events'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--event-id',
            type=str,
            help='Specific event ID to warm cache for'
        )
        parser.add_argument(
            '--all-active',
            action='store_true',
            help='Warm caches for all active events'
        )
        parser.add_argument(
            '--tenant',
            type=str,
            help='Tenant slug to filter events'
        )
    
    def handle(self, *args, **options):
        start_time = timezone.now()
        
        try:
            if options['event_id']:
                # Warm cache for specific event
                try:
                    event = Event.objects.get(id=options['event_id'])
                    self.stdout.write(f"Warming cache for event: {event.name}")
                    
                    success = sales_cache.warm_event_caches(event)
                    
                    if success:
                        self.stdout.write(
                            self.style.SUCCESS(f"Successfully warmed cache for event {event.name}")
                        )
                    else:
                        self.stdout.write(
                            self.style.WARNING(f"Failed to warm cache for event {event.name}")
                        )
                        
                except Event.DoesNotExist:
                    raise CommandError(f"Event with ID {options['event_id']} not found")
            
            elif options['all_active']:
                # Warm caches for all active events
                events_query = Event.objects.filter(status=Event.Status.ACTIVE)
                
                if options['tenant']:
                    events_query = events_query.filter(tenant__slug=options['tenant'])
                
                events = events_query.all()
                
                if not events:
                    self.stdout.write(self.style.WARNING("No active events found"))
                    return
                
                self.stdout.write(f"Warming caches for {len(events)} active events...")
                
                success_count = 0
                for event in events:
                    self.stdout.write(f"  Warming cache for: {event.name}")
                    
                    if sales_cache.warm_event_caches(event):
                        success_count += 1
                        self.stdout.write(f"    ✓ Success")
                    else:
                        self.stdout.write(f"    ✗ Failed")
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Successfully warmed caches for {success_count}/{len(events)} events"
                    )
                )
            
            else:
                raise CommandError("Please specify --event-id or --all-active")
            
            # Show execution time
            end_time = timezone.now()
            duration = (end_time - start_time).total_seconds()
            self.stdout.write(f"Cache warming completed in {duration:.2f} seconds")
            
        except Exception as e:
            raise CommandError(f"Cache warming failed: {e}")