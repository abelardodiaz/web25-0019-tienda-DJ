#file: users/urls.py
# urls.py
from .views import CustomPasswordChangeView
from django.urls import path
from . import views


app_name = 'users'


urlpatterns = [
    path('password-change/', CustomPasswordChangeView.as_view(), name='password_change'),
    # Registro & verificación WhatsApp
    path('register/', views.register_choice, name='register_choice'),
    path('register/whatsapp/', views.WhatsAppRegistrationView.as_view(), name='whatsapp_registration'),
    path('register/whatsapp/verify/', views.VerifyWhatsAppCodeView.as_view(), name='verify_whatsapp_code'),
    # Login vía WhatsApp (sin crear duplicados)
    path('login/whatsapp/', views.WhatsAppLoginView.as_view(), name='whatsapp_login'),
]