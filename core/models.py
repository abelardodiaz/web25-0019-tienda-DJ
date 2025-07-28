# file: core/models.py
# core/models.py
from django.db import models
from django.contrib.auth import get_user_model
from encrypted_model_fields.fields import EncryptedTextField
from django.utils import timezone
from django.core.exceptions import ValidationError

User = get_user_model()

class SystemConfig(models.Model):
    protected_users = models.ManyToManyField(
        User,
        blank=True,
        verbose_name="Usuarios protegidos",
        help_text="Usuarios que no pueden ser eliminados"
    )
    
    class Meta:
        verbose_name = "Configuración del Sistema"
        verbose_name_plural = "Configuraciones del Sistema"
    
    @classmethod
    def get_instance(cls):
        return cls.objects.first() or cls.objects.create()

def validate_port(value):
    if value == 25:
        raise ValidationError("El puerto 25 está bloqueado por políticas de seguridad")

class EmailConfig(models.Model):
    """Configuración SMTP singleton para envío de correos"""
    host = models.CharField(
        max_length=255, 
        blank=True, 
        verbose_name="Host SMTP"
    )
    port = models.PositiveIntegerField(
        default=587,
        validators=[validate_port],
        verbose_name="Puerto"
    )
    use_ssl = models.BooleanField(
        default=False,
        verbose_name="Usar SSL"
    )
    use_tls = models.BooleanField(
        default=True,
        verbose_name="Usar TLS"
    )
    username = models.CharField(
        max_length=255, 
        blank=True,
        verbose_name="Usuario"
    )
    password = EncryptedTextField(
        blank=True,
        verbose_name="Contraseña"
    )
    from_name = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Nombre del remitente"
    )
    active = models.BooleanField(
        default=False,
        verbose_name="Activo"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Actualizado el"
    )

    class Meta:
        verbose_name = "Configuración de correo"
        verbose_name_plural = "Configuraciones de correo"

    def __str__(self):
        return f"SMTP: {self.host}:{self.port} ({'Activo' if self.active else 'Inactivo'})"