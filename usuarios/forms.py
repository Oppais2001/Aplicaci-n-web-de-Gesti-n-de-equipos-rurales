import re
from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import Usuario

class RegistroForm(UserCreationForm):
    email = forms.EmailField()

    class Meta:
        model = Usuario
        fields = ['username', 'email', 'password1', 'password2']

    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()

        # No solo números
        if username.isdigit():
            raise forms.ValidationError(
                "El nombre de usuario no puede ser solo números."
            )

        # Solo letras, números, guion y guion bajo
        # Pero - y _ solo entre caracteres alfanuméricos
        patron = r'^[A-Za-z0-9]+(?:[-_][A-Za-z0-9]+)*$'

        if not re.fullmatch(patron, username):
            raise forms.ValidationError(
                "Solo se permiten letras, números, y los símbolos - o _ "
                "entre caracteres alfanuméricos."
            )

        # Evitar duplicados ignorando mayúsculas/minúsculas
        if Usuario.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError(
                "Ya existe un usuario con ese nombre."
            )

        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')

        if Usuario.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Ya existe una cuenta con ese correo.")

        return email


class LoginForm(AuthenticationForm):
    username = forms.CharField(label="Usuario")
    password = forms.CharField(label="Contraseña", widget=forms.PasswordInput)