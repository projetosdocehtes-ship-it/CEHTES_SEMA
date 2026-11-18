import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0409_alter_unidade_tipo"),
    ]

    operations = [
        migrations.AlterField(
            model_name="unidade",
            name="tipo",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="tipo_de_unidadade",
                to="home.tipounidade",
            ),
        ),
    ]
