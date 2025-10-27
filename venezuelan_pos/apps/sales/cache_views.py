"""
API views for cached sales operations.
Provides high-performance endpoints for ticket validation and seat availability.
"""

import logging
from typing import Dict, Any

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from django.utils import timezone
from django.http import JsonResponse

from .cache import sales_cache
from .cache_utils import (
    get_seat_availability_cached,
    get_zone_availability_cached,
    get_event_availability_cached,
    get_ticket_status_cached
)
from .models import Transaction
from ..zones.models import Seat, Zone
from ..events.models import Event

logger = logging.getLogger(__name__)


class TicketValidationAPIView(APIView):
    """
    High-performance ticket validation endpoint.
    Uses Redis cache with database fallback for real-time validation.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, fiscal_series):
        """
        Validate ticket by fiscal series number.
        Returns cached ticket data or queries database on cache miss.
        """
        try:
            # Get ticket status from cache with database fallback
            ticket_data = get_ticket_status_cached(fiscal_series)
            
            if not ticket_data:
                return Response({
                    'error': 'Ticket not found',
                    'fiscal_series': fiscal_series
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Add validation timestamp
            ticket_data['validated_at'] = timezone.now().isoformat()
            ticket_data['cache_hit'] = True
            
            return Response({
                'status': 'valid',
                'ticket': ticket_data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Ticket validation error for {fiscal_series}: {e}")
            return Response({
                'error': 'Validation failed',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SeatAvailabilityAPIView(APIView):
    """
    Real-time seat availability endpoint.
    Provides cached seat status with automatic cache invalidation.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, seat_id):
        """Get seat availability status."""
        try:
            availability_data = get_seat_availability_cached(seat_id)
            
            if not availability_data:
                return Response({
                    'error': 'Seat not found',
                    'seat_id': seat_id
                }, status=status.HTTP_404_NOT_FOUND)
            
            return Response({
                'seat': availability_data,
                'timestamp': timezone.now().isoformat()
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Seat availability error for {seat_id}: {e}")
            return Response({
                'error': 'Failed to get seat availability',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ZoneAvailabilityAPIView(APIView):
    """
    Zone availability endpoint with seat-level details.
    Provides comprehensive zone status with all seat information.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, zone_id):
        """Get zone availability with all seats."""
        try:
            availability_data = get_zone_availability_cached(zone_id)
            
            if not availability_data:
                return Response({
                    'error': 'Zone not found',
                    'zone_id': zone_id
                }, status=status.HTTP_404_NOT_FOUND)
            
            return Response({
                'zone': availability_data,
                'timestamp': timezone.now().isoformat()
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Zone availability error for {zone_id}: {e}")
            return Response({
                'error': 'Failed to get zone availability',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class EventAvailabilityAPIView(APIView):
    """
    Event availability summary endpoint.
    Provides high-level availability across all zones.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, event_id):
        """Get event availability summary."""
        try:
            availability_data = get_event_availability_cached(event_id)
            
            if not availability_data:
                return Response({
                    'error': 'Event not found',
                    'event_id': event_id
                }, status=status.HTTP_404_NOT_FOUND)
            
            return Response({
                'event': availability_data,
                'timestamp': timezone.now().isoformat()
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Event availability error for {event_id}: {e}")
            return Response({
                'error': 'Failed to get event availability',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CacheManagementAPIView(APIView):
    """
    Cache management endpoint for administrative operations.
    Allows warming, clearing, and monitoring cache status.
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Perform cache management operations."""
        try:
            action = request.data.get('action')
            
            if action == 'warm_event':
                event_id = request.data.get('event_id')
                if not event_id:
                    return Response({
                        'error': 'event_id required for warm_event action'
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                try:
                    event = Event.objects.get(id=event_id)
                    success = sales_cache.warm_event_caches(event)
                    
                    return Response({
                        'action': 'warm_event',
                        'event_id': event_id,
                        'success': success,
                        'timestamp': timezone.now().isoformat()
                    })
                    
                except Event.DoesNotExist:
                    return Response({
                        'error': 'Event not found'
                    }, status=status.HTTP_404_NOT_FOUND)
            
            elif action == 'clear_all':
                success = sales_cache.clear_all_caches()
                
                return Response({
                    'action': 'clear_all',
                    'success': success,
                    'timestamp': timezone.now().isoformat()
                })
            
            elif action == 'health_check':
                health_data = sales_cache.health_check()
                
                return Response({
                    'action': 'health_check',
                    'health': health_data
                })
            
            else:
                return Response({
                    'error': 'Invalid action',
                    'valid_actions': ['warm_event', 'clear_all', 'health_check']
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"Cache management error: {e}")
            return Response({
                'error': 'Cache management failed',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def bulk_seat_availability(request):
    """
    Get availability for multiple seats in a single request.
    Optimized for seat selection interfaces.
    """
    try:
        seat_ids = request.GET.get('seat_ids', '').split(',')
        seat_ids = [sid.strip() for sid in seat_ids if sid.strip()]
        
        if not seat_ids:
            return Response({
                'error': 'seat_ids parameter required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if len(seat_ids) > 100:  # Limit to prevent abuse
            return Response({
                'error': 'Maximum 100 seats per request'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        results = {}
        for seat_id in seat_ids:
            availability_data = get_seat_availability_cached(seat_id)
            results[seat_id] = availability_data
        
        return Response({
            'seats': results,
            'timestamp': timezone.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Bulk seat availability error: {e}")
        return Response({
            'error': 'Failed to get bulk seat availability',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def cache_stats(request):
    """
    Get cache statistics and performance metrics.
    Useful for monitoring and debugging.
    """
    try:
        health_data = sales_cache.health_check()
        
        # Add additional stats if available
        stats = {
            'cache_health': health_data,
            'timestamp': timezone.now().isoformat(),
        }
        
        # Try to get Redis info if client is available
        if sales_cache._redis_client:
            try:
                redis_info = sales_cache._redis_client.info()
                stats['redis_info'] = {
                    'used_memory_human': redis_info.get('used_memory_human'),
                    'connected_clients': redis_info.get('connected_clients'),
                    'total_commands_processed': redis_info.get('total_commands_processed'),
                    'keyspace_hits': redis_info.get('keyspace_hits'),
                    'keyspace_misses': redis_info.get('keyspace_misses'),
                }
                
                # Calculate hit rate
                hits = redis_info.get('keyspace_hits', 0)
                misses = redis_info.get('keyspace_misses', 0)
                total = hits + misses
                hit_rate = (hits / total * 100) if total > 0 else 0
                stats['redis_info']['hit_rate_percent'] = round(hit_rate, 2)
                
            except Exception as redis_error:
                stats['redis_error'] = str(redis_error)
        
        return Response(stats)
        
    except Exception as e:
        logger.error(f"Cache stats error: {e}")
        return Response({
            'error': 'Failed to get cache stats',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)