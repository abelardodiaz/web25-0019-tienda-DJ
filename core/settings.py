# file: core/settings.py
"""
Django 5.2.3.
"""
import os
from pathlib import Path
import environ
env = environ.Env()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
environ.Env.read_env(BASE_DIR / '.env')

SECRET_KEY = 'django-insecure-o@5==b%^nw6k9!1i63l1$m0g%__$^zge%$e6(6@-s5j07bzql6'

DEBUG = True
ALLOWED_HOSTS = ['192.168.0.15', 'localhost']

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
    'tema_base_oscuro',
    'setup',
    'dashboard',
    'core',
]

MIDDLEWARE = [
    'core.middleware.FirstRunMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'core.middleware.RoleMiddleware',
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
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': env('DB_NAME'),
        'USER': env('DB_USER'),
        'PASSWORD': env('DB_PASSWORD'),
        'HOST': env('DB_HOST'),
        'PORT': '3306',
        'OPTIONS': {'charset': 'utf8mb4'},
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

    