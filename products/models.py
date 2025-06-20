# file: products/models.py
# products/models.py
from __future__ import annotations

import enum
from datetime import timedelta

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


# ------------------------------------------------------------------
# ExchangeRate — tabla independiente
# ------------------------------------------------------------------
class ExchangeRate(models.Model):
    rate = models.FloatField(
        verbose_name=_("Tipo de cambio"),
        validators=[MinValueValidator(0.0)],
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_by = models.CharField(max_length=50, blank=True)
    update_type = models.CharField(max_length=10, blank=True)

    class Meta:
        verbose_name = _("Tipo de cambio")
        verbose_name_plural = _("Tipos de cambio")
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.rate:.4f} ({self.created_at:%Y-%m-%d})"


# ------------------------------------------------------------------
# Marca
# ------------------------------------------------------------------
class Brand(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name=_("Marca"))
    logo_url = models.URLField(max_length=500, blank=True, verbose_name=_("Logo"))

    class Meta:
        verbose_name = _("Marca")
        verbose_name_plural = _("Marcas")
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


# ------------------------------------------------------------------
# Categoria con auto-referencia
# ------------------------------------------------------------------
class Category(models.Model):
    name = models.CharField(max_length=100, verbose_name=_("Categoría"))
    level = models.PositiveSmallIntegerField(default=0)
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="children",
        verbose_name=_("Categoría padre"),
    )

    class Meta:
        verbose_name = _("Categoría")
        verbose_name_plural = _("Categorías")
        ordering = ["level", "name"]
        indexes = [models.Index(fields=["name"])]

    def __str__(self) -> str:
        return self.name


# ------------------------------------------------------------------
# Sucursal — nueva tabla
# ------------------------------------------------------------------
class Branch(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name=_("Sucursal"))
    slug = models.SlugField(max_length=50, unique=True, verbose_name=_("Identificador"))
    active = models.BooleanField(default=True, verbose_name=_("Activa"))
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = _("Sucursal")
        verbose_name_plural = _("Sucursales")
        ordering = ["name"]

    def __str__(self) -> str:  # pragma: no cover
        return self.name


# ------------------------------------------------------------------
# Producto
# ------------------------------------------------------------------
class Product(models.Model):
    # ­── Campos básicos SYSCom
    model = models.CharField(max_length=100, blank=True, verbose_name=_("Modelo"))
    title = models.CharField(max_length=500, blank=True, verbose_name=_("Título"))
    description = models.TextField(blank=True, verbose_name=_("Descripción"))
    short_description = models.CharField(
        max_length=700, blank=True, verbose_name=_("Descripción corta")
    )
    sat_key = models.CharField(max_length=20, blank=True, verbose_name=_("Clave SAT"))
    private_link = models.URLField(max_length=500, blank=True, verbose_name=_("Link privado"))

    # ­── Precios
    list_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, verbose_name=_("Precio lista")
    )
    special_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, verbose_name=_("Precio especial")
    )
    margin = models.FloatField(default=20.0, verbose_name=_("Margen %"))
    discount = models.FloatField(default=0.0, verbose_name=_("Descuento %"))
    public_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, verbose_name=_("Precio público")
    )
    price_edited = models.BooleanField(default=False, verbose_name=_("Precio editado"))
    visible = models.BooleanField(default=False, verbose_name=_("Visible al público"))

    syscom_id = models.CharField(max_length=100, blank=True, verbose_name=_("ID Syscom"))
    last_sync = models.DateTimeField(null=True, blank=True, verbose_name=_("Última sincronización"))

    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    # ­── Relaciones
    brand = models.ForeignKey(
        Brand, on_delete=models.SET_NULL, null=True, blank=True, related_name="products"
    )
    categories = models.ManyToManyField(
        Category, through="ProductCategory", related_name="products"
    )

    class Meta:
        verbose_name = _("Producto")
        verbose_name_plural = _("Productos")
        indexes = [models.Index(fields=["model"]), models.Index(fields=["title"])]

    # ­── Propiedad calculada para compatibilidad
    @property
    def total_stock(self) -> int:
        return (
            self.branch_stocks.aggregate(total=models.Sum("quantity")).get("total") or 0
        )

    def __str__(self) -> str:
        return self.title or self.model or f"Producto #{self.pk}"


# ------------------------------------------------------------------
# Tablas intermedias y auxiliares
# ------------------------------------------------------------------
class ProductCategory(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)

    class Meta:
        db_table = "product_category"
        unique_together = ("product", "category")


class StockType(models.TextChoices):
    NORMAL = "n", _("Normal")
    ASTERISK_A = "a", _("Asterisco A")
    ASTERISK_B = "b", _("Asterisco B")


class BranchStock(models.Model):
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="branch_stocks"
    )
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name="stocks")
    quantity = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    stock_type = models.CharField(
        max_length=1, choices=StockType.choices, default=StockType.NORMAL
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Existencia por sucursal")
        verbose_name_plural = _("Existencias por sucursal")
        unique_together = ("product", "branch")


# ------------------------------------------------------------------
# Imágenes de producto
# ------------------------------------------------------------------
class ImageType(enum.Enum):
    COVER = "portada"
    THUMBNAIL = "thumbnail"
    EXTRA = "adicional"
    ICON = "icono"
    BRAND_LOGO = "marca_logo"


class ProductImage(models.Model):
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="images"
    )
    url = models.URLField(max_length=500)
    local = models.BooleanField(default=True)
    type = models.CharField(
        max_length=15,
        choices=[(tag.value, tag.value) for tag in ImageType],
        default=ImageType.EXTRA.value,
    )
    is_main = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = _("Imagen de producto")
        verbose_name_plural = _("Imágenes de producto")
        ordering = ["sort_order"]


# ------------------------------------------------------------------
# Historial de cambios
# ------------------------------------------------------------------
class ChangeLog(models.Model):
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="change_logs"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+"
    )
    field = models.CharField(max_length=50)
    old_value = models.CharField(max_length=500, blank=True, null=True)
    new_value = models.CharField(max_length=500, blank=True, null=True)
    timestamp = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = _("Historial de cambio")
        verbose_name_plural = _("Historial de cambios")
        ordering = ["-timestamp"]


# ------------------------------------------------------------------
# Credenciales de Syscom
# ------------------------------------------------------------------
class SyscomCredential(models.Model):
    client_id = models.CharField(max_length=120)
    client_secret = models.CharField(max_length=256)
    token = models.CharField(max_length=1224, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Credencial Syscom")
        verbose_name_plural = _("Credenciales Syscom")

    # -- Helpers
    def is_expired(self, grace_days: int = 0) -> bool:
        if not self.expires_at:
            return True
        return timezone.now() > self.expires_at - timedelta(days=grace_days)

    def token_status(self, grace_days: int = 7) -> str:
        if not self.token:
            return "no-token"
        if self.is_expired():
            return "expired"
        if self.is_expired(grace_days):
            return "expiring"
        return "active"

    def time_remaining(self):
        if not self.expires_at:
            return None
        delta = self.expires_at - timezone.now()
        return max(delta, timedelta(0))
