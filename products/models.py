# Si necesitas mantener tablas:

# python
# # Añadir a allowed_tags
# 'table', 'tr', 'td', 'th'

# # Añadir a allowed_attributes
# 'table': ['border'], 'td': ['colspan', 'rowspan']

# Guardar la versión limpia en la base de datos
# para no procesar en cada visualización

# class Product(models.Model):
#     # ...
#     clean_description = models.TextField(blank=True)

#     def save(self, *args, **kwargs):
#         self.clean_description = self.clean_description()
#         super().save(*args, **kwargs)

# products/models.py
from __future__ import annotations

import enum
from datetime import timedelta

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
import bleach

# ------------------------------------------------------------------
# ExchangeRate — tabla independiente (MANTENIDA)
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
    
    def get_previous_rate(self):
        """Obtiene la tasa de cambio anterior"""
        return ExchangeRate.objects.filter(
            created_at__lt=self.created_at
        ).order_by('-created_at').values_list('rate', flat=True).first()


# ------------------------------------------------------------------
# Credenciales de Syscom (MANTENIDA)
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


# ==================================================================
# NUEVA ESTRUCTURA DE PRODUCTOS
# ==================================================================

# ------------------------------------------------------------------
# Marca
# ------------------------------------------------------------------
class Brand(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name=_("Marca"))
    logo_url = models.URLField(max_length=500, blank=True, verbose_name=_("Logo URL"))

    class Meta:
        verbose_name = _("Marca")
        verbose_name_plural = _("Marcas")
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


# ------------------------------------------------------------------
# Categoría con niveles
# ------------------------------------------------------------------
class Category(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name=_("Categoría"))
    level = models.PositiveSmallIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        verbose_name=_("Nivel")
    )

    class Meta:
        verbose_name = _("Categoría")
        verbose_name_plural = _("Categorías")
        ordering = ["level", "name"]

    def __str__(self) -> str:
        return f"{self.name} (Nivel {self.level})"


# ------------------------------------------------------------------
# Sucursal
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

    def __str__(self) -> str:
        return self.name


# ------------------------------------------------------------------
# Producto Principal
# ------------------------------------------------------------------
class Product(models.Model):
    # Identificación
    syscom_id = models.CharField(
        max_length=12, 
        unique=True,
        verbose_name=_("ID Syscom")
    )
    model = models.CharField(max_length=255, verbose_name=_("Modelo"))
    
    # Información básica
    title = models.CharField(max_length=500, verbose_name=_("Título"))
    description = models.TextField(blank=True, verbose_name=_("Descripción"))
    warranty = models.CharField(
        max_length=50, 
        blank=True, 
        verbose_name=_("Garantía")
    )
    sat_key = models.CharField(
        max_length=20, 
        blank=True, 
        verbose_name=_("Clave SAT")
    )
    private_link = models.URLField(
        max_length=500, 
        blank=True, 
        verbose_name=_("Link Privado")
    )
    
    # Relaciones
    brand = models.ForeignKey(
        Brand,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Marca")
    )
    categories = models.ManyToManyField(
        Category,
        through='ProductCategory',
        verbose_name=_("Categorías")
    )
    
    # Imágenes principales
    main_image = models.URLField(
        max_length=500, 
        blank=True, 
        verbose_name=_("Imagen Principal")
    )
    brand_logo = models.URLField(
        max_length=500, 
        blank=True, 
        verbose_name=_("Logo Marca")
    )
    
    # Auditoría
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    last_sync = models.DateTimeField(
        null=True, 
        blank=True, 
        verbose_name=_("Última Sincronización")
    )
    
    # Visibilidad
    visible = models.BooleanField(default=True, verbose_name=_("Visible al Público"))

    class Meta:
        verbose_name = _("Producto")
        verbose_name_plural = _("Productos")
        indexes = [
            models.Index(fields=['syscom_id']),
            models.Index(fields=['model']),
        ]
        ordering = ['title']

    def __str__(self) -> str:
        return f"{self.title} ({self.model})"

    @property
    def total_stock(self) -> int:
        """Existencia total en todas las sucursales"""
        return self.branch_stocks.aggregate(
            total=models.Sum('quantity')
        )['total'] or 0

        description = models.TextField()

    def clean_description(self):
        # Permitir solo estas etiquetas y atributos
        allowed_tags = [
            'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 
            'strong', 'em', 'b', 'i', 'u', 's', 
            'ul', 'ol', 'li', 'hr', 'br', 'img'
        ]
        
        allowed_attributes = {
            'img': ['src', 'alt', 'width', 'height']
        }
        
        return bleach.clean(
            self.description or '',
            tags=allowed_tags,
            attributes=allowed_attributes,
            strip=True
        )



# ------------------------------------------------------------------
# Precios (Relación 1:1 con Producto)
# ------------------------------------------------------------------
class Price(models.Model):
    product = models.OneToOneField(
        Product,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name='prices',
        verbose_name=_("Producto")
    )
    normal = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        verbose_name=_("Precio Normal")
    )
    special = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_("Precio Especial")
    )
    discount = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_("Precio con Descuento")
    )
    list_price = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        verbose_name=_("Precio de Lista")
    )
    margin = models.FloatField(
        default=20.0,
        verbose_name=_("Margen (%)")
    )
    price_edited = models.BooleanField(
        default=False,
        verbose_name=_("Precio Editado Manualmente")
    )

    class Meta:
        verbose_name = _("Precio")
        verbose_name_plural = _("Precios")

    def __str__(self) -> str:
        return f"Precios de {self.product}"


# ------------------------------------------------------------------
# Relación Producto-Categoría
# ------------------------------------------------------------------
class ProductCategory(models.Model):
    product = models.ForeignKey(
        Product, 
        on_delete=models.CASCADE,
        verbose_name=_("Producto")
    )
    category = models.ForeignKey(
        Category, 
        on_delete=models.CASCADE,
        verbose_name=_("Categoría")
    )

    class Meta:
        unique_together = ('product', 'category')
        verbose_name = _("Relación Producto-Categoría")
        verbose_name_plural = _("Relaciones Producto-Categoría")

    def __str__(self) -> str:
        return f"{self.product} en {self.category}"


# ------------------------------------------------------------------
# Imágenes Adicionales
# ------------------------------------------------------------------
class ProductImage(models.Model):
    class ImageType(models.TextChoices):
        EXTRA = 'adicional', _('Adicional')
        THUMBNAIL = 'thumbnail', _('Miniatura')
        GALLERY = 'galeria', _('Galería')

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='additional_images',
        verbose_name=_("Producto")
    )
    url = models.URLField(max_length=500, verbose_name=_("URL de Imagen"))
    type = models.CharField(
        max_length=10,
        choices=ImageType.choices,
        default=ImageType.EXTRA,
        verbose_name=_("Tipo de Imagen")
    )
    order = models.PositiveSmallIntegerField(
        default=0,
        verbose_name=_("Orden")
    )

    class Meta:
        verbose_name = _("Imagen de Producto")
        verbose_name_plural = _("Imágenes de Producto")
        ordering = ['order']

    def __str__(self) -> str:
        return f"Imagen {self.get_type_display()} para {self.product}"


# ------------------------------------------------------------------
# Existencias por Sucursal (Versión Simplificada)
# ------------------------------------------------------------------
class BranchStock(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='branch_stocks',
        verbose_name=_("Producto")
    )
    branch = models.ForeignKey(
        Branch,
        on_delete=models.CASCADE,
        verbose_name=_("Sucursal")
    )
    quantity = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Cantidad")
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Última actualización")
    )

    class Meta:
        unique_together = ('product', 'branch')
        verbose_name = _("Existencia en Sucursal")
        verbose_name_plural = _("Existencias en Sucursales")
        indexes = [
            models.Index(fields=['branch', 'quantity']),
        ]

    def __str__(self) -> str:
        return f"{self.quantity} unidades en {self.branch}"

    @classmethod
    def update_or_create_from_json(cls, product, branch_slug, quantity):
        """Método helper para crear/actualizar existencias desde JSON"""
        branch = Branch.objects.get(slug=branch_slug)
        obj, created = cls.objects.update_or_create(
            product=product,
            branch=branch,
            defaults={'quantity': int(quantity)}
        )
        return obj


# ------------------------------------------------------------------
# Características
# ------------------------------------------------------------------
class Feature(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='features',
        verbose_name=_("Producto")
    )
    text = models.CharField(
        max_length=255,
        verbose_name=_("Característica")
    )

    class Meta:
        verbose_name = _("Característica")
        verbose_name_plural = _("Características")

    def __str__(self) -> str:
        return self.text


# ------------------------------------------------------------------
# Recursos Adicionales
# ------------------------------------------------------------------
class Resource(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='resources',
        verbose_name=_("Producto")
    )
    name = models.CharField(
        max_length=255,
        verbose_name=_("Nombre del Recurso")
    )
    url = models.URLField(
        max_length=500,
        verbose_name=_("URL del Recurso")
    )

    class Meta:
        verbose_name = _("Recurso")
        verbose_name_plural = _("Recursos")

    def __str__(self) -> str:
        return self.name


# ------------------------------------------------------------------
# Iconos Especiales
# ------------------------------------------------------------------
class ProductIcon(models.Model):
    product = models.OneToOneField(
        Product,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name='icons',
        verbose_name=_("Producto")
    )
    top_left = models.URLField(
        max_length=500,
        blank=True,
        verbose_name=_("Icono Superior Izquierdo")
    )
    top_right = models.URLField(
        max_length=500,
        blank=True,
        verbose_name=_("Icono Superior Derecho")
    )

    class Meta:
        verbose_name = _("Icono de Producto")
        verbose_name_plural = _("Iconos de Producto")

    def __str__(self) -> str:
        return f"Iconos para {self.product}"



# ------------------------------------------------------------------
# Historial de Cambios (MEJORADO)
# ------------------------------------------------------------------
class ChangeLog(models.Model):
    ACTION_CHOICES = [
        ('CREATE', 'Creación'),
        ('UPDATE', 'Actualización'),
        ('DELETE', 'Eliminación'),
    ]
    
    product = models.ForeignKey(
        Product, 
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="change_logs",
        verbose_name=_("Producto")
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="changes_made",
        verbose_name=_("Usuario")
    )
    action = models.CharField(
        max_length=6, 
        choices=ACTION_CHOICES,
         default='CREATE',
        verbose_name=_("Acción")
    )
    field = models.CharField(
        max_length=50, 
        db_index=True,
        verbose_name=_("Campo Modificado")
    )
    old_value = models.TextField(
        blank=True, 
        null=True,
        verbose_name=_("Valor Anterior")
    )
    new_value = models.TextField(
        blank=True, 
        null=True,
        verbose_name=_("Nuevo Valor")
    )
    timestamp = models.DateTimeField(
        default=timezone.now, 
        db_index=True,
        verbose_name=_("Fecha/Hora")
    )
    metadata = models.JSONField(
        default=dict, 
        blank=True,
        verbose_name=_("Metadatos Adicionales")
    )

    class Meta:
        verbose_name = _("Registro de Cambio")
        verbose_name_plural = _("Historial de Cambios")
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=['product', 'field']),
            models.Index(fields=['timestamp', 'user']),
        ]

    def __str__(self) -> str:
        return f"{self.get_action_display()} en {self.field} - {self.timestamp:%Y-%m-%d %H:%M}"
    
    