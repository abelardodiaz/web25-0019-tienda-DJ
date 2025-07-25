from django.conf import settings
from random import randint
from datetime import timedelta
from django.utils import timezone

try:
    from twilio.rest import Client
except ImportError:
    # Twilio is optional during development/testing. Fail gracefully.
    Client = None

__all__ = [
    "generate_verification_code",
    "send_whatsapp_code",
    "verification_expiry",
]

DEFAULT_CODE_LENGTH = 6
CODE_EXPIRY_MINUTES = 10  # Código válido por 10 minutos

def generate_verification_code(length: int = DEFAULT_CODE_LENGTH) -> str:
    """Genera un código numérico aleatorio de `length` dígitos."""
    start = 10 ** (length - 1)
    end = (10 ** length) - 1
    return str(randint(start, end))


def verification_expiry(minutes: int = CODE_EXPIRY_MINUTES):
    """Devuelve un `datetime` de expiración a `minutes` desde ahora."""
    return timezone.now() + timedelta(minutes=minutes)


def _client() -> "Client | None":
    """Crea una instancia del cliente Twilio si las credenciales están configuradas."""
    if not Client:
        return None

    sid = getattr(settings, "TWILIO_ACCOUNT_SID", None)
    token = getattr(settings, "TWILIO_AUTH_TOKEN", None)

    if not sid or not token:
        return None

    return Client(sid, token)


def send_whatsapp_code(number: str, code: str) -> str | None:
    """Envía un mensaje de WhatsApp con el `code` al `number`.

    Retorna el SID del mensaje en caso de éxito o `None` si el envío falló o
    Twilio no está configurado. El `number` debe incluir el prefijo `whatsapp:`
    según lo requiere Twilio.
    """
    client = _client()
    if client is None:
        # En entornos de desarrollo podemos imprimir en consola
        print(f"[DEBUG] Código de verificación para {number}: {code}")
        return None

    twilio_from = getattr(settings, "TWILIO_WHATSAPP_NUMBER", None)
    if not twilio_from:
        raise ValueError("TWILIO_WHATSAPP_NUMBER no configurado en settings")

    message = client.messages.create(
        body=f"Tu código de verificación es: {code}",
        from_=twilio_from,
        to=f"whatsapp:{number}" if not number.startswith("whatsapp:") else number,
    )
    return message.sid 