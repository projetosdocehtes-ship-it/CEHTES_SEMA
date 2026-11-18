import logging

from django.urls import path

from apps.pedidos.views import (
    ApresentanteCreateView,
    ApresentanteListView,
    ApresentanteLocateView,
    ApresentanteUpdateView,
    AtoComplementarDetailView,
    AtoDeleteView,
    AtoPartesListView,
    AtosListView,
    DocumentoParaRequerimentoCreateView,
    DocumentoParaRequerimentoDeleteView,
    DocumentoParaRequerimentoDetailView,
    DocumentoParaRequerimentoListView,
    DocumentoParaRequerimentoPrintView,
    DocumentoParaRequerimentoUpdateView,
    DuplicarPedidodeProtocoloView,
    EventoAddView,
    EventoUpdateView,
    ImovelCreateView,
    ImovelDeleteView,
    ImovelDetailView,
    ImovelListView,
    ImovelUpdateView,
    ParteDeleteView,
    ParteDetailView,
    ParteUpdateView,
    ParticipacaoDeleteView,
    ParticipacoesListView,
    PedidoExportarView,
    PedidoPartesListView,
    PedidoPartesProtocoloListView,
    PedidoReciboDetailProtocoloView,
    PedidoReciboDetailView,
    PedidoRelatorioView,
    PedidosListView,
    RequerimentoCreateView,
    RequerimentoDeleteView,
    RequerimentoDetailView,
    RequerimentoListView,
    RequerimentoPedidoPrintView,
    RequerimentoPrintView,
    RequerimentoUpdateView,
    ato_complementar_create,
    ato_create,
    ato_detail_view,
    ato_participacao_create_view,
    ato_participacao_update_view,
    ato_update_view,
    audit_report,
    desativar_apresentante,
    duplicar_ato_protocolo,
    duplicar_ato_protocolo_quantidade,
    listar_atos_por_numero_protocolo,
    pedido_create,
    pedido_detail,
    pedido_protocolar_view,
    pedido_protocolo_cancelar,
    remove_participacao,
    seleciona_apresentante,
    test_view,
)

logger = logging.getLogger(__name__)

logger.debug(f"Iniciando {__name__}")

app_name = "pedidos"


# URLs de Auditorias
urlpatterns = [
    path("test/", test_view, name="test_view"),
    path("audit-report/", audit_report, name="audit_report"),
]


# ! URLs do Pedido
urlpatterns += [
    path("", PedidosListView.as_view(), name="pedidos_list"),
    path("create/", pedido_create, name="pedido_create"),
    path("<uuid:pk>/detail/", pedido_detail, name="pedido_detail"),
    path("<uuid:pk>/export/", PedidoExportarView.as_view(), name="pedido_export"),
    path(
        "<uuid:pk>/duplicar_pedido/",
        DuplicarPedidodeProtocoloView.as_view(),
        name="duplicar_pedido_de_protocolo",
    ),
    path(
        "<int:numero_protocolo>/recibo/print",
        PedidoReciboDetailProtocoloView.as_view(),
        name="pedido_recibo_print_numero_protocolo",
    ),
    path(
        "<uuid:pk>/recibo/print",
        PedidoReciboDetailView.as_view(),
        name="pedido_recibo_print",
    ),
    path(
        "<uuid:pk>/recibo_protocolo/print",
        PedidoReciboDetailProtocoloView.as_view(),
        name="pedido_recibo_protocolo_print",
    ),
    path(
        "<uuid:pk>/partes/",
        PedidoPartesListView.as_view(),
        name="pedido_partes_list",
    ),
    path(
        "<int:numero_protocolo>/protocolo/partes/",
        PedidoPartesProtocoloListView.as_view(),
        name="pedido_partes_list_protocolo",
    ),
    path(
        "<uuid:pk>/pedido_protocolo_cancelar/",
        pedido_protocolo_cancelar,
        name="pedido_protocolo_cancelar",
    ),
    path("relatorio/", PedidoRelatorioView.as_view(), name="pedido_relatorio"),
    path(
        "<uuid:pk>/protocolar/",
        pedido_protocolar_view,
        name="pedido_protocolar",
    ),
]

# ! URLs do Apresentante
urlpatterns += [
    path(
        "apresentante/locate/",
        ApresentanteLocateView.as_view(),
        name="apresentante_locate",
    ),
    path(
        "apresentante/lista/<str:nome>/",
        ApresentanteListView.as_view(),
        name="apresentante_list",
    ),
    path("seleciona/<uuid:pk>/", seleciona_apresentante, name="apresentante_seleciona"),
    path("desativar/<uuid:pk>/", desativar_apresentante, name="apresentante_desativar"),
    path(
        "apresentante/create/",
        ApresentanteCreateView.as_view(),
        name="apresentante_create",
    ),
    path(
        "apresentante/<uuid:pk>/update",
        ApresentanteUpdateView.as_view(),
        name="apresentante_update",
    ),
]

# !URLs do Imóvel
urlpatterns += [
    path("<uuid:pedido_id>/imoveis/", ImovelListView.as_view(), name="imoveis_list"),
    path(
        "<uuid:pedido_id>/imoveis/create/",
        ImovelCreateView.as_view(),
        name="imovel_create",
    ),
    path("imoveis/<uuid:pk>/update/", ImovelUpdateView.as_view(), name="imovel_update"),
    path("imoveis/<uuid:pk>/detail/", ImovelDetailView.as_view(), name="imovel_detail"),
    path("imoveis/<uuid:pk>/delete/", ImovelDeleteView.as_view(), name="imovel_delete"),
]

# !URLs do Parte
urlpatterns += [
    path("partes/<uuid:pk>/update/", ParteUpdateView.as_view(), name="parte_update"),
    path("partes/<uuid:pk>/detail/", ParteDetailView.as_view(), name="parte_detail"),
    path("partes/<uuid:pk>/delete/", ParteDeleteView.as_view(), name="parte_delete"),
]

# !URLs do Selo
urlpatterns += [
    # path("selos/create/", SeloCreateView.as_view(), name="selo_create"),
    # path("selos/<uuid:pk>/update/", SeloUpdateView.as_view(), name="selo_update"),
]

# !URLs do Evento
urlpatterns += [
    path("eventos/adicionar/", EventoAddView.as_view(), name="evento_adicionar"),
    path(
        "eventos/<uuid:evento_id>/update/",
        EventoUpdateView.as_view(),
        name="evento_alterar",
    ),
]

# URLs do Ato
urlpatterns += [
    path("<uuid:pedido_id>/ato/create/", ato_create, name="ato_create"),
    path("<uuid:pedido_id>/atos/", AtosListView.as_view(), name="atos_list"),
    path(
        "<int:numero_protocolo>/protocolo/atos/",
        listar_atos_por_numero_protocolo,
        name="atos_list_protocolo",
    ),
    path("ato/<uuid:pk>/partes/", AtoPartesListView.as_view(), name="ato_partes_list"),
    path("ato/<uuid:pk>/update/", ato_update_view, name="ato_update"),
    path("ato/<uuid:pk>/detail/", ato_detail_view, name="ato_detail"),
    path("ato/<uuid:pk>/delete/", AtoDeleteView.as_view(), name="ato_delete"),
    path(
        "<uuid:pk>/ato/duplicar/",
        duplicar_ato_protocolo,
        name="duplicar_ato_protocolo",
    ),
    path(
        "<uuid:pk>/ato/duplicar_ato_protocolo_quantidade/",
        duplicar_ato_protocolo_quantidade,
        name="duplicar_ato_protocolo_quantidade",
    ),
]

# URLs do AtoComplementar
urlpatterns += [
    path(
        "<uuid:pedido_id>/ato/<uuid:ato_id>/ato_complementar/create/",
        ato_complementar_create,
        name="ato_complementar_create",
    ),
    path(
        "ato_complementar/<uuid:pk>/detail/",
        AtoComplementarDetailView.as_view(),
        name="ato_complementar_detail",
    ),
]

# URLs do Participacao
urlpatterns += [
    path(
        "atos/<uuid:pk>/participacao/create/",
        ato_participacao_create_view,
        name="participacao_create",
    ),
    path(
        "participacoes/<int:pk>/update/",
        ato_participacao_update_view,
        name="participacao_update",
    ),
    path(
        "participacoes/<int:pk>/delete/",
        ParticipacaoDeleteView.as_view(),
        name="participacao_delete",
    ),
    path(
        "participacoes/<int:pk>/remover/",
        remove_participacao,
        name="remove_participacao",
    ),
    path(
        "atos/<uuid:pk>/participacoes/",
        ParticipacoesListView.as_view(),
        name="participacoes_list",
    ),
]


urlpatterns += [
    # URLs para Requerimentos
    path("requerimentos/", RequerimentoListView.as_view(), name="requerimentos_list"),
    path(
        "requerimentos/<int:pk>/",
        RequerimentoDetailView.as_view(),
        name="requerimento_detail",
    ),
    path(
        "requerimentos/create/",
        RequerimentoCreateView.as_view(),
        name="requerimento_create",
    ),
    path(
        "requerimentos/<int:pk>/update/",
        RequerimentoUpdateView.as_view(),
        name="requerimento_update",
    ),
    path(
        "requerimentos/<int:pk>/delete/",
        RequerimentoDeleteView.as_view(),
        name="requerimento_delete",
    ),
    path(
        "requerimentos/<int:pk>/print/",
        RequerimentoPrintView.as_view(),
        name="requerimento_print",
    ),
    path(
        "requerimentos/<int:pk>/<int:pedido_id>/print/",
        RequerimentoPedidoPrintView.as_view(),
        name="requerimento_pedido_print",
    ),
    # URLs para DocumentoParaRequerimento
    path(
        "requerimentos/<int:requerimento_id>/documentos/",
        DocumentoParaRequerimentoListView.as_view(),
        name="documentos_para_requerimento_list",
    ),
    path(
        "documentos/<int:pk>/",
        DocumentoParaRequerimentoDetailView.as_view(),
        name="documento_para_requerimento_detail",
    ),
    path(
        "documentos/create/",
        DocumentoParaRequerimentoCreateView.as_view(),
        name="documento_para_requerimento_create",
    ),
    path(
        "documentos/<int:pk>/update/",
        DocumentoParaRequerimentoUpdateView.as_view(),
        name="documento_para_requerimento_update",
    ),
    path(
        "documentos/<int:pk>/delete/",
        DocumentoParaRequerimentoDeleteView.as_view(),
        name="documento_para_requerimento_delete",
    ),
    path(
        "documentos/<int:pk>/print/",
        DocumentoParaRequerimentoPrintView.as_view(),
        name="documento_para_requerimento_print",
    ),
]
