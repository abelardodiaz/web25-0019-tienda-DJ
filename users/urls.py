#file: users/urls.py
# urls.py
from .views import CustomPasswordChangeView
from django.urls import path
from . import views


app_name = 'users'


urlpatterns = [
    path('password-change/', CustomPasswordChangeView.as_view(), name='password_change'),

]