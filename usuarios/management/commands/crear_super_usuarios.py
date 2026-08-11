from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = "Crea los superusuarios iniciales"

    def handle(self, *args, **options):
        User = get_user_model()

        usuarios = [
            {
                "username": "Nelson",
                "email": "ncarcamo794@gmail.cl",
                "password": "@carcamo123",
            },
        ]

        for datos in usuarios:
            if not User.objects.filter(username=datos["username"]).exists():
                User.objects.create_superuser(
                    username=datos["username"],
                    email=datos["email"],
                    password=datos["password"],
                )

                self.stdout.write(
                    self.style.SUCCESS(
                        f"Superusuario '{datos['username']}' creado correctamente."
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f"El usuario '{datos['username']}' ya existe."
                    )
                )