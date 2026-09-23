from django.contrib import admin
from .models import Arbitro, Dirigente, Equipo, Jugador, Liga, RedSocial, Traspaso, Prestamo, Cancha, Partido, Torneo


@admin.register(Jugador)
class JugadorAdmin(admin.ModelAdmin):
    search_fields = ['nombre', 'rut']


admin.site.register(Arbitro)
admin.site.register(Dirigente)
admin.site.register(Equipo)
admin.site.register(Liga)
admin.site.register(RedSocial)
admin.site.register(Traspaso)
admin.site.register(Prestamo)
admin.site.register(Cancha)
admin.site.register(Partido)
admin.site.register(Torneo)