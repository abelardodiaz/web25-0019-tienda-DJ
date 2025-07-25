# core/backends.py
# Crea un backend que evite errores si la tabla no existe:
from django.contrib.auth.backends import ModelBackend
from django.db import OperationalError
from django.db.models import Q

# Import inside try/except to avoid issues during migrations when users app may not be ready
try:
    from users.models import CustomUser
except Exception:  # noqa
    CustomUser = None


class SafeSetupAuthBackend(ModelBackend):
    def get_user(self, user_id):
        try:
            return super().get_user(user_id)
        except OperationalError:  # Si la tabla no existe, ignora el error
            return None


# --------------------------------------------------
#  Backend que permite autenticar por email O número de WhatsApp
# --------------------------------------------------


class WhatsAppOrEmailBackend(SafeSetupAuthBackend):
    """Autenticación por correo, username o número de WhatsApp.

    - Primero busca coincidencia exacta (case-insensitive) en `email`, `whatsapp_number` o `username`.
    - Verifica la contraseña.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        if not username or not password or CustomUser is None:
            return None

        try:
            user = CustomUser.objects.get(
                Q(email__iexact=username) |
                Q(whatsapp_number=username) |
                Q(username=username)
            )
        except CustomUser.DoesNotExist:
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None