import logging
import re
import uuid
from datetime import date, datetime
from decimal import Decimal
from functools import cached_property
from typing import Any
from urllib.parse import urlencode

from auditlog.models import AuditlogHistoryField
from django.apps import apps
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import (
    Count,
    QuerySet,
    Sum,
)
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django_ckeditor_5.fields import CKEditor5Field

from apps.cartorios.models import Usuario
from apps.comum.mixins import DocumentoMixin, EnderecoMixin
from apps.comum.models import (
    BaseModel,
    DadosBancarios,
    PrazoLegal,
    TipoRegistro,
    TipoRegistroImobiliario,
    TipoTributacao,
)
from apps.comum.utils import calcular_data_com_workalendar, formatar_moeda
from apps.ged.models import Arquivo
from apps.home import helpers as home_helpers
from apps.home import models as home_models
from apps.home.models import models_home
from apps.home.padroes import (
    ARQUIVAMENTO,
    CODIGO_PRENOTACAO_MG,
    PERCENTUAL,
    PRENOTACAO,
    PROVISORIO,
    VALOR_FIXO,
)
from apps.home.tipos import TipoSexo
from apps.mapeamentos.models import Mapeamento
from apps.pedidos.managers import (
    AtoManager,
    ImovelManager,
    PedidoFirebirdManager,
    PedidoManager,
    TabelaManager,
)
from apps.pedidos.mixins import SequencialIDMixin
from apps.pedidos.services import (
    PedidoFirebirdUtils,
    PedidoProtocolarNoFirebirdService,
)
from apps.pedidos.utils import arredondar_decimal_bancario, formatar_telefone
from core.utils.firebird_utils import FbConnection
from core.utils.formatacoes import formatar_documento

logger = logging.getLogger(__name__)

logger.debug(f"Iniciando {__name__}")


class UUIDPrimaryKeyField(models.UUIDField):
    def __init__(self, *args, **kwargs) -> None:
        kwargs["primary_key"] = True
        kwargs["default"] = uuid.uuid4
        kwargs["editable"] = False
        kwargs["verbose_name"] = "ID"
        super().__init__(*args, **kwargs)


class Pedido(BaseModel):
    id: uuid.uuid4 = UUIDPrimaryKeyField()
    numero_pedido: int = models.IntegerField(
        db_index=True,
        unique=True,
        verbose_name="Número",
    )
    data_entrada: datetime = models.DateTimeField(
        auto_now_add=True,
        null=True,
        verbose_name="Entrada",
    )
    interessado_nome: str = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Interessado",
    )
    interessado_documento: str = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Documento do Interessado",
    )
    apresentante: "Apresentante" = models.OneToOneField(
        "Apresentante",
        on_delete=models.CASCADE,
        related_name="pedido",
        null=True,
    )
    observacao: str = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name="Anotações",
        help_text="Informações adicionais sobre o Pedido",
    )
    tipo_de_servico: str = models.CharField(
        max_length=1,
        blank=True,
        null=True,
        verbose_name="Tipo de Serviço",
    )
    numero_onr: str = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Número ONR",
    )
    numero_protocolo_firebird: str = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        default="",
        verbose_name="Protocolo",
        db_index=True,
    )
    numero_selo_firebird: str = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Número do Selo Eletrônico",
    )
    codigo_seguranca_firebird: str = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Codigo de Segurança do Selo Eletrônico",
    )
    codigo_internet_firebird: str = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        verbose_name="Código para Internet do Protocolo",
    )

    ativo: bool = models.BooleanField(
        default=True,
        verbose_name="Pedido de Protocolo Utilizado",
    )
    data_modificacao: datetime = models.DateTimeField(auto_now=True)
    history: AuditlogHistoryField = AuditlogHistoryField(pk_indexable=False)

    objects: PedidoManager = PedidoManager()

    class Meta:
        verbose_name = "Pedido"
        verbose_name_plural = "Pedidos"

    def __str__(self: "Pedido") -> str:
        return f"Pedido {self.numero_pedido_formatado}"

    def get_absolute_url(self: "Pedido") -> str:
        return reverse("pedidos:pedido_detail", kwargs={"pk": self.pk})

    # def get_apresentante(self: "Pedido") -> "Apresentante":
    #     return self.apresentante if hasattr(self, "apresentante") else None

    def get_apresentante(self: "Pedido") -> "Apresentante":
        return getattr(self, "apresentante", None)

    def get_update_url(self: "Pedido") -> str:
        return reverse("pedidos:pedido_update", kwargs={"pk": self.pk})

    def get_delete_url(self: "Pedido") -> str:
        return reverse("pedidos:pedido_delete", kwargs={"pk": self.pk})

    def get_protocolo_url(self: "Pedido") -> str:
        if not self.numero_protocolo_firebird:
            return None
        protocolo = models_home.Livro01Protocolo.objects.filter(
            numero_protocolo=self.numero_protocolo_firebird,
        ).first()
        return protocolo.get_absolute_url() if protocolo else None

    def get_partes(self: "Pedido") -> QuerySet["Parte"]:
        # Obtém todos os atos relacionados ao pedido
        atos = Ato.objects.filter(pedido=self)

        # Obtém todas as participações relacionadas a esses atos
        participacoes = Participacao.objects.filter(ato__in=atos)

        # Obtém os IDs das partes a partir das participações
        ids_partes = participacoes.values_list("parte_id", flat=True)

        # Obtém todas as partes que correspondem aos IDs coletados
        return Parte.objects.filter(id__in=ids_partes)

    @cached_property
    def numero_pedido_formatado(self: "Pedido") -> str:
        # Renomeamos este método para evitar o conflito com o nome da propriedade

        if self.numero_pedido:
            return f"{self.numero_pedido:06d}".replace("000", "0.00").replace(
                "000",
                "0.00",
            )
        return self.numero_pedido

    @cached_property
    def qualificacao(self: "Pedido") -> str:
        """Retorna a qualificação do pedido com dados do apresentante."""
        return f"{self} de {self.apresentante}"

    @cached_property
    def partes(self: "Pedido") -> QuerySet["Parte"]:
        return self.get_partes()

    @cached_property
    def imoveis(self: "Pedido") -> QuerySet["Ato"]:
        """Retorna todos os imóveis associados a este Pedido que possuem número de registro."""
        return (
            Ato.objects.filter(pedido=self)
            .exclude(
                imovel_numero_registro__isnull=True,
            )
            .exclude(imovel_numero_registro__exact="")
        )

    @classmethod
    def alinhar_numero_pedido_com_fb(cls: "Pedido") -> None:
        cls.definir_proximo_numero(
            numero_proximo_pedido=Pedido.objects.get_numero_proximo_pedido_fb(),
        )

    @cached_property
    def chave_pedido_fb(self: "Pedido") -> str:
        from apps.pedidos.firebird import obter_chave_pedido_fb_pelo_numero

        return (
            obter_chave_pedido_fb_pelo_numero(self.numero_pedido)
            if self.numero_pedido
            else ""
        )

    @classmethod
    def criar(
        cls: "Pedido",
        apresentante: "Apresentante",
        criado_por: Usuario,
    ) -> models.QuerySet:
        if not apresentante or not isinstance(apresentante, Apresentante):
            msg = "O apresentante é obrigatório para criar um pedido."
            raise ValueError(msg)

        if not criado_por or not isinstance(criado_por, Usuario):
            msg = "O usuário é obrigatório para criar um pedido."
            raise ValueError(msg)

        return cls.objects.create(apresentante=apresentante, criado_por=criado_por)

    @cached_property
    def data_prevista(self: "Pedido") -> date:
        """
        A data prevista é calculada com base na data de entrada
        somada aos dias do prazo legal do ato com maior prazo.
        """
        prazo_legal_maximo = None

        for ato in self.get_atos.all():
            if not ato.ato_praticavel:
                continue

            if ato.ato_praticavel.prazo_legal and (
                prazo_legal_maximo is None
                or ato.ato_praticavel.prazo_legal.dias > prazo_legal_maximo
            ):
                prazo_legal_maximo = ato.ato_praticavel.prazo_legal.dias

        if prazo_legal_maximo is None:
            return None

        data_calculada = calcular_data_com_workalendar(
            self.data_entrada,
            prazo_legal_maximo,
        )

        logger.debug(
            f"Data Prevista calculada para o pedido {self.numero_pedido}: {data_calculada}",
        )

        return data_calculada

    @cached_property
    def data_validade(self: "Pedido") -> date:
        return calcular_data_com_workalendar(self.data_entrada, 21)

    @cached_property
    def get_atos(self: "Pedido") -> QuerySet["Ato"]:
        return Ato.objects.filter(pedido=self)

    @cached_property
    def quantidade_atos(self: "Pedido") -> int:
        return self.get_atos.count()

    @cached_property
    def total_emolumentos_pedido_de_protocolo(self: "Pedido") -> Decimal:
        try:
            soma_emolumento_liquido_com_desconto_tributacao_dos_atos = sum(
                ato.emolumento_liquido_com_desconto_tributacao
                for ato in self.get_atos
                if ato.emolumento is not None
            )
            return arredondar_decimal_bancario(
                soma_emolumento_liquido_com_desconto_tributacao_dos_atos,
            )
        except Exception as e:
            logger.exception(
                f"Erro ao calcular total de emolumentos do pedido {self.numero_pedido}: {e!s}",
            )
            return Decimal("0.0")

    @cached_property
    def total_taxa_fiscal_judiciaria_pedido(self: "Pedido") -> Decimal:
        soma_taxa_fiscal_judiciaria_com_desconto_tributacao_dos_atos = sum(
            ato.taxa_fiscal_judiciaria_com_desconto_tributacao for ato in self.get_atos
        )
        return arredondar_decimal_bancario(
            soma_taxa_fiscal_judiciaria_com_desconto_tributacao_dos_atos,
        )

    @cached_property
    def total_fundo1_pedido_de_protocolo(self: "Pedido") -> Decimal:
        try:
            soma_fundo1_com_desconto_tributacao_do_atos = sum(
                ato.fundo1_com_desconto_tributacao for ato in self.get_atos
            )
            return arredondar_decimal_bancario(
                soma_fundo1_com_desconto_tributacao_do_atos,
            )
        except Exception as e:
            logger.exception(
                f"Erro ao calcular total de fundo1 do pedido {self.numero_pedido}: {e!s}",
            )
            return Decimal("0.0")

    @cached_property
    def total_issqn_pedido_de_protocolo(self: "Pedido") -> Decimal:
        soma_issqn_com_desconto_tributacao_dos_atos = sum(
            ato.issqn_com_desconto_tributacao for ato in self.get_atos
        )
        return arredondar_decimal_bancario(soma_issqn_com_desconto_tributacao_dos_atos)

    @cached_property
    def total_pedido_de_protocolo(self: "Pedido") -> Decimal:
        soma_total_com_desconto_de_tributacao_do_atos = sum(
            ato.total_com_desconto_tributacao for ato in self.get_atos
        )
        return arredondar_decimal_bancario(
            soma_total_com_desconto_de_tributacao_do_atos,
        )

    @cached_property
    def valor_diferenca(self: "Pedido") -> Decimal:
        return self.total_pedido_de_protocolo - self.valor_total_caixa

    # property que organiza os custas totais numa string unica:
    @cached_property
    def descricao_custas_totais(self: "Pedido") -> str:
        return f"Emolumentos: R$ {self.total_emolumentos:.2f} | TJ: R$ {self.total_taxa_fiscal_judiciaria:.2f} | Fundos: R$ {self.total_recompe:.2f} | ISS: R$ {self.total_issqn:.2f} | Total: R$ {self.total:.2f}"

    # property que organiza os custas totais numa string unica:
    @cached_property
    def descricao_custas_totais_abreviado(self: "Pedido") -> str:
        return f"Emol: R$ {self.total_emolumentos:.2f} | TJ: R$ {self.total_taxa_fiscal_judiciaria:.2f} | Fundos: R$ {self.total_recompe:.2f} | ISS: R$ {self.total_issqn:.2f} | Total: R$ {self.total:.2f}"

    # PROTOCOLAR NO POSTGRESQL
    def importar_protocolo_postgresql(
        self: "Pedido",
        numero_protocolo_firebird,
        db: FbConnection,
    ) -> None:
        from apps.home.services import firebird

        print("Protocolo no Postgresql: ", numero_protocolo_firebird)

        protocolo, _ = firebird.importar_protocolo_por_numero_fb_apenas_inserir(
            numero_protocolo=numero_protocolo_firebird,
            tipo_importacao="P",
            db=db,
        )

        return protocolo

    def protocolar(self: "Pedido") -> str:
        msg = ""

        with transaction.atomic(), FbConnection() as db:
            try:
                db.begin_transaction()
                pedido_fb, pedido_item_fb = (
                    PedidoFirebirdUtils.exportar_pedido_de_protocolo_para_fb(
                        pedido=self,
                        atos=self.atos.all(),
                        user=self.criado_por,
                        db=db,
                    )
                )

                if not pedido_fb:
                    msg = "Pedido não exportado."
                    raise ValueError(msg)

                PedidoProtocolarNoFirebirdService.protocolar_pedido_no_fb(
                    pedido_fb=pedido_fb,
                    pedido_item_fb=pedido_item_fb,
                    pedido=self,
                    user=self.criado_por,
                    db=db,
                )

                # PROTOCOLAR NO POSTGRESQL
                protocolo = self.importar_protocolo_postgresql(
                    self.numero_protocolo_firebird,
                    db=db,
                )

                db.commit()

            except Exception as e:  # Captura exceções mais genéricas
                db.rollback()  # Desfaz as operações da transação em caso de erro
                msg = f"Erro ao protocolar pedido: {e!s}"
                logger.exception(msg)  # Loga a exceção com o traceback
                raise

        return (
            msg if msg else f"Pedido protocolado com sucesso.: Protocolo: {protocolo}"
        )

    def get_atos_agrupados(self):
        atos = self.get_atos.all()

        agrupamento = {}

        for ato in atos:
            agrupamento_id = (
                ato.nome,
                ato.tipo_emolumento,
                ato.imovel_tipo_registro_id,
                ato.imovel_numero_registro,
                ato.valor_titulo,
                ato.valor_avaliacao,
            )
            if agrupamento_id not in agrupamento:
                agrupamento[agrupamento_id] = {
                    "quantidade": Decimal("0.0"),
                    "emolumento_bruto_calculado": Decimal("0.0"),
                    "emolumento_liquido_com_desconto_tributacao": Decimal("0.0"),
                    "taxa_fiscal_judiciaria_com_desconto_tributacao": Decimal("0.0"),
                    "fundo1_com_desconto_tributacao": Decimal("0.0"),
                    "issqn_com_desconto_tributacao": Decimal("0.0"),
                    "total_com_desconto_tributacao": Decimal("0.0"),
                    "valor_avaliacao": Decimal("0.0"),
                    "valor_titulo": Decimal("0.0"),
                    "imovel_numero_registro": Decimal("0.0"),
                    "imovel_tipo": "",
                    "codigo_tabela": "",
                }
            # agrupamento[agrupamento_id]["quantidade"] += 1
            agrupamento[agrupamento_id]["quantidade"] += ato.quantidade
            agrupamento[agrupamento_id][
                "emolumento_liquido_com_desconto_tributacao"
            ] += ato.emolumento_liquido_com_desconto_tributacao
            agrupamento[agrupamento_id][
                "taxa_fiscal_judiciaria_com_desconto_tributacao"
            ] += ato.taxa_fiscal_judiciaria_com_desconto_tributacao
            agrupamento[agrupamento_id]["fundo1_com_desconto_tributacao"] += (
                ato.fundo1_com_desconto_tributacao
            )
            agrupamento[agrupamento_id]["issqn_com_desconto_tributacao"] += (
                ato.issqn_com_desconto_tributacao
            )
            agrupamento[agrupamento_id]["total_com_desconto_tributacao"] += (
                ato.total_com_desconto_tributacao
            )
            agrupamento[agrupamento_id]["valor_avaliacao"] = ato.valor_avaliacao
            agrupamento[agrupamento_id]["valor_titulo"] = ato.valor_titulo
            agrupamento[agrupamento_id]["imovel_numero_registro"] = (
                ato.imovel_numero_registro
            )
            agrupamento[agrupamento_id]["imovel_tipo"] = (
                TipoRegistroImobiliario.objects.filter(id=ato.imovel_tipo_registro_id)
                .values_list("nome", flat=True)
                .first()
            )
            # agrupamento[agrupamento_id]["codigo_tabela"] = ato.tipo_emolumento.codigo
            agrupamento[agrupamento_id]["codigo_tabela"] = (
                ato.codigo_emolumento_individual
            )

        return agrupamento

    def codigo_seguranca_firebird_formatado(self):
        return home_helpers.formatar_codigo_seguranca(self.codigo_seguranca_firebird)

    @cached_property
    def url_selo_digital_mg(self):
        # https://selos.tjmg.jus.br/sisnor/eselo/consultaSeloseAtos.jsf?selo={}&codigo={}
        url = models_home.Configuracao.obter(
            "url_selo_digital_mg",
            "https://selos.tjmg.jus.br/sisnor/eselo/consultaSeloseAtos.jsf?selo={}&codigo={}",
        )
        if url:
            return url.format(self.numero_selo_firebird, self.codigo_seguranca_firebird)
        return None

    def arquivos(self):
        """Retorna todos os arquivos associados a este Pedido."""
        return Arquivo.objects.for_object(self)

    firebird = PedidoFirebirdManager()

    # VALOR DO CAIXA
    @cached_property
    def valor_total_caixa(self: "Pedido") -> Decimal:
        if not self.numero_protocolo_firebird:
            return 0
        else:
            protocolo = models_home.Livro01Protocolo.objects.filter(
                numero_protocolo=self.numero_protocolo_firebird,
            ).first()

            if protocolo:
                # Soma dos valores da coluna valor_transacao para o pedido específico
                soma_total_caixa = (
                    models_home.Financeiro.objects.total_caixa(protocolo.pedido_id) or 0
                )

                return arredondar_decimal_bancario(soma_total_caixa)
            else:
                return 0

    # CANCELAR E DEVOLVER
    def registrar_cancelar_devolucao(self: "Pedido", usuario) -> None:
        self.ativo = False
        self.save()

        # descricao = "Cancelar e Devolver"
        # devolvido = self.get_devolvido
        # if devolvido:
        #     self.registrar_andamento(devolvido, descricao, usuario)

        # Cancelar o item CERTIDAO
        # pedido_imovel = Pedido.objects.filter(pedido_id=self.pk)
        # pedido_pessoa = Pedido.objects.filter(pedido_id=self.pk)

        # DESVINCULAR o item CERTIDAO
        # self.desvicular_item_certidao(pedido_imovel, pedido_pessoa)

    @cached_property
    def primeiro(self) -> "Pedido":
        return Pedido.objects.all().order_by("numero_pedido").first()

    @cached_property
    def anterior(self) -> "Pedido":
        return (
            Pedido.objects.filter(numero_pedido__lt=self.numero_pedido)
            .order_by("numero_pedido")
            .last()
        )

    @cached_property
    def seguinte(self) -> "Pedido":
        return (
            Pedido.objects.filter(numero_pedido__gt=self.numero_pedido)
            .order_by("numero_pedido")
            .first()
        )

    @cached_property
    def ultimo(self) -> "Pedido":
        return Pedido.objects.all().order_by("numero_pedido").last()


class Apresentante(DocumentoMixin, SequencialIDMixin, models.Model):
    history: AuditlogHistoryField = AuditlogHistoryField(pk_indexable=False)
    id: uuid.uuid4 = UUIDPrimaryKeyField()
    # pedido = models.OneToOneField(Pedido, on_delete=models.CASCADE, related_name="apresentante")
    nome: str = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        default="",
        verbose_name="Nome do Apresentante",
        help_text="Nome Completo do Apresentante/Requerente",
    )
    telefone: str = models.CharField(max_length=40, blank=True, null=True, default="")
    telefone_2: str = models.CharField(max_length=40, blank=True, null=True, default="")
    observacao: str = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        default="",
        verbose_name="Anotações",
        help_text="Anotações sobre o Apresentante/Requerente",
    )
    email = models.EmailField(blank=True, null=True, default="")
    dados_bancarios = models.OneToOneField(
        DadosBancarios,
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        related_name="%(class)s_dados_bancarios",
    )

    nacionalidade: str = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Nacionalidade",
        default="Brasileira",
    )

    profissao: str = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Profissão",
    )

    rg: str = models.CharField(max_length=100, blank=True, null=True, verbose_name="RG")

    estado_civil = models.ForeignKey(
        "home.EstadoCivil",
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="Estado Civil",
        help_text="Solteiro(a), Casado(a), Divorciado(a), Viúvo(a), etc.",
        related_name="apresentante_estado_civil",
    )

    endereco: str = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name="Endereço",
        help_text="Endereço completo do Apresentante/Requerente, incluindo Rua, Bairro, Cidade e Estado",
    )

    filiacao: str = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name="Filiação",
        help_text="Nome dos pais do Apresentante/Requerente",
    )

    nome_adquirente_parte: str = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        default="",
        verbose_name="Nome do Adquirente/Parte",
        help_text="Nome Completo do Adquirente/Parte",
    )

    criado_em: datetime = models.DateTimeField(auto_now_add=True, null=True)
    ativo: bool = models.BooleanField(default=True, verbose_name="Apresentante Ativo")

    class Meta:
        verbose_name = "Apresentante"
        verbose_name_plural = "Apresentantes"

    def __str__(self) -> str:
        nome_formatado = self.nome or "Não informado"

        return f"{nome_formatado}"

    def get_absolute_url(self):
        return reverse("pedidos:apresentante_detail", kwargs={"pk": self.pk})

    def get_email(self):
        return self.email or "Email Não informado"

    def qualificado(self) -> str:
        return f"{self.nome} - {self.get_documento_formatado_mascadado()}, {self.get_email() }, {formatar_telefone(self.telefone)}"

    def get_update_url(self):
        return (
            reverse("pedidos:apresentante_update", kwargs={"pk": self.pk})
            if self.pk
            else ""
        )

    def get_pedido_url(self):
        return reverse("pedidos:pedido_detail", kwargs={"pk": self.pedido.pk})

    @cached_property
    def documento_formatado(self) -> str:
        return self.get_documento_formatado()

    @cached_property
    def documento_mascarado(self) -> str:
        return self.get_documento_formatado_mascadado()

    @cached_property
    def first_name(self) -> str:
        if self.nome:
            return self.nome.replace("  ", " ").split(" ")[0]
        else:
            return ""

    @cached_property
    def documento_qualificado(self) -> str:
        return f"{self.tipo_documento.sigla}: {self.documento_formatado}"


class Imovel(EnderecoMixin, SequencialIDMixin, models.Model):
    id: uuid.uuid4 = UUIDPrimaryKeyField()
    numero_registro: str = models.CharField(
        "Número do Registro",
        max_length=100,
        blank=True,
        null=True,
    )
    tipo_registro = models.ForeignKey(
        "comum.TipoRegistroImobiliario",
        blank=True,
        verbose_name="Tipo Registro",
        null=True,
        on_delete=models.SET_NULL,
        related_name="tipo_registro_%(class)s",
    )
    atos = models.ForeignKey(
        "Ato",
        on_delete=models.CASCADE,
        null=True,
        related_name="imoveis",
    )

    cartorio: str = models.CharField(
        max_length=2,
        blank=True,
        null=True,
        default="1",
        verbose_name="Cartório",
    )
    livro: str = models.CharField(max_length=3, blank=True, null=True, default="0")
    descricao: str = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Descrição",
    )
    tipo_imovel = models.ForeignKey(
        TipoRegistro,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="Tipo de Imóvel",
        related_name="tipo_imovel",
    )
    anotacoes: str = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name="Anotações",
    )

    objects: ImovelManager = ImovelManager()

    class Meta:
        verbose_name = "Imóvel"
        verbose_name_plural = "Imóveis"

    def __str__(self) -> str:
        return self.identificacao or ""

    def get_absolute_url(self):
        return reverse("pedidos:imovel_detail", kwargs={"pk": self.pk})

    @cached_property
    def quantidade_atos(self):
        return self.pedido_ato_imovel.count()

    @cached_property
    def numero_registro_qualificado(self) -> str:
        # verificar se tipo_registro é valido
        if self.tipo_registro and self.numero_registro:
            return f"{self.tipo_registro.sigla} {self.numero_registro_formatado}"
        elif self.numero_registro:
            return f"M {self.numero_registro_formatado}"
        else:
            return ""

    @cached_property
    def numero_registro_formatado(self) -> str:
        try:
            # Extrair apenas números do numero
            numero_clean = int(re.sub(r"[^0-9]", "", str(self.numero_registro)))

            # Convertendo o valor para string e formatando com separador de ponto
            return f"{numero_clean:,.0f}".replace(",", ".")
        except Exception:
            logger.exception("Erro ao formatar número de registro")
            return self.numero_registro

    @cached_property
    def numero_simples(self) -> str:
        try:
            # Remova tudo que não seja número ou letra
            return re.sub(r"[^a-zA-Z0-9]", "", str(self.numero_registro))
        except Exception:
            logger.exception("Erro ao formatar número de registro")
            return self.numero_registro

    @cached_property
    def total_valor_atos(self):
        return (
            self.atos.aggregate(total=Sum("ato_praticavel__ato_praticavel_valor"))[
                "total"
            ]
            or 0
        )

    @cached_property
    def identificacao(self):
        partes = []

        if self.numero_registro_qualificado:
            partes.append(self.numero_registro_qualificado or "")

        if self.tipo_imovel:
            partes.append(str(self.tipo_imovel) or "")

        if self.logradouro:
            partes.append(self.logradouro or "")

        if self.numero:
            partes.append(self.numero or "")

        if self.quadra:
            partes.append(self.quadra or "")

        if self.lote:
            partes.append(self.lote or "")

        if self.complemento:  # Correção aqui
            partes.append(self.complemento or "")

        return " | ".join(partes)

    def get_alterar_url(self):
        return reverse("pedidos:imovel_update", kwargs={"pk": self.pk})

    def get_registro_url(self):
        base_url = reverse("home:abrir_livro02_pelo_numero")
        params_dict = {}

        if hasattr(self, "numero_registro") and self.numero_registro:
            params_dict["numero_informado"] = self.numero_registro

        if (
            hasattr(self, "tipo_registro")
            and self.tipo_registro
            and hasattr(self.tipo_registro, "sigla")
        ):
            params_dict["tipo_imovel"] = self.tipo_registro.sigla

        params = urlencode(params_dict)
        return f"{base_url}?{params}" if params else base_url


# parte que tem um papel no ato, como transmitente, adquirente, credor, devedor, etc
class Parte(DocumentoMixin, SequencialIDMixin, models.Model):
    id: uuid.uuid4 = UUIDPrimaryKeyField()
    nome: str = models.CharField(max_length=500, blank=True, null=True)
    estado_civil = models.ForeignKey(
        "home.EstadoCivil",
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="Estado Civil",
        related_name="pedidos_Parte_estado_civil",
    )

    tipo_regime_casamento = models.ForeignKey(
        "home.TipoRegimeCasamento",
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="Regime de Casamento",
        related_name="pedidos_Parte_tipo_regime_casamento",
        blank=True,
    )

    anotacoes: str = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name="Anotações",
    )
    conjuge = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    documento: str = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="CPF/CNPJ",
    )

    documento_auxiliar: str = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="RG ou Inscrição Estadual",
    )

    data_casamento = models.DateField(
        default=datetime.min.date(),
        null=True,
        verbose_name="Dt Casamento",
    )

    sexo: str = models.CharField(
        max_length=1,
        choices=TipoSexo.CHOICES,
        blank=True,
        null=True,
        verbose_name="Sexo",
        help_text="Sexo. Ex. Masculino, Feminino, etc.",
    )

    profissao: str = models.CharField(
        max_length=60,
        blank=True,
        null=True,
        default="N/A",
        verbose_name="Profissão",
        help_text="Profissão. Ex. Advogado, Engenheiro, Médico, etc.",
    )

    endereco: str = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        default="",
        verbose_name="Endereço",
    )

    nacionalidade: str = models.CharField(
        max_length=15,
        blank=True,
        null=True,
        default="brasileira",
    )

    criado_em: datetime = models.DateTimeField(auto_now_add=True, null=True)

    class Meta:
        verbose_name = "Parte"
        verbose_name_plural = "Partes"

    def __str__(self) -> str:
        return f"{self.nome}" or "Nome não informado"

    def get_absolute_url(self):
        return reverse("pedidos:parte_detalhes", kwargs={"pk": self.pk})

    def get_delete_url(self):
        return reverse("pedidos:parte_excluir", kwargs={"pk": self.pk})

    def get_update_url(self):
        return reverse("pedidos:parte_update", kwargs={"pk": self.pk})

    @cached_property
    def quantidade_atos(self) -> int:
        return 0  # self.pedido_ato_parte.count()

    def get_ato_url(self):
        try:
            participacao = Participacao.objects.filter(parte=self).first()
            if participacao:
                return participacao.ato.get_absolute_url()
        except Participacao.DoesNotExist:
            logger.exception(f"Parte {self} não possui participação em ato.")
            return None

    def descricao_participacao(self):
        try:
            participacao = Participacao.objects.filter(parte=self).first()
            if participacao:
                return participacao.papel.nome
        except Participacao.DoesNotExist:
            logger.exception(f"Parte {self} não possui participação em ato.")
            return None

    def percentual_participacao(self):
        try:
            participacao = Participacao.objects.filter(parte=self).first()
            if participacao:
                return participacao.percentual_participacao
        except Participacao.DoesNotExist:
            logger.exception(f"Parte {self} não possui participação em ato.")
            return None

    @cached_property
    def documento_formatado(self) -> str:
        return formatar_documento(self.documento)


class TipoTitulo(BaseModel):
    """
    Titulo apresentado no balcão para praticar o ato. Exemplos: Escritura, Contrato Particular, Carta Precatória, Cédula de Crédito Imobiliário,
    Cédula Rural, Requerimento, Usucapeão, etc.

    """

    nome: str = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    descricao: str = models.CharField(max_length=255, null=True, blank=True)
    home_titulo_protocolo = models.ForeignKey(
        "home.titulo",
        blank=True,
        verbose_name="Titulo do Protocolo",
        null=True,
        on_delete=models.SET_NULL,
        related_name="home_titulos_protocolo_%(class)s",
    )
    ativo: bool = models.BooleanField(default=True, verbose_name="Item utilizado")

    class Meta:
        verbose_name = "Tipo de Título"
        verbose_name_plural = "Tipos de Títulos"
        ordering = ["nome"]

    def __str__(self) -> str:
        return f"{self.nome}"

    @staticmethod
    def get_ativos() -> QuerySet["TipoTitulo"]:
        return TipoTitulo.objects.filter(ativo=True)

    @classmethod
    def get_tipo_titulo_provisorio(cls) -> "TipoTitulo":
        try:
            return cls.objects.get_or_create(nome=PROVISORIO, descricao=PROVISORIO)[0]
        except cls.MultipleObjectsReturned:
            return cls.objects.filter(nome__iexact=PROVISORIO)[0]

    @classmethod
    def get_tipo_titulo_prenotacao(cls) -> "TipoTitulo":
        try:
            tipo_titulo_obj, created = TipoTitulo.objects.get_or_create(
                nome=PRENOTACAO,
            )
        except TipoTitulo.MultipleObjectsReturned:
            logger.warning(
                "Mais de um tipo de título com o nome 'Prenotação' encontrado.",
            )
            tipo_titulo_obj = TipoTitulo.objects.filter(nome=PRENOTACAO).first()

        return tipo_titulo_obj

    @cached_property
    def mapeamento_antigo(self):
        """Retorna o mapeamento associado a este objeto, caso exista."""
        content_type = ContentType.objects.get_for_model(self)
        try:
            mapeamento = Mapeamento.objects.get(
                content_type_novo=content_type,
                object_id_novo=self.pk,
            )
            return mapeamento.content_object_antigo
        except Mapeamento.DoesNotExist:
            return None


class TipoEvento(SequencialIDMixin, models.Model):
    id: uuid.uuid4 = UUIDPrimaryKeyField()
    nome: str = models.CharField(max_length=100, blank=True)

    class Meta:
        verbose_name = "Tipo de Evento"
        verbose_name_plural = "Tipos de Evento"

    def __str__(self) -> str:
        return self.nome


class Evento(SequencialIDMixin, models.Model):
    id: uuid.uuid4 = UUIDPrimaryKeyField()
    nome: str = models.CharField(max_length=100, blank=True)
    tipo_evento = models.ForeignKey(TipoEvento, on_delete=models.CASCADE, null=True)
    pedido = models.ForeignKey(
        Pedido,
        on_delete=models.CASCADE,
        null=True,
        related_name="eventos",
    )
    history: AuditlogHistoryField = AuditlogHistoryField(pk_indexable=False)

    class Meta:
        verbose_name = "Evento"
        verbose_name_plural = "Eventos"

    def __str__(self) -> str:
        field_values = []
        for field in self._meta.get_fields():
            field_values.append(str(getattr(self, field.name, "")))
        return " ".join(field_values)


class TipoArmazenamento(SequencialIDMixin, models.Model):
    id: uuid.uuid4 = UUIDPrimaryKeyField()
    nome: str = models.CharField(max_length=100, blank=True)

    class Meta:
        verbose_name = "Tipo de Armazenamento"
        verbose_name_plural = "Tipos de Armazenamento"

    def __str__(self) -> str:
        return self.nome


class Anexo(SequencialIDMixin, models.Model):
    id: uuid.uuid4 = UUIDPrimaryKeyField()
    nome_arquivo: str = models.CharField(max_length=100, blank=True)
    endereco_arquivo: str = models.CharField(max_length=300, blank=True)
    tipo_armazenamento = models.ForeignKey(
        TipoArmazenamento,
        on_delete=models.CASCADE,
        null=True,
    )
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, null=True)

    class Meta:
        verbose_name = "Anexo"
        verbose_name_plural = "Anexos"

    def __str__(self) -> str:
        field_values = []
        for field in self._meta.get_fields():
            field_values.append(str(getattr(self, field.name, "")))
        return " ".join(field_values)


class Configuracao(SequencialIDMixin, models.Model):
    id: uuid.uuid4 = UUIDPrimaryKeyField()
    nome: str = models.CharField(max_length=100, blank=True)
    valor: str = models.CharField(max_length=100, blank=True)

    class Meta:
        verbose_name = "Configuração"
        verbose_name_plural = "Configurações"
        ordering = ["nome"]

    def __str__(self) -> str:
        return self.nome


class TipoEmolumento(SequencialIDMixin, BaseModel):
    """
    Itens da Tabela de Emolumentos.
    Registro de Compra e Venda, Hipoteca, Penhora, Alienação Fiduciária, etc.
    """

    id: uuid.uuid4 = UUIDPrimaryKeyField()
    nome: str = models.CharField(max_length=255, blank=True, null=True)
    descricao: str = models.CharField(max_length=255, null=True, blank=True)
    codigo: str = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name="Código",
    )

    home_emolumento = models.ForeignKey(
        "home.Emolumentos",
        blank=True,
        verbose_name="Emolumentos",
        null=True,
        on_delete=models.SET_NULL,
        related_name="home_emolumento_%(class)s",
    )

    home_emolumento_isento = models.ForeignKey(
        "home.Emolumentos",
        blank=True,
        verbose_name="Emolumentos Isento",
        null=True,
        on_delete=models.SET_NULL,
        related_name="home_emolumento_isento_%(class)s",
    )

    home_emolumento_50 = models.ForeignKey(
        "home.Emolumentos",
        blank=True,
        verbose_name="Emolumentos 50%",
        null=True,
        on_delete=models.SET_NULL,
        related_name="home_emolumento_50_%(class)s",
    )

    home_emolumento_75 = models.ForeignKey(
        "home.Emolumentos",
        blank=True,
        verbose_name="Emolumentos 75%",
        null=True,
        on_delete=models.SET_NULL,
        related_name="home_emolumento_75_%(class)s",
    )

    tipo_emolumento_isento = models.ForeignKey(
        "pedidos.TipoEmolumento",
        blank=True,
        verbose_name="Emolumentos Postgresql ligar Firebird",
        null=True,
        on_delete=models.SET_NULL,
        related_name="pedidos_emolumento_%(class)s",
    )

    tipo_emolumento_50 = models.ForeignKey(
        "pedidos.TipoEmolumento",
        blank=True,
        verbose_name="Tipo Emolumento com desconto de 50%",
        null=True,
        on_delete=models.SET_NULL,
        related_name="pedidos_tipo_emolumento_50_%(class)s",
    )

    tipo_emolumento_75 = models.ForeignKey(
        "pedidos.TipoEmolumento",
        blank=True,
        verbose_name="Tipo Emolumento com desconto de 75%",
        null=True,
        on_delete=models.SET_NULL,
        related_name="pedidos_tipo_emolumento_75_%(class)s",
    )

    # id_sequencial = models.BigIntegerField(null=True, default=1)

    ativo: bool = models.BooleanField(default=True, verbose_name="Item utilizado")

    class Meta:
        verbose_name = "Tipo de Emolumento"
        verbose_name_plural = "Tipos de Emolumentos"
        ordering = ["nome"]

    def __str__(self) -> str:
        if self.codigo is None:
            return self.nome
        return f"{self.nome} ({self.codigo})"

    @cached_property
    def mapeamento_antigo(self):
        """Retorna o mapeamento associado a este objeto, caso exista."""
        content_type = ContentType.objects.get_for_model(self)
        try:
            mapeamento = Mapeamento.objects.get(
                content_type_novo=content_type,
                object_id_novo=self.pk,
            )
            return mapeamento.content_object_antigo
        except Mapeamento.DoesNotExist:
            return None

    def get_tipo_emolumento_provisorio() -> "TipoEmolumento":
        return TipoEmolumento.get_provisorio()

    @staticmethod
    def get_provisorio() -> "TipoEmolumento":
        try:
            tipo_emolumento_obj, created = TipoEmolumento.objects.get_or_create(
                nome=PROVISORIO,
            )
        except TipoEmolumento.MultipleObjectsReturned:
            logger.warning(
                "Mais de um tipo de emolumento com o nome 'Provisório' encontrado.",
            )
            tipo_emolumento_obj = TipoEmolumento.objects.filter(
                nome=PROVISORIO,
            ).first()

        return tipo_emolumento_obj

    def get_tipo_emolumento_prenotacao():
        try:
            logger.debug(
                f"Tentando obter ou criar TipoEmolumento de Prenotação pelo codigo {CODIGO_PRENOTACAO_MG}.",
            )
            tipo_emolumento_obj, created = TipoEmolumento.objects.get_or_create(
                codigo=CODIGO_PRENOTACAO_MG,
                ativo=True,
                defaults={"nome": PRENOTACAO, "codigo": CODIGO_PRENOTACAO_MG},
            )
            if created:
                logger.debug(f"TipoEmolumento criado com ID: {tipo_emolumento_obj.id}")
            else:
                logger.debug(
                    f"TipoEmolumento existente encontrado com ID: {tipo_emolumento_obj.id}",
                )
        except TipoEmolumento.MultipleObjectsReturned:
            logger.warning(
                "Mais de um TipoEmolumento de Prenotação encontrado.",
            )
            tipo_emolumento_obj = TipoEmolumento.objects.filter(
                codigo=CODIGO_PRENOTACAO_MG,
                ativo=True,
            ).first()
            logger.debug(
                f"Primeiro TipoEmolumento ativo encontrado com ID: {tipo_emolumento_obj.id}",
            )
        except Exception as e:
            logger.exception(f"Erro inesperado ao obter ou criar TipoEmolumento: {e}")
            raise

        return tipo_emolumento_obj


class AtoPraticavel(SequencialIDMixin, BaseModel):
    """
    Atos Praticados pela serventia. Exemplos: Abertura de Matricula, Alienação Fiduciária,
        Alteração Contratual, Cancelamento de Ônus, Cancelamento de Hipoteca, Cancelamento de Penhora, etc.
    Não confundir com os itens da tabela de emolumentos que, embora tenham nomes parecidos, são custas cobradas pelos atos praticados.
    Não confundir com o Tipo de Ato que pode ser um Registro, Averbação, Matricula, etc.

    """

    id: uuid.uuid4 = UUIDPrimaryKeyField()

    nome: str = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )
    # codigo:str = models.CharField(max_length=20, blank=True, null=True, verbose_name="Código")
    prazo_legal = models.ForeignKey(
        PrazoLegal,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    descricao: str = models.CharField(max_length=255, null=True, blank=True)

    home_atos = models.ForeignKey(
        "home.AtoPratica",
        blank=True,
        verbose_name="Atos",
        null=True,
        on_delete=models.SET_NULL,
        related_name="home_ato_%(class)s",
    )

    ativo: bool = models.BooleanField(default=True, verbose_name="Item utilizado")

    ordem_do_grupo = models.BigIntegerField(
        null=True,
        default=1,
        verbose_name="Ordem do Grupo",
        help_text="Definir a ordem que os atos devem ser ordenados na tela",
    )

    class Meta:
        verbose_name = "Natureza de Ato"
        verbose_name_plural = "Naturezas de Ato"
        ordering = ["nome"]

    def __str__(self) -> str:
        return self.nome

    @cached_property
    def nome_com_codigo(self) -> str:
        """Retorna uma string com o nome e o código do objeto."""
        return f"{self.nome} ({self.codigo})"

    # Data prevista com base na data recebida somada aos dias do prazo_legal, usando o add_working_days do workalendar
    def get_data_prevista(self, data_inicio) -> date:
        """
        Calcula a data prevista adicionando os dias do prazo legal à data de início usando o Workalendar.

        Args:
        ----
            data_inicio (date): Data inicial.

        Returns:
        -------
            date: Data prevista.

        """
        return calcular_data_com_workalendar(data_inicio, self.prazo_legal.dias)

    @cached_property
    def mapeamento_antigo(self):
        """
        Retorna o mapeamento associado a este objeto, caso exista.

        Returns
        -------
            object: Objeto mapeado antigo, se existir. Caso contrário, None.

        """
        content_type = ContentType.objects.get_for_model(self)
        try:
            logger.debug(f"Buscando mapeamento antigo para o objeto com pk: {self.pk}")
            mapeamento = Mapeamento.objects.get(
                content_type_novo=content_type,
                object_id_novo=str(self.pk),
            )
            return mapeamento.content_object_antigo
        except Mapeamento.DoesNotExist:
            logger.info(
                f"Nenhum mapeamento antigo encontrado para o objeto com pk: {self.pk}",
            )
            return None

    def get_default_ato_praticavel():
        """
        Retorna ou cria uma AtoPraticavel com nome vazio.

        Returns
        -------
            AtoPraticavel: Objeto AtoPraticavel criado ou existente.

        """
        ato_praticavel_obj, created = AtoPraticavel.objects.get_or_create(nome="")
        if created:
            logger.info("Criada nova AtoPraticavel com nome vazio.")
        return ato_praticavel_obj

    def get_ato_praticavel_provisorio():
        """
        Retorna ou cria uma AtoPraticavel com nome 'Provisório'.

        Returns
        -------
            AtoPraticavel: Objeto AtoPraticavel criado ou existente.

        """
        ato_praticavel_obj, created = AtoPraticavel.objects.get_or_create(
            nome=PROVISORIO,
        )
        if created:
            logger.info("Criada nova AtoPraticavel com nome 'Provisório'.")
        return ato_praticavel_obj

    def get_ato_praticavel_prenotacao():
        """
        Retorna ou cria uma AtoPraticavel com nome 'Prenotação'.

        Returns
        -------
            AtoPraticavel: Objeto AtoPraticavel criado ou existente.

        """
        try:
            ato_praticavel_obj, created = AtoPraticavel.objects.get_or_create(
                nome=PRENOTACAO,
            )
            if created:
                logger.info("Criada nova AtoPraticavel com nome 'Prenotação'.")
        except AtoPraticavel.MultipleObjectsReturned:
            logger.warning(
                "Mais de uma AtoPraticavel com o nome 'Prenotação' encontrada.",
            )
            ato_praticavel_obj = AtoPraticavel.objects.filter(nome=PRENOTACAO).first()
        return ato_praticavel_obj


class Tabela(models.Model):
    id: uuid.uuid4 = UUIDPrimaryKeyField()
    data_inicio_validade = models.DateField(
        default=date(datetime.now().year, 1, 1),
        unique=True,
        verbose_name="Data Início",
        help_text="Data de início da validade da tabela.",
    )
    data_fim_validade = models.DateField(
        null=True,
        blank=True,
        default=date(datetime.now().year, 12, 31),
        verbose_name="Data Fim",
        help_text="Data de fim da validade da tabela.",
    )
    id_sistema_antigo = models.BigIntegerField(null=True, default=0)

    objects: TabelaManager = TabelaManager()

    class Meta:
        """Configura a meta informação da tabela."""

        verbose_name = "Tabela"
        verbose_name_plural = "Tabelas"
        ordering = ["data_inicio_validade"]

    def __str__(self) -> str:
        """Retorna a representação em string da tabela."""
        data_inicio = self.data_inicio_validade
        data_fim = self.data_fim_validade

        # Certifica-se de que as datas são objetos date antes de formatá-las
        str_data_inicio = (
            data_inicio.strftime(settings.DATE_FORMAT_STR)
            if isinstance(data_inicio, date)
            else data_inicio
        )
        str_data_fim = (
            data_fim.strftime(settings.DATE_FORMAT_STR)
            if isinstance(data_fim, date)
            else data_fim
        )

        return f"{str_data_inicio} - {str_data_fim}"

    def save(self, *args, **kwargs):
        """Sobrescreve o método save para garantir a validação completa."""
        self.full_clean()  # Garante que a validação completa seja chamada
        super().save(*args, **kwargs)

    @property
    def nome(self) -> str:
        """Propriedade que retorna o nome descritivo da tabela."""
        data_inicio = self.data_inicio_validade
        data_fim = self.data_fim_validade

        # Certifica-se de que as datas são objetos date antes de formatá-las
        str_data_inicio = (
            data_inicio.strftime(settings.DATE_FORMAT_STR)
            if isinstance(data_inicio, date)
            else data_inicio
        )
        str_data_fim = (
            data_fim.strftime(settings.DATE_FORMAT_STR)
            if isinstance(data_fim, date)
            else data_fim
        )

        return f"Validade de {str_data_inicio} até {str_data_fim}"

    def clean(self):
        """Validação para garantir que não há sobreposição de datas."""
        super().clean()
        self._validate_date_range()
        self._validate_date_overlap()

    def _validate_date_range(self) -> None:
        """Valida se a data de início é anterior à data de fim."""
        if self.data_inicio_validade >= self.data_fim_validade:
            msg = _(
                "A data de início da validade ({inicio}) deve ser anterior à data de fim da validade ({fim}).",
            ).format(inicio=self.data_inicio_validade, fim=self.data_fim_validade)
            raise ValidationError(msg)

    @transaction.atomic
    def _validate_date_overlap(self) -> None:
        """Valida se há sobreposição de datas com outras Tabelas de Emolumentos."""
        tabelas_existentes = (
            Tabela.objects.select_for_update()
            .filter(
                data_inicio_validade__lte=self.data_fim_validade,
                data_fim_validade__gte=self.data_inicio_validade,
            )
            .exclude(id=self.id)
        )

        if tabelas_existentes.exists():
            conflitos = [
                _("Tabela '{tabela}' ({inicio} - {fim})").format(
                    tabela=tabela.nome,
                    inicio=tabela.data_inicio_validade,
                    fim=tabela.data_fim_validade,
                )
                for tabela in tabelas_existentes
            ]
            msg = _(
                "As datas de validade ({inicio} - {fim}) sobrepõem-se com as seguintes tabelas: {conflitos}.",
            ).format(
                inicio=self.data_inicio_validade,
                fim=self.data_fim_validade,
                conflitos=", ".join(conflitos),
            )
            raise ValidationError(msg)

    # criar emolumento provisório
    def criar_emolumento_provisorio(self) -> "Emolumento":
        """Cria um emolumento provisório para a tabela."""
        return Emolumento.criar_provisorio(self)

    # tabela ativa
    @staticmethod
    def get_emolumentos(data_ato: date) -> QuerySet["Emolumento"]:
        """Obtem os emolumentos ativos na data do ato."""
        tabela = Tabela.objects.get_tabela(data_ato)
        return tabela.emolumentos.all()

    # tabela ativa
    @staticmethod
    def get_all(data_ato: date) -> QuerySet["TipoEmolumento"]:
        """Obtem os tipos de emolumentos ativos na data do ato."""
        tabela = Tabela.objects.get_tabela(data_ato)
        return TipoEmolumento.objects.filter(
            id__in=tabela.emolumentos.values_list(
                "tipo_emolumento",
                flat=True,
            ).distinct(),
        )

    @staticmethod
    def get_tipos_de_emolumento_ativos(data_ato: date) -> QuerySet["TipoEmolumento"]:
        """Obtem os tipos de emolumentos ativos na data do ato."""
        # Obtem a tabela atual...
        tabela: Tabela = Tabela.objects.get_tabela(data_ato)

        # Obtem os tipos de emolumentos ativos na tabela...
        tipos_de_emolumentos_ativos = TipoEmolumento.objects.filter(
            ativo=True,
            id__in=tabela.emolumentos.values_list(
                "tipo_emolumento",
                flat=True,
            ).distinct(),
        )
        # Retorna os tipos de emolumentos ativos na data do ato...
        return (
            tipos_de_emolumentos_ativos
            if tipos_de_emolumentos_ativos
            else TipoEmolumento.objects.none()
        )


class Fundo(models.Model):
    """Fundos RECOMP em MG, FUNCOMP em GO, etc."""

    TIPO_VALOR_CHOICES = (
        (PERCENTUAL, "Percentual"),
        (VALOR_FIXO, "Fixo"),
    )
    descricao: str = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        default="",
        verbose_name="Descrição",
        help_text="Descrição do fundo.",
    )
    tipo_valor: str = models.CharField(
        max_length=1,
        choices=TIPO_VALOR_CHOICES,
        default=PERCENTUAL,
        verbose_name="Tipo de Valor",
        help_text="Tipo de valor do fundo. Percentual ou Fixo.",
    )
    valor = models.DecimalField(
        default=0,
        blank=False,
        decimal_places=2,
        max_digits=10,
        verbose_name="Valor",
        help_text="Valor do fundo.",
    )

    def __str__(self) -> str:
        """Retorna a representação em string do fundo."""
        return f"{self.descricao} - {self.valor}"


class Emolumento(BaseModel):
    """Emolumento é o valor cobrado pelo serviço prestado em um cartório."""

    TIPO_VALOR_CHOICES = (
        ("P", "Percentual"),
        ("F", "Fixo"),
    )

    tabela = models.ForeignKey(
        Tabela,
        on_delete=models.CASCADE,
        null=True,
        related_name="emolumentos",
        verbose_name="Tabela",
        help_text="Tabela de emolumentos a qual este emolumento pertence.",
    )
    tipo_emolumento = models.ForeignKey(
        TipoEmolumento,
        on_delete=models.CASCADE,
        related_name="emolumento_tipo",
        verbose_name="Tipo de Emolumento",
        help_text="Tipo de emolumento a ser cobrado.",
    )
    valor = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        blank=False,
        verbose_name="Valor",
        help_text="Valor do emolumento.",
    )
    faixa_valor_inicio = models.DecimalField(
        default=0,
        blank=False,
        decimal_places=2,
        max_digits=10,
        verbose_name="Valor Inicial da Faixa",
        help_text="Valor inicial da faixa de valores para o cálculo do emolumento.",
    )
    faixa_valor_fim = models.DecimalField(
        blank=False,
        decimal_places=2,
        max_digits=10,
        default=Decimal("99999999.99"),
        verbose_name="Valor Final da Faixa",
        help_text="Valor final da faixa de valores para o cálculo do emolumento.",
    )
    taxa_fiscal_judiciaria = models.DecimalField(
        default=0,
        blank=False,
        decimal_places=2,
        max_digits=10,
        verbose_name="TFJ",
        help_text="Taxa estadual cobrada em cartórios para custear serviços judiciários. Varia conforme a legislação estadual e é calculada com base no serviço e valor do imóvel/negócio.",
    )
    fundo1_valor = models.DecimalField(
        default=0,
        blank=False,
        decimal_places=2,
        max_digits=10,
        verbose_name="Valor do Fundo 1",
        help_text="Fundo de Compensação dos Registradores Civis das Pessoas Naturais. RECOMP em MG, FUNCOMP em GO, etc.",
    )
    fundo1_descricao: str = models.CharField(
        max_length=100,
        blank=True,
        default="Fundo 1",
        null=True,
        verbose_name="Descrição do Fundo 1",
        help_text="Descrição do fundo1. Exemplo: RECOMPE em MG, FUNCOMP em GO, etc.",
    )
    fundo1_tipo_valor: str = models.CharField(
        max_length=1,
        choices=TIPO_VALOR_CHOICES,
        default=PERCENTUAL,
        verbose_name="Tipo de Valor do Fundo 1",
        help_text="Tipo de valor do fundo1. Percentual ou Fixo.",
    )
    fundo2_nome: str = models.CharField(
        max_length=100,
        blank=True,
        default="Fundo 2",
        null=True,
        verbose_name="Descrição do Fundo 2",
        help_text="Descrição do fundo2.",
    )
    fundo2_valor = models.DecimalField(
        default=0,
        blank=False,
        decimal_places=2,
        max_digits=10,
        verbose_name="Valor do Fundo 2",
        help_text="Reservado para fundo2.",
    )
    fundo2_tipo_valor: str = models.CharField(
        max_length=1,
        choices=TIPO_VALOR_CHOICES,
        default=PERCENTUAL,
        verbose_name="Tipo de Valor do Fundo 2",
        help_text="Tipo de valor do fundo2. Percentual ou Fixo.",
    )
    issqn_percentual = models.DecimalField(
        default=0,
        blank=False,
        decimal_places=2,
        max_digits=5,
        verbose_name="ISSQN %",
        help_text="Percentual. ISSQN a ser aplicado sobre o valor total da certidão.",
    )
    codigo: str = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name="Código",
        help_text="Código oficial do emolumento de acordo com a tabela de emolumentos.",
    )

    class Meta:
        verbose_name = "Emolumento"
        verbose_name_plural = "Emolumentos"

    def __str__(self) -> str:
        if self.tipo_emolumento.nome == PROVISORIO:
            # Emolumento provisório
            return f"{self.tipo_emolumento.nome}"

        if self.fundo1_tipo_valor == PERCENTUAL:  # percentual
            fundo1_saida = f"{self.fundo1_descricao}: {self.fundo1_calculado}%"
        else:
            fundo1_saida = f"{self.fundo1_descricao}: R${self.fundo1_calculado}"

        return (
            f"{self.tipo_emolumento.nome} "
            f"[{self.codigo or self.tipo_emolumento.codigo}] "
            f"({formatar_moeda(self.faixa_valor_inicio)} até "
            f"{formatar_moeda(self.faixa_valor_fim)}): "
            f"R$ {self.valor:.2f} | "
            f"TFJ: R$ {self.taxa_fiscal_judiciaria:.2f} | "
            f"{fundo1_saida} | "  # MG: fundo_estado
            f"ISSQN: {self.issqn_percentual}% - R$ {self.issqn_calculado:.2f} | "
            f"Total: R$ {self.total:.2f} | "
            f"Validade: {self.data_inicio_validade.strftime(settings.DATE_FORMAT_STR)} - "
            f"{self.data_fim_validade.strftime(settings.DATE_FORMAT_STR)}"
        )

    @cached_property
    def mapeamento_antigo(self):
        """Retorna o mapeamento associado a este objeto, caso exista."""
        content_type = ContentType.objects.get_for_model(self)
        try:
            mapeamento = Mapeamento.objects.get(
                content_type_novo=content_type,
                object_id_novo=self.pk,
            )
            return mapeamento.content_object_antigo
        except Mapeamento.DoesNotExist:
            return None

    @cached_property
    def issqn_calculado(self) -> Decimal:
        valor_final = (Decimal(self.issqn_percentual) / Decimal("100")) * Decimal(
            self.valor,
        )
        return arredondar_decimal_bancario(valor_final)

    @cached_property
    def fundo1_calculado(self) -> Decimal:
        """Calcula de acordo com o tipo fundo1_tipo_valor que pode ser percentual ou fixo."""
        if self.fundo1_tipo_valor == "P":
            valor_final = (Decimal(self.fundo1_valor) / Decimal("100")) * Decimal(
                self.valor,
            )
        else:
            valor_final = Decimal(self.fundo1_valor)
        return arredondar_decimal_bancario(valor_final)

    @cached_property
    def total(self):
        return (
            self.valor
            + self.taxa_fiscal_judiciaria
            + self.fundo1_calculado
            + self.issqn_calculado
        )

    @cached_property
    def data_inicio_validade(self) -> date:
        return self.tabela.data_inicio_validade

    @cached_property
    def data_fim_validade(self) -> date:
        return self.tabela.data_fim_validade

    @staticmethod
    def get_default_valor_ato() -> Decimal:
        return Emolumento.objects.get_or_create(
            ato_praticavel=TipoEmolumento.get_tipo_emolumento_provisorio(),
            valor=0,
        )[0]

    @staticmethod
    def criar_provisorio(tabela: Tabela) -> "Emolumento":
        tipo_emolumento_provisorio = TipoEmolumento.get_provisorio()
        emolumento_provisorio, created = Emolumento.objects.get_or_create(
            tabela=tabela,
            tipo_emolumento=tipo_emolumento_provisorio,
            defaults={
                "valor": 0,
                "faixa_valor_inicio": 0,
                "faixa_valor_fim": 99999999.99,
                "taxa_fiscal_judiciaria": 0,
                "fundo1_valor": 0,
                "fundo1_descricao": "Fundo 1",
                "fundo1_tipo_valor": "P",
                "fundo2_nome": "Fundo 2",
                "fundo2_valor": 0,
                "fundo2_tipo_valor": "P",
                "issqn_percentual": 0,
                "codigo": "",
            },
        )
        if created:
            logger.info(
                f"Emolumento 'Provisório' criado para a tabela {tabela}, com com o ID: {emolumento_provisorio.id}",
            )
        return emolumento_provisorio

    @cached_property
    def home_emolumento_id(self):
        return self.tipo_emolumento.home_emolumento_id

    @cached_property
    def home_emolumento_isento_id(self):
        return self.tipo_emolumento.home_emolumento_isento_id

    @cached_property
    def home_emolumento_50_id(self):
        return self.tipo_emolumento.home_emolumento_50_id

    @cached_property
    def home_emolumento_75_id(self):
        return self.tipo_emolumento.tipo_emolumento_75_id


class Titulo(BaseModel):
    """
    Representa um Titulo dentro de um Pedido no contexto de Projeto CEHTES.

    Um Titulo é um documento legal apresentado ao cartório para a prática de um ato, como por ex. Escritura, Contrato Particular,
    Carta Precatória, Cédula de Crédito Imobiliário, Cédula Rural, Requerimento, Usucapeão, etc.

    """

    id: uuid.uuid4 = UUIDPrimaryKeyField()
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, null=True)
    tipo_titulo = models.ForeignKey(TipoTitulo, on_delete=models.CASCADE, null=True)
    numero: str = models.CharField(max_length=100, blank=True, null=True)
    data = models.DateField(null=True)
    valor = models.DecimalField(
        default=0,
        blank=False,
        decimal_places=2,
        max_digits=10,
    )
    ativo: bool = models.BooleanField(default=True, verbose_name="Item utilizado")

    class Meta:
        verbose_name = "Título"
        verbose_name_plural = "Títulos"

    def __str__(self) -> str:
        return f"{self.tipo_titulo.nome} {self.numero} {self.data} {self.valor}"

    @staticmethod
    def get_titulo_provisorio_id() -> int:
        try:
            logger.debug("Iniciando busca pelo título provisório.")
            titulo_provisorio: Titulo | None = Titulo.get_titulo_provisorio()
            if titulo_provisorio and titulo_provisorio.tipo_titulo:
                logger.debug(f"Título provisório encontrado: {titulo_provisorio}")
                return titulo_provisorio.tipo_titulo.id
            else:
                logger.debug(
                    "Título provisório não possui tipo de título, retornando ID padrão 1377.",
                )
                return 1377
        except Exception as e:
            logger.exception(f"Erro ao obter o ID do título provisório: {e}")
            return 1377

    @classmethod
    def get_titulo_provisorio(cls) -> "Titulo":
        try:
            logger.debug("Iniciando busca ou criação do título provisório.")
            titulo_provisorio, created = Titulo.objects.get_or_create(
                numero=1377,
                defaults={
                    "tipo_titulo": TipoTitulo.get_tipo_titulo_provisorio(),
                    "valor": 0,
                },
            )
            if created:
                logger.debug(f"Título provisório criado: {titulo_provisorio}")
            else:
                logger.debug(f"Título provisório encontrado: {titulo_provisorio}")
            return titulo_provisorio
        except Exception as e:
            logger.exception(f"Erro ao obter ou criar o título provisório: {e}")
            # Aqui você pode decidir o que retornar em caso de falha, possivelmente um valor padrão ou None
            raise


class Ato(SequencialIDMixin, BaseModel):
    """
    Representa um Ato dentro de um Pedido de Protocolo no contexto de Projeto CEHTES.

    Um Ato pode ser um procedimento legal ou administrativo registrado em um cartório,
    como um Registro de Compra e Venda, Averbação de Casamento, Cancelamento de Penhora, etc.
    Cada Ato pode ter Atos Complementares associados, que são procedimentos adicionais
    necessários para a conclusão do Ato Principal.

    """

    id: uuid.uuid4 = UUIDPrimaryKeyField()
    pedido = models.ForeignKey(
        Pedido,
        on_delete=models.CASCADE,
        null=True,
        verbose_name="Pedido",
        related_name="atos",
    )
    tipo_titulo = models.ForeignKey(
        TipoTitulo,
        on_delete=models.CASCADE,
        null=True,
        verbose_name="Titulo",
        help_text="Escolha o tipo de documento que o cliente apresentou. Ex. Escritura, Contrato Particular, Carta Precatória, Cédula de Crédito Imobiliário, Cédula Rural, Requerimento, Usucapeão, etc.",
    )
    ato_praticavel = models.ForeignKey(
        AtoPraticavel,
        on_delete=models.CASCADE,
        null=True,
        related_name="ato_praticavel",
        verbose_name="Ato",
        help_text="O que o cliente deseja fazer com o documento (titulo) apresentado. Ex: Abertura de Matricula, Alienação Fiduciária, Alteração Contratual, Cancelamento de Ônus",
    )
    tipo_emolumento = models.ForeignKey(
        TipoEmolumento,
        on_delete=models.CASCADE,
        null=True,
        verbose_name="Emolumento",
        help_text="Selecione o Emolumento correspondente ao Ato, conforme tabela vigente. Ex. Registro de Compra e Venda, Hipoteca, Penhora, Alienação Fiduciária, etc. Se não souber, deixe como 'Provisório' ",
    )
    imovel_numero_registro: str = models.CharField(
        "Número do Registro",
        max_length=100,
        blank=True,
        null=True,
        help_text="Numero da Matrícula, Transcrição, Inscrição, Livro 02 ou Livro 03",
    )
    imovel_tipo_registro = models.ForeignKey(
        TipoRegistroImobiliario,
        max_length=1,
        blank=True,
        verbose_name="Tipo Registro",
        null=True,
        on_delete=models.SET_NULL,
        related_name="tipo_registro",
        help_text="Ex. Matrícula, Transcrição, Inscrição, Livro 02 ou Livro 03",
    )

    imovel_cartorio: str = models.CharField(
        max_length=2,
        blank=True,
        null=True,
        default="1",
        verbose_name="Cartório",
        help_text="Número do cartório do imóvel.",
    )

    data = models.DateField(null=True)

    criado_em = models.DateField(auto_now_add=True, null=True)

    tipo_tributacao = models.ForeignKey(
        TipoTributacao,
        on_delete=models.CASCADE,
        null=True,
        verbose_name="Tributação",
        help_text="Conforme legislação. Normal, Ex. SFH 50% etc",
    )

    valor_titulo = models.DecimalField(
        default=0,
        blank=False,
        decimal_places=2,
        max_digits=10,
        verbose_name="Valor do Titulo",
        help_text="Valor do titulo apresentado (DOI)",
    )

    valor_avaliacao = models.DecimalField(
        default=0,
        blank=False,
        decimal_places=2,
        max_digits=10,
        verbose_name="Valor da Avaliação",
        help_text="Valor da avaliação pela prefeitura (Balcão)",
    )

    ato = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="atos_complementares",
        verbose_name="Ato Principal",
        help_text="Selecione o Ato Principal se este registro for um Ato Complementar. O Ato Principal é o ato jurídico principal ao qual este ato está vinculado ou que ele complementa. Exemplos de Ato Complementares podem incluir averbações, cancelamentos ou retificações necessárias para a realização do Ato Principal.",
    )

    TIPO_ATO_CHOISE = (
        ("R", "Registro"),
        ("M", "Matrícula"),
        ("A", "Averbação"),
    )

    tipo_ato: str = models.CharField(
        max_length=1,
        default="R",
        choices=TIPO_ATO_CHOISE,
        verbose_name="Tipo de Ato",
        help_text="Identifica o tipo de ato. Registro = R, Matrícula = M, Averbação = A",
    )

    numero_ato: str = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Número do Ato",
        help_text="Número sequencial do ato dentro do tipo. Ex. 001, 002, etc.",
    )

    quantidade = models.IntegerField(
        default=1,
        verbose_name="Quantidade",
    )

    firebird_ids = models.JSONField(
        blank=True,
        null=True,
    )

    ordem_do_lancamento = models.BigIntegerField(
        null=True,
        default=1,
        verbose_name="Ordem de Lançamento do Item",
        help_text="Definir a ordem que os itens dos atos devem ser ordenados na tela",
    )

    objects: AtoManager = AtoManager()

    class Meta:
        verbose_name = "Ato"
        verbose_name_plural = "AtoPratica"

    def __str__(self) -> str:
        if self.numero_ato:
            return f"{self.nome} {self.tipo_ato}.{self.numero_ato}"
        return f"{self.nome}"

    # emolumento = models.ForeignKey(
    #     Emolumento,
    #     on_delete=models.CASCADE,
    #     null=True,
    #     verbose_name="Emolumento",
    #     help_text="Valor do emolumento associado à realização deste ato",
    # )

    def save(self, *args, **kwargs) -> None:
        """Sobrescreve o método de salvamento para incluir a validação."""
        self.clean()
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("pedidos:ato_detail", kwargs={"pk": self.pk})

    def get_prazo_calculado_em_horas(self) -> int:
        if self.ato_praticavel:
            return self.ato_praticavel.get_prazo_em_horas()
        return None

    @staticmethod
    def get_tipo_ato_registro() -> str:
        return "R"

    @staticmethod
    def get_complementares_agrupados_por_pedido(pedido) -> QuerySet:
        return (
            Ato.objects.filter(pedido=pedido, ato__isnull=True)
            .values("ato_praticavel__nome")
            .annotate(quantidade=Count("id"))
        )

    @staticmethod
    def get_complementares_agrupados_por_ato(ato) -> QuerySet:
        return (
            Ato.objects.filter(ato=ato)
            .values("ato_praticavel__nome")
            .annotate(quantidade=Count("id"))
        )

    @staticmethod
    def get_agrupados_por_titulo_principal(ato) -> QuerySet:
        return (
            Ato.objects.filter(ato=ato)
            .values("ato_praticavel__nome")
            .annotate(quantidade=Count("id"))
        )

    def get_ato_complementar_create_url(self):
        return reverse(
            "pedidos:ato_complementar_create",
            kwargs={"pedido_id": self.pedido_id, "ato_id": self.pk},
        )

    def titulo(self):
        return self.tipo_titulo.nome if self.tipo_titulo else ""

    @cached_property
    def numero_pedido(self):
        return self.pedido.numero_pedido if self.pedido else ""

    @cached_property
    def numero_protocolo(self):
        return (
            self.pedido.protocolo.numero_protocolo
            if self.pedido and self.pedido.protocolo
            else ""
        )

    @cached_property
    def nome_com_codigo(self):
        return (
            f"{self.ato_praticavel.nome} ({self.tipo_emolumento.codigo})".title()
            if self.ato_praticavel
            else None
        )

    @cached_property
    def chave_pedido_fb(self):
        return self.pedido.chave_pedido_fb if self.pedido else None

    @cached_property
    def imovel_tipo_registro_sigla(self) -> str:
        sigla = self.imovel_tipo_registro.sigla if self.imovel_tipo_registro else ""
        if not sigla:
            return (
                self.imovel_tipo_registro.nome[0].upper()
                if self.imovel_tipo_registro
                else "M"
            )
        return "M"

    @cached_property
    def numero_ri(self) -> str:
        return self.imovel_cartorio

    def is_ato(self):
        """Verifica se este ato é um ato principal."""
        return self.ato is None

    def is_ato_complementar(self):
        """Verifica se este ato é um ato complementar."""
        return self.ato is not None

    def get_valor_ato(self):
        if not hasattr(self, "_valor_ato"):
            self._valor_ato = Emolumento.objects.filter(
                tipo_emolumento=self.tipo_emolumento,
            ).first()
        return self._valor_ato

    def get_create_url(self):
        return reverse("pedidos:ato_create", kwargs={"pedido_id": self.pedido_id})

    def get_pedido_url(self):
        return self.pedido.get_absolute_url()

    def get_delete_url(self):
        return reverse("pedidos:ato_delete", kwargs={"pk": self.pk})

    def get_update_url(self):
        return reverse("pedidos:ato_update", kwargs={"pk": self.pk})

    def get_listar_url(self):
        return reverse("pedidos:atos_list", kwargs={"pedido_id": self.pedido_id})

    def get_adicionar_parte_url(self):
        return reverse("pedidos:participacao_create", kwargs={"pk": self.pk})

    @cached_property
    def data_prevista(self):
        if self.ato_praticavel:
            return self.ato_praticavel.get_data_prevista(self.criado_em)
        return None

    @cached_property
    def data_referencia(self) -> date:
        try:
            return self.data or timezone.now().date()
        except:
            return date.today()

    @cached_property
    def valor_referencia(self):
        # Trata None como 0 para comparação
        valor_titulo = self.valor_titulo if self.valor_titulo is not None else 0
        valor_avaliacao = (
            self.valor_avaliacao if self.valor_avaliacao is not None else 0
        )
        return max(valor_titulo, valor_avaliacao)

    @cached_property
    def emolumento(self):
        """
        Com base na data, localiza a tabela vigente e com base no valor do titulo
        localiza o emolumento e devolve o objeto completo do emolumento.
        """
        logger.debug(
            f"Buscando emolumento para ato {self.nome_com_codigo} com valor de referencia {self.valor_referencia} e data de referencia {self.data_referencia}",
        )
        emolumento = Tabela.objects.get_emolumento(
            valor_documento=self.valor_referencia,
            tipo_emolumento=self.tipo_emolumento,
            data_pratica_ato=self.data_referencia,
        )
        if emolumento is not None:
            return emolumento
        else:
            return None

    @cached_property
    def desconto_tipo_tributacao(self):
        calculo = 0
        if self.tipo_tributacao:
            calculo = arredondar_decimal_bancario(
                Decimal(self.tipo_tributacao.percentual_desconto) * Decimal("0.01"),
            )
        return calculo

    @cached_property
    def tributacao(self):
        return self.tipo_tributacao.nome if self.tipo_tributacao else "Normal"

    @cached_property
    def taxa_fiscal_judiciaria_com_desconto_tributacao(self):
        resultado = self.emolumento
        valor = resultado.taxa_fiscal_judiciaria if resultado else 0

        # CALCULAR CADA ATO COM A QUANTIDADE
        valor = valor * self.quantidade

        # ERRO IMPUTAVEL CARTORIO
        if self.tipo_tributacao.outros_codigo_trib_tj:
            if (
                self.tipo_tributacao.outros_codigo_trib_tj
                in get_tributacao_outros_cobrar_taxa_judiciaria(self)
            ):
                return valor
            else:
                return arredondar_decimal_bancario(
                    valor * (1 - self.desconto_tipo_tributacao),
                )
        else:
            return arredondar_decimal_bancario(
                valor * (1 - self.desconto_tipo_tributacao),
            )

        # return arredondar_decimal_bancario(valor * (1 - self.desconto_tipo_tributacao))

    @cached_property
    def emolumento_liquido_com_desconto_tributacao(self):
        resultado = self.emolumento
        valor = resultado.valor if resultado else 0

        # CALCULAR CADA ATO COM A QUANTIDADE
        valor = valor * self.quantidade

        return arredondar_decimal_bancario(valor * (1 - self.desconto_tipo_tributacao))

    @cached_property
    def fundo1_com_desconto_tributacao(self):
        resultado = self.emolumento
        valor = resultado.fundo1_calculado if resultado else 0

        # CALCULAR CADA ATO COM A QUANTIDADE
        valor = valor * self.quantidade

        return arredondar_decimal_bancario(valor * (1 - self.desconto_tipo_tributacao))

    @cached_property
    def total_com_desconto_tributacao(self):
        try:
            resultado = self.emolumento
            valor = resultado.total if resultado else 0

            # CALCULAR CADA ATO COM A QUANTIDADE
            valor = valor * self.quantidade

            desconto = self.desconto_tipo_tributacao
            return arredondar_decimal_bancario(valor * (1 - desconto))
        except Exception as e:
            logger.exception(f"Erro ao calcular total com desconto: {e}")
            return 0

    @cached_property
    def issqn_com_desconto_tributacao(self):
        resultado = self.emolumento
        valor = resultado.issqn_calculado if resultado else 0

        # CALCULAR CADA ATO COM A QUANTIDADE
        valor = valor * self.quantidade

        return arredondar_decimal_bancario(valor * (1 - self.desconto_tipo_tributacao))

    @cached_property
    def nome(self):
        return f"{self.ato_praticavel}".title() if self.ato_praticavel else None

    @cached_property
    def qualificacao(self) -> str:
        # if self.imovel:
        #     return f"{self.nome} → {self.imovel}"
        # else:
        return f"{self.nome}"
        # elif self.parte:
        #     return f"{self.tributacao} → {self.parte}"

        # return None

    @classmethod
    def construir_observacao(cls, atos: QuerySet) -> str:
        # Define atos para retirar como um set para otimizar a operação de verificação "not in"
        atos_a_retirar = {PRENOTACAO, PROVISORIO, ARQUIVAMENTO}

        # Utiliza list comprehension para construir a observação de maneira eficiente
        try:
            observacao = ", ".join(
                [
                    f"{ato.ato_praticavel.nome} {ato.imovel_tipo_registro.nome[0] or ''} {ato.imovel_numero_registro or ''}".strip()
                    for ato in atos
                    if ato.ato_praticavel.nome not in atos_a_retirar
                ],
            )
        except Exception:
            observacao = ""

        return str(observacao).upper()

    @cached_property
    def codigo_emolumento_individual(self):
        try:
            resultado = self.emolumento
            return resultado.codigo if resultado else ""
        except Exception as e:
            logger.exception(f"Erro ao buscar código do emolumento: {e}")
            return ""

    # BUSCAR NA TABALA DE EMOLUMENTOS O CODIGO DO EMOLUMENTO
    @cached_property
    def emolumento_relacionado(self) -> Emolumento:
        """INDIVIDUAL - RETORNAR CODIGO DO EMOLUMENTO, EMOLUMENTO, RECOMPE, TFJ, ISSQN."""
        maior_valor = max(self.valor_titulo, self.valor_avaliacao)

        # PostgreSQL BETWEEN
        return (
            Emolumento.objects.filter(tipo_emolumento_id=self.tipo_emolumento_id)
            .filter(
                faixa_valor_inicio__lte=maior_valor,
                faixa_valor_fim__gte=maior_valor,
            )
            .first()
        )

    def get_titulo_id(self):
        """
        Retorna o ID do título associado ao Ato, verificando se o tipo de título está presente,
        caso contrário, retorna o ID do primeiro ato complementar.
        """
        if self.tipo_titulo_id:
            return self.tipo_titulo.home_titulo_protocolo_id
        elif self.atos_complementares.exists():
            ato_complementar = self.atos_complementares.first()
            if not ato_complementar:
                return None
            return (
                ato_complementar.tipo_titulo.home_titulo_protocolo_id
                if ato_complementar.tipo_titulo
                else None
            )
        return None

    def to_dict(self):
        """Retorna um dicionário com as informações do ato para exportação."""
        tipo_imovel = (
            self.imovel_tipo_registro.nome[0] if self.imovel_tipo_registro_id else ""
        )
        titulo_id = self.get_titulo_id()
        try:
            ato_id = (
                self.ato_praticavel.home_atos_id
                if self.ato_praticavel_id
                else models_home.AtoPratica.get_ato_provisorio_id()
            )
        except AttributeError as e:
            logger.exception(f"Erro ao buscar ato_id: {e}")
            ato_id = models_home.AtoPratica.get_ato_provisorio_id()

        emolumento_id = (
            self.tipo_emolumento.home_emolumento_id
            if self.tipo_emolumento.home_emolumento
            else models_home.Emolumentos.get_emolumento_provisorio_id()
        )

        # valores individuais

        return {
            "VALOR_ITBI": self.valor_itbi,
            "VALOR_AVALIACAO": self.valor_avaliacao,
            "TIPO_IMOVEL": tipo_imovel,
            "QUANTIDADE": self.quantidade,
            "NUMERO_RI": self.imovel_cartorio,
            "NUMERO_ATO": self.numero_ato,
            "ATO_ID": ato_id,
            "CHAVE_EMOLUMENTOS": emolumento_id,
            "TITULO_ID": titulo_id,
            "NUMERO_IMOVEL": self.imovel_numero_registro,
            "TIPO_TRIBUTACAO_ID": self.percentual_desconto,
            "CODIGO_TABELA": self.codigo_tabela,
            "VALOR_EMOLUMENTO": self.valor_emolumento,
            "VALOR_FUNDO_ESTADO": self.valor_fundo_estado,
            "VALOR_TFJ": self.valor_tfj,
            "VALOR_ISSQN": self.valor_issqn,
        }

    @cached_property
    def home_ato_id(self) -> int:
        ato_id = None
        try:
            ato_id = (
                self.ato_praticavel.home_atos_id
                if self.ato_praticavel_id
                else models_home.AtoPratica.get_ato_provisorio_id()
            )
        except AttributeError as e:
            logger.exception(f"Erro ao buscar ato_id: {e}")
            ato_id = models_home.AtoPratica.get_ato_provisorio_id()

        return ato_id

    @cached_property
    def custas(self):
        from apps.home.helpers import get_custas_firebird

        tipo_tributacao_id = 0 if Decimal(self.valor_itbi) > 0 else 1

        if self.percentual_desconto == 50:
            tipo_tributacao_id = 4
        elif self.percentual_desconto == 75:
            tipo_tributacao_id = 14
        else:
            tipo_tributacao_id = 1

        tipo_tributacao_id = tipo_tributacao_id

        emolumento_id = (
            self.tipo_emolumento.home_emolumento_id
            if self.tipo_emolumento.home_emolumento
            else models_home.Emolumentos.get_emolumento_provisorio_id()
        )

        emolumento = home_models.Emolumentos.obter(
            emolumento_id,
            valor_documento=self.valor_itbi,
        )
        emolumento_id = emolumento.pk

        custas_por_tipo, emolumento_exportar_id = get_custas_firebird(
            self.percentual_desconto,
            emolumento.pk,
        )
        saida = custas_por_tipo.get(int(self.percentual_desconto), 1)
        return saida if emolumento.codigo_tabela != "0" else 1

    @cached_property
    def numero_titulo(self) -> str:
        return "1"

    @cached_property
    def valor_itbi(self) -> Decimal:
        return self.valor_titulo if self.valor_titulo else 0

    @cached_property
    def percentual_desconto(self) -> Decimal:
        return self.tipo_tributacao.percentual_desconto if self.tipo_tributacao else 0

    @cached_property
    def codigo_tabela(self) -> str:
        return self.emolumento_relacionado.codigo if self.emolumento_relacionado else ""

    @cached_property
    def codigo_ato_selo(self) -> str:
        # 4 primeiros digitos de codigo tabela
        return self.codigo_tabela[:4] if self.codigo_tabela else ""

    @cached_property
    def valor_emolumento(self) -> Decimal:
        return self.emolumento_relacionado.valor if self.emolumento_relacionado else 0

    @cached_property
    def chave_emolumento_ws_go(self) -> str:
        codigo_tabela = self.codigo_tabela[0:4]
        # CORRIGINDO O CODIGO PARA O FIREBIR
        if codigo_tabela == "4902":
            return "140"
        elif codigo_tabela == "8101":
            return "120"
        elif codigo_tabela == "8301":
            return "121"
        elif codigo_tabela == "8401":
            return "122"
        elif codigo_tabela == "8402":
            return "123"
        else:
            return ""

    @cached_property
    def valor_issqn(self) -> Decimal:
        return (
            self.emolumento_relacionado.issqn_calculado
            if self.emolumento_relacionado
            else 0
        )

    @cached_property
    def valor_tfj(self) -> Decimal:
        return (
            self.emolumento_relacionado.taxa_fiscal_judiciaria
            if self.emolumento_relacionado
            else 0
        )

    @cached_property
    def valor_fundo_estado(self) -> Decimal:
        return (
            self.emolumento_relacionado.fundo1_valor
            if self.emolumento_relacionado
            else 0
        )

    @cached_property
    def valor_total(self) -> Decimal:
        return (
            self.valor_emolumento
            + self.valor_tfj
            + self.valor_issqn
            + self.valor_fundo_estado
        )

    def duplicar_ato(self):
        print("Duplicar Ato")
        print("xxx")

    def exportar_para_fb(self: "Ato") -> None:
        from apps.pedidos.firebird import AtoUtils, atualizar_pedido_protocolo

        # SELAR NO SQL SERVER PROTOCOLO
        cartorio_model = apps.get_model("cartorios", "Cartorio")
        usar_selo_sql_server = cartorio_model.objects.values_list(
            "usar_selo_sql_server",
            flat=True,
        ).first()

        with FbConnection() as db:
            try:
                db.begin_transaction()

                # Lista para armazenar as chaves de todos os pedidos itens
                firebird_ids: list[int] = []

                # AtoUtils.excluir_ato_no_fb(self, db)
                for _ in range(self.quantidade):
                    pedido_item = AtoUtils.criar_ato_no_fb(self, db)
                    firebird_ids.append(pedido_item["CHAVE_PEDIDOS_ITENS"])

                # Armazena a lista de chaves no campo JSONField
                self.firebird_ids = firebird_ids

                db.commit()

                # ATUALIZAR OS VALORES DO PEDIDOS
                atualizar_pedido_protocolo(
                    pedido_id=self.pedido.chave_pedido_fb,
                    coluna_pedido="VALORRECEITAADICIONAL",
                    coluna_item="VALORRECEITAADICIONAL1",
                    db=db,
                )

                coluna_emolumento_item = (
                    "VALOREMOLUMENTO - VALOR_FUNDOESTADO"
                    if usar_selo_sql_server == "S"
                    else "VALOREMOLUMENTO"
                )

                atualizar_pedido_protocolo(
                    pedido_id=self.pedido.chave_pedido_fb,
                    coluna_pedido="VALOREMOLUMENTO",
                    coluna_item=coluna_emolumento_item,
                    db=db,
                )

                atualizar_pedido_protocolo(
                    pedido_id=self.pedido.chave_pedido_fb,
                    coluna_pedido="VALORFINAL",
                    coluna_item="VALORTOTALITEM",
                    db=db,
                )

                # atualizar_pedido_protocolo(
                #     pedido_id=self.pedido.chave_pedido_fb,
                #     coluna_pedido="VALORACERTO",
                #     coluna_item="VALORTOTALITEM",
                #     db=db,
                # )

                atualizar_pedido_protocolo(
                    pedido_id=self.pedido.chave_pedido_fb,
                    coluna_pedido="TAXA1",
                    coluna_item="TAXA1",
                    db=db,
                )

            except Exception as e:
                db.rollback()
                logger.exception(f"Erro ao exportar ato para o Firebird: {e}")

    @cached_property
    def descricao_tipo_ato(self) -> str:
        # TIPO DO ATO E NUMERO DO ATO
        tipo_ato = self.tipo_ato if self.tipo_ato else ""
        numero_ato = self.numero_ato if self.numero_ato else ""

        return str(tipo_ato + "." + numero_ato)


class Participacao(BaseModel):
    ato = models.ForeignKey(Ato, on_delete=models.CASCADE)
    parte = models.ForeignKey(
        Parte,
        on_delete=models.CASCADE,
        related_name="participacoes",
        verbose_name="Parte",
    )
    conjuge = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="conjuge_participacoes",
        verbose_name="Cônjuge",
        help_text="Relacionamento de cônjuge com a participação.",
    )
    papel = models.ForeignKey(
        "comum.TipoPapelParte",
        on_delete=models.CASCADE,
        verbose_name="Papel",
        null=True,
        blank=True,
    )
    percentual_participacao = models.DecimalField(
        blank=False,
        decimal_places=2,
        max_digits=5,
        help_text="Percentual de participação da parte no ato ou imóvel (ex: 30.00 para 30%)",
        default=100.00,
    )

    class Meta:
        verbose_name = "Participação"
        verbose_name_plural = "Participações"

    def __str__(self) -> str:
        return f"{self.parte} como {self.papel} com {self.percentual_participacao}% em {self.ato}"

    def save(self, *args, **kwargs) -> None:
        self.clean()
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("pedidos:participacao_detail", kwargs={"pk": self.pk})

    def get_create_url(self):
        return reverse("pedidos:participacao_create")

    def get_update_url(self):
        return reverse("pedidos:participacao_update", kwargs={"pk": self.pk})

    def get_parte_update_url(self):
        return self.parte.get_update_url()

    def get_conjuge_percentual(self) -> str:
        return (
            f"{self.conjuge.parte.nome} {self.conjuge.percentual_participacao}%"
            if self.conjuge
            else ""
        )


class OrgaoEmissor(BaseModel):
    """Orgão Emissor de Documentos."""

    nome: str = models.CharField(max_length=100, blank=True, null=True)
    sigla: str = models.CharField(max_length=10, blank=True, null=True)
    observacao = CKEditor5Field(blank=True, null=True)

    class Meta:
        verbose_name = "Orgão Emissor"
        verbose_name_plural = "Orgãos Emissor"

    def __str__(self) -> str:
        return self.nome

    def get_absolute_url(self):
        return reverse("pedidos:orgao_emissor_detail", kwargs={"pk": self.pk})

    def get_create_url(self):
        return reverse("pedidos:orgao_emissor_create")

    def get_update_url(self):
        return reverse("pedidos:orgao_emissor_update", kwargs={"pk": self.pk})

    def get_listar_url(self):
        return reverse(
            "pedidos:orgaos_emissores_list",
            kwargs={"pedido_id": self.pedido_id},
        )

    @staticmethod
    def criar_orgaos_emissores_padroes() -> None:
        logger.info("Populando Orgãos Emissores.")
        orgaos = [
            {
                "nome": "Cartório de Registro Civil",
                "sigla": "CRC",
                "observacao": "Responsável pela emissão de certidões de nascimento, casamento e óbito.",
            },
            {
                "nome": "Instituto Nacional do Seguro Social",
                "sigla": "INSS",
                "observacao": "Emite comprovantes e certidões de situação previdenciária.",
            },
            {
                "nome": "Secretaria da Receita Federal do Brasil",
                "sigla": "RFB",
                "observacao": "Responsável pela emissão do Cadastro de Pessoas Físicas (CPF).",
            },
            {
                "nome": "Secretaria de Segurança Pública",
                "sigla": "SSP",
                "observacao": "Emite carteiras de identidade (RG).",
            },
            {
                "nome": "Tribunal de Justiça",
                "sigla": "TJ",
                "observacao": "Responsável pela emissão de certidões judiciais, como certidão de distribuição.",
            },
            {
                "nome": "Ministério da Justiça",
                "sigla": "MJ",
                "observacao": "Emite certidões de antecedentes criminais.",
            },
            {
                "nome": "Departamento Estadual de Trânsito",
                "sigla": "DETRAN",
                "observacao": "Emite documentos relacionados a veículos e CNH.",
            },
            {
                "nome": "Prefeitura Municipal",
                "sigla": "PM",
                "observacao": "Emite alvarás, certidões de valor venal, e IPTU.",
            },
            {
                "nome": "Cartório de Projeto CEHTES",
                "sigla": "CRI",
                "observacao": "Responsável pelo Projeto CEHTES e emissão de matrículas e averbações.",
            },
            {
                "nome": "Cartório de Títulos e Documentos",
                "sigla": "CTD",
                "observacao": "Responsável pelo registro de documentos, como contratos e procurações.",
            },
            {
                "nome": "Instituto Nacional de Colonização e Reforma Agrária",
                "sigla": "INCRA",
                "observacao": "Emite documentos relacionados a imóveis rurais.",
            },
            {
                "nome": "Banco Central do Brasil",
                "sigla": "BACEN",
                "observacao": "Emite certidões sobre situação econômica e financeira.",
            },
            {
                "nome": "Junta Comercial",
                "sigla": "JC",
                "observacao": "Emite certidões de regularidade de empresas.",
            },
        ]

        for orgao in orgaos:
            OrgaoEmissor.objects.get_or_create(**orgao)


class Requerimento(BaseModel):
    """Um requerimento reune os documentos e instruções necessárias para o Ato."""

    ato_praticavel = models.ForeignKey(
        AtoPraticavel,
        on_delete=models.CASCADE,
        null=True,
        related_name="requerimentos",
        help_text="Ato para o qual o requerimento é necessário.",
    )

    observacao = CKEditor5Field(
        blank=True,
        null=True,
        help_text="Observações adicionais sobre o requerimento. Tais como instruções, embasamento legal, etc.",
    )

    obrigatorio: bool = models.BooleanField(
        default=False,
        help_text="Se o requerimento é obrigatório ou não para protocolar do pedido.",
    )

    ativo: bool = models.BooleanField(
        default=True,
        help_text="Se o requerimento está ativo ou não.",
    )

    class Meta:
        verbose_name = "Requerimento"
        verbose_name_plural = "Requerimentos"

    def __str__(self) -> str:
        return self.nome

    def get_absolute_url(self):
        return reverse("pedidos:requerimento_detail", kwargs={"pk": self.pk})

    def get_create_url(self):
        return reverse("pedidos:requerimento_create")

    def get_update_url(self):
        return reverse("pedidos:requerimento_update", kwargs={"pk": self.pk})

    def get_listar_url(self):
        return reverse(
            "pedidos:requerimentos_list",
            kwargs={"ato_praticavel_id": self.ato_praticavel_id},
        )

    def get_print_url(self):
        return reverse("pedidos:requerimento_print", kwargs={"pk": self.pk})

    def get_delete_url(self):
        return reverse("pedidos:requerimento_delete", kwargs={"pk": self.pk})

    # def get_url_protocolo(self):
    #     pedido = self.pedido
    #     return reverse(pedido.get_absolute_url()) if pedido else self.get_absolute_url()

    @cached_property
    def nome(self):
        return f"Requerimento para {self.ato_praticavel.nome}"

    @cached_property
    def quantidade_de_documentos(self):
        return self.documentos.count()


class DocumentoParaRequerimento(BaseModel):
    """Documento necessário para um requerimento."""

    nome: str = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Nome do Documento. Ex. Carta de Habite-se",
    )
    requerimento = models.ForeignKey(
        Requerimento,
        on_delete=models.CASCADE,
        null=True,
        related_name="documentos",
        help_text="Requerimento para o qual o documento é necessário.",
    )
    observacao = CKEditor5Field(
        blank=True,
        null=True,
        help_text="Observações adicionais sobre o documento. Tais como instruções, embasamento legal, etc.",
    )

    prazo_de_validade = models.IntegerField(
        default=0,
        help_text="Prazo de Validade do documento em dias.",
    )

    orgao_emissor = models.ForeignKey(
        OrgaoEmissor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Orgão Emissor do Documento.",
    )

    obrigatorio: bool = models.BooleanField(
        default=False,
        help_text="Se o documento é obrigatório ou não para protocolar.",
    )

    justificativa = CKEditor5Field(
        blank=True,
        null=True,
        help_text="Justificativa para a obrigatoriedade do documento.",
    )

    ativo: bool = models.BooleanField(
        default=True,
        help_text="Se o documento está ativo ou não.",
    )

    imagem = models.ImageField(
        upload_to="requerimentos/documentos/exemplos/",
        blank=True,
        null=True,
        help_text="Imagem do documento.",
    )

    class Meta:
        verbose_name = "Documento para Requerimento"
        verbose_name_plural = "Documentos para Requerimentos"

    def __str__(self) -> str:
        return f"{self.nome} para {self.requerimento}"

    def get_absolute_url(self):
        return reverse(
            "pedidos:documento_para_requerimento_detail",
            kwargs={"pk": self.pk},
        )

    def get_create_url(self):
        return reverse("pedidos:documento_para_requerimento_create")

    def get_update_url(self):
        return reverse(
            "pedidos:documento_para_requerimento_update",
            kwargs={"pk": self.pk},
        )

    def get_listar_url(self):
        return reverse(
            "pedidos:documentos_para_requerimento_list",
            kwargs={"requerimento_id": self.requerimento_id},
        )


# SEMPRE COBRAR TAXA JUDICIARIA
def get_tributacao_outros_cobrar_taxa_judiciaria(self) -> list:
    return list(
        TipoTributacao.objects.filter(sempre_cobrar_taxa_judiciaria=True).values_list(
            "id",
            flat=True,
        ),
    )


def get_ato_praticavel_prenotacao():
    """
    Obtém a natureza do ato de prenotação.

    Returns
    -------
        AtoPraticavel: Instância da natureza do ato de prenotação.

    """
    AtoPraticavel = apps.get_model("pedidos", "AtoPraticavel")
    return AtoPraticavel.get_ato_praticavel_prenotacao()


def get_tipo_emolumento_prenotacao():
    """
    Obtém o tipo de emolumento para prenotação.

    Returns
    -------
        TipoEmolumento: Instância do tipo de emolumento de prenotação.

    """
    return TipoEmolumento.get_tipo_emolumento_prenotacao()


def get_default_tipo_tributacao():
    """
    Obtém o tipo de tributação padrão.

    Returns
    -------
        TipoTributacao: Instância do tipo de tributação padrão.

    """
    return TipoTributacao.get_default_tipo_tributacao()


def get_tipo_titulo_prenotacao():
    """
    Obtém o tipo de título para prenotação.

    Returns
    -------
        TipoTitulo: Instância do tipo de título de prenotação.

    """
    return TipoTitulo.get_tipo_titulo_prenotacao()


def create_ato(
    ato_praticavel: models.Model,
    pedido: models.Model,
    tipo_emolumento: models.Model,
    data: Any,
    tipo_tributacao: models.Model,
    tipo_titulo: models.Model,
) -> models.Model:
    """
    Cria uma nova instância de Ato.

    Args:
    ----
        ato_praticavel: Instância de AtoPraticavel.
        pedido: Instância de Pedido.
        tipo_emolumento: Instância de TipoEmolumento.
        data: Data de entrada do pedido.
        tipo_tributacao: Instância de TipoTributacao.
        tipo_titulo: Instância de TipoTitulo.

    Returns:
    -------
        Ato: Instância de Ato criada.

    """
    # Obtém o modelo Ato
    Ato = apps.get_model("pedidos", "Ato")

    # Log de debug informando os parâmetros recebidos
    logger.debug(
        "Criando Ato com os seguintes parâmetros: ato_praticavel=%s, pedido=%s, tipo_emolumento=%s, data=%s, tipo_tributacao=%s, tipo_titulo=%s",
        ato_praticavel,
        pedido,
        tipo_emolumento,
        data,
        tipo_tributacao,
        tipo_titulo,
    )

    # Cria a instância de Ato
    ato_instance = Ato(
        ato_praticavel=ato_praticavel,
        pedido=pedido,
        tipo_emolumento=tipo_emolumento,
        data=data,
        tipo_tributacao=tipo_tributacao,
        tipo_titulo=tipo_titulo,
    )

    # Log de debug informando a criação da instância de Ato
    logger.debug("Instância de Ato criada: %s", ato_instance)

    return ato_instance
