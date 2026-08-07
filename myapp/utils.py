import os
import re
from datetime import date

from dateutil.relativedelta import relativedelta
from django.core.exceptions import ValidationError
from django.core.validators import validate_email as django_validate_email
from decimal import Decimal, InvalidOperation

from io import BytesIO

from django.http import HttpResponse
from PIL import Image, ImageDraw, ImageFont

from django.conf import settings
from django.contrib.staticfiles import finders

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
ruta_titulo = finders.find("fonts/ARIALBD.TTF")
ruta_normal = finders.find("fonts/ARIAL.TTF")


def crear_img_tabla(torneo, tabla_posiciones):
    alto_fila = 45
    alto_inicio = 220

    ALTO = alto_inicio + (len(tabla_posiciones) * alto_fila) + 50
    
    imagen = Image.new(
        "RGB",
        (ANCHO, ALTO),
        "#202020"
    )

    draw = ImageDraw.Draw(imagen)

    print("TITULO:", ruta_titulo)
    print("NORMAL:", ruta_normal)

    fuente_titulo = ImageFont.truetype(
        ruta_titulo,
        38
    )

    cantidad_equipos = len(tabla_posiciones)

    if cantidad_equipos <= 12:
        fuente_normal = ImageFont.truetype(ruta_normal, 24)
    elif cantidad_equipos <= 20:
        fuente_normal = ImageFont.truetype(ruta_normal, 20)
    else:
        fuente_normal = ImageFont.truetype(ruta_normal, 16)

    draw.text(

        (40,40),

        "Liga Rural",

        fill="gold",

        font=fuente_titulo

    )
    draw.text(

        (40,90),

        torneo.nombre,

        fill="white",

        font=fuente_normal

    )
    draw.line(

    (40,140,860,140),

    fill="gold",

    width=3

    )
    y = 170

    draw.text((40,y),"Pos",fill="gold",font=fuente_normal)
    draw.text((110,y),"Club",fill="gold",font=fuente_normal)
    draw.text((520,y),"PJ",fill="gold",font=fuente_normal)
    draw.text((600,y),"DG",fill="gold",font=fuente_normal)
    draw.text((700,y),"PTS",fill="gold",font=fuente_normal)
    y = 220

    for posicion, fila in enumerate(tabla_posiciones, start=1):

        draw.text(
            (40,y),
            str(posicion),
            fill="white",
            font=fuente_normal
        )

        draw.text(
            (110,y),
            fila["equipo"].nombre,
            fill="white",
            font=fuente_normal
        )

        draw.text(
            (530,y),
            str(fila["pj"]),
            fill="white",
            font=fuente_normal
        )

        draw.text(
            (610,y),
            str(fila["dg"]),
            fill="white",
            font=fuente_normal
        )

        draw.text(
            (710,y),
            str(fila["pts"]),
            fill="gold",
            font=fuente_normal
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
        'attachment; filename="tabla.png"'
    )

    return response


def _texto_ajustado(draw, texto, fuente, ancho_maximo):
    texto = str(texto or "-")

    if draw.textlength(texto, font=fuente) <= ancho_maximo:
        return texto

    while texto and draw.textlength(f"{texto}...", font=fuente) > ancho_maximo:
        texto = texto[:-1]

    return f"{texto}..." if texto else "-"


def crear_img_fechas(torneo, partidos):
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
        f"Fechas - {torneo.nombre}",
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
        ("Partidos", 40, 160),
        ("Cancha", 400, 150),
        ("Fecha y Hora", 650, 90),
    ]

    for titulo, x, _ancho in columnas:
        draw.text((x, y), titulo, fill="gold", font=fuente_pequena)

    y = 210

    if not partidos:
        draw.text(
            (40, y),
            "No hay fechas registradas para este torneo.",
            fill="white",
            font=fuente_normal
        )
    else:
        for partido in partidos:
            print(partido.estado)
            if partido.estado == 'Programado':
                valores = [
                    (f"{partido.equipo_local} v/s {partido.equipo_visitante}", 40, 250),
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
        'attachment; filename="fechas.png"'
    )

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
    
def crear_imagen_detalle_equipo(equipo, lista_jugadores):
    alto = max(360, 230 + (lista_jugadores.count() * 45))
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
        f"Listado - {equipo.nombre}",
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
        ("Nombre", 40, 300),
        ("Rut", 340, 200),
        ("C. Emerg.", 480, 200),
        ("F.Inscrip.", 650, 200),
    ]

    for titulo, x, _ancho in columnas:
        draw.text((x, y), titulo, fill="gold", font=fuente_pequena)

    y = 210

    if not lista_jugadores:
        draw.text(
            (40, y),
            "No hay jugadores registrados para este equipo.",
            fill="white",
            font=fuente_normal
        )
    else:
        for jugador in lista_jugadores:
                valores = [
                    (jugador.nombre, 40, 300),
                    (jugador.rut or "-", 340, 200),
                    (jugador.contacto_emergencia, 480, 200),
                    (jugador.fecha_inscripcion, 650, 200),
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
        f'attachment; filename="planilla_{equipo.nombre}.png"'
    )

    return response