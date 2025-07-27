import os
import sys
import django
import json
from django.db import connection
from django.apps import apps
from django.core.management.color import no_style
from django.db.backends.base.creation import BaseDatabaseCreation
from datetime import datetime
from django.db import models

def generate_model_schema():
    """Genera el esquema esperado basado en los modelos de Django"""
    model_schema = {}
    
    for model in apps.get_models():
        model_name = model._meta.db_table
        model_schema[model_name] = {
            "fields": [],
            "options": {}
        }
        
        # Obtener definiciones de campos
        for field in model._meta.fields:
            field_info = {
                "name": field.column,  # Usar nombre real de columna en BD
                "type": field.get_internal_type().replace('Field', '').lower(),  # Normalized type
                "max_length": getattr(field, "max_length", None),
                "null": field.null,
                "blank": field.blank,
                "default": field.default if field.default != models.NOT_PROVIDED else None,
                "primary_key": field.primary_key,
                "unique": field.unique,
                "is_foreign_key": isinstance(field, models.ForeignKey),
                "related_model": field.related_model._meta.db_table if isinstance(field, models.ForeignKey) else None
            }
            model_schema[model_name]["fields"].append(field_info)
        
        # Obtener opciones de modelo
        model_schema[model_name]["options"] = {
            "managed": model._meta.managed,
            "db_table": model._meta.db_table,
            "unique_together": model._meta.unique_together,
            "indexes": [index.name for index in model._meta.indexes]
        }
    
    return model_schema

def generate_db_schema():
    """Genera el esquema actual de la base de datos"""
    db_schema = {}
    with connection.cursor() as cursor:
        cursor.execute('SHOW TABLES')
        tables = [row[0] for row in cursor.fetchall()]
        
        for table in tables:
            db_schema[table] = {"fields": []}
            
            # Obtener estructura de la tabla
            cursor.execute(f'DESCRIBE {table}')
            columns = cursor.description
            column_names = [col[0] for col in columns]
            
            for row in cursor.fetchall():
                column_data = dict(zip(column_names, row))
                db_schema[table]["fields"].append({
                    "name": column_data['Field'],
                    "type": row[1].split('(')[0].strip().lower(),  # e.g., "FLOAT" -> "float"
                    "null": column_data['Null'] == 'YES',
                    "key": column_data['Key'],
                    "default": column_data['Default'],
                    "extra": column_data['Extra']
                })
    
    return db_schema

def compare_schemas(db_schema, model_schema):
    """Compara los esquemas y devuelve diferencias"""
    report = {
        "missing_tables": [],
        "extra_tables": [],
        "field_differences": {}
    }
    
    # Comparar tablas
    model_tables = set(model_schema.keys())
    db_tables = set(db_schema.keys())
    
    report["missing_tables"] = list(model_tables - db_tables)
    report["extra_tables"] = list(db_tables - model_tables)
    
    # Comparar campos en tablas comunes
    common_tables = model_tables & db_tables
    for table in common_tables:
        model_fields = {f['name']: f for f in model_schema[table]['fields']}
        db_fields = {f['name']: f for f in db_schema[table]['fields']}
        
        field_diffs = []
        
        # Campos faltantes en la base de datos
        for field_name in model_fields.keys() - db_fields.keys():
            field_diffs.append({
                "field": field_name,
                "issue": "Falta en la base de datos",
                "expected": model_fields[field_name]
            })
        
        # Campos extra en la base de datos
        for field_name in db_fields.keys() - model_fields.keys():
            field_diffs.append({
                "field": field_name,
                "issue": "Campo extra en la base de datos",
                "actual": db_fields[field_name]
            })
        
        # Comparar campos existentes
        for field_name in model_fields.keys() & db_fields.keys():
            model_field = model_fields[field_name]
            db_field = db_fields[field_name]
            
            # Comparar tipos de datos
            django_type = model_field['type']
            db_type = db_field['type']
            
            # Mapeo de tipos para comparación
            type_mapping = {
                'AutoField': 'int|bigint',
                'CharField': 'varchar',
                'TextField': 'text|longtext',
                'IntegerField': 'int',
                'BigIntegerField': 'bigint',
                'DateTimeField': 'datetime',
                'BooleanField': 'tinyint',
                'DecimalField': 'decimal',
                'ForeignKey': 'int|bigint'
            }
            
            expected_types = type_mapping.get(django_type, django_type).split('|')
            type_match = any(t in db_type.lower() for t in expected_types)
            
            if not type_match:
                field_diffs.append({
                    "field": field_name,
                    "issue": "Tipo de dato diferente",
                    "expected": f"{django_type} ({type_mapping.get(django_type, '')})",
                    "actual": db_type
                })
            
            # Comparar nulabilidad
            if model_field['null'] != db_field['null']:
                field_diffs.append({
                    "field": field_name,
                    "issue": "Nulabilidad diferente",
                    "expected": "NULL permitido" if model_field['null'] else "NOT NULL",
                    "actual": "NULL permitido" if db_field['null'] else "NOT NULL"
                })
        
        if field_diffs:
            report["field_differences"][table] = field_diffs
    
    return report

def save_comparison_report(report):
    """Guarda el reporte de comparación en un archivo"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    results_dir = os.path.join(os.path.dirname(__file__), 'results')
    os.makedirs(results_dir, exist_ok=True)
    filename = os.path.join(results_dir, f'comparison_report_{timestamp}.json')
    
    with open(filename, 'w') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    return filename

# Mapeo de tipos de Django a tipos de MariaDB
FIELD_TYPE_MAP = {
    'AutoField': 'INT',
    'BigAutoField': 'BIGINT',
    'CharField': 'VARCHAR(%(max_length)s)',
    'TextField': 'TEXT',
    'IntegerField': 'INT',
    'BigIntegerField': 'BIGINT',
    'FloatField': 'FLOAT',
    'DecimalField': 'DECIMAL(%(max_digits)s, %(decimal_places)s)',
    'BooleanField': 'BOOL',
    'DateField': 'DATE',
    'DateTimeField': 'DATETIME',
    'EmailField': 'VARCHAR(254)',
    'FileField': 'VARCHAR(100)',
    'ForeignKey': 'INT',
    'OneToOneField': 'INT',
    'ManyToManyField': 'INT',
    'UUIDField': 'CHAR(32)',
    'JSONField': 'JSON',
    'SlugField': 'VARCHAR(200)',
    'URLField': 'VARCHAR(200)',
    'ImageField': 'VARCHAR(100)',
    # Añadir todos los tipos necesarios aquí
    'PositiveIntegerField': 'INT UNSIGNED',
    'PositiveBigIntegerField': 'BIGINT UNSIGNED',
    'DurationField': 'BIGINT',
    'BinaryField': 'BLOB',
    'GenericIPAddressField': 'VARCHAR(39)',
}

def generate_sql_for_field(field_info):
    """Genera definición SQL para un campo, usando mapeo a tipos de DB"""
    field_type = field_info['type']
    
    # Manejar campos especiales
    if field_type == 'PrimaryKey':
        return 'BIGINT AUTO_INCREMENT PRIMARY KEY'
    
    # Campos relacionales deben usar BIGINT
    if field_type in ['ForeignKey', 'OneToOneField', 'ManyToManyField']:
        return 'BIGINT'
    
    # Obtener tipo base del mapeo
    base_type = FIELD_TYPE_MAP.get(field_type, 'TEXT')
    
    # Manejar parámetros específicos
    if 'max_length' in field_info and field_info['max_length']:
        try:
            base_type = base_type % {'max_length': field_info['max_length']}
        except:
            pass  # Mantener el tipo base si falla el formateo
    elif 'max_digits' in field_info and 'decimal_places' in field_info:
        try:
            base_type = base_type % {
                'max_digits': field_info['max_digits'],
                'decimal_places': field_info['decimal_places']
            }
        except:
            pass
    
    # Añadir NULL/NOT NULL
    null_clause = "NULL" if field_info.get('null', False) else "NOT NULL"
    
    return f"{base_type} {null_clause}"

def generate_sql_corrections(report):
    sql_commands = []
    
    # Check if report has the expected structure
    if 'tables' not in report:
        print("⚠️  El reporte no tiene la estructura esperada. Verificando estructura alternativa...")
        # Try the new structure where report itself is the tables dictionary
        if not isinstance(report, dict):
            print("❌ Formato de reporte inválido. No se generarán correcciones.")
            return []
        tables = report
    else:
        tables = report["tables"]
    
    for table, table_data in tables.items():
        # Handle different table data structures
        if isinstance(table_data, list):
            # New structure: table_data is a list of differences
            differences = table_data
        elif isinstance(table_data, dict):
            # Old structure: table_data is a dictionary with a "differences" key
            differences = table_data.get("differences", [])
        else:
            print(f"⚠️  Formato desconocido para las diferencias de la tabla {table}. Se omitirá.")
            differences = []
        
        for field in differences:
            if field['issue'] == "Falta en la base de datos":
                f = field['expected']
                # Usar el mapeo actualizado
                sql_def = generate_sql_for_field(f)
                sql_commands.append(
                    f"ALTER TABLE {table} ADD COLUMN {f['name']} {sql_def};"
                )
            
            elif field['issue'] == "Tipo de dato diferente":
                # 1. Preparar definición del tipo ---------------------------------
                null_clause = "NULL" if field.get('null', False) else "NOT NULL"

                django_type = field['expected'].split('(')[0].strip().lower()
                base_type = django_type[:-5] if django_type.endswith('field') else django_type

                # Diccionario ampliado
                type_conversion = {
                    'char': 'VARCHAR(255)',
                    'text': 'TEXT',
                    'int': 'INT',
                    'integer': 'INT',
                    'bigint': 'BIGINT',
                    'float': 'FLOAT',
                    'double': 'DOUBLE',
                    'decimal': 'DECIMAL(10,2)',
                    'bool': 'BOOL',
                    'boolean': 'BOOL',
                    'date': 'DATE',
                    'datetime': 'DATETIME',
                    'timestamp': 'TIMESTAMP',
                    'slug': 'VARCHAR(200)',
                    'positiveinteger': 'INT UNSIGNED',
                    'positivesmallinteger': 'SMALLINT UNSIGNED',
                    'json': 'JSON',
                    'uuid': 'CHAR(32)',
                    'blob': 'BLOB',
                    # --- nuevos mapeos ----
                    'foreignkey': 'BIGINT',
                    'onetoone': 'BIGINT',
                    'manytomany': 'BIGINT'
                }

                pk_clause = ''

                # 1️⃣  Campo id
                if field['field'] == 'id':
                    # Verificar si el id es referenciado por FKs
                    is_referenced = any(
                        fk['ref_table'] == table 
                        for fk in report.get('foreign_keys', [])
                    )
                    
                    if is_referenced:
                        print(f"⚠️  Omitiendo columna id en {table} (referenciada por FKs)")
                        continue
                    else:
                        new_type = 'BIGINT AUTO_INCREMENT'

                # 2️⃣  Claves foráneas    ←-----------   NUEVO
                elif field.get('is_foreign_key', False):
                    new_type = 'BIGINT'

                # 3️⃣  Resto de campos
                else:
                    new_type = type_conversion.get(base_type, 'TEXT')

                if not new_type.strip():
                    new_type = 'TEXT'
                    print(f"⚠️  Tipo vacío para campo {field['field']}, usando TEXT")

                # Determine the desired type and nullability from the model
                new_type = new_type

                # Determine desired nullability from the model field
                # Use the correct key for nullability (should be 'is_nullable' from the report)
                try:
                    # Get the desired nullability from the model field
                    model_nullable = field.get('model_nullable', True)  # Default to True if missing
                    desired_null = 'NOT NULL' if not model_nullable else 'NULL'
                except KeyError:
                    print(f"⚠️  Error obteniendo nulabilidad para campo {field['field']}, usando NULL por defecto")
                    desired_null = 'NULL'

                # Get the current field info from the report
                # We are now using table_data which is the data for this table
                current_field_info = table_data.get("fields", {}).get(field['field'])
                if not current_field_info:
                    # Skip if we don't have current info (shouldn't happen for existing fields)
                    continue

                current_nullable = current_field_info['is_nullable']  # 'YES' or 'NO'
                current_null = 'NULL' if current_nullable == 'YES' else 'NOT NULL'

                # Decide the null_clause to use in the ALTER
                if desired_null == current_null:
                    null_clause = desired_null
                else:
                    if desired_null == 'NOT NULL':
                        # We cannot safely set to NOT NULL because there might be NULLs, so we keep the current nullability
                        null_clause = current_null
                        # Add a warning comment
                        sql_commands.append(f"-- WARNING: Field `{table}`.`{field['field']}` was not set to NOT NULL because it currently allows NULLs. Please clean NULLs manually and then set NOT NULL.")
                    else:
                        null_clause = desired_null   # setting to NULL is safe

                # Then, generate the ALTER statement as before
                sql_commands.append(f"ALTER TABLE `{table}` MODIFY COLUMN `{field['field']}` {new_type} {null_clause}{pk_clause};")

                # 4. Recrear la FK si aplica ---------------------------------------
                if fk_name and field.get('related_model'):
                    sql_commands.append(
                        f"ALTER TABLE `{table}` ADD CONSTRAINT `{fk_name}` FOREIGN KEY (`{field['field']}`) REFERENCES `{field['related_model']}`(id);"
                    )

                # 5. Para conversiones texto→número, generar migración segura
                if (
                    field['issue'] == "Tipo de dato diferente"
                    and field.get('actual', '').startswith(('varchar', 'text'))
                    and new_type.startswith(('BIGINT', 'INT'))
                ):
                    sql_commands.extend([
                        f"ALTER TABLE `{table}` ADD COLUMN `{field['field']}_temp` {new_type};",
                        f"UPDATE `{table}` SET `{field['field']}_temp` = CAST(`{field['field']}` AS UNSIGNED);",
                        f"ALTER TABLE `{table}` DROP COLUMN `{field['field']}`;",
                        f"ALTER TABLE `{table}` CHANGE `{field['field']}_temp` `{field['field']}` {new_type};"
                    ])
    
    # 4. Ajustar auto_increment (con verificación adicional)
    auto_increment_diffs = report.get('auto_increment_differences', {})
    for table, ai_info in auto_increment_diffs.items():
        # Verificar que la información necesaria está presente
        if 'expected' in ai_info and 'current' in ai_info:
            if ai_info['expected'] > ai_info['current']:
                sql_commands.append(f"ALTER TABLE {table} AUTO_INCREMENT = {ai_info['expected']};")
        else:
            print(f"⚠️  Información de auto_increment incompleta para {table}")
    
    return "\n".join(sql_commands)

if __name__ == "__main__":
    # Configurar Django
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
    django.setup()
    
    print("🔍 Comparando base de datos con modelos de Django...")
    
    # Generar esquemas
    model_schema = generate_model_schema()
    db_schema = generate_db_schema()
    
    # Comparar
    comparison_report = compare_schemas(db_schema, model_schema)
    
    # Guardar reporte
    report_file = save_comparison_report(comparison_report)
    print(f"📝 Reporte de comparación guardado en: {report_file}")
    
    # Generar correcciones SQL
    sql_corrections = generate_sql_corrections(comparison_report)
    corrections_file = report_file.replace('.json', '_corrections.sql')
    with open(corrections_file, 'w') as f:
        f.write(sql_corrections)
    
    print(f"⚙️  Correcciones SQL generadas en: {corrections_file}")
    print("\n💡 Resumen de diferencias:")
    
    # Mostrar resumen
    if not any([comparison_report['missing_tables'], 
                comparison_report['extra_tables'], 
                comparison_report['field_differences']]):
        print("✅ No se encontraron diferencias significativas")
    else:
        if comparison_report['missing_tables']:
            print(f"⚠️  Tablas faltantes en BD: {len(comparison_report['missing_tables'])}")
        if comparison_report['extra_tables']:
            print(f"⚠️  Tablas extra en BD: {len(comparison_report['extra_tables'])}")
        if comparison_report['field_differences']:
            field_count = sum(len(fields) for fields in comparison_report['field_differences'].values())
            print(f"⚠️  Diferencias en campos: {field_count} campos en {len(comparison_report['field_differences'])} tablas")
    
    print("\n🔧 Ejecuta el archivo SQL generado para corregir las diferencias") 