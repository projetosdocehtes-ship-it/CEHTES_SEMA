from rest_framework import serializers

from .models import (
    CenarioSimulacao,
    Componente,
    Fabricante,
    HistoricoSugestaoIA,
    Projeto,
    ProjetoDiagrama,
    TipoComponente,
)


class FabricanteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Fabricante
        fields = ["id", "nome"]


class TipoComponenteSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoComponente
        fields = ["id", "codigo", "nome"]


class ComponenteSerializer(serializers.ModelSerializer):
    fabricante_nome = serializers.CharField(source="fabricante.nome", read_only=True)
    tipo_nome = serializers.CharField(source="tipo.nome", read_only=True)
    tipo_codigo = serializers.CharField(source="tipo.codigo", read_only=True)

    class Meta:
        model = Componente
        fields = [
            "id",
            "fabricante",
            "fabricante_nome",
            "tipo",
            "tipo_nome",
            "tipo_codigo",
            "nome_modelo",
            "descricao",
            "ativo",
            "potencia_kw",
            "tensao_nominal_v",
            "corrente_nominal_a",
            "energia_kwh",
            "modo_operacao",
        ]


class ProjetoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Projeto
        fields = ["id", "nome", "descricao", "criado_em", "atualizado_em"]


class ProjetoDiagramaSerializer(serializers.ModelSerializer):
    projeto_nome = serializers.CharField(source="projeto.nome", read_only=True)

    class Meta:
        model = ProjetoDiagrama
        fields = ["id", "projeto", "projeto_nome", "layout_json", "simulacao_json"]


class HistoricoSugestaoIASerializer(serializers.ModelSerializer):
    class Meta:
        model = HistoricoSugestaoIA
        fields = ["id", "projeto", "prompt", "nome_arquivo", "cidade", "modelo_json", "layout_json", "criado_em"]


class CenarioSimulacaoSerializer(serializers.ModelSerializer):
    projeto_nome = serializers.CharField(source="projeto.nome", read_only=True)

    class Meta:
        model = CenarioSimulacao
        fields = [
            "id",
            "projeto",
            "projeto_nome",
            "nome",
            "descricao",
            "modelo_origem",
            "modelo_json",
            "layout_json",
            "resultado_json",
            "criado_em",
        ]
