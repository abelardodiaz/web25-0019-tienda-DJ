#file: core/urls.py
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


from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.views.generic import TemplateView
from django.contrib.auth.views import LogoutView
from django.contrib.auth.decorators import login_required
from .views import CustomPasswordChangeView


urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', auth_views.LoginView.as_view(
        template_name='users/login.html',
        redirect_authenticated_user=True
    ), name='login'),
    # path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    # Custom logout view to redirect to home page
    # This is the preferred way to handle logout in Django 5.2.3
    # It uses the built-in LogoutView with a next_page parameter
    # to redirect users after logging out.
    # The next_page parameter is set to '/' to redirect to the home page.
    # This allows for a cleaner logout process without needing to create a custom view.
    # The template for the logout view is not specified here, as it is not needed.
    # If you want to customize the logout template, you can create a template named 'users/logout.html'
    # and specify it in the LogoutView.as_view() method.    
    path('logout/', LogoutView.as_view(next_page='/'), name='logout'),
    #path('account/profile/', TemplateView.as_view(template_name='users/profile.html'), name='profile'),
    # Using login_required to protect the profile view
    # This ensures that only authenticated users can access the profile page.
    #  login_required is a decorator that checks if the user is authenticated.
    #   If the user is not authenticated, they will be redirected to the login page.
    #   # The profile view is rendered using a TemplateView with the specified template.

    path('account/profile/', login_required(TemplateView.as_view(template_name='users/profile.html')), name='profile'),
    path('', TemplateView.as_view(template_name='index.html'), name='home'),
    path('setup/', include('setup.urls', namespace='setup')),
    path('dashboard/', include('dashboard.urls', namespace='dashboard')),
    path('password-change/', CustomPasswordChangeView.as_view(), name='password_change'),
    path('users/', include('users.urls', namespace='users')),
    
]