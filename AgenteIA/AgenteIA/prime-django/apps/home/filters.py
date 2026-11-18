import locale
import logging
import re
from datetime import datetime, time

import django_filters
from django import forms
from django.db import models
from django.utils import timezone
from django.utils.timezone import make_aware
from django_filters import BooleanFilter, CharFilter, Filter, FilterSet, NumberFilter

from apps.cartorios.models import Usuario as User
from apps.comum.models import Municipio
from apps.home.models.models_certidoes import (
    PedidoCertidao,
    PedidoCertidaoAnexo,
    TipoOrigem,
)
from apps.home.models.models_home import (
    AtoPratica,
    Colaborador,
    Event,
    Financeiro,
    Livro01Andamento,
    Livro01Protocolo,
    Livro02,
    Livro03,
    Livro04,
    Livro05,
    PedidoItem,
    SeloEletronico,
    StatusProtocolo,
    TipoAndamento,
    TipoCategoriaFinanceira,
    TipoOperacaoFinanceira,
    TipoRegistroAuxiliar,
    TipoTransacaoFinanceira,
)
from apps.home.tipos import TipoClasseRegistro, TipoRegistro
from core.utils.formatacoes import somente_numeros

logger = logging.getLogger(__name__)
logger.debug(f"Iniciando {__name__}")

locale.setlocale(locale.LC_ALL, "pt_BR.UTF-8")


def get_municipio_queryset():
    return Municipio.objects.all().order_by("nome")


def get_tipo_registro_auxiliar_queryset():
    return TipoRegistroAuxiliar.objects.all().order_by("nome")


def get_colaborador_queryset():
    return Colaborador.objects.filtrar_por_ativos()


def get_tipo_andamento_queryset():
    return TipoAndamento.objects.filtrar_por_ativos()


def get_status_protocolo_queryset():
    return StatusProtocolo.objects.all().order_by("descricao")


def get_origem_evento_queryset():
    return (
        ("P", "Protocolo"),
        ("E", "Exame Cálculo"),
        ("C", "Pedido Certidão"),
        ("G", "Geral"),
    )


def get_colaborador_ativo_queryset():
    return Colaborador.objects.filtrar_por_ativos()


def get_user_ativo_queryset():
    return User.get_ativos()


def get_tipo_andamento_ativo_queryset():
    return TipoAndamento.objects.filtrar_por_ativos()


def get_atos_queryset():
    return AtoPratica.objects.get_nome_atos_doi()


def get_tipo_operacao_financeira_queryset():
    return TipoOperacaoFinanceira.objects.all().order_by("descricao")


def get_tipo_transacao_financeira_queryset():
    return TipoTransacaoFinanceira.objects.all().order_by("descricao")


def get_tipo_categoria_financeira_queryset():
    return TipoCategoriaFinanceira.objects.all().order_by("descricao")


def get_colaborador_filtrar_por_exibir_nome_caixa():
    return Colaborador.objects.filtrar_por_exibir_nome_caixa()


class CustomNumberFilter(Filter):
    def filter(self, qs, value):
        if value is not None:
            value = value.replace(",", ".")
        return super().filter(qs, value)


class CustomBooleanFilter(BooleanFilter):
    def filter(self, qs, value):
        if value is not None:
            value = "S" if value else "N"
        return super().filter(qs, value)


class MonetarioInput(forms.NumberInput):
    template_name = "widgets/monetario_input.html"

    def __init__(self, attrs=None):
        """Inicializa o widget com atributos padrão."""
        default_attrs = {"class": "form-control", "placeholder": "0.00"}
        if attrs:
            default_attrs.update(attrs)
        super().__init__(attrs=default_attrs)


class Livro02Filter(FilterSet):
    numero_inicio = django_filters.NumberFilter(
        field_name="numero",
        lookup_expr="gte",
        widget=forms.NumberInput(
            attrs={"class": "form-control", "placeholder": "Registro de"},
        ),
        label="Número do Registro De",
    )

    numero_fim = django_filters.NumberFilter(
        field_name="numero",
        lookup_expr="lte",
        widget=forms.NumberInput(
            attrs={"class": "form-control", "placeholder": "Registro até"},
        ),
        label="Número do Registro Até",
    )

    data_abertura_inicio = django_filters.DateFilter(
        field_name="data_abertura",
        lookup_expr="gte",
        label="Data Abertura",
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
    )

    data_abertura_fim = django_filters.DateFilter(
        field_name="data_abertura",
        lookup_expr="lte",
        label="Data Abertura",
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
    )

    municipio = django_filters.ModelChoiceFilter(
        queryset=None,
        label="Municipio",
        widget=forms.Select(
            attrs={"class": "form-control", "placeholder": "Municipio"},
        ),
    )

    classe = django_filters.ChoiceFilter(
        choices=TipoClasseRegistro.CHOICES,
        label="Classe",
        widget=forms.Select(attrs={"class": "form-control", "placeholder": "Classe"}),
    )

    cartorio = django_filters.CharFilter(
        label="Cartório",
        initial="1",
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Numero do Cartório"},
        ),
    )

    tipo = django_filters.ChoiceFilter(
        choices=TipoRegistro.CHOICES,
        label="Tipo de Registro",
        widget=forms.Select(attrs={"class": "form-control"}),
        initial="",  # Faz com que "Selecione um cartório" seja a opção selecionada inicialmente
    )

    class Meta:
        model = Livro02
        fields = [
            "numero_inicio",
            "numero_fim",
            "cartorio",
            "tipo",
            "data_abertura_inicio",
            "data_abertura_fim",
            "classe",
            "municipio",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.filters["municipio"].queryset = get_municipio_queryset()


class Livro03Filter(FilterSet):
    numero_inicio = django_filters.NumberFilter(
        field_name="numero",
        lookup_expr="gte",
        widget=forms.NumberInput(
            attrs={"class": "form-control", "placeholder": "Número Mínimo"},
        ),
        label="Número",
    )

    numero_fim = django_filters.NumberFilter(
        field_name="numero",
        lookup_expr="lte",
        widget=forms.NumberInput(
            attrs={"class": "form-control", "placeholder": "Número Máximo"},
        ),
        label="Número",
    )

    data_abertura_inicio = django_filters.DateFilter(
        field_name="data_abertura",
        lookup_expr="gte",
        label="Data Abertura",
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
    )

    data_abertura_fim = django_filters.DateFilter(
        field_name="data_abertura",
        lookup_expr="lte",
        label="Data Abertura",
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
    )

    cartorio = django_filters.CharFilter(
        label="Cartório",
        initial="1",
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Informe o Cartório"},
        ),
    )

    tipo_registro_auxiliar = django_filters.ModelChoiceFilter(
        queryset=None,
        label="Tipo de Registro",
        widget=forms.Select(
            attrs={"class": "form-control", "placeholder": "Tipo de Registro"},
        ),
    )

    data_vencimento_inicio = django_filters.DateFilter(
        field_name="data_vencimento",
        lookup_expr="gte",
        label="Data Vencimento",
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
    )

    data_vencimento_fim = django_filters.DateFilter(
        field_name="data_vencimento",
        lookup_expr="lte",
        label="Data Vencimento",
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
    )

    cancelado_em_inicio = django_filters.DateFilter(
        field_name="cancelado_em",
        lookup_expr="gte",
        label="Data Cancelamento",
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
    )

    cancelado_em_fim = django_filters.DateFilter(
        field_name="cancelado_em",
        lookup_expr="lte",
        label="Data Cancelamento",
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
    )

    class Meta:
        model = Livro03
        fields = [
            "numero_inicio",
            "numero_fim",
            "cartorio",
            "data_abertura_inicio",
            "data_abertura_fim",
            "tipo_registro_auxiliar",
            "data_vencimento_inicio",
            "data_vencimento_fim",
            "cancelado_em_inicio",
            "cancelado_em_fim",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.filters[
            "tipo_registro_auxiliar"
        ].queryset = get_tipo_registro_auxiliar_queryset()


class Livro01ProtocoloFilter(FilterSet):
    numero_protocolo = django_filters.NumberFilter(
        widget=forms.NumberInput(
            attrs={
                "class": "form-control",
                "autofocus": "autofocus",
                "placeholder": "Número do protocolo",
            },
        ),
        label="Número do Protocolo",
    )

    def filter_by_papel(self, name, value):
        return self.filter(
            pedido__partes__pessoa__nome__icontains=value,
            pedido__partes__papel="S",
        )

    nome = django_filters.CharFilter(
        method=filter_by_papel,
        label="Nome do Apresentante",
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Nome Apresentante"},
        ),
    )

    start_date = django_filters.DateFilter(
        field_name="data_protocolo",
        lookup_expr="gte",
        label="Data Entrada Inicial",
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
    )

    end_date = django_filters.DateFilter(
        field_name="data_protocolo",
        lookup_expr="lte",
        label="Data Entrada Final",
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
    )

    data_reentrada = django_filters.DateFilter(
        widget=forms.DateInput(
            attrs={
                "class": "form-control",
                "type": "date",
                "placeholder": "Data Reentrada",
            },
        ),
        label="Data Reentrada",
    )

    def filter_by_da_prevista(self, name, value):
        return self.filter(pedido__dataprevista=value)

    fases_protocolo_colaborador_atual = django_filters.ModelChoiceFilter(
        queryset=None,
        label="Colaborador",
        widget=forms.Select(
            attrs={"class": "form-control", "placeholder": "Colaborador"},
        ),
    )

    status = django_filters.ModelChoiceFilter(
        queryset=None,
        label="Status Protocolo",
        widget=forms.Select(
            attrs={"class": "form-control", "placeholder": "Status do Protocolo"},
        ),
    )

    pedido_observacao = django_filters.CharFilter(
        field_name="pedido__observacao",
        lookup_expr="icontains",
        label="Observações",
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Observações do Pedido"},
        ),
    )

    class Meta:
        model = Livro01Protocolo
        fields = [
            "numero_protocolo",
            "start_date",
            "end_date",
            "data_reentrada",
            "nome",
            "fases_protocolo_colaborador_atual",
            "status",
            "pedido_observacao",
        ]
        ordering = ["-numero_protocolo"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.filters[
            "fases_protocolo_colaborador_atual"
        ].queryset = get_colaborador_queryset()
        self.filters["status"].queryset = get_status_protocolo_queryset()


def filter_start_date(queryset, name, value):
    """Ajusta a hora inicial para 00:00:00."""
    if value:
        start_datetime = datetime.combine(value, datetime.min.time())
        return queryset.filter(**{name + "__gte": start_datetime})
    return queryset


def filter_end_date(queryset, name, value):
    """Ajusta a hora final para 23:59:59."""
    if value:
        end_datetime = datetime.combine(value, datetime.max.time())
        return queryset.filter(**{name + "__lte": end_datetime})
    return queryset


class Livro01AndamentoFilter(FilterSet):
    def filter_numero_protocolo(self, queryset, name, value):
        value = somente_numeros(value)
        return queryset.filter(protocolo__numero_protocolo__icontains=value)

    start_date = django_filters.DateFilter(
        field_name="data",
        lookup_expr="gte",
        label="Data Andamento Inicio",
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
    )
    end_date = django_filters.DateFilter(
        field_name="data",
        method=filter_end_date,
        label="Data Andamento Final",
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
    )
    colaborador = django_filters.ModelChoiceFilter(
        queryset=Colaborador.objects.none(),
        label="Colaborador",
        widget=forms.Select(
            attrs={"class": "form-control", "placeholder": "Colaborador"},
        ),
    )
    tipo_andamento = django_filters.ModelChoiceFilter(
        queryset=None,
        label="Andamento",
        widget=forms.Select(attrs={"class": "form-control", "placeholder": "Evento"}),
    )
    numero_protocolo = django_filters.CharFilter(
        method="filter_numero_protocolo",
        label="Número do Protocolo",
    )

    class Meta:
        model = Livro01Andamento
        fields = [
            "start_date",
            "end_date",
            "tipo_andamento",
            "colaborador",
            # "numero_protocolo",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.filters["colaborador"].queryset = get_colaborador_ativo_queryset()
        self.filters["tipo_andamento"].queryset = get_tipo_andamento_ativo_queryset()


class AndamentosExigenciasFilter(FilterSet):
    def filter_numero_protocolo(self, queryset, name, value):
        return queryset.filter(protocolo__numero_protocolo__icontains=value)

    start_date = django_filters.DateFilter(
        field_name="data",
        lookup_expr="gte",
        label="Data Inicial",
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
    )
    end_date = django_filters.DateFilter(
        field_name="data",
        method=filter_end_date,
        label="Data Final",
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
    )
    colaborador = django_filters.ModelChoiceFilter(
        queryset=Colaborador.objects.none(),
        label="Colaborador",
        widget=forms.Select(
            attrs={"class": "form-control", "placeholder": "Colaborador"},
        ),
    )
    numero_protocolo = django_filters.CharFilter(
        method="filter_numero_protocolo",
        label="Número do Protocolo",
    )

    class Meta:
        model = Livro01Andamento
        fields = [
            "start_date",
            "end_date",
            "colaborador",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.filters["colaborador"].queryset = get_colaborador_ativo_queryset()


class AndamentosRegistradosFilter(FilterSet):
    def filter_numero_protocolo(self, queryset, name, value):
        return queryset.filter(protocolo__numero_protocolo__icontains=value)

    start_date = django_filters.DateFilter(
        field_name="data",
        lookup_expr="gte",
        label="Data Inicial",
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
    )
    end_date = django_filters.DateFilter(
        field_name="data",
        method=filter_end_date,
        label="Data Final",
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
    )
    colaborador = django_filters.ModelChoiceFilter(
        queryset=Colaborador.objects.none(),
        label="Colaborador",
        widget=forms.Select(
            attrs={"class": "form-control", "placeholder": "Colaborador"},
        ),
    )
    numero_protocolo = django_filters.CharFilter(
        method="filter_numero_protocolo",
        label="Número do Protocolo",
    )

    class Meta:
        model = Livro01Andamento
        fields = [
            "start_date",
            "end_date",
            "colaborador",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.filters["colaborador"].queryset = get_colaborador_ativo_queryset()


class AndamentosPrenotadosFilter(FilterSet):
    def filter_numero_protocolo(self, queryset, name, value):
        return queryset.filter(protocolo__numero_protocolo__icontains=value)

    start_date = django_filters.DateFilter(
        field_name="data",
        lookup_expr="gte",
        label="Data Inicial",
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
    )
    end_date = django_filters.DateFilter(
        field_name="data",
        method=filter_end_date,
        label="Data Final",
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
    )
    colaborador = django_filters.ModelChoiceFilter(
        queryset=Colaborador.objects.none(),
        label="Colaborador",
        widget=forms.Select(
            attrs={"class": "form-control", "placeholder": "Colaborador"},
        ),
    )
    numero_protocolo = django_filters.CharFilter(
        method="filter_numero_protocolo",
        label="Número do Protocolo",
    )

    class Meta:
        model = Livro01Andamento
        fields = [
            "start_date",
            "end_date",
            "colaborador",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.filters["colaborador"].queryset = get_colaborador_ativo_queryset()


class DoiFilter(FilterSet):
    numero_registro = django_filters.NumberFilter(
        widget=forms.NumberInput(
            attrs={"class": "form-control", "placeholder": "Número do Imóvel"},
        ),
        label="Imóvel",
    )

    # start_date = django_filters.DateFilter(
    #     field_name="data_pagamento",
    #     lookup_expr="gte",
    #     label="Data Entrada Inicial",
    #     widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
    # )

    # end_date = django_filters.DateFilter(
    #     field_name="data_pagamento",
    #     lookup_expr="lte",
    #     label="Data Entrada Final",
    #     widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
    # )

    # def filter_by_da_prevista(queryset, name, value):
    #     return queryset.filter(pedido__dataprevista=value)

    ato_id = django_filters.ModelChoiceFilter(
        queryset=None,
        label="Tipo Alienação",
        widget=forms.Select(
            attrs={"class": "form-control", "placeholder": "Tipo Alienação"},
        ),
    )

    class Meta:
        model = PedidoItem
        fields = [
            "numero_registro",
            "ato_id",
            # "start_date",
            # "end_date",
            # "data_reentrada",
            # "nome",
            # "fases_protocolo_colaborador_atual",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.filters["ato_id"].queryset = get_atos_queryset()


class Livro04Filter(FilterSet):
    numero_inicio = django_filters.NumberFilter(
        field_name="numero",
        lookup_expr="gte",
        widget=forms.NumberInput(
            attrs={"class": "form-control", "placeholder": "Registro Inicial"},
        ),
        label="Número",
    )

    numero_fim = django_filters.NumberFilter(
        field_name="numero",
        lookup_expr="lte",
        widget=forms.NumberInput(
            attrs={"class": "form-control", "placeholder": "Registro Final"},
        ),
        label="Número",
    )

    data_abertura_inicio = django_filters.DateFilter(
        field_name="data_abertura",
        lookup_expr="gte",
        label="Data Abertura",
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
    )

    data_abertura_fim = django_filters.DateFilter(
        field_name="data_abertura",
        lookup_expr="lte",
        label="Data Abertura",
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
    )

    municipio = django_filters.ModelChoiceFilter(
        queryset=None,
        label="Municipio",
        widget=forms.Select(
            attrs={"class": "form-control", "placeholder": "Municipio"},
        ),
    )

    classe = django_filters.ChoiceFilter(
        choices=TipoClasseRegistro.CHOICES,
        label="Classe",
        widget=forms.Select(attrs={"class": "form-control", "placeholder": "Classe"}),
    )

    cartorio = django_filters.CharFilter(
        label="Cartório",
        initial="1",
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Numero RI"},
        ),
    )

    tipo = django_filters.ChoiceFilter(
        choices=TipoRegistro.CHOICES,
        label="Tipo de Registro",
        widget=forms.Select(attrs={"class": "form-control"}),
        initial="",
    )

    class Meta:
        model = Livro04
        fields = [
            "numero_inicio",
            "numero_fim",
            "cartorio",
            "tipo",
            "data_abertura_inicio",
            "data_abertura_fim",
            "classe",
            "municipio",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.filters["municipio"].queryset = get_municipio_queryset()


class FinanceiroFilter(FilterSet):
    """Filtro do Caixa por Colaborador."""

    data_transacao_inicio = django_filters.DateFilter(
        field_name="data_transacao",
        lookup_expr="gte",
        label="Data Início",
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
        method=filter_start_date,
    )

    data_transacao_fim = django_filters.DateFilter(
        field_name="data_transacao",
        lookup_expr="lte",
        label="Data Fim",
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
        method=filter_end_date,
    )

    descricao = CharFilter(lookup_expr="icontains")

    # valor_transacao = NumberFilter(
    #     widget=forms.NumberInput(
    #         attrs={"class": "form-control", "placeholder": "0,00"},
    #     ),
    # )

    valor_transacao = NumberFilter(widget=MonetarioInput())

    tipo_operacao_financeira_id = django_filters.ModelChoiceFilter(
        queryset=TipoOperacaoFinanceira.objects.none(),
        label="Operação",
        widget=forms.Select(
            attrs={"class": "form-control"},
        ),
    )

    numero_protocolo = django_filters.NumberFilter(
        field_name="pedido__protocolo__numero_protocolo",
        lookup_expr="exact",
        label="Numero Protocolo",
    )

    numero_pedido_certidao = django_filters.NumberFilter(
        # field_name="pedido_certidao_id",
        field_name="numero_pedido_certidao",
        lookup_expr="exact",
        label="Numero Pedido Certidão",
    )

    tipo_transacao_id = django_filters.ModelChoiceFilter(
        queryset=TipoTransacaoFinanceira.objects.none(),
        label="Transação",
        widget=forms.Select(
            attrs={"class": "form-control"},
        ),
    )

    tipo_categoria_financeira = django_filters.ModelChoiceFilter(
        queryset=TipoCategoriaFinanceira.objects.none(),
        label="Categoria",
        widget=forms.Select(
            attrs={"class": "form-control"},
        ),
    )

    colaborador = django_filters.ModelChoiceFilter(
        queryset=Colaborador.objects.none(),
        label="Colaborador",
        widget=forms.Select(
            attrs={
                "class": "form-control",
                "placeholder": "Colaborador",
            },
        ),
    )

    class Meta:
        model = Financeiro
        fields = [
            "data_transacao_inicio",
            "data_transacao_fim",
            "tipo_operacao_financeira_id",
            "tipo_transacao_id",
            "tipo_categoria_financeira",
            "descricao",
            "valor_transacao",
            "colaborador",
        ]
        ordering = ["-id"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.filters[
            "tipo_operacao_financeira_id"
        ].queryset = TipoOperacaoFinanceira.objects.all().order_by("descricao")
        self.filters[
            "tipo_categoria_financeira"
        ].queryset = TipoCategoriaFinanceira.objects.all().order_by("descricao")
        self.filters[
            "tipo_transacao_id"
        ].queryset = TipoTransacaoFinanceira.objects.all().order_by("descricao")
        self.filters[
            "colaborador"
        ].queryset = Colaborador.objects.filtrar_por_exibir_nome_caixa()


class EventFilter(FilterSet):
    # origem = django_filters.ModelChoiceFilter(
    #     queryset=get_origem_evento_queryset(),
    #     label="origem",
    #     widget=forms.Select(
    #         attrs={"class": "form-control", "placeholder": "origem"},
    #     ),
    # )

    numero = CharFilter(lookup_expr="exact")
    title = CharFilter(lookup_expr="icontains")
    description = CharFilter(lookup_expr="icontains")

    start_time = django_filters.DateFilter(
        field_name="start_time",
        method=filter_start_date,
        widget=forms.DateInput(
            attrs={
                "type": "date",
                "class": "form-control",
                "placeholder": "Data Inicial",
                "title": "Data de Inicial",
            },
        ),
    )

    end_time = django_filters.DateFilter(
        field_name="start_time",
        method=filter_end_date,
        widget=forms.DateInput(
            attrs={
                "type": "date",
                "class": "form-control",
                "placeholder": "Data Final",
                "title": "Data Final",
            },
        ),
    )

    # user_id = django_filters.ModelChoiceFilter(
    #     queryset=get_colaborador_queryset(),
    #     label="Colaborador",
    #     widget=forms.Select(
    #         attrs={"class": "form-control", "placeholder": "Colaborador"},
    #     ),
    # )

    # auth_user_id = django_filters.ModelChoiceFilter(
    #     queryset=get_colaborador_queryset(),
    #     label="Destinatário",
    #     widget=forms.Select(
    #         attrs={"class": "form-control", "placeholder": "Destinatário"},
    #     ),
    # )

    class Meta:
        model = Event
        fields = [
            "origem",
            "numero",
            "title",
            "start_time",
            "end_time",
            "user",
            "auth_user",
            "description",
        ]
        ordering = ["-start_time"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Outros filtros iniciais podem ser configurados aqui
        # self.filters['colaborador'].queryset = Colaborador.objects.all()


class EventColaboradorFilter(EventFilter):
    user = django_filters.ModelChoiceFilter(
        queryset=User.objects.none(),
        label="Criado Por",
        widget=forms.Select(
            attrs={"class": "form-control", "placeholder": "Colaborador"},
        ),
    )
    auth_user = django_filters.ModelChoiceFilter(
        queryset=User.objects.none(),
        label="Encaminhado Para",
        widget=forms.Select(
            attrs={"class": "form-control", "placeholder": "Colaborador"},
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        usuarios_ativos = get_user_ativo_queryset()
        self.filters["user"].queryset = usuarios_ativos
        self.filters["auth_user"].queryset = usuarios_ativos


class FinanceiroColaboradorFilter(FinanceiroFilter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.filters["colaborador"].field.widget = forms.HiddenInput()


class UtilizadoFilter(django_filters.BooleanFilter):
    def filter(self, qs, value):
        if value is None:
            return qs
        if value:
            return qs.filter(utilizado_em__isnull=False)
        else:
            return qs.filter(utilizado_em__isnull=True)


def filter_numero_pedido(queryset, name, value):
    return SeloEletronico.objects.filter_numero_pedido().filter(numero_pedido=value)


class SeloFilter(FilterSet):
    utilizado_inicio = django_filters.DateFilter(
        field_name="utilizado_em",
        lookup_expr="gte",
        label="Utilizado de:",
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
        method=filter_start_date,
        initial=timezone.now().date(),
    )

    utilizado_fim = django_filters.DateFilter(
        field_name="utilizado_em",
        lookup_expr="lte",
        label="Utilizado Até",
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
        method=filter_end_date,
        initial=timezone.now().date(),
    )

    selo_de_consulta = CustomBooleanFilter(field_name="selo_de_consulta")

    utilizado = UtilizadoFilter(
        field_name="utilizado_em",
        label="Utilizado",
        widget=forms.CheckboxInput(
            attrs={"class": "form-check-input", "checked": True},
        ),
    )

    codigo_sequencial_unico = CharFilter(
        lookup_expr="icontains",
        label="Número Selo contém",
    )

    numero_pedido = django_filters.NumberFilter(
        method=filter_numero_pedido,
        label="Ped. Certidão",
    )

    class Meta:
        model = SeloEletronico
        fields = [
            "utilizado",
            "utilizado_inicio",
            "utilizado_fim",
            "codigo_sequencial_unico",
            "numero_pedido",
            "selo_de_consulta",
        ]


class Livro05Filter(FilterSet):
    nome = django_filters.CharFilter(lookup_expr="icontains", label="Nome")
    cpf = django_filters.CharFilter(
        lookup_expr="icontains",
        label="CPF ",
    )
    email = django_filters.CharFilter(
        field_name="versoes__email",
        lookup_expr="icontains",
        label="Email",
    )

    class Meta:
        model = Livro05
        fields = ("nome", "cpf", "email")


class PeriodoCertidaoFilter(django_filters.Filter):
    def __init__(self, field_name, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.field_name = field_name

    def filter(self, qs, value):
        if value:
            # Convertendo a string para um objeto datetime.date
            value = datetime.strptime(value, "%Y-%m-%d").date()
            data_inicio = timezone.make_aware(datetime.combine(value, time.min))
            data_fim = timezone.make_aware(datetime.combine(value, time.max))
            filtro = {
                f"{self.field_name}__gte": data_inicio,
                f"{self.field_name}__lt": data_fim,
            }
            return qs.filter(**filtro)
        return qs


class CustomTextInput(forms.TextInput):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.attrs.update({"class": "form-control"})


class PedidoCertidaoFilter(FilterSet):
    numero_pedido = CharFilter(method="filter_by_numero_pedido")

    protocolo_onr = CharFilter(lookup_expr="icontains")

    apresentante = django_filters.CharFilter(
        field_name="apresentante__nome",
        lookup_expr="icontains",
        label="Nome do Apresentante",
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Apresentante"},
        ),
    )

    data_entrada_inicial = django_filters.DateFilter(
        field_name="data_entrada",
        method=filter_start_date,
        widget=forms.DateInput(
            attrs={
                "type": "date",
                "class": "form-control",
                "placeholder": "Data de Entrada Inicial",
                "title": "Data de Entrada",
            },
        ),
    )

    data_entrada_final = django_filters.DateFilter(
        field_name="data_entrada",
        method=filter_end_date,
        widget=forms.DateInput(
            attrs={
                "type": "date",
                "class": "form-control",
                "placeholder": "Data de Entrada Final",
                "title": "Data de Entrada Final",
            },
        ),
    )

    def filtrar_por_intervalo(self, queryset, name, value):
        if value:
            # Definindo o final do dia da data final
            final_do_dia = make_aware(datetime.combine(value, datetime.max.time()))
            # Capturando a data inicial do filtro
            data_inicio = self.form.cleaned_data.get("data_entrada_inicial")
            if data_inicio:
                # Definindo o início do dia da data inicial
                inicio_do_dia = make_aware(
                    datetime.combine(data_inicio, datetime.min.time()),
                )
                # Aplicando o filtro de intervalo
                return queryset.filter(
                    data_entrada__gte=inicio_do_dia,
                    data_entrada__lte=final_do_dia,
                )
        return queryset

    def filter_by_numero_pedido(self, queryset, name, value):
        # Expressão regular para manter apenas números
        def clean_number(num) -> str:
            return re.sub(r"\D", "", num)

        # Split the input string by comma, strip extra spaces, and clean the numbers
        numero_pedidos = [
            clean_number(num.strip())
            for num in value.split(",")
            if clean_number(num.strip())
        ]

        # Filter the queryset to include only those with a numero_pedido in the cleaned list
        return queryset.filter(numero_pedido__in=numero_pedidos)

    origem = django_filters.ModelChoiceFilter(
        queryset=TipoOrigem.objects.none(),
        label="Origem",
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    class Meta:
        model = PedidoCertidao
        fields = ["numero_pedido", "protocolo_onr", "criado_por", "apresentante"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.filters["numero_pedido"].field.widget = forms.TextInput(
            attrs={"autofocus": "autofocus"},
        )
        self.filters["origem"].queryset = TipoOrigem.objects.all()
        today = timezone.now().date()
        self.filters["data_entrada_inicial"].field.initial = today
        self.filters["data_entrada_final"].field.initial = today


class ProtocoloAndamentosFilter(FilterSet):
    numero_protocolo = django_filters.NumberFilter(
        field_name="protocolo__numero_protocolo",
        lookup_expr="exact",
        label="Protocolo",
    )

    class Meta:
        model = Livro01Andamento
        fields = ["numero_protocolo"]


class PedidoCertidaoAnexoFilter(FilterSet):
    class Meta:
        model = PedidoCertidaoAnexo
        fields = ["arquivo", "descricao"]
        filter_overrides = {
            models.FileField: {
                "filter_class": django_filters.CharFilter,
                "extra": lambda f: {
                    "lookup_expr": "icontains",
                },
            },
        }


class ColaboradorFilter(FilterSet):
    class Meta:
        model = Colaborador
        fields = ["nome", "usuario__status"]
