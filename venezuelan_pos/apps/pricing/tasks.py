"""
Celery tasks for pricing stage automation.
Handles scheduled monitoring and transition processing.
"""

import logging
from celery import shared_task
from django.utils import timezone
from django.db.models import Q

from .stage_automation import stage_automation
from .models import PriceStage, StageTransition
from ..events.models import Event

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def monitor_stage_transitions(self, tenant_id=None, event_id=None):
    """
    Monitor and process automatic stage transitions.
    
    Args:
        tenant_id: Optional tenant ID to limit processing
        event_id: Optional event ID to process specific event
    
    Returns:
        Dict with processing results
    """
    try:
        logger.info(f"Starting stage transition monitoring task")
        
        # Get events to process
        events = _get_events_for_monitoring(tenant_id, event_id)
        
        results = {
            'events_processed': 0,
            'transitions_created': 0,
            'errors': [],
            'processing_time_ms': 0,
            'timestamp': timezone.now().isoformat()
        }
        
        start_time = timezone.now()
        
        for event in events:
            try:
                event_results = _process_event_transitions(event)
                results['events_processed'] += 1
                results['transitions_created'] += event_results['transitions_count']
                
                logger.info(
                    f"Processed event {event.id}: "
                    f"{event_results['transitions_count']} transitions"
                )
                
            except Exception as e:
                error_msg = f"Error processing event {event.id}: {str(e)}"
                results['errors'].append(error_msg)
                logger.error(error_msg, exc_info=True)
        
        end_time = timezone.now()
        results['processing_time_ms'] = int(
            (end_time - start_time).total_seconds() * 1000
        )
        
        logger.info(
            f"Stage transition monitoring completed: "
            f"{results['events_processed']} events, "
            f"{results['transitions_created']} transitions, "
            f"{len(results['errors'])} errors"
        )
        
        return results
        
    except Exception as e:
        logger.error(f"Stage transition monitoring task failed: {e}", exc_info=True)
        
        # Retry with exponential backoff
        if self.request.retries < self.max_retries:
            retry_delay = 60 * (2 ** self.request.retries)  # 60s, 120s, 240s
            raise self.retry(countdown=retry_delay, exc=e)
        
        raise


@shared_task
def cleanup_expired_stage_reservations():
    """
    Clean up expired stage reservations from Redis cache.
    Should be run periodically to prevent memory leaks.
    """
    try:
        logger.info("Starting cleanup of expired stage reservations")
        
        # Use the automation service to clean up
        health_status = stage_automation.health_check()
        
        if health_status.get('status') != 'healthy':
            logger.warning(
                f"Stage automation service not healthy: {health_status.get('status')}"
            )
            return {
                'status': 'skipped',
                'reason': 'Service not healthy',
                'health_status': health_status
            }
        
        # The Redis TTL will automatically expire reservations,
        # but we can do additional cleanup here if needed
        
        return {
            'status': 'completed',
            'timestamp': timezone.now().isoformat(),
            'health_status': health_status
        }
        
    except Exception as e:
        logger.error(f"Cleanup task failed: {e}", exc_info=True)
        raise


@shared_task
def warm_stage_caches(event_id=None, tenant_id=None):
    """
    Warm up stage status caches for active events.
    Useful for improving response times during peak periods.
    """
    try:
        logger.info("Starting stage cache warming")
        
        events = _get_events_for_monitoring(tenant_id, event_id)
        
        results = {
            'events_processed': 0,
            'stages_cached': 0,
            'errors': [],
            'timestamp': timezone.now().isoformat()
        }
        
        for event in events:
            try:
                # Get all active stages for the event
                stages = PriceStage.objects.filter(
                    event=event,
                    is_active=True
                )
                
                for stage in stages:
                    # This will calculate and cache the stage status
                    stage_automation.get_stage_status_cached(stage)
                    results['stages_cached'] += 1
                
                results['events_processed'] += 1
                
            except Exception as e:
                error_msg = f"Error warming caches for event {event.id}: {str(e)}"
                results['errors'].append(error_msg)
                logger.error(error_msg)
        
        logger.info(
            f"Stage cache warming completed: "
            f"{results['events_processed']} events, "
            f"{results['stages_cached']} stages cached"
        )
        
        return results
        
    except Exception as e:
        logger.error(f"Cache warming task failed: {e}", exc_info=True)
        raise


@shared_task
def generate_transition_report(days=7, tenant_id=None):
    """
    Generate a report of stage transitions over the specified period.
    
    Args:
        days: Number of days to include in the report
        tenant_id: Optional tenant ID to limit report scope
    
    Returns:
        Dict with transition statistics
    """
    try:
        logger.info(f"Generating transition report for last {days} days")
        
        since_date = timezone.now() - timezone.timedelta(days=days)
        
        # Base query for transitions
        transitions_query = StageTransition.objects.filter(
            transition_at__gte=since_date
        )
        
        if tenant_id:
            transitions_query = transitions_query.filter(tenant_id=tenant_id)
        
        # Get transition statistics
        total_transitions = transitions_query.count()
        
        # Group by trigger reason
        trigger_stats = {}
        for reason in StageTransition.TriggerReason.choices:
            count = transitions_query.filter(trigger_reason=reason[0]).count()
            trigger_stats[reason[1]] = count
        
        # Group by event
        event_stats = {}
        for transition in transitions_query.select_related('event'):
            event_name = transition.event.name
            if event_name not in event_stats:
                event_stats[event_name] = {
                    'event_id': str(transition.event.id),
                    'total_transitions': 0,
                    'date_expired': 0,
                    'quantity_reached': 0,
                    'manual': 0
                }
            
            event_stats[event_name]['total_transitions'] += 1
            
            if transition.trigger_reason == StageTransition.TriggerReason.DATE_EXPIRED:
                event_stats[event_name]['date_expired'] += 1
            elif transition.trigger_reason == StageTransition.TriggerReason.QUANTITY_REACHED:
                event_stats[event_name]['quantity_reached'] += 1
            elif transition.trigger_reason == StageTransition.TriggerReason.MANUAL:
                event_stats[event_name]['manual'] += 1
        
        report = {
            'period_days': days,
            'report_generated_at': timezone.now().isoformat(),
            'total_transitions': total_transitions,
            'trigger_reason_breakdown': trigger_stats,
            'event_breakdown': event_stats,
            'tenant_id': tenant_id
        }
        
        logger.info(
            f"Transition report generated: {total_transitions} transitions "
            f"across {len(event_stats)} events"
        )
        
        return report
        
    except Exception as e:
        logger.error(f"Transition report generation failed: {e}", exc_info=True)
        raise


def _get_events_for_monitoring(tenant_id=None, event_id=None):
    """Get events that need transition monitoring."""
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


def _process_event_transitions(event):
    """Process transitions for a single event."""
    transitions_count = 0
    
    # Process event-wide transitions
    event_transitions = stage_automation.process_automatic_transitions(event)
    transitions_count += len(event_transitions)
    
    # Process zone-specific transitions
    for zone in event.zones.all():
        zone_transitions = stage_automation.process_automatic_transitions(event, zone)
        transitions_count += len(zone_transitions)
    
    return {
        'event_id': str(event.id),
        'transitions_count': transitions_count
    }