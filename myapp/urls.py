from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('about', views.about, name='about'),
    path('equipos', views.lista_equipos, name='equipos'),
    path('equipos/ingresar_equipo', views.ingresar_equipo, name = 'ingresar_equipo'),
    path('equipos/<str:equipo>/', views.detalle_equipo, name='detalle_equipo'),
    path('equipos/editar/<int:id_equipo>/', views.editar_equipo, name='editar_equipo'),
    path('equipos/eliminar/<str:nombre>/', views.eliminar_equipo, name='eliminar_equipo'),
    path('jugadores/ingresar_jugador', views.ingresar_jugador, name='ingresar_jugador'),
    path('jugadores/editar/<int:id>/', views.editar_jugador, name='editar_jugador'),
    path('jugadores/eliminar/<str:rut>/', views.eliminar_jugador, name='eliminar_jugador'),
    path('traspasos', views.traspasos, name='traspasos'),
    path('traspasos/<int:id_jugador>/', views.realizar_traspaso, name='realizar_traspaso'),
    path('traspasos/editar/<int:id>/', views.editar_traspaso, name='editar_traspaso'),
    path('traspasos/eliminar/<int:id>/', views.eliminar_traspaso, name='eliminar_traspaso'),
    path('ligas/ajax/crear/',views.crear_liga_ajax, name='crear_liga_ajax')
]