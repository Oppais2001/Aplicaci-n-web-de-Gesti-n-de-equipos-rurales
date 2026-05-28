from functools import wraps

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden

from .models import Dirigente


def es_administrador(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser)


def obtener_dirigente(user):
    if not user.is_authenticated:
        return None

    return (
        Dirigente.objects
        .select_related('equipo', 'equipo__liga')
        .filter(usuario=user)
        .first()
    )


def es_dirigente(user):
    return obtener_dirigente(user) is not None


def admin_required(view_func):
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not es_administrador(request.user):
            return HttpResponseForbidden("No tienes permiso para realizar esta accion.")

        return view_func(request, *args, **kwargs)

    return wrapper


def usuario_autorizado_required(view_func):
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if es_administrador(request.user) or es_dirigente(request.user):
            return view_func(request, *args, **kwargs)

        return HttpResponseForbidden("Tu usuario no tiene un rol autorizado.")

    return wrapper
