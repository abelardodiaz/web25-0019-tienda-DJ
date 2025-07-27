import os
import sys
import django
from django.core.management import call_command

def clean_database():
    # Configurar entorno Django
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, project_root)
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
    
    try:
        django.setup()
    except Exception as e:
        print(f"❌ Error al configurar Django: {str(e)}")
        return False

    try:
        # 1. Resetear la base de datos de manera segura
        call_command('flush', '--no-input')
        
        # 2. Reaplicar migraciones
        call_command('migrate', '--no-input')
        
        print("✅ Base de datos limpiada y migraciones reaplicadas")
        return True
    except Exception as e:
        print(f"❌ Error al limpiar la base de datos: {str(e)}")
        return False

if __name__ == "__main__":
    clean_database() 