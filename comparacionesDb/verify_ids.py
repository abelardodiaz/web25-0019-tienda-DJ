import os
import sys
import django
import json
from datetime import datetime
from django.db import connection

# Configuración automática de Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

def check_ids(tables, target_id=1000):
    results = {}
    with connection.cursor() as cursor:
        for table in tables:
            try:
                cursor.execute(f"SELECT EXISTS(SELECT 1 FROM {table} WHERE id = %s)", [target_id])
                exists = cursor.fetchone()[0]
                results[table] = bool(exists)
            except Exception as e:
                results[table] = f"Error: {str(e)}"
    return results

if __name__ == '__main__':
    # Tablas a verificar (personaliza según necesidad)
    tables_to_check = [
        'products_changelog',
        'products_product',
        'users_customuser'
    ]
    
    print(f"Verificando existencia de ID 1000 en tablas clave...")
    id_results = check_ids(tables_to_check, 1000)
    
    print("\nResultados:")
    for table, exists in id_results.items():
        print(f"- {table}: {'Sí' if exists is True else 'No'}")
    
    # Guardar resultados
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    current_dir = os.path.dirname(os.path.abspath(__file__))
    results_dir = os.path.join(current_dir, 'results')
    os.makedirs(results_dir, exist_ok=True)
    output_file = os.path.join(results_dir, f'id_verification_{timestamp}.json')
    
    with open(output_file, 'w') as f:
        json.dump(id_results, f, indent=2)
    
    print(f"\nResultados guardados en: {output_file}")
