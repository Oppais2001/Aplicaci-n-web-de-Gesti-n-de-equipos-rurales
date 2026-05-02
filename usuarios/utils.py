from django.core.mail import send_mail
from django.urls import reverse
from django.conf import settings

def enviar_email_verificacion(request, usuario):

    link = request.build_absolute_uri(
        reverse('activar_cuenta', args=[usuario.id])
    )

    asunto = "Verifica tu cuenta"

    mensaje = f"""
Hola {usuario.username},

Gracias por registrarte.

Haz clic en el siguiente enlace para activar tu cuenta:

{link}

Si no fuiste tú, ignora este correo.
"""

    send_mail(
        asunto,
        mensaje,
        settings.DEFAULT_FROM_EMAIL,
        [usuario.email],
        fail_silently=False
    )