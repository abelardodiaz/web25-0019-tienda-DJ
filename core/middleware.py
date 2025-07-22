# file: core/middleware.py
# Django 5.2.3.
# file: core/middleware.py
from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.db import OperationalError, ProgrammingError, connections
from django.db import DatabaseError
from django.db import OperationalError
from django.conf import settings
import os
from django.conf import settings
from django.http import HttpResponseRedirect


# core/middleware.py
import os
from django.conf import settings
from django.urls import reverse
from django.http import HttpResponseRedirect

import logging
# Usar DEBUG para no mostrar en consola (nivel >=WARNING) pero sí registrar en archivo
logging.debug("SETUP_MODE en runtime: %s", os.getenv('SETUP_MODE'))



class FirstRunMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Permitir acceso a /setup/ y a static
        if request.path.startswith('/setup/') or request.path.startswith(settings.STATIC_URL):
            return self.get_response(request)

        # Verificar si hay usuarios en la BD para determinar si es primera ejecución
        User = get_user_model()
        try:
            if not User.objects.exists():
                return HttpResponseRedirect(reverse('setup:welcome'))
        except Exception:
            # Si hay error al consultar la BD, asumimos que necesita setup
            return HttpResponseRedirect(reverse('setup:welcome'))

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