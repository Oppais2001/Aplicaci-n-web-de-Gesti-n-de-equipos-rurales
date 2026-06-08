from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.tokens import default_token_generator
from django.contrib import messages
from django.core.mail import BadHeaderError
from django.db import transaction
from smtplib import SMTPException
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode

from myapp.models import Dirigente
from .forms import RegistroForm, LoginForm
from .models import Usuario

from .utils import enviar_email_verificacion

def registro_view(request):

    if request.method == 'POST':
        form = RegistroForm(request.POST)

        if form.is_valid():
            print('FORMULARIO VÁLIDO')
            try:
                print("ANTES DE CREAR USUARIO")
                with transaction.atomic():
                    usuario = form.save(commit=False)
                    usuario.email = usuario.email.lower()
                    usuario.is_active = False
                    usuario.save()

                    dirigente = Dirigente.objects.select_for_update().get(
                        correo__iexact=usuario.email,
                        usuario__isnull=True
                    )
                    dirigente.usuario = usuario
                    dirigente.save()
                    print("ANTES DE ENVIAR EMAIL")
                    enviar_email_verificacion(request, usuario)
                    print("EMAIL ENVIADO")
   
            except Exception as e:
                print("ERROR CORREO:", repr(e))

                messages.error(
                    request,
                    f"Error: {e}"
                )

                return render(
                    request,
                    'usuarios/registro.html',
                    {'form': form}
                )

            messages.success(request, "Usuario registrado correctamente.")
            return redirect('verificacion_pendiente')
        else:
            print("FORMULARIO INVALIDO")
            print(form.errors)
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
            username = request.POST.get('username', '').strip()
            usuario_inactivo = Usuario.objects.filter(
                username__iexact=username,
                is_active=False
            ).exists()

            if usuario_inactivo:
                return redirect('verificacion_pendiente')

            messages.error(request, "Usuario o contraseña incorrectos.")

    else:
        form = LoginForm()

    return render(request, 'usuarios/login.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.info(request, "Sesión cerrada correctamente.")
    return redirect('login')


def verificacion_pendiente(request):
    return render(request, 'usuarios/verificacion_pendiente.html')


@login_required
def perfil_view(request):
    return render(request, 'usuarios/perfil.html')


def activar_cuenta(request, uidb64, token):
    try:
        user_id = force_str(urlsafe_base64_decode(uidb64))
        usuario = Usuario.objects.get(id=user_id)
    except (TypeError, ValueError, OverflowError, Usuario.DoesNotExist):
        usuario = None

    if usuario is None or not default_token_generator.check_token(usuario, token):
        messages.error(request, "El enlace de activación no es válido o ya fue usado.")
        return redirect('login')

    usuario.is_active = True
    usuario.save()

    messages.success(request, "Cuenta activada correctamente.")
    return redirect('login')
