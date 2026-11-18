import itertools
import logging
from decimal import Decimal

import django_tables2 as tables
from django.conf import settings
from django.urls import reverse
from django.utils.html import escape, format_html
from django.utils.safestring import mark_safe
from django_tables2 import A, TemplateColumn

from apps.comum.utils import formatar_moeda
from apps.home.helpers import formatar_codigo_seguranca_mg, formatar_protocolo
from apps.home.models.models_certidoes import (
    Certidao,
    PedidoCertidao,
    PedidoCertidaoAndamento,
    PedidoCertidaoAnexo,
    PedidoCertidaoImovel,
    PedidoCertidaoPessoa,
)
from apps.home.models.models_home import (
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
)

logger = logging.getLogger(__name__)
logger.debug(f"Iniciando {__name__}")


def format_currency(value):
    return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


class LinkColumn(tables.Column):
    def render(self, value, record):
        url = record.get_protocolo_url()
        return format_html(
            '<a class="img-radius img-fluid wid-30" href="{}">{}</a>',
            url,
            value,
        )


class AvatarColumn(tables.Column):
    def render(self, value):
        return format_html(
            '<img src="{}" class="img-radius img-fluid wid-30" width="50" height="50"/>',
            value,
        )


class ImageNameColumn(tables.Column):
    def render(self, record: Colaborador):
        print(
            f"Imagem: {record.usuario.image.url}, Nome: {record.nome}",
        )  # Para depuração
        return format_html(
            '<img src="{}" class="img-radius img-fluid wid-30" width="50" height="50" /> {}',
            record.image.url,
            record.nome,
        )


class TabelaBase(tables.Table):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.attrs = {
            "class": "table table-hover table-striped table-bordered no-footer nowrap",
        }


class Livro01AndamentoTable(tables.Table):
    counter = tables.TemplateColumn(
        template_code="{{ record.counter }}",
        verbose_name="#",
        orderable=False,
    )
    protocolo = tables.LinkColumn(
        "home:protocolo_detail",
        args=[tables.A("protocolo_id")],
        verbose_name="Protocolo",
        orderable=True,
        attrs={"a": {"target": "_blank"}},
    )
    tipo_andamento = tables.LinkColumn(
        "home:andamento_detail",
        args=[tables.A("pk")],
        verbose_name="Tipo de Andamento",
        orderable=True,
    )
    # colaborador = tables.Column(verbose_name="Colaborador")
    data_prevista_formatada = tables.Column(empty_values=(), verbose_name="Dt Prevista")
    titulos = tables.Column(empty_values=(), verbose_name="Títulos")
    atos = tables.Column(empty_values=(), verbose_name="Atos")
    observacao = tables.Column(empty_values=(), verbose_name="Anotações")
    # colaborador_encaminhado = tables.Column(empty_values=(), verbose_name="Encaminhado")

    def render_data_prevista_formatada(self, record):
        if record.protocolo and record.protocolo.data_prevista:
            return record.protocolo.data_prevista.strftime(settings.DATE_FORMAT_STR)
        return None

    def render_titulos(self, record):
        if record.protocolo and record.protocolo.titulos_principais_descricao:
            return record.protocolo.titulos_principais_descricao
        return None

    def render_atos(self, record):
        if record.protocolo and record.protocolo.atos_principais_descritos_agrupados:
            return record.protocolo.atos_principais_descritos_agrupados()
        return None

    def render_observacao(self, record):
        return (
            record.protocolo.pedido.observacao.title()
            if record.protocolo.pedido.observacao
            else "N/A"
        )

    def count_records(self):
        return Decimal(len(self.data))

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        for index, record in enumerate(self.data, 1):
            record.counter = index

    class Meta:
        model = Livro01Andamento
        order_by = ["-data"]
        attrs = {
            "class": "table table-hover table-striped table-bordered no-footer nowrap",
        }
        empty_text = "Nenhum andamento"
        fields = (
            "counter",
            "protocolo",
            "protocolo__data_protocolo",
            "data_prevista_formatada",
            "tipo_andamento",
            "colaborador",
            "colaborador_destino",
            "titulo",
            "atos",
            "observacao",
        )


class AndamentosTableExport(Livro01AndamentoTable):
    class Meta(Livro01AndamentoTable.Meta):
        fields = (*Livro01AndamentoTable.Meta.fields, "texto")


class AndamentosValoresTableExport(Livro01AndamentoTable):
    # class Meta(Livro01AndamentoTable.Meta):
    #    fields = (*Livro01AndamentoTable.Meta.fields, "valores")

    class Meta:
        model = Livro01Andamento
        order_by = ["-data"]
        attrs = {
            "class": "table table-hover table-striped table-bordered no-footer nowrap",
        }
        empty_text = "Nenhum andamento encontrado"
        fields = (
            "counter",
            "protocolo",
            "protocolo__data_protocolo",
            # "data_prevista_formatada",
            # "tipo_andamento",
            "colaborador",
            # "colaborador_encaminhado",
            # "titulo",
            # "atos",
            # "observacao",
        )


class Livro01ProtocoloTable(tables.Table):
    # counter = TemplateColumn(
    #     template_code="{{ record.counter }}",
    #     verbose_name="#",
    #     orderable=False,
    # )
    numero_protocolo = tables.TemplateColumn(
        template_code='<a href="{% url "home:protocolo_detail" record.pk %}">{{ record.protocolo_formatado }}</a>',
        verbose_name="Protocolo",
        orderable=True,
    )

    # status_protocolo_descricao = tables.Column(verbose_name="Status Protocolo")
    colaborador_ultimo_andamento = tables.Column(verbose_name="Colaborador")
    data_protocolo = tables.DateColumn(
        verbose_name="Entrada",
        # format=settings.SHORT_DATE_FORMAT,
        format=settings.DATETIME_FORMAT,
    )
    data_prevista = tables.DateTimeColumn(
        verbose_name="Previsão",
        format=settings.SHORT_DATE_FORMAT,
    )
    data_reentrada = tables.DateTimeColumn(
        verbose_name="Reentrada",
        format=settings.SHORT_DATE_FORMAT,
    )
    observacao_pedido = tables.Column(empty_values=(), verbose_name="Anotações")
    nome_apresentante = tables.Column(empty_values=(), verbose_name="Apresentante")
    maximo_dias_qualificar_titulo = tables.Column(
        empty_values=(),
        verbose_name="Prazo",
        orderable=True,
    )
    primeira_data_exigencia = tables.DateColumn(
        verbose_name="Qualificar",
        format=settings.SHORT_DATE_FORMAT,
    )

    recebido_colaborador = tables.Column(
        empty_values=(),
        verbose_name="Recebido",
        orderable=False,
        attrs={"td": {"class": "break-word"}},
    )

    status_protocolo_descricao = tables.TemplateColumn(
        template_code='<a href="{% url "home:protocolo_andamentos" record.pk %}?numero_protocolo={{ record.numero_protocolo }}"> <span class="{% if record.status_protocolo_descricao == "Em Andamento" %} bg-success text-dark {% elif record.status_protocolo_descricao == "Registrado" %} bg-primary text-white {% elif record.status_protocolo_descricao == "Cancelado" %} bg-danger text-white {% elif record.status_protocolo_descricao == "Sub Judice" %} bg-secondary text-white {% elif record.status_protocolo_descricao == "Exigência" %} bg-warning text-dark {% elif record.status_protocolo_descricao == "Em Análise" %} bg-info text-dark {% elif record.status_protocolo_descricao == "Em Registro" %} bg-info text-dark {% endif %}"> <span class="font-weight-bold mx-3 f-12 text-white"> {{ record.status_protocolo_descricao }} </span></a>',
        verbose_name="Status",
        orderable=False,
    )

    def count_records(self):
        number = len(self.data)
        return f"{number:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")

    def render_recebido_colaborador(self, record) -> str:
        data_recebido = (
            record.data_confirmacao_recebimento.strftime(settings.DATE_FORMAT_STR)
            if record.data_confirmacao_recebimento
            else ""
        )
        colaborador = record.colaborador_que_recebeu_protocolo

        return f"{colaborador} ({data_recebido})" if colaborador else ""

    class Meta:
        model = Livro01Protocolo
        attrs = {
            "class": "table table-hover table-striped table-bordered no-footer nowrap",
        }
        empty_text = "Nenhum protocolo encontrado"
        order_by = ["-numero_protocolo"]
        fields = (
            # "counter",
            "numero_protocolo",
            "data_protocolo",
            "maximo_dias_qualificar_titulo",
            "primeira_data_exigencia",
            "data_reentrada",
            "status_protocolo_descricao",
            "data_prevista",
            "nome_apresentante",
            "recebido_colaborador",
            "observacao_pedido",
            "colaborador",
            "ultimo_andamento",
        )


class Livro01ProtocoloOnrTable(tables.Table):
    counter = TemplateColumn(
        template_code="{{ record.counter }}",
        verbose_name="#",
        orderable=False,
    )
    numero_protocolo = tables.TemplateColumn(
        template_code='<a href="{{ record.get_absolute_url }}">{{ record.protocolo_formatado }}</a>',
        verbose_name="Protocolo",
        orderable=True,
    )

    colaborador_ultimo_andamento = tables.Column(verbose_name="Colaborador")
    # data_prevista = tables.Column(empty_values=(), verbose_name="Dt Prevista")
    # data_reentrada = tables.Column(empty_values=(), verbose_name="Reentrada")

    observacao_pedido = tables.Column(empty_values=(), verbose_name="Anotações")
    nome_apresentante = tables.Column(empty_values=(), verbose_name="Apresentante")
    origem_formatada = tables.Column(empty_values=(), verbose_name="Protocolo ONR")

    # maximo_dias_qualificar_titulo = tables.Column(empty_values=(), verbose_name="Prazo", orderable=True)
    # primeira_data_exigencia = tables.Column(empty_values=(), verbose_name="Qualificar")
    # recebido_colaborador = tables.Column(
    #     empty_values=(),
    #     verbose_name="Recebido",
    #     orderable=False,
    #     attrs={"td": {"class": "break-word"}},
    # )

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        for index, record in enumerate(self.data, 1):
            record.counter = index

    def count_records(self):
        return len(self.data)

    # def render_data_reentrada(self, record):
    #     return record.data_reentrada.strftime(settings.DATE_FORMAT_STR) if record.data_reentrada else "-"

    # def render_data_prevista(self, record):
    #     return record.data_prevista.strftime(settings.DATE_FORMAT_STR) if record.data_prevista else "-"

    # def render_data_confirmacao_recebimento(self, record):
    #     return (
    #         record.data_confirmacao_recebimento.strftime(settings.DATE_FORMAT_STR)
    #         if record.data_confirmacao_recebimento
    #         else "-"
    #     )

    # def render_recebido_colaborador(self, record) -> str:
    #     data_recebido = (
    #         record.data_confirmacao_recebimento.strftime(settings.DATE_FORMAT_STR)
    #         if record.data_confirmacao_recebimento
    #         else ""
    #     )
    #     colaborador = record.colaborador_que_recebeu_protocolo

    #     return f"{colaborador} ({data_recebido})" if colaborador else ""

    class Meta:
        model = Livro01Protocolo
        attrs = {
            "class": "table table-hover table-striped table-bordered no-footer nowrap",
        }
        empty_text = "Nenhum protocolo encontrado"
        order_by = ["-numero_protocolo"]
        fields = (
            "counter",
            "numero_protocolo",
            "origem_formatada",
            "data_protocolo",
            # "maximo_dias_qualificar_titulo",
            # "primeira_data_exigencia",
            # "data_reentrada",
            # "data_prevista",
            # "recebido_colaborador",
            "nome_apresentante",
            "observacao_pedido",
            "colaborador_ultimo_evento",
            # "ultimo_evento",
        )


class Livro02Table(tables.Table):
    # counter = TemplateColumn(
    #     # template_code="{{ record.counter }}", verbose_name="#", orderable=False
    #     # adicione o link para o registro
    #     template_code='<a href="{{ record.get_absolute_url }}">{{ record.counter }}</a>',
    #     verbose_name="#",
    #     orderable=False,
    # )
    numero = tables.LinkColumn(
        "home:livro04_imovel",
        args=[A("pk")],
        verbose_name="Número",
        orderable=True,
    )

    acoes = tables.TemplateColumn(
        template_code="""
            <div class="dropdown">
                <a class="text-blue" id="dropdownMenuButton" data-bs-toggle="dropdown" aria-haspopup="true" aria-expanded="false">
                            Opções <i class="fa fa-angle-down" aria-hidden="true ms-1"></i>
                        </a>
                <div class="dropdown-menu" aria-labelledby="dropdownMenuButton{{ record.pk }}">
                    <a class="dropdown-item" href="{% url 'home:livro02_detail' record.pk %}">Abrir</a>
                    <a class="dropdown-item" href="{% url 'home:livro02_texto' record.pk %}">Abrir Ficha</a>
                    <a class="dropdown-item" href="{% url 'home:livro04_imovel' record.pk %}">Abrir Imóvel (Livro04)</a>
                    <!-- Adicione mais links de ação conforme necessário -->
                </div>
            </div>
            """,
        verbose_name="Ações",
        orderable=False,
    )

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.base_columns["cnm_formatada"].verbose_name = "CNM"
        self.base_columns["cnm_formatada"].orderable = False

    def count_records(self):
        return len(self.data)

    class Meta:
        model = Livro02
        attrs = {
            "class": "table table-hover table-striped table-bordered no-footer nowrap",
        }
        empty_text = "Nenhum registro encontrado"
        order_by = ["-numero"]
        fields = (
            "numero",
            "cnm_formatada",
            "tipo",
            "cartorio",
            "data_abertura",
            "classe",
            "municipio",
        )


class Livro03Table(tables.Table):
    counter = TemplateColumn(
        template_code="{{ record.counter }}",
        verbose_name="#",
        orderable=False,
    )

    numero = tables.LinkColumn(
        "home:livro03_detail",
        args=[A("pk")],
        verbose_name="Registro",
        orderable=True,
        attrs={"a": {"target": "_blank"}},
    )

    data_abertura = tables.DateTimeColumn(
        verbose_name="Data Abertura",
        format=settings.DATE_FORMAT,
    )
    data_vencimento = tables.DateTimeColumn(
        verbose_name="Vencimento",
        format=settings.DATE_FORMAT,
    )
    cancelado_em = tables.DateTimeColumn(
        verbose_name="Cancelamento",
        format=settings.DATE_FORMAT,
    )
    numero_cedula = tables.Column(verbose_name="Número Cédula")
    descricao = tables.Column(verbose_name="Descrição")
    tipo_registro_auxiliar = tables.Column(
        empty_values=(),
        verbose_name="Tipo de Cédula",
    )

    # def render_data_abertura(self, record):
    #     return record.data_abertura if record.data_abertura else ""

    # def render_data_vencimento(self, record):
    #     return record.data_vencimento if record.data_vencimento else ""

    # def render_cancelado_em(self, record):
    #     return record.cancelado_em if record.cancelado_em else ""

    def render_tipo_registro_auxiliar_id(self, record):
        return record.tipo_registro_auxiliar if record.tipo_registro_auxiliar_id else ""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        counter = itertools.count(start=1)
        for record in self.data:
            record.counter = next(counter)
        # self.base_columns["imovel"].verbose_name = "Imovel"

    def count_records(self):
        return Decimal(len(self.data))

    class Meta:
        model = Livro03
        attrs = {
            "class": "table table-hover table-striped table-bordered no-footer nowrap",
        }
        empty_text = "Nenhum registro encontrado"
        order_by = ["-numero"]
        fields = (
            "counter",
            "numero",
            "cartorio",
            "data_abertura",
            "data_vencimento",
            "cancelado_em",
            "tipo_registro_auxiliar",
            "numero_cedula",
            "descricao",
        )


class AndamentosExigenciasTable(tables.Table):
    counter = tables.TemplateColumn(
        template_code="{{ record.counter }}",
        verbose_name="#",
        orderable=False,
    )
    protocolo = tables.LinkColumn(
        "home:protocolo_detail",
        args=[tables.A("protocolo_id")],
        verbose_name="Protocolo",
        orderable=True,
        attrs={"a": {"target": "_blank"}},
    )
    tipo_andamento = tables.LinkColumn(
        "home:andamento_texto_detail",
        args=[tables.A("pk")],
        verbose_name="Andamento",
        orderable=False,
        attrs={"a": {"target": "_blank"}},
    )
    colaborador = tables.Column(verbose_name="Colaborador")
    data_prevista_formatada = tables.DateColumn(
        empty_values=(),
        verbose_name="Previsao",
        format=settings.DATE_FORMAT,
    )
    titulos = tables.Column(empty_values=(), verbose_name="Títulos")
    atos = tables.Column(empty_values=(), verbose_name="Atos")
    observacao = tables.Column(empty_values=(), verbose_name="Anotações")
    colaborador_encaminhado = tables.Column(empty_values=(), verbose_name="Encaminhado")

    # def render_data_prevista_formatada(self, record):
    #     if record.protocolo and record.protocolo.data_prevista:
    #         return record.protocolo.data_prevista.strftime(settings.DATE_FORMAT_STR)

    #     return ""

    def render_titulos(self, record):
        if record.protocolo and record.protocolo.titulos_principais_descricao:
            return record.protocolo.titulos_principais_descricao

        return ""

    def render_atos(self, record):
        if record.protocolo and record.protocolo.atos_principais_descritos_agrupados:
            return record.protocolo.atos_principais_descritos_agrupados()

        return ""

    def render_colaborador_encaminhado(self, record):
        if record.protocolo and record.protocolo.colaborador:
            return record.protocolo.colaborador

        return ""

    def render_observacao(self, record):
        return (
            record.protocolo.pedido.observacao.title()
            if record.protocolo.pedido.observacao
            else "N/A"
        )

    def count_records(self):
        return Decimal(len(self.data))

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        for index, record in enumerate(self.data, 1):
            record.counter = index

    class Meta:
        model = Livro01Andamento
        order_by = ["-data"]
        attrs = {
            "class": "table table-hover table-striped table-bordered no-footer nowrap",
        }
        empty_text = "Nenhum registro encontrado"
        fields = (
            "counter",
            "protocolo",
            "protocolo__data_protocolo",
            "data_prevista_formatada",
            "data",
            # "data_exigencia",
            "colaborador",
            "colaborador_encaminhado",
            "titulo",
            "atos",
            "observacao",
        )


class AndamentosRegistradosTable(tables.Table):
    counter = tables.TemplateColumn(
        template_code="{{ record.counter }}",
        verbose_name="#",
        orderable=False,
    )
    protocolo = tables.LinkColumn(
        "home:protocolo_detail",
        args=[tables.A("protocolo_id")],
        verbose_name="Protocolo",
        orderable=True,
        attrs={"a": {"target": "_blank"}},
    )
    tipo_andamento = tables.LinkColumn(
        "home:andamento_texto_detail",
        args=[tables.A("pk")],
        verbose_name="Andamento",
        orderable=False,
        attrs={"a": {"target": "_blank"}},
    )
    colaborador = tables.Column(verbose_name="Colaborador")
    data_prevista_formatada = tables.Column(empty_values=(), verbose_name="Dt Prevista")
    titulos = tables.Column(empty_values=(), verbose_name="Títulos")
    atos = tables.Column(empty_values=(), verbose_name="Atos")
    observacao = tables.Column(empty_values=(), verbose_name="Anotações")
    colaborador_encaminhado = tables.Column(empty_values=(), verbose_name="Encaminhado")

    def render_data_prevista_formatada(self, record):
        if record.protocolo and record.protocolo.data_prevista:
            return record.protocolo.data_prevista.strftime(settings.DATE_FORMAT_STR)

        return ""

    def render_titulos(self, record):
        if record.protocolo and record.protocolo.titulos_principais_descricao:
            return record.protocolo.titulos_principais_descricao

        return ""

    def render_atos(self, record):
        if record.protocolo and record.protocolo.atos_principais_descritos_agrupados:
            return record.protocolo.atos_principais_descritos_agrupados()

        return ""

    def render_colaborador_encaminhado(self, record):
        if record.protocolo and record.protocolo.fases_protocolo_colaborador_atual:
            return record.protocolo.fases_protocolo_colaborador_atual

        return ""

    def render_observacao(self, record):
        return (
            record.protocolo.pedido.observacao.title()
            if record.protocolo.pedido.observacao
            else "N/A"
        )

    def count_records(self):
        return Decimal(len(self.data))

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        for index, record in enumerate(self.data, 1):
            record.counter = index

    class Meta:
        model = Livro01Andamento
        order_by = ["-data"]
        attrs = {
            "class": "table table-hover table-striped table-bordered no-footer nowrap",
        }
        empty_text = "Nenhum registro encontrado"
        fields = (
            "counter",
            "protocolo",
            "protocolo__data_protocolo",
            "data",
            "data_prevista_formatada",
            "colaborador",
            # "colaborador_encaminhado",
            # "titulo",
            # "atos",
            # "observacao",
        )


class AndamentosPrenotadosTable(tables.Table):
    counter = tables.TemplateColumn(
        template_code="{{ record.counter }}",
        verbose_name="#",
        orderable=False,
    )
    protocolo = tables.LinkColumn(
        "home:protocolo_detail",
        args=[tables.A("protocolo_id")],
        verbose_name="Protocolo",
        orderable=True,
        attrs={"a": {"target": "_blank"}},
    )
    tipo_andamento = tables.LinkColumn(
        "home:andamento_texto_detail",
        args=[tables.A("pk")],
        verbose_name="Andamento",
        orderable=False,
        attrs={"a": {"target": "_blank"}},
    )
    colaborador = tables.Column(verbose_name="Colaborador")
    data_prevista_formatada = tables.Column(empty_values=(), verbose_name="Dt Prevista")
    titulos = tables.Column(empty_values=(), verbose_name="Títulos")
    atos = tables.Column(empty_values=(), verbose_name="Atos")
    observacao = tables.Column(empty_values=(), verbose_name="Anotações")
    colaborador_encaminhado = tables.Column(empty_values=(), verbose_name="Encaminhado")

    def render_data_prevista_formatada(self, record):
        if record.protocolo and record.protocolo.data_prevista:
            return record.protocolo.data_prevista.strftime(settings.DATE_FORMAT_STR)

        return ""

    def render_titulos(self, record):
        if record.protocolo and record.protocolo.titulos_principais_descricao:
            return record.protocolo.titulos_principais_descricao

        return ""

    def render_atos(self, record):
        if record.protocolo and record.protocolo.atos_principais_descritos_agrupados:
            return record.protocolo.atos_principais_descritos_agrupados()

        return ""

    def render_colaborador_encaminhado(self, record):
        if record.protocolo and record.protocolo.fases_protocolo_colaborador_atual:
            return record.protocolo.fases_protocolo_colaborador_atual

        return ""

    def render_observacao(self, record):
        return (
            record.protocolo.pedido.observacao.title()
            if record.protocolo.pedido.observacao
            else "N/A"
        )

    def count_records(self):
        return Decimal(len(self.data))

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        for index, record in enumerate(self.data, 1):
            record.counter = index

    class Meta:
        model = Livro01Andamento
        order_by = ["-data"]
        attrs = {
            "class": "table table-hover table-striped table-bordered no-footer nowrap",
        }
        empty_text = "Nenhum registro encontrado"
        fields = (
            "counter",
            "protocolo",
            "protocolo__data_protocolo",
            "data",
            "data_prevista_formatada",
            "colaborador",
        )


# class AndamentosTable(tables.Table):
#     counter = TemplateColumn(
#         template_code="{{ record.counter }}", verbose_name="#", orderable=False
#     )
#     protocolo_formatado = tables.LinkColumn(
#         "home:protocolo_detail",
#         args=[A("pk")],
#         verbose_name="Protocolo",
#         orderable=True,
#         attrs={"a": {"target": "_blank"}},
#     )

#     colaborador_ultimo_andamento = tables.Column(verbose_name="Colaborador")
#     data_prevista_formatada = tables.Column(empty_values=(), verbose_name="Data Prevista")
#     data_reentrada_formatada = tables.Column(empty_values=(), verbose_name="Reentrada")
#     observacao_pedido = tables.Column(empty_values=(), verbose_name="Anotações")
#     nome_apresentante = tables.Column(empty_values=(), verbose_name="Apresentante")
#     maximo_dias_qualificar_titulo = tables.Column(empty_values=(), verbose_name="Dias")
#     primeira_data_exigencia = tables.Column(empty_values=(), verbose_name="Qualificar")

#     def __init__(self, *args, **kwargs):
#         super(AndamentosTable, self).__init__(*args, **kwargs)
#         counter = itertools.count(start=1)
#         for record in self.data:
#             record.counter = next(counter)
#         self.base_columns["protocolo_formatado"].verbose_name = "Protocolo"
#         self.base_columns["colaborador_ultimo_andamento"].verbose_name = "Colaborador"
#         self.base_columns["data_prevista_formatada"].verbose_name = "Data Prevista"
#         self.base_columns["data_reentrada_formatada"].verbose_name = "Reentrada"
#         self.base_columns["observacao_pedido"].verbose_name = "Observação"
#         self.base_columns["nome_apresentante"].verbose_name = "Apresentante"
#         self.base_columns["primeira_data_exigencia"].verbose_name = "Qualificar"

#     def count_records(self):
#         return Decimal(len(self.data))

#     class Meta:
#         model = Protocolo
#         attrs = {
# "class": "table table-hover table-striped table-bordered no-footer nowrap"
# }
#         empty_text = "Nenhum registro encontrado"
#         order_by = ["-numero_protocolo"]
#         fields = (
#             "counter",
#             "protocolo_formatado",
#             "data_protocolo",
#             "maximo_dias_qualificar_titulo",
#             "primeira_data_exigencia",
#             "data_reentrada_formatada",
#             "data_prevista_formatada",
#             "nome_apresentante",
#             "observacao_pedido",
#             "colaborador_ultimo_andamento",
#             "ultimo_andamento",
#         )


class DoiTable(tables.Table):
    counter = TemplateColumn(
        template_code="{{ record.counter }}",
        verbose_name="#",
        orderable=False,
    )
    data_protocolo = tables.Column(empty_values=(), verbose_name="Data Protocolo")
    data_registro = tables.Column(empty_values=(), verbose_name="Data Registro")
    # utilizado_em = tables.Column(empty_values=(), verbose_name="Data Selo")
    numero_protocolo = tables.Column(empty_values=(), verbose_name="Protocolo")
    numero_registro = tables.Column(empty_values=(), verbose_name="Número")
    numero_ato = tables.Column(empty_values=(), verbose_name="Reg. Praticado")
    valor_avaliacao = tables.Column(empty_values=(), verbose_name="Vl. Avaliação")
    valor_itbi = tables.Column(empty_values=(), verbose_name="Vl. Alienação")
    ato_id = tables.Column(empty_values=(), verbose_name="Tipo Alienação")

    def render_data_selo(self, record):
        return record.get_data_selo().strftime(settings.DATE_FORMAT_STR)

    def render_data_registro(self, record):
        return record.get_data_registro().strftime(settings.DATE_FORMAT_STR)

    def render_data_protocolo(self, record):
        return record.get_data_protocolo().strftime(settings.DATE_FORMAT_STR)

    def render_numero_protocolo(self, record):
        return record.get_numero_protocolo()

    def render_ato_id(self, record):
        return record.descricao_ato()

    def render_valor_avaliacao(self, value):
        if value is not None:
            return (
                f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            )
        return ""  # Retorne uma string vazia se o valor for None.

    def render_valor_itbi(self, value):
        if value is not None:
            return (
                f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            )
        return ""  # Retorne uma string vazia se o valor for None.

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        counter = itertools.count(start=1)
        for record in self.data:
            record.counter = next(counter)

        self.base_columns["ato_id"].verbose_name = "Tipo Alienação"
        self.base_columns["data_protocolo"].verbose_name = "Data Protocolo"
        self.base_columns["data_registro"].verbose_name = "Data Registro"
        self.base_columns["numero_protocolo"].verbose_name = "Protocolo"

    def count_records(self):
        return Decimal(len(self.data))

    class Meta:
        model = PedidoItem
        attrs = {
            "class": "table table-hover table-striped table-bordered no-footer nowrap",
        }
        empty_text = "Nenhum registro encontrado"
        order_by = ["-numero_registro"]
        fields = (
            "counter",
            # "utilizado_em",
            "data_registro",
            "numero_protocolo",
            "numero_ato",
            "numero_registro",
            "valor_avaliacao",
            "valor_itbi",
            "ato_id",
            "data_protocolo",
        )


class Livro04Table(tables.Table):
    counter = TemplateColumn(
        # template_code="{{ record.counter }}", verbose_name="#", orderable=False
        # adicione o link para o registro
        template_code='<a href="{{ record.get_absolute_url }}">{{ record.counter }}</a>',
        verbose_name="#",
        orderable=False,
    )
    numero = tables.LinkColumn(
        "home:livro04_imovel",
        args=[A("pk")],
        verbose_name="Número",
        orderable=True,
        attrs={"a": {"target": "_blank"}},
    )

    acoes = tables.TemplateColumn(
        template_code="""
            <div class="dropdown">
                <button class="btn btn-sm btn-secondary dropdown-toggle" type="button" id="dropdownMenuButton" data-bs-toggle="dropdown" aria-haspopup="true" aria-expanded="false">
                    Opções
                </button>
                <div class="dropdown-menu" aria-labelledby="dropdownMenuButton{{ record.pk }}">
                    <a class="dropdown-item" href="{% url 'home:livro02_detail' record.pk %}">Abrir</a>
                    <a class="dropdown-item" href="{% url 'home:livro02_texto' record.pk %}">Abrir Ficha</a>
                    <a class="dropdown-item" href="{% url 'home:livro04_imovel' record.pk %}">Abrir Imóvel (Livro04)</a>
                </div>
            </div>
            """,
        verbose_name="Ações",
        orderable=False,
    )

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        counter = itertools.count(start=1)
        for record in self.data:
            record.counter = next(counter)
        # self.base_columns["imovel"].verbose_name = "Imovel"

    def count_records(self):
        return len(self.data)

    class Meta:
        model = Livro04
        attrs = {
            "class": "table table-hover table-striped table-bordered no-footer nowrap",
        }
        empty_text = "Nenhum imóvel encontrado"
        order_by = ["-numero"]
        fields = (
            "counter",
            "tipo",
            "numero",
            "cartorio",
            "data_abertura",
            "classe",
            "municipio",
            "criado_em",
        )


class PedidoPartesTable(tables.Table):
    counter = TemplateColumn(
        template_code="{{ record.counter }}",
        verbose_name="#",
        orderable=False,
    )
    nome = tables.Column(verbose_name="Nome")
    tipo = tables.Column(verbose_name="Tipo")
    cpf = tables.Column(verbose_name="CPF")
    cnpj = tables.Column(verbose_name="CNPJ")
    telefone = tables.Column(verbose_name="Telefone")
    email = tables.Column(verbose_name="E-mail")
    endereco = tables.Column(verbose_name="Endereço")
    cidade = tables.Column(verbose_name="Cidade")
    uf = tables.Column(verbose_name="UF")
    cep = tables.Column(verbose_name="CEP")
    bairro = tables.Column(verbose_name="Bairro")

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        counter = itertools.count(start=1)
        for record in self.data:
            record.counter = next(counter)


class ProtocoloAndamentosTable(tables.Table):
    counter = tables.TemplateColumn(
        template_code="{{ record.counter }}",
        verbose_name="#",
        orderable=False,
    )

    tipo_andamento = tables.TemplateColumn(
        template_code="""
                        <a href="{% url 'home:andamento_detail' pk=record.pk %}" target="_blank">
                            <span class="{{ record.status_display.class }}">
                                {{ record.status_display.text }}
                            </span>
                        </a>
                    """,
        verbose_name="Tipo de Andamento",
        orderable=False,
    )

    colaborador_destino = tables.Column(
        accessor="colaborador_destino",
        verbose_name="Encaminhado Para",
        orderable=True,
        empty_values=(),
        linkify=lambda record: (
            record.colaborador_destino.get_distribuidos_url()
            if record.colaborador_destino
            else None
        ),
    )

    arquivo_assinado = tables.TemplateColumn(
        template_code="""
            {% if record.arquivo_assinado %}
                <a href="{{ record.arquivo_assinado.url }}" download>
                    <i class="fa-regular fa-file-pdf f-22"></i>
                </a>
            {% endif %}
        """,
        verbose_name="Arquivo",
        orderable=False,
    )

    def render_andamento_ativo(self, value):
        if str(value) != "S":
            return format_html('<span class="badge bg-danger">Não</span>')
        return "Sim"

    def render_colaborador_destino(self, record):
        return record.colaborador_destino or record.colaborador

    def count_records(self):
        return Decimal(len(self.data))

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        for index, record in enumerate(self.data, 1):
            record.counter = index

    class Meta:
        model = Livro01Andamento
        order_by = ["-data"]
        attrs = {
            "class": "table table-hover table-striped table-bordered no-footer nowrap",
        }
        empty_text = "Nenhum registro encontrado"
        fields = (
            "counter",
            "andamento_ativo",
            "data",
            "tipo_andamento",
            "colaborador",
            "colaborador_destino",
            "arquivo_assinado",
        )


class ProtocoloAndamentosTableExport(ProtocoloAndamentosTable):
    """Herda de ProtocoloAndamentosTable e adiciona o campo "texto" ao final da tabela."""

    class Meta(Livro01AndamentoTable.Meta):
        fields = (*ProtocoloAndamentosTable.Meta.fields, "texto")


# class FinanceiroTable(FinanceiroColaboradorTable):
# descricao = tables.LinkColumn(
#     "home:financeiro_detalhe",
#     args=[A("pk")],
#     attrs={"a": {"class": "link"}},
# )

# pedido = tables.Column(verbose_name="Protocolo")
# # pedido_certidao_id = tables.Column(verbose_name="Pedido Certidão")
# numero_pedido_certidao = tables.Column(verbose_name="Pedido Certidão")
# data_transacao = tables.Column(verbose_name="Data")
# tipo_operacao_financeira = tables.Column(verbose_name="Operação")
# tipo_transacao = tables.Column(verbose_name="Transação")
# valor_transacao = tables.Column(verbose_name="Valor")
# # colaborador_confirmado = tables.Column(verbose_name="Confirmado por")

# acoes = tables.TemplateColumn(
#     template_code="""
#         <div class="dropdown">
#             <a class="text-blue" id="dropdownMenuButton" data-bs-toggle="dropdown" aria-haspopup="true" aria-expanded="false">
#                         Opções &emsp;<i class="fa fa-angle-down" aria-hidden="true ms-1"></i>
#                     </a>
#             <div class="dropdown-menu" aria-labelledby="dropdownMenuButton{{ record.pk }}">
#                 {% if record.colaborador_confirmado == None %}
#                     <a class="dropdown-item btn btn-primary text-white" href="{% url 'home:caixa_editar' pk=record.pk %}"><i class='fas fa-edit'></i>Editar</a>
#                     <a class="dropdown-item btn btn-danger text-white" href="{% url 'home:caixa_cancelar' pk=record.pk %}"><i class="fas fa-cancel"></i>Cancelar</a>
#                 {% endif %}

#                 <a class="dropdown-item btn btn-info text-white" href="{% url 'home:financeiro_recibo_print' record.pk %}" target="_blank"><i class="icon feather icon-paperclip"></i>Imprimir Recibo</a>
#                 <a class="dropdown-item btn btn-success text-dark" href="#"><i class="icon feather icon-paperclip"></i>Anexar arquivo</a>

#                 <!-- Adicione mais links de ação conforme necessário -->
#             </div>
#         </div>
#         """,
#     verbose_name="Ações",
#     orderable=False,
# )

# ativo = tables.Column(verbose_name="Ativo")

# def render_ativo(self, value):
#     if str(value) != "Sim":
#         return format_html('<span class="badge bg-danger">Não</span>')
#     return "Sim"

# def render_pedido(self, record):
#     return record.pedido.protocolo if record.pedido else ""

# def render_data_transacao(self, record):
#     return record.data_transacao.strftime(settings.DATE_FORMAT_STR) if record.data_transacao else ""

# def __init__(self, *args, **kwargs) -> None:
#     super().__init__(*args, **kwargs)

# class Meta:
#     model = Financeiro
#     # template_name = "django_tables2/bootstrap.html"
#     order_by = ["-data_transacao"]
#     attrs = {
#     "class": "table table-hover table-striped table-bordered no-footer nowrap"
# }
#     empty_text = "Nenhum registro encontrado"
#     fields = (
#         "ativo",
#         "acoes",
#         "data_transacao",
#         "pedido",
#         # "pedido_certidao_id",
#         # numero_pedido_certidao",
#         "valor_transacao",
#         "descricao",
#         "tipo_operacao_financeira",
#         "tipo_transacao",
#         "colaborador",
#         "colaborador_confirmado",
#         # "acoes",
#     )


class EventTable(tables.Table):
    counter = tables.TemplateColumn(
        template_code="{{ record.counter }}",
        verbose_name="#",
        orderable=False,
    )

    title = tables.LinkColumn(
        "home:event-detail",
        args=[A("pk")],
        attrs={"a": {"class": "link"}},
    )

    user_id = tables.Column(accessor="user__nome", verbose_name="Colaborador")
    auth_user_id = tables.Column(
        accessor="auth_user__nome",
        verbose_name="Destinatário",
    )

    numero = tables.Column(verbose_name="Número")

    start_time_checked = tables.DateTimeColumn(
        verbose_name="Leitura",
        format=settings.DATETIME_FORMAT,
    )
    end_time_checked = tables.DateTimeColumn(
        verbose_name="Finalizado",
        format=settings.DATETIME_FORMAT,
    )

    # # protocolo = LinkColumn(accessor="pedido__protocolo", verbose_name="Protocolo")
    # protocolo = tables.LinkColumn(
    #     "home:protocolo_detail",
    #     accessor="pedido.protocolo",
    #     args=[tables.A("pedido.protocolo.pk")],
    #     verbose_name="Protocolo",
    #     orderable=True,
    #     attrs={"a": {"target": "_blank"}},
    # )

    # # # suas outras colunas
    # # numero_pedido_certidao = tables.LinkColumn(
    # #     "home:pedido_certidao_detalhes",
    # #     args=[tables.A("numero_pedido_certidao")],
    # #     verbose_name="PedidoCertidao",
    # # )

    # numero_pedido_certidao = tables.LinkColumn(
    #     "home:pedido_certidao_detalhes_numero_certidao",
    #     args=[tables.A("numero_pedido_certidao")],
    #     verbose_name="PedidoCertidao",
    # )

    # # pedido_certidao_id = tables.Column(verbose_name="Certidão")
    # # numero_pedido_certidao = tables.Column(verbose_name="Pedido de Certidão")

    # data_transacao = tables.DateTimeColumn(verbose_name="Data", format=settings.DATETIME_FORMAT)
    # tipo_operacao_financeira = tables.Column(verbose_name="Operação")
    # tipo_transacao = tables.Column(verbose_name="Transação")
    # # Coluna para 'valor_transacao' com rodapé que soma todos os valores da coluna e formatação monetária
    # valor_transacao = tables.Column(
    #     verbose_name="Valor",
    #     footer=lambda table: format_currency(
    #         sum(x.valor_transacao for x in table.data if hasattr(x, "valor_transacao")),
    #     ),
    #     accessor="valor_transacao",
    #     attrs={"td": {"class": "currency"}},
    # )
    # # colaborador_confirmado = tables.Column(verbose_name="Confirmado por")

    # acoes = tables.TemplateColumn(
    #     template_code="""
    #         <div class="dropdown">
    #             <a class="text-blue" id="dropdownMenuButton" data-bs-toggle="dropdown" aria-haspopup="true" aria-expanded="false" href="#" title="opções">
    #             <i class="fa fa-angle-down" aria-hidden="true"  ></i>
    #             </a>
    #             <div class="dropdown-menu" aria-labelledby="dropdownMenuButton{{ record.pk }}">
    #                 {% if record.colaborador_confirmado == None %}
    #                     <a class="dropdown-item text-primary" href="{% url 'home:caixa_editar' pk=record.pk %}"><i class='fas fa-edit'></i> Editar</a>
    #                     <a class="dropdown-item text-danger" href="{% url 'home:caixa_cancelar' pk=record.pk %}"><i class="fas fa-times"></i> Cancelar</a>
    #                 {% endif %}
    #                 <a class="dropdown-item text-info" href="{% url 'home:financeiro_recibo_print' record.pk %}" target="_blank"><i class="icon feather icon-printer"></i> Imprimir Recibo</a>
    #                 <a class="dropdown-item text-success" href="#"><i class="icon feather icon-paperclip"></i> Anexar arquivo</a>
    #             </div>
    #         </div>
    #         """,
    #     verbose_name="Ações",
    #     orderable=False,
    # )

    # ativo = tables.BooleanColumn(verbose_name="Ativo")

    # def render_ativo(self, value):
    #     if str(value) != "Sim":
    #         return format_html('<span class="badge bg-danger">Não</span>')
    #     return "Sim"

    # # def render_data_transacao(self, record):
    # #     return record.data_transacao.strftime(settings.SHORT_DATETIME_FORMAT_STR) if record.data_transacao else ""

    def count_records(self):
        return Decimal(len(self.data))

    # def render_tipo_transacao(self, value):
    #     if value == "Receita":
    #         return format_html('<span style="color: green;">{}</span>', value)
    #     elif value == "Despesa":
    #         return format_html('<span style="color: red;">{}</span>', value)
    #     return value

    # def render_valor_transacao(self, value):
    #     # Formata o valor como moeda para exibição na tabela
    #     formatted_value = format_currency(value)
    #     # Aplica a classe CSS 'negative' se o valor for negativo
    #     if value < 0:
    #         return format_html('<span style="color: red;">{}</span>', formatted_value)
    #     return formatted_value

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        for index, record in enumerate(self.data, 1):
            record.counter = index

    class Meta:
        model = Event
        order_by = ["-start_time"]
        attrs = {
            "class": "table table-hover table-striped table-bordered dataTable no-footer",
        }
        empty_text = "Nenhum registro encontrado"
        fields = (
            "counter",
            "origem",
            "numero",
            "start_time",
            "end_time",
            "start_time_checked",
            "end_time_checked",
            "user_id",
            "auth_user_id",
            "title",
            "description",
        )


class FinanceiroTable(tables.Table):
    counter = tables.TemplateColumn(
        template_code="{{ record.counter }}",
        verbose_name="#",
        orderable=False,
    )
    descricao = tables.LinkColumn(
        "home:financeiro_detalhe",
        args=[A("pk")],
        attrs={"a": {"class": "link"}},
    )

    # protocolo = LinkColumn(accessor="pedido__protocolo", verbose_name="Protocolo")
    protocolo = tables.LinkColumn(
        "home:protocolo_detail",
        accessor="pedido__protocolo",
        args=[tables.A("pedido__protocolo__pk")],
        verbose_name="Protocolo",
        orderable=True,
        attrs={"a": {"target": "_blank"}},
    )

    # # suas outras colunas
    # numero_pedido_certidao = tables.LinkColumn(
    #     "home:pedido_certidao_detalhes",
    #     args=[tables.A("numero_pedido_certidao")],
    #     verbose_name="PedidoCertidao",
    # )

    numero_pedido_certidao = tables.LinkColumn(
        "home:pedido_certidao_detalhes_numero_certidao",
        args=[tables.A("numero_pedido_certidao")],
        verbose_name="PedidoCertidao",
    )

    # pedido_certidao_id = tables.Column(verbose_name="Certidão")
    # numero_pedido_certidao = tables.Column(verbose_name="Pedido de Certidão")

    data_transacao = tables.DateTimeColumn(
        verbose_name="Data",
        format=settings.DATETIME_FORMAT,
    )
    tipo_operacao_financeira = tables.Column(verbose_name="Operação")
    tipo_transacao = tables.Column(verbose_name="Transação")
    # Coluna para 'valor_transacao' com rodapé que soma todos os valores da coluna e formatação monetária
    valor_transacao = tables.Column(
        verbose_name="Valor",
        footer=lambda table: format_currency(
            sum(x.valor_transacao for x in table.data if hasattr(x, "valor_transacao")),
        ),
        accessor="valor_transacao",
        attrs={"td": {"class": "currency"}},
    )
    # colaborador_confirmado = tables.Column(verbose_name="Confirmado por")

    acoes = tables.TemplateColumn(
        template_code="""
            <div class="dropdown">
                <a class="text-blue" id="dropdownMenuButton" data-bs-toggle="dropdown" aria-haspopup="true" aria-expanded="false" href="#" title="opções">
                    Ver&emsp;<i class="icon feather icon-chevrons-down"></i>

                </a>
                <div class="dropdown-menu" aria-labelledby="dropdownMenuButton{{ record.pk }}">
                    {% if record.colaborador_confirmado == None %}
                        <a class="dropdown-item text-primary" href="{% url 'home:caixa_editar' pk=record.pk %}">
                            <i class='fas fa-edit'></i> Editar
                        </a>
                        <a class="dropdown-item text-danger" href="{% url 'home:caixa_cancelar' pk=record.pk %}">
                            <i class="fas fa-times"></i> Cancelar
                        </a>
                    {% endif %}
                    <a class="dropdown-item text-success" href="#">
                        <i class="icon feather icon-paperclip"></i> Anexar arquivo
                    </a>
                </div>
            </div>
            """,
        verbose_name="Ações",
        orderable=False,
    )

    recibo = tables.TemplateColumn(
        template_code="""
            <div class="text-center">
                <a href="{% url 'home:financeiro_recibo_print' record.pk %}"
                    target="_blank">
                    <i class="icon feather icon-printer"></i>
                </a>
            </div>
            """,
        verbose_name="Recibo",
        orderable=False,
    )

    completo = tables.TemplateColumn(
        template_code="""
            <div class="text-center">
                <a href="{% url 'home:financeiro_recibo_print' record.pk %}"
                    target="_blank">
                    <i class="icon feather icon-bookmark"></i>
                </a>
            </div>
            """,
        verbose_name="Completo",
        orderable=False,
    )

    ativo = tables.BooleanColumn(verbose_name="Ativo")

    def render_ativo(self, value):
        if str(value) != "Sim":
            return format_html('<span class="badge bg-danger">Não</span>')
        return "Sim"

    # def render_data_transacao(self, record):
    #     return record.data_transacao.strftime(settings.SHORT_DATETIME_FORMAT_STR) if record.data_transacao else ""

    def count_records(self):
        return Decimal(len(self.data))

    def render_tipo_transacao(self, value):
        if value == "Receita":
            return format_html('<span style="color: green;">{}</span>', value)
        elif value == "Despesa":
            return format_html('<span style="color: red;">{}</span>', value)
        return value

    def render_valor_transacao(self, value):
        # Formata o valor como moeda para exibição na tabela
        formatted_value = format_currency(value)
        # Aplica a classe CSS 'negative' se o valor for negativo
        if value < 0:
            return format_html('<span style="color: red;">{}</span>', formatted_value)
        return formatted_value

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        for index, record in enumerate(self.data, 1):
            record.counter = index

    class Meta:
        model = Financeiro
        # template_name = "django_tables2/bootstrap.html"
        order_by = ["-data_transacao"]
        attrs = {
            "class": "table table-hover table-striped table-bordered no-footer nowrap",
        }
        empty_text = "Nenhum registro encontrado"
        fields = (
            "counter",
            "acoes",
            "ativo",
            "recibo",
            "completo",
            "data_transacao",
            "protocolo",
            # "pedido_certidao_id",
            "numero_pedido_certidao",
            "valor_transacao",
            "descricao",
            "tipo_operacao_financeira",
            "tipo_transacao",
            "colaborador",
            "colaborador_confirmado",
        )


class FinanceiroTableExport(FinanceiroTable):
    class Meta(FinanceiroTable.Meta):
        exclude = ("acoes", "recibo", "completo")
        fields = (
            "counter",
            "data_transacao",
            "protocolo",
            "numero_pedido_certidao",
            "valor_transacao",
            "descricao",
            "tipo_operacao_financeira",
            "tipo_transacao",
            "colaborador",
        )


class EventColaboradorTable(EventTable):
    class Meta(EventTable.Meta):
        # exclude = ("colaborador_confirmado",)
        pass

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)


class FinanceiroColaboradorTable(FinanceiroTable):
    class Meta(FinanceiroTable.Meta):
        exclude = ("colaborador_confirmado",)

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)


class SeloTable(tables.Table):
    # def __init__(self, *args, **kwargs) -> None:
    #     super().__init__(*args, **kwargs)

    # class Meta:
    #     model = SeloEletronico
    #     attrs = {
    #        "class": "table table-hover table-striped table-bordered no-footer nowrap"
    #    }
    #     empty_text = "Nenhum registro encontrado"
    #     exclude = ("criador_por_id",)

    codigo_sequencial_unico = tables.Column(verbose_name="Número Selo", orderable=True)
    codigo_de_seguranca = tables.Column(
        verbose_name="Código Segurança",
        orderable=False,
    )
    utilizado_em = tables.Column(verbose_name="Utilizado", orderable=True)
    cancelado_em = tables.Column(verbose_name="Cancelado", orderable=True)
    selo_de_consulta = tables.Column(verbose_name="Consulta", orderable=True)
    certidao_id = tables.Column(verbose_name="Ped. Certidão", orderable=True)
    numero_protocolo = tables.Column(verbose_name="Protocolo", orderable=True)

    # opcoes = tables.TemplateColumn(
    #     "<a class='badge bg-danger' href=\"{% url 'home:limpar_selo' numero_selo=record.codigo_sequencial_unico %}\"><i class='icon feather icon-copy m-0'></i> Limpar Selo</a>",
    #     orderable=False,
    #     verbose_name="Ação",
    # )

    @staticmethod
    def render_codigo_de_seguranca(record) -> str:
        return formatar_codigo_seguranca_mg(record.codigo_de_seguranca, ".")

    @staticmethod
    def render_certidao_id(record) -> str:
        if record.numero_pedido:
            url = reverse(
                "home:pedido_certidao_listar_certidoes_pedido",
                args=[record.numero_pedido_id],
            )
            return format_html(
                '<a href="{}">{}</a>',
                url,
                formatar_protocolo(record.numero_pedido),
            )
        return None

    @staticmethod
    def render_numero_protocolo(record) -> str:
        return record.protocolo

    @staticmethod
    def render_utilizado_em(record) -> str:
        return record.utilizado_em.strftime("%d/%m/%y")

    class Meta:
        model = SeloEletronico
        attrs = {
            "class": "table table-hover table-striped table-bordered no-footer nowrap",
        }
        empty_text = "Nenhum registro encontrado"
        fields = (
            "utilizado_em",
            "codigo_sequencial_unico",
            "codigo_de_seguranca",
            "selo_de_consulta",
            "certidao_id",
            "numero_protocolo",
            "certidao",
            "pedido_item",
            "cancelado_em",
            # "opcoes",
        )


class Livro05Table(tables.Table):
    nome = tables.LinkColumn(
        "home:livro05_detail",
        args=[tables.A("pk")],
        verbose_name="nome",
    )

    documento_mascarado = tables.Column(verbose_name="Documento", orderable=False)

    detalhes_pessoa = tables.TemplateColumn(
        template_code="""
                        <a class="btn-sm btn-secondary"
                        href="{{ record.get_buscar_pessoal_url }}">
                        Detalhes</a>
                      """,
        orderable=False,
        verbose_name="Pessoa",
    )

    class Meta:
        model = Livro05
        attrs = {
            "class": "table table-hover table-striped table-bordered no-footer nowrap",
        }
        empty_text = "Nenhum registro encontrado"
        fields = (
            "nome",
            "documento_mascarado",
            # "telefone",
            "data_nascimento",
            "sexo",
            "observacoes",
            "quantidade_de_vinculos",
            "detalhes_pessoa",
        )


class AndamentoTable(TabelaBase):
    # editar = tables.TemplateColumn(
    #     "<a class='btn btn-sm btn-outline-success text-dark' href=\"{% url 'home:pedido_certidao_andamento_editar' record.id %}\"> <i class='fas fa-edit'></i> Editar</a>",
    #     orderable=False,
    #     verbose_name="Ação",
    # )
    acoes = tables.TemplateColumn(
        template_code="""
            <div class="d-flex flex-wrap align-items-center">
                {% if record.ativo %}
                    <a class='btn btn-sm btn-outline-success text-dark' href=\"{% url 'home:pedido_certidao_andamento_editar' record.id %}\"> <i class='fas fa-edit'></i> Editar&emsp;</a>
                {% else %}
                    <a class='btn btn-sm btn-outline-info text-dark' href=\"{% url 'home:pedido_certidao_andamento_editar' record.id %}\"> <i class='fas fa-info'></i>Visualizar</a>
                {% endif %}

                {% if record.ativo %}
                    <a class='btn btn-sm btn-outline-danger text-dark' href=\"{% url 'home:pedido_certidao_andamento_desativar' record.id %}\"> <i class='fas fa-trash'></i>Desativar</a>
                {% else %}
                    <a class='btn btn-sm btn-outline-info text-dark' href=\"{% url 'home:pedido_certidao_andamento_ativar' record.id %}\"> <i class='fas fa-info'></i>&emsp;Reativar</a>
                {% endif %}
            </div>
        """,
        orderable=False,
        verbose_name="Opções",
    )

    # {% if record.descricao != '<p>&nbsp;</p>' %}
    certidao = tables.TemplateColumn(
        """
        {% if record.certidao %}
            <a class="btn btn-sm btn-info" href="{% url 'home:pedido_certidao_andamento_texto_print' record.id %}" target="_blank"> <i class="fas fa-print"></i> Certidão</a>
        {% endif %}
        """,
        orderable=False,
        verbose_name="Emissão",
    )

    tipo_andamento = tables.TemplateColumn(
        template_code="""
            <span class="
                {% if not record.ativo %}
                    bg-danger font-weight-bold mx-3 text-white
                {% elif record.get_andamento_certidao_exigencia %}
                    bg-warning font-weight-bold mx-3 text-dark
                {% elif record.get_andamento_certidao_cancelado %}
                    bg-danger font-weight-bold mx-3 text-white
                {% elif record.get_andamento_certidao_pronta %}
                    bg-success text-white mx-3 text-dark
                {% else %}
                    bg-white font-weight-bold mx-3 text-dark
                {% endif %}">

                &emsp;{{ record.tipo_andamento }}&emsp;
            </span>
        """,
        verbose_name="Tipo andamento",
        orderable=True,
    )

    class Meta:
        model = PedidoCertidaoAndamento
        paginate = {"per_page": 5}
        fields = (
            "ativo",
            "tipo_andamento",
            "data_hora",
            "criado_por",
            "colaborador_destino",
            "acoes",
            "certidao",
        )


class PedidoCertidaoTable(TabelaBase):
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)

    selecionar = tables.CheckBoxColumn(accessor="numero_pedido", orderable=False)

    certidao_entregue = tables.Column(
        accessor="certidao_entregue",
        verbose_name="Entregue",
        orderable=False,
        empty_values=(),
    )

    @staticmethod
    def render_certidao_entregue(record) -> str:
        if record.certidao_entregue:
            status_color = "theme-bg"
            status_text = "Sim"
        else:
            status_color = "bg-c-red"
            status_text = "Não"

        return format_html(
            '<div style="display: flex; align-items: center;">'
            '<span class="{} d-block rounded-circle" style="width:10px; height:10px;"></span>'
            "<span>{}</span>"
            "</div>",
            status_color,
            status_text,
        )

    opcoes = tables.TemplateColumn(
        """
            {% if record.pk %}
                <a  class="m-r-10
                        {% if record.cancelado %} text-white
                        {% elif record.andamento_certidao_entregue %} text-primary
                        {% elif record.andamento_certidao_pronta %}  text-success
                        {% elif record.andamento_certidao_exigencia %} text-warning
                        {% else %} text-dark
                        {% endif %}"
                    title="Ver Andamentos"
                    data-toggle="tooltip"
                    data-placement="top"
                    href="{% url 'home:pedido_certidao_andamentos' record.pk %}" target='_blank'>
                    <i class='fas fa-history'></i>
                </a>
            {% else %}
                <span class="text-dark m-r-10">-</span>
            {% endif %}

            <a  class="m-r-10 text-dark"
                href="{% url 'home:pedido_certidao_recibo_do_caixa' record.pk %}"
                target="_blank"
                title="Imprimir Comprovante"
                data-toggle="tooltip"
                data-placement="top">
                <i class="icon feather icon-printer"></i>
            </a>

            <a  class="m-r-10 text-dark"
                href="{% url 'home:pedido_certidao_emitir_etiqueta' record.pk %}"
                target="_blank"
                title="Emitir Etiqueta"
                data-toggle="tooltip"
                data-placement="top">
                <i class="icon feather icon-image"></i>
            </a>
            <a  class="m-r-10 text-dark"
                href="{% url 'home:pedido_certidao_selar' record.pk %}"
                target="_blank"
                title="Selar"
                data-toggle="tooltip"
                data-placement="top">
                <i class="icon feather icon-award"></i>
            </a>

            """,
        orderable=False,
        verbose_name="Opções",
    )

    numero_pedido = tables.TemplateColumn(
        template_code="""
            {% if record.cancelado %}
                <span class="badge btn-danger f-14 text-white text-center">
                    <a href="{% url 'home:pedido_certidao_detalhes' record.pk %}" style="color: white;">{{ record.numero_pedido }}</a>
                </span>
            {% elif record.exigencia %}
                <span class="badge btn-warning f-14 text-dark text-center">
                    <a href="{% url 'home:pedido_certidao_detalhes' record.pk %}" style="color: dark;">{{ record.numero_pedido }}</a>
                </span>
            {% else %}
                <a href="{% url 'home:pedido_certidao_detalhes' record.pk %}">{{ record.numero_pedido }}</a>
            {% endif %}
            """,
        verbose_name="Número",
    )

    andamento_pedido_confirmado = tables.TemplateColumn(
        template_code="""
            {% if record.cancelado %}
                &emsp;
            {% else %}
                {% if record.andamento_pedido_confirmado %}
                    <div style="display: flex; align-items: center;">
                        <span class="theme-bg d-block rounded-circle"
                                style="width:10px; height:10px; margin-right: 5px;">
                            </span>
                        <a title="Receber - Clique para confirmar o recebimento do Pedido na sua filas"
                            data-toggle="tooltip"
                            data-placement="top"
                            href="{% url 'home:pedido_certidao_confirmar_recebimento' record.pk %}">
                            <span class="text-success">Sim</span>
                        </a>
                    </div>
                {% else %}
                    <div style="display: flex; align-items: center;">
                        <span class="bg-c-red d-block rounded-circle"
                            style="width:10px; height:10px; margin-right: 5px;">
                        </span>
                        <a title="Receber - Clique para confirmar o recebimento do Pedido na sua filas"
                            data-toggle="tooltip"
                            data-placement="top"
                            href="{% url 'home:pedido_certidao_confirmar_recebimento' record.pk %}">
                            <span class="text-secondary">Não</span>
                        </a>
                    </div>
                {% endif %}
            {% endif %}
            """,
        verbose_name="Recebido",
    )

    num_imoveis = tables.Column(
        verbose_name=format_html('<span class="fa fa-home"></span>'),
        empty_values=(),
    )
    num_pessoas = tables.Column(
        verbose_name=format_html('<span class="fa fa-users"></span>'),
        empty_values=(),
    )

    num_certidoes = tables.Column(
        verbose_name=format_html('<span class="fa fa-file"></span>'),
        empty_values=(),
    )

    num_selos = tables.Column(
        verbose_name=format_html('<span class="feather icon-award"></span>'),
        empty_values=(),
    )

    origem_formatada = tables.Column(verbose_name="Origem", empty_values=())
    total_pedido = tables.Column(verbose_name="R$ Total", empty_values=())
    valor_total_caixa = tables.Column(verbose_name="R$ Caixa", empty_values=())
    apresentante = tables.Column(
        accessor="apresentante__nome",
        verbose_name="Apresentante",
    )
    data_entrada = tables.DateColumn(
        verbose_name="Entrada",
        # format=settings.SHORT_DATE_FORMAT,
        format=settings.DATETIME_FORMAT,
    )
    data_prazo_final = tables.DateColumn(
        verbose_name="Prazo Final",
        format=settings.SHORT_DATE_FORMAT,
    )

    ultimo_andamento_grupo_fase_cartorio = tables.TemplateColumn(
        template_code="""
        {{ record.ultimo_andamento_grupo_fase_cartorio|safe }}
        """,
        verbose_name="Fase Atual",
    )

    @staticmethod
    def render_apresentante(record: "PedidoCertidao") -> str:
        # return str(record.apresentante.nome)[:30] + str(record.criado_por_id)
        criado = (
            f"Criado por: {record.criado_por.username.capitalize()} - {record.origem}"
            if record.criado_por
            else ""
        )

        return format_html(
            "<div>{}</div><div><small>{}</small></div>",
            str(record.apresentante.nome)[:30],
            criado,
        )

    @staticmethod
    def render_origem_formatada(record) -> str:
        url = record.get_origem_url() if record else None
        return format_html(
            '<a href="{}" target="_blank">{}</a>',
            url,
            record.origem_formatada,
        )

    @staticmethod
    def render_num_imoveis(record) -> str:
        url = reverse("home:pedido_certidao_imoveis_listar", args=[record.pk])
        return format_html('<a href="{}">{}</a>', url, record.imoveis.count())

    @staticmethod
    def render_num_pessoas(record) -> str:
        url = reverse("home:pedido_certidao_pessoas_list", args=[record.pk])
        return format_html('<a href="{}">{}</a>', url, record.pessoas.count())

    @staticmethod
    def render_num_certidoes(record) -> str:
        url = reverse("home:pedido_certidao_listar_certidoes_pedido", args=[record.pk])
        return format_html('<a href="{}">{}</a>', url, record.quantidade_certidoes)

    @staticmethod
    def render_num_selos(record) -> str:
        url = reverse("home:certidoes_listar_selo", args=[record.numero_pedido])
        return format_html('<a href="{}">{}</a>', url, record.quantidade_selos)

    @staticmethod
    def render_ultimo_andamento_grupo_fase_cartorio(record) -> str:
        (
            descricao,
            colaborador,
            data,
        ) = record.ultimo_andamento_grupo_fase_cartorio

        colaborador_formatado = colaborador + " - " + data

        return format_html(
            "<div>{}</div><div>{}</div>",
            descricao,
            colaborador_formatado,
        )

    def render_data_selado(self, record) -> str:
        if record.data_selado:
            return record.data_selado.strftime(settings.SHORT_DATE_FORMAT_STR)
        url = reverse(
            "home:pedido_certidao_gerar_selo_pedido_certidao",
            args=[record.pk, record.origem_id],
        )

        if self.request:
            user = self.request.user
            if user.gerar_selo_certidao:
                return format_html(
                    '<a href="{}"><i class="icon feather icon-check-circle f-14"></i> {}</a>',
                    url,
                    "Selar",
                )
            else:
                return ""
        else:
            return ""

    def render_valor_total_caixa(self, record, value):
        # Função para formatar o valor com duas casas decimais
        def formatar_valor(valor) -> str:
            return round(Decimal(valor), 2)

        valor_total_caixa_formatado = formatar_valor(record.valor_total_caixa)
        total_pedido_formatado = formatar_valor(record.total_pedido)

        if valor_total_caixa_formatado != total_pedido_formatado:
            valor_formatado = f"{valor_total_caixa_formatado:.2f}".replace(".", ",")
            return format_html(
                '<span class="badge bg-danger">{}</span>',
                valor_formatado,
            )

        return f"{formatar_valor(value):.2f}".replace(".", ",")

    class Meta:
        model = PedidoCertidao
        order_by = ["-data_entrada"]
        fields = (
            "selecionar",
            "andamento_pedido_confirmado",
            # "recibo",
            "numero_pedido",
            "opcoes",
            "origem_formatada",
            "certidao_entregue",
            "apresentante",
            "data_entrada",
            "num_imoveis",
            "num_pessoas",
            "num_certidoes",
            "num_selos",
            "ultimo_andamento_grupo_fase_cartorio",
            "total_pedido",
            "valor_total_caixa",
        )


class ImovelTable(TabelaBase):
    opcoes = tables.TemplateColumn(
        template_code="""
        <div>
            <a class="btn btn-sm btn-outline-success text-dark" href="{{ record.get_update_url }}">
                <i class="icon feather icon-edit"></i>&emsp;Editar&emsp;
            </a>
            <a class="btn btn-sm btn-outline-danger"
                            href="{{ record.get_delete_url }}">
                            <i class="icon feather icon-trash"></i> Excluir
                        </a>

        </div>
        <div>
            <a class="btn btn-sm btn-primary" href="{% url 'home:pedido_certidao_listar_certidoes_pedido' record.pedido.id %}" target="_blank">
                <i class="fas fa-print"></i> Certidão
            </a>
            <a class="btn btn-sm btn-outline-secondary" href="{{ record.get_registro_url }}">
                <i class="icon feather icon-info"></i>Acessar
            </a>
        </div>
    """,
        orderable=False,
        verbose_name="Opções",
    )

    # imovel = tables.TemplateColumn(
    #     template_code="""
    #                     <a class="btn-sm btn-secondary" href="{{ record.get_registro_url }}">Acessar</a>
    #                   """,
    #     orderable=False,
    #     verbose_name="Imóvel/Registro Auxiliar",
    # )

    quantidade_certidoes = tables.Column(
        empty_values=(),
        verbose_name="Qtd de Certidões",
    )

    anotacoes = tables.TemplateColumn(
        '<span data-toggle="tooltip" data-placement="top" title="{{ record.complemento }} {{ record.descricao }} {{ record.anotacoes }}">Ver detalhes</span>',
        orderable=False,
        verbose_name="Anotações",
    )

    def render_quantidade_certidoes(self, record):
        return Certidao.objects.filter(imovel=record).count()

    class Meta:
        model = PedidoCertidaoImovel
        paginate = {"per_page": 5}
        fields = (
            "numero_registro",
            "logradouro",
            "quadra",
            "lote",
            "municipio",
            "quantidade_certidoes",
            "anotacoes",
        )


class PedidoCertidaoPessoasTable(TabelaBase):
    quantidade_certidoes = tables.Column(
        empty_values=(),
        verbose_name="Qtd de Certidões",
    )

    anotacoes = tables.TemplateColumn(
        '<span data-toggle="tooltip" data-placement="top" title="{{ record.complemento }} {{ record.descricao }} {{ record.anotacoes }} ">Ver detalhes</span>',
        orderable=False,
        verbose_name="Anotações",
    )

    opcoes = tables.TemplateColumn(
        template_code="""
                      <div>
                        <a class="btn btn-sm btn-outline-success text-dark  "
                            href="{{ record.get_update_url }}">
                            <i class="icon feather icon-edit"></i>   Editar&emsp;
                        </a>

                        <a class="btn btn-sm btn-outline-danger"
                            href="{{ record.get_delete_url }}">
                            <i class="icon feather icon-trash"></i> Excluir
                        </a>
                      </div>
                      <div>
                          <a class="btn btn-sm btn-primary"
                              href="{% url "home:pedido_certidao_listar_certidoes_pedido" record.pedido.id %}">
                              <i class="fas fa-print"></i> Certidão
                          </a>

                          <a class="btn btn-sm btn-secondary"
                              href="{{ record.get_buscar_pessoal_url }}">
                              <i class="icon feather icon-info"></i> Busca
                          </a>
                      </div>
                      """,
        orderable=False,
        verbose_name="Opções",
    )

    def render_quantidade_certidoes(self, record):
        return Certidao.objects.filter(pessoa=record).count()

    class Meta:
        model = PedidoCertidaoPessoa
        paginate = {"per_page": 5}
        fields = (
            "nome",
            "tipo_documento",
            "documento",
            "quantidade_certidoes",
            "anotacoes",
            "opcoes",
            # "editar",
            # "certidao",
            # "remover",
        )


class PedidoCertidaoAndamentoTable(TabelaBase):
    editar = tables.TemplateColumn(
        "<a class='badge bg-secondary' href=\"{% url 'home:pedido_certidao_andamento_editar' record.pedido.id %}\"><i class='fas fa-edit'></i> Editar</a>",
        orderable=False,
        verbose_name="Ação",
    )

    class Meta:
        model = PedidoCertidaoAndamento
        fields = (
            "nome",
            "tipo_andamento",
            "criado_por",
            "colaborador_destino",
            "criado_em",
        )


class CertidaoImovelTable(TabelaBase):
    editar = tables.TemplateColumn(
        "<a class='badge bg-secondary' href=\"{% url 'home:pedido_certidao_imovel_certidao_editar' record.imovel.pedido.id record.id %}\"><i class='fas fa-edit'></i> Editar</a>",
        orderable=False,
        verbose_name="Ação",
    )

    class Meta:
        model = Certidao
        paginate = {"per_page": 5}
        fields = ("tipo", "data_emissao")


class PedidoCertidaoPessoaTable(TabelaBase):
    editar = tables.TemplateColumn(
        "<a class='badge bg-secondary' href=\"{% url 'home:pedido_certidao_pessoa_certidao_editar' record.pessoa.pedido_id record.pessoa_id record.id %}\">editar</a>",
        orderable=False,
        verbose_name="Ação",
    )

    nome = tables.Column(
        accessor="tipo__nome",
        verbose_name="Nome",
    )

    class Meta:
        model = Certidao
        paginate = {"per_page": 5}
        fields = ("nome", "editar")


class CertidaoAgrupadaTable(TabelaBase):
    nome = tables.Column(
        accessor="tipo_certidao__nome",
        verbose_name="Tipo de Certidão",
    )
    quantidade = tables.Column(
        verbose_name="Quantidade",
        footer=lambda table: table.total_quantidade(),
    )
    valor_total = tables.Column(
        empty_values=(),  # Isso garante que a coluna será processada mesmo para linhas sem dados
        verbose_name="Valor Total",
    )

    def total_quantidade(self):
        # Garantindo que a soma das quantidades seja calculada corretamente
        return sum(item.get("quantidade", 0) for item in self.data)

    def render_valor_total(self, record):
        # Apenas retorna o valor total de cada registro (que já é o total do grupo)
        return formatar_moeda(record.get("total", 0))

    class Meta:
        model = Certidao
        paginate = {"per_page": 5}
        fields = ("nome", "quantidade", "valor_total")


class CertidaoTable(TabelaBase):
    # valor = tables.Column(empty_values=(), verbose_name="Valor")

    acoes = tables.TemplateColumn(
        template_code="""
            <div class="d-flex flex-wrap align-items-center">
                <a class="btn btn-sm  btn-warning mx-1 my-1 text-dark" href="{{ record.get_update_url }}">
                    <i class="icon feather icon-edit d-none d-md-inline-block"></i> Alterar
                </a>

                <a class="btn btn-sm btn-danger mx-1 my-1" href="{{ record.get_delete_url }}">
                    <i class="icon feather icon-trash d-none d-md-inline-block"></i> Excluir
                </a>

                {% if record.pessoa %}
                    <a class="btn btn-sm btn-secondary mx-1 my-1" href="{{ record.pessoa.get_update_url }}">
                        <i class="icon feather icon-user d-none d-md-inline-block"></i> Ver Pessoa
                    </a>
                {% elif record.imovel %}
                    <a class="btn btn-sm btn-success mx-1 my-1 text-dark" href="{{ record.imovel.get_update_url }}">
                        <i class="icon feather icon-home d-none d-md-inline-block"></i> Ver Imóvel
                    </a>
                {% endif %}

                {% if record.get_selos %}
                    {% if record.pessoa %}
                        <a class="btn btn-sm btn-primary mx-1 my-1 text-white"
                            href="{% url "home:pedido_certidao_andamento_gerar_certidao_pessoa" pk=record.id %}" target="_blank">
                            <i class="icon feather icon-printer d-none d-md-inline-block"></i> Certidão
                    {% elif record.imovel %}
                        <a class="btn btn-sm btn-primary mx-1 my-1 text-white"
                            href="{% url "home:pedido_certidao_andamento_gerar_certidao_imovel" pk=record.id %}" target="_blank">
                            <i class="icon feather icon-printer d-none d-md-inline-block"></i> Certidão Imóvel
                    {% endif %}

                    </a>
                {% endif %}

            </div>
        """,
        orderable=False,
        verbose_name="Opções",
    )

    nome = tables.Column(empty_values=[], verbose_name="Certidão")

    def render_nome(self, record):
        nome_principal = escape(record.nome_com_codigo)
        nome_secundario = escape(record.qualificacao)
        # return f"{nome_principal} <br> <small>{nome_secundario}</small>"
        return mark_safe(f"{nome_principal} <br> <small>{nome_secundario}</small>")

    def render_total(self, record):
        conteudo_popover = (
            f"Emolumento Liquido: {formatar_moeda(record.emolumento_liquido_calculado)}<br>"
            f"Taxa Fiscal Judiciaria: {formatar_moeda(record.taxa_fiscal_judiciaria_calculada)}<br>"
            f"Recompe: {formatar_moeda(record.recompe_calculado)}<br>"
            f"Issqn: {formatar_moeda(record.issqn_calculado)}<br>"
            f"Tributação: {record.tributacao}<br>"
            # f"Prazo: {record.tipo_certidao.prazo_legal.valor} {self.tipo_certidao.prazo_legal.unidade}<br>"
        )

        # return (
        #     f'<span data-bs-toggle="popover" data-bs-html="true" title="Detalhes" '
        #     f'data-bs-content="{escape(conteudo_popover)}">{formatar_moeda(record.total)} '
        #     f'<i class="icon feather icon-info f-10 align-text-top"></i></span>'
        # )

        return mark_safe(
            '<span data-bs-toggle="popover" data-bs-html="true" title="Detalhes" '
            f'data-bs-content="{conteudo_popover}">{formatar_moeda(record.total)} '
            '<i class="icon feather icon-info f-10 align-text-top"></i></span>',
        )

    class Meta:
        model = Certidao
        paginate = {"per_page": 5}
        fields = (
            "nome",
            # "emolumento",
            # "taxa_fiscal_judiciaria",
            # "fundo_estado",
            # "issqn",
            "total",
            #  "data_emissao",
        )


class SelosTable(TabelaBase):
    # editar = tables.TemplateColumn(
    #     "<a class='badge bg-secondary' href=\"{% url 'home:pedido_certidao_selo_editar' record.pedido.id record.id %}\"><i class='fas fa-edit'></i> Editar</a>",
    #     orderable=False,
    #     verbose_name="Ação",
    # )
    def __init__(self, *args, **kwargs) -> None:
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)

    class Meta:
        model = SeloEletronico
        fields = ("codigo", "data_utilizacao")


class PedidoOnrTable(TabelaBase):
    def __init__(self, *args, **kwargs) -> None:
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)

    # Adiciona uma coluna para numeração das linhas
    contador = tables.Column(empty_values=(), orderable=False, verbose_name="#")

    # suas outras colunas
    numero_pedido = tables.LinkColumn(
        "home:pedido_certidao_detalhes",
        args=[tables.A("pk")],
        verbose_name="Pedido de Certidão",
    )

    # origem = tables.Column(accessor="origem.nome", verbose_name="Origem")
    num_imoveis = tables.Column(verbose_name="Imóveis", empty_values=())
    num_certidoes = tables.Column(verbose_name="Certidões", empty_values=())
    origem_formatada = tables.Column(verbose_name="Origem", empty_values=())

    # editar = tables.TemplateColumn(
    #     "<a class='' href=\"{% url 'home:detalhes_pedido' record.pk %}\"><i class='icon feather icon-eye f-16'></i> Visualizar</a>",
    #     orderable=False,
    #     verbose_name="Ação",
    # )

    nome = tables.Column(
        accessor="apresentante__nome",
        verbose_name="Apresentante",
    )

    def render_contador(self, value, record, bound_column):
        current_record_index = None

        for index, current_record in enumerate(self.data):
            if current_record == record:
                current_record_index = index
                break

        # Verifica se encontramos o registro
        if current_record_index is None:
            msg = "Registro não encontrado no conjunto de dados atual."
            raise ValueError(msg)

        # Calculando o índice global do registro
        return current_record_index + 1

    @staticmethod
    def render_origem_formatada(record) -> str:
        url = record.get_origem_url()
        return format_html('<a href="{}">{}</a>', url, record.origem_formatada)

    @staticmethod
    def render_num_imoveis(record) -> str:
        url = reverse("home:pedido_certidao_pedido_imoveis_listar", args=[record.pk])
        return format_html('<a href="{}">{}</a>', url, record.imoveis.count())

    # @staticmethod
    # def render_num_pessoas(record) -> str:
    #     url = reverse("home:pedido_certidao_pessoas_list", args=[record.pk])
    #     return format_html('<a href="{}">{}</a>', url, record.pessoas.count())

    @staticmethod
    def render_num_certidoes(record) -> str:
        url = reverse("home:pedido_certidao_listar_certidoes_pedido", args=[record.pk])
        return format_html('<a href="{}">{}</a>', url, record.quantidade_certidoes)

    @staticmethod
    def render_total_pedido(record) -> str:
        return format_html(
            '<a href="{}">{}</a>',
            record.get_absolute_url,
            formatar_moeda(record.total),
        )

    @staticmethod
    def render_data_entrada(record) -> str:
        return record.data_entrada.strftime("%a %d/%m/%y")

    class Meta:
        model = PedidoCertidao
        order_by = ["-data_entrada"]
        paginate = {"per_page": 5}
        fields = (
            "contador",
            "numero_pedido",
            "origem_formatada",
            "nome",
            "data_entrada",
            "num_imoveis",
            "num_certidoes",
        )


class PedidoCertidaoAnexoTable(tables.Table):
    class Meta:
        model = PedidoCertidaoAnexo
        fields = ("arquivo", "descricao", "pedido_certidao")


class ColaboradorTable(tables.Table):
    image = tables.TemplateColumn(
        template_code="""
            <img src="{{ record.image }}" class="img-radius img-fluid wid-30" width="50" height="50" />
        """,
        verbose_name="Foto",
        orderable=False,
    )

    nome = tables.TemplateColumn(
        template_code='<a href="{{ record.get_distribuidos_url }}">{{ record.nome }}</a>',
        verbose_name="Nome",
        orderable=True,
    )

    class Meta:
        model = Colaborador
        fields = (
            "image",
            "nome",
            "protocolos_em_aberto__count",
            "peso_protocolos_em_aberto",
        )
        order_by = ["nome"]
        attrs = {
            "class": "table table-striped table-bordered dataTable no-footer nowrap",
            "id": "simpletable",
        }
