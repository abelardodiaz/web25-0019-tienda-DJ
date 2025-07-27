from django import template
from core.utils import validate_next_url

register = template.Library()

@register.filter
def safe_next_url(value, request):
    """Filtro para sanitizar URLs 'next' en plantillas"""
    return validate_next_url(value, request, fallback='/') 