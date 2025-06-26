# Templatetag es un módulo de funciones y filtros que cargas con {% load %} y puedes invocar donde te dé la gana.
# file: core/templatetags/math_filters.py

from django import template

register = template.Library()

@register.filter
def subtract(value, arg):
    """Resta arg de value"""
    try:
        return float(value) - float(arg)
    except (TypeError, ValueError):
        return 0