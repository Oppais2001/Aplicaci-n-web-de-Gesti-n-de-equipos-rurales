from django.db.models.signals import post_delete
from django.dispatch import receiver

from .models import Dirigente


@receiver(post_delete, sender=Dirigente)
def eliminar_usuario_asociado(sender, instance, **kwargs):
    usuario = instance.usuario

    if usuario and not Dirigente.objects.filter(usuario=usuario).exists():
        usuario.delete()
