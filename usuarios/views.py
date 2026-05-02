from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from django.contrib.auth.models import User
from django.core.mail import send_mail

from .forms import RegistroForm, LoginForm
from .models import Usuario

from .utils import enviar_email_verificacion

def registro_view(request):

    if request.method == 'POST':
        form = RegistroForm(request.POST)

        if form.is_valid():
            
            usuario = form.save(commit=False)
            usuario.is_active = False
            usuario.save()
            
            enviar_email_verificacion(request, usuario)

            messages.success(request, "Usuario registrado correctamente.")
            return redirect('home')

    else:
        form = RegistroForm()

    return render(request, 'usuarios/registro.html', {'form': form})


def login_view(request):

    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)

        if form.is_valid():
            usuario = form.get_user()
            login(request, usuario)

            messages.success(request, "Inicio de sesión correcto.")
            return redirect('home')

        else:
            messages.error(request, "Usuario o contraseña incorrectos.")

    else:
        form = LoginForm()

    return render(request, 'usuarios/login.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.info(request, "Sesión cerrada correctamente.")
    return redirect('login')


@login_required
def perfil_view(request):
    return render(request, 'usuarios/perfil.html')


def activar_cuenta(request, user_id):
    usuario = Usuario.objects.get(id=user_id)
    usuario.is_active = True
    usuario.save()

    messages.success(request, "Cuenta activada correctamente.")
    return redirect('login')