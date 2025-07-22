#####PENDIENTES
##### - Verificar que el usuario sea superusuario antes de permitir el reset de la base de datos.
##### - Mejorar la seguridad de la eliminación de usuarios, asegurando que no se pueda eliminar al último administrador.
####  - implementar un sistema de registro de acciones de administración, como eliminaciones de usuarios.
###  - crear una vista para editar usuarios, permitiendo cambiar roles y datos.
#### - Implementar un sistema de paginación para la lista de usuarios en el panel de administración.
#### - Añadir una vista para ver el historial de acciones de administración, como eliminaciones de usuarios.
### - Crear un comando de Django para reset: python manage.py reset_system --full Que elimine todas las tablas y datos pero mantenga las migraciones

# file dashboard/views.py
from django.db import transaction, connection
from django.contrib import messages
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.admin.models import LogEntry, DELETION
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from users.models import CustomUser as User
from products.models import Product, SyscomCredential, ExchangeRate
from users.forms import UserEditForm 
from core.models import SystemConfig
from users.models import CustomUser
from products.models import SyscomCredential
from django.utils import timezone
from datetime import timedelta
import requests
from dashboard.tipo_cambio import obtener_tipo_cambio
from django.contrib.admin.models import LogEntry, DELETION, ADDITION, CHANGE


@login_required
@staff_member_required
def admin_panel(request):
    # Obtener credenciales Syscom si existen
    try:
        syscom_credential = SyscomCredential.objects.latest('id')
    except SyscomCredential.DoesNotExist:
        syscom_credential = None

    """Vista principal del panel de administración"""
    users_list = User.objects.all().order_by('-date_joined')
    paginator = Paginator(users_list, 10)
    page_number = request.GET.get('page')
    users = paginator.get_page(page_number)
    
    context = {
        'syscom_credential': syscom_credential,
        'users': users,
        'total_users': User.objects.count(),
        # 'total_admins': User.objects.filter(role='ADMIN').count(),
        # 'total_staff': User.objects.filter(role='STAFF').count(),
        # 'total_customers': User.objects.filter(role='USER').count(),
        'total_products': Product.objects.count(),      # Ajusta según tu modelo
        # 'total_orders': Pedido.objects.count(),           # Ajusta según tu modelo
        # 'total_income': Pedido.objects.aggregate(         # Ejemplo de cálculo de ingresos
            # total=Sum('total')
        # )['total'] or 0,
    }
    return render(request, 'admin_panel.html', context)

@staff_member_required
def save_syscom_credentials(request):
    if request.method == 'POST':
        client_id = request.POST.get('client_id')
        client_secret = request.POST.get('client_secret')
        
        if not client_id or not client_secret:
            messages.error(request, 'Client ID y Client Secret son requeridos')
            return redirect('dashboard:admin_panel')
        
        # Crear o actualizar credenciales
        cred = SyscomCredential.objects.first()
        if cred:
            cred.client_id = client_id
            cred.client_secret = client_secret
            cred.save()
        else:
            SyscomCredential.objects.create(client_id=client_id, client_secret=client_secret)
        
        messages.success(request, 'Credenciales guardadas correctamente')
        return redirect('dashboard:admin_panel')
    
    return redirect('dashboard:admin_panel')

@staff_member_required
def renew_syscom_token(request):
    try:
        cred = SyscomCredential.objects.latest('id')
    except SyscomCredential.DoesNotExist:
        messages.error(request, 'Primero debe configurar las credenciales')
        return redirect('dashboard:admin_panel')
    
    # Lógica para renovar el token
    try:
        url = "https://developers.syscom.mx/oauth/token"
        data = {
            "client_id": cred.client_id,
            "client_secret": cred.client_secret,
            "grant_type": "client_credentials"
        }
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        response = requests.post(url, data=data, headers=headers)
        response.raise_for_status()
        token_data = response.json()
        
        # Actualizar credencial con nuevo token
        cred.token = token_data['access_token']
        cred.expires_at = timezone.now() + timedelta(seconds=token_data['expires_in'])
        cred.save()
        
        messages.success(request, 'Token renovado correctamente')
    except requests.exceptions.RequestException as e:
        messages.error(request, f'Error al renovar token: {str(e)}')
    except KeyError:
        messages.error(request, 'Respuesta inválida de la API de Syscom')
    
    return redirect('dashboard:admin_panel')


@staff_member_required
def edit_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        form = UserEditForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            return redirect('admin_panel')
    else:
        form = UserEditForm(instance=user)
    
    return render(request, 'edit_user.html', {'form': form})



@staff_member_required
def delete_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    
    # Verificaciones de seguridad mejoradas
    is_last_admin = User.objects.filter(is_superuser=True).count() <= 1 and user.is_superuser
    is_current_user = request.user == user
    config = SystemConfig.get_instance()
    
    # Razones por las que no se puede eliminar
    protection_reasons = []
    
    if user in config.protected_users.all():
        protection_reasons.append("está protegido por configuración del sistema")
    
    if is_last_admin:
        protection_reasons.append("es el último administrador del sistema")
    
    if is_current_user:
        protection_reasons.append("no puedes eliminarte a ti mismo")
    
    # Manejo de la solicitud POST
    if request.method == 'POST':
        if protection_reasons:
            messages.error(request, f"No se puede eliminar este usuario porque {', '.join(protection_reasons)}.")
        else:
            try:
                # Eliminación segura con registro   
                username = user.username
                # user.delete()
                user.is_active = False
                user.save()
                messages.success(request, f"Usuario {user.username} desactivado correctamente")

                # Registrar la acción
                LogEntry.objects.log_action(
                    user_id=request.user.id,
                    content_type_id=ContentType.objects.get_for_model(User).pk,
                    object_id=user_id,
                    object_repr=f"Usuario {username}",
                    action_flag=DELETION,
                    change_message="Eliminado por administrador"
                )
                
                messages.success(request, f"Usuario {username} eliminado correctamente")
            except Exception as e:
                messages.error(request, f"Error al eliminar usuario: {str(e)}")
        
        return redirect('dashboard:admin_panel')
    
    # Contexto para la plantilla
    context = {
        'user': user,
        'protection_reasons': protection_reasons,
        'can_be_deleted': not protection_reasons
    }
    
    return render(request, 'delete_user.html', context)

@staff_member_required
def reset_db_partial(request):
    # Verificar que el usuario sea superusuario
    if not request.user.is_superuser:
        messages.error(request, "Solo los administradores pueden realizar esta acción")
        return redirect('dashboard:admin_panel')
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Desactivar restricciones de clave foránea
                with connection.cursor() as cursor:
                    cursor.execute("SET FOREIGN_KEY_CHECKS=0")
                
                # Tablas a conservar (incluyendo tablas de sesión)
                preserved_tables = [
                    'users_customuser',
                    'core_systemconfig',
                    'core_systemconfig_protected_users',
                    'products_exchangerate',
                    'products_syscomcredential',
                    'django_session',  # Conservar sesiones
                    'django_migrations',  # Conservar migraciones
                ]
                
                # Obtener todas las tablas en la base de datos
                with connection.cursor() as cursor:
                    cursor.execute("SHOW TABLES")
                    all_tables = [row[0] for row in cursor.fetchall()]
                
                # Eliminar datos de tablas no preservadas
                for table in all_tables:
                    if table not in preserved_tables:
                        with connection.cursor() as cursor:
                            cursor.execute(f"TRUNCATE TABLE `{table}`")
                
                # Reactivar restricciones de clave foránea
                with connection.cursor() as cursor:
                    cursor.execute("SET FOREIGN_KEY_CHECKS=1")
                
                # Restaurar configuración mínima del sistema
                config = SystemConfig.get_instance()
                config.protected_users.set(
                    CustomUser.objects.filter(is_superuser=True)
                )
                config.save()
                
                messages.success(request, "Reset parcial completado: Se han eliminado todos los datos excepto usuarios, tokens Syscom y tipos de cambio")
        
        except Exception as e:
            messages.error(request, f"Error durante el reset parcial: {str(e)}")
            return redirect('dashboard:admin_panel')
        
        return redirect('dashboard:admin_panel')
    
    # Si no es POST, mostrar confirmación
    return render(request, 'confirm_reset.html', {
        'reset_type': 'parcial',
        'message': '¿Estás seguro de realizar un reset parcial? Se eliminarán todos los datos excepto usuarios, tokens Syscom y tipos de cambio.'
    })

@staff_member_required
def reset_db_full(request):
    # Verificar que el usuario sea superusuario
    if not request.user.is_superuser:
        messages.error(request, "Solo los administradores pueden realizar esta acción")
        return redirect('dashboard:admin_panel')
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Desactivar restricciones de clave foránea
                with connection.cursor() as cursor:
                    cursor.execute("SET FOREIGN_KEY_CHECKS=0")
                
                # Obtener todas las tablas en la base de datos
                with connection.cursor() as cursor:
                    cursor.execute("SHOW TABLES")
                    all_tables = [row[0] for row in cursor.fetchall()]
                
                # Eliminar datos de todas las tablas excepto migraciones
                for table in all_tables:
                    if table != 'django_migrations':  # Conservar migraciones
                        with connection.cursor() as cursor:
                            cursor.execute(f"TRUNCATE TABLE `{table}`")
                
                # Reactivar restricciones de clave foránea
                with connection.cursor() as cursor:
                    cursor.execute("SET FOREIGN_KEY_CHECKS=1")
                
                messages.success(request, "Reset completo realizado. Todos los datos han sido eliminados.")
                return redirect('setup:welcome')
        
        except Exception as e:
            messages.error(request, f"Error durante el reset completo: {str(e)}")
            return redirect('dashboard:admin_panel')
    
    # Si no es POST, mostrar confirmación
    return render(request, 'confirm_reset.html', {
        'reset_type': 'completo',
        'message': '¿Estás seguro de realizar un reset completo? Se eliminarán TODOS los datos. Serás redirigido a la página de configuración inicial.'
    })

# FIXED: Tipo cambio view
@staff_member_required
def tipo_cambio(request):
    # Get latest exchange rate
    latest_rate = ExchangeRate.objects.order_by('-created_at').first()
    
    # Get history (last 7 days)
    seven_days_ago = timezone.now() - timedelta(days=7)
    history = ExchangeRate.objects.filter(
        created_at__gte=seven_days_ago
    ).order_by('-created_at')[:10]
    
    # Handle manual update
    if request.method == 'POST':
        nuevo_tipo_cambio = obtener_tipo_cambio()
        
        if nuevo_tipo_cambio is not None:
            # Create new record
            nuevo_registro = ExchangeRate(
                rate=nuevo_tipo_cambio,
                updated_by=request.user.username,
                update_type='manual'
            )
            nuevo_registro.save()
            
            # Log the action
            LogEntry.objects.log_action(
                user_id=request.user.id,
                content_type_id=ContentType.objects.get_for_model(ExchangeRate).pk,
                object_id=nuevo_registro.id,
                object_repr=f"Tipo de Cambio {nuevo_tipo_cambio}",
                action_flag=ADDITION,
                change_message="Actualización manual"
            )
            
            messages.success(request, f'Tipo de cambio actualizado a {nuevo_tipo_cambio}')
        else:
            messages.error(request, 'Error al obtener el tipo de cambio')
        return redirect('dashboard:tipo_cambio')
    
    # Calculate next update
    now = timezone.now()
    next_update = now.replace(hour=9, minute=0, second=0, microsecond=0)
    if now.hour >= 9:
        next_update += timedelta(days=1)
    
    return render(request, 'tipo_cambio.html', {
        'current_rate': latest_rate.rate if latest_rate else None,
        'last_updated': latest_rate.created_at if latest_rate else None,
        'history': history,
        'next_update': next_update
    })

# NEW: Admin action history view
@staff_member_required
def admin_action_log(request):
    # Get all admin actions
    log_entries = LogEntry.objects.all().order_by('-action_time')
    
    # Pagination
    paginator = Paginator(log_entries, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'admin_action_log.html', {'page_obj': page_obj})
