import os, django, json
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()
from django.db import connection

cur = connection.cursor()
cur.execute('SHOW TABLES')
tables = [row[0] for row in cur.fetchall()]
conflicts = []
for t in tables:
    cur.execute(f"SHOW COLUMNS FROM `{t}` LIKE 'id'")
    if not cur.fetchone():
        continue  # tabla sin columna id
    try:
        cur.execute(f"SELECT 1 FROM `{t}` WHERE id=1000 LIMIT 1")
        if cur.fetchone():
            cur.execute(f"SELECT COUNT(*) FROM `{t}`")
            cnt = cur.fetchone()[0]
            conflicts.append({'table': t, 'rows': cnt})
    except Exception as e:
        conflicts.append({'table': t, 'error': str(e)})

print(json.dumps(conflicts, indent=2)) 