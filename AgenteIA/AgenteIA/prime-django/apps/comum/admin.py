import logging

from django.contrib import admin

from apps.comum.models import (
    DadosBancarios,
    Expediente,
    Feriado,
    Fundo,
    Instrucao,
    Issqn,
    Municipio,
    Pais,
    Papel,
    PrazoLegal,
    TaxaEstadual,
    TipoCartorio,
    TipoCertidaoComum,
    TipoDocumento,
    TipoLogradouro,
    TipoOrigem,
    TipoPapelParte,
    TipoRegistro,
    TipoRegistroImobiliario,
    TipoTributacao,
    UnidadeFederativa,
    UnidadePrazo,
)

logger = logging.getLogger(__name__)
logger.debug(f"Iniciando {__name__}")


@admin.register(TipoCartorio)
class TipoCartorioAdmin(admin.ModelAdmin):
    list_display = ("id", "nome")


@admin.register(Pais)
class PaisAdmin(admin.ModelAdmin):
    list_display = ("id", "nome", "sigla")


@admin.register(UnidadeFederativa)
class UnidadeFederativaAdmin(admin.ModelAdmin):
    list_display = ("id", "sigla", "nome", "pais")
    list_filter = ("pais",)


# @admin.register(EstadoCivil)
# class EstadoCivilAdmin(admin.ModelAdmin):
#     list_display = ("id", "nome")


@admin.register(Municipio)
class MunicipioAdmin(admin.ModelAdmin):
    list_display = ("id", "nome", "uf", "codigo_ibge")
    list_filter = ("uf",)


@admin.register(TaxaEstadual)
class TaxaEstadualAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "estado",
        "atividade",
        "taxa_percentual",
        "data_inicio_validade",
        "data_fim_validade",
    )
    list_filter = ("estado", "data_inicio_validade", "data_fim_validade")


@admin.register(Issqn)
class IssqnAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "municipio",
        "atividade",
        "taxa_percentual",
        "data_inicio_validade",
        "data_fim_validade",
    )
    list_filter = ("municipio", "data_inicio_validade", "data_fim_validade")


@admin.register(TipoRegistro)
class TipoRegistroAdmin(admin.ModelAdmin):
    list_display = ("id", "nome")


@admin.register(TipoRegistroImobiliario)
class TipoRegistroImobiliarioAdmin(admin.ModelAdmin):
    list_display = ("id", "nome")


@admin.register(Instrucao)
class InstrucaoAdmin(admin.ModelAdmin):
    list_display = ("id", "card_id", "texto")


@admin.register(Feriado)
class FeriadoAdmin(admin.ModelAdmin):
    list_display = ("id", "nome", "data", "tipo", "estado", "municipio")
    list_filter = ("data", "estado", "municipio")


@admin.register(DadosBancarios)
class DadosBancariosAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "titular",
        "nome_banco",
        "numero_agencia",
        "numero_conta",
        "tipo_conta",
    )


@admin.register(TipoDocumento)
class TipoDocumentoAdmin(admin.ModelAdmin):
    list_display = ("id", "sigla", "nome")


@admin.register(TipoTributacao)
class TipoTributacaoAdmin(admin.ModelAdmin):
    list_display = ("id", "nome", "descricao", "percentual_desconto")


@admin.register(Fundo)
class FundoAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "nome",
        "descricao",
        "valor",
        "tipo",
        "estado",
        "data_inicio_validade",
        "data_fim_validade",
    )
    list_filter = ("estado", "data_inicio_validade", "data_fim_validade")


@admin.register(UnidadePrazo)
class UnidadePrazoAdmin(admin.ModelAdmin):
    list_display = ("id", "nome", "em_horas", "horas_uteis_por_dia")


@admin.register(Expediente)
class ExpedienteAdmin(admin.ModelAdmin):
    list_display = ("id", "dia_da_semana", "inicio", "fim")


@admin.register(PrazoLegal)
class PrazoLegalAdmin(admin.ModelAdmin):
    list_display = ("id", "valor", "unidade", "eh_prazo_util")
    list_filter = ("unidade", "eh_prazo_util")


@admin.register(TipoPapelParte)
class TipoPapelParteAdmin(admin.ModelAdmin):
    list_display = ("id", "nome", "descricao")


@admin.register(TipoOrigem)
class TipoOrigemAdmin(admin.ModelAdmin):
    list_display = ("id", "nome")


@admin.register(TipoLogradouro)
class TipoLogradouroAdmin(admin.ModelAdmin):
    list_display = ("id", "codigo", "nome")


@admin.register(TipoCertidaoComum)
class TipoCertidaoComumAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "nome",
        "descricao",
        "codigo",
        "prazo_legal",
        "tipo_cartorio",
    )
    list_filter = ("prazo_legal", "tipo_cartorio")


@admin.register(Papel)
class PapelAdmin(admin.ModelAdmin):
    list_display = ("id", "nome", "descricao", "codigo")
