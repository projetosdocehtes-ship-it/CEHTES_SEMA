import logging

from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view
from rest_framework.response import Response

from .models import (
    CenarioSimulacao,
    Componente,
    Fabricante,
    HistoricoSugestaoIA,
    Projeto,
    ProjetoDiagrama,
    TipoComponente,
)
from .serializers import (
    CenarioSimulacaoSerializer,
    ComponenteSerializer,
    FabricanteSerializer,
    HistoricoSugestaoIASerializer,
    ProjetoDiagramaSerializer,
    ProjetoSerializer,
    TipoComponenteSerializer,
)
from .services import executar_analise_financeira, executar_fluxo_potencia_microrredes, gerar_diagrama_base, gerar_modelo_entradas, simular_diagrama

logger = logging.getLogger(__name__)


class FabricanteViewSet(viewsets.ModelViewSet):
    queryset = Fabricante.objects.all()
    serializer_class = FabricanteSerializer


class TipoComponenteViewSet(viewsets.ModelViewSet):
    queryset = TipoComponente.objects.all()
    serializer_class = TipoComponenteSerializer


class ComponenteViewSet(viewsets.ModelViewSet):
    queryset = Componente.objects.select_related("fabricante", "tipo").all()
    serializer_class = ComponenteSerializer


class ProjetoViewSet(viewsets.ModelViewSet):
    queryset = Projeto.objects.all()
    serializer_class = ProjetoSerializer

    @action(detail=True, methods=["get", "post"], url_path="diagrama")
    def diagrama(self, request, pk=None):
        projeto = self.get_object()
        diagrama, _ = ProjetoDiagrama.objects.get_or_create(
            projeto=projeto,
            defaults={"layout_json": {"nodes": [], "edges": []}, "simulacao_json": {}},
        )

        if request.method == "GET":
            return Response(ProjetoDiagramaSerializer(diagrama).data)

        layout_json = request.data.get("layout_json", {"nodes": [], "edges": []})
        simulacao = simular_diagrama(layout_json, projeto.nome)
        diagrama.layout_json = layout_json
        diagrama.simulacao_json = simulacao
        diagrama.save(update_fields=["layout_json", "simulacao_json"])
        return Response(ProjetoDiagramaSerializer(diagrama).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="gerar-diagrama-base")
    def gerar_diagrama_base_action(self, request, pk=None):
        projeto = self.get_object()
        diagrama, _ = ProjetoDiagrama.objects.get_or_create(
            projeto=projeto,
            defaults={"layout_json": {"nodes": [], "edges": []}, "simulacao_json": {}},
        )
        layout_json = gerar_diagrama_base()
        simulacao = simular_diagrama(layout_json, projeto.nome)
        diagrama.layout_json = layout_json
        diagrama.simulacao_json = simulacao
        diagrama.save(update_fields=["layout_json", "simulacao_json"])
        return Response(ProjetoDiagramaSerializer(diagrama).data, status=status.HTTP_200_OK)


class HistoricoSugestaoIAViewSet(viewsets.ModelViewSet):
    queryset = HistoricoSugestaoIA.objects.select_related("projeto").all()
    serializer_class = HistoricoSugestaoIASerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        projeto_id = self.request.query_params.get("projeto")
        busca = self.request.query_params.get("busca")
        if projeto_id:
            queryset = queryset.filter(projeto_id=projeto_id)
        if busca:
            queryset = queryset.filter(prompt__icontains=busca)
        return queryset


class CenarioSimulacaoViewSet(viewsets.ModelViewSet):
    queryset = CenarioSimulacao.objects.select_related("projeto").all()
    serializer_class = CenarioSimulacaoSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        projeto_id = self.request.query_params.get("projeto")
        if projeto_id:
            queryset = queryset.filter(projeto_id=projeto_id)
        return queryset


@api_view(["POST"])
def simular_view(request):
    layout_json = request.data.get("layout_json", {"nodes": [], "edges": []})
    nome_projeto = request.data.get("nome_projeto", "Projeto Simulador")
    return Response(simular_diagrama(layout_json, nome_projeto))


@api_view(["POST"])
def gerar_json_modelo_view(request):
    layout_json = request.data.get("layout_json", {"nodes": [], "edges": []})
    nome_projeto = request.data.get("nome_projeto", "Projeto Simulador")
    return Response(gerar_modelo_entradas(layout_json, nome_projeto))


@api_view(["POST"])
def analise_financeira_view(request):
    layout_json = request.data.get("layout_json", {"nodes": [], "edges": []})
    nome_projeto = request.data.get("nome_projeto", "Projeto Simulador")
    modelo_entradas = request.data.get("modelo_entradas")
    modelo_origem = request.data.get("modelo_origem")
    try:
        return Response(
            executar_analise_financeira(
                layout_json,
                nome_projeto,
                modelo_entradas=modelo_entradas,
                modelo_origem=modelo_origem,
            )
        )
    except Exception as error:
        logger.exception("Erro ao gerar análise financeira")
        return Response({"erro": str(error)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["POST"])
def fluxo_potencia_microrredes_view(request):
    layout_json = request.data.get("layout_json", {"nodes": [], "edges": []})
    nome_projeto = request.data.get("nome_projeto", "Projeto Simulador")
    modelo_entradas = request.data.get("modelo_entradas")
    try:
        if modelo_entradas is None:
            modelo_entradas = gerar_modelo_entradas(layout_json, nome_projeto)
        return Response(executar_fluxo_potencia_microrredes(modelo_entradas))
    except Exception as error:
        logger.exception("Erro ao executar fluxo de potência no projeto microrredes")
        return Response({"erro": str(error)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["POST"])
def transitorio_microrredes_view(request):
    from .transitorio import executar_transitorio
    try:
        return Response(executar_transitorio(request.data.get('modelo_entradas'), request.data.get('cenario')))
    except (ValueError, TypeError, KeyError) as error:
        return Response({'erro': str(error)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as error:
        logger.exception('Erro no ensaio transitório')
        return Response({'erro': str(error)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def equipamentos_view(request):
    from .equipamentos import executar_equipamentos, modelo_do_layout
    try:
        modelo = request.data.get('modelo_entradas')
        if request.data.get('layout_json') is not None:
            modelo = modelo_do_layout(modelo, request.data['layout_json'])
        return Response(executar_equipamentos(modelo, request.data.get('configuracao')))
    except (ValueError, TypeError, KeyError) as error:
        return Response({'erro': str(error)}, status=400)
    except Exception as error:
        logger.exception('Erro no motor Equipamentos')
        return Response({'erro': str(error)}, status=500)


@api_view(["GET"])
def aneel_dados_view(request):
    cidade = str(request.query_params.get("cidade", "")).strip()
    uf = str(request.query_params.get("uf", "")).strip().upper()
    distribuidora = str(request.query_params.get("distribuidora", "")).strip()
    return Response(
        {
            "parametros": {"cidade": cidade, "uf": uf, "distribuidora": distribuidora},
            "distribuidora_sugerida": distribuidora or f"Distribuidora de referência {uf or 'BR'}",
            "tarifas_referencia": {
                "grupo_a_verde": {"consumo_ponta": 1.25, "consumo_fora_ponta": 0.68, "demanda": 42.5},
                "grupo_a_azul": {"consumo_ponta": 1.25, "consumo_fora_ponta": 0.68, "demanda_ponta": 65.0, "demanda_fora_ponta": 32.0},
                "grupo_b_convencional": {"consumo": 0.72},
                "grupo_b_branca": {"consumo_fora_ponta": 0.62, "consumo_intermediario": 0.82, "consumo_ponta": 1.1},
            },
            "observacao": "Referência local para apoiar a simulação. Substitua pelos valores oficiais da distribuidora quando disponíveis.",
        }
    )
