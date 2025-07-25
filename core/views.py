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