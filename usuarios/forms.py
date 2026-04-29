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

    def clean_password1(self):
        password = self.cleaned_data.get('password1', '')
        username = self.cleaned_data.get('username', '')

        if len(password) < 8:
            raise forms.ValidationError(
                "La contraseña debe tener al menos 8 caracteres."
            )

        if not re.search(r'[A-Z]', password):
            raise forms.ValidationError(
                "Debe contener al menos una mayúscula."
            )

        if not re.search(r'[a-z]', password):
            raise forms.ValidationError(
                "Debe contener al menos una minúscula."
            )

        if not re.search(r'\d', password):
            raise forms.ValidationError(
                "Debe contener al menos un número."
            )

        if not re.search(r'[^A-Za-z0-9]', password):
            raise forms.ValidationError(
                "Debe contener al menos un símbolo."
            )

        if username and username.lower() in password.lower():
            raise forms.ValidationError(
                "La contraseña no puede contener tu usuario."
            )

        if password.strip() != password:
            raise forms.ValidationError(
                "No uses espacios al inicio o final."
            )

        return password


class LoginForm(AuthenticationForm):
    username = forms.CharField(label="Usuario")
    password = forms.CharField(label="Contraseña", widget=forms.PasswordInput)