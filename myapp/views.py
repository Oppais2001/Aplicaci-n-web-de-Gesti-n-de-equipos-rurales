from django.shortcuts import render, redirect, get_object_or_404
from .models import Equipo, Jugador, Traspaso
from .forms import Ingresar_Equipos, Ingresar_Jugadores, Realizar_Traspasos, Editar_Jugador

def home(request):
    equipos = Equipo.objects.all()
    total_equipos = len(equipos)
    total_jugadores = len(Jugador.objects.all())
    
    lista_equipos_dict = {}
    
    #
    for equipo in equipos:
        nombre_equipo = equipo.nombre
        cantidad_jugadores = len(Jugador.objects.filter(equipo=equipo))
        lista_equipos_dict[nombre_equipo] = cantidad_jugadores
        print(nombre_equipo, cantidad_jugadores)

    return render(request, 'home.html', {
        'equipos': lista_equipos_dict,
        'total_equipos': total_equipos,
        'total_jugadores': total_jugadores
    })

def about(request):
    return render(request, 'about.html')
    
def lista_equipos(request):
    buscar = request.GET.get('buscar')

    if buscar:
        equipos = Equipo.objects.filter(nombre__icontains=buscar)
    else:
        equipos = Equipo.objects.all()

    return render(request, "equipos/equipos.html", {
        "equipos": equipos
    })


def detalle_equipo(request, equipo):
    equipo = Equipo.objects.get(nombre=equipo)
    buscar = request.GET.get('buscar')

    if buscar:
        jugadores = Jugador.objects.filter(nombre__icontains=buscar, equipo=equipo)
    else:
        jugadores = Jugador.objects.filter(equipo=equipo)

    return render(request, "equipos/detalle_equipo.html", {
        "jugadores": jugadores,
        "equipo": equipo
    }) 
    

def ingresar_equipo(request):
    if request.method == "POST":
        form = Ingresar_Equipos(request.POST)

        if form.is_valid():
            form.save()
            return redirect('equipos')
    else:
        form = Ingresar_Equipos()

    return render(request, "equipos/ingresar_equipo.html", {
        "form": form
    })
    
def eliminar_equipo(request, nombre):
    equipo = get_object_or_404(Equipo, nombre__iexact=nombre)
    equipo.delete()
    return redirect('equipos')
    
def ingresar_jugador(request):
    if request.method == "POST":
        form = Ingresar_Jugadores(request.POST)

        if form.is_valid():
            jugador = form.save()
            equipo_id = jugador.equipo.nombre
            return redirect('detalle_equipo', equipo=equipo_id)
    else:
        form = Ingresar_Jugadores()

    return render(request, "jugadores/ingresar_jugador.html", {
        "form": form
    })
    
def eliminar_jugador(request, rut):
    jugador = get_object_or_404(Jugador, rut = rut)
    equipo = jugador.equipo.nombre
    jugador.delete()
    return redirect('detalle_equipo', equipo=equipo)

def traspasos(request):
    buscar = request.GET.get('buscar')

    if buscar:
        traspasos = Traspaso.objects.filter(jugador__nombre__icontains=buscar)
    else:
        traspasos = Traspaso.objects.all()
                 
    return render(request, 'traspasos/traspasos.html', {
        'traspasos': traspasos
    })
    
def realizar_traspaso(request):
    if request.method == "POST":
        form = Realizar_Traspasos(request.POST)

        if form.is_valid():
            form.save()
            
            return redirect('traspasos')
    else:
        form = Realizar_Traspasos()

    return render(request, "traspasos/realizar_traspaso.html", {
        "form": form
    })
    
    
def editar_jugador(request, id):
    jugador = get_object_or_404(Jugador, id=id)

    if request.method == 'POST':
        form = Editar_Jugador(request.POST, instance=jugador)

        if form.is_valid():
            form.save()
            return redirect('detalle_equipo', jugador.equipo.nombre)

    else:
        form = Editar_Jugador(instance=jugador)

    return render(request, 'jugadores/editar_jugador.html', {
        'form': form,
        'jugador': jugador
    })