import logging

from django.contrib import admin

from apps.home.admin_custom import *
from apps.home.models import (
    Anexo,
    Anterior,
    Apresentante,
    AtoPratica,
    Backup,
    Caixa,
    Certidao,
    CertidaoEmitida,
    CertificadoDigital,
    ChatRoom,
    ChecklistBalcao,
    ChecklistBalcaoAto,
    ChecklistBalcaoAtoTexto,
    ChecklistBalcaoEscolha,
    CheckListRealizado,
    ChecklistRealizadoHistorico,
    Cidade,
    Colaborador,
    ColaboradorSetor,
    Configuracao,
    Contribuintes,
    Documento,
    EmolumentoAno,
    Emolumentos,
    EmolumentoValor,
    EstadoCivil,
    Event,
    EventMember,
    EventRecorrente,
    EventRecorrenteFrequencia,
    FaseAgenda,
    FaseAgendaItem,
    FaseAgendaItemAndamento,
    FichaAuxiliar,
    Files,
    Finalidade,
    Financeiro,
    FinanceiroPeriodicidade,
    Funcionario,
    GrupoDistribuicaoProtocolo,
    GrupoTipoAndamento,
    GrupoUsuario,
    GrupoUsuarioAgendaCertidao,
    ImovelClasse,
    ImovelMedida,
    Issqn,
    Lembrete,
    Livro01Andamento,
    Livro01Protocolo,
    Livro02,
    Livro02Texto,
    Livro03,
    Livro03Descricao,
    Livro03Garantia,
    Livro03Ligacao,
    Livro04,
    Livro05,
    Livro05Lri,
    LogAssinaturaDigital,
    Lote,
    Lri,
    LriAtualizacao,
    LriDocumento,
    LriPartesEnvolvidas,
    Message,
    MinutaAuxiliar,
    ModeloTexto,
    MotivoAssinaturaDigital,
    NivelAlerta,
    NotaDevolucaoTexto,
    OrdemDigitalizarBalcao,
    OrdemDigitalizarBalcaoAto,
    OrdemDigitalizarEscolha,
    Pedido,
    PedidoCertidao,
    PedidoCertidaoAndamento,
    PedidoCertidaoImovel,
    PedidoCertidaoPessoa,
    PedidoItem,
    PedidoItemImovel,
    PedidoParte,
    PedidoParteAto,
    Pergunta,
    PerguntaAcao,
    PerguntaGrupo,
    PerguntaMinuta,
    PerguntaSetor,
    PessoaEndereco,
    ProtocoloEmFase,
    RegistroVinculado,
    Rua,
    Rural,
    RuralNome,
    SeloEletronico,
    Sequencia,
    ServicoLivro01,
    ServicoLivro01Historico,
    StatusProtocolo,
    TipoAndamento,
    TipoAndamentoCertidao,
    TipoApresentante,
    TipoArmazenamento,
    TipoCategoriaFinanceira,
    TipoCertidao,
    TipoClasseRegistro,
    TipoDocumentoAssinatura,
    TipoFaseProtocolo,
    TipoFaseProtocoloColaborador,
    TipoItemCertidao,
    TipoLogradouro,
    TipoModelo,
    TipoOperacaoFinanceira,
    TipoRegimeCasamento,
    TipoRegistroAuxiliar,
    TipoRegistroProtocolo,
    TipoTransacaoFinanceira,
    TipoTributacao,
    TipoUnidade,
    TipoVinculo,
    Titulo,
    Transacao,
    Unidade,
    ValorCertidao,
    Vinculo,
)

logger = logging.getLogger(__name__)

logger.debug(f"Iniciando {__name__}")


@admin.register(TipoClasseRegistro)
class TipoClasseRegistroAdmin(admin.ModelAdmin):
    list_display = ("id", "descricao", "letra")


@admin.register(TipoTransacaoFinanceira)
class TipoTransacaoFinanceiraAdmin(admin.ModelAdmin):
    list_display = ("id", "descricao")


@admin.register(TipoOperacaoFinanceira)
class TipoOperacaoFinanceiraAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "descricao",
        "ordem_exibir",
        "grupo_dinheiro",
        "grupo_entradas",
        "tipo_pagamento_id_sistema_antigo",
        "valor_default_transacao",
    )


@admin.register(TipoCategoriaFinanceira)
class TipoCategoriaFinanceiraAdmin(admin.ModelAdmin):
    list_display = ("id", "descricao")


@admin.register(StatusProtocolo)
class StatusProtocoloAdmin(admin.ModelAdmin):
    list_display = ("id", "descricao", "finalizar")


@admin.register(Anexo)
class AnexoAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "nome",
        "descricao",
        "arquivo",
        "created_at",
        "updated_at",
        "content_type",
        "object_id",
        "uploaded_by",
    )
    search_fields = ("nome", "descricao", "arquivo")
    list_filter = ("created_at", "updated_at")
    raw_id_fields = ("content_type", "uploaded_by")
    date_hierarchy = "created_at"


@admin.register(TipoRegimeCasamento)
class TipoRegimeCasamentoAdmin(admin.ModelAdmin):
    list_display = ("id", "descricao_regime", "pacto", "exibir")


@admin.register(Files)
class FilesAdmin(admin.ModelAdmin):
    list_display = ("id", "file")


@admin.register(Funcionario)
class FuncionarioAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "nome",
        "sobrenome",
        "cpf",
        "tempo_de_servico",
        "remuneracao",
    )


@admin.register(Sequencia)
class SequenciaAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "numero_protocolo",
        "numero_matricula",
        "numero_talao",
        "numero_recibo",
        "numero_protocolo_ec",
        "numero",
    )


@admin.register(EstadoCivil)
class EstadoCivilAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "nome",
        "descricao_estado_civil",
        "tipo",
        "descricao_minuta",
        "texto_masculino",
        "texto_feminino",
        "exibir",
        "requerer_tipo_regime",
        "descricao",
        "codigo_regime",
        "auxiliar_id",
        "estacao",
        "secao",
        "tipo_regime",
        "tipo_pessoa",
        "nao_consta",
        "exibirpessoal",
        "auxiliar_certidao_id",
        "estadocivil01",
        "estadocivil02",
        "estadocivil03",
        "estadocivil04",
        "certidao1m",
        "certidao2m",
        "certidao3m",
        "certidao4m",
        "certidao1f",
        "certidao2f",
        "certidao3f",
        "certidao4f",
        "qualificacao1",
        "qualificacao2",
        "nome_solteiro_atualizado",
        "textoauxnome",
        "trial585",
        "observacao",
    )


@admin.register(Livro05)
class Livro05Admin(admin.ModelAdmin):
    list_display = (
        "id",
        "cpf",
        "nome",
        "documento",
        "sexo",
        "nacionalidade",
        "numero_ficha",
        "estado_civil",
        "tipo_regime_casamento",
        "profissao",
        "criado_em",
        "data_alteracao",
        "nome_pai",
        "nome_mae",
        "endereco",
        "data_nascimento",
        "data_casamento",
        "data_expedicao",
        "data_atualizacao",
        "email",
        "naturalidade",
        "telefone",
        "cidade",
        "uf",
        "telefone_2",
        "conjuge",
        "cep",
        "pessoa_juridica",
        "tipo_regime",
        "tipo_documento",
        "tipo_pessoa",
        "numero_controle",
        "nome_original",
        "orgao_emissor",
        "situacao",
        "tipo_casamento",
        "temporario_conjuge",
    )
    list_filter = (
        "criado_em",
        "data_alteracao",
        "data_nascimento",
        "data_casamento",
        "data_expedicao",
        "data_atualizacao",
    )
    raw_id_fields = ("estado_civil", "tipo_regime_casamento")


@admin.register(Rural)
class RuralAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "imovel",
        "area",
        "caracteristica",
        "reserva_florestal",
        "georeferencial",
        "area_inteiro",
        "gleba",
        "datatexto",
        "gleba2",
        "localizacao",
        "remanescente",
    )
    raw_id_fields = ("imovel",)


@admin.register(RuralNome)
class RuralNomeAdmin(admin.ModelAdmin):
    list_display = ("id", "imovel", "nome", "localizacao", "area")
    raw_id_fields = ("imovel",)


@admin.register(Livro02)
class Livro02Admin(admin.ModelAdmin):
    list_display = (
        "id",
        "criado_por",
        "modificado_por",
        "modificado_em",
        "numero",
        "tipo",
        "cartorio",
        "classe",
        "municipio",
        "encerrado",
        "data_abertura",
        "registro_anterior",
        "numero_nirf",
        "numero_ccirr",
        "numero_car",
        "numero_incra",
        "numero_itr",
        "cnm",
        "tipo_unidade",
        "data_validade_itr",
        "area_construida_residencial",
        "area_construida_comercial",
        "area_construida",
        "cep",
        "criado_em",
        "ultimo_livro",
        "ultimo_folha",
        "texto",
        "data_envio_cnm",
        "enviar_cnm",
        "data_envio_livro_4",
        "enviar_livro_4",
        "arquivo",
    )
    list_filter = (
        "modificado_em",
        "data_abertura",
        "criado_em",
        "data_envio_cnm",
        "enviar_cnm",
        "data_envio_livro_4",
        "enviar_livro_4",
    )
    raw_id_fields = ("criado_por", "modificado_por")


@admin.register(Livro04)
class Livro04Admin(admin.ModelAdmin):
    list_display = (
        "id",
        "criado_por",
        "modificado_por",
        "modificado_em",
        "numero",
        "tipo",
        "cartorio",
        "classe",
        "municipio",
        "encerrado",
        "data_abertura",
        "registro_anterior",
        "numero_nirf",
        "numero_ccirr",
        "numero_car",
        "numero_incra",
        "numero_itr",
        "cnm",
        "tipo_unidade",
        "data_validade_itr",
        "area_construida_residencial",
        "area_construida_comercial",
        "area_construida",
        "cep",
        "criado_em",
        "ultimo_livro",
        "ultimo_folha",
        "texto",
        "data_envio_cnm",
        "enviar_cnm",
        "data_envio_livro_4",
        "enviar_livro_4",
        "arquivo",
    )
    list_filter = (
        "modificado_em",
        "data_abertura",
        "criado_em",
        "data_envio_cnm",
        "enviar_cnm",
        "data_envio_livro_4",
        "enviar_livro_4",
    )
    raw_id_fields = ("criado_por", "modificado_por")


@admin.register(Contribuintes)
class ContribuintesAdmin(admin.ModelAdmin):
    list_display = ("id", "imovel", "valor", "numero_contribuinte")
    raw_id_fields = ("imovel",)


@admin.register(TipoUnidade)
class TipoUnidadeAdmin(admin.ModelAdmin):
    list_display = ("id", "descricao")


@admin.register(Unidade)
class UnidadeAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "imovel",
        "registro_anterior",
        "criado_em",
        "numero_unidade",
        "tipo",
        "construida",
        "nome_edificio",
        "quadra",
        "area",
        "lote_auxiliar",
        "sequencial",
        "bloco",
        "gleba",
    )
    list_filter = ("criado_em",)
    raw_id_fields = ("imovel", "registro_anterior", "tipo")


@admin.register(Lote)
class LoteAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "unidade",
        "area",
        "quadra",
        "setor",
        "residencial",
        "numero_unidade",
        "numero_edificacao",
        "superquadra",
        "conjunto",
        "bloco",
        "outras",
        "unidade_aux",
        "comercial",
        "numero_municipal",
    )
    raw_id_fields = ("unidade",)


@admin.register(TipoLogradouro)
class TipoLogradouroAdmin(admin.ModelAdmin):
    list_display = ("id", "descricao", "codigo")


@admin.register(Rua)
class RuaAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "unidade",
        "logradouro",
        "nome",
        "numero_edificacao",
        "cep",
        "tipo",
        "complemento",
    )
    raw_id_fields = ("unidade", "logradouro")


@admin.register(ImovelMedida)
class ImovelMedidaAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "imovel",
        "m_frente_metros",
        "p_frente_metros",
        "m_direito_metros",
        "p_direito_metros",
        "p_esquerdo_metros",
        "m_esquerdo_metros",
        "p_fundo_metros",
        "m_fundo_metros",
    )
    list_filter = ("imovel",)


@admin.register(Anterior)
class AnteriorAdmin(admin.ModelAdmin):
    list_display = ("id", "imovel", "numero", "tipo", "complemento")
    raw_id_fields = ("imovel",)


@admin.register(Titulo)
class TituloAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "tipo_titulo",
        "exibir",
        "prazo",
        "prazo_reentrada",
        "prazo_validade",
        "ato_principal",
        "prazo_nota_devolucao",
        "prazo_nota_devolucao_complexo",
        "titulo_prenotacao",
    )


@admin.register(Configuracao)
class ConfiguracaoAdmin(admin.ModelAdmin):
    # Campos a serem exibidos na lista
    list_display = ("sessao", "chave", "valor", "descricao")

    # Campos para busca
    search_fields = ("sessao", "chave", "valor", "descricao")

    # Filtros laterais
    list_filter = ("sessao", "chave")

    # Ordenação padrão
    ordering = ("sessao", "chave")

    # Edição inline
    list_editable = ("valor",)

    # Configuração de ações
    actions = ["marcar_como_ativo", "marcar_como_inativo"]

    def marcar_como_ativo(self, request, queryset):
        queryset.update(is_active=True)

    marcar_como_ativo.short_description = "Marcar selecionados como ativos"

    def marcar_como_inativo(self, request, queryset):
        queryset.update(is_active=False)

    marcar_como_inativo.short_description = "Marcar selecionados como inativos"

    # Personalizar o formulário de edição
    fieldsets = (
        (None, {"fields": ("sessao", "chave", "valor", "descricao")}),
        (
            "Opções Avançadas",
            {
                "classes": ("collapse",),
                "fields": ("is_active",),
            },
        ),
    )


@admin.register(AtoPratica)
class AtoPraticaAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "tipo_ato",
        "codigo_doi_id",
        "pasta_minutas",
        "exibir",
        "tipo",
        "titulo",
        "ato_principal",
        "emolumento",
        "dias_uteis",
        "ato_default",
        "dias_uteis_reentrada",
        "peso_titulo",
        "ato_prenotacao",
    )
    raw_id_fields = ("titulo",)


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "data_entrada",
        "data_prevista",
        "data_validade",
        "observacao",
        "tipo_servico",
        "numero_talao",
        "numero",
        "endereco",
        "municipio",
        "uf",
        "telefone",
        "telefone1",
        "email",
        "tipo_documento_apresentante",
        "documento_apresentante",
    )
    list_filter = ("data_entrada", "data_prevista", "data_validade")


@admin.register(TipoFaseProtocolo)
class TipoFaseProtocoloAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "ordem",
        "descricao",
        "nome",
        "prazo_dias",
        "grupo",
    )


@admin.register(FaseAgenda)
class FaseAgendaAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "nome",
        "prazo",
        "prazo_opcional",
        "descricao",
        "usar_data_atual",
    )


@admin.register(FaseAgendaItem)
class FaseAgendaItemAdmin(admin.ModelAdmin):
    list_display = ("id", "fase_agenda", "status")
    list_filter = ("fase_agenda", "status")


@admin.register(Colaborador)
class ColaboradorAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "nome",
        "inativo",
        "default",
        "antigo_id",
        "usuario",
        "recebe_protocolos_do_balcao",
        "calcula_peso",
        "exibir_nome_caixa",
    )
    list_filter = (
        "default",
        "recebe_protocolos_do_balcao",
        "calcula_peso",
        "exibir_nome_caixa",
    )
    raw_id_fields = ("usuario",)


@admin.register(TipoFaseProtocoloColaborador)
class TipoFaseProtocoloColaboradorAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "fase_protocolos",
        "colaborador",
        "fase_protocolos_solicitar_servicos",
        "descricao",
    )
    list_filter = (
        "fase_protocolos",
        "colaborador",
        "fase_protocolos_solicitar_servicos",
    )


@admin.register(NivelAlerta)
class NivelAlertaAdmin(admin.ModelAdmin):
    list_display = ("id", "descricao")


@admin.register(Lembrete)
class LembreteAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "imovel",
        "created_at",
        "updated_at",
        "descricao",
        "funcionarios_create",
        "funcionarios_update",
        "nivel_alerta",
    )
    list_filter = (
        "imovel",
        "created_at",
        "updated_at",
        "funcionarios_create",
        "funcionarios_update",
        "nivel_alerta",
    )
    date_hierarchy = "created_at"


@admin.register(Livro01Protocolo)
class Livro01ProtocoloAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "numero_protocolo",
        "titulo",
        "pedido",
        "data_protocolo",
        "observacao",
        "numero_origem",
        "origem_pedido",
        "fases_protocolo",
        "fases_protocolo_colaborador",
        "fases_protocolo_colaborador_atual",
        "data_distribuicao",
        "data_finalizado",
        "maximo_dias_titulo",
        "maximo_dias_titulo_reentrada",
        "status",
        "fases_protocolo_colaborador_atual_data",
        "numero_protocolo_anterior",
        "numero_protocolo_posterior",
        "protocolo_onr",
    )
    list_filter = (
        "data_protocolo",
        "data_distribuicao",
        "data_finalizado",
        "fases_protocolo_colaborador_atual_data",
    )
    raw_id_fields = (
        "pedido",
        "fases_protocolo",
        "fases_protocolo_colaborador",
        "fases_protocolo_colaborador_atual",
        "status",
        "numero_protocolo_anterior",
        "numero_protocolo_posterior",
    )


@admin.register(EmolumentoAno)
class EmolumentoAnoAdmin(admin.ModelAdmin):
    list_display = ("id", "data_inicial", "data_final", "descricao_periodo")
    list_filter = ("data_inicial", "data_final")


@admin.register(Emolumentos)
class EmolumentosAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "nome",
        "utilizado",
        "ato_complementar",
        "atos",
        "titulo",
        "desconto",
        "descricao",
        "inativo",
        "gerarselo",
        "codigo_tabela_inicial",
        "emolumento_default",
        "emolumento_prenotacao",
    )
    raw_id_fields = ("atos", "titulo")


@admin.register(TipoTributacao)
class TipoTributacaoAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "descricao",
        "outros_codigo_trib_tj",
        "outros",
        "utilizado",
        "percentual_desconto",
        "ativo_certidao",
        "ativo_protocolo",
    )
    list_filter = ("ativo_certidao", "ativo_protocolo")


@admin.register(PedidoItem)
class PedidoItemAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "pedido",
        "ato",
        "titulo",
        "vigencia",
        "tabelacalculo",
        "cdhu",
        "codigo_tabela",
        "numero_registro",
        "tipo_registro",
        "numero_ato",
        "selo",
        "numero_ri",
        "custas",
        "colaborador",
        "numero_titulo",
        "data_pagamento",
        "valor_emolumento",
        "valor_tfj",
        "valor_fundo_estado",
        "valor_itbi",
        "valor_issqn",
        "valor_avaliacao",
        "ato_tipo",
        "ato_numero",
    )
    list_filter = ("data_pagamento",)
    raw_id_fields = (
        "pedido",
        "ato",
        "titulo",
        "vigencia",
        "tabelacalculo",
        "custas",
    )


@admin.register(Livro02Texto)
class Livro02TextoAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "numero_ato",
        "imovel",
        "pedido_item",
        "texto",
        "estado_civil_texto_id",
    )
    list_filter = ("imovel", "pedido_item")


@admin.register(NotaDevolucaoTexto)
class NotaDevolucaoTextoAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "numero_ato",
        "imovel",
        "pedido_item",
        "pedidos",
        "texto",
    )
    list_filter = ("imovel", "pedido_item", "pedidos")


@admin.register(ProtocoloEmFase)
class ProtocoloEmFaseAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "protocolos",
        "ordem",
        "TipoFaseProtocolo",
        "data_protocolo",
        "data_fase",
        "qtde_dias",
        "status",
        "data_iniciou",
        "data_finalizou",
    )
    list_filter = (
        "TipoFaseProtocolo",
        "data_protocolo",
        "data_fase",
        "data_iniciou",
        "data_finalizou",
    )


@admin.register(SeloEletronico)
class SeloEletronicoAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "criado_por",
        "modificado_por",
        "criado_em",
        "modificado_em",
        "pedido_item",
        "certidao",
        "codigo_sequencial_unico",
        "codigo_de_seguranca",
        "utilizado_em",
        "cancelado_em",
        "selo_de_consulta",
    )
    list_filter = (
        "criado_em",
        "modificado_em",
        "utilizado_em",
        "cancelado_em",
    )
    raw_id_fields = (
        "criado_por",
        "modificado_por",
        "pedido_item",
        "certidao",
    )


@admin.register(TipoAndamento)
class TipoAndamentoAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "servico",
        "descricao_servico",
        "atualizar_status_protocolo",
        "ativo",
        "grupo_cancelado",
        "grupo_registrado",
        "grupo_exigencia",
        "grupo_cancelado_registrado",
        "grupo_subjudice",
        "grupo_reentrada",
        "grupo_reentrada_pagamento",
        "grupo_finalizado",
        "grupo_exigencia_positiva",
        "grupo_em_registro",
        "grupo_pronto_registrar",
        "grupo_distribuicao",
        "grupo_digitalizar",
        "grupo_ultimo_andamento",
        "grupo_servico_recebido",
        "grupo_reprotocolado",
        "grupo_recepcao",
    )
    list_filter = ("ativo",)


@admin.register(Livro01Andamento)
class Livro01AndamentoAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "criado_por",
        "modificado_por",
        "criado_em",
        "modificado_em",
        "protocolo",
        "colaborador",
        "tipo_andamento",
        "data",
        "colaborador_destino",
        "arquivo_assinado",
        "andamento_ativo",
        "texto",
        "data_importacao",
    )
    list_filter = ("criado_em", "modificado_em", "data", "data_importacao")
    raw_id_fields = (
        "criado_por",
        "modificado_por",
        "protocolo",
        "colaborador",
        "tipo_andamento",
        "colaborador_destino",
    )


@admin.register(FaseAgendaItemAndamento)
class FaseAgendaItemAndamentoAdmin(admin.ModelAdmin):
    list_display = ("id", "fase_agenda", "tipo_andamento")


@admin.register(ServicoLivro01)
class ServicoLivro01Admin(admin.ModelAdmin):
    list_display = ("id", "descricao")


@admin.register(ServicoLivro01Historico)
class ServicoLivro01HistoricoAdmin(admin.ModelAdmin):
    list_display = ("id", "servico_livro01", "data")
    list_filter = ("servico_livro01", "data")


@admin.register(EventRecorrenteFrequencia)
class EventRecorrenteFrequenciaAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "start_time_01",
        "start_time_02",
        "start_time_03",
        "start_time_04",
        "start_time_05",
    )


@admin.register(EventRecorrente)
class EventRecorrenteAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "description",
        "url",
        "event_recorrente_frequencia",
    )
    list_filter = ("event_recorrente_frequencia",)


@admin.register(EmolumentoValor)
class EmolumentoValorAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "criado_por",
        "modificado_por",
        "criado_em",
        "modificado_em",
        "emolumento",
        "vigencia",
        "codigo_tabela",
        "faixa_inicio",
        "faixa_fim",
        "valor_fundo_estado",
        "percentual_issqn",
        "valor_taxa2",
        "valor_taxa3",
        "valor_taxa4",
        "valor_emolumento",
        "valor_tfj",
        "valor_adicionado_2",
        "chave_emolumentos",
    )
    list_filter = ("criado_em", "modificado_em")
    raw_id_fields = (
        "criado_por",
        "modificado_por",
        "emolumento",
        "vigencia",
    )


@admin.register(FinanceiroPeriodicidade)
class FinanceiroPeriodicidadeAdmin(admin.ModelAdmin):
    list_display = ("id", "descricao", "quantidade_dias")


@admin.register(Financeiro)
class FinanceiroAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "pedido",
        "data_transacao",
        "descricao",
        "tipotransacao",
        "tipodocumento",
        "valor_transacao",
        "cheque",
        "pedido_certidao_id",
        "colaborador",
        "numero_protocolo_ec",
        "numero_pedido_certidao",
        "colaborador_confirmado",
        "dadp",
        "imposto_renda",
        "tipo_transacao",
        "tipo_operacao_financeira",
        "tipo_categoria_financeira",
        "ativo",
        "data_transacao_cancelado",
        "valor_transacao_cancelado",
        "colaborador_transacao_cancelado",
        "descricao_cancelado",
        "numero_parcela",
        "quantidade_parcela",
        "data_original_transacao",
        "nome_interessado",
        "data_transacao_colaborador_confirmado",
    )
    list_filter = (
        "data_transacao",
        "data_transacao_cancelado",
        "data_original_transacao",
        "data_transacao_colaborador_confirmado",
    )
    raw_id_fields = (
        "pedido",
        "colaborador",
        "colaborador_confirmado",
        "tipo_transacao",
        "tipo_operacao_financeira",
        "tipo_categoria_financeira",
        "colaborador_transacao_cancelado",
    )


@admin.register(PedidoParte)
class PedidoParteAdmin(admin.ModelAdmin):
    list_display = ("id", "pedido", "pessoa", "papel", "pessoa_conjuge")
    raw_id_fields = ("pedido", "pessoa", "pessoa_conjuge")


@admin.register(Livro05Lri)
class Livro05LriAdmin(admin.ModelAdmin):
    list_display = ("id", "cpf")


@admin.register(LriDocumento)
class LriDocumentoAdmin(admin.ModelAdmin):
    list_display = ("id", "cpf_cnpj", "nome")


@admin.register(LriAtualizacao)
class LriAtualizacaoAdmin(admin.ModelAdmin):
    list_display = ("id", "data_atualizacao", "data_pedido")
    list_filter = ("data_atualizacao", "data_pedido")


@admin.register(Lri)
class LriAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "protocolo_indisponibilidade",
        "data_pedido",
        "numero_do_processo",
        "telefone",
        "nome_instituicao",
        "forum_vara",
        "usuario",
        "email",
        "cancelamento_indisponibilidade",
        "cancelamento_tipo",
        "cancelamento_data",
        "observacao",
        "uso_origem",
        "descricao_cpf_cnpj",
        "descricao_detalhes",
        "data",
    )
    list_filter = ("data_pedido", "cancelamento_data", "data")


@admin.register(LriPartesEnvolvidas)
class LriPartesEnvolvidasAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "cancelado_em",
        "lri",
        "tipo_ato",
        "numero_ato",
        "vinculo",
        "situacao",
        "data",
        "pessoa",
        "matricula",
        "numero_imovel",
        "tipo_imovel",
        "data_envio",
        "numero",
        "tipo",
        "cartorio",
        "data_importacao",
        "cancelamento_indisponibilidade",
        "data_atualizacao",
        "descricao_cpf_cnpj",
        "uso_origem",
    )
    list_filter = (
        "cancelado_em",
        "data",
        "data_envio",
        "data_importacao",
        "data_atualizacao",
    )
    raw_id_fields = ("lri", "pessoa")


@admin.register(TipoVinculo)
class TipoVinculoAdmin(admin.ModelAdmin):
    list_display = ("id", "descricao", "grupo_acoes", "grupo_onus")


@admin.register(Vinculo)
class VinculoAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "criado_por",
        "modificado_por",
        "criado_em",
        "modificado_em",
        "imovel",
        "pessoa",
        "tipo_regime_casamento",
        "tipo_vinculo",
        "estado_civil",
        "situacao",
        "numero_ato",
        "tipo_ato",
        "area_pecentual",
        "transferido_em",
        "colaborador",
        "conjuge",
        "livro",
        "ficha",
        "data_aquisicaoestrangeiro",
        "data_lavratura",
        "area_pecentual1",
        "data_casamento",
        "tipo_casamento",
    )
    list_filter = (
        "criado_em",
        "modificado_em",
        "transferido_em",
        "data_aquisicaoestrangeiro",
        "data_lavratura",
        "data_casamento",
    )
    raw_id_fields = (
        "criado_por",
        "modificado_por",
        "imovel",
        "pessoa",
        "tipo_regime_casamento",
        "tipo_vinculo",
        "estado_civil",
    )


@admin.register(PedidoParteAto)
class PedidoParteAtoAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "pedido_item",
        "pessoa",
        "vinculo",
        "estado_civil",
        "tipo_regime_casamento",
        "pessoa_conjuge",
        "percentual_ato",
        "percentual_doi",
        "percentual_incra",
        "tipo_parte",
    )
    list_filter = (
        "pedido_item",
        "pessoa",
        "vinculo",
        "estado_civil",
        "tipo_regime_casamento",
        "pessoa_conjuge",
    )


@admin.register(PerguntaAcao)
class PerguntaAcaoAdmin(admin.ModelAdmin):
    list_display = ("id", "descricao")


@admin.register(PerguntaSetor)
class PerguntaSetorAdmin(admin.ModelAdmin):
    list_display = ("id", "descricao")


@admin.register(Pergunta)
class PerguntaAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "questions",
        "option1",
        "option2",
        "option3",
        "option4",
        "option5",
        "corrans",
        "acoes",
        "categoria",
        "setores",
        "observacao",
        "previsao_legal",
        "texto",
        "resposta_auxiliar",
        "pergunta_ativa",
        "ordem",
    )


@admin.register(PerguntaGrupo)
class PerguntaGrupoAdmin(admin.ModelAdmin):
    list_display = ("ato", "get_perguntas")
    filter_horizontal = ("perguntas",)


@admin.register(PerguntaMinuta)
class PerguntaMinutaAdmin(admin.ModelAdmin):
    list_display = ("id", "questions", "option1", "corrans")


@admin.register(CheckListRealizado)
class CheckListRealizadoAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "categoria",
        "item",
        "perguntas",
        "pessoa",
        "usuario",
        "pedido_item",
        "created_at",
        "updated_at",
        "resposta",
        "resposta_correta",
        "tabela_origem_id",
        "nome_tabela_origem",
        "coluna_tabela_origem",
        "ordem",
    )
    list_filter = (
        "perguntas",
        "pessoa",
        "usuario",
        "pedido_item",
        "created_at",
        "updated_at",
    )
    date_hierarchy = "created_at"


@admin.register(TipoRegistroAuxiliar)
class TipoRegistroAuxiliarAdmin(admin.ModelAdmin):
    list_display = ("id", "nome", "descricao")


@admin.register(Livro03)
class Livro03Admin(admin.ModelAdmin):
    list_display = (
        "id",
        "tipo_registro_auxiliar",
        "numero",
        "cartorio",
        "data_abertura",
        "cancelado_em",
        "data_vencimento",
        "numero_cedula",
        "descricao",
        "cnm",
        "ultimo_livro",
        "ultimo_folha",
        "observacao",
        "texto",
        "data_envio_cnm",
        "enviar_cnm",
        "arquivo",
    )
    list_filter = (
        "data_abertura",
        "cancelado_em",
        "data_vencimento",
        "data_envio_cnm",
        "enviar_cnm",
    )
    raw_id_fields = ("tipo_registro_auxiliar",)


@admin.register(RegistroVinculado)
class RegistroVinculadoAdmin(admin.ModelAdmin):
    list_display = ("id", "descricao")


@admin.register(Livro03Garantia)
class Livro03GarantiaAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "registro_auxiliar",
        "imovel_vinculado",
        "especie",
        "numero",
        "descricao",
        "quantidade",
        "grau_penhor",
        "tipo_registro",
        "numero_registro",
        "valor",
        "fazenda",
        "tipo_ato",
        "area",
    )
    raw_id_fields = ("registro_auxiliar", "imovel_vinculado")


@admin.register(Livro03Descricao)
class Livro03DescricaoAdmin(admin.ModelAdmin):
    list_display = ("id", "tipo_figura", "tipo_descricao")


@admin.register(Livro03Ligacao)
class Livro03LigacaoAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "estado_civil",
        "pessoa",
        "registro_auxiliar",
        "figuras",
        "situacao",
        "transferido_em",
        "numero_ato",
        "tipo_ato",
        "observacao",
        "regime",
    )
    list_filter = ("transferido_em",)
    raw_id_fields = (
        "estado_civil",
        "pessoa",
        "registro_auxiliar",
        "figuras",
    )


@admin.register(MinutaAuxiliar)
class MinutaAuxiliarAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "tipo_livro",
        "nome_minuta_principal",
        "nome_minuta_auxiliar_01",
        "nome_minuta_auxiliar_02",
        "nome_minuta_auxiliar_03",
        "nome_minuta_auxiliar_04",
        "nome_minuta_auxiliar_05",
        "nome_minuta_auxiliar_06",
        "nome_minuta_auxiliar_07",
        "nome_minuta_auxiliar_08",
        "nome_minuta_auxiliar_09",
        "nome_minuta_auxiliar_10",
    )


@admin.register(FichaAuxiliar)
class FichaAuxiliarAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "unidade",
        "nome",
        "nome_incorporadora",
        "data_incorporacao",
        "numero_edificacao",
        "tipo",
        "construido",
    )
    list_filter = ("data_incorporacao",)
    raw_id_fields = ("unidade",)


@admin.register(PessoaEndereco)
class PessoaEnderecoAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "vinculo",
        "ligacoes",
        "nacionalidade",
        "profissao",
    )
    list_filter = ("vinculo", "ligacoes")


@admin.register(ColaboradorSetor)
class ColaboradorSetorAdmin(admin.ModelAdmin):
    list_display = ("id", "servico")


@admin.register(GrupoUsuario)
class GrupoUsuarioAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "member_user")
    list_filter = ("user",)


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "is_active",
        "is_deleted",
        "created_at",
        "updated_at",
        "user",
        "auth_user",
        "numero",
        "title",
        "description",
        "start_time",
        "end_time",
        "origem",
        "url",
        "start_time_checked",
        "end_time_checked",
        "member_checked_user",
        "exibir_agenda_protocolo",
        "fase_agenda",
    )
    list_filter = (
        "is_active",
        "is_deleted",
        "created_at",
        "updated_at",
        "start_time",
        "end_time",
        "start_time_checked",
        "end_time_checked",
    )
    raw_id_fields = ("user", "auth_user", "fase_agenda")
    date_hierarchy = "created_at"


@admin.register(EventMember)
class EventMemberAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "is_active",
        "is_deleted",
        "created_at",
        "updated_at",
        "event",
        "user",
    )
    list_filter = ("is_active", "is_deleted", "created_at", "updated_at")
    raw_id_fields = ("event", "user")
    date_hierarchy = "created_at"


@admin.register(PedidoItemImovel)
class PedidoItemImovelAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "setor",
        "lote",
        "area",
        "residencial",
        "comercial",
        "nome_rua",
        "numero_casa",
        "municipio",
        "nome_fazenda",
        "caracteristica_fazenda",
        "remanescente",
        "reserva_legal",
        "georefenciada",
        "numero_nirf",
        "numero_ccirr",
        "numero_car",
        "numero_incra",
        "quadra",
        "area_fazenda",
        "opcao_imovel",
        "pedido_item",
        "data_validade_itr",
        "m_frente_metros",
        "p_frente_metros",
        "m_direito_metros",
        "p_direito_metros",
        "m_esquerdo_metros",
        "p_esquerdo_metros",
        "p_fundo_metros",
        "m_fundo_metros",
        "area_construida_residencial",
    )
    list_filter = ("pedido_item",)


@admin.register(Cidade)
class CidadeAdmin(admin.ModelAdmin):
    list_display = ("id", "nome")


@admin.register(TipoRegistroProtocolo)
class TipoRegistroProtocoloAdmin(admin.ModelAdmin):
    list_display = ("id", "descricao", "ordem")


@admin.register(ChecklistRealizadoHistorico)
class ChecklistRealizadoHistoricoAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "categoria",
        "perguntas",
        "pessoa",
        "colaborador",
        "conferido_usuario",
        "pedido_item",
        "pedidos",
        "created_at",
        "updated_at",
        "resposta",
        "resposta_correta",
        "ordem",
    )
    list_filter = (
        "perguntas",
        "pessoa",
        "conferido_usuario",
        "pedido_item",
        "pedidos",
        "created_at",
        "updated_at",
    )
    date_hierarchy = "created_at"


@admin.register(ChecklistBalcao)
class ChecklistBalcaoAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "text",
        "atos",
        "ordem",
        "tipo_pergunta",
        "tipo_do_imovel",
        "titulo_informacao",
    )


@admin.register(ChecklistBalcaoAto)
class ChecklistBalcaoAtoAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "checklist_balcao",
        "texto_escolha",
        "atos",
        "ordem",
        "observacao",
        "created_at",
        "updated_at",
        "impeditivo",
    )
    list_filter = ("created_at", "updated_at", "impeditivo")
    raw_id_fields = ("checklist_balcao", "atos")
    date_hierarchy = "created_at"


@admin.register(ChecklistBalcaoAtoTexto)
class ChecklistBalcaoAtoTextoAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "checklist_balcao_ato",
        "texto_escolha",
        "grupo",
        "observacao",
        "created_at",
        "updated_at",
        "impeditivo",
    )
    list_filter = ("created_at", "updated_at", "impeditivo")
    date_hierarchy = "created_at"


@admin.register(ChecklistBalcaoEscolha)
class ChecklistBalcaoEscolhaAdmin(admin.ModelAdmin):
    list_display = ("id", "pergunta_ato", "texto_escolha", "checked")
    list_filter = ("pergunta_ato", "checked")


@admin.register(OrdemDigitalizarBalcao)
class OrdemDigitalizarBalcaoAdmin(admin.ModelAdmin):
    list_display = ("id", "text")


@admin.register(OrdemDigitalizarBalcaoAto)
class OrdemDigitalizarBalcaoAtoAdmin(admin.ModelAdmin):
    list_display = ("id", "pergunta", "atos", "ordem")


@admin.register(OrdemDigitalizarEscolha)
class OrdemDigitalizarEscolhaAdmin(admin.ModelAdmin):
    list_display = ("id", "pergunta_ato", "texto_escolha", "checked")
    list_filter = ("pergunta_ato", "checked")


@admin.register(ImovelClasse)
class ImovelClasseAdmin(admin.ModelAdmin):
    list_display = ("id", "tipo", "descricao")


@admin.register(CertificadoDigital)
class CertificadoDigitalAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "certificado",
        "_senha",
        "imagem_assinatura",
        "texto_assinatura",
    )
    raw_id_fields = ("usuarios",)


@admin.register(MotivoAssinaturaDigital)
class MotivoAssinaturaDigitalAdmin(admin.ModelAdmin):
    list_display = ("id", "descricao")


@admin.register(TipoDocumentoAssinatura)
class TipoDocumentoAssinaturaAdmin(admin.ModelAdmin):
    list_display = ("id", "descricao")


@admin.register(LogAssinaturaDigital)
class LogAssinaturaDigitalAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "data_assinatura",
        "documento",
        "certificado",
        "motivo",
        "usuario",
    )
    list_filter = ("data_assinatura",)


@admin.register(Documento)
class DocumentoAdmin(admin.ModelAdmin):
    list_display = ("id", "criado_em", "titulo", "arquivo", "assinatura")
    list_filter = ("criado_em",)


@admin.register(GrupoDistribuicaoProtocolo)
class GrupoDistribuicaoProtocoloAdmin(admin.ModelAdmin):
    list_display = ("id", "colaborador", "titulo")


@admin.register(GrupoTipoAndamento)
class GrupoTipoAndamentoAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "tipo_andamento_principal",
        "tipo_andamento_auxiliar",
        "ordem",
    )
    list_filter = ("tipo_andamento_principal", "tipo_andamento_auxiliar")


@admin.register(Backup)
class BackupAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "arquivo",
        "criado_em",
        "tamanho_arquivo",
        "hash_verificacao",
    )
    list_filter = ("criado_em",)


@admin.register(TipoModelo)
class TipoModeloAdmin(admin.ModelAdmin):
    list_display = ("id", "descricao", "grupo_gerar_tipo_certidao")
    list_filter = ("grupo_gerar_tipo_certidao",)


@admin.register(ModeloTexto)
class ModeloTextoAdmin(admin.ModelAdmin):
    list_display = ("id", "titulo", "conteudo", "tipo", "ativo")
    list_filter = ("tipo", "ativo")


@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "is_private", "creator", "created_at")
    list_filter = ("is_private", "creator", "created_at")
    raw_id_fields = ("participants",)
    search_fields = ("name",)
    date_hierarchy = "created_at"


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("id", "room", "author", "content", "timestamp")
    list_filter = ("room", "author", "timestamp")


@admin.register(Caixa)
class CaixaAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "usuario",
        "saldo_inicial",
        "saldo_atual",
        "data_abertura",
        "data_fechamento",
    )
    list_filter = ("usuario", "data_abertura", "data_fechamento")


@admin.register(Transacao)
class TransacaoAdmin(admin.ModelAdmin):
    list_display = ("id", "caixa", "valor", "descricao", "data", "tipo")
    list_filter = ("caixa", "data")


@admin.register(CertidaoEmitida)
class CertidaoEmitidaAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "matricula",
        "usuario_emissor",
        "data_emissao",
        "protocolo_origem",
    )
    list_filter = ("data_emissao",)


@admin.register(Finalidade)
class FinalidadeAdmin(admin.ModelAdmin):
    list_display = ("id", "nome", "ativo")
    list_filter = ("ativo",)


@admin.register(PedidoCertidao)
class PedidoCertidaoAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "criado_por",
        "modificado_por",
        "criado_em",
        "modificado_em",
        "data_entrada_onr",
        "valor_total_onr",
        "numero_pedido",
        "data_entrada",
        "data_pedido_onr",
        "observacao",
        "tipo_de_servico",
        "protocolo_onr",
        "finalidade",
        "origem",
        "numero_pedido_firebird",
        "cancelado_em",
        "data_selado",
        "senha_site",
    )
    list_filter = (
        "criado_em",
        "modificado_em",
        "data_entrada_onr",
        "data_entrada",
        "data_pedido_onr",
        "cancelado_em",
        "data_selado",
    )


@admin.register(TipoApresentante)
class TipoApresentanteAdmin(admin.ModelAdmin):
    list_display = ("id", "nome")


@admin.register(Apresentante)
class ApresentanteAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "tipo_logradouro",
        "logradouro",
        "numero",
        "quadra",
        "lote",
        "complemento",
        "bairro",
        "municipio",
        "cep",
        "tipo_documento",
        "data_emissao",
        "orgao_emissor",
        "pedido",
        "nome",
        "telefone",
        "telefone_2",
        "observacao",
        "email",
        "tipo_apresentante",
        "documento",
        "dados_bancarios",
        "interessado_nome",
        "interessado_tipo_documento",
        "interessado_documento",
        "interessado_telefone",
        "interessado_email",
        "interessado_tipo",
        "pagador_tipo",
        "pagador_nome",
        "criado_por",
    )
    list_filter = ("data_emissao",)


@admin.register(PedidoCertidaoPessoa)
class PedidoCertidaoPessoaAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "nome",
        "rg",
        "tipo_documento",
        "documento",
        "nacionalidade",
        "profissao",
        "complemento",
        "estado_civil",
        "anotacoes",
        "pedido",
        "endereco",
    )
    list_filter = ("tipo_documento", "estado_civil", "pedido")


@admin.register(PedidoCertidaoImovel)
class PedidoCertidaoImovelAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "tipo_logradouro",
        "logradouro",
        "numero",
        "quadra",
        "lote",
        "complemento",
        "bairro",
        "municipio",
        "cep",
        "pedido",
        "numero_registro",
        "tipo_registro",
        "cartorio",
        "livro",
        "descricao",
        "tipo_imovel",
        "anotacoes",
    )


@admin.register(TipoItemCertidao)
class TipoItemCertidaoAdmin(admin.ModelAdmin):
    list_display = ("id", "nome", "explicacao")


@admin.register(TipoCertidao)
class TipoCertidaoAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "nome",
        "codigo",
        "prazo_legal",
        "tipo_item",
        "codigo_onr",
        "ativo",
        "certidao_id_sistema_antigo",
        "certidao_id_sistema_antigo_isento",
        "certidao_id_sistema_antigo_50",
    )
    list_filter = ("ativo",)


@admin.register(ValorCertidao)
class ValorCertidaoAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "tipo_certidao",
        "data_inicio_validade",
        "data_fim_validade",
        "valor",
        "taxa_fiscal_judiciaria",
        "fundo_estado",
        "issqn_percentual",
    )
    list_filter = (
        "tipo_certidao",
        "data_inicio_validade",
        "data_fim_validade",
    )


@admin.register(Certidao)
class CertidaoAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "criado_por",
        "modificado_por",
        "criado_em",
        "modificado_em",
        "tipo_certidao",
        "pessoa",
        "imovel",
        "data_emissao",
        "tipo_tributacao",
        "pessoa_cancelado",
        "imovel_cancelado",
    )
    list_filter = ("criado_em", "modificado_em", "data_emissao")


@admin.register(TipoAndamentoCertidao)
class TipoAndamentoCertidaoAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "criado_por",
        "modificado_por",
        "criado_em",
        "modificado_em",
        "descricao",
        "codigo",
        "grupo_cancelado",
        "grupo_devolucao",
        "grupo_fase_cartorio",
        "grupo_pedido_confirmado",
        "grupo_reciboimpresso",
        "grupo_selo",
        "grupo_recepcao",
        "grupo_gerar_andamento_agenda",
        "grupo_gerar_certidao",
        "grupo_certidao_pronta",
        "grupo_certidao_entregue",
        "grupo_certidao_exigencia",
        "exibir_botao_opcoes",
    )
    list_filter = (
        "criado_por",
        "modificado_por",
        "criado_em",
        "modificado_em",
        "grupo_cancelado",
        "grupo_devolucao",
        "grupo_fase_cartorio",
        "grupo_pedido_confirmado",
        "grupo_reciboimpresso",
        "grupo_selo",
        "grupo_recepcao",
        "grupo_gerar_andamento_agenda",
        "grupo_gerar_certidao",
        "grupo_certidao_pronta",
        "grupo_certidao_entregue",
        "grupo_certidao_exigencia",
        "exibir_botao_opcoes",
    )


@admin.register(PedidoCertidaoAndamento)
class PedidoCertidaoAndamentoAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "modificado_por",
        "criado_em",
        "modificado_em",
        "tipo_andamento",
        "pedido",
        "data_hora",
        "descricao",
        "criado_por",
        "colaborador_destino",
        "certidao",
    )
    list_filter = ("criado_em", "modificado_em", "data_hora")


@admin.register(TipoArmazenamento)
class TipoArmazenamentoAdmin(admin.ModelAdmin):
    list_display = ("id", "nome")


@admin.register(Issqn)
class IssqnAdmin(admin.ModelAdmin):
    list_display = ("id", "data_inicio", "percentual")
    list_filter = ("data_inicio",)


@admin.register(GrupoUsuarioAgendaCertidao)
class GrupoUsuarioAgendaCertidaoAdmin(admin.ModelAdmin):
    list_display = ("id", "colaborador", "tipo_andamento")
    list_filter = ("colaborador", "tipo_andamento")
