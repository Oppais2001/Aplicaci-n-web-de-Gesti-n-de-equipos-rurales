from django.db import models
from django.utils import timezone
from django.conf import settings

class Liga(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    fecha_fundacion = models.DateField(
        null=True,
        blank=True
    )
    logo = models.ImageField(
        upload_to='ligas/logos/',
        null=True,
        blank=True
    )
    comuna = models.CharField(
        max_length=100,
        default="Osorno"
    )
    region = models.CharField(
        max_length=100,
        default="Los Lagos"
    )
    direccion = models.CharField(
        max_length=100,
        null=True,
        blank=True
    )
    presidente = models.CharField(
        max_length=100,
        null=True,
        blank=True
    )
    secretario = models.CharField(
        max_length=100,
        null=True,
        blank=True
    )
    tesorero = models.CharField(
        max_length=100,
        null=True,
        blank=True
    )
    telefono_contacto = models.CharField(
        max_length=20,
        blank=True,
        null=True
    )
    correo_contacto = models.EmailField(
        null=True,
        blank=True
    )
    redes_sociales = models.CharField(max_length=100)
    reglamento = models.TextField(
        null=True,
        blank=True
    )
    
    def __str__(self):
        return self.nombre

class Equipo(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    fecha_creacion = models.DateField(
        null=True,
        blank=True
    )
    nombre_entrenador = models.CharField(max_length=100)
    nombre_dueno = models.CharField(max_length=100)
    liga = models.ForeignKey(Liga, on_delete=models.CASCADE)

    def __str__(self):
        return self.nombre
    
    def cantidad_jugadores(self):
        return self.jugadores.count()

class Jugador(models.Model):
    nombre = models.CharField(max_length=100)
    rut = models.CharField(max_length=12, unique=True)
    fecha_nacimiento = models.DateField(
        null=True,
        blank=True
    )
    telefono = models.CharField(
        max_length=20,
        blank=True,
        null=True
    )
    contacto_emergencia = models.CharField(
        max_length=20,
        blank=True,
        null=True
    )
    equipo = models.ForeignKey(
        "Equipo",
        on_delete=models.CASCADE,
        related_name="jugadores"
    )

    fecha_inscripcion = models.DateField(default=timezone.now)
    
    adulto_responsable = models.CharField(
        max_length=200,
        blank=True,
        null=True
    )  
      
    tipo_sangre = models.CharField(
        max_length=5,
        blank=True,
        null=True
    )
    tiene_seguro = models.BooleanField(default=False)
    alergias = models.TextField(
        blank=True,
        null=True
    )
    certificado_medico = models.FileField(
        upload_to='certificados/',
        blank=True,
        null=True
    )
    activo = models.BooleanField(default=True)
    
    def __str__(self):
        return self.nombre + " / " + self.rut
    
    def rut_formateado(self):
        rut = self.rut

        cuerpo = rut[:-1]
        dv = rut[-1].upper()

        cuerpo_con_puntos = f"{int(cuerpo):,}".replace(",", ".")

        return f"{cuerpo_con_puntos}-{dv}"
class Dirigente(models.Model):

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    equipo = models.ForeignKey(
        "Equipo",
        on_delete=models.CASCADE,
        related_name="dirigentes"
    )

    # Datos básicos
    nombre = models.CharField(max_length=100)

    rut = models.CharField(
        max_length=12,
        unique=True
    )

    telefono = models.CharField(max_length=20)

    correo = models.EmailField(unique=True)

    # Datos del cargo
    cargo = models.CharField(max_length=50)

    direccion = models.CharField(
        max_length=255,
        null=True,
        blank=True
    )

    fecha_asuncion = models.DateField(
        null=True,
        blank=True
    )

    # Estado simple
    activo = models.BooleanField(
        default=True
    )

    def __str__(self):
        return f"{self.nombre} - {self.cargo}"

    def rut_formateado(self):

        rut_limpio = (
            self.rut
            .replace(".", "")
            .replace("-", "")
        )

        cuerpo = rut_limpio[:-1]
        dv = rut_limpio[-1].upper()

        cuerpo_con_puntos = (
            f"{int(cuerpo):,}"
            .replace(",", ".")
        )

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
