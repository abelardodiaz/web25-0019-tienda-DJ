

# file dashboard/views.py
from django.contrib import messages
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.admin.models import LogEntry, DELETION
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from users.models import CustomUser as User
from products.models import Product
from users.forms import UserEditForm 

from core.models import SystemConfig




@login_required
@staff_member_required
def admin_panel(request):
    """Vista principal del panel de administración"""
    users_list = User.objects.all().order_by('-date_joined')
    paginator = Paginator(users_list, 10)
    page_number = request.GET.get('page')
    users = paginator.get_page(page_number)
    
    context = {
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
