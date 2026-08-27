from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.conf import settings
from .utils import DIAS, MESES

class Liga(models.Model):
    nombre = models.CharField(max_length=200, unique=True)
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
        return self.nombre_corto

    @property    
    def nombre_corto(self):
        max_length = 40
        if len(self.nombre) <= max_length:
            return self.nombre

        return self.nombre[:max_length].rstrip() + "..."

class Equipo(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    fecha_creacion = models.DateField(
        null=True,
        blank=True
    )
    logo = models.ImageField(
        upload_to='equipos/logos/',
        null=True,
        blank=True
    )
    nombre_entrenador = models.CharField(
        max_length=100,
        blank=True,
        null=True)
    nombre_dueno = models.CharField(max_length=100, 
        blank=True,
        null=True)
    liga = models.ForeignKey(Liga, on_delete=models.CASCADE)
    redes_sociales = models.CharField(
        max_length=100,
        blank=True,
        default=""
    )

    def __str__(self):
        palabras_repetidas = ['El ','Las ','Club ', 'Deportivo ', ' Serie']
        texto = self.nombre
        for palabra in palabras_repetidas: 
            texto = texto.replace(palabra, "")
        return texto
    
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
    
    @property
    def rut_formateado(self):
        rut = self.rut

        cuerpo = rut[:-1]
        dv = rut[-1].upper()

        cuerpo_con_puntos = f"{int(cuerpo):,}".replace(",", ".")

        return f"{cuerpo_con_puntos}-{dv}"
    
    @property
    def nombre_completo_formato_lista(self):
        nombre_completo = self.nombre.strip()
        nombre_completo = nombre_completo.split()
        return nombre_completo
        
    @property
    def apellido_paterno(self):
        return str(self.nombre_completo_formato_lista[-2])
    
    @property
    def apellido_materno(self):
        return str(self.nombre_completo_formato_lista[-1])
    
    @property 
    def apellidos(self):
        return self.apellido_paterno + " " + self.apellido_materno
        
class Dirigente(models.Model):
    
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="dirigencias"
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
    )

    telefono = models.CharField(max_length=20)

    correo = models.EmailField()

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
        return f"{self.nombre}"

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
        upload_to="canchas/",
        blank=True,
        null=True
    )

    direccion = models.CharField(
        max_length=255,
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

    capacidad_minima = models.PositiveIntegerField(
        "Capacidad mínima de espectadores",
        blank=True,
        null=True
    )

    capacidad_maxima = models.PositiveIntegerField(
        "Capacidad máxima de espectadores",
        blank=True,
        null=True
    )

    largo_metros = models.DecimalField(
        "Largo de la cancha (m)",
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True
    )

    ancho_metros = models.DecimalField(
        "Ancho de la cancha (m)",
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True
    )

    iluminacion = models.BooleanField(
        default=False
    )

    activa = models.BooleanField(
        default=True
    )
    latitud = models.DecimalField(
        "Latitud",
        max_digits=9,
        decimal_places=6,
        blank=True,
        null=True
    )

    longitud = models.DecimalField(
        "Longitud",
        max_digits=9,
        decimal_places=6,
        blank=True,
        null=True
    )

    @property
    def dimensiones(self):
        if self.largo_metros and self.ancho_metros:
            return f"{self.largo_metros} x {self.ancho_metros} m"
        return "No especificadas"
    
    @property
    def coordenadas_google_maps(self):

        if self.latitud is None or self.longitud is None:
            return None

        lat = str(self.latitud).replace(",", ".")
        lng = str(self.longitud).replace(",", ".")

        return f"{lat},{lng}"

    def __str__(self):
        return self.nombre


class Torneo(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    equipos = models.ManyToManyField(
        Equipo,
        related_name="torneos"
    )

    class Meta:
        ordering = ["-fecha_inicio", "nombre"]

    def clean(self):
        if self.fecha_inicio and self.fecha_fin and self.fecha_inicio > self.fecha_fin:
            raise ValidationError("La fecha de inicio no puede ser posterior a la fecha de fin.")

    @property
    def total_equipos(self):
        if not self.pk:
            return 0
        return self.equipos.count()

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

    torneo = models.ForeignKey(
        Torneo,
        on_delete=models.CASCADE,
        related_name="partidos",
        null=True
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

    descripcion = models.TextField(
        blank=True
    )
    
    @property
    def resumen_partido(self):
        if self.esta_jugado:
            return f"{self.equipo_local} {self.goles_local} - {self.goles_visitante} {self.equipo_visitante}"
        return f"{self.equipo_local} vs {self.equipo_visitante}"

    def __str__(self):
        return f"{self.equipo_local} vs {self.equipo_visitante} - {self.fecha.strftime('%d/%m/%Y')} {self.hora.strftime('%H:%M')}"

    @property
    def fecha_hora(self):
        dia = DIAS[self.fecha.weekday()]
        mes = MESES[self.fecha.month]
        return f"{dia} {self.fecha.day:02d} {mes}, {self.hora.strftime('%H:%M')}"
    
    @property
    def fecha_exacta(self):
        dia = DIAS[self.fecha.weekday()]
        mes = MESES[self.fecha.month]
        return f"{dia} {self.fecha.day:02d} {mes}"

    @property
    def esta_jugado(self):
        return self.goles_local is not None and self.goles_visitante is not None

    @property
    def estado(self):
        return "Jugado" if self.esta_jugado else "Programado"
    @property
    def resultado(self):
        return f"{self.goles_local} - {self.goles_visitante}"
    
class TarjetaPartido(models.Model):

    partido = models.ForeignKey(
        Partido,
        on_delete=models.CASCADE,
        related_name="tarjetas"
    )

    equipo = models.ForeignKey(
        Equipo,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="tarjetas_partido"
    )

    jugador = models.ForeignKey(
        Jugador,
        on_delete=models.CASCADE,
        related_name="tarjetas"
    )

    tipo_tarjeta = models.CharField(
        max_length=20,
        choices=[
            ("amarilla", "Amarilla"),
            ("roja", "Roja"),
        ]
    )

    def __str__(self):
        return f"{self.jugador} - {self.tipo_tarjeta}"
class GolPartido(models.Model):
    partido = models.ForeignKey(
        Partido,
        on_delete=models.CASCADE,
        related_name="goles"
    )

    # Equipo al que se le acredita el gol
    equipo = models.ForeignKey(
        Equipo,
        on_delete=models.CASCADE,
        related_name="goles_marcados"
    )

    jugador = models.ForeignKey(
        Jugador,
        on_delete=models.SET_NULL,
        related_name="goles",
        null=True,
        blank=True
    )

    minuto = models.PositiveIntegerField(
        null=True,
        blank=True
    )

    autogol = models.BooleanField(
        default=False
    )

    def __str__(self):
        return f"{self.jugador} - {self.equipo} - {self.partido}"

    def clean(self):
        super().clean()

        if not self.partido_id or not self.equipo_id or not self.jugador_id:
            return

        equipos_partido = {
            self.partido.equipo_local_id,
            self.partido.equipo_visitante_id,
        }

        # El equipo que recibe el gol registrado debe participar
        # en el partido.
        if self.equipo_id not in equipos_partido:
            raise ValidationError(
                "El equipo del gol debe ser uno de los equipos del partido."
            )

        equipos_jugador = self.jugador.equipo_id

        # Si NO es autogol, el jugador debe pertenecer al equipo
        # al que se le acredita el gol.
        if not self.autogol and equipos_jugador != self.equipo_id:
            raise ValidationError(
                "El jugador debe pertenecer al equipo al que se le acredita el gol."
            )

        # Si es autogol, el jugador debe pertenecer al equipo contrario.
        if self.autogol and equipos_jugador == self.equipo_id:
            raise ValidationError(
                "En un autogol, el jugador debe pertenecer al equipo contrario."
            )

        if self.minuto is not None and self.minuto > 150:
            raise ValidationError(
                "El minuto del gol no puede ser superior a 150."
            )