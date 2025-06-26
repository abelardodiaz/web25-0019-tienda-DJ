
# file: dashboard/tipo_cambio.py

import requests
import logging
from django.utils import timezone
from products.models import SyscomCredential

# Configurar logger
logger = logging.getLogger(__name__)

def obtener_tipo_cambio():
    """
    Obtiene el tipo de cambio actual desde la API de Syscom
    """
    try:
        # URL de la API de Syscom para tipo de cambio
        url = "https://developers.syscom.mx/api/v1/tipocambio"
        
        # Obtener credenciales
        try:
            cred = SyscomCredential.objects.latest('id')
        except SyscomCredential.DoesNotExist:
            logger.error("No hay credenciales Syscom configuradas")
            return None
        
        # Verificar si el token es válido
        if not cred.token or cred.is_expired():
            logger.error("Token de Syscom inválido o expirado")
            return None
        
        headers = {
            "Authorization": f"Bearer {cred.token}",
            "Accept": "application/json"
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        # Validar la estructura de la respuesta
        if not isinstance(data, dict) or 'preferencial' not in data:
            logger.error(f"Respuesta inesperada de Syscom: {data}")
            return None
            
        try:
            # Convertir a float y redondear a 4 decimales
            tipo_cambio = float(data['preferencial'])
            return round(tipo_cambio, 4)
        except (TypeError, ValueError) as e:
            logger.error(f"Error convirtiendo tipo de cambio: {str(e)}")
            return None
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Error de conexión: {str(e)}")
        return None
    except Exception as e:
        logger.exception(f"Error inesperado al obtener tipo de cambio: {str(e)}")
        return None
