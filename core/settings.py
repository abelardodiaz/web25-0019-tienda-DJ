# file: core/settings.py
"""
Django 5.2.3.
"""
import os, environ
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()
# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
environ.Env.read_env(BASE_DIR / '.env')
env = environ.Env()
# SETUP_MODE = env.bool("SETUP_MODE", False) 
SECRET_KEY = 'django-insecure-o@5==b%^nw6k9!1i63l1$m0g%__$^zge%$e6(6@-s5j07bzql6'
DEBUG = True
ALLOWED_HOSTS = ['192.168.0.5', '192.168.0.8','localhost', '127.0.0.1']

import os



INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'users',
    'products',
    'tasks',
    'tailwind',
    'setup',
    'dashboard',
    'catalogo',
    'core',
    'widget_tweaks',
    'django_ckeditor_5',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',  # ← Mantener pero usará cookies
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'core.middleware.FirstRunMiddleware',  # ← Nuestro middleware personalizado
    'core.middleware.RoleMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [ BASE_DIR / 'templates' ], 
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                # default Django processors…
                "django.template.context_processors.request",
                # ➊  nuestro nuevo processor
                "catalogo.context_processors.categorias_marcas",
                "catalogo.context_processors.cart_summary",
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'

# CREATOR_CONN = {
#     "ENGINE": "django.db.backends.mysql",
#     "CONN_HEALTH_CHECKS": False,
#     "CONN_MAX_AGE": 0,
#     "AUTOCOMMIT": True,
#     "USER":   env("DB_CREATOR_USER"),
#     "PASSWORD": env("DB_CREATOR_PASSWORD"),
#     "HOST":   env("DB_HOST", default="localhost"),
#     "PORT":   env.int("DB_PORT", default=3306),
#     "OPTIONS": {
#         "init_command": "SET sql_mode='STRICT_TRANS_TABLES', time_zone = '+00:00'",  # Modificado
#     },
#     "ATOMIC_REQUESTS": False,
# }

# if SETUP_MODE:
#     SESSION_ENGINE = "django.contrib.sessions.backends.signed_cookies"
#     # En modo setup apuntamos 'default' a una BD del sistema
#     # (information_schema existe siempre, evita el 1046)
#     DATABASES = {
#         "default": { **CREATOR_CONN, "NAME": "information_schema" },
#         "creator": { **CREATOR_CONN, "NAME": "" }  # opcional, para tu vista /setup
#     }
# else:
#     SESSION_ENGINE = "django.contrib.sessions.backends.db"   # comportamiento normal
#     # App ya instalada → usar la BD real con el usuario normal
#     DATABASES = {
#         "default": {
#             "ENGINE": "django.db.backends.mysql",
#             "CONN_HEALTH_CHECKS": False,
#             "CONN_MAX_AGE": 0,
#             "AUTOCOMMIT": True,
#             "NAME": env("DB_NAME"),
#             "USER": env("DB_USER"),
#             "PASSWORD": env("DB_PASSWORD"),
#             "HOST": env("DB_HOST", default="localhost"),
#             "PORT": env.int("DB_PORT", default=3306),
#             "OPTIONS": {"init_command": "SET sql_mode='STRICT_TRANS_TABLES', time_zone = '+00:00'",},
#             "TIME_ZONE": "UTC",  # ¡AÑADE ESTA LÍNEA!
#             "ATOMIC_REQUESTS": False,
#         }
#     }

# if not SETUP_MODE:
#     # Solo añadimos 'default' cuando la BD ya existe
#     DATABASES["default"] = {
#         "ENGINE": "django.db.backends.mysql",
#         "CONN_HEALTH_CHECKS": False,
#         "CONN_MAX_AGE": 0,
#         "AUTOCOMMIT": True,
#         "NAME": env("DB_NAME"),               # web25019
#         "USER": env("DB_USER"),               # web25019_us
#         "PASSWORD": env("DB_PASSWORD"),
#         "HOST": env("DB_HOST", default="localhost"),
#         "PORT": env.int("DB_PORT", default="3306"),
#         "OPTIONS": {"init_command": "SET sql_mode='STRICT_TRANS_TABLES', time_zone = '+00:00'",},
#         "TIME_ZONE": "UTC",  # ¡AÑADE ESTA LÍNEA!
#         "ATOMIC_REQUESTS": False,
#     }

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": env("DB_NAME"),
        "USER": env("DB_USER"),
        "PASSWORD": env("DB_PASSWORD"),
        "HOST": env("DB_HOST", default="localhost"),
        "PORT": env.int("DB_PORT", default=3306),
        "OPTIONS": {
            "init_command": "SET sql_mode='STRICT_TRANS_TABLES', time_zone = '+00:00'",
        },
        "TIME_ZONE": "UTC",
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Configuración de archivos estáticos
STATIC_URL = '/static/'  # URL para acceder a los archivos estáticos

# Directorios adicionales (carpeta global)
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]

# Carpeta para producción (donde se copian los archivos con collectstatic)
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Custom user model
AUTH_USER_MODEL = 'users.CustomUser'

# Tailwind CSS configuration
TAILWIND_APP_NAME = 'tema_base_oscuro'

INTERNAL_IPS = ["127.0.0.1"]  # Necesario para desarrollo

# Ruta al ejecutable de npm en Windows
NPM_BIN_PATH = r"C:\Program Files\nodejs\npm.cmd"

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/account/profile/'       # o el nombre de tu URL: reverse_lazy('home')
LOGOUT_REDIRECT_URL = '/'      # opcional, para después del logout

APPEND_SLASH = True

IVA = env.float('IVA', 16.0) / 100

CKEDITOR_5_CONFIGS = {
    'default': {
        'toolbar': ['bold', 'italic', 'underline', 'link', 'bulletedList', 'numberedList', 'removeFormat', 'sourceEditing'],
        'height': 600,
        'width': '100%',
    },
}