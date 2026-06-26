from django import forms
from django.core.exceptions import ValidationError
from django.forms import BaseInlineFormSet, inlineformset_factory

from .models import Arbitro, Dirigente, Equipo, Jugador, Liga, RedSocial, Traspaso, Cancha, Partido
from .utils import (
    calculate_age,
    validate_address,
    validate_birth_date,
    validate_blood_type,
    validate_date_not_future,
    validate_email,
    validate_entity_name,
    validate_file_upload,
    validate_person_name,
    validate_phone,
    validate_rut,
    validate_social_link,
    validate_text,
    validate_textarea,
    validate_transfer_date,
    validate_unique_value,
)
import re

class RedSocialForm(forms.ModelForm):
    class Meta:
        model = RedSocial
        fields = ["tipo", "enlace"]
        labels = {
            "tipo": "RED SOCIAL",
            "enlace": "ENLACE O USUARIO",
        }

    def clean(self):
        cleaned_data = super().clean()
        tipo = cleaned_data.get("tipo")
        enlace = cleaned_data.get("enlace")

        if not tipo and not enlace:
            return cleaned_data

        if tipo and not enlace:
            self.add_error("enlace", "Debes ingresar el enlace o usuario.")

        if enlace and not tipo:
            self.add_error("tipo", "Debes seleccionar una red social.")

        if enlace:
            cleaned_data["enlace"] = validate_social_link(enlace)

        return cleaned_data


class BaseRedSocialFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        redes = set()

        for form in self.forms:
            if not hasattr(form, "cleaned_data"):
                continue

            if form.cleaned_data.get("DELETE"):
                continue

            tipo = form.cleaned_data.get("tipo")
            enlace = form.cleaned_data.get("enlace")

            if not tipo and not enlace:
                continue

            clave = (tipo, enlace.lower())
            if clave in redes:
                raise ValidationError("No puedes repetir la misma red social.")

            redes.add(clave)


EquipoRedSocialFormSet = inlineformset_factory(
    Equipo,
    RedSocial,
    form=RedSocialForm,
    formset=BaseRedSocialFormSet,
    fields=["tipo", "enlace"],
    extra=20,
    max_num=20,
    can_delete=True,
)


LigaRedSocialFormSet = inlineformset_factory(
    Liga,
    RedSocial,
    form=RedSocialForm,
    formset=BaseRedSocialFormSet,
    fields=["tipo", "enlace"],
    extra=20,
    max_num=20,
    can_delete=True,
)


class Ingresar_Jugadores(forms.ModelForm):
    class Meta:
        model = Jugador
        fields = [
            "nombre",
            "rut",
            "fecha_nacimiento",
            "telefono",
            "contacto_emergencia",
            "equipo",
            "fecha_inscripcion",
            "adulto_responsable",
            "tipo_sangre",
            "tiene_seguro",
            "alergias",
            "certificado_medico",
        ]
        labels = {
            "nombre": "NOMBRE",
            "rut": "RUT",
            "fecha_nacimiento": "FECHA DE NACIMIENTO",
            "telefono": "TELEFONO",
            "contacto_emergencia": "CONTACTO DE EMERGENCIA",
            "equipo": "EQUIPO",
            "fecha_inscripcion": "FECHA DE INSCRIPCION",
            "adulto_responsable": "ADULTO RESPONSABLE",
            "tipo_sangre": "TIPO DE SANGRE",
            "tiene_seguro": "TIENE SEGURO?",
            "alergias": "ALERGIAS",
            "certificado_medico": "CERTIFICADO MEDICO",
        }

    def clean_nombre(self):
        return validate_person_name(self.cleaned_data.get("nombre"), "un nombre")

    def clean_rut(self):
        return validate_rut(
            self.cleaned_data.get("rut"),
            model=Jugador,
            instance=self.instance,
            duplicate_message="Ya existe otro jugador con este RUT.",
        )

    def clean_fecha_nacimiento(self):
        return validate_birth_date(self.cleaned_data.get("fecha_nacimiento"))

    def clean_fecha_inscripcion(self):
        return validate_date_not_future(
            self.cleaned_data.get("fecha_inscripcion"),
            "La fecha de inscripcion",
            required=True,
            max_age_years=100,
        )

    def clean_telefono(self):
        return validate_phone(self.cleaned_data.get("telefono"), field_name="telefono")

    def clean_contacto_emergencia(self):
        return validate_phone(
            self.cleaned_data.get("contacto_emergencia"),
            field_name="telefono de emergencia",
        )

    def clean_adulto_responsable(self):
        responsable = self.cleaned_data.get("adulto_responsable")
        fecha = self.cleaned_data.get("fecha_nacimiento")
        edad = calculate_age(fecha)

        return validate_person_name(
            responsable,
            "un adulto responsable",
            required=edad is not None and edad < 18,
            min_length=5,
            max_length=200,
        )

    def clean_tipo_sangre(self):
        return validate_blood_type(self.cleaned_data.get("tipo_sangre"))

    def clean_alergias(self):
        return validate_textarea(
            self.cleaned_data.get("alergias"),
            "alergias",
            required=False,
            max_length=500,
        )

    def clean_certificado_medico(self):
        return validate_file_upload(
            self.cleaned_data.get("certificado_medico"),
            allowed_extensions=["pdf", "jpg", "jpeg", "png"],
            max_size_mb=5,
            field_name="El certificado medico",
        )


class Ingresar_Arbitros(forms.ModelForm):
    class Meta:
        model = Arbitro
        fields = [
            "nombre",
            "apellido",
            "rut",
            "fecha_nacimiento",
            "telefono",
            "contacto_emergencia",
            "correo",
            "direccion",
            "categoria",
            "experiencia",
            "estado",
            "tipo_sangre",
            "tiene_seguro",
            "alergias",
            "certificado_medico",
        ]
        labels = {
            "nombre": "NOMBRE",
            "apellido": "APELLIDO",
            "rut": "RUT",
            "fecha_nacimiento": "FECHA DE NACIMIENTO",
            "telefono": "TELEFONO",
            "contacto_emergencia": "CONTACTO DE EMERGENCIA",
            "correo": "CORREO",
            "direccion": "DIRECCIÓN",
            "categoria": "CATEGORÍA",
            "experiencia": "AÑOS DE EXPERIENCIA",
            "estado": "ACTIVO",
            "tipo_sangre": "TIPO DE SANGRE",
            "tiene_seguro": "¿TIENE SEGURO?",
            "alergias": "ALERGÍAS",
            "certificado_medico": "CERTIFICADO MÉDICO",
        }
        widgets = {
            "fecha_nacimiento": forms.DateInput(attrs={"type": "date"}),
        }

    def clean_nombre(self):
        return validate_person_name(self.cleaned_data.get("nombre"), "un nombre")

    def clean_apellido(self):
        return validate_person_name(self.cleaned_data.get("apellido"), "un apellido")

    def clean_rut(self):
        return validate_rut(
            self.cleaned_data.get("rut"),
            model=Arbitro,
            instance=self.instance,
            duplicate_message="Ya existe otro arbitro con este RUT.",
        )

    def clean_fecha_nacimiento(self):
        return validate_birth_date(
            self.cleaned_data.get("fecha_nacimiento"),
            min_age=14,
            max_age=100,
            required=True,
        )

    def clean_telefono(self):
        return validate_phone(self.cleaned_data.get("telefono"), field_name="telefono")

    def clean_contacto_emergencia(self):
        return validate_phone(
            self.cleaned_data.get("contacto_emergencia"),
            field_name="telefono de emergencia",
        )

    def clean_correo(self):
        return validate_email(self.cleaned_data.get("correo"))

    def clean_direccion(self):
        return validate_address(self.cleaned_data.get("direccion"), required=False)

    def clean_experiencia(self):
        experiencia = self.cleaned_data.get("experiencia")

        if experiencia is None:
            return 0

        if experiencia < 0:
            raise ValidationError("La experiencia no puede ser negativa.")

        if experiencia > 80:
            raise ValidationError("La experiencia ingresada no es realista.")

        return experiencia

    def clean_tipo_sangre(self):
        return validate_blood_type(self.cleaned_data.get("tipo_sangre"))

    def clean_alergias(self):
        return validate_textarea(
            self.cleaned_data.get("alergias"),
            "alergias",
            required=False,
            max_length=500,
        )

    def clean_certificado_medico(self):
        return validate_file_upload(
            self.cleaned_data.get("certificado_medico"),
            allowed_extensions=["pdf", "jpg", "jpeg", "png"],
            max_size_mb=5,
            field_name="El certificado medico",
        )


class Ingresar_Equipos(forms.ModelForm):
    class Meta:
        model = Equipo
        fields = [
            "nombre",
            "fecha_creacion",
            "nombre_entrenador",
            "nombre_dueno",
            "liga",
        ]
        labels = {
            "nombre": "NOMBRE DEL EQUIPO",
            "fecha_creacion": "FECHA DE CREACION",
            "nombre_entrenador": "NOMBRE DEL ENTRENADOR",
            "nombre_dueno": "NOMBRE DEL DUENO",
            "liga": "LIGA",
        }

    def clean_nombre(self):
        nombre = validate_entity_name(
            self.cleaned_data.get("nombre"),
            "nombre del equipo",
            max_length=50,
        )
        return validate_unique_value(
            Equipo,
            "nombre",
            nombre,
            instance=self.instance,
            message="Ya existe un equipo con ese nombre.",
            iexact=True,
        )

    def clean_fecha_creacion(self):
        return validate_date_not_future(
            self.cleaned_data.get("fecha_creacion"),
            "La fecha de creacion",
            required=True,
            max_age_years=150,
        )

    def clean_nombre_entrenador(self):
        return validate_person_name(
            self.cleaned_data.get("nombre_entrenador"),
            "el nombre del entrenador",
        )

    def clean_nombre_dueno(self):
        return validate_person_name(
            self.cleaned_data.get("nombre_dueno"),
            "el nombre del dueno",
        )

class Ingresar_Dirigentes(forms.ModelForm):
    class Meta:
        model = Dirigente
        fields = [
            "nombre",
            "rut",
            "telefono",
            "correo",
            "cargo",
            "direccion",
            "fecha_asuncion",
            "activo",
            "equipo",
        ]
        labels = {
            "nombre": "NOMBRE",
            "rut": "RUT",
            "telefono": "TELEFONO",
            "correo": "CORREO ELECTRONICO",
            "cargo": "CARGO",
            "direccion": "DIRECCION",
            "fecha_asuncion": "FECHA DE ASUNCION",
            "activo": "ACTIVO",
            "equipo": "EQUIPO",
        }

    def clean_nombre(self):
        return validate_person_name(self.cleaned_data.get("nombre"), "un nombre")

    def clean_rut(self):
        return validate_rut(
            self.cleaned_data.get("rut"),
            model=Dirigente,
            instance=self.instance,
            duplicate_message="Ya existe otro dirigente con este RUT.",
        )

    def clean_telefono(self):
        return validate_phone(self.cleaned_data.get("telefono"), field_name="telefono")

    def clean_correo(self):
        correo = validate_email(self.cleaned_data.get("correo"))
        validate_unique_value(
            Dirigente,
            "correo",
            correo,
            instance=self.instance,
            message="Ya existe otro dirigente con este correo.",
            iexact=True,
        )

        usuario = getattr(self.instance, "usuario", None)
        if self.instance.pk and usuario and usuario.email:
            if correo != usuario.email.strip().lower():
                raise ValidationError(
                    "No puedes cambiar el correo de un dirigente que ya tiene usuario asociado."
                )

        return correo

    def clean_cargo(self):
        return validate_text(
            self.cleaned_data.get("cargo"),
            "un cargo",
            min_length=3,
            max_length=50,
            allow_numbers=False,
            allowed_symbols=r"\-",
        )

    def clean_direccion(self):
        return validate_address(self.cleaned_data.get("direccion"), required=False)

    def clean_fecha_asuncion(self):
        return validate_date_not_future(
            self.cleaned_data.get("fecha_asuncion"),
            "La fecha de asuncion",
            required=False,
            max_age_years=100,
        )


class Editar_Dirigentes(Ingresar_Dirigentes):
    class Meta(Ingresar_Dirigentes.Meta):
        pass


class Realizar_Traspasos(forms.ModelForm):
    class Meta:
        model = Traspaso
        fields = ["equipo_destino", "fecha_inscripcion_actual"]
        labels = {
            "equipo_destino": "EQUIPO DESTINO",
            "fecha_inscripcion_actual": "FECHA DE INSCRIPCION ACTUAL",
        }
        widgets = {
            "fecha_inscripcion_actual": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        self.jugador = kwargs.pop("jugador", None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        equipo_destino = cleaned_data.get("equipo_destino")
        fecha_actual = cleaned_data.get("fecha_inscripcion_actual")

        if not equipo_destino or not fecha_actual:
            return cleaned_data

        if not self.jugador:
            raise ValidationError("No se encontro el jugador para realizar el traspaso.")

        if self.jugador.equipo == equipo_destino:
            raise ValidationError("El jugador ya pertenece a ese equipo.")

        validate_transfer_date(fecha_actual, self.jugador.fecha_inscripcion)
        return cleaned_data

    def save(self, commit=True):
        traspaso = super().save(commit=False)
        jugador = self.jugador

        traspaso.jugador = jugador
        traspaso.equipo_origen = jugador.equipo
        traspaso.fecha_inscripcion_anterior = jugador.fecha_inscripcion

        if commit:
            traspaso.save()
            jugador.equipo = traspaso.equipo_destino
            jugador.fecha_inscripcion = traspaso.fecha_inscripcion_actual
            jugador.save()

        return traspaso


class Editar_Traspaso(forms.ModelForm):
    class Meta:
        model = Traspaso
        fields = ["equipo_destino", "fecha_inscripcion_actual"]
        labels = {
            "equipo_destino": "EQUIPO DESTINO",
            "fecha_inscripcion_actual": "FECHA DE INSCRIPCION ACTUAL",
        }
        widgets = {
            "fecha_inscripcion_actual": forms.DateInput(attrs={"type": "date"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        equipo_destino = cleaned_data.get("equipo_destino")
        fecha_actual = cleaned_data.get("fecha_inscripcion_actual")
        traspaso = self.instance

        if not equipo_destino or not fecha_actual:
            return cleaned_data

        if traspaso.equipo_origen == equipo_destino:
            raise ValidationError("El equipo destino no puede ser igual al equipo origen.")

        validate_transfer_date(fecha_actual, traspaso.fecha_inscripcion_anterior)
        return cleaned_data

    def save(self, commit=True):
        traspaso = super().save(commit=False)

        if commit:
            traspaso.save()
            jugador = traspaso.jugador
            jugador.equipo = traspaso.equipo_destino
            jugador.fecha_inscripcion = traspaso.fecha_inscripcion_actual
            jugador.save()

        return traspaso


class Ingresar_Liga(forms.ModelForm):
    class Meta:
        model = Liga
        fields = [
            "nombre",
            "fecha_fundacion",
            "logo",
            "comuna",
            "region",
            "direccion",
            "presidente",
            "secretario",
            "tesorero",
            "telefono_contacto",
            "correo_contacto",
            "reglamento",
        ]
        widgets = {
            "logo": forms.FileInput(attrs={"class": "form-control"}),
        }
        labels = {
            "nombre": "NOMBRE DE LA LIGA",
            "fecha_fundacion": "FECHA DE FUNDACION",
            "logo": "LOGO",
            "comuna": "COMUNA",
            "region": "REGION",
            "direccion": "DIRECCION",
            "presidente": "PRESIDENTE",
            "secretario": "SECRETARIO",
            "tesorero": "TESORERO",
            "telefono_contacto": "TELEFONO DE CONTACTO",
            "correo_contacto": "CORREO DE CONTACTO",
            "reglamento": "REGLAMENTO",
        }

    def clean_nombre(self):
        nombre = validate_entity_name(
            self.cleaned_data.get("nombre"),
            "nombre de la liga",
            max_length=50,
        )
        return validate_unique_value(
            Liga,
            "nombre",
            nombre,
            instance=self.instance,
            message="Ya existe una liga con ese nombre.",
            iexact=True,
        )

    def clean_fecha_fundacion(self):
        return validate_date_not_future(
            self.cleaned_data.get("fecha_fundacion"),
            "La fecha de fundacion",
            required=True,
            max_age_years=150,
        )

    def clean_logo(self):
        return validate_file_upload(
            self.cleaned_data.get("logo"),
            allowed_extensions=["jpg", "jpeg", "png", "webp"],
            max_size_mb=5,
            field_name="El logo",
        )

    def clean_comuna(self):
        return validate_text(self.cleaned_data.get("comuna"), "la comuna")

    def clean_region(self):
        return validate_text(self.cleaned_data.get("region"), "la region")

    def clean_direccion(self):
        return validate_address(self.cleaned_data.get("direccion"), required=False)

    def clean_presidente(self):
        return validate_person_name(
            self.cleaned_data.get("presidente"),
            "el presidente",
            required=False,
            min_length=5,
        )

    def clean_secretario(self):
        return validate_person_name(
            self.cleaned_data.get("secretario"),
            "el secretario",
            required=False,
            min_length=5,
        )

    def clean_tesorero(self):
        return validate_person_name(
            self.cleaned_data.get("tesorero"),
            "el tesorero",
            required=False,
            min_length=5,
        )

    def clean_telefono_contacto(self):
        return validate_phone(
            self.cleaned_data.get("telefono_contacto"),
            field_name="telefono",
        )

    def clean_correo_contacto(self):
        return validate_email(self.cleaned_data.get("correo_contacto"))

    def clean_reglamento(self):
        return validate_textarea(
            self.cleaned_data.get("reglamento"),
            "reglamento",
            required=False,
            max_length=3000,
        )

class Ingresar_Canchas(forms.ModelForm):

    class Meta:
        model = Cancha

        fields = [
            'nombre',
            'liga',
            'foto',
            'direccion',
            'mapa_iframe',
            'descripcion',
            'tipo_superficie',
            'capacidad',
            'iluminacion',
            'activa'
        ]

        labels = {
            'nombre': 'NOMBRE DE LA CANCHA',
            'liga': 'LIGA',
            'foto': 'FOTOGRAFÍA',
            'direccion': 'DIRECCIÓN',
            'mapa_iframe': 'MAPA DE GOOGLE',
            'descripcion': 'DESCRIPCIÓN',
            'tipo_superficie': 'TIPO DE SUPERFICIE',
            'capacidad': 'CAPACIDAD',
            'iluminacion': 'ILUMINACIÓN',
            'activa': 'ACTIVA'
        }

    def clean_nombre(self):

        nombre = self.cleaned_data.get(
            'nombre',
            ''
        ).strip()

        nombre = " ".join(nombre.split())

        if len(nombre) < 3:
            raise ValidationError(
                "El nombre es demasiado corto."
            )

        if len(nombre) > 100:
            raise ValidationError(
                "El nombre es demasiado largo."
            )

        patron = r'^[A-Za-zÁÉÍÓÚáéíóúÑñÜü0-9\s\-]+$'

        if not re.fullmatch(patron, nombre):
            raise ValidationError(
                "El nombre contiene caracteres inválidos."
            )
        
        liga = self.cleaned_data.get('liga')

        canchas = Cancha.objects.filter(
            nombre__iexact=nombre,
            liga=liga
        )

        if self.instance.pk:
            canchas = canchas.exclude(
                pk=self.instance.pk
            )

        if canchas.exists():
            raise ValidationError(
                "Ya existe una cancha con ese nombre."
            )

        return nombre.title()

    def clean_direccion(self):

        direccion = (
            self.cleaned_data.get(
                'direccion',
                ''
            ).strip()
        )

        if direccion:

            direccion = " ".join(
                direccion.split()
            )

            if len(direccion) < 5:
                raise ValidationError(
                    "La dirección es demasiado corta."
                )

            if len(direccion) > 255:
                raise ValidationError(
                    "La dirección es demasiado larga."
                )

        return direccion

    def clean_descripcion(self):

        descripcion = (
            self.cleaned_data.get(
                'descripcion',
                ''
            ).strip()
        )

        if descripcion and len(descripcion) > 1000:

            raise ValidationError(
                "La descripción es demasiado larga."
            )

        return descripcion

    def clean_capacidad(self):

        capacidad = self.cleaned_data.get(
            'capacidad'
        )

        if capacidad is not None:

            if capacidad < 0:
                raise ValidationError(
                    "La capacidad no puede ser negativa."
                )

            if capacidad > 100000:
                raise ValidationError(
                    "La capacidad ingresada no es válida."
                )

        return capacidad
    def clean_mapa_iframe(self):

        iframe = self.cleaned_data.get(
            'mapa_iframe',
            ''
        ).strip()

        if iframe and (
            '<iframe' not in iframe.lower()
            or 'google.com/maps/embed' not in iframe.lower()
        ):
            raise ValidationError(
                'Debes pegar un iframe válido de Google Maps.'
            )

        return iframe
    
# PARTIDO
class Ingresar_Partido(forms.ModelForm):

    class Meta:
        model = Partido

        fields = [
            'equipo_local',
            'equipo_visitante',
            'cancha',
            'fecha',
            'hora',
            'goles_local',
            'goles_visitante',
            'descripcion',
            'amarillas_local',
            'amarillas_visitante',
            'rojas_local',
            'rojas_visitante',
        ]

        labels = {
            'equipo_local': 'EQUIPO LOCAL',
            'equipo_visitante': 'EQUIPO VISITANTE',
            'cancha': 'CANCHA',
            'fecha': 'FECHA',
            'hora': 'HORA',
            'goles_local': 'GOLES LOCAL',
            'goles_visitante': 'GOLES VISITANTE',
            'descripcion': 'DESCRIPCION DEL PARTIDO',
            'amarillas_local': 'AMARILLAS EQUIPO LOCAL',
            'amarillas_visitante': 'AMARILLAS EQUIPO VISITANTE',
            'rojas_local': 'ROJAS EQUIPO LOCAL',
            'rojas_visitante': 'ROJAS EQUIPO VISITANTE',
        }

        widgets = {
            'fecha': forms.DateInput(
                attrs={
                    'type': 'date',
                    'min': f'{Partido.MIN_ANIO_PARTIDO}-01-01'
                }
            ),
            'hora': forms.TimeInput(
                attrs={'type': 'time'},
                format='%H:%M'
            ),
            'goles_local': forms.NumberInput(
                attrs={'min': 0, 'max': Partido.MAX_GOLES_POR_EQUIPO}
            ),
            'goles_visitante': forms.NumberInput(
                attrs={'min': 0, 'max': Partido.MAX_GOLES_POR_EQUIPO}
            ),
            'descripcion': forms.Textarea(attrs={'rows': 4}),
            'amarillas_local': forms.NumberInput(
                attrs={'min': 0, 'max': Partido.MAX_AMARILLAS_POR_EQUIPO}
            ),
            'amarillas_visitante': forms.NumberInput(
                attrs={'min': 0, 'max': Partido.MAX_AMARILLAS_POR_EQUIPO}
            ),
            'rojas_local': forms.NumberInput(
                attrs={'min': 0, 'max': Partido.MAX_ROJAS_POR_EQUIPO}
            ),
            'rojas_visitante': forms.NumberInput(
                attrs={'min': 0, 'max': Partido.MAX_ROJAS_POR_EQUIPO}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        equipos = Equipo.objects.order_by('nombre')
        self.fields['equipo_local'].queryset = equipos
        self.fields['equipo_visitante'].queryset = equipos
        self.fields['cancha'].queryset = Cancha.objects.order_by('nombre')
        self.fields['hora'].input_formats = ['%H:%M', '%H:%M:%S']

    def validar_cantidad_tarjetas(self, valor, campo, limite):
        if valor is None:
            raise ValidationError(
                f"Debes ingresar {campo}."
            )

        if valor < 0:
            raise ValidationError(
                f"{campo.capitalize()} no puede ser negativo."
            )

        if valor > limite:
            raise ValidationError(
                f"{campo.capitalize()} no puede superar {limite}."
            )

        return valor

    def validar_goles(self, valor, campo):
        if valor is None:
            return valor

        if valor < 0:
            raise ValidationError(
                f"{campo.capitalize()} no puede ser negativo."
            )

        if valor > Partido.MAX_GOLES_POR_EQUIPO:
            raise ValidationError(
                f"{campo.capitalize()} no puede superar "
                f"{Partido.MAX_GOLES_POR_EQUIPO}."
            )

        return valor

    def clean_fecha(self):
        fecha = self.cleaned_data.get('fecha')

        if fecha and fecha.year < Partido.MIN_ANIO_PARTIDO:
            raise ValidationError(
                f"No puedes ingresar un partido anterior al ano "
                f"{Partido.MIN_ANIO_PARTIDO}."
            )

        return fecha

    def clean_goles_local(self):
        return self.validar_goles(
            self.cleaned_data.get('goles_local'),
            'goles del equipo local'
        )

    def clean_goles_visitante(self):
        return self.validar_goles(
            self.cleaned_data.get('goles_visitante'),
            'goles del equipo visitante'
        )

    def clean_descripcion(self):
        descripcion = (
            self.cleaned_data.get('descripcion')
            or ''
        ).strip()

        if not descripcion:
            return ''

        if len(descripcion) > 1000:
            raise ValidationError(
                "La descripcion es demasiado larga."
            )

        patron = (
            r'^[A-Za-z0-9\u00C0-\u017F\s\.\,\;\:\!\?\u00A1'
            r'\u00BF\(\)\/"\'\-]+$'
        )

        if not re.fullmatch(patron, descripcion):
            raise ValidationError(
                "La descripcion contiene caracteres no permitidos."
            )

        return descripcion

    def clean_amarillas_local(self):
        return self.validar_cantidad_tarjetas(
            self.cleaned_data.get('amarillas_local'),
            'amarillas del equipo local',
            Partido.MAX_AMARILLAS_POR_EQUIPO
        )

    def clean_amarillas_visitante(self):
        return self.validar_cantidad_tarjetas(
            self.cleaned_data.get('amarillas_visitante'),
            'amarillas del equipo visitante',
            Partido.MAX_AMARILLAS_POR_EQUIPO
        )

    def clean_rojas_local(self):
        return self.validar_cantidad_tarjetas(
            self.cleaned_data.get('rojas_local'),
            'rojas del equipo local',
            Partido.MAX_ROJAS_POR_EQUIPO
        )

    def clean_rojas_visitante(self):
        return self.validar_cantidad_tarjetas(
            self.cleaned_data.get('rojas_visitante'),
            'rojas del equipo visitante',
            Partido.MAX_ROJAS_POR_EQUIPO
        )

    def clean(self):
        cleaned_data = super().clean()

        equipo_local = cleaned_data.get('equipo_local')
        equipo_visitante = cleaned_data.get('equipo_visitante')
        cancha = cleaned_data.get('cancha')
        goles_local = cleaned_data.get('goles_local')
        goles_visitante = cleaned_data.get('goles_visitante')

        if (
            equipo_local
            and equipo_visitante
            and equipo_local == equipo_visitante
        ):
            raise ValidationError(
                "El equipo local y el equipo visitante no pueden ser el mismo."
            )

        if cancha and equipo_local and equipo_visitante:
            ligas_equipos = {
                equipo_local.liga_id,
                equipo_visitante.liga_id,
            }

            if cancha.liga_id not in ligas_equipos:
                self.add_error(
                    'cancha',
                    "La cancha debe pertenecer a la liga de uno de los equipos."
                )

        if (goles_local is None) != (goles_visitante is None):
            raise ValidationError(
                "Debes ingresar goles locales y visitantes, o dejar ambos vacios."
            )

        return cleaned_data

