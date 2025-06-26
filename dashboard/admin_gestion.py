# dashboard/admin_gestion.py

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render, redirect

from products.models import Brand, Category, Product, BranchStock, Price 
from django.db.models import Q, Sum, OuterRef, Subquery, DecimalField

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