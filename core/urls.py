
"""
URL configuration for core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
#file: core/urls.py
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.views.generic import TemplateView
from django.contrib.auth.views import LogoutView, LoginView
from django.contrib.auth.decorators import login_required
from .views import CustomPasswordChangeView
from django.views import View
from django.shortcuts import redirect
from django.http import HttpResponseRedirect
from django.contrib.auth import authenticate, login as auth_login
from django.urls import path
from . import views
from catalogo import views as catalogo_views
from catalogo.views import instant_search

class CustomLogoutView(View):
    def get(self, request):
        # Borrar sesión manualmente
        request.session.flush()  # <-- ¡Destruye toda la sesión!
        return redirect('/')  # Redirige a home

LOGIN_URL = 'login'  # Nombre de tu URL de login
LOGIN_REDIRECT_URL = '/dashboard/'  # URL a redirigir después de login
LOGOUT_REDIRECT_URL = '/'  # URL a redirigir después de logout 

# Add this custom LoginView
class CustomLoginView(LoginView):
    def form_valid(self, form):
        """Security check complete. Log the user in and redirect."""
        auth_login(self.request, form.get_user())
        next_url = self.request.POST.get('next', self.get_success_url())
        return HttpResponseRedirect(next_url)
    
urlpatterns = [
    path('admin/', admin.site.urls),
   
    path('login/', CustomLoginView.as_view(
        template_name='users/login.html',
        redirect_authenticated_user=True,
        extra_context={'next': '/dashboard/'}
    ), name='login'),

 
    path('logout/', LogoutView.as_view(next_page='/'), name='logout'),


    path('account/profile/', login_required(TemplateView.as_view(template_name='users/profile.html')), name='profile'),
    
    path('setup/', include('setup.urls', namespace='setup')),
    path('dashboard/', include('dashboard.urls', namespace='dashboard')),
    path('password-change/', CustomPasswordChangeView.as_view(), name='password_change'),
    path('users/', include('users.urls', namespace='users')),
    
    # Endpoints necesarios para django_ckeditor_5 (subida/browse de archivos)
    path('ckeditor5/', include('django_ckeditor_5.urls')),
    
    path('producto/<slug:slug>/', catalogo_views.detalle_producto, name='detalle_producto'),
    path('add-to-cart/<slug:slug>/', catalogo_views.add_to_cart, name='add_to_cart'),
    path('update-cart/', catalogo_views.update_cart, name='update_cart'),
    path('canasta/', catalogo_views.cart_view, name='canasta'),
    
    path('', catalogo_views.catalogo_publico, name='home'),
    path('catalogo/', catalogo_views.catalogo_publico, name='catalogo'),
    path('agente/', catalogo_views.agente_chat, name='agente_chat'),
    path('instant-search/', instant_search, name='instant_search'),
]