from decimal import Decimal
from django.conf import settings
from products.models import ExchangeRate

def calculate_mxn_price(price_obj, user=None):
    if not price_obj or not price_obj.discount:
        return Decimal('0.00')
    usd_price = price_obj.discount
    latest_rate = ExchangeRate.objects.latest('created_at').rate
    base = usd_price * Decimal(latest_rate)
    base *= Decimal(1 + price_obj.margen_prod)
    base *= Decimal(1 - price_obj.descuento_prod)
    if user and user.is_authenticated:
        base *= Decimal(1 - user.descuento_cliente)
    base *= Decimal(1 + settings.IVA)
    return base.quantize(Decimal('0.01'))

def calculate_mxn_subtotal(price_obj, user=None):
    if not price_obj or not price_obj.discount:
        return Decimal('0.00')
    usd_price = price_obj.discount
    latest_rate = ExchangeRate.objects.latest('created_at').rate
    base = usd_price * Decimal(latest_rate)
    base *= Decimal(1 + price_obj.margen_prod)
    base *= Decimal(1 - price_obj.descuento_prod)
    if user and user.is_authenticated:
        base *= Decimal(1 - user.descuento_cliente)
    return base.quantize(Decimal('0.01')) 