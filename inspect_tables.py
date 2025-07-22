import os, django, json
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()
from django.db import connection

cursor = connection.cursor()
cursor.execute("SHOW TABLES LIKE 'products_%'")
tables = [row[0] for row in cursor.fetchall()]
info = []
for t in tables:
    try:
        cursor.execute(f'SELECT COUNT(*) FROM `{t}`')
        count = cursor.fetchone()[0]
        cursor.execute(f'SELECT 1 FROM `{t}` WHERE id = 1000 LIMIT 1')
        has_1000 = bool(cursor.fetchone())
        info.append({'table': t, 'rows': count, 'has_id_1000': has_1000})
    except Exception as e:
        info.append({'table': t, 'error': str(e)})

print(json.dumps(info, indent=2)) 