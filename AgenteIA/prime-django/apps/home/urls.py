import logging

from django.urls import include, path
from haystack.views import SearchView
from rest_framework.routers import DefaultRouter

from apps.home import views

logger = logging.getLogger(__name__)

logger.debug(f"Iniciando {__name__}")

router = DefaultRouter()


app_name = "home"

urlpatterns = [
    # path("calender/", views.calendar_view_new, name="calender"),
]

# Livro 01 - Protocolos
urlpatterns += [
    path("relatorio/excel/", views.download_excel_relatorio, name="relatorio_excel"),
    path("protocolos/", views.protocolos_list, name="protocolos_list"),
    # path(
    #     "protocolos/<int:protocolo_id>/andamentos/listar/",
    #     views.ProtocoloAndamentoListView.as_view(),
    #     name="protocolo_andamento_listar",
    # ),
    path(
        "protocolos/protocolo/<int:pk>/confirmar_entrega/",
        views.protocolo_confirmar_entrega_view,
        name="protocolo_confirmar_entrega",
    ),
    # Livro01Andamento
    # path("protocolos/andamentos/", views.AndamentosListView.as_view(), name="andamentos_list"),
    path(
        "protocolo/<int:protocolo_id>/add-andamento/",
        views.AndamentoCreateView.as_view(),
        name="add_andamento",
    ),
    path(
        "protocolos/andamento/<int:pk>/",
        views.AndamentoDetailView.as_view(),
        name="andamento_detail",
    ),
    path(
        "protocolos/andamento/<int:pk>/update/",
        views.AndamentoUpdateView.as_view(),
        name="andamento_edit",
    ),
    path(
        "protocolos/andamento/<int:pk>/texto_print/",
        views.AndamentoTextoPrintView.as_view(),
        name="andamento_texto_print",
    ),
    path(
        "certidoes/andamento/<int:pk>/texto_print/",
        views.PedidoCertidaoAndamentoTextoPrintView.as_view(),
        name="pedido_certidao_andamento_texto_print",
    ),
    path(
        "certidoes/andamento/<int:pk>/gerar_certidao/",
        views.pedido_certidao_andamento_texto_gerar_certidao_pessoa,
        name="pedido_certidao_andamento_gerar_certidao_pessoa",
    ),
    path(
        "certidoes/andamento/<int:pk>/gerar_certidao_imovel/",
        views.pedido_certidao_andamento_texto_gerar_certidao_imovel,
        name="pedido_certidao_andamento_gerar_certidao_imovel",
    ),
    path(
        "protocolos/andamento/<int:pk>/texto/",
        views.AndamentoTextoDetailView.as_view(),
        name="andamento_texto_detail",
    ),
    path(
        "protocolos/andamentos/exigencias/",
        views.AndamentosExigenciasListView.as_view(),
        name="andamentos_exigencias_list",
    ),
    path(
        "protocolos/andamentos/registrados/",
        views.AndamentosRegistradosListView.as_view(),
        name="andamentos_registrados_list",
    ),
    path(
        "protocolos/andamentos/prenotados/",
        views.AndamentosPrenotadosListView.as_view(),
        name="andamentos_prenotados_list",
    ),
    path(
        "protocolo/<int:protocolo_id>/andamentos/",
        views.ProtocoloAndamentosListView.as_view(),
        name="protocolo_andamentos",
    ),
    path(
        "protocolo/<int:pk>/andamentos/v2/",
        views.AndamentosListView.as_view(),
        name="andamentos_list_v2",
    ),
    path(
        "protocolos/<str:ids>/timeline/",
        views.protocolo_timeline_view,
        name="protocolo_timeline",
    ),
    path(
        "impressao-registrados/",
        views.ImpressaoProtocolosRegistradosView.as_view(),
        name="impressao_registrados",
    ),
    path(
        "impressao-recibo-protocolo/",
        views.ImpressaoReciboProtocoloView.as_view(),
        name="impressao_recibo_protocolo",
    ),
    path(
        "impressao-prenotados/",
        views.ImpressaoProtocolosRegistradosView.as_view(),
        name="impressao_prenotados",
    ),
]


# LIVRO 02 - Registros (Matriculas, Transcrições, Inscrições)
urlpatterns += [
    path("livrodoi/", views.LivroDOI, name="livrodoi_list"),
    path("livro02/", views.Livro02ListView.as_view(), name="livro02_list"),
    path("livro02/<int:pk>/", views.Livro02DetailView.as_view(), name="livro02_detail"),
    path(
        "livro02/abrir_por_numero/",
        views.Livro02View.as_view(),
        name="abrir_livro02_pelo_numero",
    ),
    path(
        "livro02/<int:pk>/texto/",
        views.Livro02TextoUpdateView.as_view(),
        name="livro02_texto",
    ),
    path(
        "livro02/<int:pk>/imagens/",
        views.Livro02ImagensListView.as_view(),
        name="registro_imagens",
    ),
    path(
        "livro02/numero/<str:numero_registro>/tipo_registro/<str:tipo_registro>/imagens/",
        views.Livro02ImagensListView.as_view(),
        name="livro02_imagens_pelo_numero",
    ),
]

# LIVRO 03 - Registros Auxiliares (Ex. Cédulas de crédito, Hipotecas, Penhoras, etc.)
urlpatterns += [
    path("livro03/", views.Livro03ListView.as_view(), name="livro03_list"),
    path("livro03/<int:pk>/", views.Livro03Detail.as_view(), name="livro03_detail"),
    path(
        "livro03Numero/<int:numero>/<str:cartorio>",
        views.livro03_numero_detail,
        name="livro03_detail_pelo_numero",
    ),
    path(
        "livro03/<int:pk>/texto/",
        views.Livro03TextoDetailView.as_view(),
        name="livro03_texto",
    ),
    path("livro03/<int:pk>/minutas/", views.livro03_minutas_list, name="minuta_lv3"),
    path("livro03/abrir/", views.abrir_livro03, name="abrir_livro03"),
]

# LIVRO 04 - Cadastro Real (Imóveis)
urlpatterns += [
    path("livro04/", views.Livro04ListView.as_view(), name="livro04_list"),
    # INDICADOR REAL DETAIL PELO ID DO IMOVEL
    path("livro04/imovel/<int:pk>", views.livro04_imovel_view, name="livro04_imovel"),
    # INDICADOR REAL PELO NUMERO DO REGISTRO
    path(
        "livro04/<str:numero_registro>/<str:tipo_registro>/<str:cartorio_imovel>/",
        views.livro04_detail_view,
        name="livro04_detail",
    ),
]

# LIVRO 05 - Cadastro Pessoal (Pessoas)

# Partes
urlpatterns += [
    path("partes/", views.PedidoPartesListView.as_view(), name="partes_list"),
]

urlpatterns += [
    path(
        "protocolos/colaborador/<int:pk>/distribuicao/",
        views.ProtocolosDistribuidosPorColaboradorListView.as_view(),
        name="protocolos_distribuidos_por_colaborador",
    ),
]


# Outras URLs...
urlpatterns += [
    path("", views.calendario_redirect_view, name="index"),
    # path("agenda_inicial/", views.calendario_redirect_view, name="index"),
    path(
        "protocolo/<int:pk>/",
        views.livro01_protocolo_detail,
        name="protocolo_detail",
    ),
    path("", views.protocolo_search_view, name="protocolo_search"),
    # path("protocolo_inicial", views.protocolo_search_view, name="protocolo_search"),
    # path("", protocolo_search_view, name="protocolo_detail"),
    path("livro01_doi/", views.protocolos_doi_list_view, name="protocolo_list_doi"),
    # path("listar", protocolos, name= "listar"),
    # path('protocolo_inicial/', Protocolo_Inicial, name= "protocolo_inicial"),
    # path("protocolo_final/<opcao>/<numero>/", Protocolo_Final, name="protocolo_final"),
    path(
        "verificar_solicitar_servico_colaborador/<colaborador_id>/",
        views.verificar_solicitar_servico_colaborador,
        name="verificar_solicitar_servico_colaborador",
    ),
    # COLABORADOR CONFIRMA QUE RECEBEU O DOCUMENTO DISTRIBUIDO
    path(
        "colaborador/<int:colaborador_id>/protocolo/<int:protocolo_id>/receber/<str:opcao_recebimento>/",
        views.ConfirmarRecebimentoProtocoloView.as_view(),
        name="colaborador_receber_protocolo",
    ),
    path(
        "solicitar_servico_colaborador/<colaborador_id>/",
        views.solicitar_servico_colaborador,
        name="solicitar_servico_colaborador",
    ),
    path(
        "pedido_item/<pedido_item_id>/<pedidos_itens_origem_id>/delete",
        views.pedido_item_delete_view,
        name="Remover_Pedido_Item",
    ),
    # path(
    #     "vincular_pessoa_protocolos/",
    #     views.ItensProtocoloView.as_view(),
    #     name="vincular_pessoa_protocolo",
    # ),
    # Gerar um pdf do HTML
    # path('exibir_pdf_checklist/', views.GeneratePdf2.as_view(), name= "visualizar_html_pdf"),
    path("exibir_pdf_checklist/", views.generate_pdf, name="visualizar_html_pdf"),
    # Atualizar tabela vinda do checklist - LIVRO 2 e 3
    path(
        "atualizar_livro02_03/<pedido_item_id>/<perguntas_id>/<coluna_tabela_origem>/<resposta_correta>/",
        views.atualizar_livro02_03,
        name="atualizar_livro02_03",
    ),
    # Atualizar tabela vinda do checklist - LIVRO 2 e 3
    path(
        "atualizar_checklist_livro02_03/<pedido_item_id>/<perguntas_id>/<coluna_tabela_origem>/<resposta_correta>/",
        views.atualizar_checklist_livro02_03,
        name="atualizar_checklist_livro02_03",
    ),
    path(
        "atualizar_checklist_partes/<pedido_item_id>/<pessoa_id>/<coluna_tabela_origem>/<resposta_correta>/",
        views.atualizar_checklist_partes,
        name="atualizar_checklist_partes",
    ),
    # Encaminhar para proximo funcionario
    path(
        "encaminhar_protocolo_ao_colaborador/<int:numero_protocolo>/",
        views.encaminhar_protocolo_ao_colaborador_view,
        name="encaminhar_protocolo_ao_colaborador_view",
    ),
    # Reentrada encaminhar para proximo funcionario
    path(
        "protocolo/<numero_protocolo>/reentrada/<opcao_reentrada>/",
        views.reentrada_pagamento_protocolo_numero,
        name="reentrada_protocolo_ao_colaborador_view",
    ),
    # Reprotocoloar encaminhar para proximo funcionario
    path(
        "reprotocolar_protocolo/<numero_protocolo>/",
        views.reprotocolar_protocolo_view,
        name="reprotocolar_protocolo_view",
    ),
    path(
        "criar_lembrete_imovel/<imovel_id>/<numero_registro>/",
        views.criar_lembrete_imovel,
        name="criar_lembrete_imovel",
    ),
    # Gerar uma nota de devolucao    -  LEMBRAR DE TIRAR ISSO
    # path('exibir_nota_devolucao/<pedido_item_id>/', gerar_nota_de_devolucao, name= "gerar_nota_de_devolucao"),
    # path("exibir_nota_devolucao/<pedido_item_id>/", views.ExportDocx.as_view(), name="gerar_nota_de_devolucao"),
    # Gerar uma nota de devolucao
    # path('download_csv_file/', download_csv_data, name= "download_csv_file"),
    # path("download_excel_file/", download_excel_data, name="download_excel_file"),
    # path("download_doc_file/<pedido_item_id>/<opcao_nota>/", views.ExportDocx.as_view(), name="download_doc_file"),
    # path("download_doc_ento/<pedido_item_id>/<opcao_nota>/", views.ExportDocx.as_view(), name="download_doc_file_pagamento"),
    path(
        "visualizar_pdf/<opcao_pasta>/<numero>/<arquivo>/",
        views.visualizar_pdf,
        name="visualizar_pdf",
    ),
    path(
        "download_pdf_file/<pedido_item_id>/",
        views.DownloadPDFFileView.as_view(),
        name="download_pdf_file",
    ),
    path(
        "importar_titulos_protocolos/",
        views.ImportarTitulosProtocolosView.as_view(),
        name="importar_titulos_protocolos",
    ),
    ############################### PROPRIETARIOS ###############################
    path(
        "get_proprietarios_lv2/<pedido_item_id>/",
        views.get_proprietarios_lv2,
        name="get_proprietarios_lv2",
    ),
    ############################### FINANCEIRO ###############################
    path("financeiro/", views.FinanceiroListView.as_view(), name="financeiro_listar"),
    path(
        "financeiro/colaborador/",
        views.financeiro_colaborador_list,
        name="financeiro_listar_por_colaborador",
    ),
    # path("financeiro/criar/", views.FinanceiroCreateView.as_view(), name="financeiro_criar"),
    path(
        "financeiro/fecharcaixa/",
        views.financeiro_fechar_caixa,
        name="confirmar_fechamento_caixa",
    ),
    path(
        "financeiro/confirmar_abrir_caixa_dia/",
        views.financeiro_abrir_caixa,
        name="confirmar_abrir_caixa_dia",
    ),
    path(
        "financeiro/<int:pk>/",
        views.financeiro_transacao_detalhes,
        name="financeiro_detalhe",
    ),
    path(
        "financeiro/caixa_receita/importar_protocolo_caixa_diferenca_view/",
        views.importar_protocolo_caixa_diferenca_view,
        name="importar_protocolo_caixa_diferenca_view",
    ),
    path(
        "financeiro/caixa_receita/caixa_verificar_diferenca/",
        views.caixa_verificar_diferenca,
        name="caixa_verificar_diferenca",
    ),
    path(
        "financeiro/caixa_receita/<int:numero_protocolo>/caixa_verificar_diferenca_direto/",
        views.caixa_verificar_diferenca_direto,
        name="caixa_verificar_diferenca_direto",
    ),
    path(
        "financeiro/caixa_receita/<int:numero_protocolo>/<str:mensagem>/caixa_verificar_diferenca_direto_sistema_antigo/",
        views.caixa_verificar_diferenca_direto_sistema_antigo,
        name="caixa_verificar_diferenca_direto_sistema_antigo",
    ),
    path(
        "financeiro/<int:pk>/recibo/",
        views.financeiro_recibo_print,
        name="financeiro_recibo_print",
    ),
    path("financeiro_previo/", views.financeiro_previo, name="financeiro_previo"),
    path("financeiro/caixa_despesa/", views.caixa_despesa, name="caixa_despesa"),
    path("financeiro/caixa_receita/", views.caixa_receita, name="caixa_receita"),
    path("financeiro/caixa_saida/", views.caixa_saida, name="caixa_saida"),
    path(
        "financeiro/caixa_cancelar/<int:pk>/",
        views.caixa_cancelar,
        name="caixa_cancelar",
    ),
    path("financeiro/caixa_fechar/", views.caixa_fechar, name="caixa_fechar"),
    path(
        "financeiro/update/<int:pk>/",
        views.CaixaUpdate.as_view(),
        name="caixa_editar",
    ),
    path(
        "checklist_balcao/<numero_protocolo>/<classe_imovel>/<ato_id>/",
        views.checklist_balcao_view,
        name="checklist_balcao",
    ),
    ############################### IMPORTAR PROTOCOLO ###############################
    path(
        "importar_protocolo/",
        views.importar_protocolo_view,
        name="importar_protocolo",
    ),
    path(
        "protocolo/<numero_protocolo>/importar",
        views.ImportarProtocoloDiretoView.as_view(),
        name="importar_protocolo",
    ),
    path(
        "importar_registro_auxiliar/<numero_registro>/<tipo_registro>/<cartorio_imovel>/",
        views.importar_registro_auxiliar,
        name="importar_registro_auxiliar",
    ),
    # IMPORTAR IMOVEIS PELO NUMERO DO PK
    path(
        "importar_imovel_pelo_id/<imovel_id>/",
        views.importar_imovel_pelo_id_view,
        name="importar_imovel_pelo_id_view",
    ),
    path(
        "importar_imovel/<pedido_item_id>/",
        views.importar_imovel_view,
        name="importar_imovel",
    ),
    path(
        "importar_protocolo_por_colaborador/<colaborador_id>/",
        views.importar_protocolo_por_colaborador,
        name="importar_protocolo_por_colaborador",
    ),
    path(
        "verificar_protocolos_nao_importado/<str:tipo_importacao>",
        views.verificar_protocolos_nao_importado,
        name="verificar_protocolos_nao_importado",
    ),
    path(
        "importar_protocolo_data/",
        views.importar_protocolo_data_view,
        name="importar_protocolo_data_view",
    ),
    path(
        "importar_protocolos_modificados/",
        views.importar_protocolos_modificados_view,
        name="importar_protocolos_modificados_view",
    ),
    path(
        "importar_protocolos_modificados_2_dias/",
        views.importar_protocolos_modificados_2_dias_view,
        name="importar_protocolos_modificados_2_dias_view",
    ),
    path(
        "importar_andamentos_protocolo/",
        views.importar_andamentos_protocolo_view,
        name="importar_andamentos_protocolo",
    ),
    # path(
    #     "importacao/importar_protocolos_fb_modificados_na_ultima_hora/",
    #     importar_protocolos_fb_modificados_na_ultima_hora_view(),
    #     name="importar_protocolos_fb_modificados_na_ultima_hora",
    # ),
    path(
        "importar_protocolo_do_dia/",
        views.importar_protocolos_do_dia_view,
        name="importar_protocolo_do_dia",
    ),
    path(
        "importar_imovel_numero/",
        views.importar_imovel_numero_view,
        name="importar_imovel_numero_view",
    ),
    # Criar no protocolo - ITEM
    path(
        "criar_item_protocolo/",
        views.criar_item_protocolo,
        name="criar_item_protocolo",
    ),
    path(
        "criar_item_protocolo_principal/",
        views.criar_item_protocolo_principal,
        name="criar_item_protocolo_principal",
    ),
    path("abrir_livro05/", views.abrir_livro05, name="abrir_livro05"),
    path("pessoas/<int:pk>/", views.PessoaUpdateView.as_view(), name="editar_pessoa"),
    path("pessoas/<int:pk>/", views.PessoaUpdateView.as_view(), name="update_pessoa"),
    path(
        "livro05/update/<int:pk>/",
        views.PessoaUpdateView.as_view(),
        name="livro05-update",
    ),
    path("abrir_livro01/", views.abrir_livro01, name="abrir_livro01"),
    path(
        "protocolo/abrir_livro01_por_numero_protocolo/<int:numero_protocolo>/",
        views.abrir_livro01_por_numero_protocolo,
        name="abrir_livro01_por_numero_protocolo",
    ),
    path(
        "protocolo/abrir_por_numero/",
        views.abrir_livro01_por_numero,
        name="abrir_livro01_por_numero",
    ),
    path("abrir_lv04/", views.abrir_lv04, name="abrir_lv04"),
    path("exibir_imagem/", views.exibir_imagem, name="exibir_imagem"),
    # Criar no protocolo - ITEM COMPLEMENTAR
    path(
        "criar_item_protocolo_complementar/",
        views.criar_item_protocolo_complementar,
        name="criar_item_protocolo_complementar",
    ),
    # Visualizar protocolo - ITEM COMPLEMENTAR
    path(
        "visualizar_protocolo_complementar/<pedido_item_id>/",
        views.visualizar_protocolo_complementar,
        name="visualizar_protocolo_complementar",
    ),
    # Criar no protocolo - ITEM COMPLEMENTAR
    path(
        "novo_item_protocolo_complementar/<pedido_item_id>/",
        views.novo_item_protocolo_complementar,
        name="novo_item_protocolo_complementar",
    ),
    ############################### Checklist ###############################
    path("checklist_ato/<pedido_item_id>/", views.checklist_ato, name="checklist"),
    path(
        "checklist_ato_resultado/pedido_item/<int:pedido_item_id>/",
        views.checklist_ato_resultado,
        name="checklist_resultado",
    ),
    path(
        "checklist_ato/pedido_item/<int:pedido_item_id>/<int:protocolo_id>/",
        views.checklist_ato,
        name="checklist_protocolo",
    ),
    ############################### MINUTAS ###############################
    path(
        "minuta_lv2/pedido_item/<int:pedido_item_id>/",
        views.minuta_list_lv2,
        name="minuta_lv2",
    ),
    path(
        "aplicar_minuta_lv2/pedido_item/<int:pedido_item_id>/",
        views.aplicar_list_lv2,
        name="aplicar_minuta_lv2",
    ),
    path(
        "exibir_perguntas_minuta_lv2/pedido_item/<int:pedido_item_id>/minuta/<minuta_atual>/ ",
        views.exibir_perguntas_minuta_lv2,
        name="exibir_perguntas_minuta_lv2",
    ),
    # path("exibir_minuta_lv2/pedido_item/<int:pedido_item_id>/", views.ExportDocx_lv2.as_view(), name="gerar_minuta_lv2"),
    path(
        "minuta_lv2_texto/pedido_item/<int:pedido_item_id>/",
        views.minuta_list_lv2_texto,
        name="minuta_lv2_texto",
    ),
    path(
        "checklist_lv2/pedido_item/<int:pedido_item_id>/opcao/<opcao>/",
        views.minuta_list_lv2,
        name="checklist_lv2",
    ),
    # INDICADOR REAL DETAIL PELO ID DO IMOVEL - LIVRO 3
    path(
        "livro04_detail_idimovel_Livro03/<int:pk>",
        views.Livro04DetailViewLivro03.as_view(),
        name="livro04_detail_idimovel_Livro03",
    ),
    # INDICADOR REAL DETAIL PELO ID DO IMOVEL - UNIDADES LOTEAMENTO
    path(
        "livro04_detail_unidade_loteamento/<int:pk>",
        views.livro04_detail_unidade_loteamento,
        name="livro04_detail_unidade_loteamento",
    ),
    # INDICADOR REAL DETAIL PELO ID DO IMOVEL - UNIDADES CONDOMINIO
    path(
        "livro04_detail_unidade_condominio/<int:pk>",
        views.livro04_detail_unidade_condominio,
        name="livro04_detail_unidade_condominio",
    ),
    # INDICADOR REGISTRO AUXILIAR DETAIL - ID
    path("livro05/<int:pk>/", views.Livro05DetailView.as_view(), name="livro05_detail"),
    path("livro05/", views.Livro05ListView.as_view(), name="livro05_list"),
    path(
        "livro05/pessoal_detalhes/",
        views.livro05_pessoal_view,
        name="livro05_pessoal_view",
    ),
    path("pessoal/<str:cpf_cnpj>/<str:nome>/", views.pessoal, name="pessoal"),
    path("livro05_por_id/<str:id>/", views.livro05_por_id_view, name="livro05_por_id"),
    path(
        "pessoal_por_id/<int:vinculo_id>",
        views.pessoal_por_id,
        name="pessoal_por_id",
    ),
    ############################### INDICADOR PESSOAL ###############################
    path("pessoal_lv2/<pedido_item_id>/", views.pessoal_list_lv2, name="pessoal_lv2"),
    path(
        "livro02/imovel/<numero_registro>/tipo/<tipo_registro>/cartorio/<cartorio_imovel>/pessoas/",
        views.livro02_pessoas_list,
        name="livro02_pessoas_list",
    ),
    ############################### VISUALIZAR IMAGEM ###############################
    path(
        "exibir_minuta_imagem/<id>/<tipo>/",
        views.documento_arquivo_view,
        name="gerar_minuta_imagem",
    ),
    ############################### VISUALIZAR IMAGEM ###############################
    path(
        "texto_nota_devolucao/<int:pk>/<str:pedido_item_id>/",
        views.TextoCreateView.as_view(),
        name="texto_nota_devolucao",
    ),
    path(
        "texto_devolucao/<int:pk>/<str:pedido_item_id>/",
        views.NotaDevolucaoDetailView.as_view(),
        name="texto_devolucao",
    ),
    path(
        "texto_exigencia_minuta/<str:pk>/",
        views.MinutaExigenciaTextoDetailView.as_view(),
        name="texto_exigencia_minuta",
    ),
    path(
        "texto_ato_minuta/<uuid:pk>/",
        views.MinutaModeloAtoTextoView.as_view(),
        name="texto_ato_minuta",
    ),
    # path("texto_lv2/", views.TextoListView.as_view(), name="texto_lv2"),
    path(
        "texto_lv2/<int:pk>/<str:pedido_item_id>/",
        views.TextoLv2View.as_view(),
        name="texto_lv2",
    ),
    path("texto_lv2_create/", views.TextoCreateView.as_view(), name="texto_lv2_create"),
    path(
        "texto_lv2_update/<int:pk>/",
        views.TtextoUpdateView.as_view(),
        name="texto_lv2_update",
    ),
    # path('books/', views.BookListView.as_view(), name='books'),
    # path('books/<pk>/', views.BookDetailView.as_view(), name='detail'),
    # path('book/<id>', detail_view),
    # path("books/", views.CheckListRealizadoListView.as_view(), name="books"),
    # path("book/<int:pk>", views.BookDetailView.as_view(), name="book-detail"),
    # path("book2/<id>", detail_view, name="book-detail2"),
    path(
        "checklist_realizado_list/<id>/",
        views.checklist_realizado_list,
        name="checklist_realizado_list",
    ),
    # Filtrar e exibir pedidos_itens_imovel
    path(
        "checklist_imovel/<id>/",
        views.ChecklistImovelView.as_view(),
        name="checklist_imovel",
    ),
    ############################### UPDATE ###############################
    path("pessoas-criar/", views.PessoaCreate.as_view(), name="criar_pessoa"),
    ############################### UPDATE ###############################
    path(
        "pessoas-atualizar/<int:pk>/",
        views.PessoaUpdate.as_view(),
        name="pessoa_editar",
    ),
    # path('pessoas-atualizar-modal/<int:pk>/', Atualizar_PessoaUpdate, name='atualizar_pessoa_editar'),
    path(
        "pessoas-atualizar-modal/",
        views.atualizar_pessoa_update,
        name="atualizar_pessoa_editar",
    ),
    path("funcionarios/", views.funcionario_list_view, name="lista_funcionarios"),
    # MODELO PARA CADASTRAR MODAL
    # path('funcionario/cadastrar/',       views.FuncionarioCreateView.as_view(), name='cadastra_funcionario'),
    path(
        "pessoa/cadastrar/<str:pedido_id>/<str:opcao_parte>/",
        views.PessoaCreateView.as_view(),
        name="cadastra_pessoa",
    ),
    # CADATRAR NOVA PESSOA
    path(
        "pessoa/novapessoa/<str:pedido_item_id>/<str:opcao_parte>/",
        views.NovaPessoaCreateView.as_view(),
        name="nova_pessoa",
    ),
    # CADASTRAR - Checklist para endereço urbano
    path(
        "cadastrarurbano/<str:pedido_item_id>/<str:opcao_imovel>/",
        views.UrbanoEnderecoCheckListCreateView.as_view(),
        name="cadastra_ChecklistEndereco_Urbano",
    ),
    path(
        "cadastrarrural/<str:pedido_item_id>/<str:opcao_imovel>/",
        views.RuralEnderecoCheckListCreateView.as_view(),
        name="cadastra_ChecklistEndereco_Rural",
    ),
    path(
        "cadastrarpessoa/<str:pedido_item_id>/<str:opcao_pessoa>/",
        views.ParteCheckListCreateView.as_view(),
        name="vincular_ChecklistPessoa",
    ),
    # path('funcionario/update/<int:pk>/', views.FuncionarioUpdateView.as_view(), name='update_funcionario'),
    path(
        "funcionario/update/<int:pk>/",
        views.FuncionarioUpdate.as_view(),
        name="update_funcionario",
    ),
    # path('pessoas-atualizar2/<int:pk>/', views.PessoaUpdate2.as_view(), name='pessoa_editar2'),
    # path('pessoas-atualizar/<int:pk>/', Livro05View, name='pessoa_editar'),
    # path('book2/<id>',      detail_view, name='book-detail2'),
    path("calender/", views.calendar_view_new, name="calender"),
    path(
        "event/colaborador/",
        views.event_colaborador_list_view,
        name="event_listar_por_colaborador",
    ),
    path(
        "calender/event/<str:event_name>/details/",
        views.event_details_name,
        name="event-detail_name",
    ),
    path("event/<int:event_id>/details/", views.event_details, name="event-detail"),
    path("pessoas-excluir/<int:pk>/", views.pessoa_delete, name="excluir_pessoa"),
    path("estado_civil/", views.estado_civil_view, name="cadastrar_estado_civil"),
    path("event/new/", views.create_event, name="event_new"),
    path("event/edit/<int:pk>/", views.EventEdit.as_view(), name="event_edit"),
    path(
        "event/<int:pk>/removecomplete",
        views.EventDeleteCompleteView.as_view(),
        name="event_remove_complete",
    ),
    path(
        "event/<int:event_id>/event_lido/",
        views.event_lido,
        name="event_lido",
    ),
    path(
        "event/<int:event_id>/event_finalizado/",
        views.event_finalizado,
        name="event_finalizado",
    ),
    # path("event/<int:event_id>/details/", event_details, name= "event-detail"),
    path(
        "calender/event/<str:event_name>/details/",
        views.event_details_name,
        name="event-detail_name",
    ),
    path(
        "add_eventmember/<int:event_id>",
        views.add_eventmember,
        name="add_eventmember",
    ),
    path(
        "event/<int:pk>/remove",
        views.EventMemberDeleteView.as_view(),
        name="remove_event",
    ),
    path("all-event-list/", views.AllEventsListView.as_view(), name="all_events"),
    path(
        "running-event-list/",
        views.RunningEventsListView.as_view(),
        name="running_events",
    ),
    path(
        "event/selecionar_membro_evento/<int:event_id>/<int:member_id>",
        views.event_member_select,
        name="selecionar_membro_event",
    ),
    path(
        "event/iniciar_membro_evento/<int:event_id>/<int:member_id>",
        views.event_member_start,
        name="start_membro_event",
    ),
    path(
        "editModalNotaDevolucao/",
        views.edit_modal_nota_devolucao,
        name="editModalNotaDevolucao",
    ),
    path("dashboard/", views.painel_eventos_view, name="painel_eventos"),
    path("pendencias/", views.PendenciasView.as_view(), name="pendencias"),
    path(
        "base_conhecimento_protocolo/<pedido_item_id>/<ato_id>/<numero_protocolo_pesquisar>/<numero_registro>/<tipo_registro>/<cartorio_imovel>/<classe>/",
        views.base_conhecimento_protocolo_view,
        name="base_conhecimento_protocolo",
    ),
    path(
        "minutas_view/<pedido_item_id>/<ato_id>/",
        views.minutas_view,
        name="minutas_view",
    ),
    path(
        "dashboard/<colaborador_id>/",
        views.painel_eventos_view,
        name="painel_eventos_id_colaborador",
    ),
    path(
        "protocolos/distribuicao_data/",
        views.distribuicao_protocolo_data,
        name="distribuicao_protocolo_data",
    ),
    # path("dashboard/", views.DashboardCartorioView.as_view(), name="dashboard"),
    # path("dashboard_data/", views.dashboard_data, name="dashboard_data"),
    path(
        "dashboard_data/",
        views.dashboard_cartorio2_view,
        name="dashboard_data",
    ),
    path(
        "dashboard/relatorio/<data_inicio>/<data_fim>/",
        views.RelatorioDashboardTemplateView.as_view(),
        name="dashboard_relatorio",
    ),
    path(
        "protocolos/distribuicao_colaboradores",
        views.DistribuicaoProtocoloColaboradoresListView.as_view(),
        name="distribuicao_protocolo_colaboradores",
    ),
    path(
        "protocolos/distribuicao",
        views.protocolo_distribuicao_list_view,
        name="distribuicao_protocolo",
    ),
    path(
        "protocolos/distribuicao/colaborador/<int:colaborador_id>/",
        views.protocolos_distribuidos_por_colaborador_list_view,
        name="distribuidos_por_colaborador",
    ),
    path(
        "protocolos/distribuicao/relatorio/<data_inicio>/<data_fim>/<colaborador_id>/",
        views.RelatorioProtocolosDistribuidosTemplateView.as_view(),
        name="distribuicao_protocolo_relatorio",
    ),
    path(
        "protocolos/distribuicao/relatorio_unico/<data_inicio>/<data_fim>/<colaborador_id>/",
        views.RelatorioProtocolosDistribuidosUnicoTemplateView.as_view(),
        name="distribuicao_protocolo_relatorio_unico",
    ),
    path(
        "protocolos/distribuicao/relatorio_todos/<data_inicio>/<data_fim>/<colaborador_id>/<opcao_id>/",
        views.RelatorioProtocolosDistribuidosTodosTemplateView.as_view(),
        name="distribuicao_protocolo_relatorio_todos",
    ),
    path(
        "protocolos/distribuicao/relatorio_distribuidos_colaborador/<data_inicio>/<data_fim>/<colaborador_id>/",
        views.RelatorioProtocolosDistribuidosColaboradorTemplateView.as_view(),
        name="distribuicao_protocolo_relatorio_distribuidos_colaborador",
    ),
    path(
        "<numero_protocolo>/distribuir/",
        views.distribuicao_protocolo_numero,
        name="distribuicao_protocolo_numero",
    ),
    path(
        "<numero_protocolo>/reprotocolar/",
        views.reprotocolar_protocolo_numero,
        name="reprotocolar_protocolo_numero",
    ),
    path(
        "<numero_protocolo>/reentrada/",
        views.reentrada_protocolo_numero,
        name="reentrada_protocolo_numero",
    ),
    path(
        "<numero_protocolo>/reentrada_pagamento/",
        views.reentrada_pagamento_protocolo_numero,
        name="reentrada_pagamento_protocolo_numero",
    ),
    # ALTERAR DADOS DO ADQUIRENTE
    path("editModalTextoL2/", views.edit_modal_texto_l2, name="editModalTextoL2"),
    path("editModalPessoa/", views.edit_modal_pessoa, name="editModalPessoa"),
    # ALTERAR DADOS DA PESSOA
    path(
        "modal_detalhes_pessoa/",
        views.modal_detalhes_pessoa,
        name="modal_detalhes_pessoa",
    ),
    path("deleteModalPessoa/", views.delete_modal_pessoa, name="deleteModalPessoa"),
    path(
        "desvincularModalPessoa/<str:opcao_parte>/",
        views.desvincular_modal_pessoa,
        name="desvincularModalPessoa",
    ),
    path(
        "desvincularProtocoloPessoa/<str:pessoa_id>/<str:papel>/<str:protocolo_id>/",
        views.desvincular_protocolo_pessoa,
        name="desvincularProtocoloPessoa",
    ),
    path(
        "desvincularModalPessoaMinuta/",
        views.desvincular_modal_pessoa_minuta,
        name="desvincularModalPessoaMinuta",
    ),
    path(
        "desvincularModalEnderecoMinuta/",
        views.desvincular_modal_endereco_minuta,
        name="desvincularModalEnderecoMinuta",
    ),
    # ALTERAR DADOS DO ADQUIRENTE
    path(
        "editModalAtoParteA/",
        views.edit_modal_ato_parte_a,
        name="editModalAtoParteA",
    ),
    path(
        "editModalAtoParteT/",
        views.edit_modal_ato_parte_t,
        name="editModalAtoParteT",
    ),
    path(
        "editModalAtoParteTPartesProtocolo/",
        views.edit_modal_ato_parte_t_partes_protocolo,
        name="editModalAtoParteTPartesProtocolo",
    ),
    path(
        "editModalAtoParteEndereco/",
        views.edit_modal_ato_parte_endereco,
        name="editModalAtoParteEndereco",
    ),
    # AGENDA DO PROTOCOLO
    path(
        "agenda_protocolo/<protocolos>/",
        views.agenda_protocolo_view,
        name="agenda_protocolo",
    ),
    # AGENDA DO PROTOCOLO - POR DATA
    path(
        "agenda_protocolo_relatorio/<data_i>/<data_f>/",
        views.agenda_protocolo_relatorio,
        name="agenda_protocolo_relatorio",
    ),
    # AGENDA DO PROTOCOLO - POR COLABORADOR
    path(
        "agenda_protocolo_colaborador/<colaborador_id>/",
        views.agenda_protocolo_colaborador,
        name="agenda_protocolo_colaborador",
    ),
    # TAREFAS DO COLABORADOR
    path("tarefas_agenda/", views.tarefas_agenda, name="tarefas_agenda"),
    # IMPPORTAR EMOLUMENTOS ITENS
    path(
        "importar_emolumentos_itens/",
        views.importar_emolumentos_itens,
        name="importar_emolumentos_itens",
    ),
    # SALVAR LEMBRETE IMOVEL
    path(
        "salvar_lembrete_imovel",
        views.salvar_lembrete_imovel,
        name="salvar_lembrete_imovel",
    ),
    path(
        "<int:protocolo_id>/anexar_documento/",
        views.anexar_documento_view,
        name="anexar_documento",
    ),
    path(
        "anexar_nota_devolucao/<int:pedido_item_id>/",
        views.anexar_nota_devolucao_view,
        name="anexar_nota_devolucao",
    ),
    # UPDLOAD
    path("integracoes/", views.integracoes_view, name="integracoes"),
    path(
        "protocolos/onr/importar/",
        views.integracoes_view_importar,
        name="integracoes_importar",
    ),
    # IMPORTAR MATRICULA VISUALIZADA, CERTIDAO EMITIR, MATRICULA VISUALIZADA, OFICIO - ONR
    path(
        "certidoes/onr/<int:origem_id>/",
        views.integracoes_onr_view,
        name="integracoes_onr",
    ),
    path(
        "certidoes/onr/matricula_visualizada/",
        views.onr_matricula_visualizada_view,
        name="onr_matricula_visualizada",
    ),
    path(
        "certidoes/onr/certidoes_a_emitir/",
        views.onr_certidoes_a_emitir_view,
        name="onr_certidoes_a_emitir",
    ),
    # IMPORTAR e-PROTOCOLO, INTIMACAO - ONR
    path(
        "certidoes/onr/eprotocolo/",
        views.onr_eprotocolo_view,
        name="onr_eprotocolo",
    ),
    path(
        "protocolos/onr/<int:origem_id>/",
        views.IntegracoesImportarONRProtocoloView.as_view(),
        name="integracoes_onr_protocolo",
    ),
    path(
        "checklist_balcao/<numero_protocolo>/<classe_imovel>/<ato_id>/",
        views.checklist_balcao_view,
        name="checklist_balcao",
    ),
    path(
        "home/download_excel_protocolo_onr/<str:origem>/<str:data_inicio>/<str:data_fim>/",
        views.download_excel_protocolo_onr,
        name="download_excel_protocolo_onr",
    ),
    path(
        "financeiro/relatório/impressao/",
        views.ImpressaoRecibosView.as_view(),
        name="impressao_recibos",
    ),
    path(
        "caixa/relatorios/impressao-recibos/",
        views.ImpressaoRecibosCaixaView.as_view(),
        name="impressao_recibos-caixa",
    ),
    path(
        "caixa/relatorios/impressao-recibos-colaborador/",
        views.ImpressaoRecibosCaixaColaboradorView.as_view(),
        name="impressao_recibos-caixa-colaborador",
    ),
]

# Anexos
urlpatterns += [
    path(
        "<int:protocolo_pk>/anexos/adicionar/",
        views.anexo_create,
        name="anexo_create",
    ),
    path(
        "<int:protocolo_pk>/anexos/<int:anexo_pk>/update",
        views.anexo_update,
        name="anexo_update",
    ),
    path(
        "<int:protocolo_pk>/anexos/",
        views.Livro01ProtocoloAnexosListView.as_view(),
        name="anexos_list",
    ),
    path(
        "protected-media/<path:file_path>/",
        views.protected_media,
        name="protected_media",
    ),
    path("<int:protocolo_pk>/upload/", views.file_upload_view, name="file_upload"),
    path(
        "file_upload_por_numero/<int:numero_protocolo>/",
        views.file_upload_view_por_numero_protocolo,
        name="file_upload_por_numero",
    ),
]

# Andamento
urlpatterns += [
    path(
        "protocolos/andamentos/",
        views.AndamentosListView.as_view(),
        name="andamentos_list",
    ),
    path("importacoes/", views.importar_protocolos, name="importacoes"),
    path("analise-texto/", views.AnaliseTextoView.as_view(), name="analise_texto"),
]

# Andamento / Assinatura de Exigências
urlpatterns += [
    path(
        "andamento/<int:andamento_id>/escolher_certificado",
        views.escolher_certificado,
        name="escolher_certificado",
    ),
    path(
        "andamento/<int:andamento_id>/certificado/<uuid:certificado_id>/assinar_andamento",
        views.gerar_e_assinar_exigencia,
        name="assinar_andamento",
    ),
]

# backup
urlpatterns += [
    path("backup/", views.backup_database, name="backup_database"),
    path(
        "download_backup/<path:filename>/",
        views.download_backup_view,
        name="download_backup",
    ),
]

# certificados
urlpatterns += [
    # escolher_certificado
    path(
        "escolher_certificado/",
        views.escolher_certificado,
        name="escolher_certificado",
    ),
    path(
        "certificado_create/",
        views.CertificadoDigitalCreate.as_view(),
        name="certificado_create",
    ),
]

urlpatterns += [
    path(
        "modelos/<uuid:modelo_id>/conteudo/protocolo/<int:protocolo_id>/",
        views.get_modelo_texto_conteudo,
        name="get_modelo",
    ),
    path(
        "modelo_de_texto_pedido_certidao/<uuid:modelo_id>/pedido_certidao/<int:pedido_certidao_andamento_id>/",
        views.modelo_texto_pedido_certidao_view,
        name="modelo_de_texto_pedido_certidao",
    ),
]

urlpatterns += [
    path("chat/<str:room_name>/", views.chat_room, name="chat_room"),
]

urlpatterns += [
    path("tts/", views.tts_view, name="tts"),
    # suas outras URLs
]


urlpatterns += [
    path("abrir/", views.abrir_caixa, name="abrir_caixa"),
    path("fechar/", views.fechar_caixa, name="fechar_caixa"),
    path("transacao/", views.registrar_transacao, name="registrar_transacao"),
]

# SeloEletronico Digitais
urlpatterns += [
    path("selos/", views.SelosListView.as_view(), name="selos_listar"),
    # path("selos/exportar_xml_tjmg", views.exportar_xml_selo_digital_mg(), name="exportar_xml_tjmg"),
]


# Certidões:
urlpatterns += [
    # ! URLs para Certidões
    path(
        "certidoes/<int:imovel_id>/adicionar_certidao_imovel",
        views.certidao_create_imovel_view,
        name="pedido_certidao_adicionar_certidao_imovel",
    ),
    path(
        "certidoes/<int:pessoa_id>/adicionar_certidao_pessoa",
        views.certidao_create_pessoa_view,
        name="pedido_certidao_adicionar_certidao_pessoa",
    ),
    path(
        "certidoes/<int:pk>/editar",
        views.CertidaoUpdateView.as_view(),
        name="pedido_certidao_editar_certidao",
    ),
    path(
        "projeto/<int:pk>/editar",
        views.ProjetoUpdateView.as_view(),
        name="projeto_editar",
    ),
    # path("api/geocode/<str:latitude>/<str:longitude>", views.latitude_longitude_view, name="latitude_longitude"),
    path("", views.IndexView.as_view(), name="index"),
    path(
        "quantas-placas/<int:pk>/",
        views.QuantasPlacasView.as_view(),
        name="quantas_placas",
    ),
    path(
        "ranking-empresas/<int:pk>/",
        views.RankingEmpresasView.as_view(),
        name="ranking_empresas",
    ),
    path(
        "perguntas/<int:pk>/",
        views.PerguntasListView.as_view(),
        name="perguntas_list",
    ),
    path(
        "perguntas/nova/<int:pk>/",
        views.PerguntaCustomCreateView.as_view(),
        name="pergunta_new",
    ),
    path(
        "perguntas/<int:pk>/<int:projeto_id>/",
        views.PerguntaCustomDetailView.as_view(),
        name="pergunta_detail",
    ),
    path(
        "perguntas/livre/<int:projeto_id>/",
        views.PerguntaCustomLivreDetailView.as_view(),
        name="pergunta_detail_livre",
    ),
    path(
        "perguntas/registrar/email/",
        views.registrar_pergunta_feita,
        name="registrar_pergunta_feita",
    ),
    path(
        "perguntas/<int:pk>/<int:projeto_id>/update/",
        views.PerguntaCustomUpdateView.as_view(),
        name="pergunta_update",
    ),
    path(
        "perguntas/<int:pk>/<int:projeto_id>/delete/",
        views.PerguntaCustomDeleteView.as_view(),
        name="pergunta_delete",
    ),
    path(
        "projeto/<int:pk>/visualizar",
        views.ProjetoVisualizarView.as_view(),
        name="projeto_visualizar",
    ),
    path(
        "projeto/<int:pk>/gerar_simular",
        views.simular_view,
        name="gerar_simulacao",
    ),
    path(
        "projeto/<int:pk>/gerar_analise_Financeira",
        views.gerar_analise_financeira_view,
        name="gerar_analise_Financeira",
    ),
    path(
        "painel/<int:pk>/editar",
        views.PainelUpdateView.as_view(),
        name="painel_editar",
    ),
    path(
        "painel/exibir/grafico/<int:pk>/editar",
        views.gerar_grafico_painel_view,
        name="painel_exibir_grafico",
    ),
    #path("simular/", views.simular_view, name="simular"),
    path(
        "painel/importar/excell",
        views.painel_importar_excell_view,
        name="painel_importar_excell",
    ),
    path(
        "inversor/<int:pk>/editar",
        views.InversorUpdateView.as_view(),
        name="inversor_editar",
    ),
    path(
        "hidrogenio_editar/<int:pk>/editar",
        views.HidrogenioUpdateView.as_view(),
        name="hidrogenio_editar",
    ),
    path(
        "projeto/<int:pk>/excluir",
        views.ProjetoDeleteView.as_view(),
        name="projeto_excluir",
    ),
    path(
        "painel/<int:pk>/excluir",
        views.PainelDeleteView.as_view(),
        name="painel_excluir",
    ),
    path(
        "inversor/<int:pk>/excluir",
        views.InversorDeleteView.as_view(),
        name="inversor_excluir",
    ),
    path(
        "hidrogenio/<int:pk>/excluir",
        views.HidrogenioDeleteView.as_view(),
        name="hidrogenio_excluir",
    ),
    path(
        "certidoes/<int:pk>/excluir",
        views.CertidaoDeleteView.as_view(),
        name="pedido_certidao_excluir_certidao",
    ),
    path(
        "certidoes/<int:pk>/imprimir",
        views.CertidaoPrintView.as_view(),
        name="pedido_certidao_imprimir_certidao",
    ),
    # Receber Pedido de Certidao e Enviar Para Caixa
    path(
        "certidoes/<int:pk>/caixa/",
        views.pedido_certidao_caixa,
        name="pedido_certidao_caixa_view",
    ),
    # Receber Pedido de Protocolo e Enviar Para Caixa
    path(
        "protocolo/<int:numero_protocolo>/valor_total/<str:valor_total_protocolo>/caixa/",
        views.enviar_pedido_de_protocolo_ao_caixa_view,
        name="enviar_pedido_de_protocolo_ao_caixa",
    ),
    path(
        "protocolo/<int:numero_protocolo>/caixa_sistema_antigo/",
        views.pedido_protocolo_caixa_sistema_antigo,
        name="pedido_protocolo_caixa_view_sistema_antigo",
    ),
    path(
        "protocolo/<int:numero_protocolo>/protocolo_sistema_antigo/",
        views.recolhido_sistema_antigo_protocolo,
        name="recolhido_sistema_antigo_protocolo",
    ),
    # VERIFICAR WEBSERVICE
    path(
        "webservice/onr/",
        views.verificar_webservice_onr,
        name="verificar_webservice_onr",
    ),
    path(
        "webservice/onr/api/",
        views.verificar_webservice_onr_api,
        name="verificar_webservice_onr_api",
    ),
    path(
        "webservice/robo/onr/",
        views.verificar_webservice_onr_robo,
        name="verificar_webservice_onr_robo",
    ),
    # ! URLs para CEHTES
    path(
        "cehtes/criar_projeto",
        views.criar_projeto,
        name="criar_projeto",
    ),
    # ! URLs para CEHTES
    path(
        "projeto/<int:projeto_id>/grafico-interativo/",
        views.grafico_interativo_geracao,
        name="grafico_interativo_geracao",
    ),
    path(
        "painel/grafico-comparar-marcas/",
        views.grafico_comparar_marcas,
        name="grafico_comparar_marcas",
    ),
    path(
        "painel/grafico-custo-geracao/",
        views.grafico_custo_geracao,
        name="grafico_custo_geracao",
    ),
    path(
        "painel/atualizar-precos/",
        views.atualizar_precos_view,
        name="atualizar_precos_painel",
    ),
    path(
        "projeto/<int:projeto_id>/sugerir-equipamento/",
        views.sugerir_equipamento_fotovoltaico,
        name="sugerir_equipamento_fotovoltaico",
    ),
    path(
        "projeto/<int:projeto_id>/exportar-sugestoes/",
        views.exportar_sugestoes,
        name="exportar_sugestoes",
    ),
    # path(
    #     "projeto/<int:projeto_id>/exportar-sugestoes-pdf/",
    #     views.exportar_sugestoes_pdf,
    #     name="exportar_sugestoes_pdf"
    # ),
    path(
        "cehtes/analisar_perguntas_ia/<str:pergunta>",
        views.analisar_perguntas_ia_view,
        name="analisar_perguntas_ia",
    ),
    path(
        "cehtes/auditar_perguntas_IA",
        views.auditar_perguntas_ia_view,
        name="auditar_perguntas_IA",
    ),
    path(
        "cehtes/criar_bateria",
        views.criar_bateria,
        name="criar_bateria",
    ),
    path(
        "cehtes/criar_hidrogenio",
        views.criar_hidrogenio,
        name="criar_hidrogenio",
    ),
    path(
        "cehtes/criar_painel_solar",
        views.criar_painel_solar,
        name="criar_painel_solar",
    ),
    path(
        "cehtes/criar_controlador_carga",
        views.criar_controlador_carga,
        name="criar_controlador_carga",
    ),
    path(
        "cehtes/criar_inversor",
        views.criar_inversor,
        name="criar_inversor",
    ),
    # ! URLs para Pedidos
    path(
        "certidoes/criar_pedido",
        views.criar_pedido_certidao,
        name="pedido_certidao_criar_pedido",
    ),
    path(
        "certidoes/pedidos/",
        views.pedido_certidao_list_view,
        name="pedido_certidao_listar_pedidos",
    ),
    path(
        "certidoes/pedidos/<int:pk>/detalhes",
        views.pedido_certidao_detail_view,
        name="pedido_certidao_detalhes",
    ),
    path(
        "certidoes/pedidos/<str:numero_pedido_certidao>/detalhes_numero_certidao",
        views.pedido_certidao_numero_certidao_view,
        name="pedido_certidao_detalhes_numero_certidao",
    ),
    path(
        "certidoes/pedidos/<int:pk>/exportar",
        views.PedidoCertidaoExportarView.as_view(),
        name="pedido_certidao_exportar",
    ),
    # path(
    #     "certidoes/pedidos/<int:pk>/exportar",
    #     views.pedido_certidao_exportar_caixa_viewView.as_view(),
    #     name="pedido_certidao_exportar_caixa",
    # ),
    path(
        "certidoes/pedidos/<int:pk>/enviar_pedido_caixa",
        views.pedido_certidao_caixa_view,
        name="pedido_certidao_enviar_ao_caixa",
    ),
    path(
        "certidoes/etiqueta/<int:pk>/emitir_etiqueta",
        views.PedidoCertidaoEmitirEtiquetaView.as_view(),
        name="pedido_certidao_emitir_etiqueta",
    ),
    path(
        "certidoes/pedidos/<int:pk>/enviar_confirmar_entrega",
        views.pedido_certidao_confirmar_entrega_view,
        name="pedido_certidao_confirmar_entrega",
    ),
    path(
        "certidoes/pedidos/<int:pk>/editar_apresentante/",
        views.PedidoCertidaoApresentanteUpdateView.as_view(),
        name="pedido_certidao_editar_apresentante",
    ),
    path(
        "certidoes/pedidos/<int:pedido_id>/listar_certidoes/",
        views.PedidoCertidaoCertidoesListView.as_view(),
        name="pedido_certidao_listar_certidoes_pedido",
    ),
    path(
        "certidoes/pedidos/<int:numero_pedido>/listar_selos_certidoes/",
        views.certidoes_listar_selo,
        name="certidoes_listar_selo",
    ),
    path(
        "certidoes/pedidos/<int:pk>/recibo/",
        views.PedidoCertidaoReciboView.as_view(),
        name="pedido_certidao_recibo",
    ),
    path(
        "certidoes/caixa/pedidos/<int:pk>/recibo/",
        views.PedidoCertidaoReciboDoCaixaView.as_view(),
        name="pedido_certidao_recibo_do_caixa",
    ),
    path(
        "certidoes/impressao-recibos/",
        views.PedidoCertidaoImpressaoRecibosView.as_view(),
        name="pedido_certidao_impressao_recibos",
    ),
    path(
        "certidoes/pedidos/relatorio/",
        views.PedidoCertidaoRelatorioView.as_view(),
        name="pedido_certidao_relatorio",
    ),  # ! URLs para imóveis
    path(
        "certidoes/<int:pedido_id>/imoveis/",
        views.PedidoCertidaoImovelListView.as_view(),
        name="pedido_certidao_imoveis_listar",
    ),
    path(
        "certidoes/<int:pedido_id>/imoveis/adicionar_imovel/",
        views.pedido_certidao_imovel_create,
        name="pedido_certidao_adicionar_imovel",
    ),
    path(
        "certidoes/imoveis/<int:pk>/update/",
        views.pedido_certidao_imovel_update,
        name="pedido_certidao_update_imovel",
    ),
    path(
        "certidoes/imoveis/<int:pk>/detalhes/",
        views.pedido_certidao_imovel_detail,
        name="pedido_certidao_detalhes_imovel",
    ),
    path(
        "certidoes/recebimento/<int:pk>/",
        views.confirmar_recebimento_certidao_view,
        name="pedido_certidao_confirmar_recebimento",
    ),
    path(
        "certidoes/imoveis/<int:pk>/delete/",
        views.PedidoCertidaoImovelDeleteView.as_view(),
        name="pedido_certidao_excluir_imovel",
    ),
    path(
        "certidoes/imoveis/<int:imovel_id>/listar_certidoes",
        views.PedidoCertidaoCertidoesImovelListView.as_view(),
        name="pedido_certidao_listar_certidoes_imovel",
    ),
    # ! URLs para pessoas
    path(
        "certidoes/<int:pedido_id>/pessoas/listar/",
        views.pedido_certidao_pessoas_list_view,
        name="pedido_certidao_pessoas_list",
    ),
    path(
        "certidoes/<int:pedido_id>/pessoas/adicionar/",
        views.pedido_certidao_pessoa_create,
        name="pedido_certidao_pessoa_create",
    ),
    path(
        "certidoes/pessoas/<int:pk>/update/",
        views.pedido_certidao_pessoa_update,
        name="pedido_certidao_pessoa_update",
    ),
    path(
        "certidoes/pessoas/<int:pk>/detalhes/",
        views.PedidoCertidaoPessoaDetailView.as_view(),
        name="pedido_certidao_detalhes_pessoa",
    ),
    path(
        "certidoes/pessoas/<int:pk>/delete/",
        views.PedidoCertidaoPessoaDeleteView.as_view(),
        name="pedido_certidao_excluir_pessoa",
    ),
    path(
        "certidoes/pessoas/<int:pessoa_id>/listar_certidoes",
        views.CertidoesPessoaListView.as_view(),
        name="pedido_certidao_listar_certidoes_pessoa",
    ),
    path(
        "certidoes/pedidos/<int:pedido_id>/andamentos/adicionar/",
        views.PedidoCertidaoAndamentoCreateView.as_view(),
        name="pedido_certidao_andamento_adicionar",
    ),
    path(
        "certidoes/pedidos/<int:pedido_certidao_id>/anexos/",
        views.PedidoCertidaoAnexosListView.as_view(),
        name="pedido_certidao_anexos_list",
    ),
    path(
        "certidoes/pedidos/<int:pedido_certidao_id>/anexos/create",
        views.PedidoCertidaoAnexoCreateView.as_view(),
        name="pedido_certidao_anexo_create",
    ),
    path(
        "certidoes/pedidos/adicionar_andamentos/",
        views.pedido_certidao_andamento_adicionar_mesmo_colaborador_lista,
        name="pedido_certidao_andamento_adicionar_mesmo_colaborador_lista",
    ),
    path(
        "certidoes/pedidos/<int:pedido_id>/<int:tipo_andamento_id>/andamentos/adicionar/",
        views.pedido_certidao_andamento_adicionar_mesmo_colaborador,
        name="pedido_certidao_andamento_adicionar_mesmo_colaborador",
    ),
    path(
        "certidoes/pedidos/adicionar_andamentos/",
        views.pedido_certidao_andamento_adicionar_mesmo_colaborador_lista,
        name="pedido_certidao_andamento_adicionar_mesmo_colaborador_lista",
    ),
    path(
        "certidoes/andamentos/<int:pk>/editar/",
        views.pedido_certidao_andamento_update,
        name="pedido_certidao_andamento_editar",
    ),
    path(
        "certidoes/andamentos/<int:pk>/desativar/",
        views.pedido_certidao_andamento_desativar,
        name="pedido_certidao_andamento_desativar",
    ),
    path(
        "certidoes/andamentos/<int:pk>/ativar/",
        views.pedido_certidao_andamento_ativar,
        name="pedido_certidao_andamento_ativar",
    ),
    path(
        "certidoes/<int:pedido_id>/andamentos/listar/",
        views.PedidoCertidaoAndamentoListView.as_view(),
        name="pedido_certidao_andamento_listar",
    ),
    path(
        "certidoes/<int:pedido_id>/andamentos/",
        views.PedidoCertidaoAndamentoListView.as_view(),
        name="pedido_certidao_andamentos",
    ),
    path(
        "certidoes/gerar_selo/onr/todo_dia_atual/<int:origem_id>",
        views.pedido_certidao_gerar_selo_onr_todo_dia_atual,
        name="pedido_certidao_gerar_selo_onr_todo_dia_atual",
    ),
    path(
        "certidoes/gerar_selo/gerar_selo_pedido_certidao_onr",
        views.pedido_certidao_onr_gerar_selo_view,
        name="pedido_certidao_gerar_selo_pedido_certidao_onr",
    ),
    path(
        "certidoes/gerar_selo/gerar_selo_pedido_certidao",
        views.pedido_certidao_gerar_selo_pedido_certidao,
        name="gerar_selo_pedido_certidao",
    ),
    path(
        "protocolos/gerar_selo_protocolos_onr",
        views.gerar_selo_protocolos_onr_view,
        name="gerar_selo_protocolos_onr",
    ),
    path(
        "certidoes/certidao/download_excel_certidao_onr/origem/<int:origem_id>/de/<str:data_inicio>/ate/<str:data_fim>/",
        views.download_excel_certidao_onr,
        name="pedido_certidao_download_excel_certidao_onr",
    ),
    path(
        "certidoes/onr/relatorio/excel/download",
        views.certidoes_onr_relatorio_excel_por_ids,
        name="certidoes_onr_relatorio_excel_por_ids",
    ),
    path(
        "protocolos/onr/relatorio/excel/download",
        views.protocolos_onr_relatorio_excel_por_ids,
        name="protocolos_onr_relatorio_excel_por_ids",
    ),
    path(
        "certidoes/pedido_certidao_cancelar/<int:pk>/",
        views.pedido_certidao_cancelar,
        name="pedido_certidao_cancelar",
    ),
    path("selos_sqlserver/", views.selos_sqlserver_view, name="selos_sqlserver"),
    path(
        "limpar_selo/<str:numero_selo>/",
        views.limpar_selo,
        name="limpar_selo",
    ),
    # path("modelo/<int:pk>/pdf/", views.modelo_pdf, name="modelo_pdf"),
    #  path("grafico_caixa/", views.caixa_grafico_view, name="grafico_caixa"),
    path("get-ai-suggestion/", views.get_ai_suggestion, name="get_ai_suggestion"),
    path("search/", SearchView(), name="search"),
    path(
        "pedido_certidao/<int:pk>/selar_certidoes",
        views.pedido_certidao_selar_certidoes_view,
        name="pedido_certidao_selar",
    ),
    path(
        "pedido_certidao/<int:pk>/atualizar_sistema_anterior",
        views.pedido_certidao_atualizar_sistema_anterior_view,
        name="pedido_certidao_atualizar_sistema_anterior",
    ),
]


router.register(r"protocolos", views.Livro01ProtocoloViewSet)
router.register(
    r"pedido_certidao_imovel",
    views.PedidoCertidaoImovelViewSet,
    basename="pedido_certidao_imovel",
)

urlpatterns += [path("api/", include(router.urls))]
