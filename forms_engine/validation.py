"""Validate question rules independently of browser controls and draft completeness."""
from decimal import Decimal, InvalidOperation
from django.core.exceptions import ValidationError


def finite_number(value):
    if isinstance(value, bool) or not isinstance(value, (str, int, float, Decimal)):
        raise ValidationError('Enter a finite number.')
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        raise ValidationError('Enter a finite number.')
    if not number.is_finite():
        raise ValidationError('Enter a finite number.')
    return number


def validate_rules(rules):
    if not isinstance(rules, dict):
        raise ValidationError('Question validation rules must be an object.')
    bounds = {}
    for key in ('min', 'max'):
        if key in rules and rules[key] is not None:
            bounds[key] = finite_number(rules[key])
    if 'min' in bounds and 'max' in bounds and bounds['min'] > bounds['max']:
        raise ValidationError('The minimum must not exceed the maximum.')
    lengths = {}
    for key in ('min_length', 'max_length'):
        if key in rules and rules[key] is not None:
            value = rules[key]
            if type(value) is not int or value < 0:
                raise ValidationError('Text length limits must be non-negative whole numbers.')
            lengths[key] = value
    if lengths.get('min_length', 0) > lengths.get('max_length', float('inf')):
        raise ValidationError('The minimum text length must not exceed the maximum.')
