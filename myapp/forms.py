from django import forms
from django.core.exceptions import ValidationError
from django.forms import BaseInlineFormSet, inlineformset_factory

from .models import Arbitro, Dirigente, Equipo, Jugador, Liga, RedSocial, Traspaso, Cancha, Partido, TarjetaPartido, Torneo
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
    validate_integer_range,
    validate_decimal_range
)
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
        return validate_phone(self.cleaned_data.get("telefono"), field_name="telefono", required=False)

    def clean_contacto_emergencia(self):
        return validate_phone(
            self.cleaned_data.get("contacto_emergencia"),
            field_name="telefono de emergencia",
            required=False
        )

    def clean_adulto_responsable(self):
        responsable = self.cleaned_data.get("adulto_responsable")
        fecha = self.cleaned_data.get("fecha_nacimiento")
        edad = calculate_age(fecha)

        return validate_person_name(
            responsable,
            "un adulto responsable",
            required=False, #required=edad is not None and edad < 18,
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
            "logo",
            "nombre_entrenador",
            "nombre_dueno",
            "liga",
        ]
        labels = {
            "nombre": "NOMBRE DEL EQUIPO",
            "fecha_creacion": "FECHA DE CREACIÓN",
            "logo": "LOGO",
            "nombre_entrenador": "NOMBRE DEL ENTRENADOR",
            "nombre_dueno": "NOMBRE DEL DUEÑO",
            "liga": "LIGA",
        }
        widgets = {
            "logo": forms.FileInput(attrs={"class": "form-control"}),
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

    def clean_logo(self):
        return validate_file_upload(
            self.cleaned_data.get("logo"),
            allowed_extensions=["jpg", "jpeg", "png", "webp"],
            max_size_mb=5,
            field_name="El logo",
        )

    def clean_nombre_entrenador(self):
        return validate_person_name(
            self.cleaned_data.get("nombre_entrenador"),
            "el nombre del entrenador",
            required=False
        )

    def clean_nombre_dueno(self):
        return validate_person_name(
            self.cleaned_data.get("nombre_dueno"),
            "el nombre del dueno",
            required=False
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
        logo_nuevo = self.files.get("logo")

        # Si no se subió un logo nuevo, conservar el actual
        if not logo_nuevo:
            return self.instance.logo

        return validate_file_upload(
            logo_nuevo,
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
    foto = forms.ImageField(
        required=False,
        label="Fotografía",
        widget=forms.FileInput(
            attrs={
                "accept": "image/*"
            }
        )
    )
    largo_metros = forms.IntegerField(
        widget=forms.NumberInput(
            attrs={
                "min": 60,
                "max": 150
            }
        )
    )

    ancho_metros = forms.IntegerField(
        widget=forms.NumberInput(
            attrs={
                "min": 30,
                "max": 105
            }
        )
    )    
    capacidad_minima = forms.IntegerField(
        widget=forms.NumberInput(
            attrs={
                "min": 1,
                "max": 100000
            }
        )
    )

    capacidad_maxima = forms.IntegerField(
        widget=forms.NumberInput(
            attrs={
                "min": 1,
                "max": 100000
            }
        )
    )
    class Meta:
        model = Cancha
        

        fields = [
            'nombre',
            'liga',
            'foto',
            'direccion',
            'descripcion',
            'tipo_superficie',
            'capacidad_minima',
            'capacidad_maxima',
            'largo_metros',
            'ancho_metros',
            'iluminacion',
            'activa',
            'latitud',
            'longitud'
        ]

        labels = {
            'nombre': 'NOMBRE DE LA CANCHA',
            'liga': 'LIGA',
            'foto': 'FOTOGRAFÍA',
            'direccion': 'DIRECCIÓN',
            'descripcion': 'DESCRIPCIÓN',
            'tipo_superficie': 'TIPO DE SUPERFICIE',
            'capacidad_minima': 'CAPACIDAD MÍNIMA',
            'capacidad_maxima': 'CAPACIDAD MÁXIMA',
            'largo_metros': 'LARGO (m)',
            'ancho_metros': 'ANCHO (m)',
            'iluminacion': 'ILUMINACIÓN',
            'activa': 'ACTIVA',
            'latitud': 'LATITUD',
            'longitud': 'LONGITUD',
        }

    def clean_nombre(self):
        nombre = validate_entity_name(
            self.cleaned_data.get("nombre"),
            "nombre de la cancha",
            max_length=100
        )

        return validate_unique_value(
            Cancha,
            "nombre",
            nombre,
            instance=self.instance,
            filters={"liga": self.cleaned_data.get("liga")},
            message="Ya existe una cancha con ese nombre.",
            iexact=True,
        )

    def clean_direccion(self):
        return validate_address(
            self.cleaned_data.get("direccion"),
            required=False
        )

    def clean_descripcion(self):
        return validate_textarea(
            self.cleaned_data.get("descripcion"),
            "descripción",
            required=False,
            max_length=1000,
        )

    def clean_capacidad_minima(self):
        return validate_integer_range(
            self.cleaned_data.get("capacidad_minima"),
            "la capacidad mínima",
            minimum=1,
            maximum=100000,
            required=True,
        )

    def clean_capacidad_maxima(self):
        return validate_integer_range(
            self.cleaned_data.get("capacidad_maxima"),
            "la capacidad máxima",
            minimum=1,
            maximum=100000,
            required=True,
        )

    def clean_largo_metros(self):
        return validate_decimal_range(
            self.cleaned_data.get("largo_metros"),
            "el largo de la cancha",
            minimum=1,
            maximum=1000,
            required=False,
        )

    def clean_ancho_metros(self):
        return validate_decimal_range(
            self.cleaned_data.get("ancho_metros"),
            "el ancho de la cancha",
            minimum=1,
            maximum=1000,
            required=False,
        )

    def clean(self):
        cleaned_data = super().clean()

        capacidad_minima = cleaned_data.get("capacidad_minima")
        capacidad_maxima = cleaned_data.get("capacidad_maxima")

        if (
            capacidad_minima is not None
            and capacidad_maxima is not None
            and capacidad_minima > capacidad_maxima
        ):
            self.add_error(
                "capacidad_maxima",
                "La capacidad máxima debe ser mayor o igual a la capacidad mínima."
            )

        return cleaned_data


class Ingresar_Torneo(forms.ModelForm):
    equipos = forms.ModelMultipleChoiceField(
        queryset=Equipo.objects.select_related("liga").order_by("liga__nombre", "nombre"),
        widget=forms.MultipleHiddenInput,
        label="EQUIPOS PARTICIPANTES",
    )

    class Meta:
        model = Torneo
        fields = [
            "nombre",
            "fecha_inicio",
            "fecha_fin",
            "equipos",
        ]
        labels = {
            "nombre": "NOMBRE DEL TORNEO",
            "fecha_inicio": "FECHA DE INICIO",
            "fecha_fin": "FECHA DE TERMINO",
        }
        widgets = {
            "fecha_inicio": forms.DateInput(attrs={"type": "date"}),
            "fecha_fin": forms.DateInput(attrs={"type": "date"}),
        }

    def clean_nombre(self):
        nombre = validate_text(
            self.cleaned_data.get("nombre"),
            "nombre del torneo",
            max_length=100,
            allowed_symbols=r"\-\/",
        )
        return validate_unique_value(
            Torneo,
            "nombre",
            nombre,
            instance=self.instance,
            message="Ya existe un torneo con ese nombre.",
            iexact=True,
        )

    def clean(self):
        cleaned_data = super().clean()
        fecha_inicio = cleaned_data.get("fecha_inicio")
        fecha_fin = cleaned_data.get("fecha_fin")
        equipos = cleaned_data.get("equipos")

        if fecha_inicio and fecha_fin and fecha_inicio > fecha_fin:
            self.add_error(
                "fecha_fin",
                "La fecha de termino debe ser igual o posterior a la fecha de inicio."
            )

        if equipos is not None and equipos.count() < 2:
            self.add_error(
                "equipos",
                "Un torneo formato liga debe tener al menos dos equipos."
            )

        return cleaned_data


# PARTIDO
class Programar_Partido(forms.ModelForm):

    class Meta:

        model = Partido

        fields = [
            'torneo',
            'equipo_local',
            'equipo_visitante',
            'cancha',
            'fecha',
            'hora',
            'descripcion',
        ]

        labels = {
            'torneo': 'TORNEO',
            'equipo_local': 'EQUIPO LOCAL',
            'equipo_visitante': 'EQUIPO VISITANTE',
            'cancha': 'CANCHA',
            'fecha': 'FECHA',
            'hora': 'HORA',
            'descripcion': 'DESCRIPCIÓN DEL PARTIDO',
        }

        widgets = {

            'fecha': forms.DateInput(
                attrs={
                    'type': 'date',
                    'min': f'{Partido.MIN_ANIO_PARTIDO}-01-01'
                }
            ),

            'hora': forms.TimeInput(
                attrs={
                    'type':'time'
                },
                format='%H:%M'
            ),

            'descripcion': forms.Textarea(
                attrs={
                    'rows':4
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        torneo = None

        if self.is_bound:
            torneo_id = self.data.get(self.add_prefix("torneo"))

            if torneo_id:
                try:
                    torneo = Torneo.objects.get(pk=torneo_id)
                except (Torneo.DoesNotExist, ValueError):
                    torneo = None
        elif self.instance and self.instance.pk:
            torneo = self.instance.torneo

        if torneo:
            equipos = torneo.equipos.order_by("nombre")
            self.fields["equipo_local"].queryset = equipos
            self.fields["equipo_visitante"].queryset = equipos

        self.fields["torneo"].queryset = Torneo.objects.prefetch_related("equipos").all()

    def clean(self):
        cleaned_data = super().clean()
        torneo = cleaned_data.get("torneo")
        equipo_local = cleaned_data.get("equipo_local")
        equipo_visitante = cleaned_data.get("equipo_visitante")
        fecha = cleaned_data.get("fecha")

        if not torneo:
            self.add_error("torneo", "Debes seleccionar un torneo.")
            return cleaned_data

        if equipo_local and equipo_visitante and equipo_local == equipo_visitante:
            self.add_error(
                "equipo_visitante",
                "El equipo visitante debe ser distinto al equipo local."
            )

        if fecha and (fecha < torneo.fecha_inicio or fecha > torneo.fecha_fin):
            self.add_error(
                "fecha",
                "La fecha del partido debe estar dentro del periodo del torneo."
            )

        equipos_torneo = torneo.equipos.all()

        if equipo_local and not equipos_torneo.filter(pk=equipo_local.pk).exists():
            self.add_error(
                "equipo_local",
                "El equipo local no pertenece al torneo seleccionado."
            )

        if equipo_visitante and not equipos_torneo.filter(pk=equipo_visitante.pk).exists():
            self.add_error(
                "equipo_visitante",
                "El equipo visitante no pertenece al torneo seleccionado."
            )

        return cleaned_data


class Ingresar_Partido(Programar_Partido):
    pass


class Registrar_Resultado_Partido(forms.Form):
    partido = forms.ModelChoiceField(
        queryset=Partido.objects.none(),
        label="FECHA PROGRAMADA",
        empty_label="Selecciona una fecha"
    )
    goles_local = forms.IntegerField(
        label="GOLES LOCAL",
        min_value=0,
        max_value=Partido.MAX_GOLES_POR_EQUIPO,
    )
    goles_visitante = forms.IntegerField(
        label="GOLES VISITANTE",
        min_value=0,
        max_value=Partido.MAX_GOLES_POR_EQUIPO,
    )
    descripcion = forms.CharField(
        label="DESCRIPCION DEL PARTIDO",
        required=False,
        widget=forms.Textarea(attrs={"rows": 4})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["partido"].queryset = Partido.objects.select_related(
            "torneo",
            "equipo_local",
            "equipo_visitante",
            "cancha"
        ).filter(
            goles_local__isnull=True,
            goles_visitante__isnull=True
        ).order_by("fecha", "hora")

    def save(self):
        partido = self.cleaned_data["partido"]
        partido.goles_local = self.cleaned_data["goles_local"]
        partido.goles_visitante = self.cleaned_data["goles_visitante"]
        partido.descripcion = self.cleaned_data["descripcion"]
        partido.save()
        return partido


class Editar_Resultado_Partido(forms.ModelForm):
    class Meta:
        model = Partido
        fields = [
            "goles_local",
            "goles_visitante",
            "descripcion",
        ]
        labels = {
            "goles_local": "GOLES LOCAL",
            "goles_visitante": "GOLES VISITANTE",
            "descripcion": "DESCRIPCION DEL PARTIDO",
        }
        widgets = {
            "goles_local": forms.NumberInput(
                attrs={
                    "min": 0,
                    "max": Partido.MAX_GOLES_POR_EQUIPO
                }
            ),
            "goles_visitante": forms.NumberInput(
                attrs={
                    "min": 0,
                    "max": Partido.MAX_GOLES_POR_EQUIPO
                }
            ),
            "descripcion": forms.Textarea(attrs={"rows": 4}),
        }

    def clean(self):
        cleaned_data = super().clean()
        goles_local = cleaned_data.get("goles_local")
        goles_visitante = cleaned_data.get("goles_visitante")

        if goles_local is None:
            self.add_error("goles_local", "Debes ingresar los goles del equipo local.")

        if goles_visitante is None:
            self.add_error("goles_visitante", "Debes ingresar los goles del equipo visitante.")

        return cleaned_data

class TarjetaPartidoForm(forms.ModelForm):

    class Meta:
        model = TarjetaPartido

        fields = [
            "equipo",
            "tipo_tarjeta",
            "afectado",
            "numero_camiseta",
            "nombre_persona",
        ]

        labels = {
            "equipo": "EQUIPO",
            "tipo_tarjeta": "TIPO DE TARJETA",
            "afectado": "CATEGORÍA",
            "numero_camiseta": "NÚMERO",
            "nombre_persona": "NOMBRE",
        }
        
class BaseTarjetaPartidoFormSet(BaseInlineFormSet):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        partido = self.instance

        if not partido or not partido.pk:
            return

        equipos_partido = Equipo.objects.filter(
            pk__in=[
                partido.equipo_local_id,
                partido.equipo_visitante_id,
            ]
        )

        for form in self.forms:
            form.fields["equipo"].queryset = equipos_partido

    def clean(self):
        super().clean()

        if any(self.errors):
            return

        contador_rojas = {}  # (equipo, afectado) -> cantidad

        for form in self.forms:
            if not hasattr(form, "cleaned_data") or form.cleaned_data.get("DELETE"):
                continue

            equipo = form.cleaned_data.get("equipo")
            tipo_tarjeta = form.cleaned_data.get("tipo_tarjeta")
            afectado = form.cleaned_data.get("afectado")

            if equipo and self.instance.pk and equipo.pk not in {
                self.instance.equipo_local_id,
                self.instance.equipo_visitante_id,
            }:
                raise ValidationError("Las tarjetas deben pertenecer al local o visitante del partido.")

            if not equipo or tipo_tarjeta != "roja" or not afectado:
                continue

            clave = (equipo, afectado)
            contador_rojas[clave] = contador_rojas.get(clave, 0) + 1

        etiquetas_afectado = dict(TarjetaPartido.TIPOS_AFECTADO)

        for (equipo, afectado), cantidad in contador_rojas.items():
            limite = TarjetaPartido.LIMITES_ROJAS_POR_AFECTADO.get(afectado)

            if limite is not None and cantidad > limite:
                raise ValidationError(
                    f"{equipo} no puede tener más de {limite} tarjetas rojas "
                    f"para '{etiquetas_afectado.get(afectado, afectado)}'."
                )


TarjetaPartidoFormSet = inlineformset_factory(
    Partido,
    TarjetaPartido,
    form=TarjetaPartidoForm,
    formset=BaseTarjetaPartidoFormSet,
    extra=10,
    can_delete=True,
)
