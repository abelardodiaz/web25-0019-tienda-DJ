# file: dashboard/buscar_sincronizar.py
# -----------------------------------------------------------------------------
# Este módulo centraliza toda la lógica de:
#   1) Renovar el token OAuth de Syscom
#   2) Consultar productos (por búsqueda o por ID) normalizando respuestas
#   3) Mostrar resultados en plantillas de administración
#   4) Sincronizar información detallada en la base interna (transacción atómica)
#   5) Funciones de prueba / debug para inspeccionar la respuesta bruta de Syscom
#
# Cada gran sección está marcada con comentarios --------------- BLOQUE --------
# para facilitar la búsqueda y el mantenimiento en el futuro.
# -----------------------------------------------------------------------------

# --- BLOQUE IMPORTS Y CONFIGURACIÓN ------------------------------------------
import json
import logging
from datetime import timedelta

import requests
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.text import slugify
from django.core.cache import cache
from django.db import IntegrityError

from products.models import (
    Branch,
    BranchStock,
    Brand,
    Category,
    Feature,
    Price,
    Product,
    ProductImage,
    SyscomCredential,
)

logger = logging.getLogger(__name__)

API_PRODUCTOS_URL = "https://developers.syscom.mx/api/v1/productos"

# --- BLOQUE TOKEN OAUTH ------------------------------------------------------


def renovar_token_syscom() -> bool:
    """
    Renueva el token de acceso a la API de Syscom y lo guarda en BD.

    Returns
    -------
    bool
        True  → renovación exitosa
        False → ocurrió un error
    """
    try:
        cred = SyscomCredential.objects.latest("id")

        url = "https://developers.syscom.mx/oauth/token"
        data = {
            "client_id": cred.client_id,
            "client_secret": cred.client_secret,
            "grant_type": "client_credentials",
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        response = requests.post(url, data=data, headers=headers, timeout=10)
        response.raise_for_status()

        token_data = response.json()
        cred.token = token_data["access_token"]
        cred.expires_at = timezone.now() + timedelta(seconds=token_data["expires_in"])
        cred.save()

        logger.info("✅  Token de Syscom renovado exitosamente")
        return True

    except Exception as e:
        logger.error(f"❌  Error renovando token de Syscom: {e}")
        return False


# --- BLOQUE PROCESAMIENTO DE PRODUCTO ----------------------------------------


def procesar_producto(item: dict) -> dict | None:
    """
    Convierte el JSON crudo de Syscom en un dict listo para plantilla.

    Se normalizan campos que a veces son lista y a veces objeto.

    Parameters
    ----------
    item : dict
        Un elemento de la respuesta de Syscom.

    Returns
    -------
    dict | None
        Dict normalizado o None si el formato es inesperado.
    """
    if not isinstance(item, dict):
        logger.warning(f"Elemento inesperado al procesar producto: {type(item)} → {item}")
        return None

    # Imagen principal
    imagen_principal = item.get("img_portada")
    if not imagen_principal and "imagenes" in item:
        imagenes = item["imagenes"]
        if isinstance(imagenes, list) and imagenes:
            first = imagenes[0]
            if isinstance(first, dict):
                imagen_principal = first.get("imagen")

    # Categorías (pueden ser dicts o strings)
    categorias: list[str] = []
    for cat in item.get("categorias", []):
        if isinstance(cat, dict):
            categorias.append(cat.get("nombre", ""))
        elif isinstance(cat, str):
            categorias.append(cat)

    # Existencia en SLP
    existencia_slp = "0"
    existencia_raw = item.get("existencia", {})
    if isinstance(existencia_raw, dict):
        detalle = (
            existencia_raw.get("detalle", {}).get("nuevo", {})
            if existencia_raw.get("detalle")
            else {}
        )
        existencia_slp = str(detalle.get("san_luis_potosi", "0"))
    elif isinstance(existencia_raw, list):
        for suc in existencia_raw:
            if (
                isinstance(suc, dict)
                and suc.get("sucursal", "").lower().startswith("san luis")
            ):
                existencia_slp = str(suc.get("cantidad", 0))
                break

    # Precios
    precios_raw = item.get("precios", {})
    if isinstance(precios_raw, list) and precios_raw:
        precios_raw = precios_raw[0]

    precio_especial = precios_raw.get("precio_especial", "0.00")
    precio_descuento = precios_raw.get("precio_descuento", "0.00")

    return {
        "id": item.get("producto_id"),
        "modelo": item.get("modelo"),
        "titulo": item.get("titulo"),
        "marca": item.get("marca"),
        "categorias": categorias,
        "existencia_total": item.get("total_existencia", 0),
        "existencia_slp": existencia_slp,
        "imagen": imagen_principal,
        "link_privado": item.get("link_privado"),
        "precio_especial": precio_especial,
        "precio_descuento": precio_descuento,
    }


# --- BLOQUE CONSULTA A SYSCOM ------------------------------------------------


def _get_auth_headers() -> dict:
    """Devuelve headers con el token más reciente."""
    cred = SyscomCredential.objects.latest("id")
    return {"Authorization": f"Bearer {cred.token}"}


def obtener_productos_syscom(query: str = "", ids: str = "", intento: int = 1) -> list:
    """
    Consulta la API de Syscom y normaliza la respuesta.

    • Si se pasa `ids`, se hacen peticiones individuales a /productos/<id>.
    • Si se pasa `query`, se usa el parámetro de búsqueda `busqueda=<query>`.

    Maneja la renovación automática del token (intenta 1 vez).
    """
    try:
        headers = _get_auth_headers()
        productos: list[dict] = []

        # --- Búsqueda por IDs -------------------------------------------------
        if ids:
            for pid in [i.strip() for i in ids.split(",") if i.strip()]:
                url = f"{API_PRODUCTOS_URL}/{pid}?inventarios=1"
                data = requests.get(url, headers=headers, timeout=15).json()

                iterable = data if isinstance(data, list) else [data]
                for item in iterable:
                    p = procesar_producto(item)
                    if p:
                        productos.append(p)
            return productos

        # --- Búsqueda por texto ----------------------------------------------
        params = {"busqueda": query, "inventarios": 1} if query else {}
        data = requests.get(API_PRODUCTOS_URL, headers=headers, params=params, timeout=15).json()

        productos_data = (
            data.get("productos", data) if isinstance(data, dict) else data
        )

        for item in productos_data:
            p = procesar_producto(item)
            if p:
                productos.append(p)

        return productos

    # --- Manejo de errores ---------------------------------------------------
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401 and intento < 2:
            logger.warning("Token expirado. Intentando renovar…")
            if renovar_token_syscom():
                return obtener_productos_syscom(query, ids, intento + 1)
        logger.error(f"HTTPError: {e}")
        return []

    except Exception as e:
        logger.error(f"Error general al obtener productos: {e}")
        return []


# --- BLOQUE FUNCIONES AUXILIARES PARA SYNC ----------------------------------

# --- BLOQUE PRECIOS (CORREGIDO) --------------------------------------------


def sync_product_price(producto, price_data):
    """
    Sincroniza (crea o actualiza) el precio principal del producto
    sin romper la clave primaria.
    """
    try:
        # 1️⃣  Un solo statement atómico
        Price.objects.update_or_create(
            product=producto,        # clave única / One-To-One
            defaults=price_data,     # campos a actualizar
        )
        return True

    except IntegrityError as e:
        logger.warning("IntegrityError en precios: %s", e)
        # 2️⃣  Segundo intento por si existe una carrera de escritura
        updated, _ = Price.objects.update_or_create(
            product=producto,
            defaults=price_data,
        )
        return updated is not None


def sync_product_stock(producto, sucursales_data):
    """Maneja la sincronización de inventarios por sucursal."""
    success_count = 0
    
    for name, qty in sucursales_data.items():
        try:
            slug = slugify(name)[:50]

            # Obtener o crear sucursal
            try:
                branch, _ = Branch.objects.get_or_create(
                    slug=slug,
                    defaults={"name": name}
                )
            except IntegrityError:
                branch = Branch.objects.get(slug=slug)

            # Sincronizar inventario
            try:
                BranchStock.objects.update_or_create(
                    product=producto,
                    branch=branch,
                    defaults={"quantity": int(qty or 0)},
                )
                success_count += 1
                
            except IntegrityError:
                # Si hay conflicto, hacer update directo
                BranchStock.objects.filter(
                    product=producto, 
                    branch=branch
                ).update(quantity=int(qty or 0))
                success_count += 1
                
        except Exception as e:
            logger.error(f"❌ Error sincronizando inventario {name} para producto {producto.syscom_id}: {e}")
    
    return success_count


# --- BLOQUE VISTAS DJANGO ----------------------------------------------------


@login_required
@staff_member_required
def sincronizar_productos(request):
    """
    Vista principal:
      • GET  → muestra resultados de búsqueda/ID
      • POST → sincroniza productos seleccionados a la BD interna
    """
    productos: list[dict] = []

    # --- GET: mostrar resultados --------------------------------------------
    if request.method == "GET" and ("q" in request.GET or "ids" in request.GET):
        query = request.GET.get("q", "")
        ids = request.GET.get("ids", "")
        productos = obtener_productos_syscom(query=query, ids=ids)

    # --- POST: sincronizar seleccionados ------------------------------------
    if request.method == "POST":
        selected_ids = request.POST.getlist("productos")
        success_count = 0
        error_count = 0

        for pid in selected_ids:
            try:
                logger.info(f"⏳ Iniciando sincronización para producto ID: {pid}")
                datos = buscar_test(pid)  # Incluye inventarios=1
                if not datos:
                    logger.warning(f"⚠️ No se obtuvieron datos para ID: {pid}")
                    error_count += 1
                    continue

                pdata = datos["inventarios"]
                logger.debug(f"📦 Datos obtenidos para ID {pid}")

                with transaction.atomic():
                    # 1. Marca
                    marca_nombre = pdata.get("marca", "Genérico")
                    logger.debug(f"🔖 Procesando marca: {marca_nombre}")
                    marca, created = Brand.objects.get_or_create(name=marca_nombre)
                    if created:
                        logger.info(f"✅ Nueva marca creada: {marca_nombre}")

                    # 2. Producto principal
                    logger.debug(f"📦 Creando/actualizando producto ID: {pid}")
                    producto, created = Product.objects.update_or_create(
                        syscom_id=pid,
                        defaults={
                            "model": pdata.get("modelo", ""),
                            "title": pdata.get("titulo", ""),
                            "description": pdata.get("descripcion", ""),
                            "warranty": pdata.get("garantia", ""),
                            "brand": marca,
                            "main_image": pdata.get("img_portada", ""),
                        },
                    )
                    logger.info(f"{'🆕 Creado' if created else '🔄 Actualizado'} producto: {producto.title}")

                    # 3. Precios
                    pr = pdata.get("precios") or {}
                    if isinstance(pr, list):
                        pr = pr[0] if pr else {}

                    price_data = {
                        "normal": float(pr.get("precio_1") or 0),
                        "special": float(pr.get("precio_especial") or 0),
                        "discount": float(pr.get("precio_descuento") or 0),
                        "list_price": float(pr.get("precio_lista") or 0),
                    }

                    if not sync_product_price(producto, price_data):
                        logger.warning(f"⚠️ No se pudieron sincronizar los precios para {pid}")

                    # 4. Existencia por sucursal
                    sucursales = (
                        pdata.get("existencia", {})
                            .get("detalle", {})
                            .get("nuevo", {})
                    )

                    if sucursales:
                        stock_success = sync_product_stock(producto, sucursales)
                        logger.debug(f"📦 {stock_success} inventarios sincronizados para {pid}")

                    # 5. Categorías
                    for cat in pdata.get("categorias", []):
                        if isinstance(cat, dict) and cat.get("nombre"):
                            try:
                                categoria, _ = Category.objects.get_or_create(
                                    name=cat["nombre"], 
                                    defaults={"level": cat.get("nivel", 1)}
                                )
                                producto.categories.add(categoria)
                            except Exception as e:
                                logger.warning(f"⚠️ Error agregando categoría {cat['nombre']}: {e}")

                    # 6. Imágenes
                    for idx, img in enumerate(pdata.get("imagenes", [])):
                        if "imagen" in img:
                            try:
                                ProductImage.objects.get_or_create(
                                    product=producto,
                                    url=img["imagen"],
                                    defaults={"order": idx, "type": "galeria"},
                                )
                            except Exception as e:
                                logger.warning(f"⚠️ Error agregando imagen {img['imagen']}: {e}")

                    # 7. Características
                    for feat in pdata.get("caracteristicas", []):
                        try:
                            Feature.objects.get_or_create(product=producto, text=feat)
                        except Exception as e:
                            logger.warning(f"⚠️ Error agregando característica: {e}")

                    success_count += 1
                    logger.info(f"✅ Producto {pid} sincronizado exitosamente")

            except Exception as e:
                logger.error(f"❌ Error crítico sincronizando {pid}: {str(e)}")
                error_count += 1

        # Mensaje final
        if success_count > 0:
            messages.success(request, f"✅ {success_count} productos sincronizados exitosamente")
        if error_count > 0:
            messages.warning(request, f"⚠️ {error_count} productos tuvieron errores")
            
        return redirect("dashboard:sincronizar")

    return render(request, "admin_sinc.html", {"productos": productos})


def sincronizar_inventario_sucursal(product_ids, branch_slug, cache_key=None):
    """Sincroniza inventario para una sucursal específica."""
    total = len(product_ids)
    processed = 0
    success_count = 0

    for pid in product_ids:
        try:
            datos = buscar_test(pid)
            if not datos:
                continue

            pdata = datos["inventarios"]
            sucursales = pdata.get("existencia", {}).get("detalle", {}).get("nuevo", {})

            if branch_slug in sucursales:
                qty = int(sucursales[branch_slug])
                producto = Product.objects.get(syscom_id=pid)
                branch = Branch.objects.get(slug=branch_slug)
                BranchStock.objects.update_or_create(
                    product=producto,
                    branch=branch,
                    defaults={"quantity": qty}
                )
                success_count += 1

        except Exception as e:
            logger.error(f"Error sincronizando inventario de {pid} para {branch_slug}: {e}")

        processed += 1
        if cache_key:
            cache.set(cache_key, {
                'total': total, 
                'processed': processed, 
                'success_count': success_count,
                'status': 'running'
            }, timeout=3600)

    if cache_key:
        progress = cache.get(cache_key, {})
        progress.update({
            'status': 'completed',
            'success_count': success_count
        })
        cache.set(cache_key, progress, timeout=3600)

    return success_count


# --- BLOQUE FUNCIONES DE PRUEBA / DEBUG --------------------------------------


def buscar_test(identificador: str) -> dict | None:
    """
    Devuelve la respuesta cruda de Syscom para inspección.
    Incluye la variante con `inventarios=1`.
    """
    try:
        headers = _get_auth_headers()

        url_base = f"{API_PRODUCTOS_URL}/{identificador}"
        data_basica = requests.get(url_base, headers=headers, timeout=15).json()

        url_inv = f"{url_base}?inventarios=1"
        data_inv = requests.get(url_inv, headers=headers, timeout=15).json()

        return {"basico": data_basica, "inventarios": data_inv}

    except Exception as e:
        logger.error(f"Error en buscar_test({identificador}): {e}")
        return None


@login_required
@staff_member_required
def sincronizar_test(request):
    """
    Vista de prueba que permite ver el JSON crudo de un producto Syscom.
    """
    context: dict = {}

    if request.method == "POST":
        pid = request.POST.get("product_id", "").strip()
        if not pid:
            messages.error(request, "Debe ingresar un ID de producto")
        else:
            datos = buscar_test(pid)
            if datos:
                context.update(
                    {
                        "product_id": pid,
                        "json_basico": json.dumps(datos["basico"], indent=4, ensure_ascii=False),
                        "json_inventarios": json.dumps(
                            datos["inventarios"], indent=4, ensure_ascii=False
                        ),
                    }
                )
            else:
                messages.error(request, "No se pudo obtener el producto o credenciales inválidas")

    return render(request, "admin_sinc_test.html", context)