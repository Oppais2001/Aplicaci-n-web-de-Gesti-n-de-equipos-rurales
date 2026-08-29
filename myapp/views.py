import json
import os
import secrets
import string
from django.contrib.auth import get_user_model
from django.contrib.staticfiles import finders
from django.db import transaction
from django.http import HttpResponseForbidden
from django.http import HttpResponse
from django.http import JsonResponse
from django.db.models import Count, Q
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.text import slugify
from django.views.decorators.http import require_POST
from django.contrib import messages
from .models import Dirigente, Equipo, Jugador, Traspaso, Liga, RedSocial, Arbitro, Cancha, Partido, Torneo
from .forms import (
    Editar_Dirigentes,
    Editar_Traspaso,
    EquipoRedSocialFormSet,
    Ingresar_Dirigentes,
    Ingresar_Equipos,
    Ingresar_Jugadores,
    Ingresar_Liga,
    LigaRedSocialFormSet,
    Realizar_Traspasos,
    Ingresar_Arbitros,
    Ingresar_Canchas,
    Editar_Resultado_Partido,
    Programar_Partido,
    Registrar_Resultado_Partido,
    Ingresar_Torneo,
    TarjetaPartidoFormSet,
    GolPartidoFormSet
)
from .permissions import admin_required, es_administrador, obtener_dirigente, usuario_autorizado_required, es_dirigente
from .documentos import (
    DOCUMENTOS_DISPONIBLES,
    NOMBRES_FORMATOS,
    crear_ficha_jugador_pdf,
    crear_papeleta_partido_pdf,
)
from .utils import crear_img_fechas, crear_img_tabla, crear_img_partidos, crear_pdf_detalle_equipo


def generar_password_temporal(length=14):
    grupos = [
        string.ascii_uppercase,
        string.ascii_lowercase,
        string.digits,
        "!#$%*-_",
    ]
    caracteres = "".join(grupos)
    password = [secrets.choice(grupo) for grupo in grupos]
    password.extend(secrets.choice(caracteres) for _ in range(length - len(password)))
    secrets.SystemRandom().shuffle(password)
    return "".join(password)


def generar_username_dirigente(dirigente):
    Usuario = get_user_model()
    partes_nombre = dirigente.nombre.split()
    primer_nombre = partes_nombre[0] if partes_nombre else ""
    primer_apellido = ""

    if len(partes_nombre) >= 3:
        primer_apellido = partes_nombre[2]
    elif len(partes_nombre) >= 2:
        primer_apellido = partes_nombre[1]

    base = slugify(f"{primer_nombre}.{primer_apellido}").replace("-", ".")

    if not base:
        base = dirigente.correo.split("@", 1)[0]

    base = base[:130].strip(".-_") or f"dirigente{dirigente.pk}"
    username = base
    contador = 1

    while Usuario.objects.filter(username__iexact=username).exists():
        username = f"{base}.{contador}"
        contador += 1

    return username


def crear_usuario_para_dirigente(dirigente):
    Usuario = get_user_model()

    # Buscar otro dirigente con el mismo RUT
    dirigente_existente = (
        Dirigente.objects
        .filter(rut=dirigente.rut)
        .exclude(pk=dirigente.pk)
        .filter(usuario__isnull=False)
        .first()
    )

    if dirigente_existente:
        usuario = dirigente_existente.usuario

        dirigente.usuario = usuario
        dirigente.save(update_fields=["usuario"])

        return usuario, None

    # No existe usuario para este RUT → crear uno nuevo
    password = generar_password_temporal()

    usuario = Usuario.objects.create_user(
        username=generar_username_dirigente(dirigente),
        email=dirigente.correo,
        password=password,
        first_name=dirigente.nombre,
        is_active=True,
        is_staff=False,
        is_superuser=False,
    )

    dirigente.usuario = usuario
    dirigente.save(update_fields=["usuario"])

    return usuario, password

# HOME Y ABOUT
def home(request):
    
    if es_dirigente(request.user):
        dirigente = obtener_dirigente(request.user)
        equipos = Equipo.objects.filter(
            id=dirigente.equipo_id
        ).annotate(
            total_jugadores=Count('jugadores')
        )
        total_traspasos = Traspaso.objects.filter(
            Q(equipo_origen=dirigente.equipo)
            | Q(equipo_destino=dirigente.equipo)
            | Q(jugador__equipo=dirigente.equipo)
        ).distinct().count()
    else:
        equipos = Equipo.objects.annotate(
            total_jugadores=Count('jugadores')
        ).order_by('nombre')
        total_traspasos = Traspaso.objects.count()

    lista_equipos_dict = {
        str(equipo): equipo.total_jugadores
        for equipo in equipos
    }

    return render(request, 'home.html', {
        'equipos': lista_equipos_dict,
        'total_equipos': equipos.count(),
        'total_jugadores': sum(lista_equipos_dict.values()),
        'total_traspasos': total_traspasos
    })

# acesso libre a jugadores
def about(request):
    return render(request, 'about.html')


def obtener_logo_documentos():
    liga = Liga.objects.exclude(logo="").filter(logo__isnull=False).first()

    if liga and liga.logo:
        try:
            if hasattr(liga.logo, "path") and os.path.exists(liga.logo.path):
                return liga.logo.path
        except (NotImplementedError, ValueError):
            pass

    return finders.find("img/logo_liga.png")


@usuario_autorizado_required
def documentos(request):
    return render(request, "documentos/documentos.html", {
        "documentos": DOCUMENTOS_DISPONIBLES.items(),
        "formatos": NOMBRES_FORMATOS.items(),
    })


@usuario_autorizado_required
def descargar_documento(request):
    tipo_documento = request.GET.get("documento", "ficha_jugador")
    formato = request.GET.get("formato", "carta").lower()

    if tipo_documento not in DOCUMENTOS_DISPONIBLES:
        tipo_documento = "ficha_jugador"
    if formato not in NOMBRES_FORMATOS:
        formato = "carta"

    ruta_logo = obtener_logo_documentos()
    documento = DOCUMENTOS_DISPONIBLES[tipo_documento]

    if tipo_documento == "papeleta_partido":
        pdf = crear_papeleta_partido_pdf(formato=formato, ruta_logo=ruta_logo)
    else:
        pdf = crear_ficha_jugador_pdf(formato=formato, ruta_logo=ruta_logo)

    nombre_archivo = f"{documento['archivo']}_{formato}.pdf"

    response = HttpResponse(pdf.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{nombre_archivo}"'
    return response

# EQUIPOS
@admin_required
def ingresar_equipo(request):
    if request.method == "POST":
        form = Ingresar_Equipos(request.POST, request.FILES)
        redes_formset = EquipoRedSocialFormSet(
            request.POST,
            prefix="redes"
        )

        if form.is_valid() and redes_formset.is_valid():
            equipo = form.save()
            redes_formset.instance = equipo
            redes_formset.save()
            return redirect('equipos')
    else:
        form = Ingresar_Equipos()
        redes_formset = EquipoRedSocialFormSet(prefix="redes")

    return render(request, "equipos/ingresar_equipo.html", {
        "form": form,
        "redes_formset": redes_formset,
    })

@admin_required
@require_POST
def ingresar_equipo_ajax(request):

    try:

        data = json.loads(request.body)

    except json.JSONDecodeError:

        return JsonResponse({

            'success': False,
            'error': 'Datos inválidos'

        }, status=400)

    form = Ingresar_Equipos({

        'nombre': data.get('nombre', ''),

        'fecha_creacion': data.get(
            'fecha_creacion',
            ''
        ),

        'nombre_entrenador': data.get(
            'nombre_entrenador',
            ''
        ),

        'nombre_dueno': data.get(
            'nombre_dueno',
            ''
        ),

        'liga': data.get('liga', '')
    })

    if form.is_valid():

        equipo = form.save()
        red_social = data.get('redes_sociales', '').strip()

        if red_social:
            RedSocial.objects.create(
                equipo=equipo,
                tipo=RedSocial.OTRO,
                enlace=red_social
            )

        return JsonResponse({

            'success': True,

            'id': equipo.id,

            'nombre': equipo.nombre
        })

    return JsonResponse({

        'success': False,

        'error': form.errors.as_text(),

        'errores': form.errors

    }, status=400)
    
def lista_equipos(request):
    buscar = request.GET.get('buscar')
    equipos = Equipo.objects.all().order_by('nombre')
    
    equipos_totales = equipos

    if buscar:
        equipos = equipos.filter(nombre__icontains=buscar)

    return render(request, "equipos/equipos.html", {
        "equipos": equipos,
        "hay_equipos": equipos_totales.exists(),
    })

@admin_required
def editar_equipo(request, id_equipo):
    equipo = get_object_or_404(Equipo, id = id_equipo)

    if request.method == 'POST':
        form = Ingresar_Equipos(request.POST, request.FILES, instance=equipo)
        redes_formset = EquipoRedSocialFormSet(
            request.POST,
            instance=equipo,
            prefix="redes"
        )
        
        if form.is_valid() and redes_formset.is_valid():
            form.save()
            redes_formset.save()
            return redirect('equipos')

    else:
        form = Ingresar_Equipos(instance=equipo)
        redes_formset = EquipoRedSocialFormSet(
            instance=equipo,
            prefix="redes"
        )

    return render(request, 'equipos/editar_equipo.html', {
        'form': form,
        'equipo':equipo,
        'redes_formset': redes_formset,
        
    })
@admin_required
def eliminar_equipo(request, nombre):
    equipo = get_object_or_404(Equipo, nombre__iexact=nombre)
    equipo.delete()
    return redirect('equipos')


# DIRIGENTES
@admin_required
def ingresar_dirigente(request):
    if request.method == "POST":
        form = Ingresar_Dirigentes(request.POST)

        if form.is_valid():
            with transaction.atomic():
                dirigente = form.save()
                usuario, password = crear_usuario_para_dirigente(dirigente)

            request.session["credenciales_dirigente"] = {
                "nombre": dirigente.nombre,
                "username": usuario.username,
                "email": usuario.email,
                "password": password,
            }
            return redirect("credenciales_dirigente")

    else:
        form = Ingresar_Dirigentes()

    return render(request, "dirigentes/ingresar_dirigente.html", {
        "form": form,
    })


@admin_required
def credenciales_dirigente(request):
    credenciales = request.session.pop("credenciales_dirigente", None)

    if not credenciales:
        return redirect("ingresar_dirigente")

    return render(request, "dirigentes/credenciales_dirigente.html", {
        "credenciales": credenciales,
    })


@usuario_autorizado_required
def lista_dirigentes(request):
    buscar = request.GET.get('buscar')
    dirigentes = Dirigente.objects.select_related(
        'equipo',
        'equipo__liga'
    )

    if not es_administrador(request.user):
        dirigente = obtener_dirigente(request.user)
        dirigentes = dirigentes.filter(equipo=dirigente.equipo)

    dirigentes_totales = dirigentes

    if buscar:
        dirigentes = dirigentes.filter(
            Q(nombre__icontains=buscar)
            | Q(rut__icontains=buscar)
            | Q(equipo__nombre__icontains=buscar)
            | Q(equipo__liga__nombre__icontains=buscar)
        )

    return render(request, "dirigentes/dirigentes.html", {
        "dirigentes": dirigentes.order_by('nombre'),
        "hay_dirigentes": dirigentes_totales.exists()
    })

@admin_required
def editar_dirigente(request, id_dirigente):
    dirigente = get_object_or_404(Dirigente, id=id_dirigente)

    if request.method == 'POST':
        form = Editar_Dirigentes(request.POST, instance=dirigente)

        if form.is_valid():
            form.save()
            return redirect('dirigentes')
    else:
        form = Editar_Dirigentes(instance=dirigente)

    return render(request, "dirigentes/editar_dirigente.html", {
        "form": form,
        "dirigente": dirigente
    })

@admin_required
def eliminar_dirigente(request, id_dirigente):
    dirigente = get_object_or_404(Dirigente, id=id_dirigente)
    dirigente.delete()
    return redirect('dirigentes')


# LIGA
@admin_required
def modal_ingresar_liga(request):

    form = Ingresar_Liga()

    return render(
        request,
        'ligas/modal_ingresar_liga.html',
        {'form': form}
    )

@admin_required
def ingresar_liga(request):

    next_page = request.GET.get('next')

    if request.method == "POST":

        form = Ingresar_Liga(
            request.POST,
            request.FILES
        )
        redes_formset = LigaRedSocialFormSet(
            request.POST,
            prefix="redes"
        )

        if form.is_valid() and redes_formset.is_valid():

            liga = form.save()
            redes_formset.instance = liga
            redes_formset.save()

            if next_page == 'equipo':

                return redirect(
                    f"/equipos/ingresar_equipo/?liga={liga.id}"
                )

            return redirect('ligas')

    else:

        form = Ingresar_Liga()
        redes_formset = LigaRedSocialFormSet(prefix="redes")

    return render(
        request,
        "ligas/ingresar_liga.html",
        {
            "form": form,
            "redes_formset": redes_formset
        }
    )

def lista_ligas(request):
    buscar = request.GET.get('buscar')
    ligas = Liga.objects.all()

    ligas_totales = ligas

    if buscar:
        ligas = ligas.filter(nombre__icontains=buscar)

    ligas = ligas.annotate(
        total_equipos=Count('equipo')
    ).order_by('nombre')

    return render(request, "ligas/ligas.html", {
        "ligas": ligas,
        "hay_ligas": ligas_totales.exists()
    })

@admin_required
def editar_liga(request, id_liga):
    liga = get_object_or_404(Liga, id=id_liga)

    if request.method == 'POST':
        form = Ingresar_Liga(request.POST,request.FILES, instance=liga)
        redes_formset = LigaRedSocialFormSet(
            request.POST,
            instance=liga,
            prefix="redes"
        )

        if form.is_valid() and redes_formset.is_valid():
            form.save()
            redes_formset.save()
            return redirect('ligas')
    else:
        form = Ingresar_Liga(instance=liga)
        redes_formset = LigaRedSocialFormSet(
            instance=liga,
            prefix="redes"
        )

    return render(request, "ligas/editar_liga.html", {
        "form": form,
        "liga": liga,
        "redes_formset": redes_formset
    })

@admin_required
def eliminar_liga(request, id_liga):
    liga = get_object_or_404(Liga, id=id_liga)
    liga.delete()
    return redirect('ligas')


@admin_required
@require_POST
def crear_liga_ajax(request):

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({
            "success": False,
            "error": "Datos inválidos."
        }, status=400)

    form = Ingresar_Liga({
        "nombre": data.get("nombre", ""),
        "fecha_fundacion": data.get("fecha_fundacion", ""),
        "comuna": data.get("comuna", ""),
        "region": data.get("region", ""),
        "direccion": data.get("direccion", ""),
        "presidente": data.get("presidente", ""),
        "secretario": data.get("secretario", ""),
        "tesorero": data.get("tesorero", ""),
        "telefono_contacto": data.get("telefono_contacto", ""),
        "correo_contacto": data.get("correo_contacto", ""),
        "reglamento": data.get("reglamento", ""),
    })

    if not form.is_valid():
        return JsonResponse({
            "success": False,
            "errores": form.errors.get_json_data()
        }, status=400)

    liga = form.save()

    red_social = data.get("redes_sociales", "").strip()

    if red_social:
        RedSocial.objects.create(
            liga=liga,
            tipo=RedSocial.OTRO,
            enlace=red_social
        )

    return JsonResponse({
        "success": True,
        "id": liga.id,
        "nombre": liga.nombre,
    })
    
def detalle_liga(request, id_liga):

    liga = get_object_or_404(
        Liga,
        id=id_liga
    )

    total_equipos = liga.equipo_set.count()

    return render(
        request,
        "ligas/detalle_liga.html",
        {
            "liga": liga,
            "total_equipos": total_equipos
        }
    )

# JUGADORES
@admin_required
def ingresar_jugador(request):
    ligas = Liga.objects.all()
    if request.method == "POST":
        form = Ingresar_Jugadores(request.POST)

        if form.is_valid():
            jugador = form.save()
            equipo_id = jugador.equipo.nombre
            return redirect('detalle_equipo', equipo=equipo_id)
    else:
        form = Ingresar_Jugadores()

    return render(request, "jugadores/ingresar_jugador.html", {
        "form": form,
        "ligas": ligas
    })
    
def detalle_equipo(request, equipo):
    equipo = get_object_or_404(Equipo, nombre=equipo)
    if es_administrador(request.user):
        puede_ver_rut = True 
        puede_descargar_planilla = True
        
    elif es_dirigente(request.user):
        puede_ver_rut = False
        puede_descargar_planilla = False
        perfiles_dirigente_asignados = None if puede_ver_rut else obtener_dirigente(request.user)
        for dirigente in perfiles_dirigente_asignados:
            if equipo == dirigente.equipo:
                puede_descargar_planilla = True    
                puede_ver_rut = True
                break       
    else:
        puede_ver_rut = False
        puede_descargar_planilla = False 
        
    buscar = request.GET.get('buscar')
    jugadores_totales = Jugador.objects.filter(equipo=equipo)

    if buscar:
        jugadores = Jugador.objects.filter(nombre__icontains=buscar, equipo=equipo)
    else:
        jugadores = Jugador.objects.filter(equipo=equipo)

    return render(request, "equipos/detalle_equipo.html", {
        "jugadores": jugadores,
        "equipo": equipo,
        "puede_ver_rut": puede_ver_rut,
        "puede_descargar_planilla": puede_descargar_planilla,
        'hay_jugadores': jugadores_totales.exists()
    }) 

@admin_required
def editar_jugador(request, id):
    jugador = get_object_or_404(Jugador, id=id)

    if request.method == 'POST':
        form = Ingresar_Jugadores(request.POST, instance=jugador)

        if form.is_valid():
            form.save()
            return redirect('detalle_equipo', jugador.equipo.nombre)

    else:
        form = Ingresar_Jugadores(instance=jugador)

    return render(request, 'jugadores/editar_jugador.html', {
        'form': form,
        'jugador': jugador
    })
    
@admin_required
def eliminar_jugador(request, rut):
    jugador = get_object_or_404(Jugador, rut = rut)
    equipo = jugador.equipo.nombre
    jugador.delete()
    return redirect('detalle_equipo', equipo=equipo)

# TRASPASOS
@admin_required
def realizar_traspaso(request, id_jugador):
    jugador = get_object_or_404(Jugador, id = id_jugador)

    if request.method == "POST":
        form = Realizar_Traspasos(request.POST,
                                  jugador = jugador)

        if form.is_valid():
            form.save()
            
            return redirect('traspasos')
    else:
        form = Realizar_Traspasos(jugador = jugador)
        
    return render(request, "traspasos/realizar_traspaso.html", {
        "form": form,
        "jugador": jugador
    })
    
def traspasos(request):
    buscar = request.GET.get('buscar')
    traspasos = Traspaso.objects.select_related(
        'jugador',
        'equipo_origen',
        'equipo_destino'
    )
    if buscar:
        traspasos = traspasos.filter(jugador__nombre__icontains=buscar)
                 
    return render(request, 'traspasos/traspasos.html', {
        'traspasos': traspasos,
        'hay_traspasos': traspasos.exists()
    })

@admin_required
def editar_traspaso(request, id):
    traspaso = get_object_or_404(Traspaso, id=id)

    if request.method == 'POST':
        form = Editar_Traspaso(request.POST, instance=traspaso)

        if form.is_valid():
            form.save()
            return redirect('traspasos')

    else:
        form = Editar_Traspaso(instance = traspaso)

    return render(request, 'traspasos/editar_traspaso.html', {
        'form': form,
        'traspaso': traspaso
    })

@admin_required
def eliminar_traspaso(request, id):

    if request.method != 'POST':

        return JsonResponse({

            'success': False,

            'error': 'Método inválido'
        })

    traspaso = get_object_or_404(
        Traspaso,
        id=id
    )

    jugador = traspaso.jugador

    ultimo_traspaso = (

        Traspaso.objects
        .filter(jugador=jugador)
        .order_by(
            '-fecha_inscripcion_actual'
        )
        .first()
    )

    if traspaso != ultimo_traspaso:

        return JsonResponse({

            'success': False,

            'error':
                'Solo puedes eliminar '
                'el último traspaso.'
        })

    jugador.equipo = (
        traspaso.equipo_origen
    )

    jugador.fecha_inscripcion = (
        traspaso.fecha_inscripcion_anterior
    )

    jugador.save()

    traspaso.delete()

    return JsonResponse({

        'success': True
    })
    

#Canchas
@admin_required
def ingresar_cancha(request):

    if request.method == "POST":

        form = Ingresar_Canchas(
            request.POST,
            request.FILES
        )

        if form.is_valid():

            form.save()

            return redirect('canchas')

    else:

        form = Ingresar_Canchas()

    return render(
        request,
        "canchas/ingresar_cancha.html",
        {
            "form": form,
        }
    )

def lista_canchas(request):

    buscar = request.GET.get('buscar')

    canchas = Cancha.objects.select_related(
        'liga'
    )

    canchas_totales = canchas

    if buscar:

        canchas = canchas.filter(
            nombre__icontains=buscar
        )

    return render(
        request,
        "canchas/canchas.html",
        {
            "canchas": canchas,
            "hay_canchas": canchas_totales.exists(),
        }
    )

@admin_required
def editar_cancha(request, id_cancha):

    cancha = get_object_or_404(
        Cancha,
        id=id_cancha
    )

    if request.method == 'POST':

        form = Ingresar_Canchas(
            request.POST,
            request.FILES,
            instance=cancha
        )

        if form.is_valid():

            form.save()

            return redirect(
                'canchas'
            )

    else:

        form = Ingresar_Canchas(
            instance=cancha
        )

    return render(
        request,
        'canchas/editar_cancha.html',
        {
            'form': form,
            'cancha': cancha,
        }
    )

@admin_required
def eliminar_cancha(request, id_cancha):

    cancha = get_object_or_404(
        Cancha,
        id=id_cancha
    )

    cancha.delete()

    return redirect(
        'canchas'
    )

def detalle_cancha(request, id_cancha):

    cancha = get_object_or_404(
        Cancha,
        id=id_cancha
    )

    return render(
        request,
        "canchas/detalle_cancha.html",
        {
            "cancha": cancha
        }
    )
    
# TORNEOS
def calcular_tabla_posiciones(torneo):
    tabla = {
        equipo.id: {
            "equipo": equipo,
            "pj": 0,
            "pg": 0,
            "pe": 0,
            "pp": 0,
            "gf": 0,
            "gc": 0,
            "dg": 0,
            "pts": 0,
        }
        for equipo in torneo.equipos.order_by("nombre")
    }

    partidos = torneo.partidos.select_related(
        "equipo_local",
        "equipo_visitante"
    ).filter(
        goles_local__isnull=False,
        goles_visitante__isnull=False
    )

    for partido in partidos:
        local = tabla.get(partido.equipo_local_id)
        visitante = tabla.get(partido.equipo_visitante_id)

        if not local or not visitante:
            continue

        local["pj"] += 1
        visitante["pj"] += 1
        local["gf"] += partido.goles_local
        local["gc"] += partido.goles_visitante
        visitante["gf"] += partido.goles_visitante
        visitante["gc"] += partido.goles_local

        if partido.goles_local > partido.goles_visitante:
            local["pg"] += 1
            local["pts"] += 3
            visitante["pp"] += 1
        elif partido.goles_local < partido.goles_visitante:
            visitante["pg"] += 1
            visitante["pts"] += 3
            local["pp"] += 1
        else:
            local["pe"] += 1
            visitante["pe"] += 1
            local["pts"] += 1
            visitante["pts"] += 1

    for fila in tabla.values():
        fila["dg"] = fila["gf"] - fila["gc"]

    return sorted(
        tabla.values(),
        key=lambda fila: (
            -fila["pts"],
            -fila["dg"],
            -fila["gf"],
            fila["equipo"].nombre.lower()
        )
    )


def datos_selector_equipos_torneo():
    return {
        "ligas": Liga.objects.order_by("nombre"),
        "equipos_disponibles": Equipo.objects.select_related("liga").order_by(
            "liga__nombre",
            "nombre"
        )
    }


@admin_required
def ingresar_torneo(request):
    if request.method == "POST":
        form = Ingresar_Torneo(request.POST)

        if form.is_valid():
            form.save()
            return redirect("torneos")
    else:
        form = Ingresar_Torneo()

    context = {
        "form": form
    }
    context.update(datos_selector_equipos_torneo())

    return render(request, "torneos/ingresar_torneo.html", context)

def lista_torneos(request):
    buscar = request.GET.get("buscar")
    torneos = Torneo.objects.prefetch_related("equipos")

    torneos_totales = torneos

    if buscar:
        torneos = torneos.filter(nombre__icontains=buscar)

    torneos = torneos.annotate(
        total_partidos=Count("partidos", distinct=True),
        total_equipos_anotado=Count("equipos", distinct=True)
    ).order_by("-fecha_inicio", "nombre")

    return render(request, "torneos/torneos.html", {
        "torneos": torneos,
        "hay_torneos": torneos_totales.exists()
    })

def detalle_torneo(request, id_torneo):
    torneo = get_object_or_404(
        Torneo.objects.prefetch_related("equipos").prefetch_related("partidos"),
        id=id_torneo
    )

    tabla_posiciones = calcular_tabla_posiciones(torneo)
    partidos_programados = torneo.partidos.filter(goles_local__isnull=True, goles_visitante__isnull=True).select_related(
        "equipo_local",
        "equipo_visitante",
        "cancha"
    ).order_by("fecha", "hora")
    partidos_jugados = torneo.partidos.filter(goles_local__isnull=False, goles_visitante__isnull=False).select_related(
        "equipo_local",
        "equipo_visitante",
        "cancha"
    ).order_by("fecha", "hora")
    
    print(partidos_programados)
    print(partidos_jugados)

    return render(request, "torneos/detalle_torneo.html", {
        "torneo": torneo,
        "tabla_posiciones": tabla_posiciones,
        "partidos_programados": partidos_programados,
        "partidos_jugados":partidos_jugados
    })


@admin_required
def editar_torneo(request, id_torneo):
    torneo = get_object_or_404(Torneo, id=id_torneo)

    if request.method == "POST":
        form = Ingresar_Torneo(request.POST, instance=torneo)

        if form.is_valid():
            form.save()
            return redirect("torneos")
    else:
        form = Ingresar_Torneo(instance=torneo)

    context = {
        "form": form,
        "torneo": torneo
    }
    context.update(datos_selector_equipos_torneo())

    return render(request, "torneos/editar_torneo.html", context)


@admin_required
def eliminar_torneo(request, id_torneo):
    torneo = get_object_or_404(Torneo, id=id_torneo)
    torneo.delete()

    return redirect("torneos")

def descargar_tabla_imagen(request, torneo_id):
    torneo = get_object_or_404(
        Torneo.objects.prefetch_related("equipos").prefetch_related("partidos"),
        id=torneo_id)
    tabla_posiciones = calcular_tabla_posiciones(torneo)
    return crear_img_tabla(torneo, tabla_posiciones)

def descargar_partidos_imagen(request, torneo_id):
    torneo = get_object_or_404(
        Torneo.objects.prefetch_related("partidos"),
        id=torneo_id
    )
    partidos = torneo.partidos.select_related(
        "equipo_local",
        "equipo_visitante",
        "cancha"
    ).order_by("fecha", "hora")

    return crear_img_partidos(torneo, partidos)

def descargar_fechas_imagen(request, torneo_id):
    liga = get_object_or_404(Liga, nombre='Unión Comunal De Clubes Deportivos Rurales, Sociales Y Culturales Entre Ríos Ex Liga Cancura, Puerto Octay')
    
    torneo = get_object_or_404(
        Torneo.objects.prefetch_related("partidos"),
        id=torneo_id
    )
    partidos = torneo.partidos.select_related(
        "equipo_local",
        "equipo_visitante",
        "cancha"
    ).order_by("fecha", "hora")

    return crear_img_fechas(torneo, partidos, liga)

@usuario_autorizado_required
def descargar_detalle_equipo(request, equipo_id):
    equipo = get_object_or_404(
        Equipo.objects.prefetch_related("jugadores"),
        id=equipo_id
    )
    mostrar_rut = es_administrador(request.user)

    if not mostrar_rut:
        dirigente = obtener_dirigente(request.user)
        if not dirigente or dirigente.equipo_id != equipo.id:
            return HttpResponseForbidden("No tienes permiso para descargar la planilla de este equipo.")

    jugadores = sorted(equipo.jugadores.all(),key= lambda jugador: jugador.apellidos)
    return crear_pdf_detalle_equipo(equipo, jugadores, mostrar_rut=mostrar_rut)

# PARTIDOS
def _datos_partido_para_widget(partidos):
    """
    Prepara los datos necesarios para los widgets de goles y tarjetas.

    equipos_por_partido:
        {
            partido_id: [
                {"id": equipo_id, "nombre": nombre},
                ...
            ]
        }

    jugadores_por_equipo:
        {
            equipo_id: [
                {"id": jugador_id, "nombre": nombre},
                ...
            ]
        }
    """

    equipos_por_partido = {}
    equipos_ids = set()

    for partido in partidos:

        equipos_por_partido[str(partido.pk)] = [
            {
                "id": partido.equipo_local_id,
                "nombre": partido.equipo_local.nombre
            },
            {
                "id": partido.equipo_visitante_id,
                "nombre": partido.equipo_visitante.nombre
            },
        ]

        equipos_ids.add(partido.equipo_local_id)
        equipos_ids.add(partido.equipo_visitante_id)

    jugadores_por_equipo = {}

    if equipos_ids:

        jugadores = Jugador.objects.filter(
            equipo_id__in=equipos_ids,
            activo=True
        ).order_by("nombre")

        for jugador in jugadores:

            jugadores_por_equipo.setdefault(
                str(jugador.equipo_id),
                []
            ).append(
                {
                    "id": jugador.pk,
                    "nombre": jugador.nombre
                }
            )

    return equipos_por_partido, jugadores_por_equipo

@admin_required
def ingresar_partido(request):

    if request.method == "POST":

        form = Registrar_Resultado_Partido(request.POST)

        partido = None

        if form.is_valid():
            partido = form.cleaned_data["partido"]

        tarjetas_formset = TarjetaPartidoFormSet(
            request.POST,
            instance=partido,
            prefix="tarjetas"
        )

        goles_formset = GolPartidoFormSet(
            request.POST,
            instance=partido,
            prefix="goles"
        )

        if (
            form.is_valid()
            and tarjetas_formset.is_valid()
            and goles_formset.is_valid()
        ):

            with transaction.atomic():

                partido = form.save()

                tarjetas_formset.instance = partido
                tarjetas_formset.save()

                goles_formset.instance = partido
                goles_formset.save()

            return redirect("partidos")

    else:

        form = Registrar_Resultado_Partido()

        tarjetas_formset = TarjetaPartidoFormSet(
            prefix="tarjetas"
        )

        goles_formset = GolPartidoFormSet(
            prefix="goles"
        )

    equipos_por_partido, jugadores_por_equipo = (
        _datos_partido_para_widget(
            form.fields["partido"].queryset
        )
    )

    return render(
        request,
        "partidos/ingresar_partido.html",
        {
            "form": form,

            "tarjetas_formset": tarjetas_formset,

            "goles_formset": goles_formset,

            "goles_equipos_por_partido":
                equipos_por_partido,

            "goles_jugadores_por_equipo":
                jugadores_por_equipo,

            # Datos para tarjetas
            "tarjetas_equipos_por_partido":
                equipos_por_partido,

            "tarjetas_jugadores_por_equipo":
                jugadores_por_equipo,
        }
    )
    
def lista_partidos(request):
    buscar = request.GET.get('buscar')
    partidos = Partido.objects.select_related(
        'torneo',
        'equipo_local',
        'equipo_visitante',
        'cancha'
    ).filter(
        goles_local__isnull=False,
        goles_visitante__isnull=False
    )

    partidos_totales = partidos

    if buscar:
        filtros = (
            Q(equipo_local__nombre__icontains=buscar)
            | Q(equipo_visitante__nombre__icontains=buscar)
            | Q(torneo__nombre__icontains=buscar)
            | Q(cancha__nombre__icontains=buscar)
            | Q(descripcion__icontains=buscar)
        )

        if buscar.isdigit():
            filtros = (
                filtros
                | Q(goles_local=int(buscar))
                | Q(goles_visitante=int(buscar))
            )

        partidos = partidos.filter(filtros)

    partidos = partidos.order_by("-fecha", "-hora")

    return render(request, "partidos/partidos.html", {
        "partidos": partidos,
        "hay_partidos": partidos_totales.exists()
    })


@admin_required
def editar_partido(request, id):

    partido = get_object_or_404(
        Partido.objects.select_related(
            "equipo_local",
            "equipo_visitante"
        ),
        id=id
    )

    if request.method == "POST":

        form = Editar_Resultado_Partido(
            request.POST,
            instance=partido
        )

        tarjetas_formset = TarjetaPartidoFormSet(
            request.POST,
            instance=partido,
            prefix="tarjetas"
        )

        goles_formset = GolPartidoFormSet(
            request.POST,
            instance=partido,
            prefix="goles"
        )

        if (
            form.is_valid()
            and tarjetas_formset.is_valid()
            and goles_formset.is_valid()
        ):

            with transaction.atomic():

                form.save()

                tarjetas_formset.save()

                goles_formset.save()

            return redirect("partidos")

    else:

        form = Editar_Resultado_Partido(
            instance=partido
        )

        tarjetas_formset = TarjetaPartidoFormSet(
            instance=partido,
            prefix="tarjetas"
        )

        goles_formset = GolPartidoFormSet(
            instance=partido,
            prefix="goles"
        )

    equipos_por_partido, jugadores_por_equipo = (
        _datos_partido_para_widget([partido])
    )

    return render(
        request,
        "partidos/editar_partido.html",
        {
            "form": form,

            "partido": partido,

            "tarjetas_formset":
                tarjetas_formset,

            "goles_formset":
                goles_formset,

            # Goles
            "goles_equipos_por_partido":
                equipos_por_partido,

            "goles_jugadores_por_equipo":
                jugadores_por_equipo,

            "goles_partido_actual_id":
                partido.pk,

            # Tarjetas
            "tarjetas_equipos_por_partido":
                equipos_por_partido,

            "tarjetas_jugadores_por_equipo":
                jugadores_por_equipo,
        }
    )
@admin_required
@require_POST
def eliminar_partido(request, id):
    partido = get_object_or_404(Partido, id=id)
    partido.tarjetas.all().delete()
    partido.goles.all().delete()
    partido.goles_local = None
    partido.goles_visitante = None
    partido.save()

    return JsonResponse({
        'success': True
    })

def lista_fechas(request):
    buscar = request.GET.get('buscar')
    fechas = Partido.objects.filter(goles_local__isnull=True, goles_visitante__isnull=True).select_related(
        'torneo',
        'equipo_local',
        'equipo_visitante',
        'cancha'
    ).order_by("fecha", "hora")

    fechas_totales = fechas

    if buscar:
        filtros = (
            Q(equipo_local__nombre__icontains=buscar)
            | Q(equipo_visitante__nombre__icontains=buscar)
            | Q(torneo__nombre__icontains=buscar)
            | Q(cancha__nombre__icontains=buscar)
            | Q(descripcion__icontains=buscar)
        )
        fechas = fechas.filter(filtros)

    return render(request, "partidos/fechas.html", {
        "fechas": fechas,
        "hay_fechas": fechas_totales.exists()
    })


@admin_required
def crear_fecha(request):
    if request.method == "POST":
        form = Programar_Partido(request.POST)

        if form.is_valid():
            form.save()
            return redirect("partidos_fechas")
    else:
        form = Programar_Partido()

    return render(request, "partidos/crear_fecha.html", {
        "form": form
    })


@admin_required
def editar_fecha(request, id):
    partido = get_object_or_404(Partido, id=id)

    if request.method == "POST":
        form = Programar_Partido(request.POST, instance=partido)

        if form.is_valid():
            form.save()
            return redirect("partidos_fechas")
    else:
        form = Programar_Partido(instance=partido)

    return render(request, "partidos/editar_fecha.html", {
        "form": form,
        "partido": partido
    })


@admin_required
@require_POST
def eliminar_fecha(request, id):
    partido = get_object_or_404(Partido, id=id)
    partido.delete()

    return JsonResponse({
        'success': True
    })

'''    
# arbitro

@admin_required
def ingresar_arbitro(request):
    if request.method == "POST":
        form = Ingresar_Arbitros(request.POST, request.FILES)

        if form.is_valid():
            arbitro = form.save()
            return redirect('arbitros')

    else:
        form = Ingresar_Arbitros()

    return render(request, "arbitros/ingresar_arbitro.html", {
        "form": form
    })
    
@admin_required
def editar_arbitro(request, id):
    arbitro = get_object_or_404(Arbitro, id=id)

    if request.method == "POST":
        form = Ingresar_Arbitros(
            request.POST,
            request.FILES,
            instance=arbitro
        )

        if form.is_valid():
            form.save()
            return redirect('arbitros')

    else:
        form = Ingresar_Arbitros(instance=arbitro)

    return render(request, "arbitros/editar_arbitro.html", {
        "form": form,
        "arbitro": arbitro
    })
@admin_required
def eliminar_arbitro(request, id):
    arbitro = get_object_or_404(Arbitro, id=id)
    arbitro.delete()

    return redirect("arbitros")

@usuario_autorizado_required
def arbitros(request):

    buscar = request.GET.get("buscar")

    if buscar:
        arbitros = Arbitro.objects.filter(
            nombre__icontains=buscar
        )
    else:
        arbitros = Arbitro.objects.all()

    return render(request, "arbitros/arbitros.html", {
        "arbitros": arbitros
    })
'''