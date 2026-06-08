import resend
from django.urls import reverse
from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

def enviar_email_verificacion(request, usuario):
    resend.api_key = settings.RESEND_API_KEY

    uid = urlsafe_base64_encode(force_bytes(usuario.pk))
    token = default_token_generator.make_token(usuario)

    link = request.build_absolute_uri(
        reverse('activar_cuenta', args=[uid, token])
    )

    resend.Emails.send({
        "from": "onboarding@resend.dev",  # ← dominio gratuito de Resend
        "to": usuario.email,
        "subject": "Verifica tu cuenta",
        "text": f"""
Hola {usuario.username},

Gracias por registrarte.

Haz clic en el siguiente enlace para activar tu cuenta:

{link}

Si no fuiste tú, ignora este correo.
""",
    })