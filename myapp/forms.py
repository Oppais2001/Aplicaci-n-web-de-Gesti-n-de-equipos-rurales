import re
from django import forms
from .models import Dirigente, Equipo, Jugador, Traspaso, Liga

from dateutil.relativedelta import relativedelta
from datetime import date

from django.core.exceptions import ValidationError

# JUGADOR
class Ingresar_Jugadores(forms.ModelForm):

    class Meta:

        model = Jugador

        fields = [
            'nombre',
            'rut',
            'fecha_nacimiento',
            'telefono',
            'contacto_emergencia',
            'equipo',
            'fecha_inscripcion',
            'adulto_responsable',
            'tipo_sangre',
            'tiene_seguro',
            'alergias',
            'certificado_medico'
        ]

        labels = {
            'fecha_inscripcion': 'Fecha de inscripción',
            'contacto_emergencia': 'Contacto de emergencia',
            'adulto_responsable': 'Adulto responsable',
            'tipo_sangre': 'Tipo de sangre',
            'tiene_seguro': '¿Tiene seguro?',
            'certificado_medico': 'Certificado médico'
        }

    # ---------------------------------------------------
    # VALIDAR NOMBRE
    # ---------------------------------------------------

    def clean_nombre(self):

        nombre = self.cleaned_data.get(
            'nombre',
            ''
        ).strip()

        nombre = " ".join(nombre.split())

        if len(nombre) < 3:

            raise forms.ValidationError(
                "El nombre es demasiado corto."
            )

        patron = r'^[A-Za-zÁÉÍÓÚáéíóúÑñÜü\s\-]+$'

        if not re.fullmatch(patron, nombre):

            raise forms.ValidationError(
                "El nombre solo puede contener letras."
            )

        if len(set(nombre.lower().replace(" ", ""))) == 1:

            raise forms.ValidationError(
                "Ingresa un nombre válido."
            )

        return nombre.title()

    # ---------------------------------------------------
    # VALIDAR RUT
    # ---------------------------------------------------

    def clean_rut(self):

        rut = self.cleaned_data.get(
            'rut',
            ''
        ).strip()

        rut = (
            rut
            .replace(".", "")
            .replace("-", "")
            .lower()
        )

        if len(rut) < 2:

            raise forms.ValidationError(
                "RUT inválido."
            )

        cuerpo = rut[:-1]
        dv = rut[-1]

        if not cuerpo.isdigit():

            raise forms.ValidationError(
                "RUT inválido."
            )

        if len(set(cuerpo)) == 1:

            raise forms.ValidationError(
                "Ingresa un rut realista."
            )

        qs = Jugador.objects.filter(rut=rut)

        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():

            raise forms.ValidationError(
                "Ya existe otro jugador con este RUT."
            )

        suma = 0
        multiplo = 2

        for digit in reversed(cuerpo):

            suma += int(digit) * multiplo

            multiplo += 1

            if multiplo > 7:
                multiplo = 2

        resto = suma % 11

        dv_calculado = 11 - resto

        if dv_calculado == 11:
            dv_calculado = "0"

        elif dv_calculado == 10:
            dv_calculado = "k"

        else:
            dv_calculado = str(dv_calculado)

        if dv != dv_calculado:

            raise forms.ValidationError(
                "RUT inválido."
            )

        return rut

    # ---------------------------------------------------
    # VALIDAR FECHA INSCRIPCIÓN
    # ---------------------------------------------------

    def clean_fecha_inscripcion(self):

        fecha = self.cleaned_data.get(
            'fecha_inscripcion'
        )

        if fecha > date.today():

            raise forms.ValidationError(
                "No puedes ingresar una fecha futura."
            )

        if fecha < date.today() - relativedelta(years=100):

            raise forms.ValidationError(
                "La fecha es demasiado antigua."
            )

        return fecha

    # ---------------------------------------------------
    # VALIDAR FECHA NACIMIENTO
    # ---------------------------------------------------

    def clean_fecha_nacimiento(self):

        fecha = self.cleaned_data.get(
            'fecha_nacimiento'
        )

        if not fecha:
            return fecha

        hoy = date.today()

        edad = relativedelta(
            hoy,
            fecha
        ).years

        if edad < 5:

            raise forms.ValidationError(
                "El jugador es demasiado joven."
            )

        if edad > 100:

            raise forms.ValidationError(
                "Edad inválida."
            )

        return fecha

    # ---------------------------------------------------
    # VALIDAR TELÉFONO
    # ---------------------------------------------------

    def clean_telefono(self):

        telefono = self.cleaned_data.get(
            'telefono',
            ''
        ).strip()

        if not telefono:
            return telefono

        telefono = telefono.replace(" ", "")

        patron = r'^\+?[0-9]{8,15}$'

        if not re.fullmatch(patron, telefono):

            raise forms.ValidationError(
                "Ingresa un teléfono válido."
            )

        return telefono

    # ---------------------------------------------------
    # VALIDAR CONTACTO EMERGENCIA
    # ---------------------------------------------------

    def clean_contacto_emergencia(self):

        telefono = self.cleaned_data.get(
            'contacto_emergencia',
            ''
        ).strip()

        if not telefono:
            return telefono

        telefono = telefono.replace(" ", "")

        patron = r'^\+?[0-9]{8,15}$'

        if not re.fullmatch(patron, telefono):

            raise forms.ValidationError(
                "Ingresa un contacto válido."
            )

        return telefono

    # ---------------------------------------------------
    # VALIDAR ADULTO RESPONSABLE
    # ---------------------------------------------------

    def clean_adulto_responsable(self):

        responsable = (
            self.cleaned_data.get(
                'adulto_responsable'
            ) or ''
        ).strip()

        fecha = self.cleaned_data.get(
            'fecha_nacimiento'
        )

        if not fecha:
            return responsable

        hoy = date.today()

        edad = relativedelta(
            hoy,
            fecha
        ).years

        if edad < 18 and not responsable:

            raise forms.ValidationError(
                "Debes ingresar un adulto responsable."
            )

        return " ".join(
            responsable.split()
        ).title()
    
    # ---------------------------------------------------
    # VALIDAR TIPO SANGRE
    # ---------------------------------------------------

    def clean_tipo_sangre(self):

        tipo = self.cleaned_data.get(
            'tipo_sangre',
            ''
        ).upper().strip()

        if not tipo:
            return tipo

        tipos_validos = [
            'A+',
            'A-',
            'B+',
            'B-',
            'AB+',
            'AB-',
            'O+',
            'O-'
        ]

        if tipo not in tipos_validos:

            raise forms.ValidationError(
                "Tipo de sangre inválido."
            )

        return tipo

    # ---------------------------------------------------
    # VALIDAR ALERGIAS
    # ---------------------------------------------------

    def clean_alergias(self):

        alergias = self.cleaned_data.get(
            'alergias',
            ''
        ).strip()

        if len(alergias) > 500:

            raise forms.ValidationError(
                "Demasiado texto."
            )

        return alergias

    # ---------------------------------------------------
    # VALIDAR CERTIFICADO MÉDICO
    # ---------------------------------------------------

    def clean_certificado_medico(self):

        archivo = self.cleaned_data.get(
            'certificado_medico'
        )

        if not archivo:
            return archivo

        extensiones_validas = [
            '.pdf',
            '.jpg',
            '.jpeg',
            '.png'
        ]

        nombre = archivo.name.lower()

        if not any(
            nombre.endswith(ext)
            for ext in extensiones_validas
        ):

            raise forms.ValidationError(
                "Archivo no permitido."
            )

        if archivo.size > 5 * 1024 * 1024:

            raise forms.ValidationError(
                "El archivo supera 5MB."
            )

        return archivo
# EQUPO
class Ingresar_Equipos(forms.ModelForm):
    class Meta:
        model = Equipo
        fields = ['nombre','fecha_creacion','nombre_entrenador','nombre_dueno', 'liga']
        labels = {
            'fecha_creacion': 'fecha creación',
            'nombre_entrenador': 'nombre entrenador',
            'nombre_dueno': 'nombre dueño'
        }

    def clean_nombre(self):

        nombre = self.cleaned_data.get(
            'nombre',
            ''
        ).strip()

        # quitar espacios múltiples
        nombre = " ".join(nombre.split())

        # mínimo largo
        if len(nombre) < 3:

            raise forms.ValidationError(
                "El nombre es demasiado corto."
            )

        # máximo razonable
        if len(nombre) > 50:

            raise forms.ValidationError(
                "El nombre es demasiado largo."
            )

        # permitir:
        # letras
        # números
        # espacios
        # guiones
        patron = r'^[A-Za-zÁÉÍÓÚáéíóúÑñÜü0-9\s\-]+$'

        if not re.fullmatch(patron, nombre):

            raise forms.ValidationError(
                "El nombre contiene caracteres inválidos."
            )

        # debe contener AL MENOS una letra
        if not re.search(r'[A-Za-zÁÉÍÓÚáéíóúÑñÜü]', nombre):

            raise forms.ValidationError(
                "El nombre debe contener al menos una letra."
            )

        # evitar nombres solo símbolos o números raros
        if nombre.replace("-", "").replace(" ", "").isdigit():

            raise forms.ValidationError(
                "El nombre no puede contener solo números."
            )
            
        if len(set(nombre.lower().replace(" ", ""))) == 1:
            raise forms.ValidationError(
                "Ingresa un nombre válido."
            )

        # evitar duplicados ignorando mayúsculas
        equipos = Equipo.objects.filter(
            nombre__iexact=nombre
        )

        if self.instance.pk:

            equipos = equipos.exclude(
                pk=self.instance.pk
            )

        if equipos.exists():

            raise forms.ValidationError(
                "Ya existe un equipo con ese nombre."
            )

        return nombre.title()


# DIRIGENTE
class Ingresar_Dirigentes(forms.ModelForm):

    class Meta:
        model = Dirigente

        fields = [
            'nombre',
            'rut',
            'telefono',
            'correo',
            'cargo',
            'direccion',
            'fecha_asuncion',
            'activo',
            'equipo',
        ]

    # -------------------------
    # VALIDADOR GENERAL TEXTO
    # -------------------------

    def validar_texto(
        self,
        valor,
        campo,
        min_length=3,
        max_length=100
    ):

        valor = valor.strip()
        valor = " ".join(valor.split())

        if not valor:
            raise ValidationError(
                f"Debes ingresar {campo}."
            )

        if len(valor) < min_length:
            raise ValidationError(
                f"{campo.capitalize()} demasiado corto."
            )

        if len(valor) > max_length:
            raise ValidationError(
                f"{campo.capitalize()} demasiado largo."
            )

        patron = r'^[A-Za-zÁÉÍÓÚáéíóúÑñÜü\s\-\.]+$'

        if not re.fullmatch(patron, valor):
            raise ValidationError(
                f"{campo.capitalize()} contiene caracteres inválidos."
            )

        if len(set(valor.lower().replace(" ", ""))) == 1:
            raise ValidationError(
                f"Ingresa {campo} válido."
            )

        return valor.title()

    # -------------------------
    # NOMBRE
    # -------------------------

    def clean_nombre(self):

        return self.validar_texto(
            self.cleaned_data.get('nombre', ''),
            'un nombre',
            3,
            100
        )

    # -------------------------
    # CARGO
    # -------------------------

    def clean_cargo(self):

        return self.validar_texto(
            self.cleaned_data.get('cargo', ''),
            'un cargo',
            3,
            50
        )

    # -------------------------
    # DIRECCION
    # -------------------------

    def clean_direccion(self):

        direccion = self.cleaned_data.get(
            'direccion',
            ''
        )

        if not direccion:
            return direccion

        direccion = direccion.strip()
        direccion = " ".join(direccion.split())

        if len(direccion) < 5:
            raise ValidationError(
                "La dirección es demasiado corta."
            )

        if len(direccion) > 255:
            raise ValidationError(
                "La dirección es demasiado larga."
            )

        return direccion.title()

    # -------------------------
    # RUT
    # -------------------------

    def clean_rut(self):

        rut = self.cleaned_data.get(
            'rut',
            ''
        ).strip()

        rut = (
            rut
            .replace(".", "")
            .replace("-", "")
            .lower()
        )

        if len(rut) < 2:
            raise ValidationError(
                "RUT inválido."
            )

        cuerpo = rut[:-1]
        dv = rut[-1]

        if not cuerpo.isdigit():
            raise ValidationError(
                "RUT inválido."
            )

        if len(set(cuerpo)) == 1:
            raise ValidationError(
                "Ingresa un RUT válido."
            )

        dirigentes = Dirigente.objects.filter(
            rut=rut
        )

        if self.instance.pk:
            dirigentes = dirigentes.exclude(
                pk=self.instance.pk
            )

        if dirigentes.exists():
            raise ValidationError(
                "Ya existe otro dirigente con este RUT."
            )

        suma = 0
        multiplo = 2

        for digit in reversed(cuerpo):

            suma += int(digit) * multiplo

            multiplo += 1

            if multiplo > 7:
                multiplo = 2

        resto = suma % 11
        dv_calculado = 11 - resto

        if dv_calculado == 11:
            dv_calculado = "0"

        elif dv_calculado == 10:
            dv_calculado = "k"

        else:
            dv_calculado = str(dv_calculado)

        if dv != dv_calculado:
            raise ValidationError(
                "RUT inválido."
            )

        return rut

    # -------------------------
    # TELEFONO
    # -------------------------

    def clean_telefono(self):

        telefono = self.cleaned_data.get(
            'telefono',
            ''
        ).strip()

        telefono_limpio = re.sub(
            r'[\s\-\+]',
            '',
            telefono
        )

        if not telefono_limpio.isdigit():
            raise ValidationError(
                "El teléfono solo puede contener números."
            )

        if len(telefono_limpio) < 8:
            raise ValidationError(
                "El teléfono es demasiado corto."
            )

        if len(telefono_limpio) > 12:
            raise ValidationError(
                "El teléfono es demasiado largo."
            )

        return telefono

    # -------------------------
    # CORREO
    # -------------------------

    def clean_correo(self):

        correo = self.cleaned_data.get(
            'correo',
            ''
        ).strip().lower()

        dirigentes = Dirigente.objects.filter(
            correo__iexact=correo
        )

        if (
            self.instance.pk
            and self.instance.usuario_id
            and correo != self.instance.usuario.email.lower()
        ):

            raise ValidationError(
                "No puedes cambiar el correo de un dirigente que ya tiene usuario asociado."
            )

        if self.instance.pk:
            dirigentes = dirigentes.exclude(
                pk=self.instance.pk
            )

        if dirigentes.exists():

            raise ValidationError(
                "Ya existe otro dirigente con este correo."
            )

        return correo


class Editar_Dirigentes(Ingresar_Dirigentes):

    class Meta:

        model = Dirigente

        fields = [
            'nombre',
            'rut',
            'telefono',
            'correo',
            'cargo',
            'direccion',
            'fecha_asuncion',
            'activo',
            'equipo',
        ]
        
# TRASPASO
class Realizar_Traspasos(forms.ModelForm):
    class Meta:

        model = Traspaso

        fields = [
            'equipo_destino',
            'fecha_inscripcion_actual'
        ]

        widgets = {

            'fecha_inscripcion_actual': forms.DateInput(
                attrs={'type': 'date'}
            )

        }

    def __init__(self, *args, **kwargs):

        self.jugador = kwargs.pop(
            'jugador',
            None
        )
        super().__init__(*args, **kwargs)

    def clean(self):

        cleaned_data = super().clean()

        equipo_destino = cleaned_data.get(
            'equipo_destino'
        )

        fecha_actual = cleaned_data.get(
            'fecha_inscripcion_actual'
        )

        jugador = self.jugador

        if not equipo_destino or not fecha_actual:

            return cleaned_data

        # No mismo equipo
        if jugador.equipo == equipo_destino:

            raise forms.ValidationError(
                "El jugador ya pertenece a ese equipo."
            )

        # Fecha mínima
        fecha_base = jugador.fecha_inscripcion

        fecha_minima = fecha_base + relativedelta(
            years=1,
            months=6
        )

        if fecha_actual < fecha_minima:

            raise forms.ValidationError(
                f"El jugador no puede transferirse antes de {fecha_minima}"
            )

        # No futura
        if fecha_actual > date.today():

            raise forms.ValidationError(
                "No puedes ingresar una fecha futura."
            )

        return cleaned_data

    def save(self, commit=True):

        traspaso = super().save(commit=False)

        jugador = self.jugador

        # Asignar jugador automáticamente
        traspaso.jugador = jugador

        # Respaldo
        traspaso.equipo_origen = jugador.equipo

        traspaso.fecha_inscripcion_anterior = (
            jugador.fecha_inscripcion
        )

        if commit:

            traspaso.save()

            # Actualizar jugador
            jugador.equipo = (
                traspaso.equipo_destino
            )

            jugador.fecha_inscripcion = (
                traspaso.fecha_inscripcion_actual
            )

            jugador.save()

        return traspaso
    
class Editar_Traspaso(forms.ModelForm):

    class Meta:

        model = Traspaso

        fields = [
            'equipo_destino',
            'fecha_inscripcion_actual'
        ]

        widgets = {

            'fecha_inscripcion_actual':
                forms.DateInput(
                    attrs={'type': 'date'}
                )
        }

    def clean(self):

        cleaned_data = super().clean()

        equipo_destino = cleaned_data.get(
            'equipo_destino'
        )

        fecha_actual = cleaned_data.get(
            'fecha_inscripcion_actual'
        )

        traspaso = self.instance

        if not equipo_destino or not fecha_actual:

            return cleaned_data

        # No mismo equipo origen
        if (
            traspaso.equipo_origen
            == equipo_destino
        ):

            raise forms.ValidationError(
                'El equipo destino no puede '
                'ser igual al equipo origen.'
            )

        # Fecha base REAL
        fecha_base = (
            traspaso.fecha_inscripcion_anterior
        )

        fecha_minima = fecha_base + relativedelta(
            years=1,
            months=6
        )

        if fecha_actual < fecha_minima:

            raise forms.ValidationError(
                f'El jugador no puede '
                f'transferirse antes de '
                f'{fecha_minima}'
            )

        if fecha_actual > date.today():

            raise forms.ValidationError(
                'No puedes ingresar '
                'una fecha futura.'
            )

        return cleaned_data

    def save(self, commit=True):

        traspaso = super().save(commit=False)

        if commit:

            traspaso.save()

            jugador = traspaso.jugador

            jugador.equipo = (
                traspaso.equipo_destino
            )

            jugador.fecha_inscripcion = (
                traspaso.fecha_inscripcion_actual
            )

            jugador.save()

        return traspaso

# LIGA
class Ingresar_Liga(forms.ModelForm):

    class Meta:
        model = Liga

        fields = [
            'nombre',
            'fecha_fundacion',
            'logo',
            'comuna',
            'region',
            'direccion',
            'presidente',
            'secretario',
            'tesorero',
            'telefono_contacto',
            'correo_contacto',
            'redes_sociales',
            'reglamento',
        ]

        widgets = {
            'logo': forms.FileInput(
                attrs={'class': 'form-control'}
            ),
        }

        labels = {
            'fecha_fundacion': 'Fecha fundación',
            'region': 'Región',
            'direccion': 'Dirección',
            'secretario': 'Secretari@',
            'tesorero': 'Tesorer@',
            'telefono_contacto': 'Teléfono contacto',
            'correo_contacto': 'Correo contacto',
            'redes_sociales': 'Redes sociales',
            'reglamento': 'Reglamento',
        }

    # -------------------------
    # VALIDACIONES GENERALES
    # -------------------------

    def validar_texto(
        self,
        valor,
        campo,
        min_length=3,
        max_length=100
    ):

        valor = valor.strip()
        valor = " ".join(valor.split())

        if not valor:
            raise ValidationError(
                f"Debes ingresar {campo}."
            )

        if len(valor) < min_length:
            raise ValidationError(
                f"{campo.capitalize()} demasiado corto."
            )

        if len(valor) > max_length:
            raise ValidationError(
                f"{campo.capitalize()} demasiado largo."
            )

        patron = r'^[A-Za-zÁÉÍÓÚáéíóúÑñÜü0-9\s\-\.\,]+$'

        if not re.fullmatch(patron, valor):
            raise ValidationError(
                f"{campo.capitalize()} contiene caracteres inválidos."
            )

        if not re.search(
            r'[A-Za-zÁÉÍÓÚáéíóúÑñÜü]',
            valor
        ):
            raise ValidationError(
                f"{campo.capitalize()} debe contener letras."
            )

        return valor.title()

    # -------------------------
    # NOMBRE
    # -------------------------

    def clean_nombre(self):

        nombre = self.validar_texto(
            self.cleaned_data.get('nombre', ''),
            'nombre de la liga',
            3,
            50
        )

        ligas = Liga.objects.filter(
            nombre__iexact=nombre
        )

        if self.instance.pk:
            ligas = ligas.exclude(
                pk=self.instance.pk
            )

        if ligas.exists():
            raise ValidationError(
                "Ya existe una liga con ese nombre."
            )

        return nombre

    # -------------------------
    # FECHA
    # -------------------------

    def clean_fecha_fundacion(self):

        fecha = self.cleaned_data.get(
            'fecha_fundacion'
        )

        if not fecha:
            raise ValidationError(
                "Debes ingresar una fecha."
            )

        if fecha > date.today():
            raise ValidationError(
                "No puedes ingresar una fecha futura."
            )

        if fecha < (
            date.today() - relativedelta(years=150)
        ):
            raise ValidationError(
                "La fecha es demasiado antigua."
            )

        return fecha

    # -------------------------
    # TELEFONO
    # -------------------------

    def clean_telefono_contacto(self):

        telefono = self.cleaned_data.get(
            'telefono_contacto',
            ''
        ).strip()

        telefono_limpio = re.sub(
            r'[\s\-\+]',
            '',
            telefono
        )

        if not telefono_limpio.isdigit():
            raise ValidationError(
                "El teléfono solo puede contener números."
            )

        if len(telefono_limpio) < 8:
            raise ValidationError(
                "El teléfono es demasiado corto."
            )

        if len(telefono_limpio) > 12:
            raise ValidationError(
                "El teléfono es demasiado largo."
            )

        return telefono

    # -------------------------
    # CORREO
    # -------------------------

    def clean_correo_contacto(self):

        correo = self.cleaned_data.get(
            'correo_contacto',
            ''
        ).strip().lower()

        if len(correo) > 100:
            raise ValidationError(
                "Correo demasiado largo."
            )

        return correo

    # -------------------------
    # COMUNA
    # -------------------------

    def clean_comuna(self):

        return self.validar_texto(
            self.cleaned_data.get('comuna', ''),
            'la comuna',
            3,
            100
        )

    # -------------------------
    # REGION
    # -------------------------

    def clean_region(self):

        return self.validar_texto(
            self.cleaned_data.get('region', ''),
            'la región',
            3,
            100
        )

    # -------------------------
    # DIRECCION
    # -------------------------

    def clean_direccion(self):

        return self.validar_texto(
            self.cleaned_data.get('direccion', ''),
            'la dirección',
            5,
            255
        )

    # -------------------------
    # PRESIDENTE
    # -------------------------

    def clean_presidente(self):

        return self.validar_texto(
            self.cleaned_data.get('presidente', ''),
            'el presidente',
            5,
            100
        )

    # -------------------------
    # SECRETARIO
    # -------------------------

    def clean_secretario(self):

        return self.validar_texto(
            self.cleaned_data.get('secretario', ''),
            'el secretario',
            5,
            100
        )

    # -------------------------
    # TESORERO
    # -------------------------

    def clean_tesorero(self):

        return self.validar_texto(
            self.cleaned_data.get('tesorero', ''),
            'el tesorero',
            5,
            100
        )

    # -------------------------
    # LOGO
    # -------------------------

    def clean_logo(self):

        logo = self.cleaned_data.get('logo')

        if logo:

            if logo.size > 5 * 1024 * 1024:
                raise ValidationError(
                    "El logo no puede superar 5MB."
                )

            extensiones = ['jpg', 'jpeg', 'png', 'webp']

            extension = logo.name.split('.')[-1].lower()

            if extension not in extensiones:
                raise ValidationError(
                    "Formato de imagen no permitido."
                )

        return logo

