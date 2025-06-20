# setup/urls.py
from django.urls import path
from . import views
app_name = 'setup'

urlpatterns = [
    path('', views.welcome, name='welcome'),
]
