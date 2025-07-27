import json
import os
import sys
from datetime import datetime

def interpret_schema(file_path):
    """Interpreta y muestra resultados de verificación de esquema"""
    with open(file_path) as f:
        data = json.load(f)
    
    print(f"\n🔍 Reporte de Esquema: {os.path.basename(file_path)}")
    print("=" * 60)
    
    for table in data['tables']:
        print(f"\n📊 Tabla: {table['table_name']}")
        
        # Resumen de columnas
        id_col = next((col for col in table['columns'] if col['Field'].lower() == 'id'), None)
        if id_col:
            print(f"  • Columna ID: Tipo={id_col['Type']}, Clave={'PRIMARY' if 'PRI' in id_col['Key'] else id_col['Key']}")
        
        # Auto-incremento
        if table['auto_increment'] is not None:
            print(f"  • AUTO_INCREMENT = {table['auto_increment']}")
            if table['auto_increment'] < 1000:
                print("    ⚠️  ADVERTENCIA: Valor bajo - podría indicar datos de prueba")
            elif table['auto_increment'] >= 1000:
                print("    ✅ Valor normal para producción")
        else:
            print("  • AUTO_INCREMENT: No aplica")
        
        # Columnas clave
        foreign_keys = [col for col in table['columns'] if 'MUL' in col['Key']]
        if foreign_keys:
            print("  • Claves foráneas:")
            for fk in foreign_keys:
                print(f"    - {fk['Field']} ({fk['Type']})")

def interpret_ids(file_path):
    """Interpreta y muestra resultados de verificación de IDs"""
    with open(file_path) as f:
        data = json.load(f)
    
    print(f"\n🔢 Reporte de IDs: {os.path.basename(file_path)}")
    print("=" * 60)
    
    for table, exists in data.items():
        status = "✅ EXISTE" if exists is True else "❌ NO EXISTE"
        if "Error" in str(exists):
            status = f"⚠️ ERROR: {exists}"
        
        print(f"- {table}: {status}")

def find_latest_report(pattern):
    """Encuentra el reporte más reciente"""
    reports_dir = os.path.join(os.path.dirname(__file__), 'results')
    reports = [f for f in os.listdir(reports_dir) if pattern in f]
    if not reports:
        return None
    
    # Ordenar por timestamp
    reports.sort(key=lambda x: os.path.getmtime(os.path.join(reports_dir, x)), reverse=True)
    return os.path.join(reports_dir, reports[0])

if __name__ == "__main__":
    # Buscar reportes más recientes
    latest_schema = find_latest_report('schema_verification')
    latest_ids = find_latest_report('id_verification')
    
    if not latest_schema or not latest_ids:
        print("❌ No se encontraron reportes recientes. Ejecuta primero run_verification.sh")
        sys.exit(1)
    
    print(f"📅 Última verificación: {datetime.fromtimestamp(os.path.getmtime(latest_schema)).strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Interpretar resultados
    interpret_schema(latest_schema)
    interpret_ids(latest_ids)
    
    print("\n💡 Consejo: Compara estos resultados con tu versión de código (0.2.4) para detectar inconsistencias")
