from datetime import date, time, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import (
    Dirigente,
    Equipo,
    GolPartido,
    Jugador,
    Liga,
    Partido,
    Prestamo,
    TarjetaPartido,
    Torneo,
)
from .views import crear_usuario_para_dirigente


class CredencialesDirigenteTests(TestCase):
    def setUp(self):
        Usuario = get_user_model()
        self.admin = Usuario.objects.create_user(
            username="admin",
            password="adminpass123",
            is_staff=True,
        )
        self.liga = Liga.objects.create(nombre="Liga Test")
        self.equipo = Equipo.objects.create(nombre="Equipo Test", liga=self.liga)

    def test_ingresar_dirigente_marca_usuario_nuevo_y_guarda_password(self):
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse("ingresar_dirigente"),
            {
                "nombre": "Juan Perez Soto",
                "rut": "12345678-5",
                "telefono": "987654321",
                "correo": "juan@example.com",
                "cargo": "Presidente",
                "direccion": "Calle Uno 123",
                "fecha_asuncion": "",
                "activo": "on",
                "equipo": self.equipo.id,
            },
        )

        self.assertRedirects(
            response,
            reverse("credenciales_dirigente"),
            fetch_redirect_response=False,
        )
        credenciales = self.client.session["credenciales_dirigente"]
        self.assertTrue(credenciales["usuario_nuevo"])
        self.assertTrue(credenciales["password"])

    def test_eliminar_dirigente_no_borra_usuario_con_otra_dirigencia(self):
        dirigente_uno = Dirigente.objects.create(
            nombre="Juan Perez Soto",
            rut="123456785",
            telefono="987654321",
            correo="juan@example.com",
            cargo="Presidente",
            equipo=self.equipo,
        )
        usuario, password = crear_usuario_para_dirigente(dirigente_uno)

        dirigente_dos = Dirigente.objects.create(
            nombre="Juan Perez Soto",
            rut="123456785",
            telefono="987654321",
            correo="juan@example.com",
            cargo="Secretario",
            equipo=self.equipo,
            usuario=usuario,
        )

        dirigente_uno.delete()

        self.assertIsNotNone(password)
        self.assertTrue(get_user_model().objects.filter(pk=usuario.pk).exists())
        self.assertTrue(Dirigente.objects.filter(pk=dirigente_dos.pk, usuario=usuario).exists())


@override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
class PrestamoTests(TestCase):
    def setUp(self):
        Usuario = get_user_model()
        self.admin = Usuario.objects.create_user(
            username="admin-prestamos",
            password="adminpass123",
            is_staff=True,
        )
        self.liga = Liga.objects.create(nombre="Liga Test Prestamos")
        self.origen = Equipo.objects.create(nombre="Origen Prestamo", liga=self.liga)
        self.destino = Equipo.objects.create(nombre="Destino Prestamo", liga=self.liga)
        self.jugador = Jugador.objects.create(
            nombre="Jugador Prestamo Test",
            rut="123456785",
            equipo=self.origen,
            fecha_inscripcion=timezone.localdate() - timedelta(days=800),
        )
        self.torneo = Torneo.objects.create(
            nombre="Torneo Prestamo Test",
            fecha_inicio=timezone.localdate(),
            fecha_fin=timezone.localdate() + timedelta(days=30),
        )
        self.torneo.equipos.add(self.destino)

    def test_realizar_prestamo_mueve_jugador_y_guarda_fechas_del_torneo(self):
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse("realizar_prestamo", args=[self.jugador.id]),
            {
                "equipo_destino": self.destino.id,
                "torneo": self.torneo.id,
            },
        )

        self.assertRedirects(response, reverse("prestamos"), fetch_redirect_response=False)
        prestamo = Prestamo.objects.get(jugador=self.jugador)
        self.jugador.refresh_from_db()
        self.assertEqual(self.jugador.equipo, self.destino)
        self.assertEqual(prestamo.equipo_origen, self.origen)
        self.assertEqual(prestamo.fecha_inicio, self.torneo.fecha_inicio)
        self.assertEqual(prestamo.fecha_fin, self.torneo.fecha_fin)
        self.assertTrue(prestamo.activo)

    def test_listado_finaliza_prestamo_vencido_y_devuelve_jugador(self):
        self.jugador.equipo = self.destino
        self.jugador.save()
        prestamo = Prestamo.objects.create(
            jugador=self.jugador,
            equipo_origen=self.origen,
            equipo_destino=self.destino,
            torneo=self.torneo,
            fecha_prestamo=timezone.localdate() - timedelta(days=10),
            fecha_inicio=timezone.localdate() - timedelta(days=10),
            fecha_fin=timezone.localdate() - timedelta(days=1),
            activo=True,
        )

        response = self.client.get(reverse("prestamos"))

        self.assertEqual(response.status_code, 200)
        self.jugador.refresh_from_db()
        prestamo.refresh_from_db()
        self.assertEqual(self.jugador.equipo, self.origen)
        self.assertFalse(prestamo.activo)


@override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
class FechasProgramadasTests(TestCase):
    def setUp(self):
        Usuario = get_user_model()
        self.admin = Usuario.objects.create_user(
            username="admin-fechas",
            password="adminpass123",
            is_staff=True,
        )
        self.liga = Liga.objects.create(
            nombre="Liga Test Fechas"
        )
        self.local = Equipo.objects.create(nombre="Local Test", liga=self.liga)
        self.visita = Equipo.objects.create(nombre="Visita Test", liga=self.liga)
        self.otro = Equipo.objects.create(nombre="Otro Test", liga=self.liga)

    def test_lista_fechas_agrupa_partidos_por_dia(self):
        Partido.objects.create(
            equipo_local=self.local,
            equipo_visitante=self.visita,
            fecha=date(2026, 9, 6),
            hora=time(15, 0),
        )
        Partido.objects.create(
            equipo_local=self.visita,
            equipo_visitante=self.otro,
            fecha=date(2026, 9, 13),
            hora=time(15, 0),
        )
        self.client.force_login(self.admin)

        response = self.client.get(reverse("fechas"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Fecha actual")
        self.assertContains(response, "Fecha siguiente")
        self.assertEqual(len(response.context["fechas_por_dia"]), 2)

    def test_descargar_fechas_dia_imagen_devuelve_png(self):
        Partido.objects.create(
            equipo_local=self.local,
            equipo_visitante=self.visita,
            fecha=date(2026, 9, 6),
            hora=time(15, 0),
        )

        response = self.client.get(
            reverse("descargar_fechas_dia_imagen", args=["2026-09-06"])
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/png")


@override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
class PartidosJugadosTests(TestCase):
    def setUp(self):
        Usuario = get_user_model()
        self.admin = Usuario.objects.create_user(
            username="admin-partidos",
            password="adminpass123",
            is_staff=True,
        )
        self.liga = Liga.objects.create(nombre="Liga Test Partidos")
        self.local = Equipo.objects.create(nombre="Local Jugado", liga=self.liga)
        self.visita = Equipo.objects.create(nombre="Visita Jugado", liga=self.liga)
        self.otro = Equipo.objects.create(nombre="Otro Jugado", liga=self.liga)
        self.jugador_local = Jugador.objects.create(
            nombre="Jugador Local Uno",
            rut="11111111-1",
            equipo=self.local,
        )
        self.jugador_visita = Jugador.objects.create(
            nombre="Jugador Visita Uno",
            rut="22222222-2",
            equipo=self.visita,
        )

    def test_lista_partidos_agrupa_partidos_jugados_por_dia(self):
        Partido.objects.create(
            equipo_local=self.local,
            equipo_visitante=self.visita,
            fecha=date(2026, 9, 13),
            hora=time(15, 0),
            goles_local=2,
            goles_visitante=1,
        )
        Partido.objects.create(
            equipo_local=self.visita,
            equipo_visitante=self.otro,
            fecha=date(2026, 9, 6),
            hora=time(15, 0),
            goles_local=0,
            goles_visitante=3,
        )
        self.client.force_login(self.admin)

        response = self.client.get(reverse("partidos"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Fecha actual")
        self.assertContains(response, "Fecha anterior")
        self.assertEqual(len(response.context["partidos_por_dia"]), 2)

    def test_lista_partidos_muestra_goleadores_y_tarjetas(self):
        partido = Partido.objects.create(
            equipo_local=self.local,
            equipo_visitante=self.visita,
            fecha=date(2026, 9, 13),
            hora=time(15, 0),
            goles_local=1,
            goles_visitante=0,
        )
        GolPartido.objects.create(
            partido=partido,
            equipo=self.local,
            jugador=self.jugador_local,
            minuto=23,
        )
        TarjetaPartido.objects.create(
            partido=partido,
            equipo=self.visita,
            jugador=self.jugador_visita,
            tipo_tarjeta="amarilla",
        )
        self.client.force_login(self.admin)

        response = self.client.get(reverse("partidos"))

        self.assertContains(response, 'class="btn-detalles-partido"')
        self.assertContains(response, f'id="detalle-{partido.pk}"')
        self.assertContains(response, "hidden")
        self.assertContains(response, "Goles")
        self.assertContains(response, "Tarjetas")
        self.assertContains(response, "Jugador Local Uno")
        self.assertContains(response, "23")
        self.assertContains(response, "Jugador Visita Uno")
        self.assertContains(response, "Amarilla")

    def test_descargar_partidos_dia_imagen_devuelve_png(self):
        Partido.objects.create(
            equipo_local=self.local,
            equipo_visitante=self.visita,
            fecha=date(2026, 9, 13),
            hora=time(15, 0),
            goles_local=2,
            goles_visitante=1,
        )

        response = self.client.get(
            reverse("descargar_partidos_dia_imagen", args=["2026-09-13"])
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/png")

    def test_editar_partido_permite_agregar_goles_y_tarjetas(self):
        partido = Partido.objects.create(
            equipo_local=self.local,
            equipo_visitante=self.visita,
            fecha=date(2026, 9, 13),
            hora=time(15, 0),
            goles_local=0,
            goles_visitante=0,
        )
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse("editar_partido", args=[partido.pk]),
            {
                "goles_local": "1",
                "goles_visitante": "0",
                "descripcion": "Resultado corregido",
                "goles-TOTAL_FORMS": "1",
                "goles-INITIAL_FORMS": "0",
                "goles-MIN_NUM_FORMS": "0",
                "goles-MAX_NUM_FORMS": "1000",
                "goles-0-equipo": str(self.local.pk),
                "goles-0-jugador": str(self.jugador_local.pk),
                "goles-0-minuto": "23",
                "tarjetas-TOTAL_FORMS": "1",
                "tarjetas-INITIAL_FORMS": "0",
                "tarjetas-MIN_NUM_FORMS": "0",
                "tarjetas-MAX_NUM_FORMS": "1000",
                "tarjetas-0-equipo": str(self.visita.pk),
                "tarjetas-0-jugador": str(self.jugador_visita.pk),
                "tarjetas-0-tipo_tarjeta": "amarilla",
            },
        )

        self.assertRedirects(response, reverse("partidos"))
        partido.refresh_from_db()
        self.assertEqual(partido.goles_local, 1)
        self.assertEqual(partido.goles_visitante, 0)
        self.assertEqual(partido.descripcion, "Resultado corregido")
        self.assertEqual(GolPartido.objects.filter(partido=partido).count(), 1)
        self.assertEqual(TarjetaPartido.objects.filter(partido=partido).count(), 1)

    def test_editar_partido_permite_marcador_sin_registrar_goleadores(self):
        partido = Partido.objects.create(
            equipo_local=self.local,
            equipo_visitante=self.visita,
            fecha=date(2026, 9, 13),
            hora=time(15, 0),
            goles_local=0,
            goles_visitante=0,
        )
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse("editar_partido", args=[partido.pk]),
            {
                "goles_local": "3",
                "goles_visitante": "1",
                "descripcion": "Sin detalle de goleadores",
                "goles-TOTAL_FORMS": "0",
                "goles-INITIAL_FORMS": "0",
                "goles-MIN_NUM_FORMS": "0",
                "goles-MAX_NUM_FORMS": "1000",
                "tarjetas-TOTAL_FORMS": "0",
                "tarjetas-INITIAL_FORMS": "0",
                "tarjetas-MIN_NUM_FORMS": "0",
                "tarjetas-MAX_NUM_FORMS": "1000",
            },
        )

        self.assertRedirects(response, reverse("partidos"))
        partido.refresh_from_db()
        self.assertEqual(partido.goles_local, 3)
        self.assertEqual(partido.goles_visitante, 1)
        self.assertEqual(GolPartido.objects.filter(partido=partido).count(), 0)

    def test_editar_partido_no_permite_mas_goles_detallados_que_marcador(self):
        partido = Partido.objects.create(
            equipo_local=self.local,
            equipo_visitante=self.visita,
            fecha=date(2026, 9, 13),
            hora=time(15, 0),
            goles_local=0,
            goles_visitante=0,
        )
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse("editar_partido", args=[partido.pk]),
            {
                "goles_local": "1",
                "goles_visitante": "0",
                "descripcion": "",
                "goles-TOTAL_FORMS": "2",
                "goles-INITIAL_FORMS": "0",
                "goles-MIN_NUM_FORMS": "0",
                "goles-MAX_NUM_FORMS": "1000",
                "goles-0-equipo": str(self.local.pk),
                "goles-0-jugador": str(self.jugador_local.pk),
                "goles-0-minuto": "23",
                "goles-1-equipo": str(self.local.pk),
                "goles-1-jugador": str(self.jugador_local.pk),
                "goles-1-minuto": "34",
                "tarjetas-TOTAL_FORMS": "0",
                "tarjetas-INITIAL_FORMS": "0",
                "tarjetas-MIN_NUM_FORMS": "0",
                "tarjetas-MAX_NUM_FORMS": "1000",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "El equipo local tiene 1 goles en el marcador",
        )
        self.assertEqual(GolPartido.objects.filter(partido=partido).count(), 0)

    def test_editar_partido_entrega_partido_actual_al_widget_tarjetas(self):
        partido = Partido.objects.create(
            equipo_local=self.local,
            equipo_visitante=self.visita,
            fecha=date(2026, 9, 13),
            hora=time(15, 0),
            goles_local=0,
            goles_visitante=0,
        )
        self.client.force_login(self.admin)

        response = self.client.get(reverse("editar_partido", args=[partido.pk]))

        self.assertContains(
            response,
            f'data-partido-actual="{partido.pk}"',
            count=2,
        )
