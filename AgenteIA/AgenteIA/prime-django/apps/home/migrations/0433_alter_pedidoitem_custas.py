import django.db.models.deletion
from django.db import migrations, models


def add_missing_fk_entries(apps, schema_editor):
    # Obter os modelos
    PedidoItem = apps.get_model("home", "PedidoItem")
    TipoTributacao = apps.get_model("home", "TipoTributacao")

    # Obter todos os IDs de 'custas' em PedidoItem
    custas_ids = PedidoItem.objects.values_list("custas", flat=True).distinct()

    # Criar registros em TipoTributacao para IDs ausentes
    for custas_id in custas_ids:
        if custas_id and not TipoTributacao.objects.filter(id=custas_id).exists():
            TipoTributacao.objects.create(id=custas_id, outros_codigo_trib_tj=0, outros="", utilizado="S")


class Migration(migrations.Migration):
    dependencies = [
        ("home", "0432_alter_pedidoitem_tabelacalculo"),
    ]

    operations = [
        migrations.RunPython(add_missing_fk_entries),
        migrations.AlterField(
            model_name="pedidoitem",
            name="custas",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="home.tipotributacao",
            ),
        ),
    ]
