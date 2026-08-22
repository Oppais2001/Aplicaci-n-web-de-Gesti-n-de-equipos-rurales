import os
import re
from datetime import date, datetime
import requests

import logging
logger = logging.getLogger(__name__)

from dateutil.relativedelta import relativedelta
from django.core.exceptions import ValidationError
from django.core.validators import validate_email as django_validate_email
from decimal import Decimal, InvalidOperation

from io import BytesIO

from django.http import HttpResponse
from PIL import Image, ImageDraw, ImageFont, ImageOps

from django.conf import settings
from django.contrib.staticfiles import finders

from reportlab.lib.utils import ImageReader
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer,
    Image as ReportLabImage,
)
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics

LETTERS = "A-Za-zÁÉÍÓÚáéíóúÑñÜü"

DIAS = {0: 'Lun', 1: 'Mar', 2: 'Mié', 3: 'Jue', 4: 'Vie', 5: 'Sáb', 6: 'Dom'}
MESES = {1: 'Ene', 2: 'Feb', 3: 'Mar', 4: 'Abr', 5: 'May', 6: 'Jun',
         7: 'Jul', 8: 'Ago', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dic'}


def normalize_spaces(value):
    return " ".join(str(value or "").strip().split())


def _meaningful_text(value):
    return re.sub(r"[\s\-\.\,\_\/\:\@\#]+", "", value.lower())


def _has_letters(value):
    return re.search(rf"[{LETTERS}]", value) is not None


def validate_text(
    value,
    field_name,
    min_length=3,
    max_length=100,
    required=True,
    allow_numbers=True,
    allowed_symbols=r"\-\.\,",
    title_case=True,
):
    value = normalize_spaces(value)

    if not value:
        if required:
            raise ValidationError(f"Debes ingresar {field_name}.")
        return ""

    if len(value) < min_length:
        raise ValidationError(f"{field_name.capitalize()} demasiado corto.")

    if len(value) > max_length:
        raise ValidationError(f"{field_name.capitalize()} demasiado largo.")

    numbers = "0-9" if allow_numbers else ""
    pattern = rf"^[{LETTERS}{numbers}\s{allowed_symbols}]+$"
    if not re.fullmatch(pattern, value):
        raise ValidationError(f"{field_name.capitalize()} contiene caracteres invalidos.")

    if not _has_letters(value):
        raise ValidationError(f"{field_name.capitalize()} debe contener letras.")

    cleaned = _meaningful_text(value)
    if cleaned and len(set(cleaned)) == 1:
        raise ValidationError(f"Ingresa {field_name} valido.")

    return value.title() if title_case else value


def validate_person_name(value, field_name="un nombre", required=True, min_length=3, max_length=100):
    return validate_text(
        value,
        field_name,
        min_length=min_length,
        max_length=max_length,
        required=required,
        allow_numbers=False,
        allowed_symbols=r"\-",
    )

def validate_league_name(
    value,
    field_name="el nombre de la liga",
    required=True,
    min_length=3,
    max_length=200,
):
    value = normalize_spaces(value)

    if not value:
        if required:
            raise ValidationError(f"Debes ingresar {field_name}.")
        return ""

    if len(value) < min_length:
        raise ValidationError(
            f"{field_name.capitalize()} demasiado corto."
        )

    if len(value) > max_length:
        raise ValidationError(
            f"{field_name.capitalize()} demasiado largo."
        )

    # Letras, números, espacios, guiones y comas
    pattern = rf"^[{LETTERS}0-9\s\-,]+$"

    if not re.fullmatch(pattern, value):
        raise ValidationError(
            f"{field_name.capitalize()} contiene caracteres invalidos."
        )

    if not _has_letters(value):
        raise ValidationError(
            f"{field_name.capitalize()} debe contener letras."
        )

    cleaned = _meaningful_text(value)

    if cleaned and len(set(cleaned)) == 1:
        raise ValidationError(
            f"Ingresa {field_name} valido."
        )

    return value.title()

def validate_entity_name(value, field_name, required=True, min_length=3, max_length=100):
    return validate_text(
        value,
        field_name,
        min_length=min_length,
        max_length=max_length,
        required=required,
        allow_numbers=True,
        allowed_symbols=r"\-",
    )


def validate_address(value, field_name="la direccion", required=False, min_length=5, max_length=255):
    return validate_text(
        value,
        field_name,
        min_length=min_length,
        max_length=max_length,
        required=required,
        allow_numbers=True,
        allowed_symbols=r"\-\.\,\/\#°º",
    )


def validate_social_media(value, required=True):
    value = normalize_spaces(value)

    if not value:
        if required:
            raise ValidationError("Debes ingresar redes sociales.")
        return ""

    if len(value) < 3:
        raise ValidationError("Redes sociales demasiado corto.")

    if len(value) > 100:
        raise ValidationError("Redes sociales demasiado largo.")

    pattern = rf"^[{LETTERS}0-9\s\.\-\_\@\:\#/]+$"
    if not re.fullmatch(pattern, value):
        raise ValidationError(
            "Redes sociales solo puede contener letras, numeros, @, puntos, guiones o enlaces simples."
        )

    if not re.search(rf"[{LETTERS}0-9]", value):
        raise ValidationError("Redes sociales no es valido.")

    return value


def validate_social_link(value, required=True):
    value = normalize_spaces(value)

    if not value:
        if required:
            raise ValidationError("Debes ingresar el enlace o usuario de la red social.")
        return ""

    if len(value) < 3:
        raise ValidationError("La red social es demasiado corta.")

    if len(value) > 255:
        raise ValidationError("La red social es demasiado larga.")

    pattern = rf"^[{LETTERS}0-9\s\.\-\_\@\:\#\/\?\=\&]+$"
    if not re.fullmatch(pattern, value):
        raise ValidationError(
            "La red social contiene caracteres invalidos."
        )

    if not re.search(rf"[{LETTERS}0-9]", value):
        raise ValidationError("La red social no es valida.")

    return value


def validate_unique_value(
    model,
    field,
    value,
    instance=None,
    filters=None,
    message="Este valor ya existe.",
    iexact=False,
):
    if value is None:
        return value

    lookup = f"{field}__iexact" if iexact else field
    queryset = model.objects.filter(**{lookup: value})

    if filters:
        queryset = queryset.filter(**filters)

    if instance and instance.pk:
        queryset = queryset.exclude(pk=instance.pk)

    if queryset.exists():
        raise ValidationError(message)

    return value


def validate_rut(value, model=None, instance=None, duplicate_message=None):
    rut = str(value or "").strip().replace(".", "").replace("-", "").lower()

    if len(rut) < 2:
        raise ValidationError("RUT invalido.")

    cuerpo = rut[:-1]
    dv = rut[-1]

    if not cuerpo.isdigit() or dv not in "0123456789k":
        raise ValidationError("RUT invalido.")

    if len(cuerpo) < 7 or len(cuerpo) > 8:
        raise ValidationError("RUT invalido.")

    if len(set(cuerpo)) == 1:
        raise ValidationError("Ingresa un RUT valido.")

    suma = 0
    multiplo = 2
    for digit in reversed(cuerpo):
        suma += int(digit) * multiplo
        multiplo = 2 if multiplo == 7 else multiplo + 1

    resultado = 11 - (suma % 11)
    dv_calculado = "0" if resultado == 11 else "k" if resultado == 10 else str(resultado)

    if dv != dv_calculado:
        raise ValidationError("RUT invalido.")

    if model:
        validate_unique_value(
            model,
            "rut",
            rut,
            instance=instance,
            message=duplicate_message,
        )

    return rut


def validate_phone(value, required=True, field_name="telefono"):
    phone = str(value or "").strip()

    if not phone:
        if required:
            raise ValidationError(f"Debes ingresar un {field_name}.")
        return ""

    cleaned = re.sub(r"[\s\-\+\(\)]", "", phone)

    if not cleaned.isdigit():
        raise ValidationError("El telefono solo puede contener numeros.")

    if len(cleaned) < 8:
        raise ValidationError("El telefono es demasiado corto.")

    if len(cleaned) > 15:
        raise ValidationError("El telefono es demasiado largo.")

    return cleaned


def validate_email(value, required=True, max_length=100):
    email = str(value or "").strip().lower().replace(" ", "")

    if not email:
        if required:
            raise ValidationError("Debes ingresar un correo.")
        return ""

    if len(email) > max_length:
        raise ValidationError("El correo es demasiado largo.")

    try:
        django_validate_email(email)
    except ValidationError:
        raise ValidationError("El formato del correo no es valido.")

    return email


def calculate_age(birth_date, today=None):
    if not birth_date:
        return None
    return relativedelta(today or date.today(), birth_date).years


def validate_date_not_future(
    value,
    field_name="La fecha",
    required=True,
    max_age_years=None,
):
    if not value:
        if required:
            raise ValidationError(f"{field_name} es obligatoria.")
        return value

    today = date.today()

    if value > today:
        raise ValidationError("No puedes ingresar una fecha futura.")

    if max_age_years and value < today - relativedelta(years=max_age_years):
        raise ValidationError("La fecha es demasiado antigua.")

    return value


def validate_birth_date(value, min_age=5, max_age=100, required=False):
    if not value:
        if required:
            raise ValidationError("Debes ingresar una fecha de nacimiento.")
        return value

    validate_date_not_future(value, "La fecha de nacimiento", required=True)
    age = calculate_age(value)

    if age is None or age <= 0:
        raise ValidationError("La persona no ha nacido.")

    if age < min_age:
        raise ValidationError("La persona es demasiado joven.")

    if age > max_age:
        raise ValidationError("Edad invalida.")

    return value


def validate_blood_type(value, required=False):
    blood_type = str(value or "").upper().strip()

    if not blood_type:
        if required:
            raise ValidationError("Debes ingresar un tipo de sangre.")
        return ""

    valid_types = {"A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"}
    if blood_type not in valid_types:
        raise ValidationError("Tipo de sangre invalido.")

    return blood_type


def validate_textarea(value, field_name, required=False, max_length=500):
    value = str(value or "").strip()

    if not value:
        if required:
            raise ValidationError(f"Debes ingresar {field_name}.")
        return ""

    if len(value) > max_length:
        raise ValidationError(f"{field_name.capitalize()} demasiado largo.")

    return value


def validate_file_upload(value, allowed_extensions, max_size_mb=5, field_name="El archivo"):
    if not value:
        return value

    extension = os.path.splitext(value.name)[1].lower().lstrip(".")
    allowed = {ext.lower().lstrip(".") for ext in allowed_extensions}

    if extension not in allowed:
        raise ValidationError(f"{field_name} tiene un formato no permitido.")

    if value.size > max_size_mb * 1024 * 1024:
        raise ValidationError(f"{field_name} no puede superar {max_size_mb}MB.")

    return value


def validate_transfer_date(value, base_date):
    validate_date_not_future(value, "La fecha de traspaso", required=True)

    min_date = base_date + relativedelta(years=1, months=6)
    if value < min_date:
        raise ValidationError(f"El jugador no puede transferirse antes de {min_date}.")

    return value
def validate_integer_range(
    value,
    field_name,
    minimum=None,
    maximum=None,
    required=False,
):
    if value is None:
        if required:
            raise ValidationError(f"Debes ingresar {field_name}.")
        return value

    if minimum is not None and value < minimum:
        raise ValidationError(
            f"{field_name.capitalize()} no puede ser menor que {minimum}."
        )

    if maximum is not None and value > maximum:
        raise ValidationError(
            f"{field_name.capitalize()} no puede ser mayor que {maximum}."
        )

    return value

def validate_decimal_range(
    value,
    field_name,
    minimum=None,
    maximum=None,
    required=True,
):
    """
    Valida un número decimal dentro de un rango permitido.
    """

    if value in (None, ""):
        if required:
            raise ValidationError(
                f"Debe ingresar {field_name}."
            )
        return None

    try:
        value = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise ValidationError(
            f"{field_name.capitalize()} debe ser un número válido."
        )

    if minimum is not None and value < Decimal(str(minimum)):
        raise ValidationError(
            f"{field_name.capitalize()} debe ser mayor o igual a {minimum}."
        )

    if maximum is not None and value > Decimal(str(maximum)):
        raise ValidationError(
            f"{field_name.capitalize()} debe ser menor o igual a {maximum}."
        )

    return value

# Creador de imagenes de la tabla de posiciones
ANCHO = 900
ruta_titulo = finders.find("fonts/Cinzel-Regular.ttf")
ruta_titulo_negrita = finders.find("fonts/Cinzel-Bold.ttf")
ruta_subtitulo = finders.find("fonts/Lato-Bold.ttf")
ruta_normal = finders.find("fonts/Lato-Regular.ttf")
ruta_normal_negrita = finders.find("fonts/Lato-Bold.ttf")

def crear_img_tabla(torneo, tabla_posiciones):
    # ---------- Constantes de layout ----------
    ALTO_FILA = 48
    ALTO_INICIO = 230
    ALTO_HEADER_BANNER = 150
    PADDING_X = 40
    ANCHO_TABLA = 860

    COL_POS = 40
    COL_CLUB = 110
    COL_PJ = 560
    COL_DG = 660
    COL_PTS = 770
    ANCHO_COL_CLUB = COL_PJ - COL_CLUB - 20  # margen para truncar nombre

    COLOR_FONDO = "#202020"
    COLOR_FONDO_HEADER = "#161616"
    COLOR_FILA_PAR = "#262626"
    COLOR_FILA_IMPAR = "#202020"
    COLOR_ORO = "gold"
    COLOR_TEXTO = "whitesmoke"
    COLOR_TENUE = "#999"
    COLOR_BORDE = "#444"

    COLOR_PODIO = {
        1: "#ffd700",  # oro
        2: "#c0c0c0",  # plata
        3: "#cd7f32",  # bronce
    }

    ALTO = ALTO_INICIO + (len(tabla_posiciones) * ALTO_FILA) + 40

    imagen = Image.new("RGB", (ANCHO, ALTO), COLOR_FONDO)
    draw = ImageDraw.Draw(imagen)

    fuente_titulo = ImageFont.truetype(ruta_titulo, 38)
    fuente_subtitulo = ImageFont.truetype(ruta_normal, 22)
    fuente_header = ImageFont.truetype(ruta_normal, 18)

    cantidad_equipos = len(tabla_posiciones)
    if cantidad_equipos <= 12:
        fuente_normal = ImageFont.truetype(ruta_normal, 22)
    elif cantidad_equipos <= 20:
        fuente_normal = ImageFont.truetype(ruta_normal, 19)
    else:
        fuente_normal = ImageFont.truetype(ruta_normal, 16)

    # ---------- Banner superior ----------
    draw.rectangle(
        (0, 0, ANCHO, ALTO_HEADER_BANNER),
        fill=COLOR_FONDO_HEADER
    )

    draw.text((PADDING_X, 35), "Liga Rural", fill=COLOR_ORO, font=fuente_titulo)
    draw.text((PADDING_X, 85), torneo.nombre, fill=COLOR_TEXTO, font=fuente_subtitulo)

    draw.line(
        (PADDING_X, ALTO_HEADER_BANNER, ANCHO - PADDING_X, ALTO_HEADER_BANNER),
        fill=COLOR_ORO,
        width=3
    )

    # ---------- Encabezado de columnas ----------
    y_header = ALTO_HEADER_BANNER + 25
    draw.text((COL_POS, y_header), "POS", fill=COLOR_ORO, font=fuente_header)
    draw.text((COL_CLUB, y_header), "CLUB", fill=COLOR_ORO, font=fuente_header)
    draw.text((COL_PJ, y_header), "PJ", fill=COLOR_ORO, font=fuente_header)
    draw.text((COL_DG, y_header), "DG", fill=COLOR_ORO, font=fuente_header)
    draw.text((COL_PTS, y_header), "PTS", fill=COLOR_ORO, font=fuente_header)

    draw.line(
        (PADDING_X, y_header + 30, ANCHO - PADDING_X, y_header + 30),
        fill=COLOR_BORDE,
        width=1
    )

    # ---------- Filas ----------
    y = ALTO_INICIO

    for posicion, fila in enumerate(tabla_posiciones, start=1):

        # Franja de fondo alternada
        color_fila = COLOR_FILA_PAR if posicion % 2 == 0 else COLOR_FILA_IMPAR
        draw.rectangle(
            (PADDING_X - 10, y - 8, ANCHO - PADDING_X + 10, y + ALTO_FILA - 12),
            fill=color_fila
        )

        # Barra de color para el podio (1°, 2°, 3°)
        if posicion in COLOR_PODIO:
            draw.rectangle(
                (PADDING_X - 10, y - 8, PADDING_X - 4, y + ALTO_FILA - 12),
                fill=COLOR_PODIO[posicion]
            )

        color_posicion = COLOR_PODIO.get(posicion, COLOR_TEXTO)

        draw.text((COL_POS, y), str(posicion), fill=color_posicion, font=fuente_normal)

        nombre_club = _texto_ajustado(draw, fila["equipo"].nombre, fuente_normal, ANCHO_COL_CLUB)
        draw.text((COL_CLUB, y), nombre_club, fill=COLOR_TEXTO, font=fuente_normal)

        draw.text((COL_PJ, y), str(fila["pj"]), fill=COLOR_TENUE, font=fuente_normal)
        draw.text((COL_DG, y), str(fila["dg"]), fill=COLOR_TENUE, font=fuente_normal)
        draw.text((COL_PTS, y), str(fila["pts"]), fill=COLOR_ORO, font=fuente_normal)

        y += ALTO_FILA

    # ---------- Pie de página ----------
    fuente_footer = ImageFont.truetype(ruta_normal, 13)
    fecha_generado = datetime.now().strftime("%d-%m-%Y %H:%M")
    draw.text(
        (PADDING_X, ALTO - 30),
        f"Generado el {fecha_generado} · Liga Rural",
        fill=COLOR_TENUE,
        font=fuente_footer
    )

    buffer = BytesIO()
    imagen.save(buffer, format="PNG")
    buffer.seek(0)

    response = HttpResponse(buffer, content_type="image/png")
    response["Content-Disposition"] = 'attachment; filename="tabla.png"'

    return response

def _formatear_fecha_hora(valor, formato_salida="%A %d de %B %Y", solo_hora=False):
    """
    Acepta un datetime real o un string, y devuelve el texto formateado.
    Si es string y no se puede parsear, lo devuelve tal cual (sin romper).
    """
    dt = valor

    if isinstance(valor, str):
        formatos_posibles = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%d/%m/%Y %H:%M",
            "%d-%m-%Y %H:%M",
        ]
        dt = None
        for formato in formatos_posibles:
            try:
                dt = datetime.strptime(valor, formato)
                break
            except ValueError:
                continue

    if dt is None or not hasattr(dt, "strftime"):
        # No se pudo interpretar como fecha: devolvemos el string tal cual
        return valor.upper() if isinstance(valor, str) else str(valor)

    if solo_hora:
        return dt.strftime("%H:%M HORAS")

    return dt.strftime(formato_salida).upper()

def _texto_ajustado(draw, texto, fuente, ancho_maximo):
    texto = str(texto or "-")

    if draw.textlength(texto, font=fuente) <= ancho_maximo:
        return texto

    while texto and draw.textlength(f"{texto}...", font=fuente) > ancho_maximo:
        texto = texto[:-1]

    return f"{texto}..." if texto else "-"

def _cargar_logo_circular(url, size, cache=None):
    """
    Descarga un logo desde una URL (Cloudinary u otra), lo recorta
    en círculo y lo devuelve como imagen RGBA lista para pegar.
    Devuelve None si falla la descarga o no hay URL.
    """
    if not url:
        return None

    if cache is not None and url in cache:
        return cache[url]

    try:
        respuesta = requests.get(url, timeout=5)
        respuesta.raise_for_status()

        logo = Image.open(BytesIO(respuesta.content)).convert("RGBA")
        logo = ImageOps.fit(logo, (size, size), Image.LANCZOS)

        mascara = Image.new("L", (size, size), 0)
        ImageDraw.Draw(mascara).ellipse((0, 0, size, size), fill=255)

        logo_circular = Image.new("RGBA", (size, size))
        logo_circular.paste(logo, (0, 0), mascara)

    except Exception as error:
        print(f"No se pudo cargar el logo ({url}): {error}")
        return None

    if cache is not None:
        cache[url] = logo_circular

    return logo_circular


def _placeholder_logo(size, letra, color_fondo="#3a3a3a", color_texto="whitesmoke"):
    """Círculo con la inicial del equipo, para cuando no hay logo."""
    placeholder = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(placeholder)
    draw.ellipse((0, 0, size, size), fill=color_fondo)

    fuente = ImageFont.truetype(ruta_normal, int(size * 0.5))
    bbox = draw.textbbox((0, 0), letra, font=fuente)
    ancho_texto = bbox[2] - bbox[0]
    alto_texto = bbox[3] - bbox[1]

    draw.text(
        ((size - ancho_texto) / 2, (size - alto_texto) / 2 - bbox[1]),
        letra,
        fill=color_texto,
        font=fuente
    )
    return placeholder

def _logo_marca_agua(url, size, opacidad=0.15, cache=None):
    """
    Descarga el logo y lo devuelve como imagen RGBA grande,
    con el canal alpha reducido para usarlo como marca de agua de fondo.
    """
    clave_cache = f"{url}_{size}_{opacidad}"
    if cache is not None and clave_cache in cache:
        return cache[clave_cache]

    if not url:
        return None

    try:
        respuesta = requests.get(url, timeout=5)
        respuesta.raise_for_status()

        logo = Image.open(BytesIO(respuesta.content)).convert("RGBA")

        # Escalar manteniendo proporción, ajustado dentro de un cuadrado 'size'
        logo.thumbnail((size, size), Image.LANCZOS)

        # Reducir opacidad multiplicando el canal alpha
        r, g, b, a = logo.split()
        a = a.point(lambda px: int(px * opacidad))
        logo = Image.merge("RGBA", (r, g, b, a))

    except Exception as error:
        print(f"No se pudo cargar la marca de agua ({url}): {error}")
        return None

    if cache is not None:
        cache[clave_cache] = logo

    return logo

def crear_img_fechas(torneo, partidos, liga):
    # ---------- Constantes de layout ----------
    PADDING_X = 40
    ALTO_HEADER = 200
    ALTO_BANNER_FECHA = 70
    ALTO_TARJETA = 130
    ESPACIO_ENTRE_TARJETAS = 20
    LOGO_LIGA_SIZE = 110
    LOGO_EQUIPO_SIZE = 90

    COLOR_FONDO = "#202020"
    COLOR_FONDO_HEADER = "#161616"
    COLOR_ORO = "#d4af37"
    COLOR_CAFE = "#5a3a1a"
    COLOR_TEXTO = "whitesmoke"
    COLOR_TENUE = "#999"
    COLOR_TARJETA_FONDO = "#2a2a2a"
    COLOR_BORDE = "#444"

    partidos_programados = [p for p in partidos if p.estado == 'Programado']

    # ---------- Cálculo correcto de altura ----------
    y_inicial_partidos = (
        ALTO_HEADER
        + 20                    # separación antes del banner
        + ALTO_BANNER_FECHA
        + 40                    # separación después del banner
    )

    # Cada partido utiliza:
    # 30  -> separación antes de la tarjeta
    # 130 -> altura de tarjeta
    # 20  -> espacio entre tarjetas
    # 25  -> espacio adicional al actualizar y
    ALTO_POR_PARTIDO = (
        30
        + ALTO_TARJETA
        + ESPACIO_ENTRE_TARJETAS
        + 25
    )

    alto = (
        y_inicial_partidos
        + len(partidos_programados) * ALTO_POR_PARTIDO
        + 80
    )

    alto = max(alto, 500)

    imagen = Image.new("RGB", (ANCHO, alto), COLOR_FONDO)
    draw = ImageDraw.Draw(imagen)

    fuente_titulo = ImageFont.truetype(ruta_titulo_negrita, 36)
    fuente_subtitulo = ImageFont.truetype(ruta_subtitulo, 24)
    fuente_fecha = ImageFont.truetype(ruta_titulo_negrita, 30)
    fuente_hora = ImageFont.truetype(ruta_subtitulo, 20)
    fuente_equipo = ImageFont.truetype(ruta_subtitulo, 24)
    fuente_vs = ImageFont.truetype(ruta_titulo_negrita, 22)
    fuente_footer = ImageFont.truetype(ruta_normal, 18)

    cache_logos = {}

    # ---------- URL del logo de la liga (una sola vez, se reusa abajo) ----------
    logo_liga_url = liga.logo.url if liga.logo else None

    # ---------- Marca de agua: logo de la liga de fondo ----------
    marca_agua = _logo_marca_agua(
        logo_liga_url,
        size=int(min(ANCHO, alto) * 0.75),  # ocupa 75% del lado más chico
        opacidad=0.12,
        cache=cache_logos
    )

    if marca_agua:
        x_wm = (ANCHO - marca_agua.width) // 2
        y_wm = (alto - marca_agua.height) // 2
        imagen.paste(marca_agua, (x_wm, y_wm), marca_agua)

    # ---------- Header con logos de la liga a ambos lados ----------
    draw.rectangle((0, 0, ANCHO, ALTO_HEADER), fill=COLOR_FONDO_HEADER)
    texto_titulo = "UNIÓN COMUNAL DE CLUBES DEPORTIVOS"
    bbox_titulo = draw.textbbox((0, 0), texto_titulo, font=fuente_titulo)
    ancho_titulo = bbox_titulo[2] - bbox_titulo[0]
    x_titulo = (ANCHO - ancho_titulo) // 2

    draw.text((x_titulo, 55), texto_titulo, fill=COLOR_ORO, font=fuente_titulo)

    texto_subtitulo = torneo.nombre.upper()
    bbox_sub = draw.textbbox((0, 0), texto_subtitulo, font=fuente_subtitulo)
    ancho_sub = bbox_sub[2] - bbox_sub[0]
    x_sub = (ANCHO - ancho_sub) // 2
    draw.text((x_sub, 115), texto_subtitulo, fill=COLOR_TEXTO, font=fuente_subtitulo)

    # ---------- Banner de fecha ----------
    y_banner = ALTO_HEADER + 20

    if partidos_programados:
        fecha_texto = _formatear_fecha_hora(partidos_programados[0].fecha_exacta)
    else:
        fecha_texto = torneo.nombre.upper()

    draw.rounded_rectangle(
        (PADDING_X, y_banner, ANCHO - PADDING_X, y_banner + ALTO_BANNER_FECHA),
        radius=14,
        fill=COLOR_CAFE
    )

    bbox_fecha = draw.textbbox((0, 0), fecha_texto, font=fuente_fecha)
    ancho_fecha = bbox_fecha[2] - bbox_fecha[0]
    alto_fecha = bbox_fecha[3] - bbox_fecha[1]
    draw.text(
        ((ANCHO - ancho_fecha) // 2, y_banner + (ALTO_BANNER_FECHA - alto_fecha) // 2 - bbox_fecha[1]),
        fecha_texto,
        fill=COLOR_ORO,
        font=fuente_fecha
    )

    # ---------- Tarjetas de partido ----------
    y = y_banner + ALTO_BANNER_FECHA + 40

    if not partidos_programados:
        draw.text(
            (PADDING_X, y),
            "No hay fechas registradas para este torneo.",
            fill=COLOR_TEXTO,
            font=fuente_equipo
        )
    else:
        for partido in partidos_programados:

            # --- Badge de hora ---
            hora_texto = _formatear_fecha_hora(partido.hora, solo_hora=True)
            bbox_hora = draw.textbbox((0, 0), hora_texto, font=fuente_hora)
            ancho_hora = bbox_hora[2] - bbox_hora[0]

            draw.rounded_rectangle(
                (
                    (ANCHO - ancho_hora) // 2 - 20, y - 18,
                    (ANCHO + ancho_hora) // 2 + 20, y + 18
                ),
                radius=18,
                fill=COLOR_ORO
            )
            draw.text(
                ((ANCHO - ancho_hora) // 2, y - bbox_hora[3] // 2),
                hora_texto,
                fill="#202020",
                font=fuente_hora
            )

            y_tarjeta = y + 30

            # --- Fondo de la tarjeta ---
            draw.rounded_rectangle(
                (PADDING_X, y_tarjeta, ANCHO - PADDING_X, y_tarjeta + ALTO_TARJETA),
                radius=14,
                fill=COLOR_TARJETA_FONDO,
                outline=COLOR_BORDE,
                width=1
            )

            centro_y = y_tarjeta + ALTO_TARJETA // 2

            # --- Logo equipo local (izquierda) ---
            logo_local_url = getattr(partido.equipo_local, "logo", None)
            logo_local_url = logo_local_url.url if logo_local_url else None
            logo_local = _cargar_logo_circular(logo_local_url, LOGO_EQUIPO_SIZE, cache_logos)
            if not logo_local:
                logo_local = _placeholder_logo(LOGO_EQUIPO_SIZE, str(partido.equipo_local)[0].upper())

            x_logo_local = PADDING_X + 25
            imagen.paste(logo_local, (x_logo_local, centro_y - LOGO_EQUIPO_SIZE // 2), logo_local)

            # --- Logo equipo visitante (derecha) ---
            logo_visita_url = getattr(partido.equipo_visitante, "logo", None)
            logo_visita_url = logo_visita_url.url if logo_visita_url else None
            logo_visita = _cargar_logo_circular(logo_visita_url, LOGO_EQUIPO_SIZE, cache_logos)
            if not logo_visita:
                logo_visita = _placeholder_logo(LOGO_EQUIPO_SIZE, str(partido.equipo_visitante)[0].upper())

            x_logo_visita = ANCHO - PADDING_X - 25 - LOGO_EQUIPO_SIZE
            imagen.paste(logo_visita, (x_logo_visita, centro_y - LOGO_EQUIPO_SIZE // 2), logo_visita)

            # --- Badge central "VS" ---
            vs_size = 60
            x_vs = (ANCHO - vs_size) // 2
            draw.ellipse(
                (x_vs, centro_y - vs_size // 2, x_vs + vs_size, centro_y + vs_size // 2),
                fill=COLOR_CAFE
            )
            bbox_vs = draw.textbbox((0, 0), "VS", font=fuente_vs)
            ancho_vs = bbox_vs[2] - bbox_vs[0]
            alto_vs = bbox_vs[3] - bbox_vs[1]

            x_texto_vs = x_vs + (vs_size - ancho_vs) // 2 - bbox_vs[0]
            y_texto_vs = (centro_y - vs_size // 2) + (vs_size - alto_vs) // 2 - bbox_vs[1]

            draw.text(
                (x_texto_vs, y_texto_vs),
                "VS",
                fill=COLOR_ORO,
                font=fuente_vs
            )

            # --- Nombre equipo local ---
            ancho_columna = x_vs - (x_logo_local + LOGO_EQUIPO_SIZE) - 20
            nombre_local = _texto_ajustado(draw, partido.equipo_local, fuente_equipo, ancho_columna)
            bbox_nl = draw.textbbox((0, 0), nombre_local, font=fuente_equipo)
            ancho_nl = bbox_nl[2] - bbox_nl[0]
            x_centro_local = x_logo_local + LOGO_EQUIPO_SIZE + 15 + (ancho_columna - ancho_nl) // 2
            draw.text((x_centro_local, centro_y - 12), nombre_local, fill=COLOR_TEXTO, font=fuente_equipo)

            # --- Nombre equipo visitante ---
            nombre_visita = _texto_ajustado(draw, partido.equipo_visitante, fuente_equipo, ancho_columna)
            bbox_nv = draw.textbbox((0, 0), nombre_visita, font=fuente_equipo)
            ancho_nv = bbox_nv[2] - bbox_nv[0]
            x_centro_visita = (x_vs + vs_size + 15) + (ancho_columna - ancho_nv) // 2
            draw.text((x_centro_visita, centro_y - 12), nombre_visita, fill=COLOR_TEXTO, font=fuente_equipo)

            y = y_tarjeta + ALTO_TARJETA + ESPACIO_ENTRE_TARJETAS + 25

    buffer = BytesIO()
    imagen.save(buffer, format="PNG")
    buffer.seek(0)

    response = HttpResponse(buffer, content_type="image/png")
    response["Content-Disposition"] = 'attachment; filename="fechas.png"'

    return response

def crear_img_partidos(torneo, partidos):
    alto = max(360, 230 + (partidos.count() * 45))
    imagen = Image.new(
        "RGB",
        (ANCHO, alto),
        "#202020"
    )

    draw = ImageDraw.Draw(imagen)

    fuente_titulo = ImageFont.truetype(
        ruta_titulo,
        38
    )

    fuente_normal = ImageFont.truetype(
        ruta_normal,
        22
    )

    fuente_pequena = ImageFont.truetype(
        ruta_normal,
        18
    )

    draw.text(
        (40, 40),
        "Liga Rural",
        fill="gold",
        font=fuente_titulo
    )

    draw.text(
        (40, 90),
        f"Partidos - {torneo.nombre}",
        fill="white",
        font=fuente_normal
    )

    draw.line(
        (40, 140, 860, 140),
        fill="gold",
        width=3
    )

    y = 170

    columnas = [
        ("Resultados", 40, 160),
        ("Cancha", 400, 150),
        ("Fecha y Hora", 650, 90),
    ]

    for titulo, x, _ancho in columnas:
        draw.text((x, y), titulo, fill="gold", font=fuente_pequena)

    y = 210

    if not partidos:
        draw.text(
            (40, y),
            "No hay partidos registrados para este torneo.",
            fill="white",
            font=fuente_normal
        )
    else:
        for partido in partidos:
            print(partido.estado)
            if partido.estado == 'Jugado':
                valores = [
                    (f"{partido.equipo_local} {partido.goles_local} - {partido.goles_visitante} {partido.equipo_visitante}", 40, 260),
                    (partido.cancha or "-", 400, 200),
                    (partido.fecha_hora, 650, 200),
                ]

                for valor, x, ancho in valores:
                    draw.text(
                        (x, y),
                        _texto_ajustado(draw, valor, fuente_pequena, ancho),
                        fill="white",
                        font=fuente_pequena
                    )

                y += 45

    buffer = BytesIO()

    imagen.save(
        buffer,
        format="PNG"
    )

    buffer.seek(0)

    response = HttpResponse(
        buffer,
        content_type="image/png"
    )

    response["Content-Disposition"] = (
        'attachment; filename="partidos.png"'
    )

    return response

def crear_pdf_detalle_equipo(equipo, lista_jugadores, mostrar_rut=True):

    # =========================================================
    # CONFIGURACIÓN A4 VERTICAL
    # =========================================================

    PAGE_WIDTH, PAGE_HEIGHT = A4

    margen_izquierdo = 10 * mm
    margen_derecho = 10 * mm
    margen_superior = 20 * mm
    margen_inferior = 16 * mm


    # =========================================================
    # COLORES
    # =========================================================

    NEGRO = colors.HexColor("#222222")
    GRIS = colors.HexColor("#666666")
    GRIS_CLARO = colors.HexColor("#E9E9E9")

    DORADO = colors.HexColor("#B8962E")


    # =========================================================
    # FUENTES
    # =========================================================

    try:

        pdfmetrics.registerFont(
            TTFont(
                "LigaNormal",
                ruta_normal
            )
        )

        pdfmetrics.registerFont(
            TTFont(
                "LigaNormalNegrita",
                ruta_normal_negrita
            )
        )

        pdfmetrics.registerFont(
            TTFont(
                "LigaTituloRegular",
                ruta_titulo
            )
        )
        pdfmetrics.registerFont(
            TTFont(
                "LigaTituloNegrita",
                ruta_titulo_negrita
            )
        )
        pdfmetrics.registerFont(
            TTFont(
                "LigaSubtitulo",
                ruta_subtitulo
            )
        )
        pdfmetrics.registerFontFamily(
            "LigaTitulo",
            normal="LigaTituloRegular",
            bold="LigaTituloNegrita"
        )
        
        pdfmetrics.registerFontFamily(
            "LigaNorma",
            normal="LigaNormal",
            bold="LigaNormalNegrita"
        )

        fuente_normal = "LigaNormal"
        fuente_titulo = "LigaTituloRegular"
        fuente_subtitulo = "LigaSubtitulo"

    except Exception:

        fuente_normal = "Helvetica"
        fuente_titulo = "Helvetica-Bold"
        fuente_subtitulo = "Helvetica"


    # =========================================================
    # DOCUMENTO
    # =========================================================

    buffer = BytesIO()

    nombre_liga = str(equipo.liga.nombre)

    doc = SimpleDocTemplate(

        buffer,

        pagesize=A4,

        rightMargin=margen_derecho,
        leftMargin=margen_izquierdo,
        topMargin=margen_superior,
        bottomMargin=margen_inferior,

        title=f"Planilla de jugadores - {equipo.nombre}",

        author=nombre_liga,
    )


    # =========================================================
    # ESTILOS
    # =========================================================

    estilo_titulo = ParagraphStyle(

        "TituloLiga",

        fontName=fuente_titulo,

        fontSize=18,
        leading=21,

        textColor=NEGRO,

        alignment=TA_LEFT,

        spaceAfter=2,
    )


    estilo_subtitulo = ParagraphStyle(

        "SubtituloLiga",

        fontName=fuente_titulo,

        fontSize=10,
        leading=12,

        textColor=NEGRO,

        alignment=TA_CENTER,

        spaceAfter=2,
    )


    estilo_celda = ParagraphStyle(

        "CeldaLiga",

        fontName=fuente_normal,

        fontSize=10,

        leading=9.5,

        textColor=NEGRO,

        alignment=TA_LEFT,
    )


    estilo_celda_centrada = ParagraphStyle(

        "CeldaCentradaLiga",

        fontName=fuente_normal,

        fontSize=10,

        leading=9.5,

        textColor=NEGRO,

        alignment=TA_CENTER,
    )
    estilo_encabezado = ParagraphStyle(

        "EncabezadoLiga",

        fontName=fuente_normal,

        fontSize=10,

        leading=12,

        textColor=NEGRO,

        alignment=TA_LEFT,
    )

    estilo_encabezado_centrado = ParagraphStyle(

        "EncabezadoLiga",

        fontName=fuente_normal,

        fontSize=10,

        leading=12,

        textColor=NEGRO,

        alignment=TA_CENTER,
    )


    estilo_total = ParagraphStyle(

        "TotalLiga",

        fontName=fuente_titulo,

        fontSize=9,

        textColor=NEGRO,
    )
    
    estilo_liga = ParagraphStyle(
        "NombreLigaHeader",
        fontName=fuente_normal,
        fontSize=10.5,
        leading=13,
        textColor=GRIS,
        alignment=TA_LEFT,
        spaceAfter=4,
    )
    estilo_club = ParagraphStyle(
        "NombreClub",
        fontName=fuente_titulo,
        fontSize=14,
        leading=17,
        textColor=DORADO,
        alignment=TA_LEFT,
        spaceBefore=3,
    )


    # =========================================================
    # JUGADORES
    # =========================================================

    if hasattr(lista_jugadores, "all"):

        jugadores = lista_jugadores.all()

    else:

        jugadores = lista_jugadores


    if hasattr(lista_jugadores, "count"):

        try:

            cantidad_jugadores = lista_jugadores.count()

        except TypeError:

            cantidad_jugadores = len(lista_jugadores)

    else:

        cantidad_jugadores = len(lista_jugadores)


    # =========================================================
    # ELEMENTOS DEL PDF
    # =========================================================

    elementos = []

    #
    # CARGA DE LOGOTIPO DE EQUIPO
    #
    logo_equipo = None

    try:
        if equipo.logo:
            url_logo_equipo = equipo.logo.url

            if url_logo_equipo.startswith("//"):
                url_logo_equipo = "https:" + url_logo_equipo

            respuesta_logo_equipo = requests.get(
                url_logo_equipo,
                timeout=15
            )
            respuesta_logo_equipo.raise_for_status()

            logo_equipo = BytesIO(respuesta_logo_equipo.content)
            logo_equipo.seek(0)

    except Exception as e:
        print(
            f"[PDF] Error descargando logo del equipo: {e}",
            flush=True
        )
        
    # =========================================================
    # ANCHO DE TABLA
    # =========================================================

    ancho_util = (

        PAGE_WIDTH
        - margen_izquierdo
        - margen_derecho

    )
    # =========================================================
    # ENCABEZADO CON LOGO DEL EQUIPO
    # =========================================================

    texto_encabezado = [
        Paragraph(
            "<b>LISTADO OFICIAL DE JUGADORES</b>",
            estilo_titulo
        ),

        Paragraph(
            f"<b>{nombre_liga}</b>",
            estilo_liga
        ),

        Spacer(1, 2 * mm),

        Paragraph(
            equipo.nombre,
            estilo_club
        ),
    ]


    if logo_equipo:
        imagen_logo = ReportLabImage(
            logo_equipo,
            width=20 * mm,
            height=20 * mm,
            kind="proportional"
        )

        contenedor_logo = Table(
            [[imagen_logo]],
            colWidths=[26 * mm],
            rowHeights=[26 * mm],
            hAlign="CENTER"
        )

        contenedor_logo.setStyle(
            TableStyle([
                ("BOX", (0, 0), (-1, -1), 1, DORADO),
                ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ])
        )

        logo_encabezado = contenedor_logo
    else:
        logo_encabezado = ""


    encabezado = Table(
        [
            [
                texto_encabezado,
                logo_encabezado
            ]
        ],
        colWidths=[
            ancho_util - 28 * mm,
            28 * mm
        ],
        hAlign="CENTER"
    )


    encabezado.setStyle(
        TableStyle(
            [
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE"
                ),

                (
                    "ALIGN",
                    (0, 0),
                    (0, 0),
                    "CENTER"
                ),

                (
                    "ALIGN",
                    (1, 0),
                    (1, 0),
                    "RIGHT"
                ),

                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    0
                ),

                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    0
                ),

                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    0
                ),

                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    0
                ),
            ]
        )
    )


    elementos.append(encabezado)

    elementos.append(
        Spacer(1, 5 * mm)
    )


    # =========================================================
    # TABLA
    # =========================================================

    encabezados = [
        Paragraph("<b>N°</b>", estilo_encabezado),
        Paragraph("<b>Apellido<br/>Paterno</b>", estilo_encabezado),
        Paragraph("<b>Apellido<br/>Materno</b>", estilo_encabezado),
        Paragraph("<b>Nombres</b>", estilo_encabezado_centrado),
    ]

    if mostrar_rut:
        encabezados.append(Paragraph("<b>RUT</b>", estilo_encabezado_centrado))

    encabezados.extend([
        Paragraph("<b>Fecha de<br/>Nacimiento</b>", estilo_encabezado),
        Paragraph("<b>Fecha de<br/>Inscripción</b>", estilo_encabezado),
    ])

    datos = [encabezados]


    if cantidad_jugadores == 0:

        datos.append(

            [Paragraph("No hay jugadores registrados para este equipo.", estilo_celda)]
            + [""] * (len(encabezados) - 1)

        )

    else:

        contador = 0
        
        for jugador in jugadores:

            nombre_completo = str(
                getattr(
                    jugador,
                    "nombre",
                    None
                ) or "-"
            )
            
            nombre_divido = nombre_completo.strip()
            nombre_divido = nombre_divido.split()
            
            if len(nombre_divido) == 4:
                nombres = nombre_divido[0] + " " + nombre_divido[1]
                apellido_paterno = nombre_divido[2]
                apellido_materno = nombre_divido[3]
                
            elif len(nombre_divido) == 3:
                nombres = nombre_divido[0]
                apellido_paterno = nombre_divido[1]
                apellido_materno = nombre_divido[2]
                
            elif len(nombre_divido) == 5:
                nombres = nombre_divido[0] + " " + nombre_divido[1] + " " + nombre_divido[2]
                apellido_paterno = nombre_divido[3]
                apellido_materno = nombre_divido[4]                
            else:
                nombres = nombre_completo
                apellido_paterno = "-"
                apellido_materno = "-"

            rut = str(
                getattr(
                    jugador,
                    "rut_formateado",
                    None
                ) or "-"
            )

            fechaNac = getattr(
                    jugador,
                    "fecha_nacimiento",
                    None
            )


            fechaInsc = getattr(
                jugador,
                "fecha_inscripcion",
                None
            )
            
            fechaNac = (
                fechaNac.strftime("%d/%m/%Y")
                if fechaNac else "-"
            )

            fechaInsc = (
                fechaInsc.strftime("%d/%m/%Y")
                if fechaInsc else "-"
            )

            contador +=1

            fila = [
                Paragraph(str(contador), estilo_celda),
                Paragraph(apellido_paterno, estilo_celda),
                Paragraph(apellido_materno, estilo_celda),
                Paragraph(nombres, estilo_celda),
            ]

            if mostrar_rut:
                fila.append(Paragraph(rut, estilo_celda))

            fila.extend([
                Paragraph(fechaNac, estilo_celda),
                Paragraph(fechaInsc, estilo_celda),
            ])

            datos.append(fila)

    # =========================================================
    # TABLA
    # =========================================================

    tabla = Table(

        datos,

        colWidths=(
            [
                ancho_util * 0.05,
                ancho_util * 0.15,
                ancho_util * 0.15,
                ancho_util * 0.19,
                ancho_util * 0.16,
                ancho_util * 0.15,
                ancho_util * 0.15,
            ]
            if mostrar_rut else
            [
                ancho_util * 0.06,
                ancho_util * 0.18,
                ancho_util * 0.18,
                ancho_util * 0.28,
                ancho_util * 0.15,
                ancho_util * 0.15,
            ]
        ),

        repeatRows=1,

        hAlign="CENTER",
    )


    # =========================================================
    # ESTILOS TABLA
    # =========================================================

    comandos_tabla = [

        (
            "BACKGROUND",
            (0, 0),
            (-1, 0),
            GRIS_CLARO
        ),

        (
            "BOX",
            (0, 0),
            (-1, -1),
            0.7,
            GRIS
        ),

        (
            "INNERGRID",
            (0, 0),
            (-1, -1),
            0.35,
            colors.HexColor("#BBBBBB")
        ),

        (
            "LINEBELOW",
            (0, 0),
            (-1, 0),
            1.2,
            DORADO
        ),

        (
            "VALIGN",
            (0, 0),
            (-1, -1),
            "MIDDLE"
        ),

        (
            "LEFTPADDING",
            (0, 0),
            (-1, -1),
            5
        ),

        (
            "RIGHTPADDING",
            (0, 0),
            (-1, -1),
            5
        ),

        (
            "TOPPADDING",
            (0, 0),
            (-1, -1),
            4
        ),

        (
            "BOTTOMPADDING",
            (0, 0),
            (-1, -1),
            4
        ),

    ]


    # =========================================================
    # FILAS ALTERNADAS
    # =========================================================


    tabla.setStyle(

        TableStyle(
            comandos_tabla
        )

    )


    elementos.append(
        tabla
    )


    elementos.append(
        Spacer(
            1,
            4 * mm
        )
    )

    # =========================================================
    # DESCARGAR LOGO DESDE CLOUDINARY
    # =========================================================

    logo_marca_agua = None

    try:
        liga = equipo.liga
    except Exception as e:
        print(f"[PDF] equipo.liga falló: {e}", flush=True)
        liga = None

    if liga is None:
        print("[PDF] No hay liga asociada al equipo, se omite marca de agua.", flush=True)

    elif not liga.logo:
        print(f"[PDF] liga.logo está vacío para la liga '{liga}' (id={liga.id}).", flush=True)

    else:

        url_logo = liga.logo.url

        if url_logo.startswith("//"):
            url_logo = "https:" + url_logo

        print(f"[PDF] URL del logo resuelta: {url_logo}", flush=True)

        try:
            respuesta_logo = requests.get(url_logo, timeout=15)
            respuesta_logo.raise_for_status()

            print(
                f"[PDF] Logo descargado OK. status={respuesta_logo.status_code} "
                f"bytes={len(respuesta_logo.content)}",
                flush=True
            )

            logo_original = Image.open(BytesIO(respuesta_logo.content)).convert("RGBA")

            ancho_max = 1200
            alto_max = 1200

            logo_original.thumbnail((ancho_max, alto_max), Image.Resampling.LANCZOS)

            alpha = logo_original.getchannel("A")
            alpha = alpha.point(lambda pixel: int(pixel * 0.1))
            logo_original.putalpha(alpha)

            logo_buffer = BytesIO()
            logo_original.save(logo_buffer, format="PNG")
            logo_buffer.seek(0)

            logo_marca_agua = logo_buffer

            print("[PDF] Marca de agua generada correctamente en memoria.", flush=True)

        except requests.exceptions.RequestException as e:
            print(f"[PDF] Error de red descargando logo desde {url_logo}: {e}", flush=True)

        except Exception as e:
            print(f"[PDF] Error procesando imagen del logo: {e}", flush=True)

    # =========================================================
    # DIBUJAR CADA PÁGINA
    # =========================================================

    def dibujar_pagina(
        canvas,
        documento
    ):

        canvas.saveState()


        # =====================================================
        # FONDO BLANCO
        # =====================================================

        canvas.setFillColor(
            colors.white
        )


        canvas.rect(

            0,
            0,

            PAGE_WIDTH,
            PAGE_HEIGHT,

            fill=1,

            stroke=0

        )


        # =====================================================
        # MARCA DE AGUA
        # =====================================================

        if logo_marca_agua:

            try:

                logo_marca_agua.seek(0)


                imagen = Image.open(
                    logo_marca_agua
                )


                ancho_logo = imagen.width
                alto_logo = imagen.height


                # ---------------------------------------------
                # Tamaño de la marca de agua
                # ---------------------------------------------

                ancho_destino = 160 * mm


                escala = (

                    ancho_destino
                    / ancho_logo

                )


                alto_destino = (

                    alto_logo
                    * escala

                )


                # ---------------------------------------------
                # CENTRAR
                # ---------------------------------------------

                x = (

                    PAGE_WIDTH
                    - ancho_destino

                ) / 2


                y = (

                    PAGE_HEIGHT
                    - alto_destino

                ) / 2


                # ---------------------------------------------
                # DIBUJAR
                # ---------------------------------------------

                logo_marca_agua.seek(0)


                logo_reader = ImageReader(
                    logo_marca_agua
                )

                print(f"[PDF] Dibujando marca de agua en x={x:.1f} y={y:.1f}", flush=True)

                canvas.drawImage(

                    logo_reader,

                    x,
                    y,

                    width=ancho_destino,
                    height=alto_destino,

                    preserveAspectRatio=True,

                    mask="auto"

                )


            except Exception as e:

                print(
                    f"Error dibujando marca de agua: {e}"
                )


        # =====================================================
        # LÍNEA SUPERIOR
        # =====================================================

        canvas.setStrokeColor(
            DORADO
        )


        canvas.setLineWidth(
            1
        )


        canvas.line(

            margen_izquierdo,

            PAGE_HEIGHT - 11 * mm,

            PAGE_WIDTH - margen_derecho,

            PAGE_HEIGHT - 11 * mm

        )


        # =====================================================
        # PIE DE PÁGINA
        # =====================================================

        canvas.setFont(

            fuente_normal,

            7

        )


        canvas.setFillColor(
            GRIS
        )


        canvas.drawString(

            margen_izquierdo,

            8 * mm,

            nombre_liga

        )


        canvas.drawRightString(

            PAGE_WIDTH - margen_derecho,

            8 * mm,

            f"Página {documento.page}"

        )


        canvas.restoreState()


    # =========================================================
    # GENERAR PDF
    # =========================================================

    doc.build(

        elementos,

        onFirstPage=dibujar_pagina,

        onLaterPages=dibujar_pagina

    )


    # =========================================================
    # RESPUESTA
    # =========================================================

    buffer.seek(0)


    response = HttpResponse(

        buffer.getvalue(),

        content_type="application/pdf"

    )


    nombre_archivo = (

        equipo.nombre

        .replace(
            " ",
            "_"
        )

        .replace(
            "/",
            "_"
        )

        .replace(
            "\\",
            "_"
        )

    )


    response["Content-Disposition"] = (

        f'attachment; '
        f'filename="planilla_{nombre_archivo}.pdf"'

    )


    return response
