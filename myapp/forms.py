import re
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
        rut = self.cleaned_data.get('rut')

        rut = rut.replace(".", "").replace("-", "").lower()

        if len(rut) < 2:
            raise forms.ValidationError("RUT inválido")

        if Jugador.objects.filter(rut=rut).exists():
            raise forms.ValidationError(
                "Ya existe un jugador con este RUT"
            )

        cuerpo = rut[:-1]
        dv = rut[-1]

        if not cuerpo.isdigit():
            raise forms.ValidationError("RUT inválido")

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
            raise forms.ValidationError("RUT inválido")

        return rut


    def clean_fecha_inscripcion(self):
        fecha = self.cleaned_data.get('fecha_inscripcion')

        if fecha > date.today():
            raise forms.ValidationError(
                "No puedes ingresar una fecha futura."
            )

        return fecha
    
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
        fields = ['jugador', 'equipo_destino', 'fecha_inscripcion_actual']

    def clean(self):
        cleaned_data = super().clean()

        jugador = cleaned_data.get('jugador')
        equipo_destino = cleaned_data.get('equipo_destino')
        fecha_actual = cleaned_data.get('fecha_inscripcion_actual')

        if not jugador or not equipo_destino or not fecha_actual:
            return cleaned_data

        # No mismo equipo
        if jugador.equipo == equipo_destino:
            raise forms.ValidationError(
                "El jugador ya pertenece a ese equipo."
            )

        # Fecha base real
        fecha_base = jugador.fecha_inscripcion

        # Debe pasar 1 año y medio
        fecha_minima = fecha_base + relativedelta(years=1, months=6)

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

        jugador = traspaso.jugador

        # Guardar respaldo
        traspaso.equipo_origen = jugador.equipo
        traspaso.fecha_inscripcion_anterior = jugador.fecha_inscripcion

        if commit:
            traspaso.save()

            # Actualizar jugador
            jugador.equipo = traspaso.equipo_destino
            jugador.fecha_inscripcion = traspaso.fecha_inscripcion_actual
            jugador.save()

        return traspaso

class Editar_Jugador(forms.ModelForm):

    class Meta:
        model = Jugador
        fields = ['nombre', 'rut', 'equipo', 'fecha_inscripcion']
        labels = {
            'fecha_inscripcion': 'Fecha de inscripción'
        }

    def clean_nombre(self):
        nombre = self.cleaned_data.get('nombre', '').strip()

        nombre = " ".join(nombre.split())

        if not nombre:
            raise forms.ValidationError(
                "Debes ingresar un nombre."
            )

        patron = r'^[A-Za-zÁÉÍÓÚáéíóúÑñÜü\s\-]+$'

        if not re.fullmatch(patron, nombre):
            raise forms.ValidationError(
                "El nombre solo puede contener letras."
            )

        return nombre.title()


    def clean_rut(self):
        # Obtener el RUT ingresado desde el formulario
        # strip() elimina espacios al inicio y al final
        rut = self.cleaned_data.get('rut', '').strip()

        # -------------------------------------------------
        # NORMALIZAR FORMATO
        # -------------------------------------------------
        # Si el usuario escribe:
        # 12.345.678-5
        # lo convertimos a:
        # 123456785
        #
        # Esto permite guardar todos los RUT igual
        # y comparar duplicados correctamente.
        rut = rut.replace(".", "").replace("-", "").lower()

        # -------------------------------------------------
        # VALIDACIÓN 1: largo mínimo
        # -------------------------------------------------
        # Un RUT necesita al menos:
        # número + dígito verificador
        # ejemplo: 1-9
        if len(rut) < 2:
            raise forms.ValidationError("RUT inválido.")

        # -------------------------------------------------
        # SEPARAR CUERPO Y DÍGITO VERIFICADOR
        # -------------------------------------------------
        # Ejemplo:
        # rut = 123456785
        #
        # cuerpo = 12345678
        # dv = 5
        cuerpo = rut[:-1]
        dv = rut[-1]

        # -------------------------------------------------
        # VALIDACIÓN 2: cuerpo solo números
        # -------------------------------------------------
        # El cuerpo del RUT no puede contener letras.
        if not cuerpo.isdigit():
            raise forms.ValidationError("RUT inválido.")

        # -------------------------------------------------
        # VALIDACIÓN 3: RUT repetido
        # -------------------------------------------------
        # Buscar si ya existe un jugador con ese RUT.
        qs = Jugador.objects.filter(rut=rut)

        # Si estamos EDITANDO jugador:
        # excluir al mismo jugador actual.
        #
        # Esto permite guardar sin error si el RUT
        # sigue siendo suyo.
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        # Si existe otro jugador con ese RUT:
        if qs.exists():
            raise forms.ValidationError(
                "Ya existe otro jugador con este RUT."
            )

        # -------------------------------------------------
        # VALIDACIÓN 4: DÍGITO VERIFICADOR REAL
        # -------------------------------------------------
        # Aquí aplicamos algoritmo oficial chileno.
        #
        # Multiplicadores:
        # 2,3,4,5,6,7 y se repiten
        #
        # Se recorre desde derecha a izquierda.
        suma = 0
        multiplo = 2

        for digit in reversed(cuerpo):
            # Multiplicar cada número por el factor actual
            suma += int(digit) * multiplo

            # Siguiente multiplicador
            multiplo += 1

            # Cuando pasa de 7 vuelve a 2
            if multiplo > 7:
                multiplo = 2

        # -------------------------------------------------
        # CÁLCULO DEL DV CORRECTO
        # -------------------------------------------------
        resto = suma % 11
        dv_calculado = 11 - resto

        # Casos especiales del sistema chileno:
        #
        # 11 = 0
        # 10 = K
        if dv_calculado == 11:
            dv_calculado = "0"
        elif dv_calculado == 10:
            dv_calculado = "k"
        else:
            dv_calculado = str(dv_calculado)

        # -------------------------------------------------
        # VALIDACIÓN FINAL
        # -------------------------------------------------
        # Si el DV ingresado no coincide con el real:
        if dv != dv_calculado:
            raise forms.ValidationError("RUT inválido.")

        # -------------------------------------------------
        # SI TODO ESTÁ BIEN:
        # devolver RUT limpio
        # ejemplo: 123456785
        # -------------------------------------------------
        return rut


    def clean_fecha_inscripcion(self):
        fecha = self.cleaned_data.get('fecha_inscripcion')

        if fecha > date.today():
            raise forms.ValidationError(
                "No puedes ingresar una fecha futura."
            )

        return fecha