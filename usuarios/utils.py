from django.urls import reverse
from django.conf import settings
from django.core.mail import EmailMessage, get_connection
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode


def enviar_email_verificacion(request, usuario):
    uid = urlsafe_base64_encode(force_bytes(usuario.pk))
    token = default_token_generator.make_token(usuario)
    link = request.build_absolute_uri(reverse('activar_cuenta', args=[uid, token]))

    asunto = "Verifica tu cuenta"
    mensaje = f"""
Hola {usuario.username},

Haz clic aquí para activar tu cuenta:

{link}
"""

    timeout = max(1, min(getattr(settings, 'EMAIL_TIMEOUT', 5), 10))
    connection = get_connection(fail_silently=False, timeout=timeout)
    email = EmailMessage(
        subject=asunto,
        body=mensaje,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[usuario.email],
        connection=connection,
    )
    email.send(fail_silently=False)
