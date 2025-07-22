# file: catalogo/context_processors.py
from products.models import Category, Brand
from decimal import Decimal
from django.conf import settings

def categorias_marcas(request):
    """
    Devuelve todas las categorías y marcas ordenadas alfabéticamente
    para usarlas en el footer y donde se necesiten.
    """
    return {
        "footer_categorias": Category.objects.order_by("name"),
        "footer_marcas":    Brand.objects.order_by("name"),
    }

def cart_summary(request):
    cart = request.session.get('cart', {})
    cart_items = []
    total_sub = Decimal('0.00')
    cart_count = 0
    for prod_id, data in cart.items():
        price = Decimal(data['price'])
        qty = data['qty']
        item_total = price * Decimal(qty)
        cart_items.append({
            'title': data['title'],
            'price': price.quantize(Decimal('0.01')),
            'qty': qty,
            'total': item_total.quantize(Decimal('0.01')),
            'slug': data['slug'],
            'image': data.get('image', '')
        })
        total_sub += item_total
        cart_count += qty
    iva = (total_sub * Decimal(settings.IVA)).quantize(Decimal('0.01'))
    grand_total = (total_sub + iva).quantize(Decimal('0.01'))
    return {
        'cart_items': cart_items,
        'cart_count': cart_count,
        'total_sub': total_sub,
        'iva': iva,
        'grand_total': grand_total
    }
