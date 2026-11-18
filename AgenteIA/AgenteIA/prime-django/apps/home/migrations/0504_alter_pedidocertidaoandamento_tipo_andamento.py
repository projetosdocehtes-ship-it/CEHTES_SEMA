import django.db.models.deletion
from django.db import migrations, models


def create_missing_tipo_andamento(apps, schema_editor):
    PedidoCertidaoAndamento = apps.get_model("home", "PedidoCertidaoAndamento")
    TipoAndamentoCertidao = apps.get_model("home", "TipoAndamentoCertidao")

    # Obter todos os códigos de tipo_andamento existentes em PedidoCertidaoAndamento
    andamento_codigos = PedidoCertidaoAndamento.objects.values_list("tipo_andamento", flat=True).distinct()

    # Verificar e criar tipos de andamento faltantes
    for codigo in andamento_codigos:
        if not TipoAndamentoCertidao.objects.filter(codigo=codigo).exists():
            TipoAndamentoCertidao.objects.create(
                codigo=codigo, descricao=f"Descricao padrão para {codigo}"
            )  # Ajuste conforme necessário


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0503_alter_tipoandamentocertidao_grupo_cancelado_and_more"),
    ]

    operations = [
        migrations.RunPython(create_missing_tipo_andamento),
        migrations.AlterField(
            model_name="pedidocertidaoandamento",
            name="tipo_andamento",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to="home.TipoAndamentoCertidao", to_field="codigo"
            ),
        ),
    ]
