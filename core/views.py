#file : core/views.py
from django.contrib.auth.views import PasswordChangeView
from django.http import JsonResponse
from django.contrib.auth import update_session_auth_hash
from django.views.decorators.csrf import csrf_protect
from django.utils.decorators import method_decorator
import os
from django.views import View
from django.shortcuts import redirect
from django.contrib.auth import logout
from django.contrib.auth.views import LoginView
from users.decorators import unauthenticated_user


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