"""
Views for cart item locking functionality.
"""

import json
import logging
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods, require_POST
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt

from .cart_lock_service import CartLockService

logger = logging.getLogger(__name__)


@require_POST
@login_required
def lock_cart_items(request):
    """Lock items when adding to cart."""
    
    try:
        data = json.loads(request.body)
        items_data = data.get('items', [])
        
        if not items_data:
            return JsonResponse({
                'success': False,
                'error': 'No items provided'
            }, status=400)
        
        # Get session key
        session_key = request.session.session_key
        if not session_key:
            request.session.create()
            session_key = request.session.session_key
        
        # Lock items
        success, created_locks, error_messages = CartLockService.lock_items(
            session_key=session_key,
            user=request.user,
            items_data=items_data
        )
        
        if success:
            locks_data = []
            for lock in created_locks:
                locks_data.append({
                    'item_key': lock.item_key,
                    'zone_name': lock.zone.name,
                    'seat_label': lock.seat.seat_label if lock.seat else None,
                    'quantity': lock.quantity,
                    'expires_at': lock.expires_at.isoformat(),
                    'time_remaining_seconds': int(lock.time_remaining.total_seconds()),
                    'price': str(lock.price_at_lock),
                })
            
            return JsonResponse({
                'success': True,
                'message': f'Locked {len(created_locks)} items',
                'locks': locks_data,
                'errors': error_messages if error_messages else None
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'Failed to lock items',
                'errors': error_messages
            }, status=400)
            
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    
    except Exception as e:
        logger.error(f"Error in lock_cart_items: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Internal server error'
        }, status=500)


@require_http_methods(["DELETE"])
@login_required
def release_cart_locks(request):
    """Release cart item locks."""
    
    try:
        # Get session key
        session_key = request.session.session_key
        if not session_key:
            return JsonResponse({
                'success': False,
                'error': 'No active session'
            }, status=400)
        
        # Get item keys from query params or request body
        item_keys = None
        
        if request.method == 'DELETE' and request.body:
            try:
                data = json.loads(request.body)
                item_keys = data.get('item_keys')
            except json.JSONDecodeError:
                pass
        
        if not item_keys:
            item_keys = request.GET.getlist('item_keys')
        
        # Release locks
        success, released_count = CartLockService.release_locks(
            session_key=session_key,
            item_keys=item_keys if item_keys else None
        )
        
        if success:
            return JsonResponse({
                'success': True,
                'message': f'Released {released_count} locks',
                'released_count': released_count
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'Failed to release locks'
            }, status=500)
            
    except Exception as e:
        logger.error(f"Error in release_cart_locks: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Internal server error'
        }, status=500)


@require_http_methods(["PUT"])
@login_required
def extend_cart_locks(request):
    """Extend cart item locks."""
    
    try:
        # Get session key
        session_key = request.session.session_key
        if not session_key:
            return JsonResponse({
                'success': False,
                'error': 'No active session'
            }, status=400)
        
        # Get extension minutes from request body
        minutes = CartLockService.DEFAULT_LOCK_DURATION_MINUTES
        
        if request.body:
            try:
                data = json.loads(request.body)
                minutes = data.get('minutes', minutes)
            except json.JSONDecodeError:
                pass
        
        # Extend locks
        success, extended_count = CartLockService.extend_locks(
            session_key=session_key,
            minutes=minutes
        )
        
        if success:
            return JsonResponse({
                'success': True,
                'message': f'Extended {extended_count} locks by {minutes} minutes',
                'extended_count': extended_count,
                'minutes': minutes
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'Failed to extend locks'
            }, status=500)
            
    except Exception as e:
        logger.error(f"Error in extend_cart_locks: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Internal server error'
        }, status=500)


@login_required
def get_cart_lock_status(request):
    """Get cart lock status for current session."""
    
    try:
        # Get session key
        session_key = request.session.session_key
        if not session_key:
            return JsonResponse({
                'success': False,
                'error': 'No active session'
            }, status=400)
        
        # Get lock status
        status_data = CartLockService.get_lock_status(session_key)
        
        return JsonResponse(status_data)
        
    except Exception as e:
        logger.error(f"Error in get_cart_lock_status: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Internal server error'
        }, status=500)


@require_POST
@csrf_exempt  # For cleanup endpoint called by Celery
def cleanup_expired_locks(request):
    """Cleanup expired locks (internal endpoint for Celery)."""
    
    try:
        # Verify this is an internal call (you might want to add authentication)
        # For now, we'll allow it but in production you should secure this
        
        expired_count = CartLockService.cleanup_expired_locks()
        
        return JsonResponse({
            'success': True,
            'message': f'Cleaned up {expired_count} expired locks',
            'expired_count': expired_count
        })
        
    except Exception as e:
        logger.error(f"Error in cleanup_expired_locks: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Internal server error'
        }, status=500)