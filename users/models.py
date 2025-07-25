# file: users/models.py
from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

class CustomUserManager(BaseUserManager):
    def make_random_password(self, length=10, allowed_chars="abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789"):
        """Genera una contraseña aleatoria si el método no existe en la clase base (compatibilidad)."""
        from django.utils.crypto import get_random_string
        return get_random_string(length, allowed_chars)

    def create_user(self, email=None, username=None, password=None, **extra_fields):
        """Permite crear usuarios con email o número de WhatsApp.

        - Si se proporciona email, se normaliza y se usa como identificador principal.
        - Si no hay email, se requiere `whatsapp_number` en extra_fields.
        - Si falta `username`, se autocompleta con email o whatsapp_number.
        - Si no se especifica password, genera uno aleatorio (recomendado para registros vía código).
        """

        whatsapp_number = extra_fields.get('whatsapp_number')

        if not email and not whatsapp_number:
            raise ValueError('Se requiere email o número de WhatsApp')

        if email:
            email = self.normalize_email(email)

        # Autocompletar username si no viene
        if not username:
            username = email if email else whatsapp_number

        user = self.model(email=email or '', username=username, **extra_fields)
        # Si no se envió password generamos uno para que pueda hacer login después de establecerlo
        if not password:
            password = self.make_random_password()
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, username, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'ADMIN')  # Asegurar rol ADMIN
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser debe tener is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser debe tener is_superuser=True.')
        
        return self.create_user(email, username, password, **extra_fields)

class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('ADMIN', _('Administrador')),
        ('STAFF', _('Staff')),
        ('USER', _('Usuario')),
    )

    # -------- Autenticación preferida --------
    AUTH_EMAIL = 'EM'
    AUTH_WHATSAPP = 'WA'
    AUTH_METHOD_CHOICES = (
        (AUTH_EMAIL, 'Email'),
        (AUTH_WHATSAPP, 'WhatsApp'),
    )

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='USER',
        verbose_name=_('Rol')
    )

    phone = models.CharField(
        max_length=20,
        blank=True,
        verbose_name=_('Teléfono')
    )

    whatsapp_number = models.CharField(
        max_length=20,
        unique=True,
        null=True,
        blank=True,
        verbose_name=_('Número de WhatsApp')
    )

    whatsapp_verified = models.BooleanField(default=False)
    auth_method = models.CharField(
        max_length=2,
        choices=AUTH_METHOD_CHOICES,
        default=AUTH_EMAIL,
        verbose_name=_('Método de autenticación')
    )

    descuento_cliente = models.FloatField(default=0.0, verbose_name="Descuento Cliente (%)")
    last_login = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = CustomUserManager()  # Usar manager personalizado

    def __str__(self):
        return self.username or self.email or self.whatsapp_number or "Usuario"

    class Meta:
        verbose_name = _('Usuario')
        verbose_name_plural = _('Usuarios')


# ------------------------
#  Modelo para almacenar códigos de verificación enviados por WhatsApp
# ------------------------


class WhatsAppVerification(models.Model):
    """Almacena códigos de verificación enviados a números de WhatsApp."""

    number = models.CharField(max_length=20)
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    attempts = models.PositiveIntegerField(default=0)
    resend_count = models.PositiveIntegerField(default=0)

    class Meta:
        indexes = [
            models.Index(fields=["number"]),
        ]

    def is_expired(self):
        return timezone.now() >= self.expires_at

    def __str__(self):
        return f"{self.number} - {self.code}"