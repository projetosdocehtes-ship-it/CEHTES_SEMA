import logging
from decimal import ROUND_HALF_UP, Decimal

import django_tables2 as tables
from django.db.models import Sum
from django.db.models.query import QuerySet
from django.urls import reverse
from django.utils.html import format_html
from django.utils.http import urlencode
from django.utils.safestring import mark_safe

from apps.comum.utils import formatar_moeda

# from apps.selos.models import Selo
from apps.pedidos.models import (
    Ato,
    DocumentoParaRequerimento,
    Evento,
    Imovel,
    Parte,
    Participacao,
    Pedido,
    Requerimento,
)

logger = logging.getLogger(__name__)

logger.debug(f"Iniciando {__name__}")


class TabelaBase(tables.Table):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        # self.attrs = {
        #    "class": "table table-hover table-striped table-bordered no-footer nowrap"
        # }


class EventoTable(TabelaBase):
    alterar = tables.TemplateColumn(
        "<a class='badge bg-secondary' href=\"{% url 'pedidos:evento_alterar' record.id %}\">Alterar</a>",
        orderable=False,
        verbose_name="Ação",
    )

    class Meta:
        model = Evento
        paginate = {"per_page": 5}
        fields = ("nome", "tipo_evento", "criado_por", "criado_em")
        attrs = {
            "class": "table table-hover table-striped table-bordered no-footer nowrap",
        }
        empty_text = "Nenhum registro encontrado"


class PedidoTable(TabelaBase):
    opcoes = tables.TemplateColumn(
        "<a class='badge bg-info' href=\"{% url 'pedidos:duplicar_pedido_de_protocolo' record.pk %}\"><i class='icon feather icon-copy m-0'></i> Duplicar</a>",
        orderable=False,
        verbose_name="Ação",
    )

    # suas outras colunas
    # num_imoveis = tables.Column(verbose_name="Imóveis", empty_values=())
    # num_partes = tables.Column(verbose_name="Partes", empty_values=())
    num_atos = tables.Column(verbose_name="Atos", empty_values=())
    total_pedido_de_protocolo = tables.Column(verbose_name="R$ Total", empty_values=())
    valor_total_caixa = tables.Column(verbose_name="R$ Caixa", empty_values=())

    # alterar = tables.TemplateColumn(
    #     "<a class='' href='{{ record.get_absolute_url }}'><i class='icon feather icon-eye f-16'></i> Visualizar</a>",
    #     orderable=False,
    #     verbose_name="Ação",
    # )
    nome = tables.Column(
        accessor="apresentante__nome",
        verbose_name="Apresentante",
    )

    # numero_pedido = tables.LinkColumn(
    #     "pedidos:pedido_detail",
    #     args=[tables.A("pk")],
    #     verbose_name="Número do Pedido",
    #     orderable=True,
    # )

    numero_pedido = tables.TemplateColumn(
        """
    {% if record.ativo %}
        <a href="{% url 'pedidos:pedido_detail' record.pk %}">{{ record.numero_pedido }}</a>
    {% else %}
        <span class="badge bg-danger f-14"><a href="{% url 'pedidos:pedido_detail' record.pk %}" class="text-white">{{ record.numero_pedido }}</a></span>
    {% endif %}
    """,
        verbose_name="Número do Pedido",
        orderable=True,
    )

    protocolo = tables.TemplateColumn(
        """
        {% if record.get_protocolo_url %}
            <a href="{{ record.get_protocolo_url }}">{{ record.numero_protocolo_firebird }}</a>
        {% else %}
            {{ record.numero_protocolo_firebird|default:"Sem protocolo"}}
        {% endif %}
        """,
        verbose_name="Protocolo",
        orderable=False,
    )

    # @staticmethod
    # def render_num_imoveis(record):
    #     if not record.numero_protocolo_firebird:
    #         return 0
    #     else:
    #         protocolo = models_home.Livro01Protocolo.objects.filter(
    #             numero_protocolo=record.numero_protocolo_firebird
    #         ).first()

    #         url = reverse("pedidos:imoveis_list", args=[protocolo.numero_protocolo])
    #         return format_html('<a href="{}">{}</a>', url, 0)

    # @staticmethod
    # def render_num_partes(record):
    #     url = reverse("pedidos:listar_partes", args=[record.pk])
    #     return format_html('<a href="{}">{}</a>', url, record.pedidos_partes.count())

    # @staticmethod
    # def render_numero_pedido(record):
    #     url = reverse("pedidos:atos_list", args=[record.pk])
    #     return format_html('<a href="{}">{}</a>', url, record.quantidade_atos)

    @staticmethod
    def render_num_atos(record) -> int:
        url = reverse("pedidos:atos_list", args=[record.pk])
        return format_html('<a href="{}">{}</a>', url, record.quantidade_atos)

    @staticmethod
    def render_total_pedido(record) -> str:
        url = record.get_absolute_url()
        return format_html('<a href="{}">{}</a>', url, formatar_moeda(record.total))

    @staticmethod
    def render_valor_total_caixa(record) -> str:
        # Função para formatar o valor com duas casas decimais
        def formatar_valor(valor) -> Decimal:
            # Convertendo o valor para Decimal e arredondando para duas casas decimais
            return Decimal(valor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        valor_total_caixa_formatado = formatar_valor(record.valor_total_caixa)
        total_pedido_formatado = formatar_valor(record.total_pedido_de_protocolo)

        if valor_total_caixa_formatado != total_pedido_formatado:
            valor_formatado = f"{valor_total_caixa_formatado:.2f}".replace(".", ",")
            return format_html(
                '<span class="badge bg-danger">{}</span>',
                valor_formatado,
            )

        return f"{valor_total_caixa_formatado:.2f}".replace(".", ",")

    class Meta:
        model = Pedido
        order_by = ["-data_entrada"]
        attrs = {
            "class": "table table-hover table-striped table-bordered no-footer nowrap",
        }
        empty_text = "Nenhum registro encontrado"
        paginate = {"per_page": 5}
        fields = (
            "numero_pedido",
            "protocolo",
            "nome",
            "data_entrada",
            "data_prevista",
            # "num_imoveis",
            # "num_partes",
            "num_atos",
            "total_pedido_de_protocolo",
            "valor_total_caixa",
            "opcoes",
        )


class ImovelTable(TabelaBase):
    opcoes = tables.TemplateColumn(
        template_code="""
            <div class="dropdown">
                <button class="btn btn-secondary dropdown-toggle" type="button" id="dropdownMenuButton" data-bs-toggle="dropdown" aria-haspopup="true" aria-expanded="false">
                    Opções
                </button>
                <div class="dropdown-menu" aria-labelledby="dropdownMenuButton">
                    <a class="dropdown-item" href="{{ record.get_alterar_url }}">Alterar</a>
                    <a class="dropdown-item" href="{{ record.get_registro_url }}">Ver Registro</a>
                </div>
            </div>
        """,
        orderable=False,
        verbose_name="Opções",
    )

    quantidade_atos = tables.Column(
        empty_values=(),
        verbose_name="Qtd de Ato",
    )

    def render_quantidade_atos(self, record):
        return Ato.objects.filter(imovel=record).count()

    class Meta:
        model = Imovel
        paginate = {"per_page": 5}
        attrs = {
            "class": "table table-hover table-striped table-bordered no-footer nowrap",
        }
        empty_text = "Nenhum registro encontrado"
        fields = (
            "numero_registro",
            "logradouro",
            "quadra",
            "lote",
            "municipio",
            "quantidade_atos",
        )


class PartesTable(TabelaBase):
    alterar = tables.TemplateColumn(
        """
        <a class='badge btn-primary f-14' href=\"{{record.get_update_url }}\"><i class="fas fa-user-edit d-none d-md-inline-block"></i> Parte </a>

        """,
        orderable=False,
        verbose_name="Ação",
    )

    quantidade_atos = tables.Column(
        empty_values=(),
        verbose_name="Qtd de Ato",
    )

    descricao_participacao = tables.Column(
        empty_values=(),
        verbose_name="Papel",
    )

    percentual_participacao = tables.Column(
        empty_values=(),
        verbose_name="Participação",
    )

    def render_quantidade_atos(self, record) -> int:
        return 0  # Ato.objects.filter(parte=record).count()

    def render_get_descricao_ato(self, value, record):
        return value or "Sem descrição"

    def render_percentual_participacao(self, value, record):
        return value or 0

    class Meta:
        model = Parte
        paginate = {"per_page": 5}
        attrs = {
            "class": "table table-hover table-striped table-bordered no-footer nowrap",
        }
        empty_text = "Nenhum registro encontrado"
        fields = (
            "documento_formatado",
            "nome",
            "descricao_participacao",
            "percentual_participacao",
            # "tipo_documento",
            "quantidade_atos",
        )


class EventosTable(TabelaBase):
    alterar = tables.TemplateColumn(
        "<a class='badge bg-secondary' href=\"{% url 'pedidos:evento_alterar' record.pedido.id record.id %}\">Alterar</a>",
        orderable=False,
        verbose_name="Ação",
    )

    class Meta:
        model = Evento
        fields = ("nome", "tipo_evento", "criado_por", "criado_em")


class ProtocoloImovelTable(TabelaBase):
    alterar = tables.TemplateColumn(
        "<a class='badge bg-secondary' href=\"{% url 'pedidos:imovel_ato_update' record.imovel.pedido.id record.id %}\">Alterar</a>",
        orderable=False,
        verbose_name="Ação",
    )

    class Meta:
        model = Ato
        attrs = {
            "class": "table table-hover table-striped table-bordered no-footer nowrap",
        }
        empty_text = "Nenhum registro encontrado"
        paginate = {"per_page": 5}
        fields = ("tipo", "data_emissao")


class ProtocoloParteTable(TabelaBase):
    alterar = tables.TemplateColumn(
        "<a class='badge bg-secondary' href=\"{% url 'pedidos:parte_ato_update' record.parte.pedido_id record.parte_id record.id %}\">alterar</a>",
        orderable=False,
        verbose_name="Ação",
    )

    nome = tables.Column(
        accessor="tipo__nome",
        verbose_name="Nome",
    )

    class Meta:
        model = Ato
        attrs = {
            "class": "table table-hover table-striped table-bordered no-footer nowrap",
        }
        empty_text = "Nenhum registro encontrado"
        paginate = {"per_page": 5}
        fields = ("nome", "alterar")


class AtosAgrupadosTable(TabelaBase):
    # alterar = tables.TemplateColumn(
    #     # "<a class='badge bg-secondary' href=\"{% url 'pedidos:imovel_ato_update' record.imovel.pedido_id record.imovel_id record.id %}\">alterar</a>",
    #     orderable=False,
    #     verbose_name="Ação",
    # )

    nome = tables.Column(
        footer="Total:",
        accessor="ato_praticavel__nome",
    )

    quantidade = tables.Column(
        footer=lambda table: table.total_quantidade(),
    )

    def total_quantidade(self):
        return sum([item["quantidade"] for item in self.data])

    class Meta:
        model = Ato
        attrs = {
            "class": "table table-hover table-striped table-bordered no-footer nowrap",
        }
        empty_text = "Nenhum registro encontrado"
        paginate = {"per_page": 5}
        fields = ("nome", "quantidade")


class AtoTable(TabelaBase):
    # alterar = tables.TemplateColumn(
    #     # "<a class='badge bg-secondary' href=\"{% url 'pedidos:imovel_ato_update' record.imovel.pedido_id record.imovel_id record.id %}\">alterar</a>",
    #     orderable=False,
    #     verbose_name="Ação",
    # )

    nome = tables.Column(
        footer="Total:",
        accessor="ato_praticavel__nome",
    )

    quantidade = tables.Column(
        footer=lambda table: table.total_quantidade(),
    )

    class Meta:
        model = Ato
        attrs = {
            "class": "table table-hover table-striped table-bordered no-footer nowrap",
        }
        empty_text = "Nenhum registro encontrado"
        paginate = {"per_page": 5}
        fields = ("nome", "quantidade")


class AtosComplementaresAgrupadosTable(TabelaBase):
    # alterar = tables.TemplateColumn(
    #     # "<a class='badge bg-secondary' href=\"{% url 'pedidos:imovel_ato_update' record.imovel.pedido_id record.imovel_id record.id %}\">alterar</a>",
    #     orderable=False,
    #     verbose_name="Ação",
    # )

    nome = tables.Column(
        footer="Total:",
        accessor="ato_praticavel__nome",
    )

    quantidade = tables.Column(
        footer=lambda table: table.total_quantidade(),
    )

    def total_quantidade(self):
        return sum([item["quantidade"] for item in self.data])

    class Meta:
        model = Ato
        attrs = {
            "class": "table table-hover table-striped table-bordered no-footer nowrap",
        }
        empty_text = "Nenhum registro encontrado"
        paginate = {"per_page": 5}
        fields = ("nome", "quantidade")


class ProtocoloTable(TabelaBase):
    # valor = tables.Column(empty_values=(), verbose_name="Valor")

    acoes = tables.TemplateColumn(
        template_code="""
            <div class="d-flex flex-wrap align-items-center">
                <a class="btn btn-sm btn-primary mx-1 my-1" href="{% url 'pedidos:ato_detail' record.pk %}">
                    <i class="icon feather icon-edit d-none d-md-inline-block"></i>
                    Ver
                </a>

                <a class="btn btn-sm btn-primary mx-1 my-1" href="{% url 'pedidos:ato_update' record.pk %}">
                    <i class="icon feather icon-edit d-none d-md-inline-block"></i>
                    Editar
                </a>

                <a class="btn btn-sm btn-danger mx-1 my-1" href="{% url 'pedidos:ato_delete' record.pk %}">
                    <i class="icon feather icon-trash d-none d-md-inline-block"></i>
                    Excluir
                </a>
            </div>
        """,
        orderable=False,
        verbose_name="Ações",
    )

    nome = tables.Column(empty_values=[], verbose_name="ato")

    def render_nome(self, record):
        principal = record.nome
        secundario = record.qualificacao
        return mark_safe(f"{principal} <br> <small>{secundario}</small>")

    def render_total(self, record):
        conteudo_popover = (
            f"Emolumento: {formatar_moeda(record.emolumento)}<br>"
            f"Taxa Adicional: {formatar_moeda(record.taxa_fiscal_judiciaria)}<br>"
            f"Recompe: {formatar_moeda(record.fundo_estado)}<br>"
            f"Issqn: {formatar_moeda(record.issqn)}<br>"
            f"Tributação: {record.tributacao}<br>"
        )

        return mark_safe(
            '<span data-toggle="popover" data-html="true" title="Detalhes" '
            f'data-content="{conteudo_popover}">{formatar_moeda(record.total)} '
            '<i class="icon feather icon-info f-10 align-text-top"></i></span>',
        )

    class Meta:
        model = Ato
        attrs = {
            "class": "table table-hover table-striped table-bordered no-footer nowrap",
        }
        empty_text = "Nenhum registro encontrado"
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


class AtosTable(TabelaBase):
    acoes = tables.TemplateColumn(
        template_code="""
            <div class="d-flex flex-wrap align-items-center">
                <a class="btn btn-sm btn-primary mx-1 my-1" href="{% url 'pedidos:ato_update' record.pk %}">
                    <i class="icon feather icon-edit d-none d-md-inline-block"></i> Alterar
                </a>

                <a class="btn btn-sm btn-danger mx-1 my-1" href="{% url 'pedidos:excluir_ato' record.pk %}">
                    <i class="icon feather icon-trash d-none d-md-inline-block"></i> Excluir
                </a>
            </div>
        """,
        orderable=False,
        verbose_name="Ações",
    )

    nome = tables.Column(empty_values=[], verbose_name="ato")

    def render_nome(self, record):
        principal = record.nome
        secundario = record.qualificacao
        return mark_safe(f"{principal} <br> <small>{secundario}</small>")

    def render_total(self, record):
        conteudo_popover = (
            f"Emolumento: {formatar_moeda(record.emolumento)}<br>"
            f"Taxa Adicional: {formatar_moeda(record.taxa_fiscal_judiciaria)}<br>"
            f"Recompe: {formatar_moeda(record.fundo_estado)}<br>"
            f"Issqn: {formatar_moeda(record.issqn)}<br>"
            f"Tributação: {record.tributacao}<br>"
        )

        return mark_safe(
            '<span data-toggle="popover" data-html="true" title="Detalhes" '
            f'data-content="{conteudo_popover}">{formatar_moeda(record.total)} '
            '<i class="icon feather icon-info f-10 align-text-top"></i></span>',
        )

    class Meta:
        model = Ato
        paginate = {"per_page": 5}
        attrs = {
            "class": "table table-hover table-striped table-bordered no-footer nowrap",
        }
        empty_text = "Nenhum registro encontrado"
        fields = (
            "nome",
            # "emolumento",
            # "taxa_fiscal_judiciaria",
            # "fundo_estado",
            # "issqn",
            "total",
            #  "data_emissao",
        )


# class SelosTable(TabelaBase):
#     alterar = tables.TemplateColumn(
#         "<a class='badge bg-secondary' href=\"{% url 'pedidos:selo_alterar' record.pedido.id record.id %}\">Alterar</a>",
#         orderable=False,
#         verbose_name="Ação",
#     )

#     class Meta:
#         model = SeloEletronico
#         attrs = {
# "class": "table table-hover table-striped table-bordered no-footer nowrap"
#        }
#         empty_text = "Nenhum registro encontrado"
#         fields = ("codigo", "data_utilizacao")


class ParticipacaoTable(tables.Table):
    # parte = tables.LinkColumn("pedidos:parte_update", args=[tables.A("pk")])

    parte__documento_formatado = tables.Column(verbose_name="Documento")
    conjuge_percentual = tables.Column(
        verbose_name="Conjuge e Participacao",
        accessor=tables.A("get_conjuge_percentual"),
    )
    opcoes = tables.TemplateColumn(
        """
        <a href="{{ record.parte.get_update_url }}"
            class="badge btn-primary f-14">
            <i class="fas fa-user-edit d-none d-md-inline-block"></i>
            Editar
        </a>

        <a href="{{record.get_update_url }}"
            class='badge btn-primary f-14' >
            <i class="icon feather icon-edit d-none d-md-inline-block"></i>
            Percentual
        </a>

        <a href="{% url 'pedidos:remove_participacao' record.id %}"
            class='badge btn-danger f-14'>
            <i class="icon feather icon-trash d-none d-md-inline-block"></i>
            Excluir
        </a>
        """,
        orderable=False,
        verbose_name="Opções",
    )

    class Meta:
        model = Participacao
        attrs = {"class": "table table-striped table-bordered no-footer nowrap"}
        empty_text = "Nenhum registro encontrado"
        fields = [
            "parte",
            "parte__documento_formatado",
            "papel",
            "percentual_participacao",
            "conjuge_percentual",
            "opcoes",
        ]

    def get_percentual_participacao_sum(self):
        if isinstance(self.data, QuerySet):
            # Quando os dados são uma QuerySet, usamos a agregação do Django
            return (
                self.data.aggregate(Sum("percentual_participacao"))[
                    "percentual_participacao__sum"
                ]
                or 0
            )
        else:
            # Quando os dados são uma lista ou outro iterável, somamos manualmente
            return (
                sum(
                    item.percentual_participacao
                    for item in self.data
                    if hasattr(item, "percentual_participacao")
                )
                or 0
            )


class RequerimentoTable(tables.Table):
    nome = tables.LinkColumn("pedidos:requerimento_detail", args=[tables.A("pk")])

    def render_nome(self, record):
        # Captura a URL atual
        current_url = self.request.get_full_path()
        # Gera a URL destino com o parâmetro next
        next_url = f"{reverse('pedidos:requerimento_detail', args=[record.pk])}?{urlencode({'next': current_url})}"
        return mark_safe(f'<a href="{next_url}">{record.nome}</a>')

    def render_observacao(self, value):
        return mark_safe(value)

    class Meta:
        model = Requerimento
        fields = ("nome", "quantidade_de_documentos")


class DocumentoParaRequerimentoTable(tables.Table):
    nome = tables.LinkColumn(
        "pedidos:documento_para_requerimento_detail",
        args=[tables.A("pk")],
    )

    class Meta:
        model = DocumentoParaRequerimento
        # template_name = "django_tables2/bootstrap4.html"
        fields = ("nome", "requerimento")
