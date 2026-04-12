from django.contrib import admin
from .models import Equipo, Jugador, Liga, Traspaso

admin.site.register(Equipo)
admin.site.register(Jugador)
admin.site.register(Liga)
admin.site.register(Traspaso)