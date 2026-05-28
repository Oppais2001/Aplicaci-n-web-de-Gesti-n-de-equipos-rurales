from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0006_dirigente_usuario'),
    ]

    operations = [
        migrations.AlterField(
            model_name='dirigente',
            name='usuario',
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to=settings.AUTH_USER_MODEL
            ),
        ),
    ]
