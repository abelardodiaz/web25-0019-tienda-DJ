# dashboard/admin_gestion.py

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render, redirect
from django.http import JsonResponse
import threading
from django.core.cache import cache

from products.models import Brand, Category, Product, BranchStock, Price, Branch
from django.db.models import Q, Sum, OuterRef, Subquery, DecimalField
from dashboard.buscar_sincronizar import sincronizar_inventario_sucursal

@login_required
@staff_member_required
def gestion_productos(request):
    """
    Admin » Gestión de productos

    Muestra un listado paginado con:
      • Existencia total y de la sucursal SLP
      • Precio especial (discount_price)
    Permite filtrar por categoría, marca y búsqueda libre.
    """
    # ─── BLOQUE 1: parámetros de filtro ───
    categoria_id = request.GET.get("categoria")
    marca_id     = request.GET.get("marca")
    busqueda     = request.GET.get("q")

    # ─── BLOQUE 2: anotaciones de stock y precio ───
    SLP_SLUG = "san_luis_potosi"  # slug de la sucursal SLP

    precio_desc_qs = (
        Price.objects
        .filter(product_id=OuterRef("pk"))
        .values("special")[:1]
    )

    productos_qs = (
        Product.objects
        .select_related("brand")
        .prefetch_related("categories")
        .annotate(
            # ── alias distinto para suma global de stock ──
            total_stock_sum = Sum("branch_stocks__quantity"),
            # ── alias distinto para suma de stock en SLP ──
            slp_stock_sum   = Sum(
                "branch_stocks__quantity",
                filter=Q(branch_stocks__branch__slug=SLP_SLUG)
            ),
            # ── el descuento queda igual ──
            discount_price  = Subquery(
                precio_desc_qs,
                output_field=DecimalField(max_digits=10, decimal_places=2)
            ),
        )
    )

    # ─── BLOQUE 3: aplicar filtros dinámicos ───
    if categoria_id:
        productos_qs = productos_qs.filter(categories__id=categoria_id)
    if marca_id:
        productos_qs = productos_qs.filter(brand__id=marca_id)
    if busqueda:
        productos_qs = productos_qs.filter(
            Q(title__icontains=busqueda) |
            Q(model__icontains=busqueda) |
            Q(brand__name__icontains=busqueda)
        )

    # ─── BLOQUE 4: paginación ───
    paginator = Paginator(productos_qs, 25)        # 25 ítems por página
    page_obj  = paginator.get_page(request.GET.get("page"))

    # ─── BLOQUE 5: contexto y render ───
    context = {
        "productos"        : page_obj,
        "categorias"       : Category.objects.all(),
        "marcas"           : Brand.objects.all(),
        "current_categoria": int(categoria_id) if categoria_id else "",
        "current_marca"    : int(marca_id)     if marca_id else "",
        "busqueda"         : busqueda or "",
    }
    return render(request, "admin_gestion.html", context)

@login_required
@staff_member_required
def sincronizar_inventarios(request):
    # Recreate queryset from filters
    categoria_id = request.GET.get("categoria")
    marca_id = request.GET.get("marca")
    busqueda = request.GET.get("q")

    productos_qs = Product.objects.all()  # Base queryset, apply filters as in gestion_productos
    if categoria_id:
        productos_qs = productos_qs.filter(categories__id=categoria_id)
    if marca_id:
        productos_qs = productos_qs.filter(brand__id=marca_id)
    if busqueda:
        productos_qs = productos_qs.filter(
            Q(title__icontains=busqueda) | Q(model__icontains=busqueda) | Q(brand__name__icontains=busqueda)
        )

    total_productos = productos_qs.count()
    sucursales = Branch.objects.all()

    if request.method == "POST":
        branch_id = request.POST.get("branch")
        if not branch_id:
            messages.error(request, "Seleccione una sucursal.")
            return redirect(request.path)

        product_ids = list(productos_qs.values_list('syscom_id', flat=True))
        branch_slug = Branch.objects.get(id=branch_id).slug

        cache_key = f'sync_progress_{request.user.id}'  # User-specific key
        cache.set(cache_key, {'total': len(product_ids), 'processed': 0, 'status': 'running'}, timeout=3600)

        def run_sync():
            sincronizar_inventario_sucursal(product_ids, branch_slug, cache_key=cache_key)

        threading.Thread(target=run_sync).start()

        # Return immediately to allow polling
        return JsonResponse({'status': 'started'})

    context = {
        'total_productos': total_productos,
        'sucursales': sucursales,
    }
    return render(request, 'admin_sinc_inventarios.html', context)

def get_sync_progress(request):
    cache_key = f'sync_progress_{request.user.id}'
    progress = cache.get(cache_key, {'processed': 0, 'total': 0, 'status': 'idle'})
    return JsonResponse(progress)