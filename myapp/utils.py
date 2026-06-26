import os
import re
from datetime import date

from dateutil.relativedelta import relativedelta
from django.core.exceptions import ValidationError
from django.core.validators import validate_email as django_validate_email


LETTERS = "A-Za-zÁÉÍÓÚáéíóúÑñÜü"


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

def validate_google_maps_iframe(iframe):
    iframe = (iframe or "").strip()

    if iframe and (
        "<iframe" not in iframe.lower()
        or "google.com/maps/embed" not in iframe.lower()
    ):
        raise ValidationError(
            "Debes pegar un iframe válido de Google Maps."
        )

    return iframe