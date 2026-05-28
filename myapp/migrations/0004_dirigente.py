from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0003_jugador_fecha_nacimiento'),
    ]

    operations = [
        migrations.CreateModel(
            name='Dirigente',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=100)),
                ('rut', models.CharField(max_length=12, unique=True)),
                ('telefono', models.CharField(max_length=20)),
                ('correo', models.EmailField(max_length=254, unique=True)),
                ('activo', models.BooleanField(default=True)),
                ('equipo', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='dirigentes', to='myapp.equipo')),
            ],
        ),
    ]
