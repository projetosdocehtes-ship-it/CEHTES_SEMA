import logging

from django.contrib import admin

from apps.pedidos.models import (
    Anexo,
    Apresentante,
    Ato,
    AtoPraticavel,
    Configuracao,
    DocumentoParaRequerimento,
    Emolumento,
    Evento,
    Fundo,
    Imovel,
    OrgaoEmissor,
    Parte,
    Participacao,
    Pedido,
    Requerimento,
    Tabela,
    TipoArmazenamento,
    TipoEmolumento,
    TipoEvento,
    TipoTitulo,
    Titulo,
)

logger = logging.getLogger(__name__)

logger.debug(f"Iniciando {__name__}")


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = (
        "criado_por",
        "modificado_por",
        "modificado_em",
        "id",
        "numero_pedido",
        "data_entrada",
        "interessado_nome",
        "interessado_documento",
        "apresentante",
        "observacao",
        "tipo_de_servico",
        "numero_onr",
        "numero_protocolo_firebird",
        "numero_selo_firebird",
        "codigo_seguranca_firebird",
        "codigo_internet_firebird",
        "criado_em",
        "data_modificacao",
    )
    list_filter = (
        "modificado_em",
        "data_entrada",
        "criado_em",
        "data_modificacao",
    )
    raw_id_fields = ("criado_por", "modificado_por", "apresentante")


@admin.register(Apresentante)
class ApresentanteAdmin(admin.ModelAdmin):
    list_display = (
        "tipo_documento",
        "documento",
        "data_emissao",
        #"orgao_emissor",
        "id_sequencial",
        "id",
        "nome",
        "telefone",
        "telefone_2",
        "observacao",
        "email",
        "dados_bancarios",
        "criado_em",
    )
    list_filter = ("data_emissao", "criado_em")
    raw_id_fields = ("tipo_documento", "dados_bancarios")


@admin.register(Imovel)
class ImovelAdmin(admin.ModelAdmin):
    list_display = (
        "tipo_logradouro",
        "logradouro",
        "numero",
        "quadra",
        "lote",
        "complemento",
        "bairro",
        "municipio",
        "cep",
        "id_sequencial",
        "id",
        "numero_registro",
        "tipo_registro",
        "atos",
        "cartorio",
        "livro",
        "descricao",
        "tipo_imovel",
        "anotacoes",
    )
    list_filter = (
        "tipo_logradouro",
        "municipio",
        "tipo_registro",
        "atos",
        "tipo_imovel",
    )


@admin.register(Parte)
class ParteAdmin(admin.ModelAdmin):
    list_display = (
        "tipo_documento",
        "documento",
        "data_emissao",
        "orgao_emissor",
        "id_sequencial",
        "id",
        "nome",
        "estado_civil",
        "anotacoes",
        "conjuge",
        "criado_em",
    )
    list_filter = (
        "tipo_documento",
        "data_emissao",
        "estado_civil",
        "conjuge",
        "criado_em",
    )


@admin.register(TipoTitulo)
class TipoTituloAdmin(admin.ModelAdmin):
    list_display = ("id", "nome", "descricao", "home_titulo_protocolo")


@admin.register(TipoEvento)
class TipoEventoAdmin(admin.ModelAdmin):
    list_display = ("id_sequencial", "id", "nome")


@admin.register(Evento)
class EventoAdmin(admin.ModelAdmin):
    list_display = ("id_sequencial", "id", "nome", "tipo_evento", "pedido")
    list_filter = ("tipo_evento", "pedido")


@admin.register(TipoArmazenamento)
class TipoArmazenamentoAdmin(admin.ModelAdmin):
    list_display = ("id_sequencial", "id", "nome")


@admin.register(Anexo)
class AnexoAdmin(admin.ModelAdmin):
    list_display = (
        "id_sequencial",
        "id",
        "nome_arquivo",
        "endereco_arquivo",
        "tipo_armazenamento",
        "pedido",
    )
    list_filter = ("tipo_armazenamento", "pedido")


@admin.register(Configuracao)
class ConfiguracaoAdmin(admin.ModelAdmin):
    list_display = ("id_sequencial", "id", "nome", "valor")


@admin.register(TipoEmolumento)
class TipoEmolumentoAdmin(admin.ModelAdmin):
    list_display = ("nome", "codigo", "ativo")
    list_filter = (
        "ativo",
        "home_emolumento",
        "home_emolumento_isento",
        "home_emolumento_50",
        "home_emolumento_75",
    )
    search_fields = ("nome", "codigo", "descricao")
    ordering = ("nome",)
    readonly_fields = ("id", "mapeamento_antigo")
    fieldsets = (
        (None, {"fields": ("id", "nome", "codigo", "descricao", "ativo")}),
        (
            "Emolumentos no Firebird",
            {
                "fields": (
                    "home_emolumento",
                    "home_emolumento_isento",
                    "home_emolumento_50",
                    "home_emolumento_75",
                ),
            },
        ),
        (
            "Informações Adicionais",
            {
                "fields": ("mapeamento_antigo",),
                "classes": ("collapse",),
            },
        ),
    )
    search_help_text = "Digite o nome, código ou descrição para buscar."

    def get_readonly_fields(self, request, obj=None):
        """Define campos que devem ser apenas de leitura."""
        if not obj:  # Quando criando um novo objeto
            return self.readonly_fields
        return (*self.readonly_fields, "nome", "codigo")

    def save_model(self, request, obj, form, change):
        """Sobrescreve o método save_model para aplicar lógica adicional no salvamento do objeto."""
        if "nome" in form.changed_data:
            obj.codigo = (
                obj.codigo.upper()
            )  # Exemplo de manipulação antes do salvamento
        super().save_model(request, obj, form, change)


@admin.register(AtoPraticavel)
class NaturezaAtoAdmin(admin.ModelAdmin):
    list_display = ("id", "nome", "prazo_legal", "descricao", "home_atos")
    raw_id_fields = ("prazo_legal", "home_atos")


@admin.register(Tabela)
class TabelaAdmin(admin.ModelAdmin):
    list_display = ("id", "data_inicio_validade", "data_fim_validade")
    list_filter = ("data_inicio_validade", "data_fim_validade")


@admin.register(Fundo)
class FundoAdmin(admin.ModelAdmin):
    list_display = ("id", "descricao", "tipo_valor", "valor")


@admin.register(Emolumento)
class EmolumentoAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "tabela",
        "tipo_emolumento",
        "valor",
        "faixa_valor_inicio",
        "faixa_valor_fim",
        "taxa_fiscal_judiciaria",
        "fundo1_valor",
        "fundo1_descricao",
        "fundo1_tipo_valor",
        "fundo2_nome",
        "fundo2_valor",
        "fundo2_tipo_valor",
        "issqn_percentual",
        "codigo",
    )
    list_filter = ("tabela", "tipo_emolumento")


@admin.register(Titulo)
class TituloAdmin(admin.ModelAdmin):
    list_display = ("id", "pedido", "tipo_titulo", "numero", "data", "valor")
    list_filter = ("pedido", "tipo_titulo", "data")


@admin.register(Ato)
class AtoAdmin(admin.ModelAdmin):
    list_display = (
        "id_sequencial",
        "id",
        "pedido",
        "tipo_titulo",
        "ato_praticavel",
        "tipo_emolumento",
        "imovel_numero_registro",
        "imovel_tipo_registro",
        "imovel_cartorio",
        "data",
        "criado_em",
        "tipo_tributacao",
        "valor_titulo",
        "valor_avaliacao",
        "ato",
        "tipo_ato",
        "numero_ato",
        "quantidade",
    )
    list_filter = ("data", "criado_em")
    raw_id_fields = (
        "pedido",
        "tipo_titulo",
        "ato_praticavel",
        "tipo_emolumento",
        "imovel_tipo_registro",
        "tipo_tributacao",
        "ato",
    )


@admin.register(Participacao)
class ParticipacaoAdmin(admin.ModelAdmin):
    list_display = ("id", "ato", "parte", "papel", "percentual_participacao")
    list_filter = ("ato", "parte", "papel")


@admin.register(OrgaoEmissor)
class OrgaoEmissorAdmin(admin.ModelAdmin):
    list_display = ("id", "nome", "sigla", "observacao")


@admin.register(Requerimento)
class RequerimentoAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "criado_por",
        "modificado_por",
        "criado_em",
        "modificado_em",
        "ato_praticavel",
        "observacao",
        "obrigatorio",
        "ativo",
    )
    list_filter = (
        "criado_por",
        "modificado_por",
        "criado_em",
        "modificado_em",
        "ato_praticavel",
        "obrigatorio",
        "ativo",
    )


@admin.register(DocumentoParaRequerimento)
class DocumentoParaRequerimentoAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "nome",
        "requerimento",
        "observacao",
        "prazo_de_validade",
        "orgao_emissor",
        "obrigatorio",
        "justificativa",
        "ativo",
        "imagem",
    )
    list_filter = ("requerimento", "orgao_emissor", "obrigatorio", "ativo")
