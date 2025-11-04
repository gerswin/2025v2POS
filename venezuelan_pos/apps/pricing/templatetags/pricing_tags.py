"""
Template tags for pricing calculations.
"""

from django import template
from decimal import Decimal

register = template.Library()


@register.filter
def calculate_markup_amount(pricing, base_price):
    """Calculate markup amount for a given base price."""
    if not pricing or not base_price:
        return Decimal('0.00')
    
    try:
        base_price = Decimal(str(base_price))
        markup_decimal = pricing.percentage_markup / 100
        return base_price * markup_decimal
    except (ValueError, TypeError, AttributeError):
        return Decimal('0.00')


@register.filter
def calculate_final_price(pricing, base_price):
    """Calculate final price with markup applied."""
    if not pricing or not base_price:
        return Decimal('0.00')
    
    try:
        base_price = Decimal(str(base_price))
        markup_amount = calculate_markup_amount(pricing, base_price)
        return base_price + markup_amount
    except (ValueError, TypeError, AttributeError):
        return Decimal('0.00')


@register.filter
def multiply(value, arg):
    """Multiply two values."""
    try:
        return Decimal(str(value)) * Decimal(str(arg))
    except (ValueError, TypeError):
        return 0


@register.filter
def percentage_of(value, percentage):
    """Calculate percentage of a value."""
    try:
        value = Decimal(str(value))
        percentage = Decimal(str(percentage))
        return value * (percentage / 100)
    except (ValueError, TypeError):
        return 0


@register.filter
def get_item(dictionary, key):
    """Get item from dictionary by key."""
    try:
        return dictionary.get(key)
    except (AttributeError, TypeError):
        return None


@register.filter
def percentage(value, total):
    """Calculate percentage of value relative to total."""
    try:
        value = float(value)
        total = float(total)
        if total == 0:
            return 0
        return (value / total) * 100
    except (ValueError, TypeError, ZeroDivisionError):
        return 0


@register.filter
def timeuntil_hours(value):
    """Calculate hours until a datetime."""
    from django.utils import timezone
    try:
        if not value:
            return 0
        now = timezone.now()
        if value <= now:
            return 0
        delta = value - now
        return int(delta.total_seconds() / 3600)
    except (ValueError, TypeError, AttributeError):
        return 0


@register.filter
def timeuntil_days(value):
    """Calculate days until a datetime."""
    from django.utils import timezone
    try:
        if not value:
            return 0
        now = timezone.now()
        if value <= now:
            return 0
        delta = value - now
        return delta.days
    except (ValueError, TypeError, AttributeError):
        return 0


@register.simple_tag
def stage_status_badge(stage):
    """Generate status badge HTML for a price stage."""
    if not stage:
        return ""
    
    if stage.is_current:
        return '<span class="badge bg-success"><i class="bi bi-play-fill"></i> Current</span>'
    elif stage.is_upcoming:
        return '<span class="badge bg-warning"><i class="bi bi-clock"></i> Upcoming</span>'
    elif stage.is_past:
        return '<span class="badge bg-secondary"><i class="bi bi-check"></i> Past</span>'
    else:
        return '<span class="badge bg-light text-dark">Scheduled</span>'


@register.simple_tag
def modifier_badge(stage):
    """Generate modifier badge HTML for a price stage."""
    if not stage:
        return ""
    
    if stage.modifier_type == 'percentage':
        return f'<span class="badge bg-primary">{stage.modifier_value}%</span>'
    else:
        return f'<span class="badge bg-primary">${stage.modifier_value}</span>'


@register.simple_tag
def scope_badge(stage):
    """Generate scope badge HTML for a price stage."""
    if not stage:
        return ""
    
    if stage.scope == 'zone' and stage.zone:
        return f'<span class="badge bg-info">{stage.zone.name}</span>'
    else:
        return '<span class="badge bg-primary">Event-wide</span>'