import os
import glob
import datetime
import shutil

def cleanup_directory(directory, patterns, days_old, max_files):
    """Limpia archivos específicos en un directorio según patrones"""
    print(f"🔍 Escaneando: {directory} | Patrones: {patterns}")  # Debug line
    deleted_count = 0
    for pattern in patterns:
        # Use recursive pattern matching
        file_pattern = os.path.join(directory, '**', pattern)  # Modified line
        all_files = glob.glob(file_pattern, recursive=True)    # Modified line
        
        print(f"  🔎 Patrón '{pattern}': Encontrados {len(all_files)} archivos")  # Debug line
        
        if not all_files:
            continue
             
        # Ordenar por fecha de modificación (más recientes primero)
        all_files.sort(key=os.path.getmtime, reverse=True)
         
        # Conservar los archivos más recientes
        files_to_keep = all_files[:max_files] if max_files > 0 else []
        current_time = datetime.datetime.now(datetime.timezone.utc)  # Use UTC time
        
        for file_path in all_files:
            # Saltar archivos que debemos conservar
            if file_path in files_to_keep:
                continue
                
            # Use UTC time for consistent comparison
            file_mtime = datetime.datetime.fromtimestamp(
                os.path.getmtime(file_path), 
                tz=datetime.timezone.utc
            )
            age = (current_time - file_mtime).days
            
            # Condición de eliminación corregida (>= en lugar de >)
            if age >= days_old:  # Cambiado de > a >=
                try:
                    if os.path.isfile(file_path):
                        print(f"  🗑️ Eliminando: {file_path} (Edad: {age}d)")
                        os.remove(file_path)
                        deleted_count += 1
                except Exception as e:
                    print(f"⚠️ Error eliminando {file_path}: {str(e)}")
    
    return deleted_count

def get_files_to_delete(directory, patterns, days_old, max_files):
    """Obtiene lista de archivos a eliminar (sin borrar)"""
    files_to_delete = []
    for pattern in patterns:
        file_pattern = os.path.join(directory, '**', pattern)
        all_files = glob.glob(file_pattern, recursive=True)
        if not all_files:
            continue

        all_files.sort(key=os.path.getmtime, reverse=True)
        files_to_keep = all_files[:max_files] if max_files > 0 else []
        current_time = datetime.datetime.now(datetime.timezone.utc)
        
        for file_path in all_files:
            if file_path in files_to_keep:
                continue
                
            file_mtime = datetime.datetime.fromtimestamp(
                os.path.getmtime(file_path), 
                tz=datetime.timezone.utc
            )
            age = (current_time - file_mtime).days
            
            if age >= days_old:
                files_to_delete.append({
                    "path": file_path,
                    "age": age,
                    "size": os.path.getsize(file_path) if os.path.isfile(file_path) else 0
                })
    
    return files_to_delete

def preview_files_to_delete(directory, patterns, days_old, max_files):
    """Muestra vista previa de archivos a eliminar"""
    from tabulate import tabulate
    
    # Obtener archivos candidatos
    files_info = []
    for pattern in patterns:
        file_pattern = os.path.join(directory, '**', pattern)
        all_files = glob.glob(file_pattern, recursive=True)
        
        if not all_files:
            continue
            
        # Ordenar por fecha
        all_files.sort(key=os.path.getmtime, reverse=True)
        files_to_keep = all_files[:max_files] if max_files > 0 else []
        current_time = datetime.datetime.now(datetime.timezone.utc)
        
        for file_path in all_files:
            file_mtime = datetime.datetime.fromtimestamp(
                os.path.getmtime(file_path), 
                tz=datetime.timezone.utc
            )
            age = (current_time - file_mtime).days
            
            # Determinar si será eliminado
            status = "✅ Conservar" if file_path in files_to_keep or age < days_old else "❌ Eliminar"
            
            files_info.append({
                "Archivo": os.path.basename(file_path),
                "Ruta": os.path.dirname(file_path),
                "Modificado": file_mtime.strftime("%Y-%m-%d %H:%M"),
                "Edad (días)": age,
                "Tamaño": os.path.getsize(file_path),
                "Estado": status
            })
    
    # Mostrar tabla
    if not files_info:
        print("ℹ️ No se encontraron archivos que coincidan con los patrones")
        return
    
    # Formatear tabla
    table_data = []
    for info in files_info:
        file_ext = os.path.splitext(info["Archivo"])[1].upper()
        table_data.append([
            info["Archivo"],
            file_ext,  # Show file type
            info["Ruta"].split("/")[-1],
            info["Modificado"],
            info["Edad (días)"],
            f"{info['Tamaño']/1024:.1f} KB",
            info["Estado"]
        ])
    
    # Update table headers to show file type
    headers = ["Archivo", "Tipo", "Directorio", "Última modificación", "Edad", "Tamaño", "Estado"]
    print(tabulate(table_data, headers=headers, tablefmt="grid"))
    return files_info

def interactive_cleanup():
    """Limpieza interactiva con selección de categorías"""
    print("\n🧹 Selecciona qué archivos limpiar:")
    print("1. Respaldos de base de datos")
    print("2. Resultados de verificaciones")
    print("3. Reportes de comparaciones")
    print("4. Todos los anteriores")
    print("5. Cancelar")
    
    choice = input("Opción: ")
    
    if choice == '5':
        print("❌ Operación cancelada")
        return 0
    
    # Obtener configuración de limpieza
    try:
        days_old = int(input("¿Eliminar archivos más antiguos de cuántos días? (ej: 7): "))
        max_files = int(input("¿Cuántos archivos recientes conservar? (ej: 5): "))
    except ValueError:
        print("❌ Por favor ingresa números válidos")
        return 0
    
    # Configurar políticas por categoría
    policies = {
        "respaldos": {
            "directory": "respaldos",
            "patterns": ["*.sql", "*.json"],  # Added JSON pattern
            "days_old": days_old,
            "max_files": max_files
        },
        "verificaciones": {
            "directory": "results",
            "patterns": ["schema_verification_*.json", "id_verification_*.json"],
            "days_old": days_old,
            "max_files": max_files
        },
        "comparaciones": {
            "directory": "results",
            "patterns": ["comparison_report_*.json", "*_corrections.sql"],
            "days_old": days_old,
            "max_files": max_files
        }
    }
    
    # Seleccionar categorías a limpiar
    categories = []
    if choice in ['1', '4']:
        categories.append("respaldos")
    if choice in ['2', '4']:
        categories.append("verificaciones")
    if choice in ['3', '4']:
        categories.append("comparaciones")
    
    # Mostrar vista previa
    print("\n📋 Vista previa de archivos:")
    for category in categories:
        policy = policies[category]
        dir_path = os.path.join(os.path.dirname(__file__), policy["directory"])
        print(f"\n🔍 Categoría: {category.upper()}")
        preview_files_to_delete(
            dir_path, 
            policy["patterns"], 
            days_old, 
            policy["max_files"]
        )
    
    # Confirmar eliminación
    confirm = input("\n¿Deseas proceder con la eliminación? (s/n): ")
    if confirm.lower() != 's':
        print("❌ Operación cancelada")
        return 0
    
    # Ejecutar limpieza
    total_deleted = 0
    for category in categories:
        policy = policies[category]
        dir_path = os.path.join(os.path.dirname(__file__), policy["directory"])
        deleted = cleanup_directory(
            dir_path, 
            policy["patterns"], 
            days_old, 
            max_files
        )
        print(f" - {category}: Eliminados {deleted} archivos")
        total_deleted += deleted
    
    return total_deleted

def cleanup_all():
    """Limpia todos los archivos con políticas predeterminadas"""
    print("🧹 Iniciando limpieza automática...")
    
    # Políticas predeterminadas
    policies = {
        "respaldos": {
            "directory": "respaldos",
            "patterns": ["*.sql", "*.json"],  # Added JSON pattern
            "days_old": 30,
            "max_files": 5
        },
        "verificaciones": {
            "directory": "results",
            "patterns": ["schema_verification_*.json", "id_verification_*.json"],
            "days_old": 15,
            "max_files": 5
        },
        "comparaciones": {
            "directory": "results",
            "patterns": ["comparison_report_*.json", "*_corrections.sql"],
            "days_old": 15,
            "max_files": 5
        }
    }
    
    total_deleted = 0
    for category, policy in policies.items():
        dir_path = os.path.join(os.path.dirname(__file__), policy["directory"])
        deleted = cleanup_directory(
            dir_path, 
            policy["patterns"], 
            policy["days_old"], 
            policy["max_files"]
        )
        print(f" - {category}: Eliminados {deleted} archivos")
        total_deleted += deleted
    
    print(f"♻️ Limpieza completada. Total eliminado: {total_deleted} elementos")
    return total_deleted

def format_size(size_bytes):
    """Formatea tamaño de archivo en unidades legibles"""
    if size_bytes < 1024:
        return f"{size_bytes}B"
    elif size_bytes < 1024*1024:
        return f"{size_bytes/1024:.1f}KB"
    else:
        return f"{size_bytes/(1024*1024):.1f}MB"

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Limpieza de archivos generados')
    parser.add_argument('--interactive', action='store_true', help='Modo interactivo')
    args = parser.parse_args()

    if args.interactive:
        total_deleted = interactive_cleanup()
    else:
        total_deleted = cleanup_all()
    
    print(f"♻️ Limpieza completada. Total eliminado: {total_deleted} elementos") 