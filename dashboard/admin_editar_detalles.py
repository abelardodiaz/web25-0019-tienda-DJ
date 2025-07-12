# dashboard/admin_editar_detalles.py
"""
Vista para editar los campos más comunes de un producto.
Se carga con /dashboard/gestion/editar-productos/<product_id>/
"""
"""
Edición de campos comunes del producto + garantía, características y existencias SLP
Ruta: /dashboard/gestion/editar-productos/<product_id>/
"""
from django import forms
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.text import slugify
import logging


from products.models import Branch, BranchStock, Feature, Product

SLP_SLUG = "san_luis_potosi"  # usado para localizar la sucursal SLP


# ─── FORMULARIO COMPLETO ─────────────────────────────────────────────────────
class ProductoForm(forms.ModelForm):
    # Campo virtual → lista de características (“una por línea”)
    features_text = forms.CharField(
        label="Características",
        required=False,
        widget=forms.Textarea(attrs={"rows": 6, "placeholder": "Una característica por línea"}),
        help_text="Separa cada característica con un salto de línea",
    )

    # Campo virtual → existencia física en SLP
    existencia_slp = forms.IntegerField(
        label="Existencia en SLP",
        min_value=0,
        required=False,
        help_text="Cantidad de piezas en la sucursal San Luis Potosí",
    )

    class Meta:
        model = Product
        fields = ["title", "model", "brand", "description", "warranty"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            "warranty": forms.TextInput(attrs={"placeholder": "12 meses"}),
        }

    # --- Rellenar campos virtuales al cargar ---------------------------------
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # 1) Características
        feats = Feature.objects.filter(product=self.instance).values_list("text", flat=True)
        self.initial["features_text"] = "\n".join(feats)

        # 2) Existencia SLP - Filtrar específicamente para SLP
        try:
            # Obtener la sucursal SLP
            branch_slp = Branch.objects.get(slug=SLP_SLUG)
            
            # Filtrar BranchStock para esta combinación producto-sucursal
            stock = BranchStock.objects.filter(
                product=self.instance,
                branch=branch_slp
            ).first()
            
            slp_qty = stock.quantity if stock else 0
        except Branch.DoesNotExist:
            slp_qty = 0
        
        self.initial["existencia_slp"] = slp_qty

        # Logging para depuración
    
        logger = logging.getLogger(__name__)
        logger.info(f"Buscando existencia SLP para producto: {self.instance.id}")

        try:
            branch_slp = Branch.objects.get(slug=SLP_SLUG)
            logger.info(f"Sucursal SLP encontrada: ID={branch_slp.id}")
            
            stock = BranchStock.objects.filter(
                product=self.instance,
                branch=branch_slp
            ).first()
            
            if stock:
                logger.info(f"Stock encontrado: {stock.quantity}")
            else:
                logger.warning("No se encontró registro de stock para SLP")
            
            slp_qty = stock.quantity if stock else 0

        except Branch.DoesNotExist:
            logger.error("Sucursal SLP no existe en la base de datos")
            slp_qty = 0

            self.initial["existencia_slp"] = slp_qty

    

@login_required
@staff_member_required
def editar_producto(request, product_id):
    """
    GET  → muestra formulario precargado
    POST → guarda cambios (producto, características y existencias)
    """
    producto = get_object_or_404(Product, pk=product_id)

    if request.method == "POST":
        form = ProductoForm(request.POST, instance=producto)
        if form.is_valid():
            # ----------------------------------------------------------------------------
            # 1) Guardamos los campos simples (title, warranty, etc.)
            # ----------------------------------------------------------------------------
            producto = form.save()

            # ----------------------------------------------------------------------------
            # 2) Sincronizamos características (Feature)
            # ----------------------------------------------------------------------------
            nuevas = {f.strip() for f in form.cleaned_data["features_text"].splitlines() if f.strip()}

            # a) borrar las que ya no existan
            Feature.objects.filter(product=producto).exclude(text__in=nuevas).delete()
            # b) crear las nuevas
            for texto in nuevas:
                Feature.objects.get_or_create(product=producto, text=texto)

            # ----------------------------------------------------------------------------
            # 3) Actualizamos existencia SLP (BranchStock)
            # ----------------------------------------------------------------------------
            qty = form.cleaned_data.get("existencia_slp")
            if qty is not None:
                branch, _ = Branch.objects.get_or_create(
                    slug=SLP_SLUG,
                    defaults={"name": "San Luis Potosí"}
                )
                # Si hay varias líneas previas, bórralas y deja una sola
                BranchStock.objects.filter(product=producto, branch=branch).delete()
                BranchStock.objects.create(product=producto, branch=branch, quantity=qty)

            # ----------------------------------------------------------------------------
            # 4) ¡listo! redirigimos a la tabla de gestión
            # ----------------------------------------------------------------------------
            return redirect("dashboard:gestion_productos")
    else:
        form = ProductoForm(instance=producto)

    # ── Cantidad total (todas las sucursales) ────────────────────────────────
    from django.db.models import Sum
    total_existencia = (
        BranchStock.objects.filter(product=producto).aggregate(total=Sum("quantity"))["total"]
        or 0
    )

    return render(
        request,
        "admin_editar_detalles.html",
        {
            "form": form,
            "producto": producto,
            "total_existencia": total_existencia,  # ➜ lo usamos en la plantilla
        },
    )

