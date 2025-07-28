#file : core/views.py
from django.contrib.auth.views import PasswordChangeView
from django.http import JsonResponse
from django.contrib.auth import update_session_auth_hash
from django.views.decorators.csrf import csrf_protect
from django.utils.decorators import method_decorator
import os
from django.views import View
from django.shortcuts import redirect, render
from django.contrib.auth import logout
from django.contrib.auth.views import LoginView
from users.decorators import unauthenticated_user
from django.views.generic import FormView
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from .forms import EmailConfigForm
from .models import EmailConfig
from django.http import JsonResponse
import json
from django.core.mail import send_mail, get_connection
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import validate_email


@method_decorator(csrf_protect, name='dispatch')
class CustomPasswordChangeView(PasswordChangeView):
    def post(self, request, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            form.save()
            update_session_auth_hash(request, form.user)
            return JsonResponse({
                'success': True,
                'message': 'Contraseña cambiada exitosamente'
            })
        return JsonResponse({
            'success': False,
            'errors': form.errors.get_json_data()
        }, status=400)


class CustomLogoutView(View):
    """Logout que redirige a la página actual o a 'next'."""

    def get(self, request, *args, **kwargs):
        logout(request)
        next_url = request.GET.get('next') or request.META.get('HTTP_REFERER') or '/'
        if 'logout' in next_url:
            next_url = '/'
        return redirect(next_url)

    def post(self, request, *args, **kwargs):
        logout(request)
        next_url = request.POST.get('next') or request.META.get('HTTP_REFERER') or '/'
        if 'logout' in next_url:
            next_url = '/'
        return redirect(next_url)

@method_decorator(unauthenticated_user, name='dispatch')
class CustomLoginView(LoginView):
    """View para LOGIN por WhatsApp (solo si el número ya existe)."""
    # The rest of the class definition would go here
    pass

@method_decorator(unauthenticated_user, name='dispatch')
class WhatsAppRegistrationView(View):
    """View para REGISTRO por WhatsApp (crea nuevo usuario si no existe)."""
    # The rest of the class definition would go here
    pass

@method_decorator(unauthenticated_user, name='dispatch')
class WhatsAppLoginView(WhatsAppRegistrationView):
    """View para LOGIN por WhatsApp (solo si el número ya existe)."""
    # The rest of the class definition would go here
    pass

@method_decorator(unauthenticated_user, name='dispatch')
class VerifyWhatsAppCodeView(View):
    """Verificación común para login/register, basada en flag de sesión."""
    # The rest of the class definition would go here
    pass

class EmailConfigView(LoginRequiredMixin, UserPassesTestMixin, FormView):
    template_name = 'dashboard/email_config.html'
    form_class = EmailConfigForm
    success_url = '/panel/email/'
    
    def test_func(self):
        return self.request.user.is_staff
    
    def get_object(self):
        return EmailConfig.objects.first()
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['instance'] = self.get_object()
        return kwargs
    
    def form_valid(self, form):
        form.save()
        messages.success(self.request, '¡Configuración SMTP actualizada correctamente!')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, 'Por favor corrige los errores en el formulario')
        return super().form_invalid(form)
    
    def post(self, request, *args, **kwargs):
        """Sobrescribimos para añadir logging pero delegamos en FormView."""
        self.object = self.get_object()
        form = self.get_form()

        print("Datos del formulario:", request.POST)

        if form.is_valid():
            print("Datos limpios:", form.cleaned_data)
            return self.form_valid(form)
        else:
            print("Errores de validación:", form.errors)
            return self.form_invalid(form)


class EmailTestView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return self.request.user.is_staff
    
    def post(self, request, *args, **kwargs):
        try:
            # Decodificar JSON correctamente
            data = json.loads(request.body)
            email = data.get('email', '').strip()
            
            # Validar email
            if not email or '@' not in email:
                return JsonResponse({
                    'ok': False,
                    'msg': 'Email inválido'
                }, status=400)
            
            config = EmailConfig.objects.first()
            if not config or not config.active or not config.host:
                return JsonResponse({
                    'ok': False,
                    'message': 'Configuración SMTP no activa o incompleta'
                }, status=400)
            
            # Configurar conexión SMTP
            connection = get_connection(
                backend='django.core.mail.backends.smtp.EmailBackend',
                host=config.host,
                port=config.port,
                username=config.username,
                password=config.password,
                use_tls=config.use_tls,
                use_ssl=config.use_ssl
            )
            
            # Enviar correo de prueba
            send_mail(
                subject='Prueba SMTP exitosa',
                message='¡Tu configuración SMTP funciona correctamente!',
                from_email=config.from_name or settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                connection=connection,
                fail_silently=False
            )
            
            return JsonResponse({
                'ok': True,
                'message': f'Correo de prueba enviado a {email} correctamente'
            })
            
        except Exception as e:
            return JsonResponse({
                'ok': False,
                'message': f'Error al enviar correo: {str(e)}'
            }, status=500)