from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    CenarioSimulacaoViewSet,
    ComponenteViewSet,
    FabricanteViewSet,
    HistoricoSugestaoIAViewSet,
    ProjetoViewSet,
    TipoComponenteViewSet,
    analise_financeira_view,
    aneel_dados_view,
    fluxo_potencia_microrredes_view,
    transitorio_microrredes_view,
    gerar_json_modelo_view,
    simular_view,
    equipamentos_view,
)

router = DefaultRouter()
router.register(r"fabricantes", FabricanteViewSet)
router.register(r"tipos", TipoComponenteViewSet)
router.register(r"componentes", ComponenteViewSet)
router.register(r"projetos", ProjetoViewSet)
router.register(r"historico-ia", HistoricoSugestaoIAViewSet)
router.register(r"cenarios", CenarioSimulacaoViewSet)

urlpatterns = [
    path('equipamentos/simular/', equipamentos_view, name='equipamentos_simular'),
    path("", include(router.urls)),
    path("simular/", simular_view, name="simular_view"),
    path("gerar-json-modelo/", gerar_json_modelo_view, name="gerar_json_modelo_view"),
    path("analise-financeira/", analise_financeira_view, name="analise_financeira_view"),
    path("microrredes/fluxo-potencia/", fluxo_potencia_microrredes_view, name="fluxo_potencia_microrredes_view"),
    path("microrredes/transitorio/", transitorio_microrredes_view, name="transitorio_microrredes_view"),
    path("aneel-dados/", aneel_dados_view, name="aneel_dados_view"),
]
