# file: core/middleware.py
# Django 5.2.3.
# file: core/middleware.py
from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib.auth import get_user_model

class FirstRunMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        User = get_user_model()
        if not User.objects.exists() and request.path != reverse('setup:welcome'):
            return redirect('setup:welcome')
        return self.get_response(request)
    

class RoleMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        # Solo procesar si el usuario está autenticado
        if request.user.is_authenticated:
            # Asignar el rol del usuario al objeto request
            request.user_role = request.user.role
            
            # Verificar acceso a rutas de administración
            if request.path.startswith('/admin/') and request.user_role != 'ADMIN':
                return HttpResponseForbidden("Acceso denegado")
        
        response = self.get_response(request)
        return response