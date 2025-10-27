"""
Management command to warm up zone availability cache.
This helps improve performance by pre-loading frequently accessed data.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone

from ...cache import sales_cache
from ...models import Transaction
from ....zones.models import Zone
from ....events.models import Event


class Command(BaseCommand):
    help = 'Warm up zone availability cache for better performance'

    def add_arguments(self, parser):
        parser.add_argument(
            '--zone-id',
            type=str,
            help='Specific zone ID to warm up (optional)',
        )
        parser.add_argument(
            '--event-id',
            type=str,
            help='Warm up all zones for a specific event (optional)',
        )

    def handle(self, *args, **options):
        zone_id = options.get('zone_id')
        event_id = options.get('event_id')
        
        if zone_id:
            # Warm up specific zone
            try:
                zone = Zone.objects.get(id=zone_id)
                self.warm_zone_cache(zone)
                self.stdout.write(
                    self.style.SUCCESS(f'Successfully warmed cache for zone: {zone.name}')
                )
            except Zone.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'Zone with ID {zone_id} not found')
                )
        elif event_id:
            # Warm up all zones for an event
            try:
                event = Event.objects.get(id=event_id)
                zones = Zone.objects.filter(event=event)
                for zone in zones:
                    self.warm_zone_cache(zone)
                self.stdout.write(
                    self.style.SUCCESS(f'Successfully warmed cache for {zones.count()} zones in event: {event.name}')
                )
            except Event.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'Event with ID {event_id} not found')
                )
        else:
            # Warm up all zones
            zones = Zone.objects.all()
            warmed_count = 0
            for zone in zones:
                if self.warm_zone_cache(zone):
                    warmed_count += 1
            
            self.stdout.write(
                self.style.SUCCESS(f'Successfully warmed cache for {warmed_count} zones')
            )

    def warm_zone_cache(self, zone):
        """Warm up cache for a specific zone."""
        try:
            # This will rebuild the cache if it doesn't exist
            sales_cache.rebuild_zone_availability_cache(zone)
            return True
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f'Failed to warm cache for zone {zone.name}: {e}')
            )
            return False