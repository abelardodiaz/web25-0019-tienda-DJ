from decimal import Decimal
from django.conf import settings
from products.models import ExchangeRate
from django.utils.http import url_has_allowed_host_and_scheme

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

def validate_next_url(next_url, request, fallback='/'):
    """
    Valida URLs de redirección (next) para prevenir:
    - Redirecciones maliciosas
    - Bucles en páginas de autenticación
    - Hosts no permitidos
    """
    # 1. Validación básica
    if not next_url:
        return fallback
    
    # 2. Bloquear rutas de autenticación
    auth_paths = ['/login/', '/register/', '/logout/', '/password-reset/']
    if any(next_url.startswith(path) for path in auth_paths):
        return fallback
    
    # 3. Validar host y esquema
    allowed_hosts = settings.ALLOWED_HOSTS
    if request:  # Incluir host actual si está disponible
        allowed_hosts = [request.get_host()] + list(allowed_hosts)
    
    is_safe = url_has_allowed_host_and_scheme(
        url=next_url,
        allowed_hosts=allowed_hosts,
        require_https=request.is_secure() if request else False
    )
    
    return next_url if is_safe else fallback 