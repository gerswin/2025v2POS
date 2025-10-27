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