import os
import sys
import subprocess
from datetime import datetime
import django

def create_backup():
    # Add project root to Python path
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, project_root)
    
    # Manual settings configuration
    from django.conf import settings
    
    if not settings.configured:
        settings.configure(
            DATABASES={
                'default': {
                    'ENGINE': 'django.db.backends.mysql',
                    'NAME': 'web25011_db',
                    'USER': 'web25011_us',
                    'PASSWORD': 'xkdjshEretsxf4',
                    'HOST': '158.69.59.205',
                    'PORT': '3306',
                }
            },
            INSTALLED_APPS=[
                'django.contrib.admin',
                'django.contrib.auth',
                'django.contrib.contenttypes',
                'django.contrib.sessions',
                'django.contrib.messages',
                'django.contrib.staticfiles',
                'core',
                'products',
                'users',
            ],
            AUTH_USER_MODEL='users.CustomUser'
        )
    
    django.setup()
    
    # Create backup directory
    backup_dir = os.path.join(os.path.dirname(__file__), 'respaldos')
    os.makedirs(backup_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 1. Create JSON backup (Django-friendly)
    json_file = os.path.join(backup_dir, f'backup_{timestamp}.json')
    create_json_backup(json_file)
    
    # 2. Create SQL backup (for emergencies)
    sql_file = os.path.join(backup_dir, f'backup_{timestamp}.sql')
    try:
        # Get database configuration
        db = settings.DATABASES['default']
        
        # Build mysqldump command
        cmd = [
            'mysqldump',
            f"--host={db['HOST']}",
            f"--user={db['USER']}",
            f"--password={db['PASSWORD']}",
            '--single-transaction',
            '--skip-column-statistics',  # Added for MariaDB compatibility
            '--no-tablespaces',         # Added for MariaDB compatibility
            '--routines',
            '--triggers',
            '--events',
            db['NAME']
        ]

        # Add MariaDB version check
        try:
            version_cmd = ['mysql', f"--host={db['HOST']}", f"--user={db['USER']}", 
                          f"--password={db['PASSWORD']}", '-e', "SELECT VERSION();"]
            version_output = subprocess.check_output(version_cmd, text=True, stderr=subprocess.STDOUT)
            if "MariaDB" in version_output:
                print("🔍 Detectado servidor MariaDB, optimizando backup...")
                # Add MariaDB-specific options
                cmd.insert(1, '--skip-column-statistics')
                cmd.insert(2, '--no-tablespaces')
        except Exception as e:
            print(f"⚠️  No se pudo detectar versión de servidor: {str(e)}")
        
        # Execute with subprocess (suppress password warning)
        with open(sql_file, 'w') as f:
            with open(os.devnull, 'w') as devnull:
                result = subprocess.run(
                    cmd,
                    stdout=f,
                    stderr=subprocess.PIPE,  # Capture stderr separately
                    text=True
                )
            
            # Filter out password warning
            if result.returncode == 0:
                if "Using a password on the command line" in result.stderr:
                    print("✅ Respaldo SQL creado (advertencia de contraseña suprimida)")
                else:
                    print(f"✅ Respaldo SQL creado: {sql_file}")
            else:
                raise subprocess.CalledProcessError(
                    result.returncode, 
                    cmd, 
                    stderr=result.stderr
                )
        
        print(f"✅ Respaldo SQL creado: {sql_file}")
        return True
    except Exception as e:
        print(f"❌ Error al crear backup SQL: {str(e)}")
        
        # Enhanced fallback: Generate comprehensive SQL using Django
        try:
            from django.core.management import call_command
            from io import StringIO
            import re
            
            print("⚠️  Usando método alternativo para SQL...")
            
            # Create in-memory buffer
            schema_buffer = StringIO()
            data_buffer = StringIO()
            
            # 1. Generate schema using inspectdb
            call_command('inspectdb', stdout=schema_buffer)
            schema = schema_buffer.getvalue()
            
            # 2. Generate data inserts
            call_command('dumpdata', format='sql', stdout=data_buffer)
            data = data_buffer.getvalue()
            
            # 3. Combine and clean SQL
            with open(sql_file, 'w') as f:
                # Write schema
                f.write("-- SCHEMA GENERATION --\n")
                f.write(schema)
                f.write("\n\n")
                
                # Write data
                f.write("-- DATA INSERTION --\n")
                
                # Filter out problematic SQL (like SET statements)
                for line in data.splitlines():
                    if not line.startswith('SET ') and not line.startswith('/*!'):
                        f.write(line + "\n")
                
                # Add transaction commit
                f.write("\nCOMMIT;\n")
            
            print(f"✅ Respaldo SQL alternativo creado: {sql_file}")
            return True
        except Exception as fallback_e:
            print(f"❌ Error al crear backup SQL alternativo: {str(fallback_e)}")
            return False

def create_json_backup(backup_file):
    try:
        from django.core.management import call_command
        
        # Lista de exclusiones base
        exclude_list = [
            'contenttypes',
            'auth.Permission',
            'sessions',
            'admin.logentry',
            'auth.Group',
            'auth.User'
        ]
        
        # Intentar hacer el dumpdata
        try:
            with open(backup_file, 'w') as f:
                call_command('dumpdata', exclude=exclude_list, stdout=f, indent=2)
        except Exception as e:
            if "doesn't exist" in str(e):
                # Extraer el nombre de la tabla faltante del mensaje de error
                import re
                match = re.search(r"Table '.*?\.(.*?)' doesn't exist", str(e))
                if match:
                    missing_table = match.group(1)
                    print(f"⚠️  Tabla faltante detectada: {missing_table}")
                    
                    # Convertir nombre de tabla a formato app_label.model_name
                    # Ejemplo: users_customuser_groups -> users.customuser
                    parts = missing_table.split('_')
                    if len(parts) > 1:
                        app_label = parts[0]
                        model_name = parts[1]  # Usar solo el primer componente después del app_label
                        exclusion = f"{app_label}.{model_name}"
                    else:
                        exclusion = missing_table
                        
                    print(f"🔄 Reintentando excluyendo: {exclusion}")
                    exclude_list.append(exclusion)
                    
                    with open(backup_file, 'w') as f:
                        call_command('dumpdata', exclude=exclude_list, stdout=f, indent=2)
                else:
                    raise
            else:
                raise
        
        print(f"✅ Respaldo JSON creado: {backup_file}")
        return True
    except Exception as e:
        print(f"❌ Error al crear backup JSON: {str(e)}")
        return False

if __name__ == "__main__":
    create_backup()