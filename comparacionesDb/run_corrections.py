import os
import sys
import django
from django.db import connection
from django.conf import settings

def execute_sql_file(file_path):
    """Ejecuta un archivo SQL en la base de datos"""
    try:
        with open(file_path) as f:
            sql = f.read()
        
        with connection.cursor() as cursor:
            # Ejecutar cada comando individualmente
            for command in sql.split(';'):
                if command.strip():
                    cursor.execute(command)
        
        print(f"✅ Correcciones aplicadas exitosamente desde: {file_path}")
        return True
    except Exception as e:
        print(f"❌ Error al aplicar correcciones: {str(e)}")
        return False

def find_latest_corrections():
    """Encuentra el archivo de correcciones más reciente"""
    results_dir = os.path.join(os.path.dirname(__file__), 'results')
    if not os.path.exists(results_dir):
        return None
    
    # Buscar archivos de correcciones
    correction_files = [f for f in os.listdir(results_dir) 
                       if f.startswith('comparison_report_') and f.endswith('_corrections.sql')]
    
    if not correction_files:
        return None
    
    # Ordenar por fecha (más reciente primero)
    correction_files.sort(reverse=True)
    return os.path.join(results_dir, correction_files[0])

if __name__ == "__main__":
    # Configurar Django
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
    django.setup()
    
    # Buscar archivo de correcciones
    corrections_file = find_latest_corrections()
    
    if not corrections_file:
        print("❌ No se encontraron archivos de correcciones recientes")
        sys.exit(1)
    
    # Confirmar ejecución
    confirm = input(f"¿Estás SEGURO que quieres aplicar las correcciones de {corrections_file}? (s/n): ")
    if confirm.lower() == 's':
        print("⏳ Aplicando correcciones...")
        if execute_sql_file(corrections_file):
            print("✨ Base de datos actualizada exitosamente!")
        else:
            print("❌ Algunas correcciones fallaron. Verifica el archivo SQL.")
    else:
        print("❌ Operación cancelada") 