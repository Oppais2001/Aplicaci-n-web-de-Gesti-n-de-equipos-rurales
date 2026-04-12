from django import forms
from .models import Equipo, Jugador, Traspaso

from dateutil.relativedelta import relativedelta
from datetime import date

class Ingresar_Jugadores(forms.ModelForm):
    class Meta:
        model = Jugador
        fields = ['nombre', 'rut', 'equipo', 'fecha_inscripcion']
        labels = {
            'fecha_inscripcion': 'Fecha de inscripción'
        }

    def clean_rut(self):
        rut = self.cleaned_data.get('rut')

        if Jugador.objects.filter(rut=rut).exists():
            raise forms.ValidationError("Ya existe un jugador con este RUT")

        return rut


class Ingresar_Equipos(forms.ModelForm):
    class Meta:
        model = Equipo
        fields = ['nombre', 'liga']

    def clean_nombre(self):
        nombre = self.cleaned_data.get('nombre')

        if Equipo.objects.filter(nombre__iexact=nombre).exists():
            raise forms.ValidationError("Ya existe un equipo con ese nombre")

        return nombre

class Realizar_Traspasos(forms.ModelForm):
    class Meta:
        model = Traspaso
        fields = ['jugador', 'equipo_destino', 'fecha']

    def clean(self):
        cleaned_data = super().clean()

        jugador = cleaned_data.get('jugador')
        equipo_destino = cleaned_data.get('equipo_destino')
        fecha = cleaned_data.get('fecha')

        if not jugador or not equipo_destino or not fecha:
            return cleaned_data

        # No puede transferirse al mismo equipo
        if jugador.equipo == equipo_destino:
            raise forms.ValidationError("El jugador ya pertenece a ese equipo.")

        #  Obtener última fecha relevante
        ultimo_traspaso = jugador.traspasos.order_by('-fecha').first()

        if ultimo_traspaso:
            fecha_base = ultimo_traspaso.fecha
        else:
            fecha_base = jugador.fecha_inscripcion

        # Validar 1 año y medio
        if fecha < fecha_base + relativedelta(years=1, months=6):
            raise forms.ValidationError(
                f"El jugador no puede transferirse antes de {fecha_base + relativedelta(years=1, months=6)}"
            )

        # No permitir fechas futuras
        if fecha > date.today():
            raise forms.ValidationError("No puedes ingresar una fecha futura.")

        return cleaned_data
    
    def save(self, commit=True):
        traspaso = super().save(commit=False)

        # asignar equipo origen automáticamente
        traspaso.equipo_origen = traspaso.jugador.equipo

        if commit:
            traspaso.save()

            jugador = traspaso.jugador
            jugador.equipo = traspaso.equipo_destino
            jugador.fecha_inscripcion = traspaso.fecha
            jugador.save()

        return traspaso
