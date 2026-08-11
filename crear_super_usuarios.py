from django.contrib.auth import get_user_model

User = get_user_model()

usuarios = [
    {
        "username": "Nelson",
        "email": "ncarcamo794@gmail.cl",
        "password": "@carcamo123",
    }
]

for datos in usuarios:
    if not User.objects.filter(username=datos["username"]).exists():
        User.objects.create_superuser(
            username=datos["username"],
            email=datos["email"],
            password=datos["password"],
        )