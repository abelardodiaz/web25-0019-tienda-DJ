from django import forms
from .models import EmailConfig
from django.core.exceptions import ValidationError
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import JsonResponse
import json
from django.core.mail import send_mail, get_connection
from django.conf import settings

class EmailConfigForm(forms.ModelForm):
    # Campo para el puerto personalizado (coincide con la plantilla)
    custom_port = forms.IntegerField(
        required=False,
        label="Puerto",
        widget=forms.NumberInput(attrs={
            'class': 'w-full bg-dark-700 border border-gray-600 text-gray-200 rounded-lg px-4 py-3 focus:outline-none focus:ring-2 focus:ring-blue-500',
            'placeholder': '587'
        })
    )

    class Meta:
        model = EmailConfig
        fields = ['host', 'username', 'password', 'from_name', 'use_ssl', 'use_tls', 'active']
        widgets = {
            'host': forms.TextInput(attrs={
                'class': 'w-full bg-dark-700 border border-gray-600 text-gray-200 rounded-lg px-4 py-3 focus:outline-none focus:ring-2 focus:ring-blue-500',
                'placeholder': 'smtp.gmail.com'
            }),
            'username': forms.TextInput(attrs={
                'class': 'w-full bg-dark-700 border border-gray-600 text-gray-200 rounded-lg px-4 py-3 focus:outline-none focus:ring-2 focus:ring-blue-500',
                'placeholder': 'usuario@dominio.com'
            }),
            'password': forms.PasswordInput(attrs={
                'class': 'w-full bg-dark-700 border border-gray-600 text-gray-200 rounded-lg px-4 py-3 pr-12 focus:outline-none focus:ring-2 focus:ring-blue-500',
                'placeholder': 'Contraseña SMTP'
            }),
            'from_name': forms.TextInput(attrs={
                'class': 'w-full bg-dark-700 border border-gray-600 text-gray-200 rounded-lg px-4 py-3 focus:outline-none focus:ring-2 focus:ring-blue-500',
                'placeholder': 'Mi Aplicación'
            })
        }
        labels = {
            'host': 'Servidor SMTP',
            'username': 'Usuario',
            'password': 'Contraseña',
            'from_name': 'Nombre del remitente',
            'use_ssl': 'Usar SSL',
            'use_tls': 'Usar TLS',
            'active': 'Activar servidor SMTP'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Si existe una instancia, prellenar el puerto personalizado
        if self.instance and hasattr(self.instance, 'port'):
            self.initial['custom_port'] = self.instance.port
        else:
            self.initial['custom_port'] = 587  # Puerto por defecto

    def clean(self):
        cleaned_data = super().clean()
        custom_port = cleaned_data.get('custom_port')
        use_ssl = cleaned_data.get('use_ssl')
        use_tls = cleaned_data.get('use_tls')

        # Validar puerto
        if custom_port is None:
            cleaned_data['custom_port'] = 587  # Puerto por defecto
            custom_port = 587

        # Validar que el puerto no sea 25
        if custom_port == 25:
            raise ValidationError({
                'custom_port': 'El puerto 25 no está permitido. Use 465 (SSL) o 587 (TLS).'
            })

        # Validar SSL y TLS
        if use_ssl and use_tls:
            raise ValidationError("No se puede activar SSL y TLS al mismo tiempo. Elija uno.")

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Asignar el puerto del campo personalizado al modelo
        instance.port = self.cleaned_data.get('custom_port', 587)
        
        if commit:
            instance.save()
        return instance