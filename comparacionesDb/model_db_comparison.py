import django
django.setup()
from django.db import connection
from django.apps import apps
import json

def get_model_schema():
    """Extract schema information from Django models"""
    schema = {}
    for app_config in apps.get_app_configs():
        for model in app_config.get_models():
            model_name = model._meta.db_table
            schema[model_name] = {}
            
            for field in model._meta.fields:
                field_info = {
                    'type': field.db_type(connection),
                    'null': field.null,
                    'primary_key': field.primary_key,
                    'max_length': getattr(field, 'max_length', None),
                }
                schema[model_name][field.column] = field_info
    return schema

def get_db_schema():
    """Extract actual database schema using Django's connection"""
    schema = {}
    with connection.cursor() as cursor:
        cursor.execute("SHOW TABLES")
        tables = [row[0] for row in cursor.fetchall()]
        
        for table in tables:
            schema[table] = {}
            cursor.execute(f"DESCRIBE {table}")
            for row in cursor.fetchall():
                field_info = {
                    'type': row[1],
                    'null': row[2] == 'YES',
                    'key': row[3],
                    'default': row[4],
                    'extra': row[5]
                }
                schema[table][row[0]] = field_info
    return schema

def compare_schemas():
    """Compare model schema with actual database schema"""
    model_schema = get_model_schema()
    db_schema = get_db_schema()
    differences = []
    
    # Compare tables
    all_tables = set(model_schema.keys()) | set(db_schema.keys())
    for table in all_tables:
        if table not in model_schema:
            differences.append(f"🚫 Table exists in DB but not in models: {table}")
            continue
            
        if table not in db_schema:
            differences.append(f"🚫 Table exists in models but not in DB: {table}")
            continue
            
        # Compare fields
        model_fields = model_schema[table]
        db_fields = db_schema[table]
        all_fields = set(model_fields.keys()) | set(db_fields.keys())
        
        for field in all_fields:
            if field not in model_fields:
                differences.append(f"  🚫 Field exists in DB but not in model: {table}.{field}")
                continue
                
            if field not in db_fields:
                differences.append(f"  🚫 Field exists in model but not in DB: {table}.{field}")
                continue
                
            model_info = model_fields[field]
            db_info = db_fields[field]
            
            # Compare field properties
            if model_info['type'] != db_info['type']:
                differences.append(
                    f"  🔄 Type mismatch: {table}.{field} "
                    f"(Model: {model_info['type']}, DB: {db_info['type']})"
                )
                
            if model_info['null'] != db_info['null']:
                differences.append(
                    f"  🔄 Nullability mismatch: {table}.{field} "
                    f"(Model: {'NULL' if model_info['null'] else 'NOT NULL'}, "
                    f"DB: {'NULL' if db_info['null'] else 'NOT NULL'})"
                )
    
    # Save and print results
    with open('comparacionesDb/results/manual_comparison.json', 'w') as f:
        json.dump({
            'model_schema': model_schema,
            'db_schema': db_schema,
            'differences': differences
        }, f, indent=2)
    
    print("✅ Comparison complete. Differences found:")
    for diff in differences:
        print(diff)

if __name__ == "__main__":
    compare_schemas() 