# users/forms.py
from django import forms
from django.contrib.auth.forms import UserChangeForm
from .models import CustomUser


password = None

class UserEditForm(UserChangeForm):
    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'first_name', 'last_name', 'is_active', 'is_staff', 'is_superuser']
        # Añade cualquier otro campo personalizado que tengas en tu CustomUser