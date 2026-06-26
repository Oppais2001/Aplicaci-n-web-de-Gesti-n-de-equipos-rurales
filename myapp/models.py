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
    redes_sociales = models.CharField(
        max_length=100,
        blank=True,
        default=""
    )
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
    redes_sociales = models.CharField(
        max_length=100,
        blank=True,
        default=""
    )

    def __str__(self):
        return self.nombre
    
    def cantidad_jugadores(self):
        return self.jugadores.count()


class RedSocial(models.Model):
    INSTAGRAM = "instagram"
    FACEBOOK = "facebook"
    TIKTOK = "tiktok"
    X = "x"
    YOUTUBE = "youtube"
    WHATSAPP = "whatsapp"
    THREADS = "threads"
    LINKEDIN = "linkedin"
    TWITCH = "twitch"
    DISCORD = "discord"
    TELEGRAM = "telegram"
    SNAPCHAT = "snapchat"
    PINTEREST = "pinterest"
    SITIO_WEB = "sitio_web"
    OTRO = "otro"

    TIPO_CHOICES = [
        (INSTAGRAM, "Instagram"),
        (FACEBOOK, "Facebook"),
        (TIKTOK, "TikTok"),
        (X, "X / Twitter"),
        (YOUTUBE, "YouTube"),
        (WHATSAPP, "WhatsApp"),
        (THREADS, "Threads"),
        (LINKEDIN, "LinkedIn"),
        (TWITCH, "Twitch"),
        (DISCORD, "Discord"),
        (TELEGRAM, "Telegram"),
        (SNAPCHAT, "Snapchat"),
        (PINTEREST, "Pinterest"),
        (SITIO_WEB, "Sitio web"),
        (OTRO, "Otro"),
    ]

    equipo = models.ForeignKey(
        "Equipo",
        on_delete=models.CASCADE,
        related_name="redes",
        null=True,
        blank=True
    )
    liga = models.ForeignKey(
        "Liga",
        on_delete=models.CASCADE,
        related_name="redes",
        null=True,
        blank=True
    )
    tipo = models.CharField(
        max_length=30,
        choices=TIPO_CHOICES
    )
    enlace = models.CharField(max_length=255)

    class Meta:
        verbose_name = "Red social"
        verbose_name_plural = "Redes sociales"
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(equipo__isnull=False, liga__isnull=True)
                    | models.Q(equipo__isnull=True, liga__isnull=False)
                ),
                name="red_social_tiene_un_propietario"
            ),
            models.UniqueConstraint(
                fields=["equipo", "tipo", "enlace"],
                name="red_social_unica_por_equipo"
            ),
            models.UniqueConstraint(
                fields=["liga", "tipo", "enlace"],
                name="red_social_unica_por_liga"
            ),
        ]

    def __str__(self):
        propietario = self.equipo or self.liga
        return f"{self.get_tipo_display()} - {propietario}"

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

class Arbitro(models.Model):
    CATEGORIAS_CHOICES = [
        ('Amateur', 'Amateur'),
        ('Juvenil', 'Juvenil'),
        ('Regional', 'Regional'),
        ('Profesional', 'Profesional'),
    ]

    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    rut = models.CharField(max_length=12, unique=True)
    fecha_nacimiento = models.DateField()
    telefono = models.CharField(max_length=20)
    contacto_emergencia = models.CharField(
        max_length=20,
        blank=True,
        null=True
    )
    correo = models.EmailField()
    direccion = models.CharField(max_length=200, blank=True, null=True)
    categoria = models.CharField(max_length=20, choices=CATEGORIAS_CHOICES, default='Amateur')
    experiencia = models.IntegerField(default=0)
    estado = models.BooleanField(default=True)
    fecha_registro = models.DateField(default=timezone.now)
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
        upload_to='certificados_arbitros/',
        blank=True,
        null=True
    )

    def __str__(self):
        return f"{self.nombre} {self.apellido}"

    def partidos_arbitrados(self):
        return self.partidos.count()
    
    def rut_formateado(self):
        rut = self.rut

        cuerpo = rut[:-1]
        dv = rut[-1].upper()

        cuerpo_con_puntos = f"{int(cuerpo):,}".replace(",", ".")

        return f"{cuerpo_con_puntos}-{dv}"

class Cancha(models.Model):

    TIPOS_SUPERFICIE = [
        ("NATURAL", "Pasto Natural"),
        ("SINTETICA", "Pasto Sintético"),
        ("TIERRA", "Tierra"),
    ]

    nombre = models.CharField(
        max_length=100
    )

    liga = models.ForeignKey(
        Liga,
        on_delete=models.CASCADE,
        related_name="canchas"
    )

    foto = models.ImageField(
        upload_to='canchas/',
        blank=True,
        null=True
    )

    direccion = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )
    mapa_iframe = models.TextField(
        "Código HTML del mapa",
        blank=True,
        null=True
    )
    descripcion = models.TextField(
        blank=True,
        null=True
    )

    tipo_superficie = models.CharField(
        max_length=20,
        choices=TIPOS_SUPERFICIE,
        default="NATURAL"
    )

    capacidad = models.PositiveIntegerField(
        blank=True,
        null=True
    )

    iluminacion = models.BooleanField(
        default=False
    )

    activa = models.BooleanField(
        default=True
    )

    def __str__(self):
        return self.nombre

class Partido(models.Model):
    MIN_ANIO_PARTIDO = 1900
    MAX_GOLES_POR_EQUIPO = 99
    MAX_AMARILLAS_POR_EQUIPO = 20
    MAX_ROJAS_POR_EQUIPO = 5

    equipo_local = models.ForeignKey(
        Equipo,
        on_delete=models.CASCADE,
        related_name="partidos_local"
    )
    equipo_visitante = models.ForeignKey(
        Equipo,
        on_delete=models.CASCADE,
        related_name="partidos_visitante"
    )
    cancha = models.ForeignKey(
        "Cancha",
        on_delete=models.SET_NULL,
        null=True,
        related_name="partidos"
    )
    fecha = models.DateField()
    hora = models.TimeField()
    goles_local = models.PositiveIntegerField(
        null=True,
        blank=True
    )
    goles_visitante = models.PositiveIntegerField(
        null=True,
        blank=True
    )
    descripcion = models.TextField(blank=True)
    amarillas_local = models.PositiveIntegerField(default=0)
    amarillas_visitante = models.PositiveIntegerField(default=0)
    rojas_local = models.PositiveIntegerField(default=0)
    rojas_visitante = models.PositiveIntegerField(default=0)

    



