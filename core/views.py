#file : core/views.py
from django.contrib.auth.views import PasswordChangeView
from django.http import JsonResponse
from django.contrib.auth import update_session_auth_hash
from django.views.decorators.csrf import csrf_protect
from django.utils.decorators import method_decorator
import os

print(os.getenv('DB_NAME')) 

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