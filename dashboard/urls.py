# file: dashboard/urls.py
from django.urls import path
from . import views

from dashboard.buscar_sincronizar import sincronizar_productos, sincronizar_test
from dashboard.admin_gestion import gestion_productos, sincronizar_inventarios, get_sync_progress
from dashboard import admin_editar_detalles


app_name = 'dashboard'

urlpatterns = [
    path('', views.admin_panel, name='dashboard'),
    path('admin/', views.admin_panel, name='admin_panel'),
    path('admin/users/edit/<int:user_id>/', views.edit_user, name='edit_user'),
    path('admin/users/delete/<int:user_id>/', views.delete_user, name='delete_user'),
    path('admin/reset-partial/', views.reset_db_partial, name='reset_partial'),
    path('admin/reset-full/', views.reset_db_full, name='reset_full'),
    path('admin/save-syscom-credentials/', views.save_syscom_credentials, name='save_syscom_credentials'),
    path('admin/renew-syscom-token/', views.renew_syscom_token, name='renew_syscom_token'),
    path('tipo-cambio/', views.tipo_cambio, name='tipo_cambio'),
    path('sincronizar/', sincronizar_productos, name='sincronizar'),
    path('sincronizar-test/', sincronizar_test, name='sincronizar_test'),
    path('gestion/', gestion_productos, name='gestion_productos'),
    path('gestion/editar-productos/<int:product_id>/', admin_editar_detalles.editar_producto, name='editar_producto'),
    path('gestion/sincronizar-inventarios/', sincronizar_inventarios, name='sincronizar_inventarios'),
    path('gestion/sync-progress/', get_sync_progress, name='sync_progress'),
    
]
