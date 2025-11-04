"""
Validation functions for pricing stage configuration.
Prevents overlapping dates, capacity conflicts, and other configuration issues.
"""

import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db.models import Q, Sum

from .models import PriceStage
from ..events.models import Event
from ..zones.models import Zone

logger = logging.getLogger(__name__)


class StageConfigurationValidator:
    """
    Validator for pricing stage configuration.
    Ensures proper stage setup and prevents conflicts.
    """
    
    @staticmethod
    def validate_stage_dates(
        event: Event,
        start_date: datetime,
        end_date: datetime,
        scope: str,
        zone: Optional[Zone] = None,
        exclude_stage_id: Optional[str] = None
    ) -> Tuple[bool, List[str]]:
        """
        Validate that stage dates don't overlap with existing stages.
        
        Args:
            event: Event the stage belongs to
            start_date: Stage start date
            end_date: Stage end date
            scope: Stage scope (event or zone)
            zone: Zone for zone-specific stages
            exclude_stage_id: Stage ID to exclude from validation (for updates)
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Basic date validation
        if start_date >= end_date:
            errors.append("End date must be after start date")
            return False, errors
        
        # Check if dates are in the past
        now = timezone.now()
        if end_date <= now:
            errors.append("Stage end date cannot be in the past")
        
        if start_date <= now:
            errors.append("Stage start date should not be in the past")
        
        # Check for overlapping stages
        overlapping_stages = PriceStage.objects.filter(
            event=event,
            is_active=True,
            scope=scope
        )
        
        # Filter by zone for zone-specific stages
        if scope == PriceStage.StageScope.ZONE_SPECIFIC:
            if not zone:
                errors.append("Zone must be specified for zone-specific stages")
                return False, errors
            overlapping_stages = overlapping_stages.filter(zone=zone)
        else:
            overlapping_stages = overlapping_stages.filter(zone__isnull=True)
        
        # Exclude current stage if updating
        if exclude_stage_id:
            overlapping_stages = overlapping_stages.exclude(id=exclude_stage_id)
        
        # Check for date overlaps
        for stage in overlapping_stages:
            if stage.start_date and stage.end_date:
                # Check if date ranges overlap
                if (start_date < stage.end_date and end_date > stage.start_date):
                    scope_desc = f"zone {zone.name}" if zone else "event"
                    errors.append(
                        f'Date range overlaps with "{stage.name}" stage in {scope_desc} '
                        f'({stage.start_date.strftime("%Y-%m-%d %H:%M")} - '
                        f'{stage.end_date.strftime("%Y-%m-%d %H:%M")})'
                    )
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_stage_quantity_limits(
        event: Event,
        quantity_limit: Optional[int],
        scope: str,
        zone: Optional[Zone] = None
    ) -> Tuple[bool, List[str]]:
        """
        Validate quantity limits against available capacity.
        
        Args:
            event: Event the stage belongs to
            quantity_limit: Proposed quantity limit
            scope: Stage scope (event or zone)
            zone: Zone for zone-specific stages
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        if not quantity_limit:
            return True, errors  # No limit is valid
        
        if quantity_limit <= 0:
            errors.append("Quantity limit must be positive")
            return False, errors
        
        # Check against capacity
        if scope == PriceStage.StageScope.ZONE_SPECIFIC:
            if not zone:
                errors.append("Zone must be specified for zone-specific stages")
                return False, errors
            
            if quantity_limit > zone.capacity:
                errors.append(
                    f"Quantity limit ({quantity_limit}) cannot exceed zone capacity ({zone.capacity})"
                )
        else:
            # Event-wide stage - check against total event capacity
            total_capacity = event.zones.aggregate(
                total=Sum('capacity')
            )['total'] or 0
            
            if total_capacity > 0 and quantity_limit > total_capacity:
                errors.append(
                    f"Quantity limit ({quantity_limit}) cannot exceed event capacity ({total_capacity})"
                )
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_stage_sequence(
        event: Event,
        stage_order: int,
        start_date: datetime,
        end_date: datetime,
        scope: str,
        zone: Optional[Zone] = None,
        exclude_stage_id: Optional[str] = None
    ) -> Tuple[bool, List[str]]:
        """
        Validate that stages are in proper chronological sequence.
        
        Args:
            event: Event the stage belongs to
            stage_order: Proposed stage order
            start_date: Stage start date
            end_date: Stage end date
            scope: Stage scope
            zone: Zone for zone-specific stages
            exclude_stage_id: Stage ID to exclude from validation
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Get other stages in the same scope
        other_stages = PriceStage.objects.filter(
            event=event,
            is_active=True,
            scope=scope
        )
        
        if scope == PriceStage.StageScope.ZONE_SPECIFIC and zone:
            other_stages = other_stages.filter(zone=zone)
        else:
            other_stages = other_stages.filter(zone__isnull=True)
        
        if exclude_stage_id:
            other_stages = other_stages.exclude(id=exclude_stage_id)
        
        # Check chronological order
        for stage in other_stages:
            if stage.stage_order < stage_order:
                # Earlier stage should end before this stage starts
                if stage.end_date and stage.end_date > start_date:
                    errors.append(
                        f'Stage "{stage.name}" (order {stage.stage_order}) ends after '
                        f'this stage starts. Stages should be in chronological order.'
                    )
            elif stage.stage_order > stage_order:
                # Later stage should start after this stage ends
                if stage.start_date and stage.start_date < end_date:
                    errors.append(
                        f'Stage "{stage.name}" (order {stage.stage_order}) starts before '
                        f'this stage ends. Stages should be in chronological order.'
                    )
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_stage_configuration(
        event: Event,
        name: str,
        start_date: datetime,
        end_date: datetime,
        quantity_limit: Optional[int],
        modifier_type: str,
        modifier_value: float,
        scope: str,
        stage_order: int,
        zone: Optional[Zone] = None,
        exclude_stage_id: Optional[str] = None
    ) -> Tuple[bool, List[str]]:
        """
        Comprehensive validation of stage configuration.
        
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        all_errors = []
        
        # Basic field validation
        if not name or not name.strip():
            all_errors.append("Stage name is required")
        
        if modifier_value < 0:
            all_errors.append("Modifier value cannot be negative")
        
        if stage_order < 0:
            all_errors.append("Stage order cannot be negative")
        
        # Date validation
        date_valid, date_errors = StageConfigurationValidator.validate_stage_dates(
            event, start_date, end_date, scope, zone, exclude_stage_id
        )
        all_errors.extend(date_errors)
        
        # Quantity validation
        quantity_valid, quantity_errors = StageConfigurationValidator.validate_stage_quantity_limits(
            event, quantity_limit, scope, zone
        )
        all_errors.extend(quantity_errors)
        
        # Sequence validation (only if dates are valid)
        if date_valid:
            sequence_valid, sequence_errors = StageConfigurationValidator.validate_stage_sequence(
                event, stage_order, start_date, end_date, scope, zone, exclude_stage_id
            )
            all_errors.extend(sequence_errors)
        
        return len(all_errors) == 0, all_errors
    
    @staticmethod
    def validate_event_stage_coverage(event: Event) -> Tuple[bool, List[str], Dict]:
        """
        Validate that event has proper stage coverage.
        Checks for gaps in stage coverage and provides recommendations.
        
        Returns:
            Tuple of (is_valid, list_of_warnings, coverage_info)
        """
        warnings = []
        coverage_info = {
            'event_wide_stages': [],
            'zone_specific_stages': {},
            'coverage_gaps': [],
            'recommendations': []
        }
        
        # Get event-wide stages
        event_stages = PriceStage.objects.filter(
            event=event,
            scope=PriceStage.StageScope.EVENT_WIDE,
            is_active=True
        ).order_by('stage_order', 'start_date')
        
        coverage_info['event_wide_stages'] = [
            {
                'name': stage.name,
                'start_date': stage.start_date,
                'end_date': stage.end_date,
                'quantity_limit': stage.quantity_limit,
                'modifier_value': stage.modifier_value
            }
            for stage in event_stages
        ]
        
        # Check for gaps in event-wide coverage
        if event_stages.exists():
            previous_end = None
            for stage in event_stages:
                if previous_end and stage.start_date > previous_end:
                    gap_duration = stage.start_date - previous_end
                    if gap_duration.total_seconds() > 3600:  # More than 1 hour gap
                        coverage_info['coverage_gaps'].append({
                            'type': 'event_wide',
                            'gap_start': previous_end,
                            'gap_end': stage.start_date,
                            'duration_hours': gap_duration.total_seconds() / 3600
                        })
                        warnings.append(
                            f"Gap in event-wide stage coverage from "
                            f"{previous_end.strftime('%Y-%m-%d %H:%M')} to "
                            f"{stage.start_date.strftime('%Y-%m-%d %H:%M')}"
                        )
                previous_end = stage.end_date
        
        # Get zone-specific stages
        for zone in event.zones.all():
            zone_stages = PriceStage.objects.filter(
                event=event,
                zone=zone,
                scope=PriceStage.StageScope.ZONE_SPECIFIC,
                is_active=True
            ).order_by('stage_order', 'start_date')
            
            if zone_stages.exists():
                coverage_info['zone_specific_stages'][zone.name] = [
                    {
                        'name': stage.name,
                        'start_date': stage.start_date,
                        'end_date': stage.end_date,
                        'quantity_limit': stage.quantity_limit,
                        'modifier_value': stage.modifier_value
                    }
                    for stage in zone_stages
                ]
                
                # Check for gaps in zone coverage
                previous_end = None
                for stage in zone_stages:
                    if previous_end and stage.start_date > previous_end:
                        gap_duration = stage.start_date - previous_end
                        if gap_duration.total_seconds() > 3600:
                            coverage_info['coverage_gaps'].append({
                                'type': 'zone_specific',
                                'zone': zone.name,
                                'gap_start': previous_end,
                                'gap_end': stage.start_date,
                                'duration_hours': gap_duration.total_seconds() / 3600
                            })
                            warnings.append(
                                f"Gap in {zone.name} stage coverage from "
                                f"{previous_end.strftime('%Y-%m-%d %H:%M')} to "
                                f"{stage.start_date.strftime('%Y-%m-%d %H:%M')}"
                            )
                    previous_end = stage.end_date
        
        # Generate recommendations
        if not event_stages.exists() and not any(coverage_info['zone_specific_stages'].values()):
            coverage_info['recommendations'].append(
                "Consider creating pricing stages to implement dynamic pricing"
            )
        
        if event_stages.exists() and coverage_info['zone_specific_stages']:
            coverage_info['recommendations'].append(
                "You have both event-wide and zone-specific stages. "
                "Zone-specific stages will take precedence over event-wide stages."
            )
        
        if coverage_info['coverage_gaps']:
            coverage_info['recommendations'].append(
                "Consider filling gaps in stage coverage or ensure gaps are intentional"
            )
        
        return len(warnings) == 0, warnings, coverage_info
    
    @staticmethod
    def get_stage_conflicts(event: Event) -> List[Dict]:
        """
        Get detailed information about stage conflicts.
        
        Returns:
            List of conflict descriptions
        """
        conflicts = []
        
        # Check event-wide stage conflicts
        event_stages = PriceStage.objects.filter(
            event=event,
            scope=PriceStage.StageScope.EVENT_WIDE,
            is_active=True
        ).order_by('start_date')
        
        conflicts.extend(
            StageConfigurationValidator._check_stage_list_conflicts(
                event_stages, "Event-wide"
            )
        )
        
        # Check zone-specific stage conflicts
        for zone in event.zones.all():
            zone_stages = PriceStage.objects.filter(
                event=event,
                zone=zone,
                scope=PriceStage.StageScope.ZONE_SPECIFIC,
                is_active=True
            ).order_by('start_date')
            
            conflicts.extend(
                StageConfigurationValidator._check_stage_list_conflicts(
                    zone_stages, f"Zone {zone.name}"
                )
            )
        
        return conflicts
    
    @staticmethod
    def _check_stage_list_conflicts(stages, scope_name: str) -> List[Dict]:
        """Check conflicts within a list of stages."""
        conflicts = []
        stage_list = list(stages)
        
        for i, stage1 in enumerate(stage_list):
            for stage2 in stage_list[i+1:]:
                # Check date overlap
                if (stage1.start_date < stage2.end_date and 
                    stage1.end_date > stage2.start_date):
                    conflicts.append({
                        'type': 'date_overlap',
                        'scope': scope_name,
                        'stage1': {
                            'id': str(stage1.id),
                            'name': stage1.name,
                            'start_date': stage1.start_date,
                            'end_date': stage1.end_date
                        },
                        'stage2': {
                            'id': str(stage2.id),
                            'name': stage2.name,
                            'start_date': stage2.start_date,
                            'end_date': stage2.end_date
                        },
                        'description': f"Stages '{stage1.name}' and '{stage2.name}' have overlapping dates"
                    })
                
                # Check quantity limit conflicts
                if (stage1.quantity_limit and stage2.quantity_limit and
                    stage1.quantity_limit + stage2.quantity_limit > 
                    (stage1.zone.capacity if stage1.zone else 
                     stage1.event.zones.aggregate(Sum('capacity'))['capacity__sum'] or 0)):
                    conflicts.append({
                        'type': 'quantity_conflict',
                        'scope': scope_name,
                        'stage1': stage1.name,
                        'stage2': stage2.name,
                        'description': f"Combined quantity limits exceed available capacity"
                    })
        
        return conflicts