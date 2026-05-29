import json
from django.http import HttpResponseForbidden
from django.http import JsonResponse
from django.db.models import Count, Q
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from .models import Dirigente, Equipo, Jugador, Traspaso, Liga
from .forms import Editar_Dirigentes, Ingresar_Dirigentes, Ingresar_Equipos, Ingresar_Jugadores, Realizar_Traspasos, Ingresar_Liga, Editar_Traspaso
from .permissions import admin_required, es_administrador, obtener_dirigente, usuario_autorizado_required

# HOME Y ABOUT
@usuario_autorizado_required
def home(request):
    if es_administrador(request.user):
        equipos = Equipo.objects.annotate(
            total_jugadores=Count('jugadores')
        ).order_by('nombre')
        total_traspasos = Traspaso.objects.count()
    else:
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

    lista_equipos_dict = {
        equipo.nombre: equipo.total_jugadores
        for equipo in equipos
    }

    return render(request, 'home.html', {
        'equipos': lista_equipos_dict,
        'total_equipos': equipos.count(),
        'total_jugadores': sum(lista_equipos_dict.values()),
        'total_traspasos': total_traspasos
    })

@usuario_autorizado_required
def about(request):
    return render(request, 'about.html')

# EQUIPOS
@admin_required
def ingresar_equipo(request):
    if request.method == "POST":
        form = Ingresar_Equipos(request.POST)

        if form.is_valid():
            form.save()
            return redirect('equipos')
    else:
        form = Ingresar_Equipos()

    return render(request, "equipos/ingresar_equipo.html", {
        "form": form,
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
        'liga': data.get('liga', '')
    })

    if form.is_valid():
        equipo = form.save()

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

@usuario_autorizado_required
def lista_equipos(request):
    buscar = request.GET.get('buscar')
    equipos = Equipo.objects.all()

    if not es_administrador(request.user):
        dirigente = obtener_dirigente(request.user)
        equipos = equipos.filter(id=dirigente.equipo_id)

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
        form = Ingresar_Equipos(request.POST, instance=equipo)
        
        if form.is_valid():
            form.save()
            return redirect('equipos')

    else:
        form = Ingresar_Equipos(instance=equipo)

    return render(request, 'equipos/editar_equipo.html', {
        'form': form,
        'equipo':equipo,
        
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
            form.save()
            return redirect('dirigentes')
    else:
        form = Ingresar_Dirigentes()

    return render(request, "dirigentes/ingresar_dirigente.html", {
        "form": form
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
def ingresar_liga(request):
    if request.method == "POST":
        form = Ingresar_Liga(request.POST)

        if form.is_valid():
            form.save()
            return redirect('ligas')
    else:
        form = Ingresar_Liga()

    return render(request, "ligas/ingresar_liga.html", {
        "form": form
    })


@usuario_autorizado_required
def lista_ligas(request):
    buscar = request.GET.get('buscar')
    ligas = Liga.objects.all()

    if not es_administrador(request.user):
        dirigente = obtener_dirigente(request.user)
        ligas = ligas.filter(id=dirigente.equipo.liga_id)

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
        form = Ingresar_Liga(request.POST, instance=liga)

        if form.is_valid():
            form.save()
            return redirect('ligas')
    else:
        form = Ingresar_Liga(instance=liga)

    return render(request, "ligas/editar_liga.html", {
        "form": form,
        "liga": liga
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
            'success': False,
            'error': 'Datos inválidos'
        }, status=400)

    form = Ingresar_Liga(data)
        
    if form.is_valid():

        liga = form.save()

        return JsonResponse({

            'success': True,

            'id': liga.id,

            'nombre': liga.nombre
        })

    mensajes = [
        error
        for errores_campo in form.errors.values()
        for error in errores_campo
    ]

    return JsonResponse({

        'success': False,
        'error': '\n'.join(mensajes),
        'mensajes': mensajes,
        'errores': form.errors
    }, status=400)
    
@usuario_autorizado_required
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
@usuario_autorizado_required
def detalle_equipo(request, equipo):
    equipo = get_object_or_404(Equipo, nombre=equipo)

    if not es_administrador(request.user):
        dirigente = obtener_dirigente(request.user)

        if equipo.id != dirigente.equipo_id:
            return HttpResponseForbidden("Solo puedes ver jugadores de tu equipo.")

    buscar = request.GET.get('buscar')
    jugadores_totales = Jugador.objects.filter(equipo=equipo)

    if buscar:
        jugadores = Jugador.objects.filter(nombre__icontains=buscar, equipo=equipo)
    else:
        jugadores = Jugador.objects.filter(equipo=equipo)

    return render(request, "equipos/detalle_equipo.html", {
        "jugadores": jugadores,
        "equipo": equipo,
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
    
@usuario_autorizado_required
def traspasos(request):
    buscar = request.GET.get('buscar')
    traspasos = Traspaso.objects.select_related(
        'jugador',
        'equipo_origen',
        'equipo_destino'
    )

    if not es_administrador(request.user):
        dirigente = obtener_dirigente(request.user)
        traspasos = traspasos.filter(
            Q(equipo_origen=dirigente.equipo)
            | Q(equipo_destino=dirigente.equipo)
            | Q(jugador__equipo=dirigente.equipo)
        ).distinct()

    traspasos_totales = traspasos

    if buscar:
        traspasos = traspasos.filter(jugador__nombre__icontains=buscar)
                 
    return render(request, 'traspasos/traspasos.html', {
        'traspasos': traspasos,
        'hay_traspasos': traspasos_totales.exists()
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
    
