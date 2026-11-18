# urls.py no aplicativo 'minutas_atos'
from django.urls import path

from apps.minutas_atos import views

app_name = "minutas_atos"

urlpatterns = [
    path(
        "adicionar/",
        views.MinutaAtoCreateView.as_view(),
        name="adicionar_minuta_ato",
    ),
    path(
        "editar/<uuid:pk>/",
        views.MinutaAtoUpdateView.as_view(),
        name="editar_minuta_ato",
    ),
    path(
        "editar_minuta_estado_civil/<uuid:pk>/",
        views.EstadoCivilUpdateView.as_view(),
        name="editar_minuta_estado_civil",
    ),
    path("remover/<uuid:pk>/", views.MinutaAtoDeleteView.as_view(), name="remover_ato"),
    path(
        "vincular_minuta_ato/<str:pk>/",
        views.MinutaAtoLigacaoCreateView.as_view(),
        name="vincular_minuta_ato",
    ),
    path(
        "mensagem_minuta_ato/",
        views.MensagemMinutaAtoView.as_view(),
        name="mensagem_minuta_ato",
    ),
    path(
        "modelo/<uuid:modelo_id>/<int:pedido_item_id>/impressao/",
        views.exibir_modelo_para_impressao,
        name="modelo_impressao",
    ),
    path(
        "modelo/<uuid:modelo_id>/<uuid:pedido_item_id>/impressao/",
        views.exibir_modelo_para_impressao,
        name="modelo_exibir_minuta",
    ),
    path(
        "exibir_perguntas_minuta_lv2/<pedido_item_id>/<modelo_id>/<lista_perguntas_atuais>/",
        views.exibir_perguntas_minuta_lv2,
        name="exibir_perguntas_minuta_lv2",
    ),
    path(
        "imprimir_respostas_tela/pedido_item/<str:pedido_item_id>/modelo/<uuid:modelo_id>/",
        views.imprimir_respostas_tela,
        name="imprimir_respostas_tela",
    ),
    path(
        "listar_estado_civil/",
        views.EstadoCivilListView.as_view(),
        name="listar_estado_civil",
    ),
    path(
        "falar_texto_minuta_ato/<str:modelo_id>/",
        views.falar_texto_minuta_ato,
        name="falar_texto_minuta_ato",
    ),
]
