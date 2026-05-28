from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('registro/', views.registro_view, name='registro'),
    path('verificacion-pendiente/', views.verificacion_pendiente, name='verificacion_pendiente'),
    path('logout/', views.logout_view, name='logout'),
    path('perfil/', views.perfil_view, name='perfil'),
    path('activar/<uidb64>/<token>/', views.activar_cuenta, name='activar_cuenta')
]
