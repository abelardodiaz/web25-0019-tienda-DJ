# file: dashboard/urls.py
from django.urls import path
from . import views
app_name = 'dashboard'

urlpatterns = [
    path('', views.admin_panel, name='dashboard'),
    path('admin/', views.admin_panel, name='admin_panel'),
    path('admin/users/edit/<int:user_id>/', views.edit_user, name='edit_user'),
    path('admin/users/delete/<int:user_id>/', views.delete_user, name='delete_user'),
    
]
