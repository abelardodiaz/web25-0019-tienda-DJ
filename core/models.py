# file: core/models.py
# core/models.py
from django.db import models
from django.contrib.auth import get_user_model

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