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
    link = request.build_absolute_uri(reverse('activar_cuenta', args=[uid, token]))

    asunto = "Verifica tu cuenta"
    mensaje = f"""
Hola {usuario.username},

Haz clic aquí para activar tu cuenta:

{link}
"""

    if settings.BREVO_API_KEY:
        # Producción: envía con Brevo
        import sib_api_v3_sdk
        configuration = sib_api_v3_sdk.Configuration()
        configuration.api_key['api-key'] = settings.BREVO_API_KEY
        api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))
        email = sib_api_v3_sdk.SendSmtpEmail(
            to=[{"email": usuario.email, "name": usuario.username}],
            sender={"email": "felipealvrado@11403316.brevosend.com", "name": "Liga Rural Cancura"},
            subject=asunto,
            text_content=mensaje
        )
        api_instance.send_transac_email(email)
    else:
        # Local: imprime en terminal
        from django.core.mail import send_mail
        send_mail(asunto, mensaje, 'local@test.com', [usuario.email], fail_silently=False)