# core/backends.py
# Crea un backend que evite errores si la tabla no existe:
from django.contrib.auth.backends import ModelBackend
from django.db import OperationalError

class SafeSetupAuthBackend(ModelBackend):
    def get_user(self, user_id):
        try:
            return super().get_user(user_id)
        except OperationalError:  # Si la tabla no existe, ignora el error
            return None