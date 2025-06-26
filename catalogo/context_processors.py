# file: catalogo/context_processors.py
from products.models import Category, Brand

def categorias_marcas(request):
    """
    Devuelve todas las categorías y marcas ordenadas alfabéticamente
    para usarlas en el footer y donde se necesiten.
    """
    return {
        "footer_categorias": Category.objects.order_by("name"),
        "footer_marcas":    Brand.objects.order_by("name"),
    }
