from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import Usuario

class RegistroForm(UserCreationForm):
    email = forms.EmailField()

    class Meta:
        model = Usuario
        fields = ['username', 'email', 'password1', 'password2']

    def clean_username(self):
        username = self.cleaned_data.get('username')

        if Usuario.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("Ya existe un usuario con ese nombre.")

        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')

        if Usuario.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Ya existe una cuenta con ese correo.")

        return email


class LoginForm(AuthenticationForm):
    username = forms.CharField(label="Usuario")
    password = forms.CharField(label="Contraseña", widget=forms.PasswordInput)