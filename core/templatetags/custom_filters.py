# Templatetag es un módulo de funciones y filtros que cargas con {% load %} y puedes invocar donde te dé la gana.
# file: core/templatetags/custom_filters.py

from django import template
from urllib.parse import urlencode

register = template.Library()

@register.simple_tag(takes_context=True)  # Añadimos takes_context=True
def param_remove(context, key, value):  # Recibimos context automáticamente
    """
    Elimina un valor específico de un parámetro GET en la URL.
    Ejemplo de uso en template: 
    {% param_remove 'categoria' 123 %}
    """
    # Obtenemos los parámetros GET actuales
    params = context['request'].GET.copy()
    
    # Obtenemos todos los valores del parámetro como lista
    values = params.getlist(key)
    
    # Convertimos value a string para comparación consistente
    str_value = str(value)
    
    # Eliminamos el valor específico si existe
    if str_value in values:
        values.remove(str_value)
        params.setlist(key, values)
    
    # Devolvemos la cadena de consulta codificada
    return urlencode(params, doseq=True)

@register.filter
def get_item(queryset, id):
    """
    Filtro para obtener un elemento específico de un queryset por ID.
    Ejemplo de uso en template:
    {{ categorias|get_item:123 }}
    """
    try:
        # Buscamos el elemento con el ID coincidente
        return next(item for item in queryset if item.id == int(id))
    except (StopIteration, ValueError):
        return None