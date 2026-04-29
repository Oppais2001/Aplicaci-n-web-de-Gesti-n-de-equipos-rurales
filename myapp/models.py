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
    
    def rut_formateado(self):
        rut = self.rut

        cuerpo = rut[:-1]
        dv = rut[-1].upper()

        cuerpo_con_puntos = f"{int(cuerpo):,}".replace(",", ".")

        return f"{cuerpo_con_puntos}-{dv}"
    

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

    fecha_inscripcion_anterior = models.DateField()
    fecha_inscripcion_actual = models.DateField(default=timezone.now)


    def __str__(self):
        return f"{self.jugador} de {self.equipo_origen} inscrito en el día ({self.fecha_inscripcion_anterior}) se traspasa a {self.equipo_destino} con fecha ({self.fecha_inscripcion_actual})"