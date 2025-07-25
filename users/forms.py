# users/forms.py
from django import forms
from django.contrib.auth.forms import UserChangeForm
from django.core.exceptions import ValidationError
from .models import CustomUser


password = None

class UserEditForm(UserChangeForm):
    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'first_name', 'last_name', 'is_active', 'is_staff', 'is_superuser']
        # Añade cualquier otro campo personalizado que tengas en tu CustomUser


class WhatsAppNumberForm(forms.Form):
    country_code = forms.CharField(
        initial="52",
        label="Código país",
        disabled=True,
        required=False,
        widget=forms.TextInput(attrs={
            "class": "w-20 bg-dark-700 text-gray-300 rounded-l-lg text-center py-3 text-xl mr-1",
        })
    )

    phone = forms.CharField(
        max_length=10,
        label="Número (10 dígitos)",
        widget=forms.TextInput(attrs={
            "placeholder": "4441234567",
            "class": "flex-1 bg-dark-700 text-gray-200 rounded-r-lg px-4 py-3 text-xl tracking-wider",
        })
    )

    def __init__(self, *args, require_unique=True, **kwargs):
        self.require_unique = require_unique
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned = super().clean()
        phone = cleaned.get("phone", "").strip()
        phone = ''.join(filter(str.isdigit, phone))

        if len(phone) != 10:
            self.add_error("phone", "El número local debe tener 10 dígitos")
            return cleaned

        number = f"52{phone}"

        exists = CustomUser.objects.filter(whatsapp_number=number).exists()
        if self.require_unique and exists:
            self.add_error("phone", ValidationError("Este número ya está registrado", code="duplicate"))
        elif not self.require_unique and not exists:
            self.add_error("phone", ValidationError("Este número no está registrado", code="not_registered"))

        cleaned["whatsapp_number"] = number
        return cleaned


class VerifyCodeForm(forms.Form):
    verification_code = forms.CharField(
        max_length=6,
        label="Código de verificación",
        widget=forms.TextInput(attrs={
            "placeholder": "123456",
            "class": "form-control",
        }),
    )