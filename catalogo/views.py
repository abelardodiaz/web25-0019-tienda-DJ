# catalogo/views.js
from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Q, Sum, OuterRef, Subquery, DecimalField, Prefetch,  IntegerField
from products.models import Product, Price, BranchStock, Branch, Category, Brand  # Asegúrate de importar los modelos necesarios

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
        # Convertir a enteros
        categorias_seleccionadas = [int(cat) for cat in categorias_seleccionadas]
        productos_list = productos_list.filter(categories__id__in=categorias_seleccionadas)
    
    # Aplicar filtros de marcas
    if marcas_seleccionadas:
        marcas_seleccionadas = [int(marca) for marca in marcas_seleccionadas]
        productos_list = productos_list.filter(brand__id__in=marcas_seleccionadas)
    
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
def detalle_producto(request, pk):
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
        pk=pk
    )

    # Consulta para poblar el panel de filtros
    categorias = Category.objects.order_by('name')
    marcas     = Brand.objects.order_by('name')

    # Lee qué filtros vinieron en la URL (GET)
    categorias_seleccionadas = request.GET.getlist('categoria')
    marcas_seleccionadas     = request.GET.getlist('marca')

    # Contexto completo
    context = {
        'producto': producto,
        'clean_description': producto.clean_description(),
        'categorias': categorias,
        'marcas': marcas,
        'categorias_seleccionadas': categorias_seleccionadas,
        'marcas_seleccionadas': marcas_seleccionadas,
    }

    return render(request, 'catalogo/cat_detalle.html', context)