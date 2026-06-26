from django.urls import path
from . import views

from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', views.home, name='home'),
    path('about', views.about, name='about'),
    path('ligas', views.lista_ligas, name='ligas'),
    path('ligas/ingresar_liga', views.ingresar_liga, name='ingresar_liga'),
    path('ligas/editar/<int:id_liga>/', views.editar_liga, name='editar_liga'),
    path('ligas/eliminar/<int:id_liga>/', views.eliminar_liga, name='eliminar_liga'),
    path('ligas/modal_ingresar_liga', views.modal_ingresar_liga, name='modal_ingresar_liga'),
    path('dirigentes', views.lista_dirigentes, name='dirigentes'),
    path('dirigentes/ingresar_dirigente', views.ingresar_dirigente, name='ingresar_dirigente'),
    path('dirigentes/editar/<int:id_dirigente>/', views.editar_dirigente, name='editar_dirigente'),
    path('dirigentes/eliminar/<int:id_dirigente>/', views.eliminar_dirigente, name='eliminar_dirigente'),
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
    path('ligas/ajax/crear/', views.crear_liga_ajax, name='crear_liga_ajax'),
    path('equipos/crear/ajax/', views.ingresar_equipo_ajax, name='crear_equipo_ajax'),
    path('ligas/detalle/<int:id_liga>/',views.detalle_liga,name='detalle_liga'),
    path('arbitros/', views.arbitros, name='arbitros'),
    path('arbitros/crear/', views.ingresar_arbitro, name='ingresar_arbitro'),
    path('arbitros/editar/<int:id>/', views.editar_arbitro, name='editar_arbitro'),
    path('arbitros/eliminar/<int:id>/', views.eliminar_arbitro, name='eliminar_arbitro'),
    path('canchas/',views.lista_canchas,name='canchas'),
    path('canchas/ingresar/',views.ingresar_cancha,name='ingresar_cancha'),
    path('canchas/editar/<int:id_cancha>/',views.editar_cancha,name='editar_cancha'),
    path('canchas/eliminar/<int:id_cancha>/',views.eliminar_cancha,name='eliminar_cancha'),
    path('canchas/<int:id_cancha>/',views.detalle_cancha,name='detalle_cancha'),
    path('partidos', views.lista_partidos, name='partidos'),
    path('partidos/ingresar_partido', views.ingresar_partido, name='ingresar_partido'),
    path('partidos/editar/<int:id>/', views.editar_partido, name='editar_partido'),
    path('partidos/eliminar/<int:id>/', views.eliminar_partido, name='eliminar_partido'),

]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)