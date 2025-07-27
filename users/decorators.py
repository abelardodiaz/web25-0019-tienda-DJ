# file:users/decorators.py
from django.http import HttpResponseForbidden
from django.shortcuts import redirect  # Add this import

def admin_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or request.user.role != 'ADMIN':
            return HttpResponseForbidden("Acceso restringido a administradores")
        return view_func(request, *args, **kwargs)
    return wrapper

def staff_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or request.user.role not in ['ADMIN', 'STAFF']:
            return HttpResponseForbidden("Acceso restringido al personal autorizado")
        return view_func(request, *args, **kwargs)
    return wrapper

# Add new decorator for unauthenticated users
def unauthenticated_user(view_func):
    def wrapper_func(request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('/')  # Redirige a home
        return view_func(request, *args, **kwargs)
    return wrapper_func