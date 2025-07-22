# file: dashboard/buscar_sincronizar.py
import requests, logging, json 
from django.utils import timezone
from products.models import SyscomCredential
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.shortcuts import render, redirect
from products.models import (
    Brand, Category, Product, Price, Branch, BranchStock,
    ProductImage, Feature, Resource, ProductCategory
)
from django.db import transaction
import re

# Configurar logger
logger = logging.getLogger(__name__)

API_PRODUCTOS_URL = "https://developers.syscom.mx/api/v1/productos"

@login_required
@staff_member_required
def obtener_productos_syscom(query='', ids=''):
    """Obtiene productos desde la API de Syscom"""
    try:
        url = "https://developers.syscom.mx/api/v1/productos"
        params = {}
        
        # CORRECCIÓN: Cambiar 'palabra' por 'busqueda' según la documentación de Syscom
        if query:
            params['busqueda'] = query  # Cambiado de 'palabra' a 'busqueda'
        if ids:
            params['ids'] = ids
        
        # Obtener credenciales (mismo método que para tipo de cambio)
        cred = SyscomCredential.objects.latest('id')
        headers = {"Authorization": f"Bearer {cred.token}"}
        
        response = requests.get(url, headers=headers, params=params, timeout=15)
        response.raise_for_status()
        
        data = response.json()
        productos = []
        
        # Manejar diferentes estructuras de respuesta
        productos_data = []
        if 'productos' in data:
            productos_data = data['productos']
        elif isinstance(data, list):
            productos_data = data
        elif 'producto_id' in data:
            productos_data = [data]
        
        for item in productos_data:
            # Obtener imagen principal
            imagen_principal = item.get("img_portada")
            if not imagen_principal and "imagenes" in item:
                if isinstance(item["imagenes"], list) and len(item["imagenes"]) > 0:
                    primera_imagen = item["imagenes"][0]
                    if isinstance(primera_imagen, dict) and "imagen" in primera_imagen:
                        imagen_principal = primera_imagen["imagen"]
            
            # Obtener categorías
            categorias = []
            for c in item.get("categorias", []):
                if isinstance(c, dict):
                    nombre_cat = c.get("nombre", "")
                    categorias.append(nombre_cat)
                elif isinstance(c, str):
                    categorias.append(c)
            
            # Obtener precios y existencias específicas
            precios = item.get("precios", {})
            existencia_detalle = item.get("existencia", {}).get("detalle", {})
            existencia_nuevo = existencia_detalle.get("nuevo", {})
            existencia_slp = existencia_nuevo.get("san_luis_potosi", 0) if isinstance(existencia_nuevo, dict) else 0
            
            productos.append({
                # 'id': item.get("producto_id"),  # <-- Eliminar este campo
                'syscom_id': item.get("producto_id"),
                'modelo': item.get("modelo"),
                'titulo': item.get("titulo"),
                'marca': item.get("marca"),
                'categorias': categorias,
                'existencia_total': item.get("total_existencia", 0),
                'existencia_slp': existencia_slp,
                'precio_especial': precios.get("precio_especial", 0),
                'precio_descuento': precios.get("precio_descuento", 0),
                'precio_lista': precios.get("precio_lista", 0),
                'imagen': imagen_principal,
                'link_privado': item.get("link_privado")
            })
        
        return productos
    
    except Exception as e:
        logger.error(f"Error obteniendo productos: {str(e)}")
        return []

@transaction.atomic
def sincronizar_producto(producto_data):
    # Obtener o crear marca
    marca, _ = Brand.objects.get_or_create(name=producto_data['marca'])
    
    # Crear o actualizar producto principal
    producto, created = Product.objects.update_or_create(
        syscom_id=producto_data['syscom_id'],
        defaults={
            'model': producto_data['modelo'],
            'title': producto_data['titulo'],
            'description': producto_data.get('descripcion', ''),
            'warranty': producto_data.get('garantia', ''),
            'sat_key': producto_data.get('sat_key', ''),
            'private_link': producto_data.get('link_privado', ''),
            'brand': marca,
            'main_image': producto_data.get('img_portada', ''),
            'brand_logo': producto_data.get('marca_logo', ''),
            'visible': True
        }
    )
    
    # Manejar categorías
    for cat_data in producto_data.get('categorias', []):
        if isinstance(cat_data, dict):
            nombre_cat = cat_data.get("nombre", "")
            nivel = cat_data.get("nivel", 1)
        else:
            nombre_cat = cat_data
            nivel = 1
            
        if nombre_cat:
            categoria, _ = Category.objects.get_or_create(
                name=nombre_cat,
                defaults={'level': nivel}
            )
            ProductCategory.objects.get_or_create(
                product=producto,
                category=categoria
            )
    
    # Manejar precios
    precios_data = producto_data.get('precios', {})
    Price.objects.update_or_create(
        product=producto,
        defaults={
            'normal': precios_data.get('precio_1', 0),
            'special': precios_data.get('precio_especial', 0),
            'discount': precios_data.get('precio_descuento', 0),
            'list_price': precios_data.get('precio_lista', 0),
        }
    )
    
    # Manejar existencias por sucursal
    existencia_data = producto_data.get('existencia', {})
    detalle_nuevo = existencia_data.get('detalle', {}).get('nuevo', {})
    
    if isinstance(detalle_nuevo, dict):
        for sucursal, cantidad in detalle_nuevo.items():
            # Normalizar nombre de sucursal
            sucursal_normalizada = sucursal.lower().replace(' ', '_')
            branch, _ = Branch.objects.get_or_create(
                slug=sucursal_normalizada,
                defaults={'name': sucursal.replace('_', ' ').title()}
            )
            BranchStock.objects.update_or_create(
                product=producto,
                branch=branch,
                defaults={'quantity': int(cantidad)}
            )
    
    # Manejar características
    caracteristicas = producto_data.get('caracteristicas', [])
    for caracteristica in caracteristicas:
        Feature.objects.get_or_create(
            product=producto,
            text=caracteristica.strip()
        )
    
    # Manejar imágenes adicionales
    for idx, img_data in enumerate(producto_data.get('imagenes', [])):
        if isinstance(img_data, dict):
            url = img_data.get('imagen')
        else:
            url = img_data
            
        if url:
            ProductImage.objects.get_or_create(
                product=producto,
                url=url,
                defaults={'order': idx}
            )
    
    # Manejar recursos
    for recurso in producto_data.get('recursos', []):
        if isinstance(recurso, dict):
            nombre = recurso.get('recurso')
            url = recurso.get('path')
        else:
            nombre = recurso
            url = recurso
            
        if nombre and url:
            Resource.objects.get_or_create(
                product=producto,
                name=nombre,
                url=url
            )
    
    return producto 
 

@login_required
@staff_member_required
def sincronizar_productos(request):
    productos = []
    search_performed = False
    
    if 'q' in request.GET or 'ids' in request.GET:
        search_performed = True
        query = request.GET.get('q', '')
        ids = request.GET.get('ids', '')
        productos = obtener_productos_syscom(query=query, ids=ids)
    
    if request.method == 'POST':
        selected_ids = request.POST.getlist('productos')
        success_count = 0
        error_count = 0
        
        for product_id in selected_ids:
            try:
                # Obtener datos completos del producto
                resultados = buscar_test(product_id)
                if resultados:
                    # Combinar datos básicos e inventarios
                    producto_data = {**resultados['basico'], **resultados['inventarios']}
                    
                    # Sincronizar producto
                    sincronizar_producto(producto_data)
                    success_count += 1
                else:
                    error_count += 1
            except Exception as e:
                logger.error(f"Error sincronizando producto {product_id}: {str(e)}")
                error_count += 1
        
        if success_count > 0:
            messages.success(request, f'{success_count} productos sincronizados exitosamente')
        if error_count > 0:
            messages.error(request, f'Error al sincronizar {error_count} productos')
        
        return redirect('dashboard:sincronizar')
    
    return render(request, 'admin_sinc.html', {
        'productos': productos,
        'search_performed': search_performed
    })

