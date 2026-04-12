from django.db import models
from django.utils import timezone

class Liga(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    
    def __str__(self):
        return self.nombre

class Equipo(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    liga = models.ForeignKey(Liga, on_delete=models.CASCADE)

    def __str__(self):
        return self.nombre


class Jugador(models.Model):
    nombre = models.CharField(max_length=100)
    rut = models.CharField(max_length=12, unique=True)
    equipo = models.ForeignKey(
        "Equipo",
        on_delete=models.CASCADE,
        related_name="jugadores"
    )

    fecha_inscripcion = models.DateField(default=timezone.now)
    
    def __str__(self):
        return self.nombre + " / " + self.rut
    

class Traspaso(models.Model):
    jugador = models.ForeignKey(
        Jugador,
        on_delete=models.CASCADE,
        related_name="traspasos"
    )

    equipo_origen = models.ForeignKey(
        Equipo,
        on_delete=models.CASCADE,
        related_name="traspasos_salida"
    )

    equipo_destino = models.ForeignKey(
        Equipo,
        on_delete=models.CASCADE,
        related_name="traspasos_entrada"
    )

    fecha = models.DateField(default=timezone.now)

    def __str__(self):
        return f"{self.jugador} de {self.equipo_origen} a {self.equipo_destino} ({self.fecha})"