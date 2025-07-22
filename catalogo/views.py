# catalogo/views.js
from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Q, Sum, OuterRef, Subquery, DecimalField, Prefetch,  IntegerField
from products.models import Product, Price, BranchStock, Branch, Category, Brand  # Asegúrate de importar los modelos necesarios
from django.http import JsonResponse
from .agent import run_agent

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
            discount_price=Subquery(
                Price.objects
                .filter(product_id=OuterRef("pk"))
                .values("discount")[:1],
                output_field=DecimalField(max_digits=10, decimal_places=2)
            ),
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
    }

    return render(request, 'catalogo/cat_detalle.html', context)

def agente_chat(request):
    if request.method == 'POST':
        if request.POST.get('clear_chat'):
            # Reset session and add greeting
            initial_msg = "¡Hola! Soy <strong>TU ASISTENTE CHIDO</strong>. ¿En qué te ayudo hoy?<br>Di algo como 'busca cámaras' para empezar."
            request.session['chat_history'] = [{'type': 'agent', 'content': initial_msg}]
            request.session.pop('last_results_ids', None)
            request.session.pop('last_product_details', None)
            return JsonResponse({'status': 'cleared', 'greeting': initial_msg})
        user_input = request.POST.get('mensaje', '')
        if not user_input:
            return JsonResponse({'respuesta': 'Por favor, ingresa un mensaje.'})
        response = run_agent(request, user_input)
        return JsonResponse({'respuesta': response})
    historial = request.session.get('chat_history', [])
    if not historial:
        initial_msg = "¡Hola! Soy <strong>TU ASISTENTE CHIDO</strong>. ¿En qué te ayudo hoy?<br>Di algo como 'busca cámaras' para empezar."
        historial = [{'type': 'agent', 'content': initial_msg}]
        request.session['chat_history'] = historial
    return render(request, 'catalogo/agente.html', {'historial': historial})