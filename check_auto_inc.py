import os, django, json
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
import django
django.setup()
from django.apps import apps
from django.db import connection

models = [
    ('products_product','Product'),
    ('products_brand','Brand'),
    ('products_category','Category'),
    ('products_branch','Branch'),
    ('products_branchstock','BranchStock'),
    ('products_productimage','ProductImage'),
    ('products_feature','Feature'),
]
results = []
with connection.cursor() as cur:
    for table, label in models:
        cur.execute(f"SELECT MAX(id) FROM {table}")
        max_id = cur.fetchone()[0] or 0
        cur.execute("SELECT AUTO_INCREMENT FROM information_schema.TABLES WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME=%s", [table])
        auto_inc = cur.fetchone()[0] or 0
        results.append({'table':table,'model':label,'max_id':max_id,'auto_inc':auto_inc})
print(json.dumps(results, indent=2))

if __name__ == "__main__":
    import django
    import os
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
    django.setup()

    from products.models import Price, BranchStock, ProductCategory, Product
    from django.db.models import Count, Min, Max

    # --- Limpiar duplicados en Price (OneToOne con Product) ---
    print("Buscando duplicados en Price...")
    price_dupes = (
        Price.objects.values('product')
        .annotate(count=Count('id'))
        .filter(count__gt=1)
    )
    for dupe in price_dupes:
        product_id = dupe['product']
        prices = Price.objects.filter(product=product_id).order_by('-id')
        to_keep = prices.first()
        to_delete = prices[1:]
        print(f"Product {product_id}: manteniendo Price id={to_keep.id}, borrando {[p.id for p in to_delete]}")
        for p in to_delete:
            p.delete()

    # --- Limpiar duplicados en BranchStock (product, branch) ---
    print("Buscando duplicados en BranchStock...")
    stock_dupes = (
        BranchStock.objects.values('product', 'branch')
        .annotate(count=Count('id'))
        .filter(count__gt=1)
    )
    for dupe in stock_dupes:
        product_id = dupe['product']
        branch_id = dupe['branch']
        stocks = BranchStock.objects.filter(product=product_id, branch=branch_id).order_by('-id')
        to_keep = stocks.first()
        to_delete = stocks[1:]
        print(f"Product {product_id}, Branch {branch_id}: manteniendo Stock id={to_keep.id}, borrando {[s.id for s in to_delete]}")
        for s in to_delete:
            s.delete()

    # --- Limpiar duplicados en ProductCategory (product, category) ---
    print("Buscando duplicados en ProductCategory...")
    cat_dupes = (
        ProductCategory.objects.values('product', 'category')
        .annotate(count=Count('id'))
        .filter(count__gt=1)
    )
    for dupe in cat_dupes:
        product_id = dupe['product']
        category_id = dupe['category']
        rels = ProductCategory.objects.filter(product=product_id, category=category_id).order_by('-id')
        to_keep = rels.first()
        to_delete = rels[1:]
        print(f"Product {product_id}, Category {category_id}: manteniendo Rel id={to_keep.id}, borrando {[r.id for r in to_delete]}")
        for r in to_delete:
            r.delete()

    print("Limpieza de duplicados completada.")

    # --- Reiniciar autoincremental de Product ---
    print("Reiniciando autoincremental de Product...")
    try:
        max_id = Product.objects.aggregate(max_id=Max('id'))['max_id'] or 0
        next_id = max(max_id + 1, 1000)  # Mínimo 1000 para evitar colisiones
        with connection.cursor() as cursor:
            cursor.execute(f"ALTER TABLE products_product AUTO_INCREMENT = {next_id}")
        print(f"Autoincremental de products_product reiniciado a {next_id}.")
    except Exception as e:
        print(f"Error reiniciando autoincremental: {e}")

    # --- Reiniciar autoincremental para TODAS las tablas products_* ---
    print("Reiniciando AUTO_INCREMENT en tablas products_*")
    try:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SHOW TABLES LIKE 'products_%'")
            tables = [row[0] for row in cursor.fetchall()]
        for table in tables:
            with connection.cursor() as cursor:
                cursor.execute(f"SELECT MAX(id) FROM `{table}`")
                max_id = cursor.fetchone()[0] or 0
                next_id = max(max_id + 1, 1000)
                cursor.execute(f"ALTER TABLE `{table}` AUTO_INCREMENT = {next_id}")
                print(f"Tabla {table}: AUTO_INCREMENT ajustado a {next_id}")
    except Exception as e:
        print(f"Error reiniciando auto_increment en tablas products_*: {e}")

    # --- Detección y eliminación de conflictos en products_product ---
    print("Buscando y eliminando conflictos en products_product...")
    try:
        # Lista de IDs conflictivos conocidos (agrega más si es necesario)
        conflicting_ids = [1000, 1001, 1002, 1003, 1004, 1005]  # Basado en errores previos
        with connection.cursor() as cursor:
            for cid in conflicting_ids:
                cursor.execute(f"SELECT COUNT(*) FROM products_product WHERE id = {cid}")
                count = cursor.fetchone()[0]
                if count > 0:
                    cursor.execute(f"DELETE FROM products_product WHERE id = {cid}")
                    print(f"Eliminado conflicto: ID {cid} en products_product")
                else:
                    print(f"No se encontró conflicto para ID {cid}")
        # Después de eliminar, reiniciar AUTO_INCREMENT
        max_id = Product.objects.aggregate(max_id=Max('id'))['max_id'] or 0
        next_id = max(max_id + 1, 1000)
        with connection.cursor() as cursor:
            cursor.execute(f"ALTER TABLE products_product AUTO_INCREMENT = {next_id}")
        print(f"AUTO_INCREMENT de products_product reiniciado a {next_id} después de limpieza")
    except Exception as e:
        print(f"Error al manejar conflictos en products_product: {e}") 