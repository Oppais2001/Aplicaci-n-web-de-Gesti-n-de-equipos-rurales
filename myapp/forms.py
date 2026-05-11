import re
from django import forms
from .models import Equipo, Jugador, Traspaso, Liga

from dateutil.relativedelta import relativedelta
from datetime import date

# JUGADOR
class Ingresar_Jugadores(forms.ModelForm):
    class Meta:
        model = Jugador
        fields = ['nombre', 'rut', 'fecha_nacimiento', 'equipo', 'fecha_inscripcion']
        labels = {
            'fecha_inscripcion': 'Fecha de inscripción'
        }

    def clean_nombre(self):
        nombre = self.cleaned_data.get('nombre', '').strip()

        # quitar espacios múltiples
        nombre = " ".join(nombre.split())

        if len(nombre) < 3:
            raise forms.ValidationError(
                "El nombre es demasiado corto."
            )

        # letras, espacios, tildes, ñ, guion
        patron = r'^[A-Za-zÁÉÍÓÚáéíóúÑñÜü\s\-]+$'

        if not re.fullmatch(patron, nombre):
            raise forms.ValidationError(
                "El nombre solo puede contener letras."
            )

        return nombre.title()


    def clean_rut(self):
        # Obtener el RUT ingresado
        rut = self.cleaned_data.get('rut', '').strip()

        # Normalizar formato
        rut = rut.replace(".", "").replace("-", "").lower()

        # VALIDACIÓN 1: largo mínimo
        if len(rut) < 2:
            raise forms.ValidationError("RUT inválido.")

        # Separar cuerpo y DV
        cuerpo = rut[:-1]
        dv = rut[-1]

        # VALIDACIÓN 2: cuerpo solo números
        if not cuerpo.isdigit():
            raise forms.ValidationError("RUT inválido.")

        # -------------------------------------------------
        # VALIDACIÓN NUEVA: evitar números repetidos
        # Ejemplo:
        # 11111111
        # 22222222
        # 99999999
        # -------------------------------------------------
        if len(set(cuerpo)) == 1:
            raise forms.ValidationError("Ingresa un rut realista.")

        # VALIDACIÓN 3: RUT repetido en base de datos
        qs = Jugador.objects.filter(rut=rut)

        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise forms.ValidationError(
                "Ya existe otro jugador con este RUT."
            )

        # VALIDACIÓN 4: cálculo DV oficial
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

        # VALIDACIÓN FINAL
        if dv != dv_calculado:
            raise forms.ValidationError("RUT inválido.")

        return rut


    def clean_fecha_inscripcion(self):
        fecha = self.cleaned_data.get('fecha_inscripcion')

        if fecha > date.today():
            raise forms.ValidationError(
                "No puedes ingresar una fecha futura."
            )
        
        # hacer validacion de fecha del pasado mas de 100 años

        return fecha
    
# EQUPO
class Ingresar_Equipos(forms.ModelForm):
    class Meta:
        model = Equipo
        fields = ['nombre', 'liga']

    def clean_nombre(self):
        nombre = self.cleaned_data.get('nombre')

        if Equipo.objects.filter(nombre__iexact=nombre).exists():
            raise forms.ValidationError("Ya existe un equipo con ese nombre")

        return nombre
    
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
        fields = ['nombre']

    def clean_nombre(self):
        nombre = self.cleaned_data.get('nombre')
        
        if not nombre:
            raise forms.ValidationError(
                "Debes ingresar un nombre."
            )

        if Liga.objects.filter(nombre__iexact=nombre).exists():
            raise forms.ValidationError("Ya existe una liga con ese nombre")

        return nombre
    