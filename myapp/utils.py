"""
utilidades.py — validaciones, generación de imágenes (tabla, fechas, resultados) y PDF de planilla.

Índice:
    1. Validaciones de formularios
    2. Imágenes: configuración, fuentes y logos
    3. Imágenes: lienzo (dibujo)
    4. Imágenes: piezas comunes, cartelera (fechas/resultados) y tabla de posiciones
    5. API de imágenes para las vistas (crear_img_*)
    6. PDF de planilla de jugadores

Fuentes (licencia OFL) a copiar en static/fonts/:
    BebasNeue-Regular.ttf, BarlowCondensed-Bold.ttf,
    BarlowCondensed-SemiBold.ttf, Barlow-Medium.ttf
Si faltan, se usan Cinzel/Lato (imágenes) o Helvetica (PDF) como respaldo.
"""
import logging
import os
import re
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, time as dtime
from decimal import Decimal, InvalidOperation
from functools import lru_cache
from io import BytesIO

import requests
from dateutil.relativedelta import relativedelta
from django.contrib.staticfiles import finders
from django.core.exceptions import ValidationError
from django.core.validators import validate_email as django_validate_email
from django.http import HttpResponse
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont, ImageOps
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Image as ReportLabImage,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

logger = logging.getLogger(__name__)


# =========================================================
# 1. VALIDACIONES DE FORMULARIOS
# =========================================================

LETTERS = "A-Za-zÁÉÍÓÚáéíóúÑñÜü"

# Usadas por models.py (from .utils import DIAS, MESES)
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
        raise ValidationError(f"{field_name.capitalize()} demasiado corto.")

    if len(value) > max_length:
        raise ValidationError(f"{field_name.capitalize()} demasiado largo.")

    # Letras, números, espacios, guiones y comas
    pattern = rf"^[{LETTERS}0-9\s\-,]+$"
    if not re.fullmatch(pattern, value):
        raise ValidationError(f"{field_name.capitalize()} contiene caracteres invalidos.")

    if not _has_letters(value):
        raise ValidationError(f"{field_name.capitalize()} debe contener letras.")

    cleaned = _meaningful_text(value)
    if cleaned and len(set(cleaned)) == 1:
        raise ValidationError(f"Ingresa {field_name} valido.")

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
        raise ValidationError("La red social contiene caracteres invalidos.")

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
            message=duplicate_message or "Este RUT ya esta registrado.",
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


def validate_date_not_future(value, field_name="La fecha", required=True, max_age_years=None):
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
    min_date = base_date + relativedelta(years=1, months=6)
    if value < min_date:
        raise ValidationError(f"El jugador no puede transferirse antes de {min_date}.")

    return value


def validate_integer_range(value, field_name, minimum=None, maximum=None, required=False):
    if value is None:
        if required:
            raise ValidationError(f"Debes ingresar {field_name}.")
        return value

    if minimum is not None and value < minimum:
        raise ValidationError(f"{field_name.capitalize()} no puede ser menor que {minimum}.")

    if maximum is not None and value > maximum:
        raise ValidationError(f"{field_name.capitalize()} no puede ser mayor que {maximum}.")

    return value


def validate_decimal_range(value, field_name, minimum=None, maximum=None, required=True):
    """Valida un número decimal dentro de un rango permitido."""
    if value in (None, ""):
        if required:
            raise ValidationError(f"Debe ingresar {field_name}.")
        return None

    try:
        value = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise ValidationError(f"{field_name.capitalize()} debe ser un número válido.")

    if minimum is not None and value < Decimal(str(minimum)):
        raise ValidationError(f"{field_name.capitalize()} debe ser mayor o igual a {minimum}.")

    if maximum is not None and value > Decimal(str(maximum)):
        raise ValidationError(f"{field_name.capitalize()} debe ser menor o igual a {maximum}.")

    return value


# =========================================================
# 2. IMÁGENES: CONFIGURACIÓN, FUENTES Y LOGOS
# =========================================================

ANCHO = 900          # ancho final en px
ESC = 2              # supersampling: se dibuja al doble y se reduce (bordes suaves)
MAX_EQUIPOS = 12
TITULO_LIGA = "UNIÓN COMUNAL DE CLUBES DEPORTIVOS"

ORO = (227, 185, 72)
ORO_CLARO = (255, 226, 140)
ORO_OSCURO = (176, 128, 30)
CAFE = (74, 46, 20)
CREMA = (245, 238, 224)
TENUE = (178, 168, 150)
TINTA = (38, 24, 8)
FONDO_ARRIBA = (44, 30, 16)
FONDO_ABAJO = (9, 7, 5)
VERDE = (126, 205, 142)
ROJO = (226, 116, 104)

PODIO = {1: (240, 196, 64), 2: (206, 208, 214), 3: (205, 127, 50)}

# clave -> (archivo principal, respaldos)
FUENTES = {
    "titulo": ("BebasNeue-Regular.ttf", ("Cinzel-Bold.ttf",)),
    "nombre": ("BarlowCondensed-Bold.ttf", ("Lato-Bold.ttf",)),
    "semi": ("BarlowCondensed-SemiBold.ttf", ("Lato-Bold.ttf",)),
    "texto": ("Barlow-Medium.ttf", ("Lato-Regular.ttf",)),
}


def S(v):
    """Pasa de px lógicos a px del lienzo (con supersampling)."""
    return int(round(v * ESC))


# =========================================================
# FUENTES Y LOGOS
# =========================================================

def _buscar_fuente(archivo):
    try:
        ruta = finders.find(f"fonts/{archivo}")
        if ruta:
            return ruta
    except Exception:
        pass
    ruta = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts", archivo)
    return ruta if os.path.exists(ruta) else None


@lru_cache(maxsize=None)
def _fuente(clave, size):
    principal, respaldos = FUENTES[clave]
    for archivo in (principal, *respaldos):
        ruta = _buscar_fuente(archivo)
        if ruta:
            return ImageFont.truetype(ruta, S(size))
        logger.warning("Fuente no encontrada: %s", archivo)
    return ImageFont.load_default(S(size))


def _normalizar_url(url):
    if url and url.startswith("//"):
        return "https:" + url
    return url


def _url_logo(obj):
    logo = getattr(obj, "logo", None)
    if not logo:
        return None
    try:
        return _normalizar_url(logo.url)
    except Exception:
        return None


def _descargar_logo(url):
    try:
        r = requests.get(url, timeout=6)
        r.raise_for_status()
        return Image.open(BytesIO(r.content)).convert("RGBA")
    except Exception:
        logger.warning("No se pudo descargar el logo %s", url, exc_info=True)
        return None


def _precargar_logos(urls):
    """Descarga en paralelo las URLs únicas. Devuelve {url: Image | None}."""
    urls = {u for u in urls if u}
    if not urls:
        return {}
    with ThreadPoolExecutor(max_workers=min(8, len(urls))) as pool:
        return dict(zip(urls, pool.map(_descargar_logo, urls)))


# =========================================================
# 3. IMÁGENES: LIENZO (DIBUJO)
# =========================================================

class Lienzo:
    def __init__(self, alto):
        self.alto = alto
        self.img = Image.new("RGBA", (S(ANCHO), S(alto)), (0, 0, 0, 255))
        self.draw = ImageDraw.Draw(self.img)

    # ---------- utilidades ----------
    def ancho(self, txt, fuente):
        return self.draw.textlength(txt, font=fuente) / ESC

    def _pegar(self, capa, pos):
        self.img.paste(capa.convert("RGB"), pos, capa.getchannel("A"))

    # ---------- fondo ----------
    def fondo(self, imagen=None):
        w, h = self.img.size
        if imagen is not None:
            base = ImageOps.fit(imagen.convert("RGB"), (w, h), Image.LANCZOS, centering=(0.5, 0.0))
            base = Image.blend(base, Image.new("RGB", (w, h), (8, 6, 4)), 0.72)
        else:
            grad = Image.linear_gradient("L").resize((w, h))
            base = ImageOps.colorize(grad, black=FONDO_ARRIBA, white=FONDO_ABAJO)
        self.img.paste(base.convert("RGBA"))

    def resplandor(self, cx, cy, radio, color=ORO, intensidad=0.3):
        r = S(radio)
        # radial_gradient llega a 255 solo en las esquinas (181 en los bordes): se reescala para que el borde sea 0
        mask = Image.radial_gradient("L").resize((2 * r, 2 * r), Image.BICUBIC)
        mask = mask.point(lambda p: int(max(0, 255 - p * 1.41) * intensidad))
        self.img.paste(Image.new("RGBA", (2 * r, 2 * r), color + (255,)), (S(cx) - r, S(cy) - r), mask)

    def patron(self, paso=26, alpha=9):
        w, h = self.img.size
        capa = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(capa)
        for x in range(-h, w, S(paso)):
            d.line((x, h, x + h, 0), fill=(255, 230, 170, alpha), width=S(1))
        self.img.alpha_composite(capa)

    def marca_agua(self, logo, desde_y, opacidad=0.2):
        """Logo grande repetido a lo largo de la imagen, centrado, bajo las tarjetas."""
        if logo is None:
            return
        lado = S(ANCHO * 0.84)
        marca = ImageOps.contain(logo, (lado, lado), Image.LANCZOS)  # también amplía logos pequeños
        alpha = marca.getchannel("A").point(lambda p: int(p * opacidad))
        rgb = marca.convert("RGB")
        zona = self.img.height - S(desde_y) - S(80)
        n = max(1, round(zona / (lado + S(30))))
        paso = zona / n
        for k in range(n):
            cy = S(desde_y) + paso * (k + 0.5)
            pos = (self.img.width // 2 - marca.width // 2, int(cy - marca.height // 2))
            self.img.paste(rgb, pos, alpha)

    def vineta(self, fuerza=0.6):
        w, h = self.img.size
        mask = Image.radial_gradient("L").resize((w, h), Image.BICUBIC).point(lambda p: int(p * fuerza))
        self.img.paste((0, 0, 0, 255), (0, 0, w, h), mask)

    # ---------- formas ----------
    def panel(self, box, radio=16, relleno=(0, 0, 0, 150), borde=None, grosor=1):
        x0, y0, x1, y1 = (S(v) for v in box)
        w, h = x1 - x0, y1 - y0
        capa = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        ImageDraw.Draw(capa).rounded_rectangle(
            (0, 0, w - 1, h - 1), radius=S(radio), fill=relleno,
            outline=borde, width=S(grosor) if borde else 0)
        self._pegar(capa, (x0, y0))

    def panel_degradado(self, box, radio, arriba, abajo):
        x0, y0, x1, y1 = (S(v) for v in box)
        w, h = x1 - x0, y1 - y0
        grad = ImageOps.colorize(Image.linear_gradient("L").resize((w, h)), black=arriba, white=abajo)
        mask = Image.new("L", (w, h), 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, w - 1, h - 1), radius=S(radio), fill=255)
        self.img.paste(grad.convert("RGBA"), (x0, y0), mask)

    def linea_dorada(self, y, x0=40, x1=860, grosor=2, rombo=True):
        w, h = S(x1 - x0), S(grosor)
        mitad = Image.linear_gradient("L").rotate(90).resize((w // 2, h))
        mask = Image.new("L", (w, h), 0)
        mask.paste(mitad, (0, 0))
        mask.paste(ImageOps.mirror(mitad), (w // 2, 0))
        self.img.paste(ORO + (255,), (S(x0), S(y), S(x0) + w, S(y) + h), mask)
        if rombo:
            cx, cy, r = S((x0 + x1) / 2), S(y) + h // 2, S(6)
            self.draw.polygon([(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)], fill=ORO)

    # ---------- texto ----------
    def texto(self, xy, txt, fuente, color=CREMA, anchor="la", sombra=True, grad=None):
        """Texto con sombra suave y, opcionalmente, relleno en degradado vertical (grad=(arriba, abajo))."""
        x, y = S(xy[0]), S(xy[1])
        l, t, r, b = self.draw.textbbox((x, y), txt, font=fuente, anchor=anchor)
        pad = S(10)
        ox, oy = l - pad, t - pad
        w, h = r - l + 2 * pad, b - t + 2 * pad
        mask = Image.new("L", (w, h), 0)
        ImageDraw.Draw(mask).text((x - ox, y - oy), txt, font=fuente, fill=255, anchor=anchor)
        if sombra:
            sm = mask.filter(ImageFilter.GaussianBlur(S(2.2))).point(lambda p: int(p * 0.85))
            self.img.paste((0, 0, 0, 255), (ox + S(1), oy + S(2.5), ox + S(1) + w, oy + S(2.5) + h), sm)
        if grad:
            fill = ImageOps.colorize(Image.linear_gradient("L").resize((w, h)), black=grad[0], white=grad[1])
            self.img.paste(fill.convert("RGBA"), (ox, oy), mask)
        else:
            self.img.paste(tuple(color) + (255,), (ox, oy, ox + w, oy + h), mask)

    def fuente_ajustada(self, txt, clave, size, ancho_max, minimo=14):
        while size > minimo:
            f = _fuente(clave, size)
            if self.ancho(txt, f) <= ancho_max:
                return f
            size -= 1
        return _fuente(clave, minimo)

    def lineas_nombre(self, nombre, clave, size, ancho_max):
        """Divide un nombre en hasta 2 líneas; reduce la fuente si hace falta."""
        nombre = " ".join(str(nombre or "-").split())
        palabras = nombre.split()
        for sz in range(size, 15, -2):
            f = _fuente(clave, sz)
            if self.ancho(nombre, f) <= ancho_max:
                return [nombre], f
            mejor = None
            for i in range(1, len(palabras)):
                a, b = " ".join(palabras[:i]), " ".join(palabras[i:])
                m = max(self.ancho(a, f), self.ancho(b, f))
                if mejor is None or m < mejor[0]:
                    mejor = (m, [a, b])
            if mejor and mejor[0] <= ancho_max:
                return mejor[1], f
        f = _fuente(clave, 16)
        t = nombre
        while t and self.ancho(t + "...", f) > ancho_max:
            t = t[:-1]
        return [(t + "...") if t else "-"], f

    # ---------- logos ----------
    def logo_libre(self, cx, cy, tam, logo):
        """Logo de la liga sin recortar (respeta escudos y formas no circulares)."""
        lado = S(tam)
        l = ImageOps.contain(logo, (lado, lado), Image.LANCZOS)
        x, y = S(cx) - l.width // 2, S(cy) - l.height // 2
        sombra = Image.new("L", (l.width + S(40), l.height + S(40)), 0)
        sombra.paste(l.getchannel("A").point(lambda p: int(p * 0.7)), (S(20), S(20)))
        sombra = sombra.filter(ImageFilter.GaussianBlur(S(6)))
        self.img.paste((0, 0, 0, 255), (x - S(20), y - S(16), x - S(20) + sombra.width, y - S(16) + sombra.height), sombra)
        self.img.paste(l.convert("RGB"), (x, y), l.getchannel("A"))

    def logo_circular(self, cx, cy, d, logo, letra="?", borde=3):
        D = S(d)
        x0, y0 = S(cx) - D // 2, S(cy) - D // 2
        pad = S(14)
        sombra = Image.new("L", (D + 2 * pad, D + 2 * pad), 0)
        ImageDraw.Draw(sombra).ellipse((pad, pad, pad + D, pad + D), fill=190)
        sombra = sombra.filter(ImageFilter.GaussianBlur(S(6)))
        self.img.paste((0, 0, 0, 255), (x0 - pad, y0 - pad + S(4), x0 - pad + sombra.width, y0 - pad + S(4) + sombra.height), sombra)

        B = S(borde)
        self.draw.ellipse((x0 - B, y0 - B, x0 + D + B, y0 + D + B), fill=ORO)
        if logo is not None:
            self.draw.ellipse((x0, y0, x0 + D, y0 + D), fill=(246, 241, 230, 255))
            inner = D - S(6)
            recorte = ImageOps.fit(logo, (inner, inner), Image.LANCZOS)
            mask = Image.new("L", (inner, inner), 0)
            ImageDraw.Draw(mask).ellipse((0, 0, inner - 1, inner - 1), fill=255)
            alpha = ImageChops.multiply(recorte.getchannel("A"), mask)
            self.img.paste(recorte.convert("RGB"), (x0 + S(3), y0 + S(3)), alpha)
        else:
            self.draw.ellipse((x0, y0, x0 + D, y0 + D), fill=(40, 28, 16, 255))
            self.texto((cx, cy + d * 0.03), (letra or "?")[0].upper(), _fuente("titulo", int(d * 0.62)),
                       anchor="mm", sombra=False, grad=(ORO_CLARO, ORO_OSCURO))

    def exportar(self):
        final = self.img.resize((ANCHO, self.alto), Image.LANCZOS).convert("RGB")
        buf = BytesIO()
        final.save(buf, format="PNG", optimize=True)
        return buf.getvalue()


# =========================================================
# 4. IMÁGENES: PIEZAS COMUNES
# =========================================================

def _inicial(obj):
    return (str(obj or "?").strip() or "?")[0]


def _hora_texto(h):
    if hasattr(h, "strftime"):
        return h.strftime("%H:%M") + " HORAS"
    s = str(h or "").strip()
    return (s[:5] + " HORAS") if s else "POR DEFINIR"


def _orden(p):
    return (p.fecha, p.hora or dtime.min)


DIAS_LARGO = ["LUNES", "MARTES", "MIÉRCOLES", "JUEVES", "VIERNES", "SÁBADO", "DOMINGO"]
MESES_LARGO = ["ENERO", "FEBRERO", "MARZO", "ABRIL", "MAYO", "JUNIO", "JULIO",
               "AGOSTO", "SEPTIEMBRE", "OCTUBRE", "NOVIEMBRE", "DICIEMBRE"]


def _fecha_larga(f):
    """'SÁBADO 10 DE OCTUBRE DE 2026'. No depende del locale del servidor."""
    if isinstance(f, datetime):
        f = f.date()
    if not isinstance(f, date):
        return ""
    return f"{DIAS_LARGO[f.weekday()]} {f.day} DE {MESES_LARGO[f.month - 1]} DEL {f.year}"


def _plano(texto):
    """Mayúsculas y sin tildes, para comparar textos."""
    t = unicodedata.normalize("NFD", str(texto or "").upper())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def _titulo_sin_fecha(titulo, grupos, por_defecto):
    """
    La fecha se muestra solo en el banner de cada grupo. Si el título recibido ya
    trae alguna de esas fechas, se descarta y se usa el título por defecto.
    """
    if not titulo:
        return por_defecto
    t = _plano(titulo)
    for g in grupos:
        f = g["partidos"][0].fecha
        if isinstance(f, datetime):
            f = f.date()
        if not isinstance(f, date):
            continue
        exacta = _plano(getattr(g["partidos"][0], "fecha_exacta", ""))
        mes = _plano(MESES_LARGO[f.month - 1])
        if (
            (exacta and exacta in t)
            or f.strftime("%d/%m/%Y") in t
            or f.isoformat() in t
            or (re.search(rf"\b0?{f.day}\b", t) and mes in t)
        ):
            return por_defecto
    return titulo


def _agrupar_por_fecha(partidos, etiquetas=()):
    grupos, actual = [], None
    for p in partidos:
        if p.fecha != actual:
            etiqueta = etiquetas[len(grupos)] if len(grupos) < len(etiquetas) else ""
            fecha = _fecha_larga(p.fecha) or str(getattr(p, "fecha_exacta", "")).upper()
            txt = f"{etiqueta}  ·  {fecha}" if etiqueta else fecha
            grupos.append({"texto": txt.upper(), "partidos": []})
            actual = p.fecha
        grupos[-1]["partidos"].append(p)
    return grupos


def _encabezado(lz, subtitulo, logo_liga):
    """Dibuja el encabezado y devuelve su alto."""
    alto = 290 if logo_liga else 185
    lz.panel((0, 0, ANCHO, alto), 0, (0, 0, 0, 125))
    if logo_liga:
        lz.resplandor(450, 100, 170, ORO, 0.32)
        lz.logo_libre(450, 100, 130, logo_liga)
        y = 182
    else:
        y = 34
    f = lz.fuente_ajustada(TITULO_LIGA, "titulo", 48, 800)
    lz.texto((450, y), TITULO_LIGA, f, anchor="ma", grad=(ORO_CLARO, ORO_OSCURO))
    sub = subtitulo.upper()
    fs = lz.fuente_ajustada(sub, "semi", 30, 780, minimo=18)
    lz.texto((450, y + 56), sub, fs, CREMA, anchor="ma")
    lz.linea_dorada(alto - 10)
    return alto


def _pie(lz, y, nombre_liga=None):
    lz.linea_dorada(y, rombo=False, grosor=1.5)
    txt = f"Generado el {datetime.now():%d-%m-%Y %H:%M}"
    if nombre_liga:
        txt += f"   ·   {nombre_liga}"
    lz.texto((450, y + 14), txt, _fuente("texto", 16), TENUE, anchor="ma", sombra=False)


def _respuesta(datos, filename):
    r = HttpResponse(datos, content_type="image/png")
    r["Content-Disposition"] = f'attachment; filename="{filename}"'
    return r


# =========================================================
# 4b. CARTELERA (fechas programadas y resultados)
# =========================================================

CARD_H = 228
BANNER_H = 56


def _tarjeta_partido(lz, y0, p, logos, resultado):
    lz.panel((40, y0, 860, y0 + CARD_H), 20, (12, 9, 6, 150), borde=ORO + (85,), grosor=1.5)

    # píldora de hora
    hora = _hora_texto(p.hora)
    fh = _fuente("semi", 22)
    w = lz.ancho(hora, fh) + 46
    lz.panel_degradado((450 - w / 2, y0 - 17, 450 + w / 2, y0 + 17), 17, ORO_CLARO, ORO_OSCURO)
    lz.texto((450, y0), hora, fh, TINTA, anchor="mm", sombra=False)

    cy = y0 + 88
    for cx, equipo in ((150, p.equipo_local), (750, p.equipo_visitante)):
        lz.logo_circular(cx, cy, 104, logos.get(_url_logo(equipo)), _inicial(equipo))
        lineas, f = lz.lineas_nombre(equipo, "nombre", 28, 195)
        ny = y0 + 156
        for i, linea in enumerate(lineas):
            lz.texto((cx, ny + i * 31), linea.upper(), f, CREMA, anchor="ma")

    if resultado:
        gl, gv = p.goles_local, p.goles_visitante
        lz.panel((335, cy - 52, 565, cy + 52), 24, CAFE + (235,), borde=ORO, grosor=2)
        fg = _fuente("titulo", 84)
        gana_l, gana_v = (gl or 0) >= (gv or 0), (gv or 0) >= (gl or 0)
        for x, val, gana, anc in ((450 - 34, gl, gana_l, "rm"), (450 + 34, gv, gana_v, "lm")):
            if gana:
                lz.texto((x, cy + 2), str(val), fg, anchor=anc, grad=(ORO_CLARO, ORO_OSCURO))
            else:
                lz.texto((x, cy + 2), str(val), fg, (205, 190, 160), anchor=anc)
        lz.texto((450, cy + 2), "-", _fuente("titulo", 54), TENUE, anchor="mm", sombra=False)
    else:
        lz.resplandor(450, cy, 70, ORO, 0.25)
        lz.draw.ellipse((S(450 - 40), S(cy - 40), S(450 + 40), S(cy + 40)), fill=ORO)
        lz.draw.ellipse((S(450 - 36), S(cy - 36), S(450 + 36), S(cy + 36)), fill=CAFE + (255,))
        lz.texto((450, cy + 2), "VS", _fuente("titulo", 38), anchor="mm", sombra=False, grad=(ORO_CLARO, ORO))

    cancha = str(getattr(p, "cancha", "") or "").strip()
    if cancha:
        fc = lz.fuente_ajustada(cancha.upper(), "semi", 21, 230, minimo=14)
        lz.texto((450, y0 + 150), cancha.upper(), fc, TENUE, anchor="ma", sombra=False)


def _render_cartelera(grupos, subtitulo, liga, resultado, vacio):
    n = sum(len(g["partidos"]) for g in grupos)
    logo_url = _url_logo(liga) if liga else None
    equipos = [e for g in grupos for p in g["partidos"] for e in (p.equipo_local, p.equipo_visitante)]
    logos = _precargar_logos([logo_url] + [_url_logo(e) for e in equipos])
    logo_liga = logos.get(logo_url)

    enc = 290 if logo_liga else 185
    cuerpo = 110 if n == 0 else len(grupos) * (BANNER_H + 46) + n * (CARD_H + 46)
    alto = max(enc + 30 + cuerpo + 90, 700)

    lz = Lienzo(alto)
    lz.fondo()
    lz.resplandor(450, enc, 520, ORO, 0.10)
    lz.patron()
    lz.marca_agua(logo_liga, enc, 0.22)
    lz.vineta()
    _encabezado(lz, subtitulo, logo_liga)

    y = enc + 30
    if n == 0:
        lz.panel((40, y, 860, y + 90), 18, (12, 9, 6, 150), borde=ORO + (80,))
        lz.texto((450, y + 45), vacio, _fuente("semi", 26), CREMA, anchor="mm")
    for g in grupos:
        lz.panel_degradado((40, y, 860, y + BANNER_H), 16, ORO_CLARO, ORO_OSCURO)
        f = lz.fuente_ajustada(g["texto"], "titulo", 34, 780, minimo=18)
        lz.texto((450, y + BANNER_H / 2 + 1), g["texto"], f, TINTA, anchor="mm", sombra=False)
        y += BANNER_H + 46
        for p in g["partidos"]:
            _tarjeta_partido(lz, y, p, logos, resultado)
            y += CARD_H + 46

    _pie(lz, alto - 64, getattr(liga, "nombre", None))
    return lz.exportar()


def render_fechas(torneo, partidos, liga, titulo=None):
    prog = sorted((p for p in partidos if p.estado == "Programado"), key=_orden)
    grupos = _agrupar_por_fecha(prog, ("FECHA ACTUAL", "FECHA SIGUIENTE"))
    defecto = getattr(torneo, "nombre", None) or "Fechas programadas"
    sub = _titulo_sin_fecha(titulo, grupos, defecto)
    return _render_cartelera(grupos, sub, liga, False, "No hay fechas registradas para este torneo.")


def render_partidos(torneo, partidos, titulo=None, liga=None):
    jug = sorted((p for p in partidos if p.estado == "Jugado"), key=_orden)
    if liga is None:
        liga = next((p.equipo_local.liga for p in jug if p.equipo_local and p.equipo_local.liga), None)
    grupos = _agrupar_por_fecha(jug)
    defecto = f"Resultados · {torneo.nombre}" if torneo else "Partidos jugados"
    sub = _titulo_sin_fecha(titulo, grupos, defecto)
    return _render_cartelera(grupos, sub, liga, True, "No hay partidos registrados para este torneo.")


# =========================================================
# 4c. TABLA DE POSICIONES
# =========================================================

FILA_H = 52
FILA_PASO = 62
COL_PJ, COL_DG, COL_PTS = 622, 712, 800


def _fmt_dg(dg):
    try:
        v = int(dg)
    except (TypeError, ValueError):
        return str(dg), TENUE
    if v > 0:
        return f"+{v}", VERDE
    if v < 0:
        return str(v), ROJO
    return "0", TENUE


def render_tabla(torneo, tabla_posiciones, fondo_img=None):
    filas = list(tabla_posiciones[:MAX_EQUIPOS])
    liga = getattr(torneo, "liga", None)
    if liga is None and filas:
        liga = getattr(filas[0]["equipo"], "liga", None)

    logo_url = _url_logo(liga) if liga else None
    logos = _precargar_logos([logo_url] + [_url_logo(f["equipo"]) for f in filas])
    logo_liga = logos.get(logo_url)

    enc = 290 if logo_liga else 185
    alto = enc + 24 + 52 + len(filas) * FILA_PASO + 100

    lz = Lienzo(alto)
    lz.fondo(fondo_img)
    lz.resplandor(450, enc, 520, ORO, 0.10)
    lz.patron()
    lz.marca_agua(logo_liga, enc, 0.20)
    lz.vineta()
    _encabezado(lz, f"Tabla de posiciones · {torneo.nombre}", logo_liga)

    y = enc + 24
    fh = _fuente("semi", 22)
    lz.texto((80, y + 14), "POS", fh, ORO, anchor="mm", sombra=False)
    lz.texto((124, y + 14), "CLUB", fh, ORO, anchor="lm", sombra=False)
    for x, t in ((COL_PJ, "PJ"), (COL_DG, "DG"), (COL_PTS, "PTS")):
        lz.texto((x, y + 14), t, fh, ORO, anchor="mm", sombra=False)
    lz.panel((40, y + 34, 860, y + 36), 0, ORO + (110,))
    y += 52

    for pos, fila in enumerate(filas, start=1):
        equipo = fila["equipo"]
        podio = PODIO.get(pos)
        lz.panel((40, y, 860, y + FILA_H), 14,
                 (12, 9, 6, 165) if pos % 2 else (30, 22, 14, 150),
                 borde=(podio + (120,)) if podio else (255, 255, 255, 18), grosor=1.5 if podio else 1)
        cy = y + FILA_H / 2

        if podio:
            lz.draw.ellipse((S(80 - 19), S(cy - 19), S(80 + 19), S(cy + 19)), fill=podio)
            lz.texto((80, cy + 1), str(pos), _fuente("titulo", 28), TINTA, anchor="mm", sombra=False)
        else:
            lz.texto((80, cy + 1), str(pos), _fuente("titulo", 30), (205, 195, 175), anchor="mm", sombra=False)

        lz.logo_circular(150, cy, 38, logos.get(_url_logo(equipo)), _inicial(equipo.nombre), borde=2)
        nombre = str(equipo.nombre).upper()
        f = lz.fuente_ajustada(nombre, "nombre", 30, 400, minimo=16)
        lz.texto((184, cy + 1), nombre, f, CREMA, anchor="lm")

        lz.texto((COL_PJ, cy + 1), str(fila["pj"]), _fuente("titulo", 32), (205, 195, 175), anchor="mm", sombra=False)
        dg, color = _fmt_dg(fila["dg"])
        lz.texto((COL_DG, cy + 1), dg, _fuente("titulo", 32), color, anchor="mm", sombra=False)

        lz.panel((COL_PTS - 42, y + 7, COL_PTS + 42, y + FILA_H - 7), 14, CAFE + (230,), borde=ORO, grosor=1.5)
        lz.texto((COL_PTS, cy + 1), str(fila["pts"]), _fuente("titulo", 34), anchor="mm", sombra=False,
                 grad=(ORO_CLARO, ORO_OSCURO))
        y += FILA_PASO

    _pie(lz, alto - 64, getattr(liga, "nombre", None))
    return lz.exportar()


# =========================================================
# 5. API DE IMÁGENES PARA LAS VISTAS (HttpResponse)
# =========================================================

def crear_img_tabla(torneo, tabla_posiciones):
    ruta = finders.find("img/tabla_fondo.png")
    fondo = Image.open(ruta) if ruta else None
    return _respuesta(render_tabla(torneo, tabla_posiciones, fondo), "tabla.png")


def crear_img_fechas(torneo, partidos, liga, titulo=None, filename="fechas.png"):
    return _respuesta(render_fechas(torneo, partidos, liga, titulo), filename)


def crear_img_partidos(torneo, partidos, titulo=None, filename="partidos.png"):
    return _respuesta(render_partidos(torneo, partidos, titulo), filename)


# ---------------------------------------------------------
# Helpers conservados del módulo anterior (por compatibilidad con otras partes del proyecto)
# ---------------------------------------------------------

def _formatear_fecha_hora(valor, formato_salida="%A %d de %B %Y", solo_hora=False):
    """
    Acepta un datetime/time real o un string y devuelve el texto formateado.
    Si es string y no se puede parsear, lo devuelve tal cual (sin romper).
    """
    dt = valor

    if isinstance(valor, str):
        dt = None
        for formato in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%d/%m/%Y %H:%M", "%d-%m-%Y %H:%M"):
            try:
                dt = datetime.strptime(valor, formato)
                break
            except ValueError:
                continue

    if dt is None or not hasattr(dt, "strftime"):
        return valor.upper() if isinstance(valor, str) else str(valor)

    if solo_hora:
        return dt.strftime("%H:%M HORAS")

    return dt.strftime(formato_salida).upper()


def _texto_ajustado(draw, texto, fuente, ancho_maximo):
    """Recorta el texto con '...' hasta que quepa en ancho_maximo."""
    texto = str(texto or "-")

    if draw.textlength(texto, font=fuente) <= ancho_maximo:
        return texto

    while texto and draw.textlength(f"{texto}...", font=fuente) > ancho_maximo:
        texto = texto[:-1]

    return f"{texto}..." if texto else "-"


# =========================================================
# 6. PDF DE PLANILLA DE JUGADORES
# =========================================================

PDF_DORADO = colors.HexColor("#B8962E")
PDF_NEGRO = colors.HexColor("#222222")
PDF_GRIS = colors.HexColor("#666666")
PDF_GRIS_CLARO = colors.HexColor("#E9E9E9")

_PDF_FUENTES = None


def _fuentes_pdf():
    """Registra las fuentes una sola vez. Devuelve {'normal': ..., 'titulo': ...}."""
    global _PDF_FUENTES
    if _PDF_FUENTES:
        return _PDF_FUENTES
    try:
        for nombre, clave in (("LigaNormal", "texto"), ("LigaNegrita", "nombre"), ("LigaTitulo", "titulo")):
            archivo = FUENTES[clave][0]
            ruta = _buscar_fuente(archivo)
            if not ruta:
                raise FileNotFoundError(archivo)
            pdfmetrics.registerFont(TTFont(nombre, ruta))
        # Necesario para que <b>...</b> use la negrita real
        pdfmetrics.registerFontFamily("LigaNormal", normal="LigaNormal", bold="LigaNegrita")
        _PDF_FUENTES = {"normal": "LigaNormal", "titulo": "LigaTitulo"}
    except Exception:
        logger.warning("No se pudieron registrar las fuentes del PDF; se usa Helvetica.", exc_info=True)
        _PDF_FUENTES = {"normal": "Helvetica", "titulo": "Helvetica-Bold"}
    return _PDF_FUENTES


def _separar_nombre(nombre_completo):
    """Devuelve (nombres, apellido_paterno, apellido_materno) según la cantidad de palabras."""
    partes = nombre_completo.split()
    if len(partes) == 3:
        return partes[0], partes[1], partes[2]
    if len(partes) == 4:
        return " ".join(partes[:2]), partes[2], partes[3]
    if len(partes) == 5:
        return " ".join(partes[:3]), partes[3], partes[4]
    return nombre_completo, "-", "-"


def _fecha_texto(valor):
    return valor.strftime("%d/%m/%Y") if valor else "-"


def _descargar_bytes(url, timeout=15):
    try:
        r = requests.get(_normalizar_url(url), timeout=timeout)
        r.raise_for_status()
        return r.content
    except Exception:
        logger.warning("[PDF] No se pudo descargar %s", url, exc_info=True)
        return None


def _marca_agua_pdf(liga, opacidad=0.10):
    """Devuelve un ImageReader con el logo de la liga translúcido, o None."""
    url = _url_logo(liga) if liga else None
    if not url:
        return None
    datos = _descargar_bytes(url)
    if not datos:
        return None
    try:
        logo = Image.open(BytesIO(datos)).convert("RGBA")
        logo.thumbnail((1200, 1200), Image.LANCZOS)
        logo.putalpha(logo.getchannel("A").point(lambda p: int(p * opacidad)))
        buf = BytesIO()
        logo.save(buf, format="PNG")
        buf.seek(0)
        return ImageReader(buf)
    except Exception:
        logger.warning("[PDF] No se pudo procesar el logo de la liga.", exc_info=True)
        return None


def crear_pdf_detalle_equipo(equipo, lista_jugadores, mostrar_rut=True):
    PAGE_WIDTH, PAGE_HEIGHT = A4
    margen_x = 10 * mm
    ancho_util = PAGE_WIDTH - 2 * margen_x

    fuentes = _fuentes_pdf()
    f_normal, f_titulo = fuentes["normal"], fuentes["titulo"]

    liga = getattr(equipo, "liga", None)
    nombre_liga = str(getattr(liga, "nombre", "") or "")

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=margen_x,
        leftMargin=margen_x,
        topMargin=20 * mm,
        bottomMargin=16 * mm,
        title=f"Planilla de jugadores - {equipo.nombre}",
        author=nombre_liga,
    )

    # ---------- Estilos ----------
    def estilo(nombre, **kw):
        base = dict(fontName=f_normal, fontSize=10, leading=12, textColor=PDF_NEGRO, alignment=TA_LEFT)
        base.update(kw)
        return ParagraphStyle(nombre, **base)

    est_titulo = estilo("TituloLiga", fontName=f_titulo, fontSize=20, leading=23, spaceAfter=2)
    est_liga = estilo("NombreLigaHeader", fontSize=10.5, leading=13, textColor=PDF_GRIS, spaceAfter=4)
    est_club = estilo("NombreClub", fontName=f_titulo, fontSize=17, leading=20, textColor=PDF_DORADO, spaceBefore=3)
    est_celda = estilo("CeldaLiga")
    est_enc = estilo("EncabezadoLiga")
    est_enc_centro = estilo("EncabezadoCentrado", alignment=TA_CENTER)

    # ---------- Jugadores ----------
    jugadores = lista_jugadores.all() if hasattr(lista_jugadores, "all") else lista_jugadores
    jugadores = list(jugadores)

    # ---------- Encabezado con logo del equipo ----------
    texto_encabezado = [
        Paragraph("LISTADO OFICIAL DE JUGADORES", est_titulo),
        Paragraph(f"<b>{nombre_liga}</b>", est_liga),
        Spacer(1, 2 * mm),
        Paragraph(equipo.nombre, est_club),
    ]

    logo_encabezado = ""
    url_logo_equipo = _url_logo(equipo)
    datos_logo = _descargar_bytes(url_logo_equipo) if url_logo_equipo else None
    if datos_logo:
        try:
            imagen_logo = ReportLabImage(BytesIO(datos_logo), width=20 * mm, height=20 * mm, kind="proportional")
            logo_encabezado = Table([[imagen_logo]], colWidths=[26 * mm], rowHeights=[26 * mm], hAlign="CENTER")
            logo_encabezado.setStyle(TableStyle([
                ("BOX", (0, 0), (-1, -1), 1, PDF_DORADO),
                ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ]))
        except Exception:
            logger.warning("[PDF] Logo del equipo inválido.", exc_info=True)
            logo_encabezado = ""

    encabezado = Table([[texto_encabezado, logo_encabezado]], colWidths=[ancho_util - 28 * mm, 28 * mm], hAlign="CENTER")
    encabezado.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (0, 0), "CENTER"),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))

    elementos = [encabezado, Spacer(1, 5 * mm)]

    # ---------- Tabla ----------
    cabecera = [
        Paragraph("<b>N°</b>", est_enc),
        Paragraph("<b>Apellido<br/>Paterno</b>", est_enc),
        Paragraph("<b>Apellido<br/>Materno</b>", est_enc),
        Paragraph("<b>Nombres</b>", est_enc_centro),
    ]
    if mostrar_rut:
        cabecera.append(Paragraph("<b>RUT</b>", est_enc_centro))
    cabecera += [
        Paragraph("<b>Fecha de<br/>Nacimiento</b>", est_enc),
        Paragraph("<b>Fecha de<br/>Inscripción</b>", est_enc),
    ]
    datos = [cabecera]

    if not jugadores:
        datos.append(
            [Paragraph("No hay jugadores registrados para este equipo.", est_celda)] + [""] * (len(cabecera) - 1)
        )
    else:
        for n, jugador in enumerate(jugadores, start=1):
            nombre_completo = str(getattr(jugador, "nombre", None) or "-").strip()
            nombres, ap_pat, ap_mat = _separar_nombre(nombre_completo)

            fila = [
                Paragraph(str(n), est_celda),
                Paragraph(ap_pat, est_celda),
                Paragraph(ap_mat, est_celda),
                Paragraph(nombres, est_celda),
            ]
            if mostrar_rut:
                fila.append(Paragraph(str(getattr(jugador, "rut_formateado", None) or "-"), est_celda))
            fila += [
                Paragraph(_fecha_texto(getattr(jugador, "fecha_nacimiento", None)), est_celda),
                Paragraph(_fecha_texto(getattr(jugador, "fecha_inscripcion", None)), est_celda),
            ]
            datos.append(fila)

    if mostrar_rut:
        proporciones = [0.05, 0.15, 0.15, 0.19, 0.16, 0.15, 0.15]
    else:
        proporciones = [0.06, 0.18, 0.18, 0.28, 0.15, 0.15]

    tabla = Table(datos, colWidths=[ancho_util * p for p in proporciones], repeatRows=1, hAlign="CENTER")
    comandos = [
        ("BACKGROUND", (0, 0), (-1, 0), PDF_GRIS_CLARO),
        ("BOX", (0, 0), (-1, -1), 0.7, PDF_GRIS),
        ("INNERGRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#BBBBBB")),
        ("LINEBELOW", (0, 0), (-1, 0), 1.2, PDF_DORADO),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    if not jugadores:
        comandos.append(("SPAN", (0, 1), (-1, 1)))
    tabla.setStyle(TableStyle(comandos))

    elementos += [tabla, Spacer(1, 4 * mm)]

    # ---------- Decoración de cada página ----------
    marca_agua = _marca_agua_pdf(liga)   # se descarga y procesa una sola vez

    def dibujar_pagina(canvas, documento):
        canvas.saveState()
        canvas.setFillColor(colors.white)
        canvas.rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, fill=1, stroke=0)

        if marca_agua:
            try:
                ancho_px, alto_px = marca_agua.getSize()
                ancho_dest = 160 * mm
                alto_dest = alto_px * ancho_dest / ancho_px
                canvas.drawImage(
                    marca_agua,
                    (PAGE_WIDTH - ancho_dest) / 2,
                    (PAGE_HEIGHT - alto_dest) / 2,
                    width=ancho_dest,
                    height=alto_dest,
                    mask="auto",
                )
            except Exception:
                logger.warning("[PDF] Error dibujando la marca de agua.", exc_info=True)

        canvas.setStrokeColor(PDF_DORADO)
        canvas.setLineWidth(1)
        canvas.line(margen_x, PAGE_HEIGHT - 11 * mm, PAGE_WIDTH - margen_x, PAGE_HEIGHT - 11 * mm)

        canvas.setFont(f_normal, 7)
        canvas.setFillColor(PDF_GRIS)
        canvas.drawString(margen_x, 8 * mm, nombre_liga)
        canvas.drawRightString(PAGE_WIDTH - margen_x, 8 * mm, f"Página {documento.page}")
        canvas.restoreState()

    doc.build(elementos, onFirstPage=dibujar_pagina, onLaterPages=dibujar_pagina)

    # ---------- Respuesta ----------
    nombre_archivo = re.sub(r"[^\w\-]+", "_", str(equipo.nombre)).strip("_") or "equipo"
    response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="planilla_{nombre_archivo}.pdf"'
    return response