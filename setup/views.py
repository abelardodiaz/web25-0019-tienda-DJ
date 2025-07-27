# setup/views.py
import requests,  MySQLdb, os, re 
from django.db import connection, OperationalError
from django.contrib.auth import get_user_model
from django.shortcuts import render, redirect
from django import forms
from django.core.exceptions import ValidationError
from django.conf import settings
from django.core.management import call_command
from django.db import connections
from django.http import HttpResponse
from dotenv import load_dotenv
from django.contrib.auth import authenticate, login 







class SetupForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded focus:outline-none focus:ring-1 focus:ring-blue-500',
            'placeholder': 'tu@email.com'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded focus:outline-none focus:ring-1 focus:ring-blue-500',
            'placeholder': '••••••••'
        })
    )
    password_confirm = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded focus:outline-none focus:ring-1 focus:ring-blue-500',
            'placeholder': '••••••••'
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')
        
        if password and password_confirm and password != password_confirm:
            raise ValidationError("Las contraseñas no coinciden")
        
        if password:
            # Validar fortaleza de la contraseña
            errors = []
            if len(password) < 8:
                errors.append('La contraseña debe tener al menos 8 caracteres')
            if not re.search(r'[A-Z]', password):
                errors.append('La contraseña debe contener al menos una letra mayúscula')
            if not re.search(r'[0-9]', password):
                errors.append('La contraseña debe contener al menos un número')
            if not re.search(r'[@$!%*?&]', password):
                errors.append('La contraseña debe contener al menos un carácter especial (@$!%*?&)')
            
            if errors:
                raise ValidationError(errors)
        
        return cleaned_data
    


def get_public_ip():
    try:
        return requests.get('https://api.ipify.org').text
    except:
        return "No se pudo obtener la IP pública"

def create_database():
    try:
        conn = MySQLdb.connect(
            host=os.getenv('DB_HOST'),
            port=int(os.getenv('DB_PORT')),
            user=os.getenv('DB_CREATOR_USER'),
            password=os.getenv('DB_CREATOR_PASSWORD')
        )
        cursor = conn.cursor()

        db_name   = os.getenv('DB_NAME')
        app_user  = os.getenv('DB_USER')
        app_pass  = os.getenv('DB_PASSWORD')

        # 1. Validar nombre de BD (solo caracteres seguros)
        if not re.match(r'^[a-zA-Z0-9_]+$', db_name):
            raise ValueError("Nombre de base de datos inválido")
        
        # 2. Crear BD
        cursor.execute(
            f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )

        # 3. Crear usuario
        cursor.execute(
            "CREATE USER IF NOT EXISTS %s@'%%' IDENTIFIED BY %s",
            (app_user, app_pass)
        )
        conn.commit()   

        # 4. Otorgar privilegios (sin FLUSH PRIVILEGES)
        cursor.execute(
            f"GRANT ALL PRIVILEGES ON `{db_name}`.* TO %s@'%%'",
            (app_user,)
        )
        conn.commit()
        cursor.execute("FLUSH PRIVILEGES") 
        return True
    except Exception as e:
        print("Error creando BD:", e)
        return False
    finally:
        if conn:
            conn.close()


def welcome(request):
    env_path = os.path.join(settings.BASE_DIR, ".env")
    load_dotenv(env_path, override=True)
    
    public_ip = get_public_ip()
    User = get_user_model()
    db_status = None
    database_ready = False
    tables_exist = False

    # ─── Etapa 1: Verificar conexión y existencia de la BD ───
    try:
        # Verificar conexión con las credenciales normales
        conn = MySQLdb.connect(
            host=os.getenv('DB_HOST'),
            port=int(os.getenv('DB_PORT')),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            database=os.getenv('DB_NAME')
        )
        
        # Verificar si las tablas existen
        with conn.cursor() as cur:
            cur.execute("SHOW TABLES")
            tables = cur.fetchall()
            tables_exist = len(tables) > 0
        
        conn.close()

        if tables_exist:
            db_status = {
                'status': 'success',
                'message': 'Tablas existentes detectadas',
                'icon': 'fa-check-circle',
                'color': 'text-green-500'
            }
            database_ready = True
        else:
            db_status = {
                'status': 'warning',
                'message': 'Base de datos vacía. Presiona "Inicializar Base de Datos" para crear las tablas.',
                'icon': 'fa-exclamation-triangle',
                'color': 'text-yellow-500'
            }

    except Exception as e:
        db_status = {
            'status': 'error',
            'message': f'Error de conexión: {e}',
            'icon': 'fa-exclamation-triangle',
            'color': 'text-red-500'
        }
        return render(request, 'templates/setup/welcome.html', {
            'db_status': db_status,
            'public_ip': public_ip
        })
    
    # Etapa 2: Inicialización de la base de datos (creación de tablas)
    if request.method == 'POST' and 'initialize_db' in request.POST:
        try:
            # Cerrar todas las conexiones existentes
            connections.close_all()
            
            # Actualizar conexiones con credenciales normales
            for alias in connections:
                connections[alias].settings_dict.update({
                    'NAME': os.getenv('DB_NAME'),
                    'USER': os.getenv('DB_USER'),
                    'PASSWORD': os.getenv('DB_PASSWORD'),
                })

            # Aplicar migraciones
            call_command('migrate', interactive=False)
            
            # Verificar tablas creadas
            with connection.cursor() as cursor:
                cursor.execute("SHOW TABLES")
                tables = cursor.fetchall()
                if len(tables) > 0:
                    db_status = {
                        'status': 'success',
                        'message': 'Tablas creadas exitosamente',
                        'icon': 'fa-check-circle',
                        'color': 'text-green-500'
                    }
                    database_ready = True
                else:
                    db_status = {
                        'status': 'error',
                        'message': 'No se crearon tablas después de las migraciones',
                        'icon': 'fa-exclamation-triangle',
                        'color': 'text-red-500'
                    }
            
        except Exception as e:
            import traceback
            print("ERROR DETALLADO:", traceback.format_exc())
            
            db_status = {
                'status': 'error',
                'message': f'Error aplicando migraciones: {e}',
                'icon': 'fa-exclamation-triangle',
                'color': 'text-red-500'
            }
    
    # Etapa 3: Creación de usuario admin
    form = None
    if database_ready:
        if request.method == 'POST' and 'create_user' in request.POST:
            form = SetupForm(request.POST)
            if form.is_valid():
                try:
                    # Crear superusuario
                    email = form.cleaned_data['email']
                    username = email.split('@')[0]
                    
                    User.objects.create_superuser(
                        email=email,
                        username=username,
                        password=form.cleaned_data['password'],
                    )
                    
                    # Autenticar y loguear al usuario
                    user = authenticate(
                        request=request,
                        username=username,
                        password=form.cleaned_data['password']
                    )
                    if user is not None:
                        login(request, user)
                        return redirect('dashboard:dashboard')
                    else:
                        form.add_error(None, 'Error al autenticar al usuario recién creado')
                except Exception as e:
                    form.add_error(None, f'Error al crear usuario: {str(e)}')
        else:
            form = SetupForm()
    
    return render(request, 'templates/setup/welcome.html', {
        'form': form,
        'db_status': db_status,
        'public_ip': public_ip,
        'database_ready': database_ready
    })

def setup_view(request):
    db_name     = "web25019"
    app_user    = "web25019_us"
    app_pass    = "SUPER_SEGURO_123"

    with connections['creator'].cursor() as c:
        c.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4")
        c.execute(f"CREATE USER IF NOT EXISTS '{app_user}'@'%' IDENTIFIED BY %s", [app_pass])
        c.execute(f"GRANT ALL PRIVILEGES ON `{db_name}`.* TO '{app_user}'@'%'")
        c.execute("FLUSH PRIVILEGES")

    # 1) Escribe/actualiza .env
    env_file = os.path.join(settings.BASE_DIR, ".env")
    with open(env_file, "a", encoding="utf-8") as f:
        f.write(f"\nDB_NAME={db_name}\nDB_USER={app_user}\nDB_PASSWORD={app_pass}\nSETUP_MODE=False\n")

    # 2) Opcional: recarga conexiones y lanza migraciones automáticamente
    from django.core import management, apps
    settings.DATABASES["default"] = settings.DATABASES["creator"].copy()
    settings.DATABASES["default"].update({
        "NAME": db_name, "USER": app_user, "PASSWORD": app_pass,
    })
    connections.databases = settings.DATABASES  # actualiza el handler
    management.call_command("migrate", interactive=False)

    return HttpResponse("✅ Base de datos creada; reinicia el servidor.")