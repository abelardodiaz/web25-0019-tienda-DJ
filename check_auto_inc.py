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