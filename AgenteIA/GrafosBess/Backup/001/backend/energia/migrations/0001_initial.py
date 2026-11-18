from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Fabricante",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nome", models.CharField(max_length=150, unique=True)),
            ],
            options={"ordering": ["nome"]},
        ),
        migrations.CreateModel(
            name="Projeto",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nome", models.CharField(max_length=200)),
                ("descricao", models.TextField(blank=True)),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
                ("atualizado_em", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["-id"]},
        ),
        migrations.CreateModel(
            name="TipoComponente",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("codigo", models.CharField(max_length=50, unique=True)),
                ("nome", models.CharField(max_length=100)),
            ],
            options={"ordering": ["nome"]},
        ),
        migrations.CreateModel(
            name="ProjetoDiagrama",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("layout_json", models.JSONField(blank=True, default=dict)),
                ("simulacao_json", models.JSONField(blank=True, default=dict)),
                ("projeto", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="diagrama", to="energia.projeto")),
            ],
        ),
        migrations.CreateModel(
            name="Componente",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nome_modelo", models.CharField(max_length=200)),
                ("descricao", models.TextField(blank=True)),
                ("ativo", models.BooleanField(default=True)),
                ("potencia_kw", models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ("tensao_nominal_v", models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ("corrente_nominal_a", models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ("energia_kwh", models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ("modo_operacao", models.CharField(blank=True, max_length=50)),
                ("fabricante", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="componentes", to="energia.fabricante")),
                ("tipo", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="componentes", to="energia.tipocomponente")),
            ],
            options={"ordering": ["tipo__nome", "fabricante__nome", "nome_modelo"]},
        ),
        migrations.AddConstraint(
            model_name="componente",
            constraint=models.UniqueConstraint(fields=("fabricante", "tipo", "nome_modelo"), name="unique_modelo_por_tipo_e_fabricante"),
        ),
    ]
