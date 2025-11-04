"""
Management command for monitoring and processing stage transitions.
Can be run as a scheduled task to ensure automatic transitions are processed.
"""

import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Q

from venezuelan_pos.apps.events.models import Event
from venezuelan_pos.apps.pricing.stage_automation import stage_automation
from venezuelan_pos.apps.pricing.models import PriceStage

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Monitor and process automatic stage transitions for active events'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--event-id',
            type=str,
            help='Process transitions for a specific event ID',
        )
        parser.add_argument(
            '--tenant-id',
            type=str,
            help='Process transitions for a specific tenant ID',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be processed without making changes',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Enable verbose output',
        )
    
    def handle(self, *args, **options):
        """Main command handler."""
        self.verbosity = 2 if options['verbose'] else 1
        self.dry_run = options['dry_run']
        
        if self.dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN MODE - No changes will be made')
            )
        
        # Get events to process
        events = self._get_events_to_process(
            event_id=options.get('event_id'),
            tenant_id=options.get('tenant_id')
        )
        
        if not events:
            self.stdout.write(
                self.style.WARNING('No active events found to process')
            )
            return
        
        self.stdout.write(
            f'Processing {len(events)} active events for stage transitions...'
        )
        
        total_transitions = 0
        total_errors = 0
        
        for event in events:
            try:
                transitions = self._process_event_transitions(event)
                total_transitions += len(transitions)
                
                if self.verbosity >= 2 or transitions:
                    self.stdout.write(
                        f'Event "{event.name}" ({event.id}): '
                        f'{len(transitions)} transitions processed'
                    )
                    
                    for transition in transitions:
                        self.stdout.write(
                            f'  - {transition.stage_from.name} -> '
                            f'{transition.stage_to.name if transition.stage_to else "Final"} '
                            f'({transition.trigger_reason})'
                        )
                
            except Exception as e:
                total_errors += 1
                logger.error(f'Error processing event {event.id}: {e}')
                self.stdout.write(
                    self.style.ERROR(
                        f'Error processing event "{event.name}": {e}'
                    )
                )
        
        # Summary
        self.stdout.write(
            self.style.SUCCESS(
                f'Processing complete: {total_transitions} transitions processed, '
                f'{total_errors} errors'
            )
        )
        
        # Health check
        if not self.dry_run:
            health_status = stage_automation.health_check()
            if health_status.get('status') != 'healthy':
                self.stdout.write(
                    self.style.WARNING(
                        f'Stage automation health check: {health_status.get("status")}'
                    )
                )
    
    def _get_events_to_process(self, event_id=None, tenant_id=None):
        """Get list of events to process transitions for."""
        now = timezone.now()
        
        # Base query for active events with future dates
        queryset = Event.objects.filter(
            status=Event.Status.ACTIVE,
            start_date__gt=now  # Only future events
        ).select_related('tenant')
        
        # Filter by specific event if provided
        if event_id:
            queryset = queryset.filter(id=event_id)
        
        # Filter by tenant if provided
        if tenant_id:
            queryset = queryset.filter(tenant_id=tenant_id)
        
        # Only include events that have active price stages with auto-transition
        queryset = queryset.filter(
            price_stages__is_active=True,
            price_stages__auto_transition=True
        ).distinct()
        
        return list(queryset)
    
    def _process_event_transitions(self, event):
        """Process transitions for a single event."""
        all_transitions = []
        
        if self.dry_run:
            # In dry run mode, just check what would be processed
            return self._check_pending_transitions(event)
        
        try:
            # Process event-wide transitions
            event_transitions = stage_automation.process_automatic_transitions(event)
            all_transitions.extend(event_transitions)
            
            # Process zone-specific transitions
            for zone in event.zones.all():
                zone_transitions = stage_automation.process_automatic_transitions(event, zone)
                all_transitions.extend(zone_transitions)
            
            return all_transitions
            
        except Exception as e:
            logger.error(f'Failed to process transitions for event {event.id}: {e}')
            raise
    
    def _check_pending_transitions(self, event):
        """Check what transitions would be processed (dry run mode)."""
        pending_transitions = []
        now = timezone.now()
        
        # Check event-wide stages
        event_stages = PriceStage.objects.filter(
            event=event,
            scope=PriceStage.StageScope.EVENT_WIDE,
            is_active=True,
            auto_transition=True
        )
        
        for stage in event_stages:
            should_transition, reason = stage.should_transition()
            if should_transition:
                # Create a mock transition object for display
                mock_transition = type('MockTransition', (), {
                    'stage_from': stage,
                    'stage_to': stage.get_next_stage(),
                    'trigger_reason': reason,
                    'zone': None
                })()
                pending_transitions.append(mock_transition)
        
        # Check zone-specific stages
        for zone in event.zones.all():
            zone_stages = PriceStage.objects.filter(
                event=event,
                zone=zone,
                scope=PriceStage.StageScope.ZONE_SPECIFIC,
                is_active=True,
                auto_transition=True
            )
            
            for stage in zone_stages:
                should_transition, reason = stage.should_transition()
                if should_transition:
                    mock_transition = type('MockTransition', (), {
                        'stage_from': stage,
                        'stage_to': stage.get_next_stage(),
                        'trigger_reason': reason,
                        'zone': zone
                    })()
                    pending_transitions.append(mock_transition)
        
        return pending_transitions