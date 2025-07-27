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

def verify_database_schema():
    results = {"tables": []}
    with connection.cursor() as cursor:
        cursor.execute('SHOW TABLES')
        tables = [row[0] for row in cursor.fetchall()]
        
        for table in tables:
            table_info = {
                "table_name": table,
                "columns": [],
                "auto_increment": None,
                "has_id_column": False
            }
            
            # 1. Obtener estructura de la tabla
            cursor.execute(f'DESCRIBE {table}')
            columns = cursor.description
            column_names = [col[0] for col in columns]
            
            for row in cursor.fetchall():
                column_data = dict(zip(column_names, row))
                table_info["columns"].append(column_data)
                
                # Verificar si tiene columna 'id'
                if column_data['Field'] == 'id':
                    table_info["has_id_column"] = True
            
            # 2. Obtener auto-incremento
            try:
                cursor.execute(f'SHOW CREATE TABLE {table}')
                create_sql = cursor.fetchone()[1]
                if 'AUTO_INCREMENT' in create_sql:
                    ai_value = create_sql.split('AUTO_INCREMENT=')[1].split()[0]
                    table_info["auto_increment"] = int(ai_value)
            except Exception as e:
                table_info["auto_increment_error"] = str(e)
            
            results["tables"].append(table_info)
    
    return results

def save_results(results):
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    # Cambiar la ruta de results
    os.makedirs('results', exist_ok=True)  # Directorio directo en comparacionesDb
    filename = f'results/schema_verification_{timestamp}.json'  # Ruta corregida
    
    with open(filename, 'w') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    return filename

if __name__ == '__main__':
    print("Iniciando verificación de esquema de base de datos...")
    results = verify_database_schema()
    output_file = save_results(results)
    print(f"Verificación completada. Resultados guardados en: {output_file}")
    print(f"Tablas analizadas: {len(results['tables'])}")
