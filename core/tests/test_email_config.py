import pytest
from django.core.exceptions import ValidationError
from core.models import EmailConfig
from core.forms import EmailConfigForm
from django.core import mail
from unittest.mock import patch

@pytest.mark.django_db
def test_port_25_validation():
    # Test que el puerto 25 genera ValidationError
    form = EmailConfigForm(data={
        'port_choice': 'custom',
        'custom_port': 25,
        'host': 'smtp.example.com',
        'use_ssl': False,
        'use_tls': False,
        'username': 'user',
        'password': 'pass',
        'from_name': 'Test',
        'active': True
    })
    assert not form.is_valid()
    assert 'El puerto 25 está bloqueado' in form.errors['__all__'][0]

@pytest.mark.django_db
def test_password_encryption():
    # Test que la contraseña se guarda cifrada
    config = EmailConfig.objects.create(
        host='smtp.example.com',
        port=587,
        username='user',
        password='secret',
        from_name='Test',
        active=True
    )
    
    # Verificar que no está en texto plano
    assert config.password != 'secret'
    
    # Verificar que se puede leer correctamente
    assert config.password == 'secret'

@pytest.mark.django_db
@patch('django.core.mail.get_connection')
def test_send_test_email_invalid_host(mock_get_connection):
    # Test que send_test_email captura errores con host inválido
    from core.views import EmailTestView
    
    # Simular error de conexión
    mock_get_connection.side_effect = Exception('Could not connect to SMTP host')
    
    # Crear configuración
    config = EmailConfig.objects.create(
        host='invalid.host',
        port=587,
        username='user',
        password='pass',
        from_name='Test',
        active=True
    )
    
    # Crear request simulada
    class Request:
        user = type('User', (object,), {'is_staff': True})
        body = b'{"email": "test@example.com"}'
    
    # Probar la vista
    response = EmailTestView().post(Request())
    data = response.json()
    
    assert response.status_code == 500
    assert not data['ok']
    assert 'Error al enviar correo' in data['message'] 