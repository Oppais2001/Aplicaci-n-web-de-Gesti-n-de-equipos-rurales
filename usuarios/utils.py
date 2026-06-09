import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
from django.urls import reverse
from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode


def enviar_email_verificacion(request, usuario):
    uid = urlsafe_base64_encode(force_bytes(usuario.pk))
    token = default_token_generator.make_token(usuario)

    link = request.build_absolute_uri(
        reverse('activar_cuenta', args=[uid, token])
    )

    configuration = sib_api_v3_sdk.Configuration()
    configuration.api_key['api-key'] = settings.BREVO_API_KEY

    api_instance = sib_api_v3_sdk.TransactionalEmailsApi(
        sib_api_v3_sdk.ApiClient(configuration)
    )

    email = sib_api_v3_sdk.SendSmtpEmail(
        to=[{"email": usuario.email, "name": usuario.username}],
        sender={"email": "felipealvrado@gmail.com", "name": "Liga Cancura"},
        subject="Verifica tu cuenta",
        text_content=f"""
Hola {usuario.username},

Gracias por registrarte.

Haz clic en el siguiente enlace para activar tu cuenta:

{link}

Si no fuiste tú, ignora este correo.
"""
    )

    api_instance.send_transac_email(email)