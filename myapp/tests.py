from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Dirigente, Equipo, Liga
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
