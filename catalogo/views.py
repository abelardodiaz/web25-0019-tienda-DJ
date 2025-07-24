# catalogo/views.js
from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.db.models import Q, Sum, OuterRef, Subquery, DecimalField, Prefetch,  IntegerField
from products.models import Product, Price, BranchStock, Branch, Category, Brand  # Asegúrate de importar los modelos necesarios
from django.http import JsonResponse
from .agent import run_agent
from django.http import StreamingHttpResponse
from core.utils import calculate_mxn_price, calculate_mxn_subtotal
from decimal import Decimal
from django.conf import settings
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.urls import reverse
from django.db.models import Q

SLP_SLUG = "san_luis_potosi"


def catalogo_publico(request):
    # Obtener parámetros de búsqueda y filtros
    search_query = request.GET.get('q', '')
    categorias_seleccionadas = request.GET.getlist('categoria')
    marcas_seleccionadas = request.GET.getlist('marca')
    
    # Optimización: Prefetch para stock de SLP
    try:
        slp_branch = Branch.objects.get(slug=SLP_SLUG)
        slp_stock_qs = BranchStock.objects.filter(branch=slp_branch)
    except Branch.DoesNotExist:
        slp_branch = None
        slp_stock_qs = BranchStock.objects.none()

    # Construir queryset base
    productos_list = (
        Product.objects
        .filter(visible=True)
        .select_related("brand")
        .prefetch_related(
            Prefetch('branch_stocks', queryset=slp_stock_qs, to_attr='slp_stocks')
        )
        .annotate(
            slp_stock_sum=Sum(
                'branch_stocks__quantity',
                filter=Q(branch_stocks__branch__slug=SLP_SLUG)
            )
        )
        .order_by('-created_at')
    )
    
    # Aplicar filtro de búsqueda si existe
    if search_query:
        productos_list = productos_list.filter(
            Q(title__icontains=search_query) | 
            Q(description__icontains=search_query) |
            Q(brand__name__icontains=search_query)
        )
    
    # Aplicar filtros de categorías
    if categorias_seleccionadas:
        productos_list = productos_list.filter(categories__slug__in=categorias_seleccionadas)
    
    # Aplicar filtros de marcas
    if marcas_seleccionadas:
        productos_list = productos_list.filter(brand__slug__in=marcas_seleccionadas)
    
    # Obtener todas las categorías y marcas para el panel de filtros
    categorias = Category.objects.all()
    marcas = Brand.objects.all()
    
    # Paginación (12 productos por página)
    paginator = Paginator(productos_list, 12)
    page_number = request.GET.get('page')
    productos = paginator.get_page(page_number)
    
    for p in productos:
        if hasattr(p, 'prices') and p.prices.discount:
            p.mxn_price = calculate_mxn_price(p.prices, request.user)
        else:
            p.mxn_price = None

    return render(request, 'catalogo/cat_completo.html', {
        'productos': productos,
        'categorias': categorias,
        'marcas': marcas,
        'categorias_seleccionadas': categorias_seleccionadas,
        'marcas_seleccionadas': marcas_seleccionadas,
    })
def detalle_producto(request, slug):
    # Recupera el producto con sus relaciones y el stock SLP
    producto = get_object_or_404(
        Product.objects
               .select_related('brand')
               .prefetch_related('features', 'categories', 'additional_images')
               .annotate(
                   slp_stock_quantity=Sum(
                       'branch_stocks__quantity',
                       filter=Q(branch_stocks__branch__slug=SLP_SLUG)
                   )
               )
               .filter(visible=True),
        slug=slug
    )

    # Consulta para poblar el panel de filtros
    categorias = Category.objects.order_by('name')
    marcas     = Brand.objects.order_by('name')

    # Lee qué filtros vinieron en la URL (GET)
    categorias_seleccionadas = request.GET.getlist('categoria')
    marcas_seleccionadas     = request.GET.getlist('marca')

    # Construir breadcrumb de categorías (raíz ➜ hoja)
    breadcrumb_categories = []
    # Tomar la categoría de nivel más profundo
    deepest_cat = (
        producto.categories.all().order_by('-level').first()
    )
    cat = deepest_cat
    while cat:
        breadcrumb_categories.insert(0, cat)
        cat = cat.parent

    # Contexto completo
    context = {
        'producto': producto,
        'clean_description': producto.clean_description(),
        'categorias': categorias,
        'marcas': marcas,
        'categorias_seleccionadas': categorias_seleccionadas,
        'marcas_seleccionadas': marcas_seleccionadas,
        'breadcrumb_categories': breadcrumb_categories,
        'mxn_price': calculate_mxn_price(producto.prices, request.user),
    }

    return render(request, 'catalogo/cat_detalle.html', context)

def agente_chat(request):
    if request.method == 'POST':
        if request.POST.get('clear_chat'):
            initial_msg = "¡Hola! Soy <strong>TU ASISTENTE CHIDO</strong>. ¿En qué te ayudo hoy?<br>Di algo como 'busca cámaras' para empezar."
            request.session['chat_history'] = [{'type': 'agent', 'content': initial_msg}]
            request.session.pop('last_search_ids', None)
            request.session.pop('last_product_details', None)
            return JsonResponse({'status': 'cleared', 'greeting': initial_msg})
        
        user_input = request.POST.get('mensaje', '').strip()
        if user_input:
            response = run_agent(request, user_input)
            return JsonResponse({'respuesta': response})
        
    # Handle GET requests for initial page load
    historial = request.session.get('chat_history', [])
    if not historial:
        initial_msg = "¡Hola! Soy <strong>TU ASISTENTE CHIDO</strong>. ¿En qué te ayudo hoy?<br>Di algo como 'busca cámaras' para empezar."
        historial = [{'type': 'agent', 'content': initial_msg}]
        request.session['chat_history'] = historial
    
    return render(request, 'catalogo/agente.html', {'historial': historial})

@require_POST
def add_to_cart(request, slug):
    product = get_object_or_404(Product, slug=slug)
    cart = request.session.get('cart', {})
    prod_id = str(product.id)
    subtotal = calculate_mxn_subtotal(product.prices, request.user)
    subtotal_str = str(subtotal)
    image_url = product.additional_images.first().url if product.additional_images.exists() else ''
    
    if prod_id in cart:
        cart[prod_id]['qty'] += 1
    else:
        cart[prod_id] = {
            'qty': 1,
            'price': subtotal_str,
            'title': product.title,
            'slug': product.slug,
            'image': image_url
        }
    
    request.session['cart'] = cart
    cart_count = sum(item['qty'] for item in cart.values())
    
    # Compute detailed cart data for JSON response
    cart_items = []
    total_sub = Decimal('0.00')
    for prod_id, data in cart.items():
        price = Decimal(data['price'])
        qty = data['qty']
        item_total = price * Decimal(qty)
        cart_items.append({
            'image': data.get('image', ''),
            'title': data['title'],
            'price': float(price.quantize(Decimal('0.01'))),
            'qty': qty,
            'total': float(item_total.quantize(Decimal('0.01')))
        })
        total_sub += item_total
    iva = (total_sub * Decimal(settings.IVA)).quantize(Decimal('0.01'))
    grand_total = (total_sub + iva).quantize(Decimal('0.01'))
    
    return JsonResponse({
        'success': True,
        'cart_count': cart_count,
        'cart_items': cart_items,
        'grand_total': float(grand_total)
    })

@require_POST
def update_cart(request):
    action = request.POST.get('action')
    cart = request.session.get('cart', {})
    if action == 'clear':
        cart.clear()
    elif action == 'remove':
        prod_id = request.POST.get('prod_id')
        if prod_id in cart:
            del cart[prod_id]
    elif action == 'update_qty':
        prod_id = request.POST.get('prod_id')
        qty = int(request.POST.get('qty', 1))
        if prod_id in cart and qty > 0:
            cart[prod_id]['qty'] = qty
        elif qty <= 0 and prod_id in cart:
            del cart[prod_id]
    request.session['cart'] = cart
    # Recalculate totals for response
    total_sub = Decimal('0.00')
    cart_count = 0
    for data in cart.values():
        price = Decimal(data['price'])
        item_total = price * Decimal(data['qty'])
        total_sub += item_total
        cart_count += data['qty']
    iva = (total_sub * Decimal(settings.IVA)).quantize(Decimal('0.01'))
    grand_total = (total_sub + iva).quantize(Decimal('0.01'))
    return JsonResponse({
        'success': True,
        'cart_count': cart_count,
        'total_sub': str(total_sub),
        'iva': str(iva),
        'grand_total': str(grand_total)
    })

def cart_view(request):
    cart = request.session.get('cart', {})
    cart_items = []
    total_sub = Decimal('0.00')
    for prod_id, data in cart.items():
        price = Decimal(data['price'])
        qty = data['qty']
        item_total = price * Decimal(qty)
        cart_items.append({
            'prod_id': prod_id,
            'title': data['title'],
            'price': price.quantize(Decimal('0.01')),
            'qty': qty,
            'total': item_total.quantize(Decimal('0.01')),
            'slug': data['slug'],
            'image': data.get('image', '')
        })
        total_sub += item_total
    iva = (total_sub * Decimal(settings.IVA)).quantize(Decimal('0.01'))
    grand_total = (total_sub + iva).quantize(Decimal('0.01'))
    context = {
        'cart_items': cart_items,
        'total_sub': total_sub,
        'iva': iva,
        'grand_total': grand_total
    }
    return render(request, 'catalogo/canasta.html', context)

def instant_search(request):
    query = request.GET.get('q', '')
    results = []
    if query:
        products = Product.objects.filter(
            Q(title__icontains=query) | 
            Q(description__icontains=query)
        )[:5]  # Reduced from 10 to 5 for faster response
        results = [{
            'name': p.title,
            'price': f"${calculate_mxn_price(p.prices, request.user) if p.prices else Decimal('0.00')}",
            'url': reverse('detalle_producto', kwargs={'slug': p.slug}),
            'image': p.main_image if p.main_image else ''
        } for p in products]
    return JsonResponse({'results': results})