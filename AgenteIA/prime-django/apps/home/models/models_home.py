import contextlib
import io
import logging
import re
import uuid
import xml.etree.ElementTree as ET
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from enum import Enum
from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING, Optional
from urllib.parse import urlencode

import pytz
from auditlog.models import AuditlogHistoryField
from dateutil.relativedelta import relativedelta
from django.apps import apps
from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied, ValidationError
from django.db import IntegrityError, connection, models, transaction
from django.db.models import (
    Case,
    F,
    IntegerField,
    Max,
    OuterRef,
    Q,
    QuerySet,
    Subquery,
    Sum,
    Value,
    When,
)
from django.db.models.functions import Upper
from django.templatetags.static import static
from django.urls import reverse
from django.utils import timezone
from django.utils.timezone import datetime
from django_ckeditor_5.fields import CKEditor5Field
from sequences import get_next_value
from unidecode import unidecode

from apps.cartorios.models import Usuario as User
from apps.comum.helpers import ajustar_sequence
from apps.comum.mixins import (
    ConfiguracaoMixin,
)
from apps.comum.models import (
    BaseModel,
    TipoRegistro,
    UnidadeFederativa,
)
from apps.comum.models import UnidadeFederativa as Uf
from apps.comum.utils import CalendarioBrasileiroPersonalizado, formatar_moeda
from apps.home import helpers, managers
from apps.home.models import models_certidoes
from apps.home.padroes import *
from apps.home.services import firebird, sqlserver
from apps.home.tipos import (
    CartorioNumero,
    TipoAtivoCancelado,
    TipoAto,
    TipoFaseAgenda,
    TipoParte,
    TipoSexo,
    TipoSimNao,
    TipoStatusProtocolo,
)
from apps.pedidos.models import TipoEmolumento
from core.middlewares import get_current_user
from core.utils.firebird_utils import FbConnection
from core.utils.formatacoes import (
    formatar_documento,
    formatar_documento_com_descricao,
    formatar_nome,
    somente_numeros,
)

logger = logging.getLogger(__name__)

logger.debug(f"Iniciando {__name__}")

imported = True

if TYPE_CHECKING:
    from apps.home.managers import Livro01ProtocoloQuerySet
    from apps.home.models import PedidoCertidao, TipoClasseRegistro


# SEMPRE COBRAR TAXA JUDICIARIA
def get_tributacao_outros_cobrar_taxa_judiciaria(self) -> list:
    return list(
        TipoTributacao.objects.filter(sempre_cobrar_taxa_judiciaria=True).values_list(
            "id",
            flat=True,
        ),
    )


def anexo_with_id(instance, filename: str) -> str:
    return "{}/anexo/{}".format(f"{instance.id}", filename)


def anexo_with_numero_protocolo(instance, filename) -> str:
    return "{}/anexo/{}".format(f"{instance.numero_protocolo}", filename)


class SNBooleanField(models.CharField):
    description = "Boolean field that stores 'S' or 'N' in the database."

    def __init__(self, *args, **kwargs):
        kwargs["max_length"] = 1
        kwargs["choices"] = (("S", "Sim"), ("N", "Não"))
        kwargs["default"] = "N"
        super().__init__(*args, **kwargs)

    def from_db_value(self, value, expression, connection):
        if value is None:
            return value
        return value == "S"

    def to_python(self, value):
        if isinstance(value, bool):
            return value
        if value in ("S", "N"):
            return value == "S"
        return value

    def get_prep_value(self, value):
        if value is None:
            return value
        return "S" if value else "N"


class TipoClasseRegistro(models.Model):
    URBANO = "U"
    RURAL = "R"
    LOTE = "L"
    CONDOMINIO = "C"
    TODAS = "T"

    CHOICES = (
        (URBANO, "Urbano"),
        (RURAL, "Rural"),
        (LOTE, "Lote"),
        (CONDOMINIO, "Condomínio"),
        (TODAS, "Todas"),
    )

    _choice_dict = dict(CHOICES)

    descricao: str = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        unique=True,
    )
    letra: str = models.CharField(
        max_length=1,
        choices=CHOICES,
        default=URBANO,
        unique=True,
    )

    class Meta:
        verbose_name = "Tipo de Classe de Registro"
        verbose_name_plural = "Tipos de Classe de Registro"

    def __str__(self) -> str:
        return self.descricao

    @classmethod
    def get_descricao(cls, value) -> str:
        return cls._choice_dict.get(value, "Outros")

    @classmethod
    def criar_padroes(cls) -> None:
        for choice in cls.CHOICES:
            cls.objects.get_or_create(letra=choice[0], descricao=choice[1])


class UUIDPrimaryKeyField(models.UUIDField):
    def __init__(self, *args, **kwargs) -> None:
        kwargs["primary_key"] = True
        kwargs["default"] = uuid.uuid4
        kwargs["editable"] = False
        kwargs["verbose_name"] = "ID"
        super().__init__(*args, **kwargs)

    @staticmethod
    def generate_uuid() -> uuid.UUID:
        return uuid.uuid4()


class TipoTransacaoFinanceira(BaseModel):
    """Tipo de Transação Financeira: Receita ou Despesa."""

    RECEITA = "Receita"
    DESPESA = "Despesa"
    DEVOLUCAO = "Devolução"
    SAIDA = "Saida"

    CHOICES = (
        (RECEITA, "Receita"),
        (DESPESA, "Despesa"),
        (DEVOLUCAO, "Devolução"),
        (SAIDA, "Saida"),
    )

    descricao: str = models.CharField(
        max_length=300,
        blank=True,
        null=True,
        default="",
        unique=True,
        choices=CHOICES,
    )

    class Meta:
        verbose_name = "Tipo de Transação Financeira"
        verbose_name_plural = "Tipos de Transações Financeiras"
        ordering = ["descricao"]

    def __str__(self) -> str:
        return self.descricao

    _choice_dict = dict(CHOICES)

    @classmethod
    def get_receita(cls) -> "TipoTransacaoFinanceira":
        return cls.objects.get_or_create(descricao=cls.RECEITA)[0]

    @classmethod
    def get_despesa(cls) -> "TipoTransacaoFinanceira":
        return cls.objects.get_or_create(descricao=cls.DESPESA)[0]

    @classmethod
    def get_devolucao(cls) -> "TipoTransacaoFinanceira":
        return cls.objects.get_or_create(descricao=cls.DEVOLUCAO)[0]

    @classmethod
    def get_saida(cls) -> "TipoTransacaoFinanceira":
        return cls.objects.get_or_create(descricao=cls.SAIDA)[0]

    @classmethod
    def receita_id(cls) -> int:
        return cls.get_receita().id

    @classmethod
    def despesa_id(cls) -> int:
        return cls.get_despesa().id

    @classmethod
    def devolucao_id(cls) -> int:
        return cls.get_devolucao().id

    @classmethod
    def saida_id(cls) -> int:
        return cls.get_saida().id

    @classmethod
    def criar_padroes(cls) -> None:
        cls.get_receita()
        cls.get_despesa()
        cls.get_devolucao()
        cls.get_saida()


class TipoOperacaoFinanceira(BaseModel):
    """Forma de Pagamento: Dinheiro, Cartão Crédito, Pix, Cartão Crédito, Transferência Bancária etc."""

    descricao: str = models.CharField(
        max_length=300,
        blank=True,
        null=True,
        default="",
        unique=True,
    )

    ordem_exibir = models.BigIntegerField(blank=True, null=True, default=1)

    grupo_dinheiro = SNBooleanField(
        blank=True,
        null=True,
    )

    grupo_entradas = SNBooleanField(
        blank=True,
        null=True,
    )

    tipo_pagamento_id_sistema_antigo = models.BigIntegerField(null=True, default=1)

    valor_default_transacao = models.BigIntegerField(blank=True, null=True, default=1)

    class Meta:
        verbose_name = "Tipo de Operação Financeira"
        verbose_name_plural = "Tipos de Operações Financeiras"
        ordering = ["descricao"]

    def __str__(self) -> str:
        return self.descricao

    @classmethod
    def devolucao_id(cls) -> "TipoOperacaoFinanceira":
        return cls.objects.get_or_create(descricao="Devolução")[0].id

    @classmethod
    def saida_id(cls) -> "TipoOperacaoFinanceira":
        return cls.objects.get_or_create(descricao="Saída")[0].id

    @classmethod
    def despesa_id(cls) -> "TipoOperacaoFinanceira":
        return cls.objects.get_or_create(descricao="Despesa")[0].id

    @classmethod
    def criar_padroes(cls) -> None:
        cls.objects.get_or_create(descricao="Dinheiro")
        cls.objects.get_or_create(descricao="Cartão de Crédito")
        cls.objects.get_or_create(descricao="Pix")
        cls.objects.get_or_create(descricao="Transferência Bancária")
        cls.objects.get_or_create(descricao="Boleto Bancário")
        cls.objects.get_or_create(descricao="Cheque")
        cls.objects.get_or_create(descricao="Cartão de Débito")
        cls.objects.get_or_create(descricao="ONR")
        cls.objects.get_or_create(descricao="TED")
        cls.objects.get_or_create(descricao="Devolução")
        cls.objects.get_or_create(descricao="Saída")
        cls.objects.get_or_create(descricao="Despesa")
        cls.objects.get_or_create(descricao="Devolução (Dinheiro)")
        cls.objects.get_or_create(descricao="Devolução (Pix)")
        cls.objects.get_or_create(descricao="Saída - Dinheiro")
        cls.objects.get_or_create(descricao="Saída - Cheque")


class TipoCategoriaFinanceira(BaseModel):
    """Categoria Financeira: Geral, Protocolo, Pedido de Certidão, etc."""

    descricao: str = models.CharField(
        max_length=300,
        blank=True,
        null=True,
        default="",
        unique=True,
    )

    class Meta:
        verbose_name = "Categoria Financeira"
        verbose_name_plural = "Categorias Financeiras"
        ordering = ["descricao"]

    def __str__(self) -> str:
        return self.descricao

    @classmethod
    def get_geral(cls) -> "TipoCategoriaFinanceira":
        return cls.objects.get_or_create(
            id="1",
            defaults={"descricao": "Geral"},
        )[0]

    @classmethod
    def get_protocolo(cls) -> "TipoCategoriaFinanceira":
        return cls.objects.get_or_create(
            id="2",
            defaults={"descricao": "Protocolo"},
        )[0]

    @classmethod
    def get_pedido_certidao(cls) -> "TipoCategoriaFinanceira":
        return cls.objects.get_or_create(
            id="3",
            defaults={"descricao": "Pedido de Certidão"},
        )[0]

    @classmethod
    def criar_padroes(cls) -> None:
        cls.get_geral()
        cls.get_protocolo()
        cls.get_pedido_certidao()


class StatusProtocolo(BaseModel):
    EM_ANDAMENTO = "Em Andamento"
    EXIGENCIA = "Exigência"
    CANCELADO = "Cancelado"
    REGISTRADO = "Registrado"
    SUBJUDICE = "SubJudice"
    EM_REGISTRO = "Em Registro"
    PRONTO_PARA_REGISTRAR = "Pronto para Registrar"
    DISTRIBUIDO = "Distribuido"
    EM_ANALISE = "Em Análise"
    REENTRADA = "Reentrada"

    # Tupla de escolhas para o campo 'descricao'
    CHOICES = (
        (EM_ANDAMENTO, "Em Andamento"),
        (EXIGENCIA, "Exigência"),
        (CANCELADO, "Cancelado"),
        (REGISTRADO, "Registrado"),
        (SUBJUDICE, "Sub Judice"),
        (EM_REGISTRO, "Em Registro"),
        (PRONTO_PARA_REGISTRAR, "Pronto para Registrar"),
        (DISTRIBUIDO, "Distribuido"),
        (EM_ANALISE, "Em Análise"),
        (REENTRADA, "Reentrada"),
    )

    descricao: str = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        choices=CHOICES,
    )
    finalizar: str = models.CharField(
        max_length=1,
        blank=True,
        null=True,
        default=TipoSimNao.NAO,
        choices=TipoSimNao.CHOICES,
    )

    objects: managers.StatusProtocoloManager = managers.StatusProtocoloManager()

    class Meta:
        verbose_name = "Status do Protocolo"
        verbose_name_plural = "Status dos Protocolos"

    def __str__(self) -> str:
        return self.descricao if self.descricao else ""

    _choice_dict = dict(CHOICES)

    @classmethod
    def get_descricao(cls, value) -> str:
        return cls._choice_dict.get(value, "Em Andamento")

    @classmethod
    def get_em_andamento(cls) -> "StatusProtocolo":
        return cls.objects.get_or_create(descricao=cls.EM_ANDAMENTO)[0]

    @classmethod
    def get_exigencia(cls) -> "StatusProtocolo":
        return cls.objects.get_or_create(descricao=cls.EXIGENCIA)[0]

    @classmethod
    def get_concluido(cls) -> "StatusProtocolo":
        return cls.objects.get_or_create(descricao=cls.REGISTRADO)[0]

    @classmethod
    def get_id_status_concluido(cls) -> int:
        return (
            cls.objects.get_or_create(descricao=cls.REGISTRADO)[0].id
            if cls.objects.get_or_create(descricao=cls.REGISTRADO)
            else 0
        )

    @classmethod
    def get_ids_cancelados_e_concluidos(cls) -> list[int]:
        # CANCELADOS E REGISTRADOS
        registrado = cls.objects.get_or_create(descricao=cls.REGISTRADO)[0]
        cancelado = cls.objects.get_or_create(descricao=cls.CANCELADO)[0]

        # retonrar os ids
        return [registrado.id, cancelado.id]

    @classmethod
    def get_id_status_exigencia(cls) -> int:
        status_exigencia = cls.objects.get_or_create(descricao=cls.EXIGENCIA)[0]
        return status_exigencia.id if status_exigencia else 0

    @classmethod
    def em_exigencia_positiva(cls) -> "StatusProtocolo":
        return cls.objects.get_or_create(descricao=cls.EXIGENCIA)[0]

    @classmethod
    def get_id_status_exigencia_positiva(cls) -> int:
        status_exigencia = cls.objects.get_or_create(descricao=cls.EXIGENCIA)[0]
        return status_exigencia.id if status_exigencia else 0

    @classmethod
    def get_id_status_cancelado(cls) -> int:
        status_cancelado = cls.objects.get_or_create(descricao=cls.CANCELADO)[0]
        return status_cancelado.id if status_cancelado else 0

    @classmethod
    def get_registrado(cls) -> "StatusProtocolo":
        return cls.objects.get_or_create(descricao=cls.REGISTRADO)[0]

    @classmethod
    def get_subjudice(cls) -> "StatusProtocolo":
        return cls.objects.get_or_create(descricao=cls.SUBJUDICE)[0]

    @classmethod
    def get_em_registro(cls) -> "StatusProtocolo":
        return cls.objects.get_or_create(descricao=cls.EM_REGISTRO)[0]


class Anexo(models.Model):
    nome: str = models.CharField(max_length=300, blank=True, null=True, default="")
    descricao: str = models.CharField(max_length=300, blank=True, null=True, default="")
    arquivo = models.FileField(upload_to="anexos/", blank=True, null=True)
    created_at: datetime = models.DateTimeField(auto_now_add=True)
    updated_at: datetime = models.DateTimeField(auto_now=True)
    content_type = models.ForeignKey(ContentType, on_delete=models.SET_NULL, null=True)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="anexos",
        blank=True,
        null=True,
    )

    objects = models.Manager()

    class Meta:
        verbose_name = "Anexo"
        verbose_name_plural = "Anexos"

    def __str__(self) -> str:
        return self.nome if self.nome else "Sem nome"

    def delete(self, *args, **kwargs):
        msg = "Este registro não pode ser excluído."
        raise PermissionDenied(msg)

    @cached_property
    def nome_do_arquivo(self) -> str:
        return self.arquivo.name.split("/")[-1]

    def vincular_imovel(self) -> None:
        # Extrai o número do imóvel do nome do arquivo, assumindo que esteja antes do '.pdf'
        try:
            # Primeiro, remove o sufixo '.pdf' para isolar o identificador
            identificador_bruto = self.nome_do_arquivo.split(".pdf")[0]

            # Remove pontos do identificador
            identificador_sem_pontos = identificador_bruto.replace(".", "")

            # Remove zeros à esquerda
            numero_imovel = identificador_sem_pontos.lstrip("0")

            # Busca por um imóvel com esse número ajustado
            imovel = Livro02.objects.get(numero=numero_imovel)

            # Atualização do object_id para o ID do imóvel encontrado
            self.object_id = imovel.id
            self.save()
        except (IndexError, ObjectDoesNotExist, ValueError):
            # Tratamento de erro se o número ajustado não for encontrado ou o imóvel não existir
            logger.info(f"Erro ao vincular o imóvel para o anexo {self.nome}: ")


class TipoRegimeCasamento(models.Model):
    descricao_regime: str = models.CharField(max_length=200, blank=True, null=True)
    pacto: str = models.CharField(
        max_length=1,
        blank=True,
        null=True,
        default=TipoSimNao.NAO,
        choices=TipoSimNao.CHOICES,
    )
    exibir: str = models.CharField(
        max_length=1,
        blank=True,
        null=True,
        default=TipoSimNao.SIM,
    )

    objects: managers.TipoRegimeCasamentoManager = managers.TipoRegimeCasamentoManager()

    class Meta:
        verbose_name = "Tipo de Regime de Casamento"
        verbose_name_plural = "Tipos de Regimes de Casamento"
        ordering = ["descricao_regime"]

    def __str__(self) -> str:
        return str(self.descricao_regime)


class Files(models.Model):
    file = models.FileField(upload_to="file")

    class Meta:
        verbose_name = "Arquivo"
        verbose_name_plural = "Arquivos"

    def __str__(self) -> str:
        return self.file.name


class Funcionario(models.Model):
    nome: str = models.CharField(max_length=255, null=False, blank=False)
    sobrenome: str = models.CharField(max_length=255, null=False, blank=False)
    cpf: str = models.CharField(max_length=14, null=False, blank=False)
    tempo_de_servico = models.BigIntegerField(default=0, null=False, blank=False)
    remuneracao = models.DecimalField(
        default=0,
        blank=False,
        decimal_places=2,
        max_digits=8,
        null=False,
    )

    class Meta:
        verbose_name = "Funcionário"
        verbose_name_plural = "Funcionários"

    def __str__(self) -> str:
        return f"{self.nome} {self.sobrenome}"


# Criar usuario no CARTORIOS_USUARIO
def converter_colaborador_em_usuario_do_sistema(funcionario_id):
    # OBTER O CODIDO E NOME DO USUARIO NA TABELA HOME_COLABORADOR
    colaborador = (
        Colaborador.objects.filter(pk=funcionario_id)
        .values_list("nome", flat=True)
        .first()
    )
    # colaborador = mapear_do_sistema_antigo(str(colaborador_default))

    # APENAS CRIAR O USUARIO
    # colaborador_default_TEMP = str(colaborador_default) + str(funcionario_id)

    from apps.cartorios.models import Cartorio

    cartorio = (
        Cartorio.objects.filter(id_isnull=False).values_list("id", flat=True).first()
    )

    usuario = cartorio.objects.criar_usuario_no_cartorio(
        username=colaborador.nome_mapeado,
        password=make_password("CONFIGURAR_LOCALMENTE"),
        first_name=colaborador.nome_mapeado,
    )

    # # Gravando o usuario na table CARTORIOS_USUARIO
    # usuario = User(
    #     id=funcionario_id,
    #     cartorio_id=cartorio,
    #     funcao_id=1,
    #     status=1,
    #     username=colaborador_default_TEMP,
    #     password="CONFIGURAR_LOCALMENTE",
    #     first_name=colaborador_default_TEMP,
    # )

    return usuario.pk, usuario.username


# # Pasando o id do usuario e pegando o username dele
# def get_user_autenticado(auth_user_id):
#     username_id = ""
#     is_staff = True

#     for encaminhado in list(User.objects.all().values("id", "username", "is_staff")):
#         if str(encaminhado["id"]) == str(auth_user_id):
#             # user = encaminhado["username"]
#             is_staff = encaminhado["is_staff"]

#     return username_id, is_staff


# Pasando o username do usuario e pegando o id dele
def get_user_id(auth_user_name):
    try:
        # user = User.objects.get(username=auth_user_name)
        user = (
            User.objects.annotate(username_upper=Upper("username"))
            .filter(username_upper=auth_user_name.upper())
            .first()
        )

        return user.id, user.is_staff
    except User.DoesNotExist:
        # Se não encontrar o usuário, retorna None e False
        return None, False


# Pasando o username do usuario e pegando o id dele
def get_usuario_do_sistema_pelo_username_no_fb(username):
    return User.objects.get_ou_criar_usuario(username)


# def filtrar_imovel_pedidos_itens_LV3(pedido_item_id) -> dict:
#     # PEGANDO O IMOVEL NOS ITENS DO PROTOCOLO
#     pedido_item = PedidoItem.objects.filter(pk=pedido_item_id).first()

#     # PEGANDO OS DADOS DO REGISTRO AUXILIAR
#     registro_auxiliar = (
#         Livro03.objects.filter(
#             numero=pedido_item.numero_registro, cartorio=pedido_item.numero_ri
#         ).first()
#         if pedido_item
#         else None
#     )

#     return {
#         "numero_registro_auxiliar": pedido_item.numero_registro if pedido_item else "",
#         "tipo_registro": pedido_item.tipo_registro if pedido_item else "",
#         "cartorio_imovel": pedido_item.numero_ri if pedido_item else "",
#         "cancelado_em_id": registro_auxiliar.id if registro_auxiliar else "",
#         "data_abertura_id": registro_auxiliar.data_abertura if registro_auxiliar else "",
#         "registro_auxiliar_id": registro_auxiliar.cancelado_em if registro_auxiliar else "",
#         "municipio_id": "",
#         "data_vencimento_id": registro_auxiliar.data_vencimento if registro_auxiliar else "",
#         "numero_cedula_l_id3": registro_auxiliar.numero_cedula if registro_auxiliar else "",
#         "tipo_registro_auxiliar_id": registro_auxiliar.tipo_registro_auxiliar if registro_auxiliar else "",
#         "descricao_id": registro_auxiliar.descricao if registro_auxiliar else "",
#     }


# Retornar os dados da tabela filtrando no ITEM DO PEDIDO


# Verificar as acoes do imovel
def verificar_acoes_pergunta(acoes_id: int, corrans, pedido_item_id: int) -> str:
    # Direct mapping of acoes_id to dict keys
    key_map = {
        1: "setor_id",
        2: "quadra_id",
        3: "numero_unidade_id",
        4: "nome_rua_id",
        5: "numero_rua_id",
        6: "area_id",
        7: "comercial_id",  # Special handling required
        8: "numero_contribuinte_id",
        9: "municipio_id",
        27: "m_frente_metros",
        28: "m_direito_metros",
        29: "m_fundo_metros",
        30: "m_esquerdo_metros",
        31: "p_frente_metros",
        32: "p_direito_metros",
        33: "p_fundo_metros",
        34: "p_esquerdo_metros",
    }

    if acoes_id == 0:
        return str(corrans)

    pedido_item: PedidoItem = PedidoItem.objects.filter(pk=pedido_item_id).first()

    if acoes_id in key_map:
        dict_auxiliar = pedido_item.get_dados_do_registro()

        # Special handling for acoes_id 7
        if (
            acoes_id == 7
            and (str(dict_auxiliar["comercial_id"]) == "")
            and (str(dict_auxiliar["residencial_id"]) == "")
        ):
            return "LOTE"

        return str(dict_auxiliar.get(key_map[acoes_id], ""))

    return ""


class Sequencia(models.Model):
    numero_protocolo = models.BigIntegerField()
    numero_matricula = models.BigIntegerField()
    numero_talao = models.BigIntegerField()
    numero_recibo = models.BigIntegerField()
    numero_protocolo_ec = models.BigIntegerField()
    numero = models.BigIntegerField()

    objects = models.Manager()

    def __str__(self) -> str:
        field_values = []
        for field in self._meta.get_fields():
            field_values.append(str(getattr(self, field.name, "")))
        return " ".join(field_values)


class EstadoCivil(models.Model):
    nome: str = models.CharField(max_length=50, blank=True, null=True, db_index=True)
    descricao_estado_civil: str = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        db_index=True,
    )
    tipo: str = models.CharField(max_length=1, blank=True, null=True)
    descricao_minuta: str = models.CharField(max_length=200, blank=True, null=True)
    texto_masculino: str = models.CharField(max_length=200, blank=True, null=True)
    texto_feminino: str = models.CharField(max_length=200, blank=True, null=True)
    exibir: str = models.CharField(max_length=1, blank=True, null=True)
    requerer_tipo_regime: str = models.CharField(max_length=1, blank=True, null=True)
    descricao: str = models.CharField(max_length=100, blank=True, null=True)
    codigo_regime: str = models.CharField(max_length=10, blank=True, null=True)
    auxiliar_id = models.BigIntegerField(null=True)
    estacao: str = models.CharField(max_length=50, blank=True, null=True)
    secao: str = models.CharField(max_length=50, blank=True, null=True)
    tipo_regime = models.BigIntegerField(null=True)
    tipo_pessoa: str = models.CharField(max_length=1, blank=True, null=True)
    nao_consta: str = models.CharField(max_length=1, blank=True, null=True)
    exibirpessoal: str = models.CharField(max_length=1, blank=True, null=True)
    auxiliar_certidao_id = models.BigIntegerField(null=True)
    estadocivil01: str = models.CharField(max_length=200, blank=True, null=True)
    estadocivil02: str = models.CharField(max_length=200, blank=True, null=True)
    estadocivil03: str = models.CharField(max_length=200, blank=True, null=True)
    estadocivil04: str = models.CharField(max_length=200, blank=True, null=True)
    certidao1m = models.BigIntegerField(null=True)
    certidao2m = models.BigIntegerField(null=True)
    certidao3m = models.BigIntegerField(null=True)
    certidao4m = models.BigIntegerField(null=True)
    certidao1f = models.BigIntegerField(null=True)
    certidao2f = models.BigIntegerField(null=True)
    certidao3f = models.BigIntegerField(null=True)
    certidao4f = models.BigIntegerField(null=True)
    qualificacao1: str = models.CharField(max_length=10, blank=True, null=True)
    qualificacao2: str = models.CharField(max_length=10, blank=True, null=True)
    nome_solteiro_atualizado: str = models.CharField(
        max_length=1,
        blank=True,
        null=True,
    )
    textoauxnome: str = models.CharField(max_length=100, blank=True, null=True)
    trial585: str = models.CharField(max_length=1, blank=True, null=True)
    observacao = CKEditor5Field(config_name="default", blank=True, null=True)

    objects: managers.EstadoCivilManager = managers.EstadoCivilManager()

    class Meta:
        ordering = ["descricao_estado_civil"]

    def __str__(self) -> str:
        return self.descricao_estado_civil

    def get_casado(self) -> str:
        return self.objects.get_or_create(descricao_estado_civil="Casado")[0]

    def get_solteiro(self) -> str:
        return self.objects.get_or_create(descricao_estado_civil="Solteiro")[0]

    def get_list(self) -> list:
        return self.objects.all()


class Livro05(models.Model):
    """Cadastro Pessoal ou Indicador Pessoal. Representa uma pessoa física ou jurídica."""

    cpf: str = models.CharField(
        max_length=14,
        blank=True,
        null=True,
        verbose_name="CPF/CNPJ",
        db_index=True,
    )
    nome: str = models.CharField(max_length=250, verbose_name="Nome", db_index=True)
    documento: str = models.CharField(
        max_length=40,
        blank=True,
        null=True,
        verbose_name="Documento",
        help_text="Segundo documento. Ex. RG, CHN, etc.",
        db_index=True,
    )
    sexo: str = models.CharField(
        max_length=1,
        choices=TipoSexo.CHOICES,
        blank=True,
        null=True,
        verbose_name="Sexo",
        help_text="Sexo. Ex. Masculino, Feminino, etc.",
    )
    nacionalidade: str = models.CharField(
        max_length=15,
        blank=True,
        null=True,
        default="brasileira",
    )
    numero_ficha = models.BigIntegerField(
        default=1,
        null=True,
        verbose_name="Nro Ficha",
    )
    estado_civil = models.ForeignKey(
        EstadoCivil,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="Estado Civil",
        help_text="Estado Civil. Ex. Solteiro, Casado, Divorciado, Viúvo, etc.",
        default=0,
    )
    tipo_regime_casamento = models.ForeignKey(
        TipoRegimeCasamento,
        on_delete=models.CASCADE,
        null=True,
        default=0,
        verbose_name="Regime de Casamento",
        help_text="Regime de Casamento. Ex. Comunhão Parcial de Bens, Comunhão Universal de Bens, Separação Total de Bens, etc.",
    )
    profissao: str = models.CharField(
        max_length=60,
        blank=True,
        null=True,
        default="N/A",
        verbose_name="Profissão",
        help_text="Profissão. Ex. Advogado, Engenheiro, Médico, etc.",
    )
    criado_em: datetime = models.DateTimeField(
        auto_now_add=True,
        null=True,
        verbose_name="Dt Cadastro",
    )
    data_alteracao: datetime = models.DateTimeField(
        auto_now=True,
        null=True,
        verbose_name="Dt Alteração",
    )
    nome_pai: str = models.CharField(
        max_length=300,
        blank=True,
        null=True,
        default="",
        verbose_name="Nome do Pai",
    )
    nome_mae: str = models.CharField(
        max_length=300,
        blank=True,
        null=True,
        default="",
        verbose_name="Nome da Mãe",
    )
    endereco: str = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        default="",
        verbose_name="Endereço",
    )
    data_nascimento = models.DateField(
        default=datetime.min.date(),
        null=True,
        verbose_name="Dt Nascimento",
    )
    data_casamento = models.DateField(
        default=datetime.min.date(),
        null=True,
        verbose_name="Data de Casamento",
    )
    data_expedicao = models.DateField(
        default=datetime.min.date(),
        null=True,
        verbose_name="Dt Expedição",
    )
    data_atualizacao = models.DateField(
        default=date.today,
        null=True,
        verbose_name="Dt Atualização",
    )
    email = models.EmailField(blank=True, null=True, default="", verbose_name="E-mail")
    naturalidade: str = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        default="brasileiro",
        verbose_name="Naturalidade",
    )
    telefone: str = models.CharField(
        max_length=40,
        blank=True,
        null=True,
        default="",
        verbose_name="Telefone",
    )
    cidade: str = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        default="",
        verbose_name="Cidade",
    )
    uf: str = models.CharField(
        max_length=2,
        blank=True,
        null=True,
        default="",
        verbose_name="UF",
    )
    telefone_2: str = models.CharField(
        max_length=40,
        blank=True,
        null=True,
        default="",
        verbose_name="Telefone 2",
    )
    conjuge = models.BigIntegerField(
        blank=True,
        null=True,
        default=0,
        verbose_name="Conjuge",
    )
    cep: str = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        default="",
        verbose_name="CEP",
    )
    pessoa_juridica: str = models.CharField(
        max_length=1,
        blank=True,
        null=True,
        choices=TipoSimNao.CHOICES,
        default=TipoSimNao.NAO,
        verbose_name="Pessoa Jurídica",
    )
    tipo_regime = models.BigIntegerField(null=True)
    tipo_documento = models.BigIntegerField(null=True)
    tipo_pessoa: str = models.CharField(max_length=1, blank=True, null=True)
    numero_controle = models.BigIntegerField(null=True, default=0)
    nome_original: str = models.CharField(
        max_length=250,
        blank=True,
        null=True,
        default="",
    )
    orgao_emissor: str = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        default="",
    )
    situacao: str = models.CharField(max_length=100, blank=True, null=True)
    tipo_casamento: str = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        default="",
        verbose_name="Tipo de Casamento",
    )
    temporario_conjuge = models.BigIntegerField(null=True)

    objects: managers.Livro05Manager = managers.Livro05Manager()

    class Meta:
        verbose_name = "Livro05 - Pessoa"
        verbose_name_plural = "Livro05 - Pessoas"
        indexes = [
            models.Index(fields=["nome"]),
            models.Index(fields=["cpf"]),
            models.Index(fields=["cpf", "nome"], name="idx_cpf_nome"),
            models.Index(fields=["criado_em"]),
        ]

    def __str__(self) -> str:
        return f"{formatar_nome(self.nome)} ({self.documento_formatado})"

    def save(self, *args, **kwargs):
        # Se o nome original não foi definido, copia o nome atual
        if not self.nome_original:
            self.nome_original = self.nome
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("home:livro05_detail", kwargs={"pk": self.pk})

    def get_conjuge(self):
        if self.conjuge:
            return Livro05.objects.filter(pk=self.conjuge).first()
        return None

    def get_buscar_pessoal_url(self):
        nome = str(unidecode(self.nome)).strip()
        documento = self.cpf_numero

        pessoas = (
            Livro05.objects.filter(cpf__icontains=documento, nome__icontains=nome)
            if documento and nome
            else (
                Livro05.objects.filter(cpf__icontains=documento)
                if documento
                else Livro05.objects.filter(nome__icontains=nome)
            )
        )

        pessoas_ids = pessoas.values_list("id", flat=True)

        base_url = reverse("home:livro05_pessoal_view")
        query_string = urlencode({"pessoa_id": list(pessoas_ids)}, doseq=True)
        return f"{base_url}?{query_string}"

    @cached_property
    def documento_mascarado(self):
        """Retorna o documento obscurecido."""
        return helpers.mascarar_documento(self.cpf)

    @cached_property
    def cpf_numero(self):
        """Retorna o número do CPF."""
        return somente_numeros(self.cpf)

    @classmethod
    def get_ultima_pessoa_por_cpf(cls, cpf) -> object:
        logger.info(f"Procurando CPF: {cpf}")

        queryset = cls.objects.filter(cpf=cpf).exclude(nome="")
        return queryset.last()

    @cached_property
    def documento_formatado(self):
        """Retorna o documento formatado."""
        return formatar_documento(self.cpf)

    @cached_property
    def documento_formatado_sem_mascara(self):
        """Retorna o documento formatado."""
        return formatar_documento(self.cpf)

    @cached_property
    def documento_configurado(self) -> tuple:
        return formatar_documento_com_descricao(self.cpf)

    @cached_property
    def quantidade_de_vinculos(self):
        return self.vinculos_pessoa.count()

    @classmethod
    def get_ultima_pessoa_pelo_cpf(cls, cpf: str) -> "Livro05":
        resultado = cls.objects.filter(cpf=cpf).order_by("id").last()

        if not resultado:
            return None

        return resultado

    @classmethod
    def quantidade_aberto_indisponibilidade_pelo_id(cls, pk) -> int:
        # vinculo = 0 signifa que o processo ainda esta em aberto
        return LriPartesEnvolvidas.objects.filter(id__in=pk, vinculo=0).count()

    @classmethod
    def quantidade_finalizado_indisponibilidade_pelo_id(cls, pk) -> int:
        # vinculo = 1 signifa que o processo foi finalizado. COLUNA cancelamento_indisponibilidade por esta preenchida
        return LriPartesEnvolvidas.objects.filter(id__in=pk, vinculo=1).count()

    @classmethod
    def pessoas_pelo_cpf_cnpj_com_indisponibilidade(cls, cpf) -> QuerySet:
        # Obtemos os CPFs de Livro05 que estão no LriDocumento
        cpfs_indisponiveis = (
            LriDocumento.objects.filter(
                cpf_cnpj__in=Subquery(Livro05.objects.filter(cpf=cpf).values("cpf")),
            )
            .values_list("cpf_cnpj", flat=True)
            .first()
        )

        if cpfs_indisponiveis is None:
            return None

        # Filtramos Livro05 pelos CPFs obtidos
        return (
            Lri.objects.filter(lri_partes_envolvidas__pessoa__cpf=cpfs_indisponiveis)
            .annotate(
                id_lpe=F("lri_partes_envolvidas__id"),
                tipo_ato=F("lri_partes_envolvidas__tipo_ato"),
                numero_ato=F("lri_partes_envolvidas__numero_ato"),
                vinculo=F("lri_partes_envolvidas__vinculo"),
                cancelado_em=F("lri_partes_envolvidas__cancelado_em"),
                pessoa_id=F("lri_partes_envolvidas__pessoa__id"),
                pessoa_cpf=F("lri_partes_envolvidas__pessoa__cpf"),
                pessoa_nome=F("lri_partes_envolvidas__pessoa__nome"),
            )
            .values(
                "id",
                "tipo_ato",
                "numero_ato",
                "vinculo",
                "numero_do_processo",
                "protocolo_indisponibilidade",
                "cancelamento_indisponibilidade",
                "data_pedido",
                "cancelado_em",
                "pessoa_id",
                "pessoa_cpf",
                "pessoa_nome",
            )
        )

        # print(results)


class Rural(models.Model):
    imovel = models.ForeignKey(
        "Livro02",
        on_delete=models.CASCADE,
        null=True,
        related_name="rurais",
    )
    area: str = models.CharField(max_length=140, blank=True, null=True)
    caracteristica: str = models.CharField(max_length=120, blank=True, null=True)
    reserva_florestal: str = models.CharField(max_length=1, blank=True, null=True)
    georeferencial: str = models.CharField(max_length=1, blank=True, null=True)
    area_inteiro = models.BigIntegerField(blank=True, null=True)
    gleba: str = models.CharField(max_length=100, blank=True, null=True)
    datatexto: str = models.CharField(max_length=200, blank=True, null=True)
    gleba2: str = models.CharField(max_length=200, blank=True, null=True)
    localizacao: str = models.CharField(max_length=200, blank=True, null=True)
    remanescente: str = models.CharField(max_length=1, blank=True, null=True)

    class Meta:
        verbose_name = "Rural"
        verbose_name_plural = "Rurais"

    def __str__(self) -> str:
        return str(self.pk)


class RuralNome(models.Model):
    imovel = models.ForeignKey(
        "Livro02",
        on_delete=models.CASCADE,
        null=True,
        related_name="rural_nomes",
    )
    nome: str = models.CharField(max_length=150, blank=True, null=True)
    localizacao: str = models.CharField(max_length=200, blank=True, null=True)
    area: str = models.CharField(max_length=140, blank=True, null=True)

    objects = models.Manager()

    class Meta:
        verbose_name = "Nome Rural"
        verbose_name_plural = "Nomes Rural"

    def __str__(self) -> str:
        return str(self.nome)


class Livro02(BaseModel):
    """
    Livro02 é o Livro de Registros.

    Um Registro reune os dados do Real (Livro04), Pessoal (Livro05), Protocolo (Livro01), SeloEletronico, etc.
    "Registro" refere-se ao ato formal pelo qual os detalhes de um ou mais imóveis são transcritos/incristos/matriculados.

    """

    numero = models.BigIntegerField(
        null=True,
        db_index=True,
        verbose_name="Número do Registro",
        help_text="Número do Registro (Matrícula, Transcrição, Inscrição)",
    )
    tipo: str = models.CharField(
        max_length=3,
        blank=True,
        null=True,
        db_index=True,
        default=TipoRegistro.MATRICULA,
        verbose_name="Tipo de Registro",
        help_text="Define o tipo de registro. (Matrícula, Transcrição, Inscrição)",
        choices=TipoRegistro.CHOICES,
    )
    # Quando cartórios de unificam é usado separar os registros
    # do cartório de origem do cartório atual
    cartorio: str = models.CharField(
        max_length=2,
        blank=True,
        null=True,
        db_index=True,
        default=CartorioNumero.Um,
        verbose_name="Nº Cartório",
        help_text="Numero do Cartório onde o Registro foi criado (Ex. 1,2,3)",
        choices=CartorioNumero.CHOICES,
    )
    classe: str = models.CharField(
        max_length=1,
        blank=True,
        null=True,
        default=TipoClasseRegistro.URBANO,
        verbose_name="Classe do Registro",
        help_text="Define se o Registro é Urbano, Rural, Loteamento, Condominio, etc.",
        choices=TipoClasseRegistro.CHOICES,
    )
    municipio: str = models.CharField(
        max_length=40,
        blank=True,
        null=True,
        default="(Não Informado)",
        verbose_name="Município",
        help_text="Município do Registro",
    )
    encerrado: str = models.CharField(
        max_length=1,
        blank=True,
        null=True,
        default=TipoSimNao.NAO,
        choices=TipoSimNao.CHOICES,
        verbose_name="Registro Encerrado",
        help_text="Define se o registro está encerrado",
    )
    data_abertura = models.DateField(
        blank=True,
        null=True,
        default=date.today,
        verbose_name="Dt Abertura",
        help_text="Data de Abertura do Registro",
    )
    registro_anterior = models.BigIntegerField(
        blank=True,
        null=True,
        verbose_name="Registro Anterior",
        help_text="Registro que deu origem ao atual",
    )
    numero_nirf: str = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name="NIRF",
        help_text="Número de Identificação no Cadastro de Imóveis Rurais (Cafir)",
    )
    numero_ccirr: str = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name="CCIR",
        help_text="Numero do Certificado de Cadastro de Imóvel Rural",
    )
    numero_car: str = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="CAR",
        help_text="Numero do registro no Cadastro Ambiental Rural",
    )
    numero_incra: str = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="INCRA",
        help_text="Código do imovel no Instituto Nacional de Colonização e Reforma Agrária (INCRA)",
    )
    numero_itr: str = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        default="",
        verbose_name="ITR",
        help_text="Imposto sobre a Propriedade Territorial Rural",
    )
    cnm: str = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        default="",
        verbose_name="CNM",
        help_text="Código Nacional de Matrícula",
    )
    tipo_unidade: str = models.CharField(
        max_length=1,
        blank=True,
        null=True,
        default="",
        verbose_name="Tipo de Unidade",
        help_text="Tipo de Unidade, Quadra, Lote, etc.",
    )
    data_validade_itr: str = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        default=settings.MINDATE,
        verbose_name="Validade do ITR",
        help_text="Validade do Imposto sobre a Propriedade Territorial Rural",
    )

    area_construida_residencial: str = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        default="0",
        verbose_name="Área Construída Residencial",
    )
    area_construida_comercial: str = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        default="0",
        verbose_name="Área Construída Comercial",
    )
    area_construida: str = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        default="0",
        verbose_name="Área Construída Total",
    )

    cep: str = models.CharField(
        max_length=15,
        blank=True,
        null=True,
        verbose_name="CEP",
    )
    criado_em: datetime = models.DateTimeField(
        default=date.today,
        blank=True,
        null=True,
        verbose_name="Criado em",
    )
    ultimo_livro: str = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name="Último Livro",
    )
    ultimo_folha: str = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name="Última Folha",
    )
    texto = CKEditor5Field(
        blank=True,
        null=True,
        config_name="default",
        verbose_name="Texto do Registro",
        default="",
    )
    data_envio_cnm = models.DateField(
        blank=True,
        null=True,
        default=None,
        db_index=True,
    )
    enviar_cnm: bool = models.BooleanField(default=False)
    data_envio_livro_4 = models.DateField(
        blank=True,
        null=True,
        default=None,
        db_index=True,
    )
    enviar_livro_4: bool = models.BooleanField(default=False)
    arquivo = models.FileField(upload_to="livro02", blank=True, null=True)

    objects: managers.Livro02Manager = managers.Livro02Manager()

    livro = 2

    class Meta:
        verbose_name = "Registro"
        verbose_name_plural = "Registros"
        indexes = [
            models.Index(
                fields=["cartorio", "numero", "tipo"],
                name="registros_c_n_t_idx",
            ),
            models.Index(fields=["numero"]),
        ]

    def __str__(self) -> str:
        return self.qualificacao

    def get_absolute_url(self):
        return reverse("home:livro02_detail", kwargs={"pk": self.pk})

    @classmethod
    def ultimo_registro_enviado_onr(cls) -> int:
        resultado = (
            cls.objects.filter(data_envio_cnm__isnull=False, numero__lte=115000)
            .order_by("-numero")
            .first()
        )

        if resultado:
            return resultado.numero_registro_formatado
        else:
            return 0

    @cached_property
    def lembretes_v2(self) -> list:
        try:
            lembretes = Lembrete.objects.filter(imovel=self).order_by("id")

            if lembretes is None:
                return []

            return [
                [
                    lembrete.id,
                    lembrete.imovel,
                    lembrete.created_at,
                    lembrete.updated_at,
                    lembrete.descricao,
                    lembrete.funcionarios_create_id,
                    lembrete.funcionarios_update_id,
                    lembrete.nivel_alerta_id,
                ]
                for lembrete in lembretes
            ]

        except Exception:
            logger.exception("ERRO")
            return ""

    @cached_property
    def qualificacao(self) -> str:
        return f"{self.tipo_classe_descricao} {self.tipo_registro_descricao}: {self.numero_formatado} - RI {self.numero_ri} | CNM: {self.cnm_formatada}"

    @cached_property
    def tipo_classe_descricao(self):
        return TipoClasseRegistro.get_descricao(self.classe)

    @cached_property
    def numeros_contribuinte(self):
        """Obtém os números de contribuintes associados a um determinado imóvel."""
        contribuintes_list = Contribuintes.objects.filter(
            imovel_id=self.pk,
        ).values_list(
            "numero_contribuinte",
            flat=True,
        )

        return ", ".join(contribuintes_list).strip()

    def calcular_cnm(self) -> str:
        """Calcula o CNM (Cadastro Nacional de Matrículas) com base nos atributos cartório, livro e número."""
        cns = int(Configuracao.obter("CNS") or 0)
        livro = int(self.livro or 0)
        numero = int(self.numero or 0)

        resultado = int(f"{cns:06d}{livro:01d}{numero:07d}") * 100
        resultado = resultado % 97 or 0
        resultado = 98 - resultado or 0
        return f"{cns:06d}{livro:01d}{numero:07d}{resultado:02d}"

    @cached_property
    def numero_registro(self):
        return self.numero if self.numero else "0"

    @cached_property
    def tipo_registro(self):
        return self.tipo if self.tipo else TipoRegistro.MATRICULA

    @cached_property
    def cartorio_imovel(self):
        return self.cartorio_registro

    @cached_property
    def cartorio_registro(self):
        return self.cartorio if self.cartorio else "1"

    @cached_property
    def cnm_formatada(self):
        cnm = self.calcular_cnm()
        return helpers.formatar_cnm(cnm)

    def descricao_dados_registro(self) -> str:
        if self.classe == TipoClasseRegistro.RURAL:
            return "Imóvel Rural"

        if self.classe == TipoClasseRegistro.URBANO:
            return "Imóvel Urbano"

        if self.classe == TipoClasseRegistro.LOTE:
            return "Imóvel Lote"

        if self.classe == TipoClasseRegistro.CONDOMINIO:
            return "Imóvel Condomínio"

        return " dados do Imóvel"

    @cached_property
    def quantidade_de_registros_no_livro03(self):
        return Livro03Garantia.objects.filter(
            numero_registro=self.numero_registro,
            tipo_registro=self.tipo_registro,
        ).count()

    @cached_property
    def registros_no_livro03(self):
        return Livro03Garantia.objects.filter(
            numero_registro=self.numero_registro,
            tipo_registro=self.tipo_registro,
        ).order_by("-id")

    @cached_property
    def rural(self):
        # return Rural.objects.filter(imovel_id=self.pk).first()
        return Rural.objects.filter(imovel_id=self.pk)

    @cached_property
    def rural_nome(self):
        return RuralNome.objects.filter(imovel_id=self.pk).first()

    @cached_property
    def rural_todos_nome(self):
        return RuralNome.objects.filter(imovel_id=self.pk)

    @cached_property
    def rural_nome_fazenda(self):
        return self.rural_nome.nome if self.rural_nome else ""

    @cached_property
    def rural_area_total_fazenda(self):
        return self.rural.area if self.rural else ""

    @cached_property
    def rural_municipio_fazenda(self):
        return self.municipio if self.rural else ""

    @cached_property
    def nomes(self):
        rural_nomes = RuralNome.objects.filter(imovel_id=self.pk)
        return ", ".join([rural_nome.nome for rural_nome in rural_nomes])

    @cached_property
    def ruas(self):
        ruas = Rua.objects.none()

        if self.classe != TipoClasseRegistro.RURAL:
            try:
                unidades = Unidade.objects.filter(imovel_id=self.pk)
            except Unidade.DoesNotExist:
                from apps.home.utils.importar_livro2 import (
                    converter_livro02_pelo_id_do_fb,
                )

                converter_livro02_pelo_id_do_fb(self.pk)
                unidades = Unidade.objects.filter(imovel_id=self.pk)

            if unidades:
                return Rua.objects.filter(unidade_id=unidades[0].id)
            else:
                return (
                    Rua.objects.none()
                )  # Retorna um queryset vazio de forma explícita

        return ruas if ruas else ""

    @cached_property
    def lotes(self) -> list:
        if self.classe != TipoClasseRegistro.RURAL:
            return self.get_lotes()
        return None

    def get_lotes(self) -> list:
        unidade = Unidade.objects.filter(imovel_id=self.pk).first()
        try:
            return Lote.objects.filter(unidade_id=unidade.pk)
        except Exception:
            logger.exception("ERRO ao obter os lotes")
            from apps.home.utils.importar_livro2 import converter_livro02_pelo_id_do_fb

            converter_livro02_pelo_id_do_fb(self.pk)
            try:
                return Lote.objects.filter(unidade_id=unidade.pk)
            except Exception:
                logger.exception("ERRO ao obter os lotes")
                return []

    @cached_property
    def unidades_do_condominio(self):
        ficha_auxiliar = FichaAuxiliar.objects.get(id=self.pk)
        registro_anterior = ficha_auxiliar.unidade_id
        return Unidade.objects.filter(registro_anterior=registro_anterior)

    @cached_property
    def numero_formatado(self):
        numero = str(self.numero)

        if not numero:
            return ""

        if len(numero) <= 3:
            return numero

        return numero[:-3] + "." + numero[-3:]

    @cached_property
    def indice_cadastral(self):
        # PEGANDO OS NÚMEROS DOS CONTRIBUINTES DO IMOVEL URBANO
        numeros_contribuinte = Contribuintes.objects.filter(
            imovel_id=self.pk,
        ).values_list(
            "numero_contribuinte",
            flat=True,
        )

        # Converter diretamente para lista para evitar chamadas de função desnecessárias
        return list(numeros_contribuinte)

    @cached_property
    def alienacoes(self):
        return Vinculo.objects.filtrar_alienacoes_do_imovel(self.pk)

    @cached_property
    def alienacoes_v2(self):
        try:
            alienacoes = self.alienacoes

            # Filtrando os vinculos - HIPOTECAS
            return [
                [
                    alienacao.numero_ato_formatado,
                    None,
                    alienacao.pessoa.documento_formatado,
                    alienacao.pessoa.nome,
                    None,
                ]
                for alienacao in alienacoes
            ]

        except Exception:
            logger.exception("ERRO")
            return None

    @cached_property
    def hipotecas(self):
        return Vinculo.objects.get_hipotecas_do_imovel(self.pk)

    @cached_property
    def hipotecas_v2(self):
        try:
            # Hipotecas Atuais
            hipotecas_atuais = []

            # Filtrando os vinculos HIPOTECA
            ordem_penhor = 0
            nro_ato_atual = ""

            # Filtrando os vinculos - HIPOTECAS
            for hipoteca in self.hipotecas:
                # Se mudar o numero do ato a ordem do penhor e acrescida de 1
                if str(nro_ato_atual) != str(hipoteca.numero_ato):
                    nro_ato_atual = str(hipoteca.numero_ato)
                    ordem_penhor = int(ordem_penhor) + 1

                grau_penhor = "(Grau: " + str(ordem_penhor) + ")"

                # Filtrando o nome das pessoas
                hipotecas_atuais.append(
                    [
                        hipoteca.numero_ato_formatado,
                        grau_penhor,
                        hipoteca.pessoa.documento_formatado,
                        hipoteca.pessoa.nome,
                        hipoteca.percentual_formatado,
                    ],
                )

            return hipotecas_atuais
        except Exception:
            logger.exception("ERRO")
            return ""

    @cached_property
    def acoes_e_onus(self) -> list:
        try:
            # acoes_e_onus Atuais
            acoes_e_onus_atuais = []

            # acoes_e_onus Atuais
            acoes_e_onus = (
                Vinculo.objects.select_related("pessoa", "tipo_vinculo")
                .filter(
                    imovel_id=self.pk,
                    situacao="F",
                    tipo_vinculo_id__in=TipoVinculo.get_id_acoes_onus(),
                )
                .order_by("numero_ato")
            )

            # Filtrando os vinculos acoes_e_onus
            # ordem_penhor = 0
            # nro_ato_atual = ""

            # Filtrando os vinculos - acoes_e_onus
            for acoes in acoes_e_onus:
                pessoa: Livro05 = Livro05.objects.filter(pk=acoes.pessoa.id).first()
                percentual = "(" + str(acoes.percentual_formatado) + ")"

                # Se mudar o numero do ato a ordem do penhor e acrescida de 1
                # if str(nro_ato_atual) != str(acoes.numero_ato):
                #    nro_ato_atual = str(acoes.numero_ato)
                #    ordem_penhor = int(ordem_penhor) + 1

                # grau_penhor = "(Grau: " + str(ordem_penhor) + ")"

                # Filtrando o nome das pessoas
                with contextlib.suppress(Exception):
                    acoes_e_onus_atuais.append(
                        [
                            acoes.numero_ato_formatado,
                            "",
                            pessoa.documento_formatado,
                            pessoa.nome,
                            percentual,
                            pessoa.id,
                        ],
                    )

            return acoes_e_onus_atuais
        except Exception:
            logger.exception("ERRO ao obter as acoes e onus")
            return ""

    @cached_property
    def quantidade_acoes_e_onus(self) -> int:
        return len(self.acoes_e_onus)

    @cached_property
    def tipo_descrito(self):
        return TipoRegistro.get_descricao(self.tipo)

    @cached_property
    def pasta_de_imagens(self) -> str:
        numero_do_imovel_formatado = str(self.numero).zfill(6)
        tres_primeiros_digitos = numero_do_imovel_formatado[0:3]
        pasta = self.pasta_imagens
        pasta_de_anexos = (
            f"{pasta}/{tres_primeiros_digitos}/{numero_do_imovel_formatado}"
        )
        return pasta_de_anexos if self else None

    def imagens(self) -> list[str]:
        from apps.home.helpers import get_urls_imagens_pela_webservice

        imagens = get_urls_imagens_pela_webservice(self.pasta_de_imagens)

        if not imagens:
            logger.warning(f"Nenhuma imagens encontrada para o registro {self.pk}.")
            return []

        return imagens

    @cached_property
    def lista_contribuintes(self):
        return self.contribuintes.all()

    @cached_property
    def tipo_registro_descricao(self):
        # print("Obtendo Descrição do Tipo de Registro")
        return self.__class__.get_descricao_tipo_registro(self.tipo)

    @cached_property
    def numero_ri(self):
        return str(self.cartorio) or "1"

    @cached_property
    def nome_cidade(self):
        # print("Obtendo Nome da cidade")
        return formatar_nome(self.municipio) or "Município não informado"

    @cached_property
    def vinculos_de_proprietarios_atuais(self):
        tipos_proprietarios = Configuracao.obter("proprietario_id")
        return self.vinculos.filter(
            situacao="F",
            tipo_vinculo_id__in=tipos_proprietarios,
        ).all()

    @cached_property
    def registros_anteriores(self):
        # Buscar todos os registros anteriores relacionados ao imóvel
        anteriores = Anterior.objects.filter(imovel_id=self.pk)

        # Inicializar lista para armazenar strings formatadas
        registro = []

        # Pré-processar descrições e matrículas se necessário
        tipos_processados = {}
        matriculas_processadas = {}

        for anterior in anteriores:
            # Processar e armazenar resultados únicos para evitar recalculo
            tipo = tipos_processados.setdefault(anterior.tipo, anterior.tipo_descrito)
            matricula = matriculas_processadas.setdefault(
                anterior.numero,
                anterior.numero_formatado,
            )

            registro.append(f"{tipo} {matricula}, {anterior.complemento or ''}")

        # return {"{{ registro_anterior }}": "; ".join(filter(None, registro))}
        return "".join(filter(None, registro))

    @cached_property
    def enderecos(self):
        resultado = []

        if self.classe == "R":
            imovel_rural = Rural.objects.filter(imovel_id=self.pk).first()

            if imovel_rural:
                imovel_rural_nome = RuralNome.objects.filter(imovel_id=self.pk).first()

                if imovel_rural_nome:
                    nome = str(imovel_rural_nome.nome).replace("None", "")
                    localizacao = str(imovel_rural.caracteristica).replace("None", "")
                    area = str(imovel_rural.area).replace("None", "")

                    resultado.append(
                        [
                            f"Nome: {nome}",
                            f"Localização: {localizacao}",
                            f"Área: {area}",
                        ],
                    )
                else:
                    localizacao = str(imovel_rural.caracteristica).replace("None", "")
                    area = str(imovel_rural.area).replace("None", "")

                    resultado.append(
                        [
                            f"Localização: {localizacao}",
                            f"Área: {area}",
                        ],
                    )
        else:
            unidade = Unidade.objects.filter(imovel_id=self.pk).first()
            if unidade:
                lotes = Lote.objects.filter(unidade=unidade.pk).all()

                resultado = [
                    [
                        f"Bairro: {lote.setor}",
                        f"Quadra: {lote.quadra}; Lote: {lote.numero_unidade}; Área: {lote.area}",
                        # f"Rua(s): {', '.join(unidade.get_nomes_das_ruas())}",
                        f"Rua(s): {unidade.get_nomes_das_ruas()}",
                    ]
                    for lote in lotes
                ]

        return resultado

    # @cached_property
    # def loteamento(self):
    #     """Esta função retorna uma lista contendo informações sobre o loteamento.

    #     Se o imóvel anterior não existir, retorna uma lista vazia.
    #     Caso contrário, retorna uma lista contendo o tipo, número e cartório do imóvel atual,
    #     bem como o nome, nome da incorporadora e data de incorporação do imóvel anterior.
    #     """
    #     # Se não houver imóvel anterior, retorna uma lista vazia
    #     imovel_auxiliar, ficha_auxiliar_mae, temp_list = [], [], None

    #     if not self.registro_anterior:
    #         # ITEM - FICHA AUXILIAR
    #         ficha_auxiliar_mae = FichaAuxiliar.objects.filter(id=self.id, tipo="L")

    #         # VERIFICAR SE A PROPRIA FICHA
    #         if ficha_auxiliar_mae:
    #             pass
    #         else:
    #             return []
    #     else:
    #         # ITEM - UNIDADE
    #         ficha_auxiliar_mae = FichaAuxiliar.objects.filter(id=self.registro_anterior, tipo="L")

    #         if ficha_auxiliar_mae:
    #             pass
    #         else:
    #             return []

    #     if self.classe == TipoClasseRegistro.CONDOMINIO:
    #         return []

    #     # Tenta obter o imóvel anterior
    #     try:
    #         # ficha_auxiliar_mae = FichaAuxiliar.objects.filter(id=ficha_id)
    #         if ficha_auxiliar_mae:
    #             for item_ficha in ficha_auxiliar_mae:
    #                 imovel_auxiliar = Livro02.objects.filter(id=item_ficha.id)

    #     except FichaAuxiliar.DoesNotExist:
    #         # Se o imóvel anterior não existir, retorna uma lista vazia
    #         return []

    #     # Adiciona as informações do imóvel atual
    #     if imovel_auxiliar:
    #         # Inicializa a lista com o tipo, número e cartório do imóvel atual
    #         temp_list = []

    #         for imovel in imovel_auxiliar:
    #             temp_list = [imovel.tipo or "", imovel.numero or "", imovel.cartorio or ""]

    #         # Adiciona as informações do LOTEAMENTO atual
    #         for ficha in ficha_auxiliar_mae:
    #             temp_list.extend([ficha.nome or "", ficha.nome_incorporadora or "", ficha.data_incorporacao or ""])

    #     # Retorna a lista
    #     return [temp_list]

    @cached_property
    def loteamento(self):
        """
        Esta função retorna uma lista contendo informações sobre o loteamento.

        Se o imóvel anterior não existir, retorna uma lista vazia.
        Caso contrário, retorna uma lista contendo o tipo, número e cartório do imóvel atual,
        bem como o nome, nome da incorporadora e data de incorporação do imóvel anterior.
        """
        # Verificar se a classe é CONDOMINIO e retornar lista vazia
        if self.classe == TipoClasseRegistro.CONDOMINIO:
            return []

        # Definir o ID do registro a ser consultado (atual ou anterior)
        registro_id = self.registro_anterior if self.registro_anterior else self.id
        ficha_auxiliar_mae = FichaAuxiliar.objects.filter(id=registro_id, tipo="L")

        # Se não encontrar nenhuma ficha auxiliar, retornar lista vazia
        if not ficha_auxiliar_mae.exists():
            return []

        # Tenta obter o imóvel anterior
        imovel_auxiliar = Livro02.objects.filter(
            id__in=ficha_auxiliar_mae.values_list("id", flat=True),
        )

        # Se o imóvel anterior não existir, retorna uma lista vazia
        if not imovel_auxiliar.exists():
            return []

        # Inicializa a lista com o tipo, número e cartório do imóvel atual
        temp_list = []
        for imovel in imovel_auxiliar:
            temp_list = [imovel.tipo or "", imovel.numero or "", imovel.cartorio or ""]

        # Adiciona as informações do LOTEAMENTO atual
        for ficha in ficha_auxiliar_mae:
            temp_list.extend(
                [
                    ficha.nome or "",
                    ficha.nome_incorporadora or "",
                    ficha.data_incorporacao or "",
                ],
            )

        # Retorna a lista
        return [temp_list]

    @cached_property
    def get_lote_associado(self):
        if self.classe != "R":
            try:
                # Filtrando as unidades
                unidades = Unidade.objects.get(imovel_id=self.pk)

                # PEGANDO O ENDERECO DO IMOVEL URBANO
                return Lote.objects.filter(unidade_id=unidades.imovel_id)
            except Unidade.DoesNotExist:
                # Retorne None ou uma lista vazia, dependendo de como você quer lidar com a ausência de unidades
                return None
        else:
            return None

    @cached_property
    def get_ficha_condominio(self):
        if self.classe not in [
            TipoClasseRegistro.CONDOMINIO,
            TipoClasseRegistro.RURAL,
        ]:  # Condominio ou Rural
            imovel_id = int(self.imovel)

            try:
                ficha = FichaAuxiliar.objects.get(id=imovel_id)
                if ficha.unidade:
                    return Unidade.objects.filter(
                        registro_anterior=ficha.unidade_id,
                    ).count()
                return 0
            except FichaAuxiliar.DoesNotExist:
                return 0
        else:
            return 0

    # @cached_property
    # def condominio_de_origem(self) -> list:
    #     # Filtrando pelas unidades - CONDOMINIO DE ORIGEM
    #     if self.classe == TipoClasseRegistro.CONDOMINIO:
    #         registro_id = self.registro_anterior
    #     # Filtrando pelo CONDOMINIO DE ORIGEM
    #     else:
    #         registro_id = self.id

    #     # PESQUISAR O CONDOMINIO
    #     ficha_auxiliar_mae = FichaAuxiliar.objects.filter(id=registro_id, tipo="C").first()

    #     # CONDOMINIO NAO ENCONTRADO
    #     if ficha_auxiliar_mae is None:
    #         return []

    #     # FIltrando os dados do Condominio
    #     imovel = Livro02.objects.filter(id=registro_id).first()

    #     return [
    #         [
    #             imovel.tipo,
    #             imovel.numero,
    #             ficha_auxiliar_mae.nome,
    #             ficha_auxiliar_mae.numero_edificacao,
    #             ficha_auxiliar_mae.nome_incorporadora,
    #             ficha_auxiliar_mae.data_incorporacao,
    #             imovel.cartorio,
    #             imovel.encerrado,
    #         ],
    #     ]

    @cached_property
    def condominio_de_origem(self) -> list:
        # Determinar o registro_id com base na classe
        registro_id = (
            self.registro_anterior
            if self.classe == TipoClasseRegistro.CONDOMINIO
            else self.id
        )

        # Pesquisar o condomínio de origem
        ficha_auxiliar_mae = FichaAuxiliar.objects.filter(
            id=registro_id,
            tipo="C",
        ).first()

        # Retornar lista vazia se não encontrar o condomínio de origem
        if not ficha_auxiliar_mae:
            return []

        # Filtrar os dados do imóvel
        imovel = Livro02.objects.filter(id=registro_id).first()

        # Retornar as informações do condomínio de origem
        return (
            [
                [
                    imovel.tipo,
                    imovel.numero,
                    ficha_auxiliar_mae.nome,
                    ficha_auxiliar_mae.numero_edificacao,
                    ficha_auxiliar_mae.nome_incorporadora,
                    ficha_auxiliar_mae.data_incorporacao,
                    imovel.cartorio,
                    imovel.encerrado,
                ],
            ]
            if imovel
            else []
        )

    @cached_property
    def total_lotes_associados(self):
        if self.classe == TipoClasseRegistro.CONDOMINIO:
            return Lote.objects.filter(
                unidade__in=Unidade.objects.filter(registro_anterior=self.id),
            ).count()
        else:
            return 0

    @cached_property
    def quantidade_livro03(self):
        # PEGANDO OS DADOS DAS GARANTIAS - Filtrar as garantias do LIVRO 3 - Vinculadas ao IMOVEL
        return Livro03Garantia.objects.filter(
            numero_registro=self.numero,
            tipo_registro=self.tipo,
        ).count()

    @cached_property
    def get_acoes_e_onus(self):
        try:
            hipoteca_atual = Vinculo.objects.get_hipotecas_do_imovel(self.pk)

            hipoteca_atual = []
            ordem_penhor, percentual_hipoteca_atual = 0, 0
            nro_ato_atual = ""

            for item in hipoteca_atual:
                try:
                    percentual_hipoteca_atual += Decimal(item.area_pecentual)
                except ValueError:
                    logger.exception("Erro ao somar percentual de hipoteca")
                    percentual_hipoteca_atual = 0

                numero_ato_temp = (
                    f"{item.tipo_ato}.{str(item.numero_ato).split('.')[0]}"
                )
                nome = item.pessoa.nome
                cpf = item.pessoa.documento_formatado
                percentual = f"({percentual_hipoteca_atual:.2f}%)"
                pessoa_id = item.pessoa.id

                if nro_ato_atual != item.numero_ato:
                    nro_ato_atual = item.numero_ato
                    ordem_penhor += 1

                grau_penhor = f"(Grau: {ordem_penhor})"

                hipoteca_atual.append(
                    [numero_ato_temp, grau_penhor, cpf, nome, percentual, pessoa_id],
                )

            return hipoteca_atual
        except Exception:
            logger.exception("ERRO ao obter ações e ônus do imóvel")
            return ""

    @cached_property
    def vinculos(self):
        return (
            Vinculo.objects.select_related("pessoa", "tipo_vinculo")
            .filter(imovel_id=self.pk)
            .order_by("numero_ato")
        )

    @cached_property
    def get_condominio_origem(self):
        lista = []
        setor, numero_unidade, rua = "", "", ""

        try:
            unidade = Unidade.objects.select_related("imovel").get(
                id=self.registro_anterior,
            )

            lote = Lote.objects.get(unidade=unidade)
            setor = lote.setor

            unidade_atual = Unidade.objects.get(imovel_id=self.imovel)
            numero_unidade = unidade_atual.numero_unidade
            rua = get_ruas(self.registro_anterior)

            imovel = unidade.imovel
            ficha = FichaAuxiliar.objects.filter(pk=imovel.id).first()

            # Precisa entender melhor, parece que ele tenta buscar numa
            # tabela de tipos de unidades que não existe...
            tipo_unidade = str(Unidade.get_tipo_pelo_id(self.tipo_unidade))

            lista.append(
                [
                    imovel.tipo,
                    imovel.numero,
                    imovel.cartorio,
                    ficha.nome if ficha else "",
                    ficha.nome_incorporadora if ficha else "",
                    ficha.data_incorporacao if ficha else "",
                    ficha.numero_edificacao if ficha else "",
                    numero_unidade,
                    unidade.nome_edificio,
                    tipo_unidade,
                    "",
                    unidade.area,
                    unidade.quadra,
                    unidade.lote_auxiliar,
                    setor,
                    rua,
                ],
            )

            return lista
        except (Unidade.DoesNotExist, Lote.DoesNotExist, FichaAuxiliar.DoesNotExist):
            return []

    @classmethod
    def get_numero_do_registro_pelo_id(cls: "Livro02", imovel_id: int) -> int:
        registro = cls.objects.filter(pk=imovel_id).first()
        return registro.numero if registro else 0

    @classmethod
    def get_descricao_tipo_registro(cls: "Livro02", value) -> str:
        return TipoRegistro.get_descricao(value)

    @cached_property
    def pasta_imagens(self: "Livro02") -> str | None:
        try:
            if self.tipo == TipoRegistro.MATRICULA:
                return "Matriculas"
            elif self.tipo == TipoRegistro.TRANSCRICAO:
                return "Transcricao"
            elif self.tipo == TipoRegistro.INSCRICAO:
                return "Inscricao"
            elif self.tipo == TipoRegistro.AVERBACAO:
                return "RAuxiliar"
            else:
                return ""
        except Exception:
            logger.exception("Erro ao obter a pasta de imagens")
            return ""

    @cached_property
    def quantidade_de_unidades_no_condominio(self: "Livro02"):
        if not self.pk or self.pk == 0:
            return 0

        # if self.classe != TipoClasseRegistro.CONDOMINIO:
        if self.tipo_unidade and self.tipo_unidade != "":
            return 0

        try:
            ficha = FichaAuxiliar.objects.get(id=self.pk)

            if ficha.unidade_id > 0:
                return Unidade.objects.filter(
                    registro_anterior_id=ficha.unidade_id,
                ).count()
            return 0
        except FichaAuxiliar.DoesNotExist:
            return 0

    @cached_property
    def get_unidade_no_condominio(self: "Livro02"):
        if not self.pk or self.pk == 0:
            return 0

        # VERIFICAR SE E UMA UNIDADE VALIDA (APARTAMENTO, CASA, GARAGEM, ETC...)
        if (self.tipo_unidade == "") or (self.tipo_unidade is None):
            return 0

        # BUSCANDO A FICHA MAE
        ficha = FichaAuxiliar.objects.filter(id=self.registro_anterior).first()

        # PEGANDO A UNIDADE - PELO ID DA UNIDADE DA FICHA MAE
        if ficha and ficha.unidade_id > 0:
            return Unidade.objects.filter(
                registro_anterior_id=ficha.unidade_id,
                imovel_id=self.pk,
            )
        else:
            return None

    @cached_property
    def get_lotes_no_loteamento(self: "Livro02"):
        if self.classe == TipoClasseRegistro.CONDOMINIO:
            return 0

        # UNIDADE DO IMOVEL FILHO - BUSCAR A ID IMOVEL DA FICHA MAE
        return Unidade.objects.select_related("imovel").filter(
            registro_anterior_id=self.pk,
        )

    @cached_property
    def quantidade_de_lotes_no_loteamento(self: "Livro02"):
        if self.classe == TipoClasseRegistro.CONDOMINIO:
            return 0

        # VERIFICAR SE O IMOVEL É UM CONDOMINIO
        try:
            ficha = FichaAuxiliar.objects.filter(id=self.pk).first()
        except:
            return None

        if ficha is None:
            # print("Nao tem Ficha")
            return None

        if ficha.tipo == "C":
            # print("CONDOMINIO")
            return None

        # UNIDADE DO IMOVEL FILHO - BUSCAR A ID IMOVEL DA FICHA MAE
        return Unidade.objects.filter(registro_anterior_id=self.pk).count()

    @cached_property
    def partes(self: "Livro02"):
        tipo_vinculo_proprietario_id = Configuracao.obter("proprietario_id")

        return (
            Vinculo.objects.select_related("pessoa", "tipo_vinculo")
            .filter(
                imovel_id=self.pk,
                situacao="F",
                tipo_vinculo_id__in=tipo_vinculo_proprietario_id,
            )
            .order_by("numero_ato")
        )

    @cached_property
    def proprietarios_atuais_formatados(self: "Livro02") -> list:
        # Proprietarios Atuais
        proprietario_atual = []
        percentual_proprietario_atual = 0

        for parte in self.partes:
            nome_atual = Livro05.objects.filter(id=parte.pessoa)

            # Formatar o percentual
            try:
                percentual_proprietario_atual += parte.area_pecentual
            except Exception:
                logger.exception("ERRO")
                percentual_proprietario_atual = 0

            # Filtrando o nome das pessoas
            proprietario_atual.append(
                str(parte.tipo_ato)
                + "."
                + str(parte.numero_ato).split(".")[0]
                + " - "
                + str(parte.area_pecentual).replace(".", ",")
                + "% - "
                + str(formatar_documento(nome_atual[0].cpf))
                + " - "
                + str(nome_atual[0].nome)
                + " ("
                + parte.estado_civil.descricao_estado_civil
                + ") ",
            )

    @cached_property
    def enderecos_bairro(self):
        resultado = []

        if self.classe != "R":
            unidade = Unidade.objects.filter(imovel_id=self.pk).first()

            if unidade:
                lotes = Lote.objects.filter(unidade=unidade.pk)
                resultado = [lote.setor for lote in lotes]

        return ", ".join(resultado)

    @cached_property
    def enderecos_quadra(self):
        resultado = []

        if self.classe != "R":
            unidade = Unidade.objects.filter(imovel_id=self.pk).first()

            if unidade:
                lotes = Lote.objects.filter(unidade=unidade.pk)
                resultado = [lote.quadra for lote in lotes]

        return ", ".join(resultado)

    @cached_property
    def enderecos_lote(self):
        resultado = []

        if self.classe != "R":
            unidade = Unidade.objects.filter(imovel_id=self.pk).first()

            if unidade:
                lotes = Lote.objects.filter(unidade=unidade.pk)
                resultado = [lote.numero_unidade for lote in lotes]

        return ", ".join(resultado)

    @cached_property
    def enderecos_area(self):
        resultado = []

        if self.classe != "R":
            unidade = Unidade.objects.filter(imovel_id=self.pk).first()

            if unidade:
                lotes = Lote.objects.filter(unidade=unidade.pk)
                resultado = [lote.area for lote in lotes]

        return ", ".join(resultado)

    @cached_property
    def get_ficha_das_unidades_no_condominio_pelo_id(self: "Livro02"):
        if not self.pk or self.pk == 0:
            return 0

        # BUSCANDO A FICHA MAE
        ficha = FichaAuxiliar.objects.get(id=self.pk)

        # PEGANDO A UNIDADE - PELO ID DA UNIDADE DA FICHA MAE
        if ficha.unidade_id > 0:
            return Unidade.objects.filter(registro_anterior_id=ficha.unidade_id)
        else:
            return None


class Livro04(Livro02):
    """
    Livro 04 é o Livro de Registros Reais (Imóveis).

    Um Registro Real é a representação de um imóvel no cartório.

    """

    class Meta:
        proxy = True
        verbose_name = "Real"
        verbose_name_plural = "Reais"

    def __str__(self) -> str:
        return str(self.pk)

    def get_imovel(self, pk):
        return self.objects.get(pk=pk)


class Contribuintes(models.Model):
    """Na prefeitura cada imóvel tem um numero de contribuinte."""

    imovel = models.ForeignKey(
        Livro02,
        on_delete=models.CASCADE,
        default=0,
        related_name="contribuintes",
        verbose_name="Registro",
    )
    valor = models.DecimalField(
        default=0,
        blank=False,
        decimal_places=2,
        max_digits=12,
        verbose_name="Valor",
    )
    numero_contribuinte: str = models.CharField(max_length=100, blank=True, null=True)

    objects = models.Manager()

    def __str__(self) -> str:
        return f"{self.imovel} ({self.numero_contribuinte})"


class TipoUnidade(BaseModel):
    # A	Apartamento
    # B	Box
    # C	Casa
    # E	Escaninho
    # J	Loja
    # K	Kitchenette
    # O	Conjunto
    # R	Lote
    # S	Sala
    # T	Estudio
    # G	Garagem
    # F	Fazenda
    # L Loteamento
    # I Imovel
    id: str = models.CharField(
        max_length=3,
        primary_key=True,
        verbose_name="ID",
        auto_created=True,
        serialize=False,
    )
    descricao: str = models.CharField(max_length=40, blank=True, null=True)

    objects: managers.TipoUnidadeManager = managers.TipoUnidadeManager()

    class Meta:
        verbose_name = "Tipo de Unidade"
        verbose_name_plural = "Tipos de Unidade"

    def __str__(self) -> str:
        return self.descricao

    @classmethod
    def get_tipo_unidade_padrao(cls) -> str:
        return cls.objects.get_or_create(pk="I", descricao="Imóvel")[0]


class Unidade(BaseModel):
    # imovel = models.BigIntegerField()
    imovel = models.ForeignKey(
        Livro02,
        on_delete=models.SET_NULL,
        null=True,
        related_name="unidades",
    )
    # registro_anterior = models.BigIntegerField()
    registro_anterior = models.ForeignKey(
        Livro02,
        on_delete=models.SET_NULL,
        null=True,
        related_name="imoveis",
    )
    # id = models.ForeignKey(Lote, on_delete=models.SET_NULL, null=True, related_name="lotes")

    numero_unidade: str = models.CharField(
        max_length=30,
        blank=True,
        null=True,
        default="",
        verbose_name="Número da Unidade",
        help_text="Número da unidade.",
    )

    # tipo:str = models.CharField(max_length=3, blank=True, null=True)
    tipo = models.ForeignKey(
        TipoUnidade,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tipo_de_unidadade",
        default=TipoUnidade.get_tipo_unidade_padrao,
    )
    construida: str = models.CharField(
        max_length=1,
        blank=True,
        null=True,
        default="F",
        choices=(("T", "Sim"), ("F", "Não")),
        verbose_name="Construída",
        help_text="Define se a unidade está construída ou não.",
    )
    nome_edificio: str = models.CharField(
        max_length=400,
        blank=True,
        null=True,
        default="",
        verbose_name="Nome do Edifício",
        help_text="Nome do edifício onde a unidade está localizada.",
    )
    quadra: str = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        default="",
        verbose_name="Quadra",
        help_text="Quadra onde a unidade está localizada.",
    )
    area: str = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        default="",
        verbose_name="Área",
        help_text="Área da unidade.",
    )
    lote_auxiliar: str = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        default="",
        verbose_name="Lote Auxiliar",
        help_text="Lote auxiliar da unidade.",
    )
    sequencial = models.BigIntegerField(
        default=0,
        blank=True,
        null=True,
        verbose_name="Sequencial",
        help_text="Sequencial da unidade.",
    )
    bloco: str = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        default="",
        verbose_name="Bloco",
        help_text="Bloco onde a unidade está localizada.",
    )
    gleba: str = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        default="",
        verbose_name="Gleba",
        help_text="Gleba onde a unidade está localizada.",
    )

    objects: managers.UnidadeManager = managers.UnidadeManager()

    class Meta:
        verbose_name = "Unidade"
        verbose_name_plural = "Unidade"

    def __str__(self) -> str:
        return str(self.tipo)

    @classmethod
    def get_tipo_pelo_id(cls, unidade_id) -> str:
        try:
            return cls.objects.get(pk=unidade_id).tipo
        except cls.DoesNotExist:
            return ""

    def get_nomes_das_ruas(self):
        nomes_ruas = [rua.nome for rua in self.ruas.all()]

        # Junta todos os nomes das ruas, separados por vírgula, em uma única string.
        return ", ".join(nomes_ruas)

    @classmethod
    def get_nomes_das_ruas_pela_unidade_id(cls, unidade_id) -> str:
        nomes_ruas = [rua.nome for rua in Rua.objects.filter(unidade_id=unidade_id)]

        # Junta todos os nomes das ruas, separados por vírgula, em uma única string.
        return ", ".join(nomes_ruas)

    @cached_property
    def lote(self):
        return Lote.objects.filter(unidade=self.pk).first()


class Lote(models.Model):
    # unidade = models.BigIntegerField()
    # unidade = models.OneToOneField(Unidade, on_delete=models.CASCADE, related_name="lote")
    unidade = models.ForeignKey(Unidade, on_delete=models.SET_NULL, null=True)
    area: str = models.CharField(max_length=20, blank=True, null=True)
    quadra: str = models.CharField(max_length=50, blank=True, null=True)
    setor: str = models.CharField(max_length=150, blank=True, null=True)
    residencial: str = models.CharField(max_length=1, blank=True, null=True)
    numero_unidade: str = models.CharField(max_length=50, blank=True, null=True)
    numero_edificacao: str = models.CharField(max_length=20, blank=True, null=True)
    superquadra: str = models.CharField(max_length=100, blank=True, null=True)
    conjunto: str = models.CharField(max_length=200, blank=True, null=True)
    bloco: str = models.CharField(max_length=200, blank=True, null=True)
    outras: str = models.CharField(max_length=400, blank=True, null=True)
    unidade_aux: str = models.CharField(max_length=50, blank=True, null=True)
    comercial: str = models.CharField(max_length=1, blank=True, null=True)
    numero_municipal: str = models.CharField(max_length=100, blank=True, null=True)

    objects: managers.LoteManager = managers.LoteManager()

    class Meta:
        verbose_name = "Lote"
        verbose_name_plural = "Lote"

    def __str__(self) -> str:
        return f"{self.numero_unidade} - {self.area} m²"

    @staticmethod
    def get_total_lotes_associados(imovel_id: int = 0) -> int:
        return (
            Lote.objects.filter(
                unidade__in=Unidade.objects.filter(registro_anterior=imovel_id),
            ).count()
            if imovel_id
            else 0
        )


class TipoLogradouro(models.Model):
    """Tipos de Logradouros. Ex: Avenida, Rua e etc."""

    descricao: str = models.CharField(max_length=40, blank=True, null=True)
    codigo: str = models.CharField(max_length=10, blank=True, null=True)

    objects: managers.TiposLogradourosManager = managers.TiposLogradourosManager()

    class Meta:
        verbose_name = "Tipo de Logradouro"
        verbose_name_plural = "Tipos de Logradouros"

    def __str__(self) -> str:
        return self.descricao

    @classmethod
    def get_default(cls) -> None:
        return TipoLogradouro.objects.get_or_create(
            id=177,
            descricao="Não Especificado",
        )[0]

    @classmethod
    def get_default_id(cls) -> int:
        return TipoLogradouro.get_default().id if TipoLogradouro.get_default() else 177


class Rua(models.Model):
    unidade = models.ForeignKey(
        Unidade,
        on_delete=models.CASCADE,
        related_name="ruas",
        blank=True,
        null=True,
    )

    # logradouro = models.BigIntegerField(blank=True, null=True, default=0)

    logradouro = models.ForeignKey(
        TipoLogradouro,
        on_delete=models.CASCADE,
        related_name="ruas",
        blank=True,
        null=True,
        # default=TipoLogradouro.get_default_id,
    )

    nome: str = models.CharField(max_length=150, default="", blank=True, null=True)
    numero_edificacao: str = models.CharField(
        max_length=20,
        default="",
        blank=True,
        null=True,
    )
    cep: str = models.CharField(max_length=10, default="", blank=True, null=True)
    tipo: str = models.CharField(max_length=100, default="", blank=True, null=True)
    complemento: str = models.CharField(
        max_length=300,
        default="",
        blank=True,
        null=True,
    )

    class Meta:
        verbose_name = "Rua"
        verbose_name_plural = "Ruas"

    def __str__(self) -> str:
        return (
            f"{self.nome} - {self.numero_edificacao}"
            if self.numero_edificacao
            else self.nome
        )


class ImovelMedida(models.Model):
    imovel = models.ForeignKey(
        Livro02,
        on_delete=models.CASCADE,
        related_name="medidas",
    )

    m_frente_metros: str = models.CharField(max_length=100, blank=True, null=True)
    p_frente_metros: str = models.CharField(max_length=100, blank=True, null=True)

    m_direito_metros: str = models.CharField(max_length=100, blank=True, null=True)
    p_direito_metros: str = models.CharField(max_length=100, blank=True, null=True)

    p_esquerdo_metros: str = models.CharField(max_length=100, blank=True, null=True)
    m_esquerdo_metros: str = models.CharField(max_length=100, blank=True, null=True)

    p_fundo_metros: str = models.CharField(max_length=100, blank=True, null=True)
    m_fundo_metros: str = models.CharField(max_length=100, blank=True, null=True)

    objects: managers.ImovelMedidaManager = managers.ImovelMedidaManager()

    class Meta:
        verbose_name = "Medida"
        verbose_name_plural = "Medidas"

    def __str__(self) -> str:
        return self.imovel


class Anterior(models.Model):
    imovel = models.ForeignKey(
        Livro02,
        on_delete=models.CASCADE,
        null=True,
        related_name="anteriores",
    )

    numero = models.BigIntegerField(blank=True, null=True)
    tipo: str = models.CharField(max_length=1, blank=True, null=True)
    complemento: str = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        verbose_name = "Registro Anterior"
        verbose_name_plural = "Registros Anteriores"

    def __str__(self) -> str:
        return self.numero

    @cached_property
    def tipo_descrito(self):
        return TipoRegistro.get_descricao(self.tipo)

    @cached_property
    def numero_formatado(self):
        return helpers.formatar_numero_registro(self.numero)


class Titulo(models.Model):
    """Titulo são documentos usados para a prática de atos cartorários. Exemplos: Escritura, Contrato, etc."""

    tipo_titulo: str = models.CharField(max_length=40, blank=True, null=True)
    exibir: str = models.CharField(max_length=1, blank=True, null=True)
    prazo = models.BigIntegerField(default=20)
    prazo_reentrada = models.BigIntegerField(default=3)
    prazo_validade = models.BigIntegerField(default=20)
    ato_principal: str = models.CharField(max_length=1, blank=True, null=True)
    prazo_nota_devolucao = models.BigIntegerField(default=10)
    prazo_nota_devolucao_complexo = models.BigIntegerField(default=10)
    titulo_prenotacao: str = models.CharField(
        max_length=1,
        blank=True,
        null=True,
        default=TipoSimNao.NAO,
        choices=TipoSimNao.CHOICES,
    )

    objects: managers.TituloManager = managers.TituloManager()

    class Meta:
        verbose_name = "Titulo de Protocolo"
        verbose_name_plural = "Titulos de Protocolo"

    def __str__(self) -> str:
        return (
            self.tipo_titulo.title()
            if self.tipo_titulo
            else "[Tipo de Titulo Não Informado]"
        )

    @cached_property
    def provisorio_id(self):
        return Titulo.get_default_titulo_provisorio_id()

    @classmethod
    def get_default_titulo_provisorio_id(cls) -> int:
        tipo_titulo = cls.objects.filter(tipo_titulo__icontains=PROVISORIO).first()
        return tipo_titulo if tipo_titulo else 96


# class TipoAto(models.Model):
#     codigo_doi_id = models.BigIntegerField(blank=True, null=True)
#     tipo:str = models.CharField(max_length=40, blank=True, null=True)
#     utilizar:str = models.CharField(max_length=1, blank=True, null=True)

#     class Meta:
#         verbose_name = "Tipo de Ato"
#         verbose_name_plural = "Tipos de Ato"

#     def __str__(self) -> str:
#         return self.tipo


class Configuracao(ConfiguracaoMixin, BaseModel):
    def __str__(self) -> str:
        return self.chave

    @staticmethod
    def obter(chave: str, fallback: str = "") -> str:
        chave = str(chave).lower()
        configuracao = Configuracao.objects.filter(chave=chave).first()

        if configuracao:
            # Se uma configuração já existe, retorna o valor, se existente, ou o fallback se o valor estiver vazio
            valor = configuracao.valor if configuracao.valor else fallback
            logger.debug(f"CONFIG obtida no BD: {chave} = {valor}")
            return valor
        else:
            # Se a configuração não existe, tenta recuperar de settings
            logger.debug(f"CONFIG: Não encontrada no banco de dados: {chave}")
            config_default = f"DEFAULT_{str(chave).upper()}"
            valor = getattr(settings, config_default, fallback)
            if valor is None:
                logger.info(
                    f"CONFIG: não encontrada nos settings: {config_default}",
                )
                valor = fallback
                logger.info(f"CONFIG: Usando valor padrão: {valor}")
            else:
                logger.info(f"CONFIG: Usando valor dos settings: {valor}")

            # Cria a configuração no banco apenas se não existir
            Configuracao.objects.create(chave=chave, valor=valor)
            logger.debug(f"CONFIG: criada no banco de dados: {chave} = {valor}")

            return valor

    @classmethod
    def get_lista(cls, chave, opcao="TEXTO") -> list:
        valor = cls.obter(chave)

        # Caso não encontre nenhum valor, retorna uma lista vazia
        if not valor:
            return []

        lista_valores = valor.split(",")

        # Converte para inteiro se a opção for "INTEIRO"
        if opcao == "INTEIRO":
            lista_valores = [int(val) for val in lista_valores if val.isdigit()]

        return lista_valores

    @staticmethod
    def usar_selo_sql_server() -> bool:
        usuario_atual: User = get_current_user()
        return usuario_atual.cartorio.usar_selo_sql_server == "S"

    @staticmethod
    def exibir_site_no_cabecalho() -> bool:
        return Configuracao.obter("exibir_site_no_cabecalho", "S") == "S"

    @property
    def all(self):
        return Configuracao.objects.all()


class AtoPratica(models.Model):
    tipo_ato: str = models.CharField(max_length=40, blank=True, null=True)
    codigo_doi_id = models.BigIntegerField(null=True)
    pasta_minutas: str = models.CharField(max_length=200, blank=True, null=True)
    exibir: str = models.CharField(
        max_length=1,
        blank=True,
        null=True,
        default=TipoSimNao.SIM,
        choices=TipoSimNao.CHOICES,
    )
    tipo: str = models.CharField(
        max_length=2,
        blank=True,
        null=True,
        choices=TipoAto.CHOICES,
    )
    titulo = models.ForeignKey(Titulo, on_delete=models.CASCADE, blank=True, null=True)
    ato_principal: str = models.CharField(
        max_length=1,
        blank=True,
        null=True,
        default=TipoSimNao.NAO,
        choices=TipoSimNao.CHOICES,
    )
    # emolumentos = models.ForeignKey(Emolumentos, on_delete=models.CASCADE)
    emolumento = models.BigIntegerField(blank=True, null=True)
    dias_uteis = models.BigIntegerField(blank=True, null=True)
    ato_default: str = models.CharField(
        max_length=1,
        blank=True,
        null=True,
        default=TipoSimNao.NAO,
        choices=(TipoSimNao.CHOICES),
    )
    dias_uteis_reentrada = models.DecimalField(
        blank=False,
        max_digits=12,
        decimal_places=2,
        default=5,
    )

    peso_titulo = models.BigIntegerField(default=1)

    ato_prenotacao: str = models.CharField(
        max_length=1,
        blank=True,
        null=True,
        default=TipoSimNao.NAO,
        choices=TipoSimNao.CHOICES,
    )

    objects: managers.AtosManager = managers.AtosManager()

    class Meta:
        verbose_name = "Ato Praticavel"
        verbose_name_plural = "Atos Praticaveis"
        ordering = ["tipo_ato"]

    def __str__(self) -> str:
        return self.tipo_ato

    @staticmethod
    def provisorio_id() -> int:
        return AtoPratica.get_ato_provisorio_id()

    @staticmethod
    def get_ato_provisorio_id() -> int:
        try:
            tipo_ato = AtoPratica.objects.get_or_create(tipo_ato__icontains=PROVISORIO)[
                0
            ]
            return tipo_ato.id
        except AtoPratica.MultipleObjectsReturned:
            logger.warning("ERRO: Mais de um tipo de ato provisório encontrado.")
            tipo_ato = (
                AtoPratica.objects.filter(tipo_ato__icontains=PROVISORIO)
                .order_by("id")
                .first()
            )
        return tipo_ato.id

    @classmethod
    def get_default_ato_provisorio(cls) -> int:
        tipo_ato = cls.objects.filter(tipo_ato__icontains=PROVISORIO).first()
        return tipo_ato.id if tipo_ato else 392


# Create your models here.
def get_next_pedido():
    try:
        return Pedido.objects.latest("numero").numero + 1
    except Pedido.DoesNotExist:
        return 1


class Pedido(models.Model):
    """Pedido de Protocolo."""

    data_entrada = models.DateField(
        null=True,
        blank=True,
        default=date.today,
        verbose_name="Dt Entrada",
    )
    data_prevista = models.DateField(
        null=True,
        blank=True,
        default=date.today,
        verbose_name="Dt Prevista",
    )
    data_validade = models.DateField(
        null=True,
        blank=True,
        default=date.today,
        verbose_name="Dt Validade",
    )
    observacao: str = models.CharField(
        max_length=500,
        default="",
        blank=True,
        null=True,
        verbose_name="Anotações",
    )
    tipo_servico: str = models.CharField(
        max_length=1,
        default="",
        blank=True,
        null=True,
        verbose_name="Tipo de Serviço",
    )
    numero_talao = models.BigIntegerField(
        blank=True,
        default=0,
        null=True,
        verbose_name="Nº Talão",
    )
    numero = models.BigIntegerField(
        blank=True,
        null=True,
        default=get_next_pedido,
        verbose_name="Nº Pedido",
    )
    # Dados do apresentante:
    endereco: str = models.CharField(
        max_length=300,
        default="",
        blank=True,
        null=True,
        verbose_name="Endereço do Apresentante",
    )
    municipio: str = models.CharField(
        max_length=20,
        default="",
        blank=True,
        null=True,
        verbose_name="Município do Apresentante",
    )
    uf = models.BigIntegerField(
        blank=True,
        default=Uf.get_default_uf_numero,
        null=True,
        verbose_name="UF",
    )
    telefone: str = models.CharField(
        max_length=40,
        default="",
        null=True,
        verbose_name="Telefone do Apresentante",
    )
    telefone1: str = models.CharField(
        max_length=40,
        default="",
        blank=True,
        null=True,
        verbose_name="Telefone 2 do Apresentante",
    )
    email = models.EmailField(
        blank=True,
        null=True,
        default="",
        verbose_name="E-mail",
        help_text="E-mail do solicitante",
    )
    tipo_documento_apresentante = models.BigIntegerField(
        blank=True,
        null=True,
        verbose_name="Tipo de Documento do Apresentante",
        help_text="Exemplo: CPF, CNPJ",
    )
    documento_apresentante: str = models.CharField(
        max_length=20,
        default="",
        blank=True,
        null=True,
        verbose_name="Número do Documento",
    )

    objects: managers.PedidosManager = managers.PedidosManager()

    # itens_do_pedido: QuerySet["PedidoItem"]

    class Meta:
        verbose_name = "Pedido"
        verbose_name_plural = "Pedidos"

    def __str__(self: "Pedido") -> str:
        return f"nº {self.numero} de {self.data_entrada}"

    # por {self.nomeadquirente}"

    def pedidos_itens(self: "Pedido") -> QuerySet["PedidoItem"]:
        # return PedidoItem.objects.filter(pedido_id=self.pk)
        return self.itens_do_pedido

    @cached_property
    def itens(self: "Pedido") -> QuerySet["PedidoItem"]:
        return self.itens_do_pedido

    def criar_partes_do_fb(self, pedido_fb: dict):
        PedidoParte.objects.deletar_por_pedido_id(self.pk)
        PedidoParte.objects.criar_do_fb(self, pedido_fb)

    def _calculate_aggregates(self) -> None:
        if not hasattr(self, "_aggregates"):
            self._aggregates = self.itens_do_pedido.aggregate(
                max_prazo=Max("titulo__prazo"),
                max_prazo_reentrada=Max("titulo__prazo_reentrada"),
                max_prazo_validade=Max("titulo__prazo_validade"),
                max_prazo_nota_devolucao=Max("titulo__prazo_nota_devolucao"),
                max_prazo_nota_devolucao_complexo=Max(
                    "titulo__prazo_nota_devolucao_complexo",
                ),
            )

    @cached_property
    def max_prazo(self):
        self._calculate_aggregates()
        return self._aggregates["max_prazo"]

    @cached_property
    def max_prazo_reentrada(self):
        self._calculate_aggregates()
        return self._aggregates["max_prazo_reentrada"]

    @cached_property
    def max_prazo_validade(self):
        self._calculate_aggregates()
        return self._aggregates["max_prazo_validade"]

    @cached_property
    def max_prazo_nota_devolucao(self):
        self._calculate_aggregates()
        return self._aggregates["max_prazo_nota_devolucao"]

    @cached_property
    def max_prazo_nota_devolucao_complexo(self):
        self._calculate_aggregates()
        return self._aggregates["max_prazo_nota_devolucao_complexo"]

    @cached_property
    def documento_apresentante_formatado(self):
        return formatar_documento(
            self.documento_apresentante,
            self.tipo_documento_apresentante,
        )

    @cached_property
    def itens_de_livro02_numero(self):
        pedido_livro_02 = PedidoItem.objects.get_registros_por_pedido(
            self.pk,
        ).values_list("numero_registro", flat=True)
        # Converte os números de registro em strings e junta com ", "
        return ", ".join(map(str, pedido_livro_02))

    @cached_property
    def itens_de_livro03(self):
        return PedidoItem.objects.get_registros_auxiliares_por_pedido(self.pk)

    @cached_property
    def registros(self):
        return PedidoItem.objects.get_registros_por_pedido(self.pk)

    @cached_property
    def nome_solicitante_formatado(self) -> str:
        return formatar_nome(self.nome_solicitante)

    @cached_property
    def nome_solicitante(self: "Pedido") -> str:
        # parte = PedidoParte.objects.filter(pedido=self, papel=SIM).first()

        solicitante = self.partes.filter(papel=SIM).first()

        # VERIFICAR SE A PARTE EXISTE
        if solicitante:
            return solicitante.pessoa.nome if solicitante.pessoa else ""
        else:
            return ""

    @cached_property
    def pronto_para_registrar(self) -> "Livro01Andamento":
        andamento_pronto_para_registrar = (
            Livro01Andamento.objects.get_queryset()
            .filter(
                protocolo_id=self.pk,
                tipo_andamento__grupo_pronto_registrar="S",
            )
            .order_by("data")
            .last()
        )

        return (
            andamento_pronto_para_registrar if andamento_pronto_para_registrar else None
        )

    @cached_property
    def totais(self) -> dict:
        return {
            "valor_total_sum": self.valor_total_pedido,
            "valor_emolumento_sum": self.valor_emolumento_sum,
            "valor_tfj_sum": self.valor_tfj_sum,
            "valor_issqn_sum": self.valor_issqn_sum,
            "valor_fundo_estado_sum": self.valor_fundo_estado_sum,
        }

    @cached_property
    def valor_total_pedido(self) -> Decimal:
        from apps.pedidos.models import Pedido as PedidoPrime

        # VERIFICAR SE O VALOR ESTA NO PEDIDO DO PRIME
        pedido_prime = PedidoPrime.objects.filter(
            numero_protocolo_firebird=self.protocolo.numero_protocolo,
        ).first()

        if pedido_prime:
            return pedido_prime.total_pedido_de_protocolo or 0.0
        else:
            return sum(
                item.valor_total for item in self.itens_do_pedido.all()
            ) or Decimal("0.0")

    @cached_property
    def valor_diferenca(self) -> Decimal:
        return self.valor_total_pedido or 0 - self.valor_total_pago or 0

    @cached_property
    def valor_emolumento_sum(self) -> Decimal:
        from apps.pedidos.models import Pedido as PedidoPrime

        # VERIFICAR SE O VALOR ESTA NO PEDIDO DO PRIME
        pedido_prime = PedidoPrime.objects.filter(
            numero_protocolo_firebird=self.protocolo.numero_protocolo,
        ).first()

        if pedido_prime:
            return pedido_prime.total_emolumentos_pedido_de_protocolo or 0.0
        else:
            return (
                self.itens_do_pedido.aggregate(Sum("valor_emolumento"))[
                    "valor_emolumento__sum"
                ]
                or 0.0
            )

    @cached_property
    def valor_tfj_sum(self) -> Decimal:
        from apps.pedidos.models import Pedido as PedidoPrime

        # VERIFICAR SE O VALOR ESTA NO PEDIDO DO PRIME
        pedido_prime = PedidoPrime.objects.filter(
            numero_protocolo_firebird=self.protocolo.numero_protocolo,
        ).first()

        if pedido_prime:
            return pedido_prime.total_taxa_fiscal_judiciaria_pedido or 0.0
        else:
            return (
                self.itens_do_pedido.aggregate(Sum("valor_tfj"))["valor_tfj__sum"]
                or 0.0
            )

    @cached_property
    def valor_issqn_sum(self) -> Decimal:
        from apps.pedidos.models import Pedido as PedidoPrime

        # VERIFICAR SE O VALOR ESTA NO PEDIDO DO PRIME
        pedido_prime = PedidoPrime.objects.filter(
            numero_protocolo_firebird=self.protocolo.numero_protocolo,
        ).first()

        if pedido_prime:
            return pedido_prime.total_issqn_pedido_de_protocolo or 0.0
        else:
            valor_issqn_calculado = sum(
                [item.valor_issqn_calculado for item in self.itens_do_pedido.all()],
            )
            return valor_issqn_calculado or Decimal("0")

    @cached_property
    def valor_fundo_estado_sum(self) -> Decimal:
        from apps.pedidos.models import Pedido as PedidoPrime

        # VERIFICAR SE O VALOR ESTA NO PEDIDO DO PRIME
        pedido_prime = PedidoPrime.objects.filter(
            numero_protocolo_firebird=self.protocolo.numero_protocolo,
        ).first()

        if pedido_prime:
            return pedido_prime.total_fundo1_pedido_de_protocolo or 0.0
        else:
            return (
                self.itens_do_pedido.aggregate(Sum("valor_fundo_estado"))[
                    "valor_fundo_estado__sum"
                ]
                or 0.0
            )

    @cached_property
    def valor_total_pedido_sum(self) -> Decimal:
        if self.valor_emolumento_sum:
            return (
                Decimal(self.valor_emolumento_sum)
                + Decimal(self.valor_fundo_estado_sum)
                + Decimal(self.valor_tfj_sum)
                + Decimal(self.valor_issqn_sum)
            )
        else:
            return 0.0

    @cached_property
    def estado(self):
        return UnidadeFederativa.retornar_estado(self.uf) if self.uf else ""

    @cached_property
    def chave(self):
        return str(int(self.pk))

    @cached_property
    def titulos(self):
        return self.itens_do_pedido.select_related("titulo").values("titulo")

    def get_prazo_em_dias(self, opcao="P") -> tuple:
        data_retorno = self.protocolo.data_protocolo
        dias_retorno = self.max_prazo

        if str(opcao) == "V":
            dias_retorno = self.max_prazo_validade
        elif str(opcao) == "N":
            dias_retorno = self.max_prazo_nota_devolucao

        if not dias_retorno:
            dias_retorno = 20

        return data_retorno, int(dias_retorno)

    def data_exigencia(self) -> None:
        data_hora, max_dias = self.get_prazo_em_dias("V")

    def selos(self) -> QuerySet["SeloEletronico"]:
        pedido_itens = self.itens_do_pedido.all()
        return SeloEletronico.objects.filter(pedido_item__in=pedido_itens)

    @cached_property
    def registros_financeiros(self) -> QuerySet["Financeiro"]:
        registros_financeiros_do_pedido = self.registros_financeiros_do_pedido
        return (
            registros_financeiros_do_pedido
            if registros_financeiros_do_pedido
            else Financeiro.objects.none()
        )


class TipoFaseProtocolo(models.Model):
    """
    ### Tipos de Fase:
    Recepção, Digitalização, Análise, Registro, Arquivo, Entrega, Cancelamento.

    """

    ordem = models.BigIntegerField(blank=True, null=True)
    descricao: str = models.CharField(max_length=1, blank=True, null=True)
    nome: str = models.CharField(max_length=100, blank=True, null=True)
    prazo_dias = models.BigIntegerField(blank=True, null=True)
    grupo = models.BigIntegerField(blank=True, null=True)

    objects: managers.FasesProtocoloManager = managers.FasesProtocoloManager()

    class Meta:
        verbose_name = "Fase do Protocolo"
        verbose_name_plural = "Fases do Protocolo"

    def __str__(self) -> str:
        return formatar_nome(self.nome)

    def fase_protocolo_default() -> "TipoFaseProtocolo":
        #  BUG QUE ESTAVA ATRAPHANDO A IMPORTACAO

        # try:
        #     return TipoFaseProtocolo.objects.get_or_create(descricao="Recepção").first()
        # except TipoFaseProtocolo.MultipleObjectsReturned:
        #     logger.warning("Mais de uma fase padrão encontrada")
        #     return TipoFaseProtocolo.objects.filter(descricao="Recepção").first()
        return None

    def fase_protocolo_default_id(self) -> int:
        fase = self.fase_protocolo_default()
        return fase.pk if fase else 1


class FaseAgenda(models.Model):
    nome: str = models.CharField(max_length=100, blank=True, null=True)
    prazo = models.BigIntegerField(default=1)
    prazo_opcional = models.BigIntegerField(default=1)
    descricao: str = models.CharField(max_length=200, blank=True, null=True)
    usar_data_atual: str = models.CharField(
        max_length=1,
        blank=True,
        null=True,
        default=TipoSimNao.NAO,
        choices=(TipoSimNao.CHOICES),
    )

    objects: managers.FasesAgendaManager = managers.FasesAgendaManager()

    class Meta:
        verbose_name = "Fase da Agenda"
        verbose_name_plural = "Fases da Agenda"

    def __str__(self) -> str:
        return self.nome


class FaseAgendaItem(models.Model):
    fase_agenda = models.ForeignKey(FaseAgenda, on_delete=models.CASCADE, default=1)
    status = models.ForeignKey(
        StatusProtocolo,
        on_delete=models.CASCADE,
        null=True,
        default=0,
    )
    objects: managers.FaseAgendaItensManager = managers.FaseAgendaItensManager()

    class Meta:
        unique_together = ["fase_agenda", "status"]
        verbose_name = "Fase da Agenda Itens"
        verbose_name_plural = "Fases da Agenda Itens"

    def __str__(self) -> str:
        if self.fase_agenda:
            return f"{self.fase_agenda} - {self.status}"
        return self.id


class Colaborador(models.Model):
    """
    Colaborador é quem está responsável por um protocolo em determinada fase.
    Não confundir com o usuário do sistema, (login) que é quem acessa o sistema.
    Nem todo colaborador tem um login (usuario) do sistema.
    """

    nome: str = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Nome",
    )
    inativo: str = models.CharField(
        max_length=1,
        blank=True,
        null=True,
        default=TipoSimNao.NAO,
        choices=TipoSimNao.CHOICES,
        verbose_name="Inativo",
    )
    default: bool = models.BooleanField(default=False, verbose_name="Padrão")
    antigo_id: str = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        default="",
        verbose_name="ID Antigo",
    )
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="Usuário",
        related_name="colaborador",
    )
    recebe_protocolos_do_balcao: bool = models.BooleanField(
        default=False,
        verbose_name="Pode receber protocolo do balcão",
        help_text="Marque se o colaborador pode receber protocolos do balcão.",
    )
    calcula_peso: bool = models.BooleanField(
        default=True,
        verbose_name="Calcular Peso",
        help_text="Marque se o colaborador deve ter o peso dos protocolos calculados",
    )

    exibir_nome_caixa: bool = models.BooleanField(
        default=True,
        verbose_name="Pode visualizar o caixa completo",
        help_text="Marque se o colaborador pode visualizar o caixa completo.",
    )

    objects: managers.ColaboradorManager = managers.ColaboradorManager()

    class Meta:
        ordering = ["nome"]
        verbose_name = "Colaborador"
        verbose_name_plural = "Colaboradores"

    def __str__(self) -> str:
        nome = self.usuario.first_name if self.usuario else self.nome
        return formatar_nome(nome)

    def get_distribuidos_url(self):
        return reverse("home:distribuidos_por_colaborador", args=(self.pk,))

    @classmethod
    def processar_colaboradores(cls, funcionarios_fb: list) -> None:
        with transaction.atomic():
            cls.atualizar_colaboradores_existentes(funcionarios_fb)
            cls.criar_ou_atualizar_colaboradores(funcionarios_fb)

    @classmethod
    def atualizar_colaboradores_existentes(cls, funcionarios_fb) -> None:
        funcionarios_ids = [fb["CHAVE_FUNCIONARIOS"] for fb in funcionarios_fb]
        usuarios = User.objects.filter(pk__in=funcionarios_ids)

        for usuario in usuarios:
            if usuario:
                novo_nome = f"{usuario.username} -- ({uuid.uuid4()}) EXCLUIR"
                cls.marcar_como_excluir_e_atualizar_referencias(usuario, novo_nome)

    @classmethod
    def marcar_como_excluir_e_atualizar_referencias(cls, usuario, novo_nome) -> None:
        usuario.username = novo_nome
        usuario.save()
        # Atualiza todas as referências de uma vez usando pk do usuário
        cls.atualizar_referencias_usuario(usuario.pk)

    @classmethod
    def atualizar_referencias_usuario(cls, usuario_id) -> None:
        # models_to_update = [Livro01Protocolo, Livro01Andamento, Financeiro, EventMember]
        # for model in models_to_update:
        #     model.objects.filter(colaborador_id=usuario_id).update(colaborador=usuario_id)
        pass

    @classmethod
    def criar_ou_atualizar_colaboradores(cls, funcionarios_fb) -> None:
        # for funcionario_fb in funcionarios_fb:
        #     funcionario_id = funcionario_fb["CHAVE_FUNCIONARIOS"]
        #     funcionario_nome = cls.get_nome_mapeado(funcionario_fb["NOME"])
        #     defaults = {"username": funcionario_nome, "password": make_password("CONFIGURAR_LOCALMENTE")}
        #     Usuario.objects.update_or_create(pk=funcionario_id, defaults=defaults)
        pass

    @classmethod
    def importar_protocolos_do_fb(cls, db: "FbConnection") -> None:
        from apps.home.services import firebird

        firebird.importar_protocolos_por_colaborador(cls.pk, db)

    @cached_property
    def image(self) -> str:
        # Verifica se self.usuario existe e possui uma imagem
        if self.usuario and self.usuario.image:
            return self.usuario.image
        # Caso contrário, retorna o caminho da imagem padrão
        return static("assets/images/user/anon.png")

    @cached_property
    def username(self: "Colaborador") -> str:
        return self.usuario.username if self.usuario else ""

    @cached_property
    def nome_mapeado(self: "Colaborador") -> str:
        return Colaborador.get_nome_mapeado(self.nome) if self.nome else ""

    @cached_property
    def nome_com_quantidade_de_protocolo(self: "Colaborador") -> str:
        """Retorna o nome do colaborador com a quantidade de protocolos em aberto."""
        if self.usuario:
            return f"{self.usuario.username} ({self.protocolos_em_aberto.count()})"
        return self.nome + f"({self.protocolos_em_aberto.count()})"

    @cached_property
    def protocolos(self: "Colaborador") -> "Livro01ProtocoloQuerySet":
        logger.debug(f"Obtendo protocolos do colaborador: {self}")
        """Retorna todos os protocolos associados ao colaborador considerando apenas o último andamento."""
        return Livro01Protocolo.objects.filtrar_por_colaborador(self.pk)

    @cached_property
    def protocolos_em_aberto(self: "Colaborador") -> "Livro01ProtocoloQuerySet":
        logger.debug(f"Obtendo protocolos em aberto do colaborador: {self}")
        """Retorna todos os protocolos em aberto associados ao colaborador."""
        return self.protocolos.filtrar_em_aberto()

    @cached_property
    def protocolos_em_reentrada(self: "Colaborador") -> QuerySet["Livro01Protocolo"]:
        """Retorna todos os protocolos em reentrada associados ao colaborador."""
        logger.debug(f"Obtendo protocolos em reentrada do colaborador: {self}")
        return self.protocolos_em_aberto.filtrar_com_reentrada()

    @cached_property
    def protocolos_abertos_sem_reentrada(
        self: "Colaborador",
    ) -> QuerySet["Livro01Protocolo"]:
        """Retorna todos os protocolos em aberto sem reentrada associados ao colaborador."""
        logger.debug(
            f"Obtendo protocolos em aberto sem reentrada do colaborador: {self.pk}",
        )
        return self.protocolos_em_aberto.filtrar_sem_reentrada()

    @cached_property
    def peso_protocolos_em_aberto(self: "Colaborador") -> int:
        """Retorna o peso total dos protocolos em aberto associados ao colaborador."""
        logger.debug(
            f"Calculando peso dos protocolos em aberto do colaborador: {self.pk}",
        )

        if not self.calcula_peso:
            return 0

        try:
            # Filtrar e anotar em uma única consulta
            total_peso = self.protocolos.filter(data_finalizado__isnull=True).aggregate(
                total=Sum("pedido__itens_do_pedido__ato__peso_titulo"),
            )["total"]

            return total_peso or 0
        except Exception:
            logger.exception("Erro ao calcular o peso dos protocolos em aberto.")
            return 0

    @staticmethod
    def with_protocolos_em_aberto() -> QuerySet["Colaborador"]:
        # from apps.home.models import Livro01Protocolo

        subquery = Livro01Protocolo.objects.filter(
            colaborador=OuterRef("pk"),
            data_finalizado__isnull=True,
        ).values(
            "colaborador",
        )

        return Colaborador.objects.annotate(protocolos_em_aberto=Subquery(subquery))

    @staticmethod
    def get_nome_mapeado(nome: str) -> str:
        logger.debug(f"Mapeando nome do colaborador: {nome}")
        """
        Mapeia o nome do funcionário usando o dicionário NOME_MAP.
        Retorna o nome original se não houver mapeamento.
        """
        if not nome:
            return ""

        return formatar_nome(User.NOME_MAP.get(nome, nome))

    @classmethod
    def get_ou_criar_pelo_usuario(cls, user: "User") -> None:
        logger.debug(f"Obtendo ou criando colaborador pelo usuário: {user}")
        try:
            colaborador = cls.objects.filter(usuario=user).first()
        except cls.DoesNotExist:
            colaborador = cls.objects.create(nome=user.username, usuario=user)

        return colaborador

    # VERIFICAR SE O COLABORADOR ESTA CADASTRADO NO HOME COLABORADOR
    @classmethod
    def checar_ou_criar_colaborador(cls, colaborador_id) -> "Colaborador":
        logger.debug(f"Checando ou criando colaborador: {colaborador_id}")
        nome = "NAO INFORMADO: " + str(colaborador_id)
        colaborador = None

        # Tenta obter o colaborador pelo ID fornecido; se não existir, cria um novo.
        try:
            colaborador, criado = Colaborador.objects.get_or_create(
                pk=colaborador_id,
                defaults={
                    "nome": nome,
                },
            )
        except Exception:
            logger.exception(
                f"ERRO: Tentar criar um colaborador com o ID: {colaborador_id}",
            )

        # Retorna o objeto colaborador e um booleano indicando se foi criado ou não.
        return colaborador

    @classmethod
    def get_nome_por_id(cls, colaborador_id) -> str:
        logger.debug(f"Obtendo nome do colaborador pelo ID: {colaborador_id}")
        try:
            # Tentativa de obter diretamente o objeto colaborador.
            colaborador = Colaborador.objects.get(pk=colaborador_id)
        except ObjectDoesNotExist:
            # Retorna uma string vazia se o colaborador não existir.
            return ""
        else:
            # Retorna o nome do colaborador se ele existir.
            if colaborador.nome:
                return colaborador.nome
            else:
                return colaborador.usuario.first_name

    def get_or_create_default() -> "Colaborador":
        colaborador = Colaborador.objects.filter(default=True).first()

        if not colaborador:
            funcionario_id_sistema_antigo = Configuracao.obter(
                "funcionario_id_sistema_antigo",
                999998,
            )

            usuario = User.get_or_create_usuario_sistema()
            colaborador = Colaborador.objects.get_or_create(
                id=funcionario_id_sistema_antigo,
                defaults={
                    "nome": "Sistema",
                    "default": True,
                    "usuario": usuario,
                },
            )[0]

        return colaborador


class TipoFaseProtocoloColaborador(models.Model):
    fase_protocolos = models.ForeignKey(
        TipoFaseProtocolo,
        on_delete=models.CASCADE,
        default=1,
        related_name="colaboradores_fase_protocolos",
    )
    colaborador = models.ForeignKey(Colaborador, on_delete=models.CASCADE, default="0")
    fase_protocolos_solicitar_servicos = models.ForeignKey(
        TipoFaseProtocolo,
        on_delete=models.CASCADE,
        default=1,
        related_name="colaboradores_fase_protocolos_solicitar_servicos",
    )
    descricao: str = models.CharField(max_length=400, default="Aviso")

    class Meta:
        verbose_name = "Fase do Protocolo"
        verbose_name_plural = "Fases do Protocolo"

    def __str__(self) -> str:
        return self.descricao


class NivelAlerta(models.Model):
    descricao: str = models.CharField(max_length=400, default="Aviso")

    class Meta:
        verbose_name = "Nível de Alerta"
        verbose_name_plural = "Níveis de Alerta"

    def __str__(self) -> str:
        return self.descricao


class Lembrete(models.Model):
    imovel = models.ForeignKey(
        Livro02,
        on_delete=models.CASCADE,
        default=0,
        null=True,
        blank=True,
    )

    created_at: datetime = models.DateTimeField(auto_now_add=True)
    updated_at: datetime = models.DateTimeField(auto_now=True)
    descricao: str = models.CharField(max_length=400, default=".")
    funcionarios_create = models.ForeignKey(
        Colaborador,
        on_delete=models.CASCADE,
        related_name="lembretes_criados",
        default="0",
    )
    funcionarios_update = models.ForeignKey(
        Colaborador,
        on_delete=models.CASCADE,
        related_name="lembretes_atualizados",
        default="0",
    )
    nivel_alerta = models.ForeignKey(NivelAlerta, on_delete=models.CASCADE, default="0")

    class Meta:
        verbose_name = "Lembrete"
        verbose_name_plural = "Lembrete"

    def __str__(self) -> str:
        return self.descricao


class Livro01Protocolo(models.Model):
    numero_protocolo: str = models.CharField(
        max_length=20,
        verbose_name="Número do Protocolo",
        unique=True,
    )
    titulo = models.BigIntegerField(default=-1)
    pedido = models.OneToOneField(
        Pedido,
        on_delete=models.CASCADE,
        related_name="protocolo",
        verbose_name="Pedido",
    )
    # titulo_id           = models.ForeignKey(Titulo, on_delete=models.CASCADE)
    data_protocolo: datetime = models.DateTimeField(
        default=timezone.now,
        verbose_name="Entrada",
        help_text="Data de entrada do protocolo",
    )
    observacao = CKEditor5Field(
        blank=True,
        null=True,
        verbose_name="Anotações",
        help_text="Observações sobre o protocolo",
    )
    numero_origem = models.BigIntegerField(null=True, blank=True)
    origem_pedido = models.BigIntegerField(null=True, blank=True)
    fases_protocolo = models.ForeignKey(
        TipoFaseProtocolo,
        on_delete=models.SET_NULL,
        null=True,
        default=TipoFaseProtocolo.fase_protocolo_default,
        verbose_name="Fase do Protocolo",
    )

    fases_protocolo_colaborador = models.ForeignKey(
        Colaborador,
        on_delete=models.SET_NULL,
        null=True,
        related_name="colaborador_fase",
    )

    fases_protocolo_colaborador_atual = models.ForeignKey(
        Colaborador,
        on_delete=models.SET_NULL,
        null=True,
        related_name="colaborador_atual",
        verbose_name="Colaborador Atual",
    )

    data_distribuicao = models.DateField(blank=True, null=True)
    data_finalizado = models.DateField(blank=True, null=True)
    maximo_dias_titulo = models.BigIntegerField(null=True, blank=True, default=20)
    maximo_dias_titulo_reentrada = models.BigIntegerField(
        null=True,
        blank=True,
        default=5,
    )
    status = models.ForeignKey(
        StatusProtocolo,
        on_delete=models.SET_NULL,
        null=True,
        default=0,
    )
    fases_protocolo_colaborador_atual_data = models.DateField(blank=True, null=True)
    numero_protocolo_anterior = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="protocolo_anterior",
        verbose_name="Protocolo Anterior",
        help_text="Protocolo anterior é o protocolo que deu origem a este protocolo",
    )
    numero_protocolo_posterior = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="protocolo_posterior",
        verbose_name="Protocolo Posterior",
        help_text="Protocolo posterior é o protocolo que foi gerado a partir deste protocolo",
    )

    protocolo_onr: str = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        default="S",
        verbose_name="Protocolo ONR",
        help_text="Numero do Protocolo fornecido pela ONR.",
    )

    data_agendamento: datetime = models.DateTimeField(
        null=True,
        verbose_name="Agendamento",
    )

    objects: managers.Livro01ProtocoloQuerySet = (
        managers.Livro01ProtocoloQuerySet.as_manager()
    )

    itens_do_pedido: QuerySet["PedidoItem"]

    class Descricao(Enum):
        Distribuido = "Distribuído o Protocolo"

    class Meta:
        verbose_name = "Livro01 Protocolo"
        verbose_name_plural = "Livro01 Protocolos"
        indexes = [
            models.Index(fields=["numero_protocolo"]),
            models.Index(fields=["data_finalizado"]),
            models.Index(fields=["data_protocolo"]),
        ]
        # ordering = ["-numero_protocolo"]

    def __str__(self) -> str:
        """Retorna o número do protocolo formatado."""
        return str(self.protocolo_formatado)

    def get_absolute_url(self: "Livro01Protocolo") -> str:
        """Retorna a URL para o detalhe do protocolo."""
        return reverse("home:protocolo_detail", args=(self.pk,))

    def get_timeline_url(self: "Livro01Protocolo") -> str:
        """Retorna a URL para a timeline do protocolo."""
        return reverse("home:protocolo_timeline", args=(self.pk,))

    def get_add_andamento_url(self: "Livro01Protocolo") -> str:
        """Retorna a URL para adicionar um novo andamento ao protocolo."""
        return reverse("home:add_andamento", args=(self.pk,))

    def get_financeiro_url(self: "Livro01Protocolo") -> str:
        utlimo_registro_financeiro = self.get_registros_financeiros().last()
        return (
            reverse("home:financeiro_detalhe", args=(utlimo_registro_financeiro.pk,))
            if utlimo_registro_financeiro
            else ""
        )

    def get_pedido_url(self: "Livro01Protocolo") -> str:
        """Retorna a URL para o detalhe do pedido associado ao protocolo."""
        pedido_id = self.dados_do_pedido.get("id") if self.dados_do_pedido else 0
        if pedido_id == 0:
            return ""
        return reverse("pedidos:pedido_detail", kwargs={"pk": pedido_id})

    def get_confirmar_recebimento_url(self: "Livro01Protocolo") -> str:
        opcao_recebimento = "N" if self.recebido else "S"

        return (
            reverse(
                "home:colaborador_receber_protocolo",
                kwargs={
                    "protocolo_id": self.pk,
                    "colaborador_id": self.colaborador_destino.pk,
                    "opcao_recebimento": opcao_recebimento,
                },
            )
            if self.colaborador_destino
            else ""
        )

    def get_registros_financeiros(self: "Livro01Protocolo") -> QuerySet["Financeiro"]:
        return Financeiro.objects.filter(pedido__protocolo=self.pk).order_by("id")

    def get_recibo_de_protocolo_url(self: "Livro01Protocolo") -> str:
        base_url = reverse("home:impressao_recibo_protocolo")
        query_string = urlencode({"protocolo_id": self.pk}, doseq=True)
        return f"{base_url}?{query_string}"

    def get_recibo_url(self: "Livro01Protocolo") -> str:
        base_url = reverse("home:impressao_registrados")
        query_string = urlencode({"protocolo_id": self.pk}, doseq=True)
        return f"{base_url}?{query_string}"

    def get_andamentos_url(self: "Livro01Protocolo"):
        query_string = urlencode(
            {"numero_protocolo": self.numero_protocolo},
            doseq=True,
        )
        base_url = reverse("home:protocolo_andamentos", args=(self.pk,))
        return f"{base_url}?{query_string}"

    def get_sincronizar_url(self: "Livro01Protocolo"):
        return reverse("home:importar_protocolo", args=(self.numero_protocolo,))

    def numero_protocolo_inteiro(self: "Livro01Protocolo"):
        """RETORNA O NÚMERO DO PROTOCOLO SEM FORMATAÇÃO."""
        return str(self.numero_protocolo).replace(".", "").replace(",", "")

    @cached_property
    def dados_do_pedido(self: "Livro01Protocolo") -> dict:
        """Retorna os dados do pedido associado ao protocolo."""
        from apps.pedidos.models import Pedido as PedidoPrime

        pedido = PedidoPrime.objects.filter(
            numero_protocolo_firebird=self.numero,
        ).first()
        if not pedido:
            return {}

        return {
            "id": pedido.id,
            "apresentante_id": pedido.apresentante_id or "",
            "numero_pedido": pedido.numero_pedido or "",
            "data_pedido": pedido.data_entrada or "",
            "nome_solicitante": pedido.apresentante.nome if pedido.apresentante else "",
            "documento_solicitante": pedido.apresentante.documento
            if pedido.apresentante
            else "",
            "documento_solicitante_qualificado": pedido.apresentante.documento_qualificado
            if pedido.apresentante
            else "",
            "telefone_solicitante": pedido.apresentante.telefone
            if pedido.apresentante
            else "",
            "telefone_solicitante_2": pedido.apresentante.telefone_2
            if pedido.apresentante
            else "",
        }

    @classmethod
    def get_status_ids_por_protocolos_ids(
        cls,
        protocolos_ids: list,
        status_id,
    ) -> list:
        logger.debug(
            f"Obtendo protocolos por status {status_id} para os protocolos: {protocolos_ids}",
        )
        return cls.objects.filter(
            id__in=protocolos_ids,
            status_id__in=status_id,
        ).values_list("id", flat=True)

    @classmethod
    def get_por_numero(cls, numero_protocolo: int) -> "Livro01Protocolo":
        """Retorna o protocolo com o número informado."""
        logger.debug(f"Obtendo protocolo por número: {numero_protocolo}")
        if not numero_protocolo:
            logger.warning("ERRO: Número do protocolo não informado.")
            return cls.objects.none()
        return (
            cls.objects.filtrar_por_numero(numero_protocolo).first()
            or cls.objects.none()
        )

    @classmethod
    @transaction.atomic
    def atualizar_distribuicao_protocolos(cls) -> None:
        """Atualiza a data de distribuição dos protocolos que estão em reentrada."""
        logger.debug("Atualizando a data de distribuição dos protocolos em reentrada.")

        # Filtrar os protocolos em reentrada e com data de andamento a partir de hoje
        protocolos = cls.objects.filter(
            andamentos_do_protocolo__tipo_andamento__grupo_reentrada="S",
            andamentos_do_protocolo__data__gte=timezone.now().date(),
        ).distinct()

        # Atualizar a data de distribuição em uma única operação
        protocolos.update(data_distribuicao=timezone.now().date())

        logger.info(
            f"{protocolos.count()} protocolos atualizados com a nova data de distribuição.",
        )

    @classmethod
    def reset_sequence(cls) -> None:
        """Reseta a sequência do ID do protocolo."""
        logger.debug("Resetando a sequência do ID do protocolo com base na tabela.")
        ajustar_sequence("home_livro01protocolo", "home_livro01protocolo_id_seq")

    @cached_property
    def anexos(self) -> QuerySet["Anexo"]:
        return Anexo.objects.filter(
            object_id=self.pk,
            content_type__model="livro01protocolo",
        )

    @cached_property
    def data_reentrada(self) -> date:
        """Retorna a data da última reentrada do protocolo com base nos andamentos."""
        logger.debug(f"Obtendo data de reentrada do protocolo {self}")
        return (
            self.andamentos.filter(tipo_andamento__servico="Reentrada")
            .select_related("tipo_andamento")
            .aggregate(Max("data"))["data__max"]
        )

    @cached_property
    def url_selo_digital_mg(self):
        if str(self.selo_codigo_para_consulta.codigo_sequencial_unico) != "":
            url = Configuracao.obter(
                "url_selo_digital_mg",
                "https://selos.tjmg.jus.br/sisnor/eselo/consultaSeloseAtos.jsf?selo={}&codigo={}",
            )

            if url:
                return url.format(
                    self.selo_codigo_para_consulta.codigo_sequencial_unico,
                    self.selo_codigo_para_consulta.codigo_de_seguranca,
                )

        return None

    @cached_property
    def valor_emolumentos(self) -> Decimal:
        return self.pedido.valor_emolumento_sum or 0

    @cached_property
    def valor_tfj(self) -> Decimal:
        return self.pedido.valor_tfj_sum or 0

    @cached_property
    def valor_issqn(self) -> Decimal:
        return self.pedido.valor_issqn_sum or 0

    @cached_property
    def valor_recompe(self) -> Decimal:
        return self.pedido.valor_fundo_estado_sum or 0

    @cached_property
    def colaborador(self) -> "Colaborador":
        return (
            self.ultimo_andamento.colaborador_destino if self.ultimo_andamento else None
        )

    @classmethod
    def create_protocolo(cls, protocolo_fb, pedido) -> "Livro01Protocolo":
        from apps.comum.helpers import ajustar_sequence

        protocolo_id = protocolo_fb["CHAVE_PROTOCOLOS"]

        # PESQUISAR O PROTOCOLO NO BANCO DE DADOS
        livro01_protocolo = cls.objects.filter(pk=protocolo_id)
        if livro01_protocolo.exists():
            protocolo_id = ajustar_sequence(
                "home_livro01protocolo",
                "home_livro01protocolo_id_seq",
            )

        try:
            with transaction.atomic():
                cls.reset_sequence()
                obj = cls.objects.create(
                    pk=protocolo_id,
                    numero_protocolo=protocolo_fb["NROORDEM"],
                    pedido=pedido,
                    data_protocolo=protocolo_fb["DATAPROTOCOLO"],
                    titulo=protocolo_fb["CHAVE_TITULOS"],
                    origem_pedido=protocolo_fb.get("ORIGEM_PEDIDO", 0)
                    if protocolo_fb.get("ORIGEM_PEDIDO")
                    else 0,
                    numero_origem=0,
                    protocolo_onr=protocolo_fb["NUMEROPEDIDOCRI"]
                    if protocolo_fb["NUMEROPEDIDOCRI"]
                    else None,
                )
                logger.info(f"PROTOCOLOS: {protocolo_fb['NROORDEM']} criado.")
                return obj
        except IntegrityError:
            logger.exception(f"Erro ao criar o protocolo {protocolo_fb['NROORDEM']}")
            return None

    @classmethod
    def update_protocolo(
        cls,
        protocolo_fb,
        protocolo: "Livro01Protocolo",
        pedido: "Pedido",
    ) -> "Livro01Protocolo":
        with transaction.atomic():
            protocolo.pedido = pedido
            protocolo.data_protocolo = protocolo_fb["DATAPROTOCOLO"]
            protocolo.titulo = protocolo_fb["CHAVE_TITULOS"]
            protocolo.origem_pedido = protocolo_fb.get("ORIGEM_PEDIDO", 0) or 0
            protocolo.numero_origem = 0
            protocolo.protocolo_onr = protocolo_fb.get("NUMEROPEDIDOCRI")
            protocolo.numero_protocolo = protocolo_fb["NROORDEM"]
            protocolo.save()

            logger.info(f"PROTOCOLOS: {protocolo_fb['NROORDEM']} atualizado.")

            return protocolo

    def criar_andamentos_obtidos_do_fb(
        self,
        andamentos_fb: list,
        db: FbConnection,
    ) -> None:
        existentes_ids = [
            andamento_fb["CHAVE_ANDAMENTOS"] for andamento_fb in andamentos_fb
        ]
        existentes = Livro01Andamento.objects.filter(pk__in=existentes_ids)
        existentes_map = {obj.pk: obj for obj in existentes}

        novos_andamentos = []
        atualizar_andamentos = []

        data_importacao = timezone.now()

        for andamento_fb in andamentos_fb:
            data_naive = andamento_fb["DATA"]
            data_aware = timezone.make_aware(data_naive)
            data_local = timezone.localtime(data_aware)
            defaults = {
                "protocolo_id": self.pk,
                "data": data_local,
                "colaborador_id": andamento_fb.get("CHAVE_FUNCIONARIOS"),
                "tipo_andamento_id": andamento_fb.get("CHAVE_SERVICOS_ANDAMENTOS"),
                "colaborador_destino_id": andamento_fb.get("CHAVE_FUNCIONARIOS_DESTINO")
                or andamento_fb.get("CHAVE_FUNCIONARIOS"),
                "data_importacao": data_importacao,
                "texto": andamento_fb.get("OBSERVACAO", ""),
            }

            if andamento_fb["CHAVE_ANDAMENTOS"] in existentes_map:
                andamento = existentes_map[andamento_fb["CHAVE_ANDAMENTOS"]]
                for key, value in defaults.items():
                    setattr(andamento, key, value)
                atualizar_andamentos.append(andamento)
            else:
                novos_andamentos.append(
                    Livro01Andamento(pk=andamento_fb["CHAVE_ANDAMENTOS"], **defaults),
                )

        with transaction.atomic():
            if novos_andamentos:
                Livro01Andamento.objects.bulk_create(novos_andamentos)
            if atualizar_andamentos:
                Livro01Andamento.objects.bulk_update(
                    atualizar_andamentos,
                    fields=list(defaults.keys()),
                )

        return atualizar_andamentos + novos_andamentos

    def criar_andamento_obtido_no_firebird(
        self,
        andamento_fb: dict,
    ) -> "Livro01Andamento":
        colaborador_destino_id = andamento_fb.get(
            "CHAVE_FUNCIONARIOS_DESTINO",
        ) or andamento_fb.get(
            "CHAVE_FUNCIONARIOS",
        )
        data_naive = andamento_fb["DATA"]
        data_aware = timezone.make_aware(data_naive)
        data_local = timezone.localtime(data_aware)

        try:
            andamento = Livro01Andamento.objects.select_for_update().get(
                pk=andamento_fb["CHAVE_ANDAMENTOS"],
            )
            andamento.protocolo_id = self.pk
            andamento.data = data_local
            andamento.colaborador_id = andamento_fb.get("CHAVE_FUNCIONARIOS")
            andamento.tipo_andamento_id = andamento_fb.get("CHAVE_SERVICOS_ANDAMENTOS")
            andamento.colaborador_destino_id = colaborador_destino_id
            andamento.data_importacao = timezone.now()
            andamento.texto = andamento_fb.get("OBSERVACAO", "(Não Informado)")
            andamento.save()
        except ObjectDoesNotExist:
            andamento = Livro01Andamento.objects.create(
                pk=andamento_fb["CHAVE_ANDAMENTOS"],
                protocolo_id=self.pk,
                data=data_local,
                colaborador_id=andamento_fb.get("CHAVE_FUNCIONARIOS"),
                tipo_andamento_id=andamento_fb.get("CHAVE_SERVICOS_ANDAMENTOS"),
                colaborador_destino_id=colaborador_destino_id,
                data_importacao=timezone.now(),
                texto=andamento_fb.get("OBSERVACAO", "(Não Informado)"),
            )

        return andamento

        # # Filtrar protocolos manualmente para data_reentrada e fases_protocolo_colaborador_atual_id (propriedades calculadas)
        # return [
        #     protocolo
        #     for protocolo in protocolos_nao_finalizados
        #     if protocolo.data_reentrada is not None and protocolo.colaborador.pk == colaborador_id
        # ]

    # @classmethod
    # def get_protocolos_sem_reentrada_por_colaborador(cls, colaborador_id) -> "Livro01Protocolo":
    #     return cls.objects.filter(
    #         colaborador_id=colaborador_id,
    #         data_finalizado__isnull=True,
    #         data_reentrada__isnull=True,
    #     ).order_by("numero_protocolo")

    @classmethod
    def get_protocolos_a_distribuir_no_periodo(
        cls,
        start_date: date,
        end_date: date,
    ) -> "Livro01Protocolo":
        logger.info(
            f"Carregando protocolos a distribuir no período... {start_date} - {end_date} ",
        )
        return cls.objects.filtrar_distribuir_por_periodo(
            start_date=start_date,
            end_date=end_date,
        )

    @classmethod
    def get_protocolos_distribuidos_no_periodo(
        cls,
        start_date: date,
        end_date: date,
    ) -> "Livro01Protocolo":
        logger.info(
            f"Carregando protocolos distribuídos no período... {start_date} - {end_date}",
        )
        return cls.objects.filtrar_distribuidos_por_periodo(
            start_date=start_date,
            end_date=end_date,
        )

    # def get_anexos(self) -> QuerySet:
    #     # Obtem os anexos que contêm o número do protocolo no nome do arquivo ou um formato alternativo do número do protocolo, e não estão ligados ao mesmo object_id
    #     anexos = Anexo.objects.filter(
    #         Q(arquivo__icontains=self.numero_protocolo) | Q(arquivo__icontains=self.numero_protocolo_formatado),
    #     ).exclude(object_id=self.pk)

    #     # Atualiza o object_id dos anexos filtrados para vincular ao objeto atual, um por um, para acionar sinais e validações

    #     for anexo in anexos:
    #         anexo.object_id = self.pk
    #         anexo.save()  # Salva cada anexo individualmente

    #     # Retorna todos os anexos agora vinculados a este objeto
    #     return Anexo.objects.filter(object_id=self.pk)
    #     # Retorna todos os anexos agora vinculados a este objeto

    @cached_property
    def imagens_protocolo(self) -> QuerySet:
        return self.get_arquivos_de_imagens(
            Configuracao.obter("diretorio_ged_protocolos"),
            "protocolos",
        )

    @cached_property
    def imagens_nota_devolucao(self) -> QuerySet:
        return self.get_arquivos_de_imagens(
            Configuracao.obter("diretorio_ged_nota_devolucao"),
            "",
        )

    @cached_property
    def valor_fundo_estado(self) -> Decimal:
        return self.pedido.valor_fundo_estado_sum if self.pedido else Decimal(0)

    @cached_property
    def data(self):
        # Retorna a data de reentrada se existir, caso contrário, retorna a data do protocolo se existir, caso contrário, retorna a data atual
        return (
            self.data_reentrada
            if self.data_reentrada
            else self.data_protocolo
            if self.data_protocolo
            else timezone.now().date()
        )

    @cached_property
    def data_prevista_primeira_exigencia(self) -> date:
        """Retorna a data prevista para a primeira exigência com base na data do protocolo."""
        return helpers.get_data_util_em_x_dias(self.data_protocolo, 10)

    @cached_property
    def fases(self) -> QuerySet:
        return ProtocoloEmFase.objects.get_fases_por_protocolo_id(self.pk)

    @cached_property
    def quantidade_titulo_principal(self):
        return len(self.titulos_principais)

    @cached_property
    def data_protocolo_formatada(self) -> None:
        return self.data_protocolo.strftime(settings.DATE_FORMAT_STR)

    @cached_property
    def numero_protocolo_formatado(self) -> str:
        return f"{self.protocolo_formatado}"

    @cached_property
    def content_type(self) -> ContentType:
        return self.get_content_type()

    @cached_property
    def content_type_id(self) -> int:
        return self.get_content_type().id

    def get_content_type(self) -> ContentType:
        return ContentType.objects.get_for_model(self.__class__)

    @classmethod
    def get_list_url(cls) -> str:
        return reverse("home:protocolo_list")

    def get_protocolo_formatado(self) -> str:
        return f"{self.protocolo_formatado}"

    @cached_property
    def data_ultimo_andamento(self) -> date:
        return self.ultimo_andamento.data if self.ultimo_andamento else None

    @cached_property
    def colaborador_destino(self) -> Colaborador:
        return (
            self.ultimo_andamento.colaborador_destino if self.ultimo_andamento else None
        )

    @cached_property
    def ultimo_servico(self):
        return (
            self.ultimo_andamento.tipo_andamento.servico
            if self.ultimo_andamento
            else None
        )

    @cached_property
    def numero_formatado(self) -> str:
        return f"{self.protocolo_formatado}"

    @cached_property
    def numero(self) -> str:
        return f"{self.numero_protocolo}"

    def atos_principais_descritos_agrupados(self):
        pedido_itens = PedidoItem.objects.get_atos_principais_por_pedido(self.pedido)
        # Inicializa um dicionário para contar as ocorrências de cada título
        atos_contagem = {}
        for item in pedido_itens:
            # Converte cada título para string, pois pode ser um objeto
            ato_str = str(item.ato_principal)
            if ato_str in atos_contagem:
                atos_contagem[ato_str] += 1
            else:
                atos_contagem[ato_str] = 1

        # Formata a string para incluir a contagem ao lado de cada ato único
        return ", ".join(
            f"{ato} ({contagem})" for ato, contagem in atos_contagem.items()
        )

    @cached_property
    def titulos_principais(self):
        return PedidoItem.objects.get_titulos_principais_por_pedido(self.pedido)

    @cached_property
    def exibir_prazo(self) -> bool:
        # Verifica se o protocolo está em um status que permite exibir o prazo.
        # Retornando True se o protocolo estiver em um status que permita exibir o prazo.
        return self.status_id not in [
            StatusProtocolo.REGISTRADO,
            StatusProtocolo.CANCELADO,
        ]

    @cached_property
    def livro_02(self):
        return self.pedido.registros

    @cached_property
    def livro_03(self):
        livro_03_do_protocolo = []
        cedula = ""
        for item_l3 in self.pedido.itens_de_livro03:
            registros_auxiliares = Livro03.objects.filter(
                numero=item_l3.numero_registro,
                cartorio=item_l3.numero_ri,
            )

            for registro_auxiliar in registros_auxiliares:
                data_abertura = (
                    registro_auxiliar.data_abertura.strftime(settings.DATE_FORMAT_STR)
                    if registro_auxiliar.data_abertura
                    else None
                )
                cancelado_em = (
                    registro_auxiliar.cancelado_em.strftime(
                        settings.DATE_FORMAT_STR,
                    )
                    if registro_auxiliar.cancelado_em
                    else None
                )
                data_vencimento = (
                    registro_auxiliar.data_vencimento.strftime(settings.DATE_FORMAT_STR)
                    if registro_auxiliar.data_vencimento
                    else None
                )

                try:
                    cedula = (
                        f"{item_l3.tipo_registro_auxiliar.nome} - "
                        f"{item_l3.numero_cedula} - "
                        f"\nAbertura: {data_abertura} - "
                        f"\nVencimento: {cancelado_em} - "
                        f"\nProduto: {registro_auxiliar.descricao} - "
                        f"\nBaixa da Cédula: {data_vencimento}"
                    )
                except AttributeError:
                    cedula = " -  - \nAbertura:  - \nVencimento:  - \nProduto:  - \nBaixa da Cédula: "

                # Atualizando o livro 3
                livro_03_do_protocolo = (
                    [
                        item_l3.codigo_tabela,
                        item_l3.tipo_registro,
                        item_l3.numero_registro,
                        item_l3.numero_ri,
                        item_l3.numero_ato,
                        cedula,
                        [],
                        [],
                        [],
                        [],
                        item_l3.pk,
                        item_l3.ato.tipo_ato,
                        (
                            registro_auxiliar.tipo_registro_auxiliar.nome
                            if registro_auxiliar.tipo_registro_auxiliar
                            else ""
                        ),
                        (
                            registro_auxiliar.numero_cedula
                            if registro_auxiliar.numero_cedula
                            else ""
                        ),
                        data_abertura,
                        cancelado_em,
                        (
                            registro_auxiliar.descricao
                            if registro_auxiliar.descricao
                            else ""
                        ),
                        data_vencimento,
                    ],
                )

        return livro_03_do_protocolo

    @cached_property
    def titulos_principais_descricao(self):
        pedido_itens = self.titulos_principais

        titulos_contagem = {}
        for item in pedido_itens:
            # Converte cada título para string, pois pode ser um objeto
            titulo_str = str(item.titulo_principal)
            if titulo_str in titulos_contagem:
                titulos_contagem[titulo_str] += 1
            else:
                titulos_contagem[titulo_str] = 1

        # Formata a string para incluir a contagem ao lado de cada título único
        return ", ".join(
            f"{titulo} ({contagem})" for titulo, contagem in titulos_contagem.items()
        )

    def get_partes_url(self):
        return reverse("home:protocolo_detail", args=[self.pk]) + "#itens_pedido_partes"

    @cached_property
    def descricao(self) -> str:
        return f"Protocolo nº {self.numero_protocolo}"

    @cached_property
    def pessoas_versoes(self):
        # Obter o ContentType do Protocolo
        protocolo_content_type = ContentType.objects.get_for_model(self.__class__)

        # Filtrar os Vínculos pelo Protocolo atual
        Vinculo = apps.get_model("pessoas", "Vinculo")

        vinculos = Vinculo.objects.filter(
            content_type=protocolo_content_type,
            object_id=self.id,
        )

        # Supondo que o modelo Vinculo tenha uma referência direta a Pessoa (via ForeignKey, por exemplo)
        versoes_pessoas_ids = vinculos.values_list(
            "versao_pessoa__id",
            flat=True,
        ).distinct()

        VersaoPessoa = apps.get_model("pessoas", "VersaoPessoa")
        # Obter as versões das Livro05 associadas aos Vínculos
        return VersaoPessoa.objects.filter(pk=versoes_pessoas_ids)

    @cached_property
    def colaborador_ultimo_andamento(self):
        return self.colaborador

    @cached_property
    def ultimo_andamento_formatado(self) -> str | None:
        andamento = self.ultimo_andamento
        if andamento:
            # Assumindo que o fuso horário do usuário está definido
            timezone.activate(timezone.get_current_timezone())

            # Verifique se andamento.data existe antes de tentar ajustar a timezone
            if andamento.data:
                data_ajustada = andamento.data.astimezone(
                    timezone.get_current_timezone(),
                )
                return f"{andamento.colaborador} - {andamento.tipo_andamento} em {data_ajustada.strftime(settings.DATE_FORMAT_STR)}"
            else:
                # Defina data_ajustada como None ou como um valor padrão apropriado
                return (
                    None  # Ou qualquer valor padrão que faça sentido para sua aplicação
                )
            # data_ajustada = andamento.data.astimezone(timezone.get_current_timezone())
            # return f"{andamento.tipo_andamento} em {data_ajustada.strftime(settings.DATE_FORMAT_STR)}"
        return "Não há andamentos"

    @cached_property
    def ultimo_andamento(self) -> "Livro01Andamento":
        return (
            self.andamentos_do_protocolo.order_by("data").last()
            or Livro01Andamento.objects.none()
        )
        # logger.info(f"Obtendo último andamento do protocolo {self}: {andamento}")

    @cached_property
    def get_maior_data_andamento(self):
        resultado = Livro01Andamento.objects.filter(protocolo=self).aggregate(
            data_maxima=Max("data"),
        )
        data_maxima = resultado["data_maxima"]

        if data_maxima:
            # Agora, encontre o(s) objeto(s) com essa data máxima
            andamentos_com_data_maxima = Livro01Andamento.objects.filter(
                protocolo=self,
                data=data_maxima,
            )

            # Ativa o fuso horário do usuário
            timezone.activate(timezone.get_current_timezone())

            # Ajusta data_maxima para o fuso horário atual
            return (
                data_maxima.astimezone(timezone.get_current_timezone()),
                andamentos_com_data_maxima,
            )
        else:
            # Retorna None ou um valor padrão, caso não haja data_maxima
            return self.data_protocolo, None

    @cached_property
    def quantidade_andamentos(self):
        return Livro01Andamento.objects.filter(protocolo=self).count()

    @cached_property
    def pessoas_com_indisponibilidade(self):
        # Obtemos os IDs das pessoas relacionadas a este pedido
        ids_pessoas = PedidoParte.objects.filter(pedido=self.pedido).values_list(
            "pessoa_id",
            flat=True,
        )

        # Obtemos os CPFs de Livro05 que estão no LriDocumento
        cpfs_indisponiveis = LriDocumento.objects.filter(
            cpf_cnpj__in=Subquery(
                Livro05.objects.filter(id__in=ids_pessoas).values("cpf"),
            ),
        ).values_list("cpf_cnpj", flat=True)

        # Filtramos Livro05 pelos CPFs obtidos
        return Livro05.objects.filter(cpf__in=cpfs_indisponiveis)

    @cached_property
    def status_protocolo_descricao(self) -> str:
        andamentos_agrupados = Livro01Andamento.objects.agrupar_por_status([self.pk])

        concluidos = andamentos_agrupados["registrado"]
        cancelados = andamentos_agrupados["cancelado"]
        exigencia = andamentos_agrupados["exigencia"]
        subjudice = andamentos_agrupados["subjudice"]
        exigencia_positiva = andamentos_agrupados["exigencia_positiva"]
        em_registro = andamentos_agrupados["em_registro"]
        reentrada = andamentos_agrupados["reentrada"]

        if concluidos:
            return StatusProtocolo.REGISTRADO
        elif cancelados:
            return StatusProtocolo.CANCELADO
        elif subjudice:
            return StatusProtocolo.SUBJUDICE
        else:
            # Define conjuntos aqui para reutilização e performance
            cancelados_concluidos = set(cancelados).union(concluidos).union(subjudice)
            exigencia_diferenca = set(exigencia) - cancelados_concluidos

            if reentrada:
                return StatusProtocolo.REENTRADA

            if exigencia_diferenca:
                if em_registro:
                    return StatusProtocolo.EM_REGISTRO
                else:
                    return StatusProtocolo.EXIGENCIA
            elif exigencia_positiva:
                return StatusProtocolo.EM_ANALISE
            elif em_registro:
                return StatusProtocolo.EM_REGISTRO
            else:
                return StatusProtocolo.EM_ANDAMENTO

    @cached_property
    def seguinte(self):
        return (
            self.__class__.objects.filter(numero_protocolo__gt=self.numero_protocolo)
            .order_by("numero_protocolo")
            .first()
        )

    @cached_property
    def anterior(self):
        return (
            self.__class__.objects.filter(numero_protocolo__lt=self.numero_protocolo)
            .order_by("-numero_protocolo")
            .first()
        )

    @cached_property
    def primeiro(self):
        return (
            self.__class__.objects.filter(numero_protocolo__isnull=False)
            .exclude(numero_protocolo=0)
            .order_by("numero_protocolo")
            .first()
        )

    @cached_property
    def ultimo(self):
        return (
            self.__class__.objects.filter(numero_protocolo__isnull=False)
            .exclude(numero_protocolo=0)
            .order_by("-numero_protocolo")
            .first()
        )

    @cached_property
    def andamentos(self):
        return Livro01Andamento.objects.filtrar_por_protocolo(self)

    @cached_property
    def visualizar_selos_sqlserver(self):
        from apps.home.services import sqlserver

        """ ALFENAS ADICIONAR CAMPOS PARA O SQLSERVER """

        with sqlserver.SqlServerConnection() as db:
            db.get_selo_por_protocolo(self.numero_protocolo)

    @cached_property
    def selos(self):
        # ALFENAS ADICIONAR CAMPOS PARA O SQLSERVER
        from apps.cartorios.models import Cartorio

        usar_selo_sql_server = Cartorio.objects.all().values_list(
            "usar_selo_sql_server",
            flat=True,
        )[0]
        if usar_selo_sql_server == "S":
            self.visualizar_selos_sqlserver

        return SeloEletronico.objects.filtrar_por_protocolo(self)

    @cached_property
    def selos_pedidos_itens(self):
        selos = self.selos

        # Cria uma lista de PedidoItem diretamente dos objetos SeloEletronico, sem a necessidade de uma segunda consulta
        return [selos.pedido_item for selo in selos]

    @cached_property
    def selos_pedidos_itens_valores(self):
        # Utiliza Prefetch para otimizar a recuperação dos itens de pedido relacionados aos selos
        selo_item = self.selos.values_list("pedido_item", flat=True)

        # Filtrar os itens de pedido relacionados aos selos
        pedido_item_valores = PedidoItem.objects.filter(id__in=selo_item)

        # Calcula a soma dos valores diretamente no banco de dados
        resultado = pedido_item_valores.aggregate(
            valor_selado_total=Sum(
                F("valor_emolumento")
                + F("valor_tfj")
                + F("valor_fundo_estado")
                + F("valor_issqn"),
            ),
        )

        """
            <p>Emolumento: {{ item.valor_emolumento|formatar_moeda }}</p>
            <p>TFJ: {{ item.valor_tfj|formatar_moeda }}</p>
            <p>ISSQN: {{ item.valor_issqn|formatar_moeda }}</p>
            <p>Recomep: {{ item.valor_fundo_estado|formatar_moeda }}</p>
            <p>Vigor: {{ item.vigencia_id.descricao_periodo }}</p>
        """

        return resultado.get("valor_selado_total", 0)

    @cached_property
    def pedidos_itens(self):
        return PedidoItem.objects.filter(pedido=self.pedido)

    @cached_property
    def itens(self):
        return self.pedido.itens.all()
        # return PedidoItem.objects.filter(pedido=self.pedido)

    @cached_property
    def quantidade_itens_pedido(self):
        from apps.pedidos.models import Pedido as PedidoPrime

        pedido = PedidoPrime.objects.filter(
            numero_protocolo_firebird=self.numero_protocolo,
        ).first()
        if pedido:
            return pedido.atos.count
        else:
            return 0

    @cached_property
    def valor_prenotacao_mg(self):
        from apps.pedidos.models import Emolumento, TipoEmolumento

        # Filtrando os itens onde codigo_tabela é '4701-9' e obtendo o maior 'numero'
        # pedido_item_valores = PedidoItem.objects.filter(pk=maior_numero_pedido)
        tipo_emolumento = TipoEmolumento.objects.filter(
            codigo=firebird.get_cod_prenotacao(),
            ativo=True,
        ).first()
        pedido_item_valores = Emolumento.objects.filter(
            tipo_emolumento_id=tipo_emolumento,
        ).first()

        return (
            pedido_item_valores.valor
            + pedido_item_valores.taxa_fiscal_judiciaria
            + pedido_item_valores.fundo1_valor
            + ((pedido_item_valores.issqn_percentual / 100) * pedido_item_valores.valor)
        )

        # RETORNAR OS VALORES DOS SELOS - ITENS SELADOS

    @cached_property
    def nome_apresentante(self):
        return self.pedido.nome_solicitante_formatado

    @cached_property
    def nome_adquirente_balcao(self):
        from apps.pedidos.models import Pedido as PedidoPrime

        resultados = PedidoPrime.objects.filter(
            numero_protocolo_firebird=self.numero_protocolo,
        ).values(
            "apresentante__nome_adquirente_parte",
        )

        for resultado in resultados:
            return resultado["apresentante__nome_adquirente_parte"]
        return None

    @cached_property
    def protocolo_formatado(self) -> str:
        """Retorna o número do protocolo formatado."""
        try:
            numero = int(str(self.numero_protocolo).split(".")[0])
        except ValueError:
            numero = 0

        return f"{numero // 1000:03d}.{numero % 1000:03d}"

    @cached_property
    def user_id_atual_protocolo(self) -> str:
        # Supondo que colaborador seja um campo de relacionamento ForeignKey
        # para um modelo que representa colaboradores e 'id' é o campo desejado.
        return self.colaborador.pk if self.colaborador else ""

    @cached_property
    def partes_protocolo(self):
        from apps.pedidos.models import Ato as AtoPrime
        from apps.pedidos.models import Participacao as ParticipacaoPrime
        from apps.pedidos.models import Pedido as PedidoPrime

        try:
            pedido = PedidoPrime.objects.filter(
                numero_protocolo_firebird=self.numero_protocolo,
            ).first()

            # Obtém todos os atos relacionados ao pedido
            atos = AtoPrime.objects.filter(pedido=pedido)

            # Obtém todas as participações relacionadas a esses atos
            return ParticipacaoPrime.objects.filter(ato__in=atos)

        except Exception:
            partes = []

        return partes

    @cached_property
    def quantidade_partes_protocolo(self):
        from apps.pedidos.models import Pedido as PedidoPrime

        pedido = PedidoPrime.objects.filter(
            numero_protocolo_firebird=self.numero_protocolo,
        ).first()

        if pedido:
            return pedido.partes.count
        else:
            return 0

    def get_ultimo_registro_financeiro(self: "Livro01Protocolo"):
        """Retorna o último registro financeiro do protocolo."""
        return (
            Financeiro.objects.filter(pedido=self.pedido_id)
            .order_by("-data_transacao")
            .first()
        )

    @cached_property
    def partes(self: "Livro01Protocolo") -> dict:
        """Retorna as partes do protocolo agrupadas por tipo de parte."""
        try:
            partes = PedidoParteAto.objects.filter(
                pedido_item_id=self.pedido_item_id,
            ).order_by("tipo_parte", "id")
        except Exception:
            partes = []

        return partes

        # return {
        #     "A": [parte for parte in partes if parte.tipo_parte == "A"],
        #     "T": [parte for parte in partes if parte.tipo_parte == "T"],
        #     "D": [parte for parte in partes if parte.tipo_parte == "D"],
        #     "C": [parte for parte in partes if parte.tipo_parte == "C"],
        #     "R": [parte for parte in partes if parte.tipo_parte == "R"],
        #     "S": [parte for parte in partes if parte.tipo_parte == "S"],
        # }

    @cached_property
    def partes_adquirentes(self: "Livro01Protocolo"):
        """Retorna os adquirentes do protocolo."""
        adquirentes = (
            self.partes_do_protocolo()
            # .filter(papel="A")
            .filter(papel=1)
            # .annotate(nome=F("pessoa__nome"))
            .annotate(nome=F("parte__nome"))
            .values_list("nome", flat=True)
        )
        return ", ".join(adquirentes)

    @cached_property
    def partes_transmitentes(self: "Livro01Protocolo"):
        transmitentes = (
            self.partes_do_protocolo()
            # .filter(papel="T")
            .filter(papel=2)
            # .annotate(nome=F("pessoa__nome"))
            .annotate(nome=F("parte__nome"))
            .values_list("nome", flat=True)
        )
        return ", ".join(transmitentes)

    def partes_do_protocolo(self: "Livro01Protocolo"):
        return self.partes_protocolo

    def partes_envolvidas(self: "Livro01Protocolo"):
        return self.partes

    def adquirentes(self: "Livro01Protocolo"):
        return self.partes["A"]

    def transmitentes(self: "Livro01Protocolo"):
        return self.partes["T"]

    def devedores(self: "Livro01Protocolo"):
        return self.partes["D"]

    def credores(self: "Livro01Protocolo"):
        return self.partes["C"]

    def apresentante(self: "Livro01Protocolo"):
        return self.partes  # Apresentante/Solicitante

    def requerente(self: "Livro01Protocolo"):
        return self.partes["S"]  # Apresentante/Solicitante

    def executar_reentrada(
        self,
        opcao_reentrada: str,
        colaborador_id: int,
        colaborador_encaminhado_id: int,
        valor_diferenca=0,
    ) -> "Financeiro":
        # BUSCAR O ANDAMENTO DE REENTRADA
        if opcao_reentrada == "R":
            tipo_andamento_id = TipoAndamento.reentrada().id

        elif opcao_reentrada == "P":
            tipo_andamento_id = TipoAndamento.reentrada_pagamento().id

        # GRAVAR CAIXA - FIREBIRD
        with transaction.atomic(), firebird.FbConnection() as db:
            db.begin_transaction()
            financeiro: Financeiro = None
            try:
                if valor_diferenca > 0 and opcao_reentrada == "P":
                    firebird.gravar_caixa_do_protocolo_no_firebird(
                        pedido_id=self.pedido_id,
                        valor=valor_diferenca,
                        funcionarios_id=colaborador_id,
                        descricao=str(
                            f"""
                            'Diferença - {str(self.pedido.nome_solicitante_formatado).upper()}'
                            """,
                        ),
                        db=db,
                    )

                    # ATUALIZAR VALOR ACERTO - FIREBIRD
                    firebird.atualizar_valor_acerto_no_fb(
                        pedido_id=self.pedido_id,
                        db=db,
                    )

                    firebird.criar_andamento_fb(
                        pedido_id=self.pedido_id,
                        colaborador_id=colaborador_id,
                        tipo_andamento_id=tipo_andamento_id,
                        colaborador_encaminhado_id=colaborador_encaminhado_id,
                        db=db,
                    )

                    # GRAVAR CAIXA
                    financeiro = Financeiro.criar_financeiro(
                        pedido_id=self.pedido_id,
                        valor=valor_diferenca,
                        colaborador_id=colaborador_id,
                        # request.user.id
                        descricao="Diferença de Protocolo",
                    )

                # Verificar se existe o grupo de Andamento para o protocolo - FIREBIRD
                from apps.home.utils.gravar_protocolo import (
                    atualizar_andamento_no_firebird,
                )

                atualizar_andamento_no_firebird(
                    pedido_id=self.pedido_id,
                    protocolo_id=self.pk,
                    colaborador_id=colaborador_id,
                    tipo_andamento_id=tipo_andamento_id,
                    colaborador_encaminhado_id=colaborador_encaminhado_id,
                    db=db,
                )

                # DISTRIBUIR PARA O COLABORADOR - encaminhar_protocolo_ao_colaborador
                self.atualizar_colaborador(colaborador_encaminhado_id, opcao_reentrada)

                # ATUALIZAR DATA REENTRADA PARA O COLABORADOR
                # self.atualizar_data_reentrada_2()

                db.commit()
            except Exception:
                logger.exception("Erro ao executar reentrada")
                db.rollback()

        return financeiro if financeiro else None

    @cached_property
    def data_prevista(self) -> date:
        if self.data_reentrada:
            return helpers.get_data_util_em_x_dias(
                self.data_reentrada,
                self.maximo_dias_titulo_reentrada,
            )
        else:
            return helpers.get_data_util_em_x_dias(
                self.data_protocolo,
                self.maximo_dias_titulo,
            )

    @cached_property
    def prazo_em_dias(self) -> int:
        if self.data_reentrada:
            return self.maximo_dias_titulo_reentrada
        else:
            return self.maximo_dias_titulo

    @cached_property
    def prazo_previsto_em_dias(self) -> int:
        """
        Calcula o prazo previsto em dias.

        Retorna o número de dias entre a data prevista e a data atual.
        Se a data prevista não estiver definida, retorna None.

        Returns
        -------
            int: O número de dias entre a data prevista e a data atual, ou None se a data prevista não estiver definida.

        """
        if self.data_prevista:
            return relativedelta(self.data_prevista - timezone.now().date()).days
        return None

    @cached_property
    def dias_restantes(self):
        return self.prazo_previsto_em_dias

    @cached_property
    def atos(self):
        return AtoPratica.objects.filter(pedido=self.pedido_id)

    @cached_property
    def caixa(self):
        return Financeiro.objects.filter(pedido=self.pedido_id)

    @cached_property
    def valor_total_caixa(self):
        # Método para atualizar as fases do protocolo
        return Financeiro.objects.total_caixa(self.pedido_id) or 0

    @cached_property
    def valor_total_protocolo(self):
        return self.pedido.valor_total_pedido

    # BUSCAR VALORES ANTIGOS
    def valores_sistema_antigo(self):
        protocolo = Livro01Protocolo.objects.get(numero_protocolo=self.numero_protocolo)

        with firebird.FbConnection() as db:
            valor_atual_protocolo = protocolo.get_valor_final_sistema_antigo(db) or 0
            valor_total_pago_protocolo = (
                protocolo.get_valor_acerto_sistema_antigo(db) or 0
            )
            valor_transacao = valor_atual_protocolo - valor_total_pago_protocolo
            valor_transacao = Decimal(valor_transacao)

        return valor_atual_protocolo, valor_total_pago_protocolo, valor_transacao

    # BUSCAR VALORES ANTIGOS
    def valor_atual_protocolo_sistema_antigo(self):
        valor_atual_protocolo, _, _ = self.valores_sistema_antigo()
        return valor_atual_protocolo or 0

    # BUSCAR VALORES ANTIGOS
    def valor_pago_protocolo_sistema_antigo(self):
        _, valor_total_pago_protocolo, _ = self.valores_sistema_antigo()
        return valor_total_pago_protocolo or 0

    @cached_property
    def valor_diferenca(self) -> Decimal:
        valor_atual_protocolo, valor_total_pago_protocolo, valor_transacao = (
            self.valores_sistema_antigo()
        )

        return (valor_atual_protocolo - valor_total_pago_protocolo) or 0
        # return (self.valor_total_protocolo - self.valor_total_caixa) or 0

    @cached_property
    def valor_total_pago(self) -> Decimal:
        return (self.valor_total_protocolo or 0 - self.valor_diferenca or 0) or 0

    @cached_property
    def data_do_ultimo_pagamento(self) -> date:
        financeiro = self.financeiro.last()
        return financeiro.data_transacao if financeiro else None

    # RECUPERAR O ANDAMENTO DE RECEBIDO
    def atualizar_recebido(self, andamento) -> None:
        # andamento.protocolo.colaborador_que_recebeu_protocolo = andamento.colaborador
        # andamento.protocolo.data_confirmacao_recebimento = andamento.data

        # andamento.save()
        pass

    def apagar_eventos(self):
        """Apaga todos os eventos relacionados ao protocolo."""
        logger.info(f"PROTOCOLO {self}: Apagando Eventos do Protocolo")
        Event.objects.apagar_eventos_pelo_numero(numero=self.numero_protocolo)

    def atualizar_fases(self) -> None:
        """Método para atualizar as fases do protocolo."""
        logger.info(f"PROTOCOLO {self}: Atualizando Fases do Protocolo")
        self.atualizar_maximo_dias_titulo()
        self.atualizar_maximo_dias_titulo_reentrada()
        self.atualizar_status_id()
        self.atualizar_fases_protocolo_id()

    # Método para atualizar maximo_dias_titulo
    def atualizar_maximo_dias_titulo(self) -> None:
        logger.info(f"PROTOCOLO {self}: Atualizando Maximo Dias do Título")
        if self.maximo_dias_titulo is None:
            self.maximo_dias_titulo = 20
            self.save()

    # Método para atualizar maximo_dias_titulo_reentrada
    def atualizar_maximo_dias_titulo_reentrada(self) -> None:
        logger.info(f"PROTOCOLO {self}: Atualizando Maximo Dias de Reentrada")
        if self.maximo_dias_titulo_reentrada is None:
            self.maximo_dias_titulo_reentrada = 3
            self.save()

    # Método para atualizar status_id, se necessário
    def atualizar_status_id(self) -> None:
        logger.info(
            f"""PROTOCOLO {self}: Atualizando Status do Protocolo - Em Andamento""",
        )
        if self.status_id is None:
            obj = StatusProtocolo.objects.get_status_em_andamento()
            self.status = obj
            self.save()

    def atualizar_fases_protocolo_id(self: "Livro01Protocolo") -> None:
        logger.info(f"PROTOCOLO {self}: Atualizando Fases do Protocolo - Conferência")
        if self.fases_protocolo_id is None:
            fase_conferencia, created = TipoFaseProtocolo.objects.get_fase_conferencia()
            self.fases_protocolo = fase_conferencia
            self.save()

    @cached_property
    def ultimo_andamento_de_confirmacao(self):
        # Obtém o andamento de confirmação mais recente
        confirmacao = (
            self.andamentos_do_protocolo.filter(
                tipo_andamento__grupo_servico_recebido="S",
            )
            .select_related("tipo_andamento")
            .order_by("data")
            .last()
        )

        if not confirmacao:
            return None

        # Verifica se há reentrada após o andamento de confirmação
        reentrada_posterior = self.andamentos_do_protocolo.filter(
            tipo_andamento__grupo_reentrada="S",
            data__gt=confirmacao.data,
        ).exists()

        return None if reentrada_posterior else confirmacao

    def verificar_reentrada_pos_confirmacao(self):
        andamento_confirmacao = self.ultimo_andamento_de_confirmacao
        if not andamento_confirmacao:
            return False  # Não houve andamento de confirmação de recebimento

        return self.andamentos_do_protocolo.filter(
            tipo_andamento__grupo_reentrada="S",
            data__gt=andamento_confirmacao.data,
        ).exists()

    @cached_property
    def data_confirmacao_recebimento(self):
        andamento = self.ultimo_andamento_de_confirmacao
        return andamento.data if andamento else None

    @cached_property
    def colaborador_que_recebeu_protocolo(self) -> Colaborador:
        andamento = self.ultimo_andamento_de_confirmacao
        return andamento.colaborador if andamento else None

    @cached_property
    def recebido(self) -> bool:
        return self.colaborador_que_recebeu_protocolo is not None

    def atualizar_data_finalizado_atual(self, data, status_id) -> None:
        try:
            self.data_finalizado = data
            status, created = StatusProtocolo.objects.get_or_create(id=status_id)
            if status:
                self.status = status
                self.save()
                logger.info(
                    f"PROTOCOLO {self}: Atualizando Data Finalizado do Protocolo",
                )
        except Exception:
            msg = "ERRO ao atualizar data_finalizado do Protocolo"
            logger.exception(msg)

    def atualizar_status(self, descricao_status) -> None:
        logger.info(
            f"PROTOCOLO {self}: Atualizando Status do Protocolo: {descricao_status}",
        )
        try:
            status, created = StatusProtocolo.objects.get_or_create(
                descricao=descricao_status,
            )
            if status:
                self.status = status
                self.save()
                logger.info(f"PROTOCOLO {self}: Atualizado Status do Protocolo.")
        except Exception:
            msg = "ERRO ao atualizar Status do Protocolo: {descricao_status}"
            logger.exception(msg)

    def atualizar_data_distribuicao(
        self,
        tipo_andamento_id,
        colaborador_encaminhado_id,
    ) -> None:
        """
        Atualiza a 'data_reentrada' para este protocolo, com base na data mais recente
        de um andamento relacionado que corresponda ao 'tipo_andamento_id'.
        """
        # Obtem a data mais recente do andamento específico para este protocolo
        data_maxima = Livro01Andamento.objects.filter(
            protocolo=self,  # Usa a instância atual para filtrar
            tipo_andamento_id=tipo_andamento_id,
        ).aggregate(data_max=Max("data"))["data_max"]

        if data_maxima:
            try:
                # Atualiza 'data_distribuicao' para este protocolo com a data_maxima encontrada
                # self.data_reentrada = data_maxima
                self.data_distribuicao = data_maxima
                self.fases_protocolo_colaborador_id = colaborador_encaminhado_id
                self.save()
                print(
                    f"PROTOCOLO {self}: Atualizado Data Distribuicao para {self.data_distribuicao}",
                )
            except Exception:
                msg = f"ERRO ao atualizar protocolo: {self}"
                logger.exception(msg)

    def atualizar_colaborador_atual(self, andamento) -> None:
        if not andamento:
            return

        logger.info(
            f"PROTOCOLO {self}: Atualizando Colaborador Atual: {self.colaborador}",
        )

        data_andamento = andamento.data or timezone.now()

        try:
            self.fases_protocolo_colaborador_atual_id = (
                andamento.colaborador_destino_id or andamento.colaborador_id
            )
            self.fases_protocolo_colaborador_atual_data = data_andamento
            self.save()
            print(
                f"PROTOCOLO {self}: Colaborador Atual do Protocolo Atualizado para {self.colaborador} - {self.fases_protocolo_colaborador_atual_data}",
            )
        except Exception:
            msg = f"ERRO ao atualizar_colaborador_atual no protocolo: {self}"
            logger.exception(msg)

    # ATUALIZAR O STATUS PELO ANDAMENTO
    def atualizar_status_pelo_andamento(self, andamento_id: int) -> None:
        if not andamento_id:
            return

        andamento = Livro01Andamento.objects.filter(pk=andamento_id).first()
        if not andamento:
            return

        tipo_andamento_id = (
            andamento.tipo_andamento.pk if andamento.tipo_andamento else None
        )
        colaborador_encaminhado_id = (
            andamento.colaborador_destino.pk if andamento.colaborador_destino else None
        )

        if not tipo_andamento_id:
            return

        if not colaborador_encaminhado_id:
            colaborador_encaminhado_id = (
                andamento.colaborador.pk if andamento.colaborador else None
            )

        with transaction.atomic():
            # 3 = REGISTRADO
            if TipoAndamento.objects.eh_registrados(tipo_andamento_id):
                logger.info(f"PROTOCOLO {self}: Atualizando pelo status REGISTRADO")
                self.atualizar_data_finalizado_atual(data=andamento.data, status_id=3)
                self.atualizar_colaborador_atual(andamento)

            # 7 = DISTRIBUICAO
            elif TipoAndamento.objects.eh_distribuicao(tipo_andamento_id):
                logger.info(f"PROTOCOLO {self}: Atualizando pelo status DISTRIBUICAO")
                self.atualizar_data_distribuicao(
                    tipo_andamento_id,
                    colaborador_encaminhado_id,
                )
                self.atualizar_data_finalizado_atual(data=None, status_id=7)
                self.atualizar_colaborador_atual(andamento)

            # 1 = EXIGENCIA
            elif TipoAndamento.objects.eh_exigencia(tipo_andamento_id):
                logger.info(f"PROTOCOLO {self}: Atualizando status EXIGENCIA")
                self.atualizar_data_finalizado_atual(data=None, status_id=1)
                self.atualizar_colaborador_atual(andamento)

            # 4 SUBJUDICE
            elif TipoAndamento.objects.eh_subjudice(tipo_andamento_id):
                logger.info(f"PROTOCOLO {self}: Atualizando pelo status SUBJUDICE")
                self.atualizar_status("SubJudice")
                self.atualizar_data_finalizado_atual(data=None, status_id=4)
                self.atualizar_colaborador_atual(andamento)

            # 0 - REENTRADA
            elif TipoAndamento.objects.eh_reentrada(tipo_andamento_id):
                logger.info(f"PROTOCOLO {self}: Atualizando pelo status REENTRADA")

                # self.atualizar_data_reentrada(tipo_andamento_id, colaborador_encaminhado_id)
                self.atualizar_status("Em Andamento")
                self.atualizar_data_finalizado_atual(data=None, status_id=0)
                self.atualizar_colaborador_atual(andamento)

            # 2 - CANCELADOS
            elif TipoAndamento.objects.eh_cancelados(tipo_andamento_id):
                logger.info(f"PROTOCOLO {self}: Atualizando pelo status CANCELADO")
                self.atualizar_data_finalizado_atual(data=andamento.data, status_id=2)
                self.atualizar_colaborador_atual(andamento)

            # 1 EXIGENCIA POSITIVA
            elif TipoAndamento.objects.eh_exigencia_positiva(tipo_andamento_id):
                logger.info(
                    f"PROTOCOLO {self}: Atualizando pelo status EXIGENCIA POSITIVA",
                )
                self.atualizar_data_finalizado_atual(data=andamento.data, status_id=1)
                self.atualizar_colaborador_atual(andamento)

            # 5 = EM REGISTRO
            elif (
                tipo_andamento_id
                in TipoAndamento.objects.filtrar_por_tipo_em_registro()
            ):
                logger.info(f"PROTOCOLO {self}: Atualizando pelo status EM REGISTRO")
                self.atualizar_status(StatusProtocolo.EM_REGISTRO)
                self.atualizar_data_finalizado_atual(data=None, status_id=5)
                self.atualizar_colaborador_atual(andamento)

            # STATUS 6 = PRONTO REGISTRAR
            elif TipoAndamento.objects.eh_pronto_registrar(tipo_andamento_id):
                print(
                    f"PROTOCOLO {self}: Atualizando pelo status PRONTO PARA REGISTRAR",
                )
                # ATUALIZANDO OS DADOS NO PROTOCOLO
                self.atualizar_data_finalizado_atual(data=None, status_id=6)
                self.atualizar_colaborador_atual(andamento)

            # PRONTO RECEBIDO
            elif TipoAndamento.objects.eh_recebido(tipo_andamento_id):
                logger.info(f"PROTOCOLO {self}:Atualizando pelo status RECEBIDO")
                # ATUALIZANDO OS DADOS NO PROTOCOLO
                self.atualizar_recebido(andamento)

            if TipoAndamento.objects.eh_atualizar_status_protocolo(tipo_andamento_id):
                logger.info(f"PROTOCOLO {self}: Atualizando Status do Protocolo")
                self.atualizar_fases()
                self.atualizar_colaborador_atual(andamento)

    # OBTER OS DADOS DO TITULO LANCADOS NO PROTOCOLO
    @cached_property
    def observacao_pedido(self):
        return self.pedido.observacao

    # FORMATAR A DATA PREVISTA
    @cached_property
    def data_prevista_formatada(self):
        return self.data_prevista.strftime(settings.DATE_FORMAT_STR)

    @cached_property
    def data_reentrada_formatada(self):
        if self.data_reentrada:
            resultado_data_reentrada = helpers.get_data_util_em_x_dias(
                self.data_reentrada,
                self.maximo_dias_titulo_reentrada,
            )
        else:
            return ""

        return resultado_data_reentrada.strftime(settings.DATE_FORMAT_STR)

    @cached_property
    def maximo_dias_qualificar_titulo(self):
        data_hora, max_dias = self.pedido.get_prazo_em_dias("N")
        return max_dias

    @cached_property
    def primeira_data_exigencia(self) -> date:
        data_hora, max_dias = self.pedido.get_prazo_em_dias("N")
        return helpers.get_data_util_em_x_dias(data_hora, max_dias)

    # FORMATAR A DATA PREVISTA
    @cached_property
    def data_entrada_protocolo_formatada(self) -> str:
        return self.data_protocolo.strftime(settings.DATE_FORMAT_STR)

    def atualizar_colaborador(self, colaborador_id: int, opcao="") -> None:
        logger.info(f"PROTOCOLO {self}: Atualizando Colaborador")
        data_atual = timezone.now()  # Chamada única para a função now
        self.fases_protocolo_colaborador_id = colaborador_id
        self.fases_protocolo_colaborador_atual_id = colaborador_id
        self.data_distribuicao = data_atual

        # REENTRADA OU PAGAMENTO DO PROTOCOLO
        if opcao in ["R", "P"]:
            self.data_distribuicao = data_atual
            self.data_reentrada = data_atual

        self.save()

    def criar_andamento(
        self,
        colaborador_id,
        tipo_andamento_id,
        colaborador_encaminhado_id,
    ) -> "Livro01Andamento":
        data_atual = timezone.now()  # Chamada única para a função now

        with transaction.atomic():  # Assegura que as operações são atômicas
            Livro01Andamento.reset_sequence()

            andamento, created = Livro01Andamento.objects.update_or_create(
                protocolo=self,
                tipo_andamento_id=tipo_andamento_id,
                colaborador_id=colaborador_id,
                defaults={
                    "colaborador_destino_id": colaborador_encaminhado_id,
                    "data": data_atual,
                },
            )
            andamento.atualizar_colaborador(colaborador_id)

        return andamento

    @classmethod
    def criar_protocolo(
        cls,
        pedido_id,
        titulo_id,
        observaco,
        protocolo_sistema,
    ) -> "Livro01Protocolo":
        with transaction.atomic():
            cls.proximo_numero_protocolo()

            return cls.objects.create(
                numero_protocolo=cls.proximo_numero_protocolo(),
                titulo=titulo_id,
                pedido_id=pedido_id,
                data_protocolo=timezone.now(),
                observacao=str(observaco),
                numero_origem=protocolo_sistema,
                origem_pedido=6,
            )

    @classmethod
    def proximo_numero_protocolo(cls) -> int:
        logger.info("Obtendo o próximo número de protocolo")
        return get_next_value("numero_livro01_id_seq")

    def get_arquivos_de_imagens(self, diretorio, pasta) -> list:
        logger.info(
            f"Obtendo arquivos de imagens em {diretorio} para o protocolo {self.numero_protocolo}",
        )
        """Lista todos os arquivos PDF em uma pasta específica associada a um número de protocolo."""
        caminho_pasta = Path(diretorio) / str(pasta) / str(self.numero_protocolo)
        try:
            # Verifique se o caminho existe antes de prosseguir
            logger.info(f"Verificando o caminho da pasta: {caminho_pasta}")
            if not caminho_pasta.exists() or not caminho_pasta.is_dir():
                logger.warning(
                    f"Caminho não encontrado ou não é uma pasta: {caminho_pasta}",
                )
                return []
        except Exception:
            logging.exception(f"Erro ao acessar o caminho da pasta: {caminho_pasta}")
            return []

        # Listando arquivos PDF
        arquivos_pdf = [arquivo.name for arquivo in caminho_pasta.glob("*.pdf")]

        logger.info(f"Quantidade de imagens encontradas: {len(arquivos_pdf)}")

        return arquivos_pdf

    def encaminhar_ao_colaborador(
        self,
        colaborador_id,
        colaborador_encaminhado_id,
        titulo_id,
        fase_id,
        db: "FbConnection",
    ) -> None:
        descricao_servico_distribuido = Configuracao.obter(
            "DESCRICAO_SERVICO_DISTRIBUIDO",
        )
        tipo_andamento = TipoAndamento.objects.get(
            servico=descricao_servico_distribuido,
        )

        # if colaborador_encaminhado and fase:
        if colaborador_encaminhado_id:
            self.fases_protocolo_id = fase_id
            self.fases_protocolo_colaborador_id = colaborador_encaminhado_id
            self.fases_protocolo_colaborador_atual_id = colaborador_encaminhado_id
            self.data_distribuicao = timezone.now()
            self.save()
        else:
            msg = "Colaborador ou setor não encontrado."
            raise ValueError(msg)

        try:
            self.criar_andamento(
                colaborador_id,
                tipo_andamento.pk,
                colaborador_encaminhado_id,
            )
        except Exception:
            logger.exception("Erro ao criar andamento")

        if str(titulo_id) is not None:
            pass

        evento_titulo = (
            Configuracao.obter("DESCRICAO_SERVICO_DISTRIBUIDO")
            + " "
            + str(self.numero_protocolo)
        )

        descricao = "Distribuído o Protocolo" + str(self.numero_protocolo)
        data_inicio = timezone.now()
        data_fim = data_inicio

        evento = Event.criar_evento_no_calendario(
            user=colaborador_encaminhado_id,
            auth_user=colaborador_encaminhado_id,
            numero=self.numero_protocolo,
            title=evento_titulo,
            description=descricao,
            origem="P",
            horas_adicionais=1,
            data_futura_inicio=data_inicio,
            data_futura_fim=data_fim,
            gravar_apenas_data="S",
        )

        if evento:
            Event.criar_membro_no_evento_do_calendario(
                evento=evento,
                colaborador_id=colaborador_encaminhado_id,
            )

        # Verificar se existe o grupo de Andamento para o protocolo - FIREBIRD
        from apps.home.utils.gravar_protocolo import atualizar_andamento_no_firebird

        atualizar_andamento_no_firebird(
            pedido_id=self.pedido_id,
            protocolo_id=self.pk,
            colaborador_id=colaborador_id,
            tipo_andamento_id=tipo_andamento.pk,
            colaborador_encaminhado_id=colaborador_encaminhado_id,
            db=db,
        )

        firebird.criar_andamento_fb(
            pedido_id=self.pedido_id,
            colaborador_id=colaborador_id,
            tipo_andamento_id=tipo_andamento.pk,
            colaborador_encaminhado_id=colaborador_encaminhado_id,
            db=db,
        )

    @cached_property
    def quantidade_de_andamentos_de_exigencia(self) -> int:
        return self.andamentos_do_protocolo.filter(
            tipo_andamento__grupo_exigencia="S",
        ).count()

    # ADICIONAR AGENDA - DIGITALIZAR
    def agendar_notificacao_digitalizacao(self, data_agenda) -> None:
        # Configuração de zona horária
        timezone_sao_paulo = pytz.timezone("America/Sao_Paulo")

        # Se data_agenda não for fornecida, usa a data e hora atual na zona especificada
        if data_agenda is None:
            data_agenda = datetime.now(timezone_sao_paulo)
        elif isinstance(data_agenda, str):
            # Se for uma string, tenta converter para datetime
            try:
                data_agenda = datetime.strptime(data_agenda, "%Y-%m-%d").replace(
                    tzinfo=timezone_sao_paulo,
                )
            except ValueError:
                # Considerar tratamento de erro ou log aqui
                print("Erro ao converter data_agenda: ")
                return

        # Lista de colaborador para notificação
        colaboradores = User.get_usuarios_com_protocolos_prontos_digitalizar()

        # Verifica se há colaboradores para notificar
        if colaboradores:
            for _colaborador in colaboradores:
                # Supondo que criar_evento deve fazer algo com colaborador_id
                self.criar_evento(
                    fase_agenda=FaseAgenda.objects.get(pk=2),
                    exibir_agenda="N",
                    informar_prazo="S",
                    # colaborador=colaborador,  # Adicionado como exemplo de como usar o colaborador_id
                )

    def criar_evento(self, fase_agenda, exibir_agenda="S", informar_prazo=True) -> None:
        fase_agenda = FaseAgenda.objects.filter(id=fase_agenda.id).first()

        if fase_agenda:
            # PRAZO FIXO
            prazo = 0 if not informar_prazo else int(fase_agenda.prazo)

            if fase_agenda.id == TipoFaseAgenda.PROTOCOLO:  # PROTOCOLO
                prazo = Configuracao.obter("PRAZO_EXIGENCIA_EM_DIAS", 10)
            elif fase_agenda.id == TipoFaseAgenda.EVENTO:  # EVENTO
                prazo = Configuracao.obter("PRAZO_PREVISO_PROTOCOLO_EM_DIAS", 20)
            elif fase_agenda.id == 120:  # DISTRIBUICAO
                prazo = Configuracao.obter("PRAZO_VALIDADE_PROTOCOLO_EM_DIAS", 21)
            else:
                prazo = 0

            data_agenda = helpers.get_data_util_em_x_dias(
                self.data_protocolo,
                int(prazo),
            )

            # VERIFICAR SE O ANDAMENTO SERA FINALIZADO
            if (self.status.descricao in ["Registrado"]) and (
                fase_agenda.usar_data_atual
            ):
                andamento_pronto_para_registrar = self.pronto_para_registrar

                data_agenda = helpers.get_data_util_em_x_dias(
                    data=andamento_pronto_para_registrar.data,
                    dias=int(prazo),
                )
            else:
                data_agenda = helpers.get_data_util_em_x_dias(
                    data=self.data_protocolo,
                    dias=int(prazo),
                )

            # VERIFICAR SE EXISTE COLABORADOR VINCULADO A FASE
            if self.fases_protocolo_colaborador:
                colaborador = self.fases_protocolo_colaborador
            else:
                print("Verificando o colaborador default")
                colaborador = Colaborador.get_or_create_default()

            Event.criar_evento_no_calendario(
                user=colaborador,
                auth_user=colaborador,
                numero=self.numero_protocolo,
                title=fase_agenda.nome,
                description=f"{fase_agenda.descricao} {data_agenda.strftime(settings.DATE_FORMAT_STR)}",
                url="",
                origem="P",
                horas_adicionais=1,
                data_futura_inicio=data_agenda,
                data_futura_fim=data_agenda,
                gravar_apenas_data=False,
                fase_agenda_id=1,
                exibir_agenda=exibir_agenda,
            )
            return
        return

    def criar_eventos(self) -> None:
        print("CALENDARIO: Criando eventos para o Protocolo:", self)

        if self.status:
            print("CALENDARIO: Status atual do Protocolo:", self.status)

            # Filtrar os itens da agenda que correspondem ao status atual do protocolo
            fase_agenda_itens = FaseAgendaItem.objects.filter(status=self.status)

            # VERIFICANDO AS AGENDAS DE CADAS FASE
            for fase in fase_agenda_itens:
                self.criar_evento(fase_agenda=fase.fase_agenda)
                print("CALENDARIO: Evento criado: ", fase.fase_agenda.nome)

            logger.info(
                f"CALENDARIO: Fim da criação dos envetos na Agenda do Protocolo: {self}",
            )

    @classmethod
    def get_pelo_id(cls, pk) -> "Livro01Protocolo":
        if not pk:
            return None

        protocolo = cls.objects.filter(pk=pk).first()
        return protocolo if protocolo else None

    def get_pelo_numero(self, numero) -> "Livro01Protocolo":
        if not numero:
            return None

        protocolo = self.objects.filter(numero_protocolo=numero).first()
        return protocolo if protocolo else None

    @cached_property
    def data_pagamento(self) -> date:
        registros_financeiros = self.pedido.registros_financeiros
        return registros_financeiros if registros_financeiros else None

    @cached_property
    def origem_formatada(self) -> str:
        if self.protocolo_onr:
            return f" ONR: {self.protocolo_onr}"

        return f"{self.origem}" if self.origem else "Balcão"

    # PEDIDOS DE CERTIDÃO DE MATRÍCULA VISUALIZADA NO DIA ATUAL
    @classmethod
    def onr_e_protocolo(cls, data_inicio=None, data_fim=None) -> QuerySet:
        data_inicio = data_inicio or timezone.now().date()
        data_fim = data_fim or timezone.now().date() + timedelta(1)

        return cls.objects.filter(
            origem_pedido=7,
            data_protocolo__range=[data_inicio, data_fim],
        ).order_by("numero_protocolo")

    def registrar_impressao_recibo(self, usuario) -> None:
        pass
        # self.registrar_historico(TipoAndamento.RECIBO_IMPRESSO, descricao, usuario)

    def emolumento_bruto_calculado(self) -> Decimal:
        return Decimal("0.0")

    def emolumento_liquido_calculado(self) -> Decimal:
        return Decimal("0.0")

    def taxa_fiscal_judiciaria_calculada(self) -> Decimal:
        return Decimal("0.0")

    def recompe_calculado(self) -> Decimal:
        return Decimal("0.0")

    def issqn_calculado(self) -> Decimal:
        return Decimal("0.0")

    def total_calculado(self) -> Decimal:
        return Decimal("0.0")

    # TODOS OS ITENS SEPARADOS
    def get_itens_separados(self):
        agrupamento = {}

        for pedido_item in self.itens:
            agrupamento_id = (pedido_item.id, pedido_item.id)
            if agrupamento_id not in agrupamento:
                agrupamento[agrupamento_id] = {
                    "quantidade": 0,
                    "descricao_ato": "",
                    "codigo_tabela": "",
                    "numero_ato": "",
                    "tipo_registro": "",
                    "numero_registro": "",
                    "emolumento_bruto_calculado": Decimal("0.0"),
                    "emolumento_liquido_calculado": Decimal("0.0"),
                    "taxa_fiscal_judiciaria_calculada": Decimal("0.0"),
                    "recompe_calculado": Decimal("0.0"),
                    "issqn_calculado": Decimal("0.0"),
                    "total": Decimal("0.0"),
                    "selos": "",
                    "valor_avaliacao": Decimal("0.0"),
                    "descricao_cobranca": "",
                    "tipo_cobranca": "",
                }

            agrupamento[agrupamento_id]["quantidade"] += pedido_item.cdhu
            agrupamento[agrupamento_id]["descricao_ato"] += pedido_item.ato.tipo_ato
            agrupamento[agrupamento_id]["descricao_cobranca"] += (
                pedido_item.tabelacalculo.nome if pedido_item.tabelacalculo else ""
            )
            agrupamento[agrupamento_id]["tipo_cobranca"] += str(
                pedido_item.custas.descricao,
            ).split(
                "-",
            )[1]
            agrupamento[agrupamento_id]["codigo_tabela"] += pedido_item.codigo_tabela
            agrupamento[agrupamento_id]["numero_ato"] += (
                str(pedido_item.numero_ato)
                if pedido_item.numero_ato is not None
                else ""
            )
            agrupamento[agrupamento_id]["tipo_registro"] += (
                str(pedido_item.tipo_registro)
                if pedido_item.tipo_registro is not None
                else ""
            )
            agrupamento[agrupamento_id]["numero_registro"] += (
                str(pedido_item.numero_registro_formatado)
                if pedido_item.numero_registro_formatado is not None
                else ""
            )
            agrupamento[agrupamento_id]["emolumento_bruto_calculado"] += (
                pedido_item.valor_emolumento
            )
            agrupamento[agrupamento_id]["emolumento_liquido_calculado"] += (
                pedido_item.valor_emolumento
            )
            agrupamento[agrupamento_id]["taxa_fiscal_judiciaria_calculada"] += (
                pedido_item.valor_tfj
            )
            agrupamento[agrupamento_id]["recompe_calculado"] += (
                pedido_item.valor_fundo_estado
            )
            agrupamento[agrupamento_id]["issqn_calculado"] += (
                pedido_item.valor_issqn_calculado
            )
            agrupamento[agrupamento_id]["total"] += (
                pedido_item.valor_emolumento
                + pedido_item.valor_tfj
                + pedido_item.valor_fundo_estado
                + pedido_item.valor_issqn_calculado
            )
            # agrupamento[agrupamento_id]["selos"] +=

            # if pedido_item.get_data_selo_formatada:
            #     str(pedido_item.get_selos + " (" + str(pedido_item.get_data_selo_formatada) + ")")
            # else:
            #     ''
            #         ,

            # Verifica e adiciona o selo formatado
            if pedido_item.get_data_selo_formatada:
                selo_formatado = (
                    f"{pedido_item.get_selos} ({pedido_item.get_data_selo_formatada})"
                )
            else:
                selo_formatado = pedido_item.get_selos

            agrupamento[agrupamento_id]["selos"] += selo_formatado
            agrupamento[agrupamento_id]["valor_avaliacao"] += (
                pedido_item.valor_avaliacao
            )

        return agrupamento

    def get_itens_agrupados(self):
        itens_do_pedido = self.pedidos_itens.all()

        agrupamento = {}

        for pedido_item in itens_do_pedido:
            agrupamento_id = (pedido_item.titulo_principal, pedido_item.ato_principal)
            if agrupamento_id not in agrupamento:
                agrupamento[agrupamento_id] = {
                    "quantidade": 0,
                    "emolumento_bruto_calculado": Decimal("0.0"),
                    "emolumento_liquido_calculado": Decimal("0.0"),
                    "taxa_fiscal_judiciaria_calculada": Decimal("0.0"),
                    "recompe_calculado": Decimal("0.0"),
                    "issqn_calculado": Decimal("0.0"),
                    "total": Decimal("0.0"),
                }

            agrupamento[agrupamento_id]["quantidade"] += 1
            agrupamento[agrupamento_id]["emolumento_bruto_calculado"] += (
                pedido_item.valor_emolumento
            )
            agrupamento[agrupamento_id]["emolumento_liquido_calculado"] += (
                pedido_item.valor_emolumento
            )
            agrupamento[agrupamento_id]["taxa_fiscal_judiciaria_calculada"] += (
                pedido_item.valor_tfj
            )
            agrupamento[agrupamento_id]["recompe_calculado"] += (
                pedido_item.valor_fundo_estado
            )
            agrupamento[agrupamento_id]["issqn_calculado"] += pedido_item.valor_issqn
            agrupamento[agrupamento_id]["total"] += 0

        return agrupamento

    def encerrar_evento_pela_data_do_andamento(
        self,
        andamento: "Livro01Andamento",
    ) -> None:
        # FILTRAR OS EVENTOS DO SERVICOS ANDAMENTOS
        fase_agenda_itens_andamentos = models.FaseAgendaItemAndamento.objects.filter(
            tipo_andamento_id=andamento.tipo_andamento_id,
        )

        for evento in fase_agenda_itens_andamentos:
            titulo = (
                evento.fase_agenda.nome
            )  # FaseAgenda.objects.filter(self=evento).values_list("nome", flat=True)
            titulo_baixar = f"{titulo} {self.numero_protocolo!s}"
            models.Event.objects.encerrar_evento_pelo_titulo(
                titulo=titulo_baixar,
                data=andamento.data,
            )

    def get_data_registro(self: "Livro01Protocolo"):
        protocolo_id = Livro01Protocolo.objects.filter(
            pedido_id=self.pedido_id,
        ).values_list("id", flat=True)[0]
        return Livro01Andamento.objects.filtrar_andamento_data_registrado(protocolo_id)

    @classmethod
    def criar_ou_atualizar_protocolo_obtido_do_fb(
        cls: "Livro01Protocolo",
        protocolo_fb: dict,
    ) -> "Livro01Protocolo":
        logger.info(
            f"PROTOCOLOS: Criando/atualizando protocolo a partir: {protocolo_fb['NROORDEM']}",
        )

        pedido = Pedido.objects.filter(pk=protocolo_fb["CHAVE_PEDIDOS"]).first()

        if not pedido:
            logger.warning(
                f"Pedido {protocolo_fb['CHAVE_PEDIDOS']} não encontrado para criar/atualizar protocolo",
            )
            return None

        try:
            logger.info("\n\n\n*************************************")
            logger.info(
                f"PROTOCOLOS: Verificando protocolo {protocolo_fb['NROORDEM']} com dados",
            )

            obj = cls.objects.filter(numero_protocolo=protocolo_fb["NROORDEM"]).first()
            obj = (
                cls.update_protocolo(protocolo_fb, obj, pedido)
                if obj
                else cls.create_protocolo(protocolo_fb, pedido)
            )

        except Exception as e:
            logger.exception(
                f"ERRO ao criar/atualizar protocolo a partir do FB {protocolo_fb['NROORDEM']}: {e}",
            )
            raise

        return obj

    @cached_property
    def selo_codigo_para_consulta(self):
        return SeloEletronico.objects.filter(
            pedido_item__in=self.itens,
            selo_de_consulta="S",
        ).first()

    @cached_property
    def quantidade_selo_sqlserver(self):
        with sqlserver.SqlServerConnection() as db:
            selo = db.get_selo_por_protocolo(self.numero_protocolo)

        return selo if selo else 0

    def selar(self):
        with transaction.atomic():
            try:
                retorno = sqlserver.selar_certidao(self)
                if retorno:
                    Livro01Protocolo.registrar_andamento_selo(self)
                else:
                    msg = "Não foi possivel selar: Verifique se já foi selada anteriormente."
                    raise Exception(msg)
            except Exception as e:
                logger.exception(f"Erro ao selar certidão {e}")
                raise

    def enviar_para_pagamento_caixa(
        self,
        valor_transacao,
        tipo_operacao_financeira_id,
        tipo_transacao_id,
        descricao,
        nome_pagador,
        data_original,
        colaborador_financeiro_id,
    ):
        Financeiro.receber_protocolo_caixa(
            self,
            valor_transacao=valor_transacao,
            tipo_operacao_financeira_id=tipo_operacao_financeira_id,
            tipo_transacao_id=tipo_transacao_id,
            descricao=descricao,
            nome_pagador=nome_pagador,
            data_original=data_original,
            colaborador_financeiro_id=colaborador_financeiro_id,
        )

    def enviar_para_caixa_firebird(
        self,
        usuario: User,
        valor_transacao,
    ) -> tuple[bool, str]:
        from apps.home.services.firebird import gravar_caixa_do_protocolo_no_firebird

        db = FbConnection()
        db.begin_transaction()

        gravar_caixa_do_protocolo_no_firebird(
            pedido_id=self.pedido_id,
            # valor=self.valor_total_protocolo,
            valor=valor_transacao,
            funcionarios_id=usuario.id,
            descricao=str(self.nome_apresentante).upper(),
            db=db,
        )

        db.commit()
        db.close()

        return True, "Protocolo enviado para o caixa."
        # return False, "Erro ao enviar o protocolo para o caixa."

    @property
    def andamento_protocolo_entregue(self):
        return self.andamentos.filter(
            Q(tipo_andamento__grupo_protocolo_entregue="S") & Q(andamento_ativo="S"),
        ).exists()

    def registrar_andamento_protocolo_entregue(self, usuario) -> None:
        tipos_andamentos = TipoAndamento.objects.filter(grupo_protocolo_entregue="S")

        # VERIFICAR SE NAO TEM VALOR EM ABERTO DO PROTOCOLO NO SISTEMA ANTIGO
        db = firebird.FbConnection()
        valor_diferenca = self.verificar_diferenca_sistema_antigo(db)

        # SO ENTREGUE SE NAO HOUVER VALORES A RECEBER
        if Decimal(valor_diferenca) == 0:
            if tipos_andamentos:
                for tipo_andamento in tipos_andamentos:
                    Livro01Andamento.objects.create(
                        protocolo=self,
                        tipo_andamento=tipo_andamento,
                        data=timezone.now(),
                        texto="PROTOCOLO ENTREGUE",
                        colaborador_id=usuario.id,
                        colaborador_destino_id=usuario.id,
                    )
            return None
        else:
            return "EXISTEM VALORES EM ABERTO. NÃO E PERMITIDO ENTREGAR SEM ACERTAR VALORES!"

    def verificar_diferenca_sistema_antigo(self, db) -> Decimal:
        """FILTRAR PEDIDO - ORIGINAL - CALCULAR DIFERENCA."""
        pedido_fb = firebird.get_pedido_fb(self.pedido.id, db)
        if pedido_fb:
            return pedido_fb["VALORFINAL"] - pedido_fb["VALORACERTO"]
        return 0

    def get_valor_final_sistema_antigo(self, db) -> Decimal:
        """VALORFINAL."""
        pedido_fb = firebird.get_pedido_fb(self.pedido.id, db)
        if pedido_fb:
            return pedido_fb["VALORFINAL"] if pedido_fb["VALORFINAL"] else 0
        return 0

    def get_valor_acerto_sistema_antigo(self, db) -> Decimal:
        """VALORACERTO."""
        pedido_fb = firebird.get_pedido_fb(self.pedido.id, db)
        if pedido_fb:
            return pedido_fb["VALORACERTO"] if pedido_fb["VALORACERTO"] else 0
        return 0

    # verificar se os andamentos estao sincronizados com sistema antigo
    def verificar_andamentos_sistema_antigo(self):
        # ULTIMO ANDAMENTO CADASTRADO
        data_ultimo_andamento = self.data_ultimo_andamento

        if data_ultimo_andamento:
            # PESQUISAR TODOS OS ANDAMENTOS DO SISTEMA ANTIGO
            firebird.pesquisar_andamentos_do_protocolo_pela_data(
                self,
                data_ultimo_andamento,
            )


class EmolumentoAno(models.Model):
    data_inicial = models.DateField()
    data_final = models.DateField()
    descricao_periodo: str = models.CharField(max_length=50, blank=True, null=True)

    objects: managers.EmolumentoAnoManager = managers.EmolumentoAnoManager()

    class Meta:
        verbose_name = "Emolumento Ano"
        verbose_name_plural = "Emolumentos Anos"
        ordering = ["-data_final"]

    def __str__(self) -> str:
        return f"VIGENCIA: ({self.data_inicial.strftime(settings.DATE_FORMAT_STR) } até {self.data_final.strftime(settings.DATE_FORMAT_STR)})"

    @cached_property
    def ano(self):
        return self.data_inicial.year if self.data_inicial else timezone.now().year

    @classmethod
    def get_vigencia_atual(cls) -> "EmolumentoAno":
        """Retorna o ID da vigencia mais recente dos emolumentos."""
        vigencia = cls.objects.order_by("id").last()

        if not vigencia:
            data_inicial = timezone.now().date()
            data_final = timezone.now().date() + timedelta(days=365)
            logger.info(
                f"Criando um nova vigencia para os emolumentos de {data_inicial} até {data_final}",
            )
            vigencia = cls.objects.create(
                data_inicial=data_inicial,
                data_final=data_final,
                descricao_periodo=f"Vigencia: {data_inicial} até {data_final}",
            )

        logger.info(f"Obtendo:{vigencia}")
        return vigencia

    @classmethod
    def get_vigencia(cls, data: datetime | None = None) -> "EmolumentoAno":
        """Retorna a vigencia de acordo com a data."""
        if data is None:
            print("Data não informada para obter a vigencia. Utilizando a data atual.")
            data = timezone.now().date()

        vigencia = cls.objects.filter(
            data_inicial__lte=data,
            data_final__gte=data,
        ).first()

        if not vigencia:
            logger.debug("Vigencia não encontrada. Verificando a vigencia atual.")
            cls.objects.last()
            # data_inicial = data
            # data_final = data + timedelta(days=365)
            # logger.info(
            #     f"Criando um nova vigencia para emolumentos de {data_inicial} até {data_final}",
            # )
            # vigencia = cls.objects.create(
            #     data_inicial=data_inicial,
            #     data_final=data_final,
            #     descricao_periodo=f"Vigencia: {data_inicial} até {data_final}",
            # )

        logger.info(f"{vigencia}")
        return vigencia

    # SELAR NO SQL SERVER PROTOCOLO
    def selar(self: "Livro01Protocolo") -> None:
        with transaction.atomic():
            try:
                selado = sqlserver.selar_certidao(self)
                if selado:
                    models_certidoes.PedidoCertidao.adicionar_andamento_selo(
                        pedido_certidao=self,
                    )
                else:
                    msg = f"Não foi possivel selar: {self.qualificacao_completa}. Verifique se já foi selada anteriormente."
                    raise Exception(msg)
            except Exception as e:
                logger.exception(
                    f"Erro ao selar certidão {self.qualificacao_completa}: {e}",
                )
                raise


class Emolumentos(models.Model):
    nome: str = models.CharField(max_length=100, blank=True, null=True)
    utilizado: str = models.CharField(max_length=1, blank=True, null=True)
    ato_complementar: str = models.CharField(max_length=1, blank=True, null=True)
    atos = models.ForeignKey(
        AtoPratica,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    titulo = models.ForeignKey(Titulo, on_delete=models.CASCADE, blank=True, null=True)
    desconto = models.DecimalField(
        default=0,
        blank=False,
        max_digits=15,
        decimal_places=2,
        null=True,
    )
    descricao: str = models.CharField(max_length=500, blank=True, null=True)
    inativo: str = models.CharField(max_length=1, blank=True, null=True)
    gerarselo: str = models.CharField(max_length=1, blank=True, null=True)
    codigo_tabela_inicial: str = models.CharField(blank=True, null=True)
    emolumento_default: str = models.CharField(
        max_length=1,
        blank=True,
        null=True,
        default="N",
        choices=(("S", "Sim"), ("N", "Não")),
    )

    emolumento_prenotacao: str = models.CharField(
        max_length=1,
        blank=True,
        null=True,
        default=TipoSimNao.NAO,
        choices=TipoSimNao.CHOICES,
    )

    objects: managers.EmolumentoManager = managers.EmolumentoManager()

    class Meta:
        verbose_name = "Emolumento"
        verbose_name_plural = "Emolumentos"

    def __str__(self) -> str:
        return str(self.nome)

    @cached_property
    def codigo_tabela(self):
        # Verifica se o valor inicial é válido
        if self.codigo_tabela_inicial:
            # Converte para inteiro, desprezando as casas decimais
            codigo_corrigido = int(Decimal(self.codigo_tabela_inicial))
            # Formata o código como string com 5 dígitos, separando o último dígito com traço
            codigo_formatado = f"{codigo_corrigido:05}"
            codigo_formatado = f"{codigo_formatado[:-1]}-{codigo_formatado[-1]}"
        else:
            # Retorna o valor padrão se o código inicial for None ou inválido
            codigo_formatado = "0000-0"
        return codigo_formatado

    @classmethod
    def obter(
        cls,
        emolumento_id: int,
        valor_documento: Decimal,
        data_documento=None,
    ) -> "Emolumentos":
        """Obtem um emolumento baseado no ID fornecido ou retorna o emolumento provisório."""
        data_documento = data_documento if data_documento else timezone.now().date()

        emolumento = cls.objects.filter(pk=emolumento_id).first()
        if not emolumento:
            logger.warning(
                "Emolumento não encontrado. Retornando emolumento provisório.",
            )
            emolumento = cls.get_default_provisorio()
        emolumento.vigencia = (
            EmolumentoAno.get_vigencia(data_documento)
            if data_documento
            else EmolumentoAno.get_vigencia_atual()
        )

        valores = emolumento.calcular(valor_documento, emolumento.vigencia)
        emolumento.codigo_tabela = valores.codigo_tabela if valores else 0
        emolumento.valores = valores if valores else None

        return emolumento

    @cached_property
    def vigencia_atual_id(self) -> int:
        vigencia_atual = EmolumentoAno.get_vigencia_atual()
        return vigencia_atual.id if vigencia_atual else 0

    @classmethod
    def get_vigencia_atual_id(cls) -> int:
        vigencia_atual = EmolumentoAno.get_vigencia_atual()
        return vigencia_atual.id if vigencia_atual else 0

    @classmethod
    def get_vigencia_atual(cls) -> EmolumentoAno:
        return EmolumentoAno.get_vigencia_atual()

    @classmethod
    def get_emolumento_provisorio_id(cls) -> int:
        emolumento = cls.get_default_provisorio()
        return emolumento.id if emolumento else 1377

    @staticmethod
    def get_provisorio_query() -> Q:
        """
        Retorna uma expressão Q para verificar se o nome é igual a 'Provisório' ou 'Provisorio',
        ignorando maiúsculas e minúsculas.
        """
        return Q(nome__iexact=PROVISORIO) | Q(nome__iexact="Provisorio")

    @classmethod
    def get_default_provisorio(cls) -> "Emolumentos":
        try:
            obj, created = cls.objects.get_or_create(cls.get_provisorio_query())
            return obj
        except (cls.DoesNotExist, cls.MultipleObjectsReturned):
            logger.warning(
                "Erro ao obter emolumento provisório. Mais de um registro encontrado. Retornando o primeiro.",
            )
            return cls.objects.filter(cls.get_provisorio_query()).first()

    def calcular(
        self: "Emolumentos",
        valor_documento: Decimal,
        vigencia: "EmolumentoAno" = None,
    ) -> "EmolumentoValor":
        """Seleciona emolumentos com base na faixa de valor do documento."""
        vigencia = vigencia if vigencia else Emolumentos.get_vigencia_atual()
        logger.info(
            f"Obtendo valores de emolumentos para o valor do documento: {valor_documento}. {vigencia}",
        )
        valor_documento_decimal = Decimal(str(valor_documento).replace(",", "."))
        emolumento_valor = (
            EmolumentoValor.objects.filter(
                emolumento_id=self.pk,
                vigencia=vigencia,
                faixa_inicio__lte=valor_documento_decimal,
                faixa_fim__gte=valor_documento_decimal,
                valor_emolumento__gt=0,
            )
            .order_by("id")
            .last()
        )

        if not emolumento_valor:
            # Tenta encontrar o emolumento pelo codigo:
            emolumento_valor = (
                EmolumentoValor.objects.filter(
                    codigo_tabela=self.codigo_tabela,
                    vigencia=vigencia,
                    faixa_inicio__lte=valor_documento_decimal,
                    faixa_fim__gte=valor_documento_decimal,
                    valor_emolumento__gt=0,
                )
                .order_by("id")
                .last()
            )

            if not emolumento_valor and valor_documento_decimal > 0:
                # Tenta encontrar o emolumento pelo codigo:
                emolumento_valor = (
                    EmolumentoValor.objects.filter(
                        codigo_tabela=self.codigo_tabela,
                        vigencia=vigencia,
                        faixa_inicio=0,
                        faixa_fim=0,
                        valor_emolumento__gt=0,
                    )
                    .order_by("id")
                    .last()
                )

            if not emolumento_valor:
                logger.warning(
                    f"""Valores de emolumentos não encontrados com os criterios fornecidos:
                        Emolumento ID: {self.pk},
                        Valor Documento: {valor_documento_decimal},
                        Vigencia: {vigencia},
                        Valor maior que: 0
                    -> Será utilizado o emolumento provisório.
                        """,
                )
                # obter provisorio
                emolumento_valor: EmolumentoValor = EmolumentoValor.get_provisorio()

            # emolumento.descricao = emolumento.descricao or "Não Encontrado"
            emolumento_valor.faixa_inicio = (
                safe_decimal(emolumento_valor.faixa_inicio, 0.0)
                if emolumento_valor.faixa_inicio
                else Decimal(0.0)
            )
            emolumento_valor.faixa_fim = (
                safe_decimal(emolumento_valor.faixa_fim, 0.0)
                if emolumento_valor.faixa_fim
                else Decimal(0.0)
            )
            emolumento_valor.codigo_tabela = emolumento_valor.codigo_tabela or 0
            # emolumento_valor.valor_adicionado = (
            #     safe_decimal(emolumento_valor.valor_adicionado, 0.0) if emolumento_valor.valor_adicionado else Decimal(0.0)
            # )
            emolumento_valor.valor_fundo_estado = (
                safe_decimal(emolumento_valor.valor_fundo_estado, 0.0)
                if emolumento_valor.valor_fundo_estado
                else Decimal(0.0)
            )
            emolumento_valor.valor_taxa2 = (
                safe_decimal(emolumento_valor.valor_taxa2, 0.0)
                if emolumento_valor.valor_taxa2
                else Decimal(0.0)
            )
            emolumento_valor.valor_taxa3 = (
                safe_decimal(emolumento_valor.valor_taxa3, 0.0)
                if emolumento_valor.valor_taxa3
                else Decimal(0.0)
            )
            emolumento_valor.valor_taxa4 = (
                safe_decimal(emolumento_valor.valor_taxa4, 0.0)
                if emolumento_valor.valor_taxa4
                else Decimal(0.0)
            )
            emolumento_valor.valor_emolumento = (
                safe_decimal(emolumento_valor.valor_emolumento, 0.0)
                if emolumento_valor.valor_emolumento
                else Decimal(0.0)
            )
            emolumento_valor.valor_issqn = (
                safe_decimal(emolumento_valor.valor_issqn, 0.0)
                if emolumento_valor.valor_issqn
                else Decimal(0.0)
            )
            emolumento_valor.valor_total = (
                safe_decimal(emolumento_valor.valor_total, 0.0)
                if emolumento_valor.valor_total
                else Decimal(0.0)
            )

        return emolumento_valor


class TipoTributacao(models.Model):
    descricao: str = models.CharField(max_length=300, blank=True, null=True)
    outros_codigo_trib_tj = models.BigIntegerField(blank=True, null=True)
    outros: str = models.CharField(max_length=300, blank=True, null=True, default="")
    utilizado: str = models.CharField(max_length=1, blank=True, null=True, default="S")
    percentual_desconto = models.DecimalField(
        blank=False,
        max_digits=15,
        decimal_places=2,
        null=True,
        default=0.0,
    )

    ativo_certidao: bool = models.BooleanField(default=True)
    ativo_protocolo: bool = models.BooleanField(default=True)
    sempre_cobrar_taxa_judiciaria: bool = models.BooleanField(default=False)

    objects: managers.TipoTributacaoManager = managers.TipoTributacaoManager()

    class Meta:
        verbose_name = "Tipo de Tributação"
        verbose_name_plural = "Tipos de Tributação"
        ordering = ["descricao"]

    def __str__(self) -> str:
        return str(self.descricao)


# Create your models here.
class PedidoItem(models.Model):
    pedido = models.ForeignKey(
        Pedido,
        on_delete=models.CASCADE,
        related_name="itens_do_pedido",
        null=True,
    )
    ato = models.ForeignKey(
        AtoPratica,
        on_delete=models.CASCADE,
        related_name="pedido_item_atos",
        null=True,
    )
    titulo = models.ForeignKey(Titulo, on_delete=models.CASCADE, null=True)
    vigencia = models.ForeignKey(EmolumentoAno, on_delete=models.CASCADE, null=True)

    tabelacalculo = models.ForeignKey(Emolumentos, on_delete=models.CASCADE, null=True)

    cdhu = models.DecimalField(max_digits=12, decimal_places=2)
    codigo_tabela: str = models.CharField(max_length=10, blank=True, null=True)

    # numero_registro:str = models.CharField(max_length=12, blank=True, null=True, db_index=True)
    numero_registro = models.BigIntegerField(null=True, db_index=True)

    tipo_registro: str = models.CharField(
        max_length=1,
        blank=True,
        null=True,
        db_index=True,
    )
    numero_ato: str = models.CharField(max_length=20, blank=True, null=True)
    selo: str = models.CharField(max_length=50, blank=True, null=True)
    numero_ri: str = models.CharField(
        max_length=6,
        blank=True,
        null=True,
        db_index=True,
    )
    custas = models.ForeignKey(TipoTributacao, on_delete=models.CASCADE, null=True)
    colaborador = models.BigIntegerField(blank=True, null=True)
    numero_titulo = models.BigIntegerField(blank=True, null=True)
    data_pagamento = models.DateField(blank=True, null=True)

    # Valores do Ato
    valor_emolumento = models.DecimalField(
        blank=False,
        max_digits=12,
        decimal_places=2,
        verbose_name="Valor do Emolumento",
        default=0.0,
        null=True,
        help_text="Valor do Emolumento",
    )
    valor_tfj = models.DecimalField(
        blank=False,
        decimal_places=2,
        max_digits=12,
        verbose_name="Valor da Taxa Fiscal Judiciaria",
        null=True,
        default=0.0,
        help_text="Taxa Fiscal Judiciária",
    )
    valor_fundo_estado = models.DecimalField(
        blank=False,
        max_digits=12,
        decimal_places=2,
        null=True,
        default=0.0,
        verbose_name="Valor Fundo Estado",
        help_text="Valor Fundo Estado",
    )
    valor_itbi = models.DecimalField(
        blank=False,
        decimal_places=2,
        max_digits=12,
        null=True,
        verbose_name="Valor do ITBI",
        default=0.0,
        help_text="Imposto sobre Transmissão de Bens Imóveis",
    )
    valor_issqn = models.DecimalField(
        blank=False,
        max_digits=12,
        decimal_places=2,
        null=True,
        verbose_name="Valor do ISSQN",
        default=0.0,
        help_text="ISSQN - Imposto Sobre Serviços de Qualquer Natureza",
    )
    valor_avaliacao = models.DecimalField(
        blank=False,
        max_digits=12,
        decimal_places=2,
        null=True,
        default=0.0,
        verbose_name="Valor de Avaliação",
        help_text="Valor do imóvel avaliado",
    )

    # Tipo do Ato
    ato_tipo: str = models.CharField(max_length=3, blank=False, null=True)
    ato_numero = models.BigIntegerField(blank=True, null=True)

    objects: managers.PedidoItemManager = managers.PedidoItemManager()

    class Meta:
        verbose_name = "Pedido Item"
        verbose_name_plural = "Pedidos Itens"
        # db_table = "pedido_item"
        # cria indice composto para numero_registro, tipo_registro, numero_ri
        indexes = [
            models.Index(fields=["numero_registro", "tipo_registro", "numero_ri"]),
        ]

    def __str__(self) -> str:
        return str(self.titulo)

    @cached_property
    def texto_nota_devolucao(self) -> str:
        return NotaDevolucaoTexto.objects.filter(pedido_item=self)

    @cached_property
    def numero_registro_formatado(self) -> str:
        if self.numero_registro:
            numero = str(self.numero_registro)
            return numero if len(numero) <= 3 else numero[:-3] + "." + numero[-3:]
        else:
            return ""

    @cached_property
    def valor_avaliacao_moeda(self) -> str:
        return formatar_moeda(self.valor_avaliacao)

    @cached_property
    def valor_itbi_moeda(self) -> str:
        return formatar_moeda(self.valor_itbi)

    @cached_property
    def valor_fundo_estado_moeda(self) -> str:
        return formatar_moeda(self.valor_fundo_estado)

    @cached_property
    def valor_tfj_moeda(self) -> str:
        return formatar_moeda(self.valor_tfj)

    @cached_property
    def valor_emolumento_moeda(self) -> str:
        return formatar_moeda(self.valor_emolumento)

    @cached_property
    def valor_issqn_moeda(self) -> str:
        return formatar_moeda(self.valor_issqn)

    @cached_property
    def get_selos(self):
        selo = SeloEletronico.objects.filter(pedido_item_id=self.id).values_list(
            "codigo_sequencial_unico",
            flat=True,
        )
        return ", ".join(selo) if selo else ""

    @cached_property
    def valor_issqn_calculado(self) -> Decimal:
        percentual_issqn = EmolumentoValor.objects.filter(
            vigencia_id=self.vigencia_id,
        ).aggregate(
            Max("percentual_issqn"),
        )["percentual_issqn__max"]

        return (
            (percentual_issqn / 100) * self.valor_emolumento
            if percentual_issqn
            else Decimal(0.0)
        )

    @cached_property
    def valor_total(self) -> Decimal:
        return (
            self.valor_emolumento
            + self.valor_tfj
            + self.valor_fundo_estado
            + self.valor_issqn
        )

    @cached_property
    def valor_total_formatado(self) -> str:
        # Formata o valor total para representação em string com duas casas decimais
        return f"{self.valor_total.quantize(Decimal('0.01'))}"

    @cached_property
    def valor_total_moeda(self) -> str:
        return formatar_moeda(self.valor_total_formatado)

    def get_dados_do_registro_auxiliar(self: "PedidoItem") -> dict:
        # PEGANDO OS DADOS DO REGISTRO AUXILIAR
        registro_auxiliar = Livro03.objects.filter(
            numero=self.numero_registro,
            cartorio=self.numero_ri,
        ).first()

        return {
            "numero_registro_auxiliar": self.numero_registro if self else "",
            "tipo_registro": self.tipo_registro if self else "",
            "cartorio_imovel": self.numero_ri if self else "",
            "cancelado_em_id": registro_auxiliar.id if registro_auxiliar else "",
            "data_abertura_id": (
                registro_auxiliar.data_abertura if registro_auxiliar else ""
            ),
            "registro_auxiliar_id": (
                registro_auxiliar.cancelado_em if registro_auxiliar else ""
            ),
            "municipio_id": "",
            "data_vencimento_id": (
                registro_auxiliar.data_vencimento if registro_auxiliar else ""
            ),
            "numero_cedula_l_id3": (
                registro_auxiliar.numero_cedula if registro_auxiliar else ""
            ),
            "tipo_registro_auxiliar_id": (
                registro_auxiliar.tipo_registro_auxiliar if registro_auxiliar else ""
            ),
            "descricao_id": registro_auxiliar.descricao if registro_auxiliar else "",
        }

    def get_dados_do_registro(self: "PedidoItem") -> dict:
        dados_do_registro_dict = {
            "numero_registro": "",
            "tipo_registro": "",
            "cartorio_imovel": "",
            "comercial_id": "",
            "numero_unidade_U_id": "",
            "quadra_U_id": "",
            "area_U_id": "",
            "lotes_id": "",
            "area_id": "",
            "quadra_id": "",
            "setor_id": "",
            "residencial_id": "",
            "numero_unidade_id": "",
            "numero_edificacao_id": "",
            "conjunto_id": "",
            "bloco_id": "",
            "outras_id": "",
            "unidade_aux_id": "",
            # "comercial_id": "",
            "numero_municipal_id": "",
            "ruas_id": "",
            "nome_rua_id": "",
            "numero_rua_id": "",
            "numero_contribuinte_id": "",
            "municipio_id": "",
            "data_abertura_id": "",
            "classe_id": "",
            "anterior_numero_id": "",
            "anterior_tipo_id": "",
            "anterior_complemento_id": "",
            "imovel_id": "",
            "nome_fazenda_rural_id": "",
            "localizacao_rural_id": "",
            "area_rural_id": "",
            "caracteristica_rural_id": "",
            "remanescente_id": "",
            "numero_nirf": "",
            "numero_ccirr": "",
            "numero_car": "",
            "numero_incra": "",
            "data_validade_itr": "",
            "m_frente_metros": "",
            "p_frente_metros": "",
            "m_direito_metros": "",
            "p_direito_metros": "",
            "p_esquerdo_metros": "",
            "m_esquerdo_metros": "",
            "p_fundo_metros": "",
            "m_fundo_metros": "",
        }
        dados_do_registro_dict.update(
            {
                "numero_registro": self.numero_registro,
                "tipo_registro": self.tipo_registro,
                "cartorio_imovel": self.numero_ri,
            },
        )

        # PEGANDO OS DADOS DO IMOVEL
        registro = Livro02.objects.get_pelo_pedido_item(self)

        if not registro:
            logger.warning(f"Imóvel não encontrado para o pedido_item_id: {self.pk}")
            return dados_do_registro_dict

        (
            dados_do_registro_dict.update(
                {
                    "municipio_id": registro.municipio,
                    "classe_id": registro.classe,
                    "data_abertura_id": registro.data_abertura,
                    "imovel_id": registro.pk,
                    "numero_nirf": registro.numero_nirf,
                    "numero_ccirr": registro.numero_ccirr,
                    "numero_car": registro.numero_car,
                    "numero_incra": registro.numero_incra,
                    "data_validade_itr": registro.data_validade_itr,
                    "area_construida_residencial_id": registro.area_construida_residencial,
                },
            )
            if registro
            else ""
        )

        if registro.classe == "R":
            rural_nome = RuralNome.objects.filter(imovel_id=registro.pk).first()
            nome_fazenda_rural_id = rural_nome.nome

            rural = Rural.objects.filter(imovel_id=registro.pk).first()

            if rural:
                dados_do_registro_dict.update(
                    {
                        "nome_fazenda_rural_id": nome_fazenda_rural_id,
                        "localizacao_rural_id": rural.localizacao,
                        "area_rural_id": rural.area,
                        "caracteristica_rural_id": rural.caracteristica,
                        "remanescente_id": (
                            "Sim" if rural.remanescente == "T" else "Näo"
                        ),
                        "georeferencial_id": (
                            "Sim" if rural.georeferencial == "T" else "Näo"
                        ),
                        "comercial_id": "Rural",
                    },
                )

        # LISTANDO OS DADOS DO LOTE
        if registro.classe == "L":
            # PEGANDO O ENDERECO DO IMOVEL URBANO
            unidade = Unidade.objects.filter(imovel_id=registro.pk).first()

            # PEGANDO O ENDERECO DO IMOVEL URBANO
            lote = Lote.objects.filter(unidade=unidade.id).first()

            # VERIFIR SE O IMOVEL E COMERCIAL
            if lote:
                comercial_residencial_id = "Comercial" if lote.comercial == "T" else ""
                comercial_residencial_id = (
                    "Residencial" if lote.residencial == "T" else ""
                )
            else:
                comercial_residencial_id = ""
                comercial_residencial_id = ""

            # Atualizando a lista - TIPO DE CONSTRUCAO
            dados_do_registro_dict.update(
                {
                    "comercial_id": comercial_residencial_id,
                    "numero_unidade_id": lote.numero_unidade if lote else "",
                    "area_id": lote.area if lote else 0,
                    "quadra_id": lote.quadra if lote else 0,
                    "setor_id": lote.setor if lote else 0,
                },
            )

            # PEGANDO A RUA DO ENDERECO DO IMOVEL URBANO - SEMPRE O 1 NOME DA RUA
            rua = Rua.objects.filter(unidade_id=unidade.pk).first()

            if rua:
                dados_do_registro_dict.update(
                    {
                        "nome_rua_id": rua.nome,
                        "numero_rua_id": rua.numero_edificacao,
                    },
                )

            # PEGANDO AS MEDIDAS DO IMOVEL
            medida = ImovelMedida.objects.filter(imovel_id=registro.pk).first()

            if medida:
                dados_do_registro_dict.update(
                    {
                        "m_frente_metros": medida.m_frente_metros if medida else 0,
                        "p_frente_metros": medida.p_frente_metros if medida else 0,
                        "m_direito_metros": medida.m_direito_metros if medida else 0,
                        "p_direito_metros": medida.p_direito_metros if medida else 0,
                        "p_esquerdo_metros": medida.p_esquerdo_metros if medida else 0,
                        "m_esquerdo_metros": medida.m_esquerdo_metros if medida else 0,
                        "p_fundo_metros": medida.p_fundo_metros if medida else 0,
                        "m_fundo_metros": medida.m_fundo_metros if medida else 0,
                    },
                )

        # PEGANDO O CONTRIBUINTE DO IMOVEL URBANO
        contribuinte = Contribuintes.objects.filter(imovel_id=registro.pk).first()
        dados_do_registro_dict.update(
            {
                "numero_contribuinte_id": (
                    contribuinte.numero_contribuinte if contribuinte else ""
                ),
            },
        )

        # PEGANDO O Anterior DO IMOVEL
        anterior = Anterior.objects.filter(imovel_id=registro.pk).first()

        if anterior:
            dados_do_registro_dict.update(
                {
                    "anterior_numero_id": anterior.numero,
                    "anterior_tipo_id": anterior.tipo,
                    "anterior_complemento_id": anterior.complemento,
                },
            )

        return dados_do_registro_dict

    @cached_property
    def ato_principal(self):
        return self.ato

    @cached_property
    def titulo_principal(self):
        return self.titulo

    def garantias(self):
        return Livro03Garantia.objects.filter(
            numero_registro=self.numero_registro,
            tipo_registro=self.tipo_registro,
        ).order_by("-registro_auxiliar")

    @cached_property
    def imovel(self):
        return Livro02.objects.filter(
            numero=self.numero_registro,
            tipo=self.tipo_registro,
            cartorio=self.numero_ri,
        ).first()

    @cached_property
    def quantidade_de_registros_relacionados(self):
        return Livro02.objects.filter(
            numero=self.numero_registro,
            tipo=self.tipo_registro,
            cartorio=self.numero_ri,
        ).count()

    def descricao_ato(self):
        return str(self.ato.tipo_ato)

    @cached_property
    def protocolo(self):
        return self.pedido.protocolo

    def get_numero_protocolo(self):
        return Livro01Protocolo.objects.filter(pedido_id=self.pedido_id).values_list(
            "numero_protocolo",
            flat=True,
        )[0]

    def get_data_protocolo(self):
        return Livro01Protocolo.objects.filter(pedido_id=self.pedido_id).values_list(
            "data_protocolo",
            flat=True,
        )[0]

    @cached_property
    def get_data_selo_formatada(self):
        try:
            maior_data = SeloEletronico.objects.filter(
                pedido_item_id=self.id,
            ).aggregate(
                maior_data_selo=Max("utilizado_em"),
            )["maior_data_selo"]
        except Exception:
            maior_data = SeloEletronico.objects.filter(
                pedido_id=self.pedido_id,
            ).aggregate(
                maior_data_selo=Max("utilizado_em"),
            )["maior_data_selo"]

        # RETORNANDO A DATA FORMATADA
        if maior_data:
            return maior_data.strftime(settings.DATE_FORMAT_STR)
        else:
            return ""

    def get_data_selo(self):
        try:
            maior_data = SeloEletronico.objects.filter(
                pedido_item_id=self.id,
            ).aggregate(
                maior_data_selo=Max("utilizado_em"),
            )["maior_data_selo"]
        except Exception:
            maior_data = SeloEletronico.objects.filter(
                pedido_id=self.pedido_id,
            ).aggregate(
                maior_data_selo=Max("utilizado_em"),
            )["maior_data_selo"]

        if maior_data:
            return maior_data
        else:
            return self.get_data_protocolo()

    def get_data_registro(self):
        protocolo_id = Livro01Protocolo.objects.filter(
            pedido_id=self.pedido_id,
        ).values_list(
            "id",
            flat=True,
        )[0]
        return Livro01Andamento.objects.filtrar_andamento_data_registrado(protocolo_id)

    @cached_property
    def data_prevista(self):
        data, dias = self.pedido.get_prazo_em_dias("P")
        calendario = CalendarioBrasileiroPersonalizado()
        return calendario.add_working_days(data, dias)

    @classmethod
    # Montando o dados para o SQL
    def criar_pedido_item(
        cls,
        pedido_id,
        valor_itbi,
        valor_avaliacao,
        tipo_registro,
        numero_registro,
        emolumento_id,
        quantidade,
        numero_ri,
        numero_titulo,
        numero_ato,
        colaborador,
        ato_id,
        titulo_id,
    ) -> "PedidoItem":
        """Insere um novo item de pedido no banco de dados e retorna o ID do item inserido e a data de pagamento."""
        data_pagamento = timezone.now().date()

        emolumento = Emolumentos.obter(emolumento_id, valor_documento=valor_itbi)

        ato_numero = 0
        # valor_total = 0
        custas = 1

        pedido_item = cls.objects.create(
            pedido_id=pedido_id,
            ato_id=ato_id,
            titulo_id=titulo_id,
            colaborador=colaborador,
            tabelacalculo=emolumento_id,
            vigencia=emolumento.vigencia,
            data_pagamento=data_pagamento,
            cdhu=quantidade,
            tipo_registro=tipo_registro,
            numero_registro=numero_registro,
            numero_ri=numero_ri,
            numero_ato=numero_ato,
            codigo_tabela=emolumento.valores.codigo_tabela,
            valor_emolumento=emolumento.valores.valor_emolumento,
            valor_tfj=emolumento.valores.valor_tfj,
            valor_issqn=emolumento.valores.valor_issqn,
            valor_fundo_estado=emolumento.valores.valor_fundo_estado,
            valor_itbi=valor_itbi,
            valor_avaliacao=valor_avaliacao,
            numero_titulo=numero_titulo,
            # valor_total=valor_total,
            custas=custas,
            ato_numero=ato_numero,
        )

        print("Gravado Pedido Item:", str(pedido_item.pk))

        return pedido_item


class Livro02Texto(models.Model):
    numero_ato = models.BigIntegerField(blank=True, null=True)
    imovel = models.ForeignKey(
        Livro02,
        on_delete=models.CASCADE,
        default=0,
        null=True,
        blank=True,
    )
    pedido_item = models.ForeignKey(PedidoItem, on_delete=models.CASCADE, default=0)
    texto = CKEditor5Field(blank=True, null=True, config_name="default")
    estado_civil_texto_id = models.BigIntegerField(default=0, null=True, blank=True)

    objects: managers.Livro02TextoManager = managers.Livro02TextoManager()

    class Meta:
        verbose_name = "Texto"
        verbose_name_plural = "Textos"

    def __str__(self) -> str:
        return " ".join(
            [str(getattr(self, field.name, "")) for field in self._meta.get_fields()],
        )

    def get_absolute_url(self) -> str:
        return reverse("home:texto_lv2", args=self.imovel_id)


class NotaDevolucaoTexto(models.Model):
    numero_ato = models.BigIntegerField(null=True)
    imovel = models.ForeignKey(Livro02, on_delete=models.CASCADE, null=True, default=0)
    pedido_item = models.ForeignKey(PedidoItem, on_delete=models.CASCADE, default=0)
    pedidos = models.ForeignKey(Pedido, on_delete=models.CASCADE, default=0)
    texto = CKEditor5Field(blank=True, null=True, config_name="default")
    objects: managers.NotaDevolucaoTextoManager = managers.NotaDevolucaoTextoManager()

    class Meta:
        verbose_name = "Nota de Devolução"
        verbose_name_plural = "Notas de Devolução"

    def __str__(self) -> str:
        return self.numero_ato

    def get_absolute_url(self):
        # return reverse('texto_lv2', args=(str(self.id)))
        return reverse("home:texto_lv2_nota_devolucao")


class ProtocoloEmFase(models.Model):
    protocolos = models.BigIntegerField(blank=True, null=True)
    ordem = models.BigIntegerField(blank=True, null=True)
    TipoFaseProtocolo = models.ForeignKey(TipoFaseProtocolo, on_delete=models.CASCADE)
    data_protocolo = models.DateField()
    data_fase = models.DateField()
    qtde_dias = models.BigIntegerField(blank=True, null=True)
    status: str = models.CharField(max_length=1, blank=True, null=True)
    data_iniciou = models.DateField()
    data_finalizou = models.DateField()
    # models.ForeignKey(Livro01Protocolo, on_delete=models.CASCADE)

    objects: managers.ProtocoloEmFaseManager = managers.ProtocoloEmFaseManager()

    def __str__(self) -> str:
        field_values = []
        for field in self._meta.get_fields():
            field_values.append(str(getattr(self, field.name, "")))
        return " ".join(field_values)


class SeloEletronico(BaseModel):
    pedido_item = models.ForeignKey(
        PedidoItem,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="selo_do_pedido_item",
    )

    # pedido_certidao_item = models.BigIntegerField(blank=True, null=True)
    certidao = models.ForeignKey(
        "Certidao",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="selos_da_certidao",
    )
    codigo_sequencial_unico: str = models.CharField(max_length=8, blank=True, null=True)
    codigo_de_seguranca: str = models.CharField(max_length=16, blank=True, null=True)
    utilizado_em = models.DateField(null=True)
    cancelado_em = models.DateField(null=True)
    selo_de_consulta: str = models.CharField(
        max_length=1,
        blank=True,
        null=True,
        default=TipoSimNao.NAO,
        choices=TipoSimNao.CHOICES,
    )

    enviado_tribunal = models.BooleanField(
        default=False,
        db_index=True,
        null=True,
        blank=True,
    )

    objects: managers.SeloManager = managers.SeloManager()
    # objects = SeloManager()

    class Meta:
        verbose_name = "Selo Eletrônico"
        verbose_name_plural = "Selos Eletrônicos"

    def __str__(self) -> str:
        return f"{self.codigo_sequencial_unico}"

    @cached_property
    def numero_pedido_id(self: "SeloEletronico") -> int:
        if self.certidao:
            # return self.pedido_item.pedido.numero
            if self.certidao.imovel_id:
                return self.certidao.imovel.pedido.id
            elif self.certidao.pessoa_id:
                return self.certidao.pessoa.pedido.id
            else:
                return None
        else:
            return self.certidao

    @cached_property
    def numero_pedido(self: "SeloEletronico") -> int:
        if self.certidao:
            # return self.pedido_item.pedido.numero
            if self.certidao.imovel_id:
                return self.certidao.imovel.pedido.numero_pedido
            elif self.certidao.pessoa_id:
                return self.certidao.pessoa.pedido.numero_pedido
            else:
                return None
        else:
            return self.certidao

    @cached_property
    def protocolo(self: "SeloEletronico") -> "Livro01Protocolo":
        return self.pedido_item.protocolo if self.pedido_item else None

    # @cached_property
    # def certidao(self: "SeloEletronico") -> "Certidao":
    #     return s

    @cached_property
    def disponivel(self: "SeloEletronico") -> bool:
        return self.utilizado is False and self.cancelado_em is not None

    @cached_property
    def utilizado(self: "SeloEletronico") -> bool:
        return self.utilizado_em is not None

    @cached_property
    def data_selo_formatada(self: "SeloEletronico") -> str:
        return self.utilizado_em.strftime(settings.DATE_FORMAT_STR)

    @cached_property
    def data_selo_extenso(self: "SeloEletronico") -> str:
        return (
            helpers.exibir_data_extenso(self.utilizado_em) if self.utilizado_em else ""
        )

    @cached_property
    def ato(self: "SeloEletronico"):
        if self.protocolo:
            return self.pedido_item
        else:
            return self.certidao

    @cached_property
    def codigo_fiscal_do_ato(self: "SeloEletronico") -> str:
        if self.certidao:
            return self.certidao.tipo_certidao.codigo
        elif self.pedido_item:
            return self.pedido_item.codigo_tabela
        return None

    @cached_property
    def codigo_de_seguranca_formatado(self: "SeloEletronico") -> str:
        if not self.codigo_de_seguranca:
            return ""

        numero = somente_numeros(self.codigo_de_seguranca)

        return (
            numero[0:4] + "." + numero[4:8] + "." + numero[8:12] + "." + numero[12:16]
        )

    @cached_property
    def ano_referencia_tabela(self: "SeloEletronico") -> int:
        if self.certidao:
            return self.certidao.data_emissao.year
        elif self.pedido_item:
            return self.pedido_item.data_pagamento.year
        return None

    @cached_property
    def data_pratica_ato(self: "SeloEletronico") -> date:
        return self.pedido_item.data_pagamento

    @cached_property
    def tipo_tributacao(self: "SeloEletronico") -> int:
        return self.pedido_item.custas.outros_codigo_trib_tj

    @cached_property
    def valor_tfj(self: "SeloEletronico") -> Decimal:
        return self.pedido_item.valor_tfj

    # @cached_property
    # def protocolo(self) -> str:
    #     return self.pedido_item.protocolo

    @cached_property
    def cpf_pessoa(self: "SeloEletronico") -> str:
        if self.certidao:
            return self.certidao.cpf
        else:
            return self.protocolo.pedido.documento

    @cached_property
    def bem(self: "SeloEletronico") -> str:
        return self.pedido_item.titulo.descricao

    @cached_property
    def detalhamento_certidao(self: "SeloEletronico") -> str:
        return "outros"

    @cached_property
    def especie_certidao(self: "SeloEletronico") -> int:
        return 0

    @cached_property
    def complemento_certidao(self: "SeloEletronico") -> int:
        return 0

    @cached_property
    def nome_cartorio_origem(self: "SeloEletronico") -> str:
        return self.pedido_item.numero_ri

    @cached_property
    def valor_emolumento(self: "SeloEletronico") -> Decimal:
        if self.certidao:
            return self.certidao.emolumento_liquido_calculado
        else:
            return self.pedido_item.valor_emolumento

    @cached_property
    def nome_pessoa(self: "SeloEletronico") -> str:
        if self.certidao:
            return self.certidao.nome_solicitante
        else:
            return self.pedido_item.pedido.nome_solicitante

    @cached_property
    def folha(self) -> str:
        return self.pedido_item.numero_registro

    @cached_property
    def numero_de_ordem(self) -> str:
        return self.pedido_item.numero_ato or ""

    @cached_property
    def ordem_sequencial(self) -> str:
        return self.pedido_item.numero_ato

    @cached_property
    def valor_final_usuario(self: "SeloEletronico") -> Decimal:
        return (
            self.protocolo.valor_total_protocolo
            if self.protocolo
            else self.certidao.valor_total
            if self.certidao
            else Decimal(0.0)
        )

    @cached_property
    def tipo_de_escrituracao(self) -> int:
        return 0

    @cached_property
    def tipo_livro(self) -> int:
        return 0

    def to_xml_element(self: "SeloEletronico") -> ET.ElementTree:
        selo = ET.Element("Selo")

        ET.SubElement(selo, "CodigoSequencialUnico").text = self.codigo_sequencial_unico
        ET.SubElement(selo, "CodigoDeSeguranca").text = self.codigo_de_seguranca
        ET.SubElement(selo, "SeloConsulta").text = self.selo_de_consulta
        ET.SubElement(selo, "DataUtilizacao").text = self.utilizado_em.strftime(
            "%Y-%m-%dT%H:%M:%S",
        )

        ato = ET.SubElement(selo, "Ato")
        ET.SubElement(ato, "CodigoFiscalDoAto").text = str(self.codigo_fiscal_do_ato)
        ET.SubElement(ato, "AnoReferenciaTabela").text = str(self.ano_referencia_tabela)
        ET.SubElement(ato, "DataPraticaAto").text = self.data_pratica_ato.strftime(
            "%d-%m-%Y",
        )

        composicao_ato = ET.SubElement(selo, "ComposicaoAto")
        ET.SubElement(composicao_ato, "TipoTributacao").text = str(self.tipo_tributacao)
        ET.SubElement(composicao_ato, "ValorTFJ").text = str(self.valor_tfj)
        ET.SubElement(composicao_ato, "ValorFinalUsuario").text = str(
            self.valor_final_usuario,
        )
        ET.SubElement(composicao_ato, "Protocolo").text = str(
            (
                self.protocolo.numero_protocolo
                if self.protocolo
                else self.certidao.numero_pedido_certidao
                if self.certidao
                else "0"
            ),
        )

        if self.certidao:
            ET.SubElement(composicao_ato, "CPFPessoa").text = str(self.cpf_pessoa) or ""
            ET.SubElement(composicao_ato, "Bem").text = str(self.bem) or ""
            ET.SubElement(composicao_ato, "DetalhamentoCertidao").text = str(
                self.detalhamento_certidao,
            )
            ET.SubElement(composicao_ato, "EspecieCertidao").text = str(
                self.especie_certidao,
            )
            ET.SubElement(composicao_ato, "ComplementoCertidao").text = str(
                self.complemento_certidao,
            )
            ET.SubElement(composicao_ato, "NomeCartorioOrigem").text = (
                str(self.nome_cartorio_origem) or ""
            )

        ET.SubElement(composicao_ato, "ValorEmolumento").text = str(
            self.valor_emolumento,
        )
        ET.SubElement(composicao_ato, "NomePessoa").text = self.nome_pessoa
        ET.SubElement(composicao_ato, "Folha").text = str(self.folha) or ""
        ET.SubElement(composicao_ato, "NumeroDeOrdem").text = (
            str(self.numero_de_ordem) or ""
        )
        ET.SubElement(composicao_ato, "OrdemSequencial").text = str(
            self.ordem_sequencial,
        )
        ET.SubElement(composicao_ato, "TipoDeEscrituracao").text = str(
            self.tipo_de_escrituracao,
        )
        ET.SubElement(composicao_ato, "TipoLivro").text = str(self.tipo_livro)

        return selo

    @classmethod
    def alocar_selo_para_pedido_ou_certidao(
        cls,
        pedido,
        pedido_item_id,
        pedido_certidao_id,
        pedido_certidao_item,
        opcao,
    ) -> None:
        """Aloca um selo disponível para um pedido ou certidão, atualizando as informações relevantes."""
        selo_disponivel = SeloEletronico.objects.filtrar_proximo_disponivel()

        # Se não houver selos disponíveis, retorna ou lança uma exceção
        if not selo_disponivel:
            return

        selo = cls.objects.get(pk=selo_disponivel.id)
        if opcao == "P":
            selo.pedidos = pedido
            selo.pedido_item = pedido_item_id
        elif opcao == "C":
            selo.pedido_certidao = pedido_certidao_id
            selo.pedido_certidao_item = pedido_certidao_item

        selo.utilizado_em = timezone.now().date()
        selo.save()

    @staticmethod
    def gerar_xml_tjmg(selos, codigo_serventia) -> str:
        root = ET.Element(
            "Selos",
            {
                "xmlns": "http://notarial.tjmg.jus.br",
                "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
                "xsi:schemaLocation": "http://selos.tjmg.jus.br atospraticados.xsd",
            },
        )

        ET.SubElement(root, "CodigoServentia").text = codigo_serventia

        for selo in selos:
            xml_element = selo.to_xml_element()
            root.append(xml_element)

        return ET.tostring(root, encoding="unicode")

    @classmethod
    def criar_atualizar_selos_certidao(cls, certidao, selos) -> None:
        """CRIAR OU ATUALIZAR OS SELOS DO PEDIDO DE CERTIDAO."""
        for selo in selos:
            print("Selo atualizado: ", selo.get("CODIGO_SEQUENCIAL_UNICO", ""))

            SeloEletronico.objects.update_or_create(
                pedido_item=None,
                certidao=certidao,
                codigo_sequencial_unico=selo.get("CODIGO_SEQUENCIAL_UNICO", ""),
                codigo_de_seguranca=selo.get("CODIGO_DE_SEGURANCA", ""),
                utilizado_em=selo.get("DATA_UTILIZACAO", ""),
                cancelado_em=None,
                selo_de_consulta=selo.get("EH_SELO_PRINCIPAL", ""),
            )

    @classmethod
    def criar_atualizar_selos_protocolo(cls, selo, numero_protocolo) -> None:
        """CRIAR OU ATUALIZAR OS SELOS DO PEDIDO DE CERTIDAO."""
        print("Selo atualizado: ", selo.get("CODIGO_SEQUENCIAL_UNICO", ""))

        # VERIFICAR SE O ITEM DO PEDIDO ESTA PRESENTE NA TABELA DE PEDIDO ITEM
        pedido_item_id = selo.get("IDENTIFICACAO", "")
        pedido_item = PedidoItem.objects.filter(id=pedido_item_id).exists()

        # CASO O ITEM NAO ESTEJA PRESENTE NA TABELA DE PEDIDO ITEM
        if not pedido_item:
            protocolo = (
                Livro01Protocolo.objects.select_related("pedido")
                .filter(numero_protocolo=numero_protocolo)
                .first()
            )

            if protocolo:
                pedido_item = PedidoItem.objects.filter(pedido=protocolo.pedido).first()
                if pedido_item:
                    pedido_item_id = pedido_item.id

        SeloEletronico.objects.update_or_create(
            pedido_item_id=pedido_item_id,
            certidao=None,
            codigo_sequencial_unico=selo.get("CODIGO_SEQUENCIAL_UNICO", ""),
            codigo_de_seguranca=selo.get("CODIGO_DE_SEGURANCA", ""),
            utilizado_em=selo.get("DATA_UTILIZACAO", ""),
            cancelado_em=None,
            selo_de_consulta=selo.get("EH_SELO_PRINCIPAL", ""),
        )


class TipoAndamento(models.Model):
    id = models.BigAutoField(
        primary_key=True,
        verbose_name="ID",
        auto_created=True,
        serialize=False,
    )
    servico: str = models.CharField(
        max_length=40,
        blank=True,
        null=True,
        default="",
        db_index=True,
    )
    descricao_servico: str = models.CharField(
        max_length=250,
        blank=True,
        null=True,
        default="",
    )
    atualizar_status_protocolo: str = models.CharField(
        max_length=1,
        default=NAO,
        choices=TipoSimNao.CHOICES,
        db_index=True,
    )
    ativo: bool = models.BooleanField(
        default=True,
        db_index=True,
    )

    grupo_cancelado: str = models.CharField(
        max_length=1,
        blank=True,
        null=True,
        default=NAO,
        choices=TipoSimNao.CHOICES,
        db_index=True,
    )
    grupo_registrado: str = models.CharField(
        max_length=1,
        blank=True,
        null=True,
        default=NAO,
        choices=TipoSimNao.CHOICES,
    )
    grupo_exigencia: str = models.CharField(
        max_length=1,
        blank=True,
        null=True,
        default=NAO,
        choices=TipoSimNao.CHOICES,
        db_index=True,
    )
    grupo_cancelado_registrado: str = models.CharField(
        max_length=1,
        blank=True,
        null=True,
        default=NAO,
        choices=TipoSimNao.CHOICES,
        db_index=True,
    )
    grupo_subjudice: str = models.CharField(
        max_length=1,
        blank=True,
        null=True,
        default=NAO,
        choices=TipoSimNao.CHOICES,
        db_index=True,
    )
    grupo_reentrada: str = models.CharField(
        max_length=1,
        blank=True,
        null=True,
        default=NAO,
        choices=TipoSimNao.CHOICES,
        db_index=True,
    )
    grupo_reentrada_pagamento: str = models.CharField(
        max_length=1,
        blank=True,
        null=True,
        default=NAO,
        choices=TipoSimNao.CHOICES,
        db_index=True,
    )
    grupo_finalizado: str = models.CharField(
        max_length=1,
        blank=True,
        null=True,
        default=NAO,
        choices=TipoSimNao.CHOICES,
        db_index=True,
    )
    grupo_exigencia_positiva: str = models.CharField(
        max_length=1,
        blank=True,
        null=True,
        default=NAO,
        choices=TipoSimNao.CHOICES,
        db_index=True,
    )
    grupo_em_registro: str = models.CharField(
        max_length=1,
        blank=True,
        null=True,
        default=NAO,
        choices=TipoSimNao.CHOICES,
        db_index=True,
    )
    grupo_pronto_registrar: str = models.CharField(
        max_length=1,
        blank=True,
        null=True,
        default=NAO,
        choices=TipoSimNao.CHOICES,
        db_index=True,
    )
    grupo_distribuicao: str = models.CharField(
        max_length=1,
        blank=True,
        null=True,
        default=NAO,
        choices=TipoSimNao.CHOICES,
        db_index=True,
    )
    grupo_digitalizar: str = models.CharField(
        max_length=1,
        blank=True,
        null=True,
        default=NAO,
        choices=TipoSimNao.CHOICES,
        db_index=True,
    )
    grupo_ultimo_andamento: str = models.CharField(
        max_length=1,
        blank=True,
        null=True,
        default=SIM,
        choices=TipoSimNao.CHOICES,
        db_index=True,
    )
    grupo_servico_recebido: str = models.CharField(
        max_length=1,
        blank=True,
        null=True,
        default=SIM,
        choices=TipoSimNao.CHOICES,
        db_index=True,
    )
    grupo_reprotocolado: str = models.CharField(
        max_length=1,
        blank=True,
        null=True,
        default=NAO,
        choices=TipoSimNao.CHOICES,
        db_index=True,
    )
    grupo_recepcao: str = models.CharField(
        max_length=1,
        blank=True,
        null=True,
        default=NAO,
        choices=TipoSimNao.CHOICES,
        db_index=True,
    )

    grupo_protocolo_entregue: str = models.CharField(
        max_length=1,
        blank=True,
        null=True,
        default=NAO,
        choices=TipoSimNao.CHOICES,
        db_index=True,
    )

    requer_validacao_andamento: bool = models.BooleanField(default=False)

    objects: managers.TipoAndamentoManager = managers.TipoAndamentoManager()

    grupos: managers.TipoAndamentoGrupoManager = managers.TipoAndamentoGrupoManager()

    class Meta:
        ordering = ["servico"]
        verbose_name = "Tipo de Andamento"
        verbose_name_plural = "Tipos de Andamento"

    def __str__(self) -> str:
        return self.servico.title()

    @classmethod
    def get_prenotacao_id(cls) -> int:
        tipo_andamento = TipoAndamento.objects.filter(
            # servico__icontains="Prenota",
            grupo_recepcao="S",
        ).first()
        return tipo_andamento.id if tipo_andamento else 12

    @classmethod
    def exigencias(cls) -> QuerySet:
        return cls.objects.filter(grupo_exigencia="S")

    @classmethod
    def reentradas(cls) -> QuerySet:
        return cls.objects.filter(grupo_reentrada="S")

    @classmethod
    def get_recebido(cls) -> QuerySet:
        resultado = cls.objects.filter(grupo_servico_recebido="S").first()
        if not resultado:
            resultado = cls.objects.get_or_create(
                servico="Recebido",
                descricao_servico="Recebido",
                grupo_servico_recebido="S",
            )[0]
        return resultado

    @classmethod
    def reentrada(cls) -> Optional["TipoAndamento"]:
        return cls.objects.filter(grupo_reentrada="S").first()

    @classmethod
    def reentrada_id(cls) -> int:
        obj = cls.objects.filter(grupo_reentrada="S").first()
        return obj.id if obj else 0

    @classmethod
    def reentradas_pagamento(cls) -> QuerySet:
        return cls.objects.filter(grupo_reentrada_pagamento="S")

    @classmethod
    def reentrada_pagamento(cls) -> QuerySet:
        return cls.objects.filter(grupo_reentrada_pagamento="S").first()

    @classmethod
    def subjudices(cls) -> QuerySet:
        return cls.objects.filter(grupo_subjudice="S")

    @classmethod
    def finalizados(cls) -> QuerySet:
        return cls.objects.filter(grupo_finalizado="S")

    @classmethod
    def em_registros(cls) -> QuerySet:
        return cls.objects.filter(grupo_em_registro="S")

    @classmethod
    def prontos_registrar(cls) -> QuerySet:
        return cls.objects.filter(grupo_pronto_registrar="S")

    @classmethod
    def distribuicao(cls) -> QuerySet:
        return cls.objects.filter(grupo_distribuicao="S")

    @classmethod
    def digitalizar(cls) -> QuerySet:
        return cls.objects.filter(grupo_digitalizar="S")

    # dasda
    @classmethod
    def get_ids_para_atualizar_status(cls) -> list[int]:
        """
        Obtém os identificadores de todos os serviços em andamento que necessitam de atualização de status.

        Consulta a própria classe do modelo para encontrar todos os registros
        com a flag `atualizar_status_protocolo` configurada como "S" (Sim). Retorna uma lista
        com os campos `tipo_andamento` desses registros.

        Retorna:
            list: Lista de identificadores `tipo_andamento` para os serviços que precisam de atualização de status.
                  Retorna uma lista vazia se nenhum serviço corresponder ao critério.

        Exemplo:
            >>> TipoAndamento.get_ids_para_atualizar_status()
            [1, 2, 3]  # Ou [] se nenhum serviço necessitar de atualização de status
        """
        servicos_para_atualizar = cls.objects.filter(
            atualizar_status_protocolo="S",
        ).values_list(
            "tipo_andamento",
            flat=True,
        )

        return list(servicos_para_atualizar)


class Livro01Andamento(BaseModel):
    id = models.BigAutoField(
        primary_key=True,
        verbose_name="ID",
        auto_created=True,
        serialize=False,
    )
    protocolo = models.ForeignKey(
        Livro01Protocolo,
        on_delete=models.CASCADE,
        related_name="andamentos_do_protocolo",
    )

    colaborador = models.ForeignKey(
        Colaborador,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="colaborador",
        verbose_name="Colaborador",
        help_text="Selecione o colaborador",
    )

    tipo_andamento = models.ForeignKey(
        TipoAndamento,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="andamento_tipo",
        verbose_name="Tipo de Andamento",
        help_text="Selecione o tipo de andamento",
    )

    data: datetime = models.DateTimeField(
        db_index=True,
        blank=True,
        null=True,
        verbose_name="Data do Andamento",
    )

    colaborador_destino = models.ForeignKey(
        Colaborador,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="andamentos_do_colaborador_destino",
        verbose_name="Encaminhado Para",
    )

    arquivo_assinado = models.FileField(upload_to="andamentos/", blank=True, null=True)
    andamento_ativo: str = models.CharField(
        max_length=1,
        blank=True,
        null=True,
        default="S",
        verbose_name="Ativo",
    )
    texto = CKEditor5Field("Texto", config_name="default", blank=True, null=True)
    data_importacao: datetime = models.DateTimeField(blank=True, null=True)

    objects: managers.AndamentosManager = managers.AndamentosManager()

    exigencias = managers.ExigenciasManager()
    registrados = managers.RegistradosManager()

    class Meta:
        verbose_name = "Andamento de Protocolo"
        verbose_name_plural = "Andamentos de Protocolos"
        ordering = ["data"]

        indexes = [
            models.Index(fields=["data"]),
            models.Index(fields=["protocolo"]),
            models.Index(fields=["tipo_andamento"]),
            models.Index(fields=["protocolo", "colaborador_destino"]),
        ]

    def __str__(self) -> str:
        return f"{self.tipo_andamento.descricao_servico.title() if self.tipo_andamento else '(Não Especificado)'} | Protocolo: {self.protocolo if self.protocolo else ''} | Colab. {self.colaborador.nome if self.colaborador else 'Não Informado'} | Em: {timezone.localtime(self.data).strftime('%d-%m-%y %H:%M') if self.data else 'Não Informado'}"

    def get_absolute_url(self):
        return reverse("home:andamento_detail", args=(self.pk,))

    def get_andamento_prenotacao():
        return TipoAndamento.get_tipo_prenotacao_id()

    def reset_sequence() -> None:
        # Abre uma conexão com o banco de dados
        with connection.cursor() as cursor:
            # Executa a consulta para obter o valor máximo da coluna ID
            cursor.execute("SELECT MAX(ID) FROM PUBLIC.HOME_LIVRO01ANDAMENTO")
            max_value = cursor.fetchone()[0]

            # Verifica se max_value não é None e é maior que zero
            if max_value is not None and max_value > 0:
                # Prepara a consulta SQL para reiniciar a sequência com o próximo valor
                cursor.execute(
                    "ALTER SEQUENCE PUBLIC.HOME_LIVRO01ANDAMENTO_ID_SEQ RESTART WITH %s",
                    [max_value + 1],
                )

    @cached_property
    def servico(self):
        return self.tipo_andamento

    @cached_property
    def registrado(self) -> bool:
        return self._status_servico[0] == "S" if self._status_servico else False

    @cached_property
    def cancelado(self) -> bool:
        return self._status_servico[1] == "S" if self._status_servico else False

    @cached_property
    def finalizado(self) -> bool:
        return self._status_servico[2] == "S" if self._status_servico else False

    @cached_property
    def exigencia(self) -> bool:
        return self._status_servico[3] == "S" if self._status_servico else False

    @cached_property
    def subjudice(self) -> bool:
        return self._status_servico[4] == "S" if self._status_servico else False

    @cached_property
    def exigencia_positiva(self) -> bool:
        return self._status_servico[5] == "S" if self._status_servico else False

    @cached_property
    def em_registro(self) -> bool:
        return self._status_servico[6] == "S" if self._status_servico else False

    @cached_property
    def _status_servico(self) -> tuple[str]:
        # Busca todos os status relevantes em uma única consulta.
        return (
            TipoAndamento.objects.filter(pk=self.tipo_andamento_id)
            .values_list(
                "grupo_registrado",
                "grupo_cancelado",
                "grupo_finalizado",
                "grupo_exigencia",
                "grupo_subjudice",
                "grupo_exigencia_positiva",
                "grupo_em_registro",
            )
            .first()
        )

    @cached_property
    def status_descrito(self):
        return self.tipo_andamento.servico if self.tipo_andamento else "(Não Informado)"

    @cached_property
    def possui_exigencia(self):
        return (
            self.tipo_andamento_id in TipoAndamento.objects.get_ids_de_tipo_exigencia()
        )

    @cached_property
    def status_display(self):
        if self.registrado:
            return {"class": "badge bg-primary", "text": self.status_descrito.title()}
        elif self.cancelado:
            return {"class": "badge bg-danger", "text": self.status_descrito.title()}
        elif self.exigencia:
            return {
                "class": "badge bg-warning font-weight-bold text-dark",
                "text": self.status_descrito.title(),
            }
        elif self.subjudice:
            return {"class": "badge bg-secondary", "text": self.status_descrito.title()}
        elif self.finalizado:
            return {"class": "badge bg-success", "text": self.status_descrito.title()}
        elif self.exigencia_positiva or self.em_registro:
            return {"class": "badge bg-info", "text": self.status_descrito.title()}
        else:
            return {"class": "", "text": self.status_descrito.title()}

    @cached_property
    def modelos_de_texto(self):
        return Livro01Andamento.get_modelos_de_texto()

    @classmethod
    def get_modelos_de_texto(cls) -> QuerySet:
        modelo_texto = ModeloTexto.objects.filter(tipo__descricao="Andamento")
        if not modelo_texto:
            modelo_texto = ModeloTexto.objects.all()
        return modelo_texto if modelo_texto else None

    @cached_property
    def texto_rtf(self):
        from apps.home.utils.libreoffice import converter_html_para_rtf

        texto = ""

        with contextlib.suppress(Exception):
            texto = converter_html_para_rtf(self.texto)

        # return converter_html_para_rtf(self.texto)
        if texto:
            return texto
        else:
            return ""

    @cached_property
    def texto_pdf(self) -> io.BytesIO:
        from apps.home.services.services import converter_html_para_pdf

        try:
            pdf_bytes = converter_html_para_pdf(self.texto)
        except Exception:
            pdf_bytes = None

        return pdf_bytes

    @cached_property
    def texto_html_aprimorado(self) -> str:
        from apps.home.utils.html_utils import adicionar_head_elements_django

        body = self.texto
        styles = ["assets/css/ckeditor5/content-styles.css"]
        scripts = ["https://cdn.ckeditor.com/ckeditor5/41.3.0/classic/ckeditor.js"]

        return adicionar_head_elements_django(
            body,
            styles=styles,
            scripts=scripts,
        )

    def atualizar_colaborador(self, protocolo_id) -> None:
        Livro01Andamento.objects.filter(
            protocolo_id=protocolo_id,
            colaborador_destino_id__isnull=True,
        ).update(
            colaborador_destino_id=F("colaborador_id"),
        )

    @classmethod
    def criar_andamento_protocolo(
        cls,
        protocolo_id,
        colaborador_id,
        tipo_andamento_id,
        colaborador_encaminhado_id=None,
    ) -> "Livro01Andamento":
        # ATUALIZAR A SEQUENCE PROTOCOLO ANTES DE GERAR ANDAMENTO
        with transaction.atomic():
            cls.reset_sequence()

            obj, created = cls.objects.update_or_create(
                protocolo_id=protocolo_id,
                tipo_andamento_id=tipo_andamento_id,
                data=timezone.now(),
                colaborador_id=colaborador_id,
                defaults={
                    "colaborador_id": colaborador_id,
                    "colaborador_destino_id": colaborador_encaminhado_id,
                    "data": timezone.now(),
                },
            )

            # Atualizar o colaborador com codigo vazio
            cls.atualizar_colaborador_vazio(protocolo_id)

        return obj

    @classmethod
    def atualizar_colaborador_vazio(cls, protocolo_id) -> None:
        Livro01Andamento.objects.filter(
            protocolo=protocolo_id,
            colaborador_destino_id__isnull=True,
        ).update(
            colaborador_destino_id=F("colaborador_id"),
        )

    def encerrar_eventos(self) -> None:
        # FILTRAR OS EVENTOS DO SERVICOS ANDAMENTOS
        fase_agenda_itens_andamentos = FaseAgendaItemAndamento.objects.filter(
            tipo_andamento_id=self.tipo_andamento_id,
        )

        for evento in fase_agenda_itens_andamentos:
            titulo = f"{evento.fase_agenda.nome!s} {self.protocolo.numero_protocolo!s}"
            Event.objects.encerrar_evento_pelo_titulo(titulo=titulo, data=self.data)


class FaseAgendaItemAndamento(models.Model):
    fase_agenda = models.ForeignKey(FaseAgenda, on_delete=models.CASCADE, default=1)

    tipo_andamento = models.ForeignKey(
        TipoAndamento,
        on_delete=models.CASCADE,
        null=True,
        default=0,
    )

    class Meta:
        unique_together = ["fase_agenda", "tipo_andamento"]
        verbose_name = "Fase Agenda Item Andamento"
        verbose_name_plural = "Fase Agenda Itens Livro01Andamento"

    def __str__(self) -> str:
        return f"{self.fase_agenda} - {self.tipo_andamento}"


class ServicoLivro01(models.Model):
    descricao: str = models.CharField(max_length=40, blank=True, null=True)

    class Meta:
        verbose_name = "Serviço Livro 01"
        verbose_name_plural = "Serviços Livro 01"

    def __str__(self) -> str:
        return self.descricao


class ServicoLivro01Historico(models.Model):
    servico_livro01 = models.ForeignKey(ServicoLivro01, on_delete=models.CASCADE)
    data = models.DateField()

    class Meta:
        verbose_name = "Serviço Livro 01 Histórico"
        verbose_name_plural = "Serviços Livro 01 Histórico"

    def __str__(self) -> str:
        return (
            self.servico_livro01 + " - " + self.data.strftime(settings.DATE_FORMAT_STR)
        )

    def get_max_date(self):
        return self.servicolivro01historico_set.aggregate(max_date=Max("data"))[
            "max_date"
        ]


class EventRecorrenteFrequencia(models.Model):
    title: str = models.CharField(max_length=200, unique=True)
    start_time_01 = models.TimeField(blank=True, null=True)
    start_time_02 = models.TimeField(blank=True, null=True)
    start_time_03 = models.TimeField(blank=True, null=True)
    start_time_04 = models.TimeField(blank=True, null=True)
    start_time_05 = models.TimeField(blank=True, null=True)

    class Meta:
        verbose_name = "Frequência de Evento Recorrente"
        verbose_name_plural = "Frequências de Eventos Recorrentes"

    def __str__(self) -> str:
        return self.title


class EventRecorrente(models.Model):
    title: str = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True, null=True)
    url: str = models.CharField(max_length=200, blank=True, null=True)
    event_recorrente_frequencia = models.ForeignKey(
        EventRecorrenteFrequencia,
        on_delete=models.CASCADE,
    )

    class Meta:
        verbose_name = "Evento Recorrente"
        verbose_name_plural = "Eventos Recorrentes"

    def __str__(self) -> str:
        return self.title


class EmolumentoValor(BaseModel):
    emolumento = models.ForeignKey(
        Emolumentos,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        verbose_name="Emolumento",
        help_text="Selecione o Emolumento",
    )
    # vigencia_id = models.BigIntegerField(blank=True, null=True)
    vigencia = models.ForeignKey(
        EmolumentoAno,
        default=Emolumentos.get_vigencia_atual_id,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        verbose_name="Vigencia",
        help_text="Selecione a vigencia de emolumentos",
    )
    # descricao:str = models.CharField(
    #     max_length=50,
    #     default="Emolumento",
    #     blank=True,
    #     null=True,
    #     verbose_name="Descrição",
    #     help_text="Descrição do emolumento",
    # )
    codigo_tabela: str = models.CharField(
        max_length=10,
        default="",
        blank=True,
        null=True,
        verbose_name="Código o item na Tabela de Emolumentos",
        help_text="Informa o código do item da tabela de emolumentos. Ex. 4701-9",
    )
    faixa_inicio = models.DecimalField(
        blank=False,
        decimal_places=2,
        max_digits=12,
        default=0.0,
        null=True,
        verbose_name="Faixa Inicio",
        help_text="Valor inicial da faixa de emolumentos",
    )
    faixa_fim = models.DecimalField(
        blank=False,
        decimal_places=2,
        max_digits=12,
        default=9999999999.99,
        null=True,
        verbose_name="Faixa Fim",
        help_text="Valor final da faixa de emolumentos",
    )
    valor_fundo_estado = models.DecimalField(
        blank=False,
        decimal_places=2,
        max_digits=12,
        default=0.0,
        null=True,
        verbose_name="RECOMPE",
    )
    # taxa1
    percentual_issqn = models.DecimalField(
        blank=False,
        decimal_places=2,
        max_digits=12,
        default=0.0,
        null=True,
        verbose_name="% ISSQN",
    )
    valor_taxa2 = models.DecimalField(
        blank=False,
        decimal_places=2,
        max_digits=12,
        default=0.0,
        null=True,
    )
    valor_taxa3 = models.DecimalField(
        blank=False,
        decimal_places=2,
        max_digits=12,
        default=0.0,
        null=True,
    )
    valor_taxa4 = models.DecimalField(
        blank=False,
        decimal_places=2,
        max_digits=12,
        default=0.0,
        null=True,
    )
    valor_emolumento = models.DecimalField(
        blank=False,
        decimal_places=2,
        max_digits=12,
        default=0.0,
        null=True,
        verbose_name="Valor Emolumento Liquido",
    )
    valor_tfj = models.DecimalField(
        blank=False,
        decimal_places=2,
        max_digits=12,
        default=0.0,
        null=True,
        verbose_name="TFJ",
        help_text="Taxa de Fiscalização Judiciária",
    )
    valor_adicionado_2 = models.DecimalField(
        blank=False,
        decimal_places=2,
        max_digits=12,
        default=0.0,
        null=True,
        verbose_name="RECOMPE 2",
    )
    chave_emolumentos = models.BigIntegerField(default=0, blank=True, null=True)

    objects: managers.EmolumentoValorManager = managers.EmolumentoValorManager()

    class Meta:
        verbose_name = "Emolumento Valor"
        verbose_name_plural = "Emolumentos Valores"

    def __str__(self) -> str:
        return str(self.descricao)

    @cached_property
    def descricao(self) -> str:
        if self.emolumento:
            return self.emolumento.descricao
        elif self.codigo_tabela:
            tipo_emolumento_em_pedido = self.get_tipo_emolumento_em_pedidos()
            return (
                tipo_emolumento_em_pedido.descricao
                if tipo_emolumento_em_pedido
                else "Não Informado"
            )
        return "Não Informado"

    @cached_property
    def valor_issqn(self) -> Decimal:
        return (
            safe_decimal((self.percentual_issqn / 100) * self.valor_emolumento)
            if self.percentual_issqn
            else Decimal(0.0)
        )

    @cached_property
    def valor_total(self) -> Decimal:
        return (
            self.valor_emolumento
            + self.valor_fundo_estado
            + self.valor_issqn
            + self.valor_tfj
        )

    @classmethod
    def get_provisorio(cls) -> "EmolumentoValor":
        print("Obtendo emolumento provisório.")
        obj, created = cls.objects.get_or_create(
            emolumento_id=Emolumentos.get_emolumento_provisorio_id(),
            vigencia=Emolumentos.get_vigencia_atual(),
            valor_fundo_estado=Decimal(0.0),
            percentual_issqn=Decimal(0.0),
            valor_taxa2=Decimal(0.0),
            valor_taxa3=Decimal(0.0),
            valor_taxa4=Decimal(0.0),
            valor_emolumento=Decimal(0.0),
            valor_tfj=Decimal(0.0),
            valor_adicionado_2=Decimal(0.0),
        )
        return obj

    def get_tipo_emolumento_em_pedidos(self) -> TipoEmolumento:
        return TipoEmolumento.objects.filter(home_emolumento_id=self.id).first()


class FinanceiroPeriodicidade(models.Model):
    # id = models.BigIntegerField(primary_key=True, default=0)
    descricao: str = models.CharField(max_length=500, blank=True, null=True)
    quantidade_dias = models.BigIntegerField(null=True, default=1)

    def __str__(self) -> str:
        return self.descricao

    @classmethod
    def criar_padroes(cls) -> None:
        cls.objects.get_or_create(id=1, descricao="Única", quantidade_dias=1)
        cls.objects.get_or_create(id=2, descricao="Semanal", quantidade_dias=1)
        cls.objects.get_or_create(id=3, descricao="Quinzenal", quantidade_dias=1)
        cls.objects.get_or_create(id=4, descricao="Mensal", quantidade_dias=1)
        cls.objects.get_or_create(id=5, descricao="Semestral", quantidade_dias=1)
        cls.objects.get_or_create(id=6, descricao="Anual", quantidade_dias=1)


class FinanceiroBase(models.Model):
    pedido = models.ForeignKey(
        Pedido,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="Pedido",
        related_name="%(class)s_registros_financeiros_do_pedido",
    )
    data_transacao: datetime = models.DateTimeField(
        default=timezone.now,
        verbose_name="Data da Transação",
    )
    descricao: str = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name="Descrição",
    )

    tipotransacao = models.BigIntegerField(
        default=1,
        blank=True,
        null=True,
        verbose_name="Tipo de Transação",
        help_text="Informe o tipo de transação. Ex. Despesa, Receita, etc.",
    )
    tipodocumento = models.BigIntegerField(
        default=1,
        blank=True,
        null=True,
        verbose_name="Tipo de Documento",
    )
    valor_transacao = models.DecimalField(
        blank=False,
        decimal_places=2,
        default=0,
        max_digits=12,
        null=True,
        verbose_name="Valor da Transação",
    )
    cheque: str = models.CharField(
        max_length=25,
        blank=True,
        null=True,
        verbose_name="Cheque",
    )
    pedido_certidao_id: str = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="Pedido Certidão",
    )
    colaborador = models.ForeignKey(
        Colaborador,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="Colaborador",
    )
    numero_protocolo_ec = models.BigIntegerField(null=True)
    numero_pedido_certidao: str = models.CharField(
        max_length=100,
        null=True,
        blank=True,
    )

    colaborador_confirmado = models.ForeignKey(
        Colaborador,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="%(class)s_colaborador_confirmado",
        verbose_name="Colaborador Confirmado",
    )

    dadp: str = models.CharField(
        max_length=1,
        blank=True,
        null=True,
        default=TipoSimNao.NAO,
        choices=TipoSimNao.CHOICES,
        verbose_name="DADP",
    )

    imposto_renda: str = models.CharField(
        max_length=1,
        blank=True,
        null=True,
        default=TipoSimNao.NAO,
        choices=TipoSimNao.CHOICES,
        verbose_name="Imposto de Renda",
    )

    tipo_transacao = models.ForeignKey(
        TipoTransacaoFinanceira,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        default=1,
        verbose_name="Tipo de Transação",
        help_text="Informe a transação financeira. Ex. Receita, Despesa, etc.",
    )

    tipo_operacao_financeira = models.ForeignKey(
        TipoOperacaoFinanceira,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        default=1,
        verbose_name="Forma de Pagamento",
        help_text="Dinheiro, Cartão Crédito, Pix, Cartão Crédito, Transferência Bancária etc.",
    )

    tipo_categoria_financeira = models.ForeignKey(
        TipoCategoriaFinanceira,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        default=1,
        verbose_name="Tipo de Categoria Financeira",
        help_text="Informe a categoria financeira. Ex. Abertura de Caixa, Protocolo, Certidao, etc.",
    )

    ativo: str = models.CharField(
        max_length=1,
        blank=True,
        null=True,
        default=TipoAtivoCancelado.ATIVO,
        choices=TipoAtivoCancelado.CHOICES,
        verbose_name="Ativo",
        help_text="Informe se a transação está ativa ou cancelada",
    )

    data_transacao_cancelado: datetime = models.DateTimeField(null=True)
    valor_transacao_cancelado = models.DecimalField(
        default=0,
        blank=False,
        decimal_places=2,
        null=True,
        max_digits=12,
    )
    colaborador_transacao_cancelado = models.ForeignKey(
        Colaborador,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="%(class)s_colaborador_transacao_cancelado",
        verbose_name="Colaborador Transacao Cancelado",
    )
    descricao_cancelado: str = models.CharField(max_length=500, blank=True, null=True)
    numero_parcela = models.BigIntegerField(null=True, default=1)
    quantidade_parcela = models.BigIntegerField(null=True, default=1)
    data_original_transacao: datetime = models.DateTimeField(default=timezone.now)
    nome_interessado: str = models.CharField(max_length=200, blank=True, null=True)
    data_transacao_colaborador_confirmado: datetime = models.DateTimeField(null=True)

    history: AuditlogHistoryField = AuditlogHistoryField()

    objects: managers.FinanceiroManager = managers.FinanceiroManager()

    class Meta:
        # indice para pedido_certidao_id
        indexes = [
            models.Index(fields=["pedido_certidao_id"]),
            models.Index(fields=["numero_pedido_certidao"]),
            models.Index(fields=["data_transacao"]),
        ]
        abstract = True

    def __str__(self) -> str:
        return f"{self.id} - {self.descricao} - {self.valor_transacao} - {self.data_transacao} - {self.pedido}"

    def get_absolute_url(self) -> str:
        return reverse("home:financeiro_detalhe", args=(self.pk,))

    def get_recibo_url(self) -> str:
        return reverse("home:financeiro_recibo_print", args=(self.pk,))

    def get_protocolo_url(self) -> str:
        protocolo = self.pedido.protocolo
        return protocolo.get_absolute_url() if self.pedido else ""

    def get_pedido_certidao_url(self) -> str:
        pedido_certidao = models_certidoes.PedidoCertidao.objects.filter(
            id=self.pedido_certidao_id,
        ).first()
        return pedido_certidao.get_absolute_url() if pedido_certidao else ""

    def exportar_para_firebird():
        from apps.home.services.firebird import exportar_financeiro

        exportar_financeiro()

    def descricao_dinamica(self) -> str:
        if self.protocolo:
            return f"{self.protocolo} Nº {self.protocolo.numero_protocolo}"
        return None

    @classmethod
    def ajustar_sequence(cls) -> None:
        ajustar_sequence("home_financeiro", "home_financeiro_id_seq")

    @classmethod
    def calcular_somas(cls, queryset):
        """
        Calcula as somas das diferentes transações financeiras.

        :param queryset: Queryset de Financeiro
        :return: Dicionário com as somas das receitas, despesas, saídas e devoluções
        """
        return queryset.aggregate(
            receitas=Sum(
                Case(
                    When(
                        tipo_transacao__descricao=TipoTransacaoFinanceira.RECEITA,
                        then="valor_transacao",
                    ),
                    default=Value(0),
                    output_field=IntegerField(),
                ),
            ),
            despesas=Sum(
                Case(
                    When(
                        tipo_transacao__descricao=TipoTransacaoFinanceira.DESPESA,
                        then="valor_transacao",
                    ),
                    default=Value(0),
                    output_field=IntegerField(),
                ),
            ),
            saidas=Sum(
                Case(
                    When(
                        tipo_transacao__descricao=TipoTransacaoFinanceira.SAIDA,
                        then="valor_transacao",
                    ),
                    default=Value(0),
                    output_field=IntegerField(),
                ),
            ),
            devolucoes=Sum(
                Case(
                    When(
                        tipo_transacao__descricao=TipoTransacaoFinanceira.DEVOLUCAO,
                        then="valor_transacao",
                    ),
                    default=Value(0),
                    output_field=IntegerField(),
                ),
            ),
        )

    @classmethod
    def receber_pedido_certidao(cls, pedido_certidao: "PedidoCertidao") -> None:
        cls.objects.update_or_create(
            pedido_certidao_id=pedido_certidao.id,
            defaults={
                "valor_transacao": pedido_certidao.total_pedido,
                "tipo_transacao_id": TipoTransacaoFinanceira.get_receita().id,
                "colaborador_id": pedido_certidao.criado_por_id,
                "descricao": f"Pedido Certidão Nº {pedido_certidao.numero_pedido}",
            },
        )

    # SALVANDO NO CAIXA - PEDIDO DE CERTIDAO
    @classmethod
    def receber_pedido_certidao_caixa(
        cls,
        pedido_certidao: "PedidoCertidao",
        valor_transacao,
        tipo_operacao_financeira_id,
        tipo_transacao_id,
        descricao,
        nome_pagador,
        data_original,
        colaborador_financeiro_id,
    ) -> None:
        # ATUALIZAR A SEQUENCE ANTES DE GRAVAR
        with transaction.atomic(), FbConnection() as db:
            db.begin_transaction()
            caixa_id = db.sequence("CAIXA_SEQ").proximo
            while cls.objects.filter(id=caixa_id).exists():
                caixa_id = db.sequence("CAIXA_SEQ").proximo
            db.commit()

            print("Caixa Seq Firebird:", caixa_id)

            cls.objects.create(
                id=caixa_id,
                pedido_certidao_id=pedido_certidao.pk,
                numero_pedido_certidao=pedido_certidao.numero_pedido,
                valor_transacao=valor_transacao,
                tipo_operacao_financeira_id=tipo_operacao_financeira_id,
                tipo_transacao_id=tipo_transacao_id,
                # colaborador_id=pedido_certidao.criado_por_id,
                colaborador_id=colaborador_financeiro_id,
                descricao=descricao,
                nome_interessado=nome_pagador,
                data_original_transacao=data_original,
            )

            # AJUSTAR A SEQUENCE DO POSTGRESQL
            cls.ajustar_sequence()

    # SALVANDO NO CAIXA - PROTOCOLO
    @classmethod
    def receber_protocolo_caixa(
        cls,
        protocolo: "Livro01Protocolo",
        valor_transacao,
        tipo_operacao_financeira_id,
        tipo_transacao_id,
        descricao,
        nome_pagador,
        data_original,
        colaborador_financeiro_id,
    ) -> None:
        # ATUALIZAR A SEQUENCE ANTES DE GRAVAR
        with transaction.atomic(), FbConnection() as db:
            db.begin_transaction()
            caixa_id = db.sequence("CAIXA_SEQ").proximo
            while cls.objects.filter(id=caixa_id).exists():
                caixa_id = db.sequence("CAIXA_SEQ").proximo
            db.commit()

            print("Caixa Seq Firebird:", caixa_id)

            cls.objects.create(
                id=caixa_id,
                pedido_id=protocolo.pedido_id,
                valor_transacao=valor_transacao,
                tipo_operacao_financeira_id=tipo_operacao_financeira_id,
                tipo_transacao_id=tipo_transacao_id,
                colaborador_id=colaborador_financeiro_id,
                descricao=descricao,
                nome_interessado=nome_pagador,
                data_original_transacao=data_original,
            )

            # AJUSTAR A SEQUENCE DO POSTGRESQL
            cls.ajustar_sequence()

    # # SALVANDO NO CAIXA
    # @classmethod
    # def gravar_pagamento_caixa_protocolo(cls, pedido_id, descricao, valor_transacao, colaborador_id) -> None:
    #     print("GRAVANDO NO CAIXA")

    #     # SALVANDO NO CAIXA
    #     cls.objects.create(
    #         pedidos=pedido_id,
    #         data_transacao=timezone.now(),
    #         descricao=descricao,
    #         tipotransacao=TipoTransacao.CREDITO,
    #         tipodocumento=1,
    #         valor_transacao=valor_transacao,
    #         colaborador_id=colaborador_id,
    #     )

    @classmethod
    def criar_financeiro(
        cls,
        pedido_id: int,
        valor: Decimal,
        colaborador_id: int,
        descricao: str,
    ) -> "Financeiro":
        with transaction.atomic():
            cls.ajustar_sequence()

            financeiro, created = cls.objects.update_or_create(
                pedido_id=pedido_id,
                data_transacao=timezone.now(),
                valor_transacao=valor,
                defaults={
                    "descricao": descricao,
                    "tipotransacao": 1,
                    "tipodocumento": 1,
                    "colaborador_id": colaborador_id,
                },
            )
            return financeiro

    @classmethod
    def criar_financeiro_despesa_receita(
        cls,
        pedido_id: int,
        pedido_certidao_id: int,
        tipo_transacao_id: int,
        tipo_categoria_financeira_id: int,
        tipo_operacao_financeira_id: int,
        colaborador_id: int,
        colaborador_confirmado_id: int,
        data_transacao: datetime,
        data_original_transacao: datetime,
        valor_transacao: Decimal,
        dadp: str,
        imposto_renda: str,
        descricao: str,
        quantidade_parcelas: int,
        recorrencia_id: int,
        user_id: int,
    ) -> "Financeiro":
        with transaction.atomic():
            cls.ajustar_sequence()

            # VERIFICAR QUANTIDADE DE RECORRENCIA
            if not FinanceiroPeriodicidade.objects.exists():
                FinanceiroPeriodicidade.criar_padroes()
                print("Cadastrar Recorrencia ")

            # BUSCAR A RECORRENCIA
            try:
                dias_adicionar = FinanceiroPeriodicidade.objects.get(
                    id=recorrencia_id,
                ).quantidade_dias
                dias_adicionar = int(dias_adicionar)
            except FinanceiroPeriodicidade.DoesNotExist:
                print("Erro ao criar recorrencia_id: ", str(recorrencia_id))
                dias_adicionar = 1
            except (ValueError, TypeError):
                print("Erro de valor do recorrencia_id: ", str(recorrencia_id))
                dias_adicionar = 1

            # ATUALIZAR A QUANTIDADE DE PARCELAS
            quantidade_parcelas_interar = int(quantidade_parcelas) + 1

            # ATUALIZAR A DATA DE TRANSAÇÃO
            data_transacao = datetime.strptime(data_transacao, "%Y-%m-%d").date()

            # VERIFICAR SE É PARCELADO E ADICIONAR AS PARCELAS
            for numero_parcela in range(1, quantidade_parcelas_interar):
                financeiro, created = cls.objects.update_or_create(
                    # financeiro, created = cls.objects.create(
                    pedido_id=pedido_id,
                    pedido_certidao_id=pedido_certidao_id,
                    tipo_transacao_id=tipo_transacao_id,
                    tipo_categoria_financeira_id=tipo_categoria_financeira_id,
                    tipo_operacao_financeira_id=tipo_operacao_financeira_id,
                    colaborador_id=user_id,
                    colaborador_confirmado_id=colaborador_confirmado_id,
                    data_transacao=data_transacao,
                    data_original_transacao=data_transacao,
                    valor_transacao=valor_transacao,
                    dadp=dadp,
                    imposto_renda=imposto_renda,
                    descricao=descricao,
                    numero_parcela=numero_parcela,
                    quantidade_parcela=quantidade_parcelas,
                )

                if created:
                    print("Salvo no caixa")

                # Adicionar os dias para a próxima parcela
                data_transacao = data_transacao + timedelta(days=dias_adicionar)
                data_transacao = helpers.get_data_util_em_x_dias(
                    data=data_transacao,
                    dias=0,
                )

            return financeiro

    @classmethod
    def criar_financeiro_despesa_receita_pelo_id(
        cls,
        pk: int,
        pedido_id: int,
        pedido_certidao_id: int,
        tipo_transacao_id: int,
        tipo_categoria_financeira_id: int,
        tipo_operacao_financeira_id: int,
        colaborador_id: int,
        colaborador_confirmado_id: int,
        data_transacao: datetime,
        data_original_transacao: datetime,
        valor_transacao: Decimal,
        dadp: str,
        imposto_renda: str,
        descricao: str,
        quantidade_parcelas: int,
        recorrencia_id: int,
        user_id: int,
    ) -> "Financeiro":
        with transaction.atomic():
            cls.ajustar_sequence()

            # VERIFICAR QUANTIDADE DE RECORRENCIA
            if not FinanceiroPeriodicidade.objects.exists():
                FinanceiroPeriodicidade.criar_padroes()
                print("Cadastrar Recorrencia ")

            # BUSCAR A RECORRENCIA
            try:
                dias_adicionar = FinanceiroPeriodicidade.objects.get(
                    id=recorrencia_id,
                ).quantidade_dias
                dias_adicionar = int(dias_adicionar)
            except FinanceiroPeriodicidade.DoesNotExist:
                print("Erro ao criar recorrencia_id: ", str(recorrencia_id))
                dias_adicionar = 1
            except (ValueError, TypeError):
                print("Erro de valor do recorrencia_id: ", str(recorrencia_id))
                dias_adicionar = 1

            # ATUALIZAR A QUANTIDADE DE PARCELAS
            quantidade_parcelas_interar = int(quantidade_parcelas) + 1

            # ATUALIZAR A DATA DE TRANSAÇÃO
            data_transacao = datetime.strptime(data_transacao, "%Y-%m-%d").date()

            # if tipo_transacao_id = 1 e RECEITA e valor menor que zero e uma devolucao
            if (
                tipo_transacao_id == TipoTransacaoFinanceira.get_receita().id
                and valor_transacao < 0
            ):
                tipo_transacao_id = TipoTransacaoFinanceira.devolucao_id()
                tipo_operacao_financeira_id = TipoOperacaoFinanceira.devolucao_id()
                print("Devolucao")

            # VERIFICAR SE É PARCELADO E ADICIONAR AS PARCELAS
            for numero_parcela in range(1, quantidade_parcelas_interar):
                # if not Financeiro.objects.filter(id=id).exists():
                financeiro, created = cls.objects.update_or_create(
                    id=pk,
                    defaults={
                        "pedido_id": pedido_id,
                        "pedido_certidao_id": pedido_certidao_id,
                        "numero_pedido_certidao": pedido_certidao_id,
                        "tipo_transacao_id": tipo_transacao_id,
                        "tipo_categoria_financeira_id": tipo_categoria_financeira_id,
                        "tipo_operacao_financeira_id": tipo_operacao_financeira_id,
                        "colaborador_id": user_id,
                        "colaborador_confirmado_id": colaborador_confirmado_id,
                        "data_transacao": data_transacao,
                        "valor_transacao": valor_transacao,
                        "dadp": dadp,
                        "imposto_renda": imposto_renda,
                        "descricao": descricao,
                        "numero_parcela": numero_parcela,
                        "quantidade_parcela": quantidade_parcelas,
                    },
                )

                if created:
                    print("Um novo registro foi criado caixa.")
                else:
                    print("O registro existente foi atualizado caixa.")

                # Adicionar os dias para a próxima parcela
                data_transacao = data_transacao + timedelta(days=dias_adicionar)
                data_transacao = helpers.get_data_util_em_x_dias(
                    data=data_transacao,
                    dias=0,
                )

    @classmethod
    def get_financeiro_diario(
        cls,
        colaborador_id: int,
        start_date: date,
        end_date: date,
        tipo_categoria_financeira=None,  # Adicionando o parâmetro opcional
    ) -> QuerySet:
        # PESQUISAR PELO COLABORADOR
        financeiro_diario = Financeiro.objects.filter(
            data_transacao__range=[start_date, end_date],
        )

        if colaborador_id:
            financeiro_diario = financeiro_diario.filter(
                colaborador_id=colaborador_id,
            )

        if tipo_categoria_financeira:
            financeiro_diario = financeiro_diario.filter(
                tipo_categoria_financeira=tipo_categoria_financeira,
            )

        return financeiro_diario.order_by("id")

    @classmethod
    def get_financeiro_total_despesa(
        cls,
        colaborador_id: int,
        start_date: date,
        end_date: date,
        tipo_categoria_financeira=None,
    ) -> dict:
        financeiro_total_despesa = Financeiro.objects.filter(
            data_transacao__range=[start_date, end_date],
            tipo_transacao_id=2,
        )

        if colaborador_id:
            financeiro_total_despesa = financeiro_total_despesa.filter(
                colaborador_id=colaborador_id,
            )

        if tipo_categoria_financeira:
            financeiro_total_despesa = financeiro_total_despesa.filter(
                tipo_categoria_financeira=tipo_categoria_financeira,
            )

        return financeiro_total_despesa.aggregate(total_despesa=Sum("valor_transacao"))

    @classmethod
    def get_financeiro_total_receita(
        cls,
        colaborador_id,
        start_date,
        end_date,
        tipo_categoria_financeira=None,
    ) -> dict:
        financeiro_total_receita = Financeiro.objects.filter(
            data_transacao__range=[start_date, end_date],
            tipo_transacao_id=1,
        )

        if colaborador_id:
            financeiro_total_receita = financeiro_total_receita.filter(
                colaborador_id=colaborador_id,
            )

        if tipo_categoria_financeira:
            financeiro_total_receita = financeiro_total_receita.filter(
                tipo_categoria_financeira=tipo_categoria_financeira,
            )

        return financeiro_total_receita.aggregate(total_receita=Sum("valor_transacao"))

    @classmethod
    def get_financeiro_total_saidas(
        cls,
        colaborador_id,
        start_date,
        end_date,
        tipo_categoria_financeira=None,
    ) -> dict:
        financeiro_total_saidas = Financeiro.objects.filter(
            data_transacao__range=[start_date, end_date],
            tipo_transacao_id=3,
        )

        if colaborador_id:
            financeiro_total_saidas = financeiro_total_saidas.filter(
                colaborador_id=colaborador_id,
            )

        if tipo_categoria_financeira:
            financeiro_total_saidas = financeiro_total_saidas.filter(
                tipo_categoria_financeira=tipo_categoria_financeira,
            )

        return financeiro_total_saidas.aggregate(total_saidas=Sum("valor_transacao"))

    @classmethod
    def get_pedidos_certidao_nao_confirmados_caixa(
        cls,
        start_date,
        end_date,
    ) -> list:
        """LISTA DE PEDIDOS DE CERTIDAO NAO CONFIRMADOS NO CAIXA."""
        # PEGAR DO CAIXA OS PEDIDO DE CERTIDAO NA DATA
        financeiro_certidao = Financeiro.objects.filter(
            data_transacao__range=[start_date, end_date],
        ).exclude(pedido_certidao_id__isnull=True)

        # Obter apenas os IDs de pedido de certidão confirmados no caixa como inteiros
        financeiro_certidao_ids = list(
            map(int, financeiro_certidao.values_list("pedido_certidao_id", flat=True)),
        )

        # PEGAR TODOS OS PEDIDOS DE CERTIDAO NAO CONFIRMADOS NO CAIXA NA DATA
        if financeiro_certidao_ids:
            pedidos_certidao_nao_confirmados = (
                models_certidoes.PedidoCertidao.objects.filter(
                    data_entrada__range=[start_date, end_date],
                ).exclude(id__in=financeiro_certidao_ids)
            )
        else:
            pedidos_certidao_nao_confirmados = (
                models_certidoes.PedidoCertidao.objects.filter(
                    data_entrada__range=[start_date, end_date],
                )
            )

        # RETORNAR OS NUMEROS DOS PEDIDOS NAO CONFIRMADOS AIND
        if pedidos_certidao_nao_confirmados:
            # Obter a lista de numeros de pedidos de certidão não confirmados
            numeros_pedidos = pedidos_certidao_nao_confirmados.values_list(
                "numero_pedido",
                flat=True,
            )

            # Retornar a lista de números de pedidos separados por vírgula
            return ", ".join(map(str, numeros_pedidos))
        else:
            return None

    @classmethod
    def get_pedidos_protocolo_nao_confirmados_caixa(
        cls,
        start_date,
        end_date,
    ) -> list:
        """LISTA DE PEDIDOS DE PROTOCOLO NAO CONFIRMADOS NO CAIXA."""
        # PEGAR DO CAIXA OS PROTOCOLO NA DATA
        financeiro_protocolo = Financeiro.objects.filter(
            data_transacao__range=[start_date, end_date],
        ).exclude(pedido_id__isnull=True)

        # Obter apenas os IDs de pedido de certidão confirmados no caixa como inteiros
        financeiro_protocolo_ids = list(
            map(int, financeiro_protocolo.values_list("pedido_id", flat=True)),
        )

        # PEGAR TODOS OS PEDIDOS DE CERTIDAO NAO CONFIRMADOS NO CAIXA NA DATA
        if financeiro_protocolo_ids:
            pedidos_protocolo_nao_confirmados = Livro01Protocolo.objects.filter(
                data_protocolo__range=[start_date, end_date],
            ).exclude(pedido_id__in=financeiro_protocolo_ids)
        else:
            pedidos_protocolo_nao_confirmados = Livro01Protocolo.objects.filter(
                data_protocolo__range=[start_date, end_date],
            )

        # RETORNAR OS NUMEROS DOS PEDIDOS NAO CONFIRMADOS AIND
        if pedidos_protocolo_nao_confirmados:
            # Obter a lista de numeros de pedidos de certidão não confirmados
            numeros_pedidos = pedidos_protocolo_nao_confirmados.values_list(
                "numero_protocolo",
                flat=True,
            )

            # Retornar a lista de números de pedidos separados por vírgula
            return ", ".join(map(str, numeros_pedidos))
        else:
            return None

    @classmethod
    def get_financeiro_total_devolucoes_dinheiro(
        cls,
        colaborador_id,
        start_date,
        end_date,
        tipo_categoria_financeira=None,
    ) -> dict:
        if colaborador_id:
            financeiro_total_devolucoes_dinheiro = Financeiro.objects.filter(
                data_transacao__range=[start_date, end_date],
                tipo_operacao_financeira_id=1,
                tipo_transacao_id=3,
                colaborador_id=colaborador_id,
            )
        else:
            financeiro_total_devolucoes_dinheiro = Financeiro.objects.filter(
                data_transacao__range=[start_date, end_date],
                tipo_operacao_financeira_id=1,
                tipo_transacao_id=3,
            )

        if tipo_categoria_financeira:
            financeiro_total_devolucoes_dinheiro = (
                financeiro_total_devolucoes_dinheiro.filter(
                    tipo_categoria_financeira=tipo_categoria_financeira,
                )
            )

        return financeiro_total_devolucoes_dinheiro.aggregate(
            total_devolucoes_dinheiro=Sum("valor_transacao"),
        )

    @classmethod
    def get_financeiro_total_caixa(
        cls,
        colaborador_id,
        start_date,
        end_date,
        tipo_categoria_financeira=None,
    ) -> dict:
        financeiro_total_caixa = Financeiro.objects.filter(
            data_transacao__range=[start_date, end_date],
        )

        if colaborador_id:
            financeiro_total_caixa = financeiro_total_caixa.filter(
                colaborador_id=colaborador_id,
            )

        if tipo_categoria_financeira:
            financeiro_total_caixa = financeiro_total_caixa.filter(
                tipo_categoria_financeira=tipo_categoria_financeira,
            )

        return financeiro_total_caixa.aggregate(total_caixa=Sum("valor_transacao"))

    @classmethod
    def get_financeiro_total_abertura_caixa(
        cls,
        colaborador_id: int,
        start_date: date,
        end_date: date,
        tipo_categoria_financeira=None,
    ) -> dict:
        financeiro_total_abertura_caixa = Financeiro.objects.filter(
            data_transacao__range=[start_date, end_date],
            tipo_categoria_financeira_id=4,
        )

        if colaborador_id:
            financeiro_total_abertura_caixa = financeiro_total_abertura_caixa.filter(
                colaborador_id=colaborador_id,
            )

        if tipo_categoria_financeira:
            financeiro_total_abertura_caixa = financeiro_total_abertura_caixa.filter(
                tipo_categoria_financeira=tipo_categoria_financeira,
            )

        return financeiro_total_abertura_caixa.aggregate(
            total_abertura_caixa=Sum("valor_transacao"),
        )

    @classmethod
    def get_financeiro_total_agrupado(
        cls,
        colaborador_id,
        start_date,
        end_date,
        tipo_categoria_financeira=None,
    ) -> QuerySet:
        # Realize a consulta agrupando por 'tipotransacao' e somando 'valor_transacao'
        if colaborador_id:
            financeiro_total_agrupado = (
                Financeiro.objects.filter(
                    data_transacao__range=[start_date, end_date],
                    colaborador_id=colaborador_id,
                )
                .values("tipo_operacao_financeira")
                .annotate(total_caixa=Sum("valor_transacao"))
                .annotate(
                    operacao_financeira_descricao=F(
                        "tipo_operacao_financeira__descricao",
                    ),
                )
                .order_by(
                    "tipo_operacao_financeira__ordem_exibir",
                )  # Adiciona a ordenação aqui
            )

            (
                financeiro_total_agrupado_despesa_saida_grupo_1,
                financeiro_total_agrupado_despesa_saida_grupo_2,
                financeiro_total_agrupado_despesa_saida_grupo_3,
            ) = (
                None,
                None,
                None,
            )
        else:
            financeiro_total_agrupado = (
                Financeiro.objects.filter(
                    data_transacao__range=[start_date, end_date],
                    valor_transacao__gt=0,
                )
                .values("tipo_operacao_financeira")
                .annotate(total_caixa=Sum("valor_transacao"))
                .annotate(
                    operacao_financeira_descricao=F(
                        "tipo_operacao_financeira__descricao",
                    ),
                )
                .order_by(
                    "tipo_operacao_financeira__ordem_exibir",
                )  # Adiciona a ordenação aqui
            )

            financeiro_total_agrupado_despesa_saida_grupo_1 = (
                Financeiro.objects.filter(
                    data_transacao__range=[start_date, end_date],
                    valor_transacao__lt=0,
                    tipo_operacao_financeira__valor_default_transacao=1,
                )
                .values("tipo_operacao_financeira")
                .annotate(total_caixa=Sum("valor_transacao"))
                .annotate(
                    operacao_financeira_descricao=F(
                        "tipo_operacao_financeira__descricao",
                    ),
                )
                .order_by(
                    "tipo_operacao_financeira__ordem_exibir",
                )  # Adiciona a ordenação aqui
            )

            financeiro_total_agrupado_despesa_saida_grupo_2 = (
                Financeiro.objects.filter(
                    data_transacao__range=[start_date, end_date],
                    valor_transacao__lt=0,
                    tipo_operacao_financeira__valor_default_transacao=2,
                )
                .values("tipo_operacao_financeira")
                .annotate(total_caixa=Sum("valor_transacao"))
                .annotate(
                    operacao_financeira_descricao=F(
                        "tipo_operacao_financeira__descricao",
                    ),
                )
                .order_by(
                    "tipo_operacao_financeira__ordem_exibir",
                )  # Adiciona a ordenação aqui
            )

            financeiro_total_agrupado_despesa_saida_grupo_3 = (
                Financeiro.objects.filter(
                    data_transacao__range=[start_date, end_date],
                    valor_transacao__lt=0,
                    tipo_operacao_financeira__valor_default_transacao=3,
                )
                .values("tipo_operacao_financeira")
                .annotate(total_caixa=Sum("valor_transacao"))
                .annotate(
                    operacao_financeira_descricao=F(
                        "tipo_operacao_financeira__descricao",
                    ),
                )
                .order_by(
                    "tipo_operacao_financeira__ordem_exibir",
                )  # Adiciona a ordenação aqui
            )

        if tipo_categoria_financeira:
            financeiro_total_agrupado = (
                financeiro_total_agrupado.filter(
                    tipo_categoria_financeira=tipo_categoria_financeira,
                )
                if financeiro_total_agrupado
                else None
            )
            financeiro_total_agrupado_despesa_saida_grupo_1 = (
                financeiro_total_agrupado_despesa_saida_grupo_1.filter(
                    tipo_categoria_financeira=tipo_categoria_financeira,
                )
                if financeiro_total_agrupado_despesa_saida_grupo_1
                else None
            )
            financeiro_total_agrupado_despesa_saida_grupo_2 = (
                financeiro_total_agrupado_despesa_saida_grupo_2.filter(
                    tipo_categoria_financeira=tipo_categoria_financeira,
                )
                if financeiro_total_agrupado_despesa_saida_grupo_2
                else None
            )
            financeiro_total_agrupado_despesa_saida_grupo_3 = (
                financeiro_total_agrupado_despesa_saida_grupo_3.filter(
                    tipo_categoria_financeira=tipo_categoria_financeira,
                )
                if financeiro_total_agrupado_despesa_saida_grupo_3
                else None
            )

        return (
            financeiro_total_agrupado,
            financeiro_total_agrupado_despesa_saida_grupo_1,
            financeiro_total_agrupado_despesa_saida_grupo_2,
            financeiro_total_agrupado_despesa_saida_grupo_3,
        )

    @classmethod
    def get_total_dinheiro_liquido(
        cls,
        financeiro_total_agrupado,
    ) -> tuple[str, Decimal]:
        # Defina os tipos de operação financeira que você deseja filtrar
        tipos_operacao_financeira = (
            TipoOperacaoFinanceira.objects.filter(grupo_dinheiro=True)
            .values_list(
                "descricao",
                flat=True,
            )
            .order_by("ordem_exibir")
        )

        # Filtre e some os valores em memória
        total_dinheiro_liquido = sum(
            item["total_caixa"]
            for item in financeiro_total_agrupado
            if item["operacao_financeira_descricao"] in tipos_operacao_financeira
        )

        # Converter o QuerySet para uma lista para garantir o tipo de dado
        lista_descricoes = list(tipos_operacao_financeira)
        lista_das_descricoes = " - ".join(lista_descricoes)

        return lista_das_descricoes, total_dinheiro_liquido

    @cached_property
    def protocolo(self: "Financeiro") -> Livro01Protocolo:
        return self.pedido.protocolo if self.pedido else None

    @cached_property
    def certidao(self: "Financeiro") -> "PedidoCertidao":
        return models_certidoes.PedidoCertidao.objects.filter(
            id=self.pedido_certidao_id,
        ).first()


class FinanceiroHistorico(FinanceiroBase):
    data_operacao: datetime = models.DateTimeField(auto_now_add=True)
    tipo_operacao: str = models.CharField(
        max_length=20,
        choices=[
            ("criação", "Criação"),
            ("atualização", "Atualização"),
            ("exclusão", "Exclusão"),
        ],
    )

    class Meta:
        verbose_name = "Histórico Financeiro"
        verbose_name_plural = "Históricos Financeiros"

    @classmethod
    def atualizar_ou_criar_historico(cls, instance, tipo_operacao: str) -> None:
        if not isinstance(instance, apps.get_model("home", "Financeiro")):
            msg = "A instância fornecida não é do tipo 'Financeiro'."
            logger.error(msg)
            raise TypeError(msg)

        logger.debug(
            f"Atualizando ou criando histórico para Financeiro ID {instance.id} com tipo de operação '{tipo_operacao}'.",
        )

        campos = {
            field.name: getattr(instance, field.name, None)
            for field in instance._meta.fields
        }

        campos["tipo_operacao"] = tipo_operacao

        logger.debug(f"Campos para atualizar/criar: {campos}")

        try:
            with transaction.atomic():
                historico, created = cls.objects.update_or_create(
                    defaults=campos,
                    pk=instance.id,
                    tipo_operacao=tipo_operacao,
                )
                if created:
                    logger.info(
                        f"Histórico '{tipo_operacao}' criado para Financeiro ID {instance.id}",
                    )
                else:
                    logger.info(
                        f"Histórico '{tipo_operacao}' atualizado para Financeiro ID {instance.id}",
                    )
        except Exception as e:
            logger.exception(
                f"Erro ao atualizar ou criar histórico para Financeiro ID {instance.id}: {e}",
            )


class Financeiro(FinanceiroBase):
    class Meta:
        verbose_name = "Financeiro"
        verbose_name_plural = "Financeiros"


# Partes Envolvidas no PROTOCOLO
class PedidoParte(models.Model):
    pedido = models.ForeignKey(
        Pedido,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="partes",
        verbose_name="Pedido",
    )
    pessoa = models.ForeignKey(
        Livro05,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        verbose_name="Pessoa",
    )
    papel: str = models.CharField(
        max_length=1,
        choices=TipoParte.CHOICES,
        blank=True,
        null=True,
        verbose_name="Papel",
    )

    pessoa_conjuge = models.ForeignKey(
        Livro05,
        on_delete=models.CASCADE,
        related_name="pedido_parte_pessoa_conjuge",
        null=True,
        blank=True,
        verbose_name="Conjuge",
    )

    pessoa_vinculo = models.ForeignKey(
        "pessoas.Vinculo",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        verbose_name="Pessoa Vinculo",
    )

    objects: managers.PedidoParteManager = managers.PedidoParteManager()

    class Meta:
        verbose_name = "Parte do Pedido"
        verbose_name_plural = "Partes do Pedido"

    def __str__(self) -> str:
        return f"{self.pessoa.nome } - {self.papel} - {self.pedido.numero}"

    @classmethod
    def vincular_pessoa_a_pedido(cls, pessoa_id, pedido_id, papel) -> None:
        pedido_parte = cls(pessoa_id=pessoa_id, pedido_id=pedido_id, papel=papel)
        pedido_parte.save()

    @classmethod
    def criar(cls, pedido_id, participacao_nome, participacao_cpf_cnpj, papel) -> None:
        pessoa, criado = Livro05.objects.get_or_create(
            nome=participacao_nome,
            cpf=participacao_cpf_cnpj,
        )
        cls.objects.create(pedido_id=pedido_id, pessoa=pessoa, papel=papel)


class Livro05Lri(models.Model):
    cpf = models.BigIntegerField(unique=True)

    class Meta:
        managed = False

    def __str__(self) -> str:
        return f"{self.cpf}"


class LriDocumento(models.Model):
    cpf_cnpj: str = models.CharField(
        max_length=14,
        blank=True,
        null=True,
        db_index=True,
    )
    nome: str = models.CharField(max_length=250, blank=True, null=True)
    # quantidade_aberto = models.BigIntegerField(default=0, null=False, blank=False)
    # quantidade_finalizado = models.BigIntegerField(default=0, null=False, blank=False)

    def __str__(self) -> str:
        return f"{self.cpf_cnpj} - {self.nome}"


class LriAtualizacao(models.Model):
    data_atualizacao = models.DateField()
    data_pedido = models.DateField()

    def __str__(self) -> str:
        return f"{self.data_atualizacao} - {self.data_pedido}"


class Lri(models.Model):
    """Indisponibilidades."""

    protocolo_indisponibilidade: str = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )
    data_pedido = models.DateField(blank=True, null=True)
    numero_do_processo: str = models.CharField(max_length=500, blank=True, null=True)
    telefone: str = models.CharField(max_length=500, blank=True, null=True)
    nome_instituicao: str = models.CharField(max_length=500, blank=True, null=True)
    forum_vara: str = models.CharField(max_length=500, blank=True, null=True)
    usuario: str = models.CharField(max_length=500, blank=True, null=True)
    email: str = models.CharField(max_length=500, blank=True, null=True)
    cancelamento_indisponibilidade: str = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )
    cancelamento_tipo = models.BigIntegerField(blank=True, null=True)
    cancelamento_data = models.DateField(blank=True, null=True)
    observacao: str = models.CharField(max_length=500, blank=True, null=True)
    uso_origem: str = models.CharField(max_length=1, blank=True, null=True)
    descricao_cpf_cnpj: str = models.CharField(max_length=500, blank=True, null=True)
    descricao_detalhes: str = models.CharField(max_length=500, blank=True, null=True)
    data = models.DateField(blank=True, null=True)

    class Meta:
        verbose_name = "Indisponibilidade"
        verbose_name_plural = "Indisponibilidades"

    def __str__(self) -> str:
        return f"{self.protocolo_indisponibilidade} - {self.data_pedido}"


class LriPartesEnvolvidas(models.Model):
    """Partes Envolvidas na Indisponibilidade."""

    cancelado_em = models.DateField(blank=True, null=True)
    lri = models.ForeignKey(Lri, on_delete=models.CASCADE, null=True)
    tipo_ato: str = models.CharField(max_length=1, blank=True, null=True)
    numero_ato: str = models.CharField(max_length=3, blank=True, null=True)
    vinculo = models.BigIntegerField(blank=True, null=True, db_index=True)
    situacao = models.BigIntegerField(blank=True, null=True)
    data = models.DateField(blank=True, null=True)
    pessoa = models.ForeignKey(Livro05, on_delete=models.CASCADE, null=True)
    matricula = models.BigIntegerField(blank=True, null=True)
    numero_imovel = models.BigIntegerField(blank=True, null=True)
    tipo_imovel: str = models.CharField(max_length=1, blank=True, null=True)
    data_envio = models.DateField(blank=True, null=True)
    numero = models.BigIntegerField(blank=True, null=True)
    tipo: str = models.CharField(max_length=3, blank=True, null=True)
    cartorio: str = models.CharField(max_length=2, blank=True, null=True)
    data_importacao = models.DateField(blank=True, null=True)
    cancelamento_indisponibilidade: str = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        db_index=True,
    )
    data_atualizacao = models.DateField(blank=True, null=True)
    descricao_cpf_cnpj: str = models.CharField(max_length=20, blank=True, null=True)
    uso_origem: str = models.CharField(max_length=1, blank=True, null=True)

    class Meta:
        indexes = [
            models.Index(fields=["pessoa_id", "vinculo"], name="idx_pessoa_id_vinculo"),
        ]
        verbose_name = "Parte Envolvida na Indisponibilidade"
        verbose_name_plural = "Partes Envolvidas na Indisponibilidade"

    def __str__(self) -> str:
        return f"{self.pessoa.nome} - {self.vinculo} - {self.lri.protocolo_indisponibilidade}"


class TipoVinculo(models.Model):
    """Tipos de Vinculos. Ex: Proprietário, Usufrutuário, Credor, Réu, Avalista."""

    descricao: str = models.CharField(
        max_length=40,
        blank=True,
        null=True,
        db_index=True,
    )

    grupo_acoes: str = models.CharField(
        max_length=1,
        blank=True,
        null=True,
        default=TipoSimNao.NAO,
        choices=TipoSimNao.CHOICES,
    )

    grupo_onus: str = models.CharField(
        max_length=1,
        blank=True,
        null=True,
        default=TipoSimNao.NAO,
        choices=TipoSimNao.CHOICES,
    )

    objects: managers.TipoVinculoManager = managers.TipoVinculoManager()

    class Meta:
        verbose_name = "Tipo de Vinculo"
        verbose_name_plural = "Tipos de Vinculo"
        ordering = ["descricao"]

    def __str__(self) -> str:
        return self.descricao

    @classmethod
    def get_tipo_proprietario(cls: "TipoVinculo") -> "TipoVinculo":
        return cls.objects.get_or_create(descricao="Proprietário")[0]

    # OBTER OS ACOES E ONUS
    @classmethod
    def get_id_acoes_onus(cls: "TipoVinculo") -> "TipoVinculo":
        return cls.objects.filter(Q(grupo_acoes="S") | Q(grupo_onus="S")).values_list(
            "id",
            flat=True,
        )


class Vinculo(BaseModel):
    """Vinculo entre Pessoas (L5) e Imóveis (L4). Ex: Proprietário, Usufrutuário, Credor, Réu, Avalista."""

    imovel = models.ForeignKey(
        Livro02,
        on_delete=models.CASCADE,
        default=0,
        blank=True,
        null=True,
        verbose_name="Registro",
        related_name="imovel",
    )
    pessoa = models.ForeignKey(
        Livro05,
        on_delete=models.CASCADE,
        default=0,
        blank=True,
        null=True,
        verbose_name="Pessoa",
        related_name="vinculos_pessoa",
    )
    tipo_regime_casamento = models.ForeignKey(
        TipoRegimeCasamento,
        on_delete=models.CASCADE,
        null=True,
        default=-1,
        verbose_name="Regime de Casamento",
        help_text="Regime de Casamento. Ex. Comunhão Parcial de Bens, Comunhão Universal de Bens, Separação Total de Bens, etc.",
        related_name="regime",
    )
    # conjuge    = models.ForeignKey(Livro05, on_delete=models.CASCADE, default=0)       #conjuge_id TRABALHANDO

    tipo_vinculo = models.ForeignKey(
        TipoVinculo,
        on_delete=models.CASCADE,
        default=0,
        blank=True,
        null=True,
        verbose_name="Tipo de Vinculo",
    )
    estado_civil = models.ForeignKey(
        EstadoCivil,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        default=0,
        verbose_name="EstadoCivil",
    )
    situacao: str = models.CharField(max_length=1, blank=True, null=True)
    numero_ato = models.BigIntegerField(
        blank=True,
        null=True,
        default=0,
        verbose_name="Número do Ato",
        help_text="Número do Ato",
    )
    tipo_ato: str = models.CharField(
        max_length=1,
        blank=True,
        null=True,
        default=TipoAto.REGISTRO,
        choices=TipoAto.CHOICES,
        verbose_name="Tipo de Ato",
        help_text="Tipo de Ato. Ex. Registro, Averbação, etc.",
    )
    area_pecentual = models.DecimalField(
        default=0,
        blank=False,
        decimal_places=2,
        max_digits=12,
        null=True,
    )
    transferido_em = models.DateField(default=None, blank=True, null=True)
    colaborador = models.BigIntegerField(default=0, blank=True, null=True)
    conjuge = models.DecimalField(
        default=0,
        blank=False,
        decimal_places=2,
        max_digits=12,
        null=True,
    )
    livro: str = models.CharField(max_length=5, blank=True, null=True)
    ficha: str = models.CharField(max_length=5, blank=True, null=True)
    data_aquisicaoestrangeiro = models.DateField(default=None, blank=True, null=True)
    data_lavratura = models.DateField(default=None, blank=True, null=True)
    area_pecentual1 = models.BigIntegerField(default=0, blank=True, null=True)
    data_casamento = models.DateField(default=None, blank=True, null=True)
    tipo_casamento: str = models.CharField(max_length=200, blank=True, null=True)

    objects: managers.VinculoManager = managers.VinculoManager()

    class Meta:
        verbose_name = "Vinculo"
        verbose_name_plural = "Vinculos"
        indexes = [
            models.Index(
                fields=["imovel", "situacao", "tipo_vinculo"],
                name="vinculos_id_s_t_idx",
            ),
            models.Index(fields=["numero_ato"], name="vinculos_numero_ato_idx"),
            models.Index(fields=["situacao"]),
            models.Index(fields=["conjuge"]),
            models.Index(fields=["colaborador"]),
            models.Index(fields=["pessoa"]),
            models.Index(fields=["imovel"]),
            models.Index(fields=["numero_ato"]),
            models.Index(fields=["tipo_vinculo"]),
            models.Index(fields=["pessoa", "imovel", "numero_ato"]),
        ]

    def __str__(self) -> str:
        return f"{self.imovel!s} | Ato: {self.numero_do_ato!s} | {self.nome_pessoa!s}"

    @cached_property
    def percentual_formatado(self) -> str:
        return f"{self.percentual:.2f} %"

    @cached_property
    def percentual(self) -> Decimal:
        return round(
            Decimal(self.area_pecentual) if self.area_pecentual else Decimal(0),
            2,
        )

    @cached_property
    def numero_ato_formatado(self) -> str:
        return f"{self.tipo_ato!s}.{self.numero_ato!s}"

    @cached_property
    def inteiro_id(self):
        return int(str(self.id).split(".")[0])

    @cached_property
    def tipo_de_vinculo(self):
        return self.tipo_vinculo.descricao or ""

    @cached_property
    def nome_pessoa(self):
        return self.pessoa or ""

    @cached_property
    def numero_do_ato(self):
        if self.numero_ato is None:
            return ""
        return int(self.numero_ato)

    @cached_property
    def get_pessoal_por_id_url(self):
        return reverse("home:pessoal_por_id", args=(self.id,))


class PedidoParteAto(models.Model):
    """Relaciona as Partes de um Ato de um Pedido de Protocolo."""

    pedido_item = models.ForeignKey(
        PedidoItem,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    pessoa = models.ForeignKey(Livro05, on_delete=models.CASCADE, null=True, blank=True)
    vinculo = models.ForeignKey(
        Vinculo,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    estado_civil = models.ForeignKey(
        EstadoCivil,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        default=0,
    )
    tipo_regime_casamento = models.ForeignKey(
        TipoRegimeCasamento,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="Regime de Casamento",
        help_text="Regime de Casamento. Ex. Comunhão Parcial de Bens, Comunhão Universal de Bens, Separação Total de Bens, etc.",
        default=0,
    )
    # pessoa_conjuge = models.BigIntegerField(null=True)
    pessoa_conjuge = models.ForeignKey(
        Livro05,
        on_delete=models.CASCADE,
        related_name="pessoa_conjuge",
        null=True,
        blank=True,
    )
    percentual_ato = models.BigIntegerField(default=0)
    percentual_doi = models.BigIntegerField(default=0)
    percentual_incra = models.BigIntegerField(default=0)
    tipo_parte: str = models.CharField(
        max_length=1,
        blank=True,
        null=True,
        default=TipoParte.ADQUIRENTE,
        choices=TipoParte.CHOICES,
        verbose_name="Tipo de Parte",
        help_text="Ex. Adquirente, Transmitente, Credor, Devedor, etc.",
    )

    objects: managers.PedidosPartesAtoManager = managers.PedidosPartesAtoManager()

    class Meta:
        verbose_name = "Pedido Parte Ato"
        verbose_name_plural = "Pedido Partes Ato"
        unique_together = ["pessoa", "tipo_parte", "pedido_item"]

    def __str__(self) -> str:
        return self.pessoa.nome or ""

    @classmethod
    def criar(cls, pedido_item_id, pessoa_id, tipo_parte) -> None:
        cls.objects.create(
            pedido_item_id=pedido_item_id,
            pessoa_id=pessoa_id,
            status=tipo_parte,
            percentual_ato=0,
            percentual_doi=0,
            percentual_incra=0,
            # vinculo_id = 0
            # estado_civil = 0
            # tipo_regime_id = 0
        )

    @classmethod
    def criar_pedido_parte_ato(
        cls,
        pedido_item_id,
        pessoa,
        status,
        estado_civil,
        total,
        ato_baixa_id,
        percentual_ato,
    ) -> None:
        total_doi = str(100 / total) if total else "0"  # Evita divisão por zero
        percentual_ato = percentual_ato or "0"

        return cls.objects.create(
            pedido_item_id=pedido_item_id,
            pessoa=pessoa,
            status=status,
            percentual_doi=total_doi,
            estado_civil=estado_civil,
            percentual_ato=percentual_ato,
            vinculo_id=ato_baixa_id,
        )

    @classmethod
    def vincular_pedido_parte_ato(cls, pedido_item_id: int) -> None:
        # Verificar se o ato ainda nao foi cadastrado
        pedido_item = PedidoItem.objects.get(id=pedido_item_id)

        partes = cls.objects.filter(pedido_item_id=pedido_item_id)

        if not partes.exists():
            partes = PedidoParte.objects.filter(
                pedido_id=pedido_item.pedido_id,
                papel__in=["A", "T"],
            )

            # Filtrar todas as partes
            for parte in partes:
                total = partes.count()
                cls.objects.create(
                    pedido_item_id=pedido_item_id,
                    pessoa=parte.pessoa,
                    status=parte.papel,
                    estado_civil=parte.pessoa.estado_civil,
                    vinculo_id=None,  # Isso pode precisar de ajuste se a contagem total específica for necessária
                    percentual_ato=0,
                    percentual_doi=100 / total if total else 0,
                )


class PerguntaAcao(models.Model):
    descricao: str = models.CharField(max_length=300)

    class Meta:
        verbose_name = "Pergunta Ação"
        verbose_name_plural = "Perguntas Ações"

    def __str__(self) -> str:
        return self.descricao


class PerguntaSetor(models.Model):
    descricao: str = models.CharField(max_length=100)

    class Meta:
        verbose_name = "Pergunta Setor"
        verbose_name_plural = "Perguntas Setor"

    def __str__(self) -> str:
        return self.descricao


class Pergunta(models.Model):
    questions: str = models.CharField(max_length=300)
    option1: str = models.CharField(max_length=100)
    option2: str = models.CharField(max_length=100, default=".")
    option3: str = models.CharField(max_length=100, default=".")
    option4: str = models.CharField(max_length=100, default=".")
    option5: str = models.CharField(max_length=100, default=".")
    corrans: str = models.CharField(max_length=100, default=".")
    acoes = models.ForeignKey(PerguntaAcao, on_delete=models.CASCADE, default=0)

    status = (("E", "E"), ("T", "T"))

    categoria: str = models.CharField(max_length=1, choices=status, default="E")
    setores = models.ForeignKey(PerguntaSetor, on_delete=models.CASCADE, default=1)
    observacao: str = models.CharField(max_length=400, default=".")
    previsao_legal: str = models.CharField(max_length=100)
    texto = CKEditor5Field("texto", blank=True, null=True, config_name="default")
    resposta_auxiliar: str = models.CharField(max_length=100, default=".")
    pergunta_ativa: str = models.CharField(
        max_length=1,
        default=TipoSimNao.NAO,
        choices=TipoSimNao.CHOICES,
    )
    ordem = models.BigIntegerField(default=1)

    class Meta:
        verbose_name = "Pergunta"
        verbose_name_plural = "Perguntas"

    def __str__(self) -> str:
        return self.questions

    @classmethod
    def get_resposta_correta(
        cls: "Pergunta",
        pergunta_id: int,
        pedido_item_id: int,
    ) -> tuple[str, str]:
        for pergunta in cls.objects.filter(id=pergunta_id):
            resposta_correta = verificar_acoes_pergunta(
                pergunta.acoes_id,
                pergunta.corrans,
                pedido_item_id,
            )
            ordem = pergunta.ordem
        return resposta_correta, str(ordem)


class PerguntaGrupo(models.Model):
    ato = models.ForeignKey(
        AtoPratica,
        on_delete=models.CASCADE,
        null=True,
        verbose_name="Atos",
        help_text="Ato de Prática",
    )

    perguntas = models.ManyToManyField(
        Pergunta,
        verbose_name="Pergunta",
        help_text="Perguntas",
        related_name="perguntas",
    )

    class Meta:
        verbose_name = "Pergunta Grupo"
        verbose_name_plural = "Perguntas Grupos"

    def __str__(self) -> str:
        return f"{self.ato} - {self.get_perguntas()}"

    def get_perguntas(self) -> str:
        return ", ".join([str(pergunta) for pergunta in self.perguntas.all()])


class PerguntaMinuta(models.Model):
    questions: str = models.CharField(max_length=300)
    option1: str = models.CharField(max_length=100)
    corrans: str = models.CharField(max_length=100, unique=True, default="")

    def __str__(self) -> str:
        return self.questions


class CheckListRealizado(models.Model):
    status = (("O", "O"), ("A", "A"), ("T", "T"))
    categoria: str = models.CharField(
        max_length=1,
        choices=status,
        default="O",
        null=True,
        blank=True,
    )
    item = models.BigIntegerField(null=True, blank=True)
    perguntas = models.ForeignKey(
        Pergunta,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    pessoa = models.ForeignKey(Livro05, on_delete=models.CASCADE, null=True, blank=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    pedido_item = models.ForeignKey(
        PedidoItem,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    created_at: datetime = models.DateTimeField(
        auto_now_add=True,
        null=True,
        blank=True,
    )
    updated_at: datetime = models.DateTimeField(auto_now=True, null=True, blank=True)
    resposta: str = models.CharField(max_length=400, default=".", null=True, blank=True)
    resposta_correta: str = models.CharField(
        max_length=400,
        default=".",
        null=True,
        blank=True,
    )
    tabela_origem_id = models.BigIntegerField()
    nome_tabela_origem: str = models.CharField(
        max_length=100,
        default="",
        null=True,
        blank=True,
    )
    coluna_tabela_origem: str = models.CharField(
        max_length=100,
        default="",
        null=True,
        blank=True,
    )
    ordem = models.BigIntegerField(default=1, null=True, blank=True)

    objects: managers.CheckListRealizadoManager = managers.CheckListRealizadoManager()

    class Meta:
        ordering = ["id"]
        verbose_name = "Checklist Realizado"
        verbose_name_plural = "Checklists Realizados"

    def __str__(self) -> str:
        return f"{self.id} {self.categoria} - {self.resposta}"


class TipoRegistroAuxiliar(models.Model):
    nome: str = models.CharField(max_length=40, blank=True, null=True)
    descricao: str = models.CharField(max_length=100, blank=True, null=True)

    objects: managers.RegistroAuxiliarManager = managers.RegistroAuxiliarManager()

    class Meta:
        verbose_name = "Tipo de Registro Auxiliar"
        verbose_name_plural = "Tipos de Registro Auxiliar"
        indexes = [
            models.Index(fields=["nome"]),
        ]

    def __str__(self) -> str:
        return self.nome


class Livro03(models.Model):
    """Livro de Registros Auxiliares."""

    tipo_registro_auxiliar = models.ForeignKey(
        TipoRegistroAuxiliar,
        on_delete=models.CASCADE,
    )
    numero = models.BigIntegerField(null=True)
    cartorio: str = models.CharField(max_length=2, blank=True, null=True)
    data_abertura = models.DateField(blank=True, null=True, default=date.today)
    cancelado_em = models.DateField(blank=True, null=True)
    data_vencimento = models.DateField(blank=True, null=True)
    numero_cedula: str = models.CharField(max_length=102, blank=True, null=True)
    descricao: str = models.CharField(max_length=200, blank=True, null=True)
    cnm: str = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        default="",
        verbose_name="CNM",
    )
    ultimo_livro: str = models.CharField(max_length=100, blank=True, null=True)
    ultimo_folha: str = models.CharField(max_length=100, blank=True, null=True)
    observacao: str = models.CharField(max_length=250, blank=True, null=True)
    texto = CKEditor5Field("Texto", blank=True, null=True, config_name="default")
    data_envio_cnm = models.DateField(
        blank=True,
        null=True,
        default=None,
        db_index=True,
    )
    enviar_cnm: bool = models.BooleanField(default=False)
    arquivo = models.FileField(upload_to="livro03", blank=True, null=True)

    objects: managers.RegistroAuxiliarManager = managers.RegistroAuxiliarManager()

    livro = 3

    class Meta:
        verbose_name = "Registro Auxiliar"
        verbose_name_plural = "Registros Auxiliares"

    def __str__(self) -> str:
        return f"Nº: {self.numero} - {self.tipo_registro_auxiliar} ({self.numero_cedula}) | Descrição: {self.descricao.title()} "

    def calcular_cnm(self) -> str:
        """
        Calcula o CNM (Cadastro Nacional de Matrículas) com base nos atributos cartório, livro e número.

        Retorna:
            str: O valor calculado do CNM.
        """
        cns = int(Configuracao.obter("CNS")) or 0
        livro = int(self.livro) or 0
        numero = int(self.numero) or 0

        resultado = int(f"{cns:06d}{livro:01d}{numero:07d}") * 100
        resultado = resultado % 97 or 0
        resultado = 98 - resultado or 0
        return f"{cns:06d}{livro:01d}{numero:07d}{resultado:02d}"

    @classmethod
    def get_ultimo_envio_numero_onr_l3(cls) -> str:
        # Sua consulta original modificada para incluir aggregate
        resultado = cls.objects.filter(
            data_envio_cnm__isnull=False,
            numero__lte=115000,
        ).aggregate(maior_numero=Max("numero"))

        from apps.home.templatetags.home_formatos import formatar_numero_registro

        return (
            formatar_numero_registro(resultado["maior_numero"])
            if resultado["maior_numero"]
            else ""
        )

    @staticmethod
    def get_list_url() -> str:
        return reverse("home:livro03_list")

    @cached_property
    def numero_cedula_formatado(self) -> str:
        return str(self.numero_cedula) if self.numero_cedula else ""

    @cached_property
    def data_vencimento_cedula_l3(self) -> str:
        return (
            self.cancelado_em.strftime(settings.DATE_FORMAT_STR)
            if self.cancelado_em
            else ""
        )

    @cached_property
    def data_emissao_cedula(self) -> str:
        return (
            self.data_abertura.strftime(settings.DATE_FORMAT_STR)
            if self.data_abertura
            else ""
        )

    @cached_property
    def numero_registro_formatado(self):
        return self.numero_formatado

    @cached_property
    def imovel(self):
        return Livro02.objects.get_registro_pelo_livro03(self)

    @cached_property
    def numero_formatado(self):
        from apps.home.templatetags.home_formatos import formatar_numero_registro

        return formatar_numero_registro(self.numero) if self.numero else ""

    @cached_property
    def ligacoes(self) -> QuerySet["Livro03Ligacao"]:
        # PEGANDO OS DADOS DAS LIGACOES
        return Livro03Ligacao.objects.filter(registro_auxiliar_id=self.id)

    @cached_property
    def garantias(self) -> QuerySet["Livro03Garantia"]:
        # PEGANDO OS DADOS DAS GARANTIAS - Filtrar as garantias do LIVRO 3 - Vinculadas ao IMOVEL
        return Livro03Garantia.objects.filter(registro_auxiliar_id=self.id)

    @cached_property
    def envolvidos(self) -> QuerySet["Livro03Ligacao"]:
        return Livro03Ligacao.objects.filter(registro_auxiliar_id=self.id)

    @cached_property
    def data_abertura_formatada(self) -> str:
        # VERIIFICAR A DATA
        try:
            return helpers.formatar_data(self.data_abertura, 1)
        except:
            return ""

    @cached_property
    def cancelado_em_formatada(self) -> str:
        try:
            return helpers.formatar_data(self.cancelado_em, 1)
        except:
            return ""

    @cached_property
    def data_vencimento_formatada(self) -> str:
        try:
            return helpers.formatar_data(self.data_vencimento, 1)
        except:
            return ""

    @cached_property
    def avalistas(self) -> QuerySet["Livro03Garantia"]:
        return self.envolvidos.filter(
            figuras__tipo_figura=TipoParte.get_descricao(TipoParte.AVALISTA),
        )

    @cached_property
    def credores(self) -> QuerySet["Livro03Garantia"]:
        return self.envolvidos.filter(
            figuras__tipo_figura=TipoParte.get_descricao(TipoParte.CREDOR),
        )

    @cached_property
    def devedores(self) -> QuerySet["Livro03Garantia"]:
        return self.envolvidos.filter(
            figuras__tipo_figura=TipoParte.get_descricao(TipoParte.DEVEDOR),
        )

    @cached_property
    def quantidade_de_credores(self) -> int:
        return self.credores.count()

    @cached_property
    def quantidade_de_avalistas(self) -> int:
        return self.avalistas.count()

    @cached_property
    def quantidade_de_devedores(self) -> int:
        return self.devedores.count()

    @cached_property
    def quantidade_de_envolvidos(self) -> int:
        return len(self.envolvidos)

    @cached_property
    def quantidade_de_garantias(self) -> int:
        return self.garantias.count()

    @cached_property
    def grau_penhor(self) -> str:
        return self.garantias.first().grau_penhor if self.garantias.first() else ""

    @cached_property
    def area(self) -> str:
        return self.garantias.first().area if self.garantias.first() else ""

    @cached_property
    def vencido(self) -> bool:
        if self.data_vencimento is None:
            return False  # Considera não vencido se não houver data de vencimento
        return self.data_vencimento < timezone.now().date()

    @cached_property
    def cancelado(self) -> bool:
        return self.cancelado_em is not None

    @cached_property
    def cnm_formatada(self):
        cnm = self.calcular_cnm()
        return helpers.formatar_cnm(cnm)

    @classmethod
    def get_dados_em_lista_pelo_numero_do_registro(cls, numero_registro=0) -> list:
        try:
            # vinculado_imovel Atuais
            vinculado_imovel_atual = []

            livro03 = cls.objects.filter(numero=numero_registro).first()

            grau_penhor = ""
            area = ""

            vinculado_imovel_atual.append(
                [
                    livro03.numero_formatado,  # 0
                    livro03.tipo_registro_auxiliar.nome,  # 1
                    str(livro03.numero_cedula),  # 2
                    grau_penhor,  # 3
                    livro03.data_abertura_formatada,  # 4
                    livro03.cancelado_em_formatada,  # 5
                    livro03.data_vencimento_formatada,  # 6
                    livro03.descricao,  # 7
                    area,  # 8
                    livro03.envolvidos,  # 9
                    livro03.garantias,  # 10
                    livro03.quantidade_de_credores,  # 11
                    livro03.quantidade_de_devedores,  # 12
                    livro03.quantidade_de_avalistas,  # 13
                    livro03.quantidade_de_envolvidos,  # 14
                    livro03.quantidade_de_garantias,  # 15
                    livro03.id,  # 16
                ],
            )

            return vinculado_imovel_atual
        except Exception:
            logger.exception("Erro ao construir dict do Livro03 - Registro Auxiliar")
            return []


class RegistroVinculado(models.Model):
    descricao: str = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self) -> str:
        return self.descricao

    objects: managers.RegistroVinculadoManager = managers.RegistroVinculadoManager()


class Livro03Garantia(models.Model):
    registro_auxiliar = models.ForeignKey(
        Livro03,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    imovel_vinculado = models.ForeignKey(
        RegistroVinculado,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    especie: str = models.CharField(max_length=20, blank=True, null=True)
    numero: str = models.CharField(max_length=35, blank=True, null=True)
    descricao: str = models.CharField(max_length=500, blank=True, null=True)
    quantidade: str = models.CharField(max_length=20, blank=True, null=True)
    grau_penhor: str = models.CharField(max_length=5, blank=True, null=True)
    tipo_registro: str = models.CharField(max_length=2, blank=True, null=True)
    numero_registro = models.BigIntegerField(null=True, blank=True)
    valor: str = models.CharField(max_length=100, blank=True, null=True)
    fazenda: str = models.CharField(max_length=100, blank=True, null=True)
    tipo_ato: str = models.CharField(max_length=15, blank=True, null=True)
    area: str = models.CharField(max_length=100, blank=True, null=True)

    objects: managers.Livro03GarantiaManager = managers.Livro03GarantiaManager()

    class Meta:
        verbose_name = "Auxiliar de Garantia"
        verbose_name_plural = "Auxiliares de Garantia"
        indexes = [
            models.Index(
                fields=["numero_registro", "tipo_registro"],
                name="auxiliar_gar_numero_i_idx",
            ),
            models.Index(
                fields=["-registro_auxiliar_id"],
                name="auxiliar_gar_id_desc_idx",
            ),
        ]

    def __str__(self) -> str:
        return self.especie

    @cached_property
    def eh_matricula(self) -> bool:
        return self.tipo_registro == "M"

    @cached_property
    def tipo_registro_descrito(self) -> str:
        return (
            TipoRegistro.get_descricao(self.tipo_registro)
            if self.tipo_registro
            else "M"
        )

    def numero_registro_formatado(self):
        if not self.numero_registro:
            return ""

        numero_registro = str(self.numero_registro)

        # if len(str(self.numero_registro)) <= 3:
        #    return self.numero_registro

        # return self.numero_registro[:-3] + "." + self.numero_registro[-3:] if self.numero_registro else ""
        return numero_registro[:-3] + "." + numero_registro[-3:]

    def livro03(self):
        return Livro03.objects.get(id=self.registro_auxiliar)


class Livro03Descricao(models.Model):
    tipo_figura: str = models.CharField(max_length=40, blank=True, null=True)
    tipo_descricao: str = models.CharField(max_length=100, blank=True, null=True)

    objects: managers.Livro03Manager = managers.Livro03Manager()

    class Meta:
        verbose_name = "Descrição"
        verbose_name_plural = "Descrições"

    def __str__(self) -> str:
        return self.tipo_descricao


class Livro03Ligacao(models.Model):
    estado_civil = models.ForeignKey(
        EstadoCivil,
        on_delete=models.CASCADE,
        default=0,
        null=True,
    )
    pessoa = models.ForeignKey(
        Livro05,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="livro03_ligacao_pessoa",
    )
    registro_auxiliar = models.ForeignKey(
        Livro03,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    figuras = models.ForeignKey(
        Livro03Descricao,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    situacao: str = models.CharField(max_length=1, blank=True, null=True)
    transferido_em = models.DateField(blank=True, null=True)
    numero_ato = models.BigIntegerField()
    tipo_ato: str = models.CharField(max_length=1, blank=True, null=True)

    observacao: str = models.CharField(max_length=200, blank=True, null=True)
    regime: str = models.CharField(max_length=100, blank=True, null=True)

    objects: managers.Livro03LigacaoManager = managers.Livro03LigacaoManager()

    def __str__(self) -> str:
        field_values = []
        for field in self._meta.get_fields():
            field_values.append(str(getattr(self, field.name, "")))
        return " ".join(field_values)

    @cached_property
    def tipo_parte(self) -> str:
        return self.figuras.tipo_figura if self.figuras else ""


class MinutaAuxiliar(models.Model):
    tipo_livro = models.BigIntegerField()
    nome_minuta_principal = models.TextField(blank=True, null=True, default="")
    nome_minuta_auxiliar_01 = models.TextField(blank=True, null=True, default="")
    nome_minuta_auxiliar_02 = models.TextField(blank=True, null=True, default="")
    nome_minuta_auxiliar_03 = models.TextField(blank=True, null=True, default="")
    nome_minuta_auxiliar_04 = models.TextField(blank=True, null=True, default="")
    nome_minuta_auxiliar_05 = models.TextField(blank=True, null=True, default="")
    nome_minuta_auxiliar_06 = models.TextField(blank=True, null=True, default="")
    nome_minuta_auxiliar_07 = models.TextField(blank=True, null=True, default="")
    nome_minuta_auxiliar_08 = models.TextField(blank=True, null=True, default="")
    nome_minuta_auxiliar_09 = models.TextField(blank=True, null=True, default="")
    nome_minuta_auxiliar_10 = models.TextField(blank=True, null=True, default="")

    def __str__(self) -> str:
        return self.tipo_livro


# class TipoUnidade(models.Model):
#     id:str = models.CharField(max_length=3, primary_key=True, verbose_name="ID", auto_created=True, serialize=False)
#     descricao:str = models.CharField(max_length=40, blank=True, null=True)

#     def __str__(self) -> str:
#         return self.descricao


class FichaAuxiliar(models.Model):
    unidade = models.ForeignKey(
        Unidade,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    nome: str = models.CharField(max_length=300, blank=True, null=True)
    nome_incorporadora: str = models.CharField(max_length=300, blank=True, null=True)
    data_incorporacao = models.DateField(default=date.today, blank=True, null=True)
    numero_edificacao: str = models.CharField(max_length=60, blank=True, null=True)
    tipo: str = models.CharField(max_length=3, blank=True, null=True)
    construido: str = models.CharField(max_length=1, blank=True, null=True)

    def __str__(self) -> str:
        return self.nome

    @staticmethod
    def get_quantidade_de_unidades_no_condominio(imovel_id: int = 0) -> int:
        if imovel_id <= 0:
            return 0

        try:
            ficha = FichaAuxiliar.objects.get(id=imovel_id)
            if ficha.unidade:
                return Unidade.objects.filter(
                    registro_anterior_id=ficha.unidade_id,
                ).count()
            return 0
        except FichaAuxiliar.DoesNotExist:
            return 0


class PessoaEndereco(models.Model):
    vinculo = models.ForeignKey(Vinculo, on_delete=models.CASCADE, null=True)
    ligacoes = models.ForeignKey(Livro03Ligacao, on_delete=models.CASCADE, null=True)
    nacionalidade: str = models.CharField(max_length=15, blank=True, null=True)
    profissao: str = models.CharField(max_length=60, blank=True, null=True)

    def __str__(self) -> str:
        field_values = []
        for field in self._meta.get_fields():
            field_values.append(str(getattr(self, field.name, "")))
        return " ".join(field_values)


class ColaboradorSetor(models.Model):
    servico: str = models.CharField(max_length=40, blank=True, null=True)

    def __str__(self) -> str:
        field_values = []
        for field in self._meta.get_fields():
            field_values.append(str(getattr(self, field.name, "")))
        return " ".join(field_values)


# Gravar direto no BANCO DE DADOS


class GrupoUsuario(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    member_user = models.BigIntegerField(null=True, blank=True)

    def __str__(self) -> str:
        return str(self.user)


# INICIO CALENDARIO
class EventAbstract(models.Model):
    """Event abstract model."""

    is_active: bool = models.BooleanField(default=True)
    is_deleted: bool = models.BooleanField(default=False)
    created_at: datetime = models.DateTimeField(auto_now_add=True)
    updated_at: datetime = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Event(EventAbstract):
    """Event model."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="events",
    )
    auth_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name="Usuário",
    )
    numero = models.BigIntegerField(
        null=True,
        default=0,
        verbose_name="Número Relacionado",
        help_text="Número do Protocolo ou Pedido de Certidão",
    )
    title: str = models.CharField(max_length=200, verbose_name="Título do Evento")
    description = models.TextField(blank=True, null=True, verbose_name="Descrição")
    start_time: datetime = models.DateTimeField(verbose_name="Início do Evento")
    end_time: datetime = models.DateTimeField(
        verbose_name="Fim do Evento",
        blank=True,
        null=True,
        db_index=True,
    )
    status_origem = (
        ("P", "Protocolo"),
        ("E", "Exame Cálculo"),
        ("C", "Pedido Certidão"),
        ("G", "Geral"),
    )
    origem: str = models.CharField(
        max_length=1,
        choices=sorted(status_origem),
        default="G",
        verbose_name="Origem",
        help_text="Origem do Evento",
    )
    url: str = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        default="/calender/",
        verbose_name="URL",
        help_text="URL do Evento",
    )
    start_time_checked: datetime = models.DateTimeField(null=True)
    end_time_checked: datetime = models.DateTimeField(null=True)
    member_checked_user = models.BigIntegerField(null=True, blank=True)
    exibir_agenda_protocolo: str = models.CharField(
        max_length=1,
        blank=True,
        null=True,
        default="S",
    )
    fase_agenda = models.ForeignKey(
        FaseAgenda,
        on_delete=models.CASCADE,
        related_name="events",
        default=1,
    )

    objects: managers.EventManager = managers.EventManager()

    class Meta:
        verbose_name = "Evento"
        verbose_name_plural = "Eventos"
        indexes = [models.Index(fields=["origem", "numero"])]

    def __str__(self) -> str:
        return self.title

    def get_absolute_url(self):
        return reverse("home:event-detail", args=(self.id,))

    @cached_property
    def event_open(self):
        return 123

    @cached_property
    def get_html_url(self) -> str:
        url = reverse("home:event-detail", args=(self.id,))
        return f'<a href= "{url}"> {self.title} </a>'

    @classmethod
    def montar_evento(
        cls,
        usuario_id,
        desc,
        url,
        title,
        hour,
        minuto,
        year_inicio,
        month_inicio,
        day_inicio,
        year_fim,
        month_fim,
        day_fim,
        colaborador_id,
    ) -> None:
        # Data de Inicio
        data_inicio = datetime(
            year_inicio,
            month_inicio,
            day_inicio,
            hour,
            minuto,
            tzinfo=timezone.get_current_timezone(),
        )

        # Gravando hora
        title_temp = (
            title + " (" + str(helpers.data_formato_modelo_hora(data_inicio)) + ") "
        )
        title_temp = str(title_temp).replace("/", ".")

        data_fim = datetime(
            year_fim,
            month_fim,
            day_fim,
            hour,
            minuto,
            tzinfo=timezone.get_current_timezone(),
        )

        cls.criar_evento_no_calendario(
            colaborador_id=colaborador_id,
            usuario_id=usuario_id,
            numero=0,
            title=title_temp,
            description=desc,
            url=url,
            origem="G",
            horas_adicionais=1,
            data_futura_inicio=data_inicio,
            data_futura_fim=data_fim,
            gravar_apenas_data="N",
            fase_agenda_id="1",
            exibir_agenda="S",
        )

    @classmethod
    def criar_evento_na_agenda(
        cls,
        numero_protocolo=0,
        tipo_status_protocolo: TipoStatusProtocolo = TipoStatusProtocolo.EM_ANDAMENTO,
        data_finalizado="",
        colaborador_id=0,
    ) -> "Event":
        if tipo_status_protocolo in [
            TipoStatusProtocolo.EXIGENCIA,
            TipoStatusProtocolo.CANCELADO,
            TipoStatusProtocolo.REGISTRADO,
        ]:
            if tipo_status_protocolo == TipoStatusProtocolo.EXIGENCIA:  # EXIGENCIA
                servico = Configuracao.obter("DESCRICAO_SERVICO_EXIGENCIA")
                titulo = f"{servico} {numero_protocolo}"
                descricao = f"Atualmente o protocolo esta: {servico}"
            elif tipo_status_protocolo == TipoStatusProtocolo.CANCELADO:  # CANCELADO
                titulo = f"{Configuracao.obter('DESCRICAO_SERVICO_CANCELADO')} {numero_protocolo}"
                descricao = f"Atualmente o protocolo esta: {Configuracao.obter('DESCRICAO_SERVICO_CANCELADO')}"
            elif tipo_status_protocolo == TipoStatusProtocolo.REGISTRADO:  # REGISTRADO
                titulo = f"{Configuracao.obter('DESCRICAO_SERVICO_REGISTRADO')} {numero_protocolo}"
                descricao = f"Atualmente o protocolo esta: {Configuracao.obter('DESCRICAO_SERVICO_REGISTRADO')}"

            # Localiza o usuario correpondendo em Colaboradores com base no ID.
            # usuario_id = int(str(usuario_id).split(".")[0])
            # usuario_obtido_no_firebird = Colaborador.objects.get(pk=usuario_id)

            # Localiza o usuario no banco de dados do sistema com base no username.
            # usuario = User.objects.get_ou_criar_usuario(usuario_obtido_no_firebird.nome)

            if colaborador_id:
                evento = cls.criar_evento_no_calendario(
                    colaborador_id=colaborador_id,
                    usuario_id=colaborador_id,
                    numero=numero_protocolo,
                    title=titulo,
                    description=descricao,
                    origem="P",
                    horas_adicionais=1,
                    data_futura_inicio=data_finalizado,
                    data_futura_fim=data_finalizado,
                    fase_agenda_id=81,
                )
                if evento:
                    Event.criar_membro_no_evento_do_calendario(
                        evento,
                        colaborador_id=colaborador_id,
                    )

                    # ENCERRANDO OS EVENTOS DA AGENDA
                    Event.objects.encerrar_evento_pelo_titulo(
                        titulo=titulo,
                        data=data_finalizado,
                        exibir_agenda_protocolo="S",
                    )

                    return evento
        return None

    @classmethod
    def criar_evento_no_calendario(
        cls,
        user,
        auth_user,
        numero,
        title,
        description,
        origem,
        horas_adicionais,
        url=None,
        data_futura_inicio=None,
        data_futura_fim=None,
        gravar_apenas_data="N",
        fase_agenda_id=1,
        exibir_agenda="S",
    ) -> "Event":
        try:
            # print("CALENDARIO: Criando evento")

            # from apps.cartorios.models import Usuario

            # usuario = user if isinstance(user, Usuario) else Usuario.objects.get_ou_criar_usuario(user)

            # VERIFICAR SE O USUÁRIO É UMA INSTÂNCIA DE USUÁRIO
            # if not usuario:
            #     usuario = Usuario.objects.first()

            if not user:
                from apps.cartorios.models import Usuario

                user = Usuario.get_current_user()

            # Define se a hora deve ser desprezada
            ignorar_hora = str(gravar_apenas_data) == "S"

            # Verifica se data_futura_inicio não é None e é uma instância de date mas não de datetime
            if data_futura_inicio is not None:
                if isinstance(data_futura_inicio, date) and not isinstance(
                    data_futura_inicio,
                    datetime,
                ):
                    # Define o horário de início e fim baseado na flag ignorar_hora
                    current_time = datetime.now().time()
                    inicio_hora = datetime.time.min if ignorar_hora else current_time
                    fim_hora = datetime.time.min if ignorar_hora else current_time

                    # Combina a data com o horário definido
                    data_evento_inicio = datetime.combine(
                        data_futura_inicio,
                        inicio_hora,
                    )
                    data_evento_fim = datetime.combine(data_futura_fim, fim_hora)
                else:
                    # Se já é um objeto datetime, usa diretamente
                    data_evento_inicio = data_futura_inicio
                    data_evento_fim = data_futura_fim
            else:
                # Se não, usa o momento atual e adiciona horas adicionais para definir data_evento_fim
                agora = timezone.now()
                data_evento_inicio = agora
                data_evento_fim = agora + timedelta(hours=int(horas_adicionais))

            # Torna os datetimes aware (não é necessário se já são aware)
            data_evento_inicio = (
                timezone.make_aware(data_evento_inicio)
                if not data_evento_inicio.tzinfo
                else data_evento_inicio
            )
            data_evento_fim = (
                timezone.make_aware(data_evento_fim)
                if not data_evento_fim.tzinfo
                else data_evento_fim
            )

            evento, created = Event.objects.update_or_create(
                user=(user if user else auth_user if auth_user else 1),
                numero=numero,
                title=title,
                description=str(description),
                origem=origem,
                defaults={
                    "auth_user": auth_user if auth_user else 1,
                    "member_checked_user": user.pk,
                    "url": url if url else "",
                    "start_time": data_evento_inicio,
                    "end_time": data_evento_fim,
                    "fase_agenda_id": fase_agenda_id,
                    "exibir_agenda_protocolo": exibir_agenda,
                },
            )

            if created:
                logger.info(f"CALENDARIO: {title} criado.")
            else:
                logger.info(f"CALENDARIO: {title} atualizado .")

            return evento
        except Exception as e:
            logger.debug(f"CALENDARIO: Erro ao criar evento: {e}")

    @classmethod
    def criar_membro_no_evento_do_calendario(
        cls,
        evento,
        colaborador_id: int,
        salvar_membro="N",
    ) -> None:
        colaborador = Colaborador.objects.get(pk=colaborador_id)
        usuario = colaborador.usuario

        if usuario:
            membro = None

            if salvar_membro == "S":
                membro, created = EventMember.objects.get_or_create(
                    event=evento,
                    user=usuario,
                )
                if created:
                    print(
                        f"CALENDARIO: Membro '{membro}' adicionado ao evento: {evento.title}.",
                    )
                else:
                    print(
                        f"CALENDARIO: Membro '{membro}' já existe no evento: {evento.title}.",
                    )

            else:
                for auth_colaborador in GrupoUsuario.objects.filter(user=usuario):
                    membro, created = EventMember.objects.get_or_create(
                        event=evento,
                        user=auth_colaborador,
                    )
                    if created:
                        print(
                            f"CALENDARIO: Membro '{membro}' adicionado ao evento: {evento.title}.",
                        )
                    else:
                        print(
                            f"CALENDARIO: Membro '{membro}' já existe no evento: {evento.title}.",
                        )

            return membro

        return None

    # Gravar Eventos pela Frequencia
    @classmethod
    def criar_eventos_frequencia(
        cls,
        event,
        event_frequencia,
        member_id,
        data_inicio,
        data_fim,
    ) -> None:
        # Pegando as data STR e formando para DATE
        (
            _,
            year_inicio,
            month_inicio,
            day_inicio,
            _,
            _,
            _,
            dia_da_semana_nro_i,
            _,
            _,
        ) = helpers.convert_string_to_date_and_add_months(
            data_inicio,
            settings.DATE_FORMAT_STR,
            0,
        )
        (
            _,
            year_fim,
            month_fim,
            day_fim,
            _,
            _,
            _,
            dia_da_semana_nro_f,
            _,
            _,
        ) = helpers.convert_string_to_date_and_add_months(
            data_fim,
            settings.DATE_FORMAT_STR,
            0,
        )

        year_inicio, month_inicio, day_inicio = (
            int(year_inicio),
            int(month_inicio),
            int(day_inicio),
        )
        year_fim, month_fim, day_fim = int(year_fim), int(month_fim), int(day_fim)

        # Verificar se o dia da semana cai no sabado ou domingo
        if int(dia_da_semana_nro_i) not in [0, 6]:
            # Pegando os dados para exibir no EVENTO
            title, desc, url = event.title, event.description, event.url

            # Iniciar o Flag
            id_01, id_02, id_03, id_04 = 0, 0, 0, 0

            # Checando os Flag
            if event_frequencia.id == 1:  # TODO dia (1 vez)
                id_01, id_02, id_03, id_04 = 1, 0, 0, 0
            elif event_frequencia.id == 2:  # TODO dia (2 vezes)
                id_01, id_02, id_03, id_04 = 1, 1, 0, 0
            elif event_frequencia.id == 3:  # TODO dia (3 vezes)
                id_01, id_02, id_03, id_04 = 1, 1, 1, 0
            elif event_frequencia.id == 4:  # Último dia do mês
                id_01, id_02, id_03, id_04 = 1, 1, 1, 1
            else:  # Nao categorizado
                id_01, id_02, id_03, id_04 = 1, 0, 0, 0

            # Gravando hora 1
            if id_01 == 1:
                cls.montar_evento(
                    usuario_id=member_id,
                    desc=desc,
                    url=url,
                    title=title,
                    hour=event_frequencia.start_time_01.hour,
                    minuto=event_frequencia.start_time_01.minute,
                    year_inicio=year_inicio,
                    month_inicio=month_inicio,
                    day_inicio=day_inicio,
                    year_fim=year_fim,
                    month_fim=month_fim,
                    day_fim=day_fim,
                    colaborador_id=member_id,
                )

            # Gravando hora 2
            if id_02 == 1:
                cls.montar_evento(
                    usuario_id=member_id,
                    desc=desc,
                    url=url,
                    title=title,
                    hour=event_frequencia.start_time_02.hour,
                    minuto=event_frequencia.start_time_02.minute,
                    year_inicio=year_inicio,
                    month_inicio=month_inicio,
                    day_inicio=day_inicio,
                    year_fim=year_fim,
                    month_fim=month_fim,
                    day_fim=day_fim,
                    colaborador_id=member_id,
                )

            # Gravando hora 3
            if id_03 == 1:
                cls.montar_evento(
                    usuario_id=member_id,
                    desc=desc,
                    url=url,
                    title=title,
                    hour=event_frequencia.start_time_03.hour,
                    minuto=event_frequencia.start_time_03.minute,
                    year_inicio=year_inicio,
                    month_inicio=month_inicio,
                    day_inicio=day_inicio,
                    year_fim=year_fim,
                    month_fim=month_fim,
                    day_fim=day_fim,
                    colaborador_id=member_id,
                )

            # Gravando hora 4
            if id_04 == 1:
                cls.montar_evento(
                    usuario_id=member_id,
                    desc=desc,
                    url=url,
                    title=title,
                    hour=event_frequencia.start_time_04.hour,
                    minuto=event_frequencia.start_time_04.minute,
                    year_inicio=year_inicio,
                    month_inicio=month_inicio,
                    day_inicio=day_inicio,
                    year_fim=year_fim,
                    month_fim=month_fim,
                    day_fim=day_fim,
                    colaborador_id=member_id,
                )

    # Gerar Evento Recorrente para determinado
    @classmethod
    def get_evento_recorrente(
        cls,
        member_id,
        event_id,
        data_inicio,
        data_fim,
    ) -> None:
        # dt_inicio = helpers.convert_string_to_date_and_add_months(str(data_inicio), settings.DATE_FORMAT_STR, 0)
        # dt_fim = helpers.convert_string_to_date_and_add_months(str(data_fim), settings.DATE_FORMAT_STR, 0)

        # Selecionar Evento para gravar
        for event in EventRecorrente.objects.filter(pk=event_id):
            event_recorrente_frequencia_id = event.event_recorrente_frequencia_id
            for event_frequencia in EventRecorrenteFrequencia.objects.filter(
                pk=event_recorrente_frequencia_id,
            ):
                cls.criar_eventos_frequencia(
                    event,
                    event_frequencia,
                    member_id,
                    data_inicio,
                    data_fim,
                )


class EventMember(EventAbstract):
    """Event member model."""

    # print("Evento", User)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="events")
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="event_members",
    )

    class Meta:
        unique_together = ["event", "user"]

    def __str__(self) -> str:
        return str(self.user)


class PedidoItemImovel(models.Model):
    setor: str = models.CharField(max_length=150, blank=True, null=True)
    lote: str = models.CharField(max_length=50, blank=True, null=True)
    area: str = models.CharField(max_length=20, blank=True, null=True)
    residencial: str = models.CharField(max_length=1, blank=True, null=True)
    comercial: str = models.CharField(max_length=1, blank=True, null=True)
    nome_rua: str = models.CharField(max_length=150, blank=True, null=True)
    numero_casa: str = models.CharField(max_length=20, blank=True, null=True)
    municipio: str = models.CharField(max_length=120, blank=True, null=True)
    nome_fazenda: str = models.CharField(max_length=200, blank=True, null=True)
    caracteristica_fazenda: str = models.CharField(
        max_length=120,
        blank=True,
        null=True,
    )
    remanescente: str = models.CharField(max_length=1, blank=True, null=True)
    reserva_legal: str = models.CharField(max_length=1, blank=True, null=True)
    georefenciada: str = models.CharField(max_length=1, blank=True, null=True)
    numero_nirf: str = models.CharField(max_length=200, blank=True, null=True)
    numero_ccirr: str = models.CharField(max_length=200, blank=True, null=True)
    numero_car: str = models.CharField(max_length=200, blank=True, null=True)
    numero_incra: str = models.CharField(max_length=200, blank=True, null=True)
    quadra: str = models.CharField(max_length=50, blank=True, null=True)
    area_fazenda: str = models.CharField(max_length=140, blank=True, null=True)
    opcao_imovel: str = models.CharField(max_length=1, blank=True, null=True)
    pedido_item = models.ForeignKey(PedidoItem, on_delete=models.CASCADE)
    data_validade_itr: str = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        default=settings.MINDATE,
    )
    m_frente_metros: str = models.CharField(max_length=100, blank=True, null=True)
    p_frente_metros: str = models.CharField(max_length=100, blank=True, null=True)
    m_direito_metros: str = models.CharField(max_length=100, blank=True, null=True)
    p_direito_metros: str = models.CharField(max_length=100, blank=True, null=True)
    m_esquerdo_metros: str = models.CharField(max_length=100, blank=True, null=True)
    p_esquerdo_metros: str = models.CharField(max_length=100, blank=True, null=True)
    p_fundo_metros: str = models.CharField(max_length=100, blank=True, null=True)
    m_fundo_metros: str = models.CharField(max_length=100, blank=True, null=True)
    area_construida_residencial: str = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    objects: managers.PedidosItensDadosImovelManager = (
        managers.PedidosItensDadosImovelManager()
    )

    class Meta:
        verbose_name = "Dados do Imovel do Pedido"
        verbose_name_plural = "Dados dos Livro02 do Pedido"

    def __str__(self) -> str:
        return self.nome_rua


class Cidade(models.Model):
    nome: str = models.CharField(max_length=120, blank=True, null=True)

    class Meta:
        verbose_name = "Cidade"
        verbose_name_plural = "Cidades"
        ordering = ["nome"]

    def __str__(self) -> str:
        return self.nome


class TipoRegistroProtocolo(models.Model):
    id: str = models.CharField(max_length=1, primary_key=True)
    descricao: str = models.CharField(max_length=120, blank=True, null=True)
    ordem = models.BigIntegerField(default=0)

    def __str__(self) -> str:
        return str(self.descricao)


class ChecklistRealizadoHistorico(models.Model):
    status = (("O", "O"), ("A", "A"), ("T", "T"))

    categoria: str = models.CharField(
        max_length=1,
        choices=status,
        default="O",
        null=True,
        blank=True,
    )
    perguntas = models.ForeignKey(
        Pergunta,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    pessoa = models.ForeignKey(Livro05, on_delete=models.CASCADE, null=True, blank=True)
    colaborador = models.BigIntegerField(default=0, null=True, blank=True)

    """ colaborador = models.ForeignKey(
        Colaborador, on_delete=models.CASCADE, related_name="funcionario"
    ) """
    conferido_usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="conferente",
        null=True,
        blank=True,
    )
    pedido_item = models.ForeignKey(
        PedidoItem,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    pedidos = models.ForeignKey(Pedido, on_delete=models.CASCADE, null=True, blank=True)
    created_at: datetime = models.DateTimeField(
        auto_now_add=True,
        null=True,
        blank=True,
    )
    updated_at: datetime = models.DateTimeField(auto_now=True, null=True, blank=True)
    resposta: str = models.CharField(max_length=400, default=".", null=True, blank=True)
    resposta_correta: str = models.CharField(
        max_length=400,
        default=".",
        null=True,
        blank=True,
    )
    ordem = models.BigIntegerField(default=1, null=True, blank=True)
    objects: managers.ChecklistRealizadoHistoricoManager = (
        managers.ChecklistRealizadoHistoricoManager()
    )

    class Meta:
        ordering = ["id"]
        verbose_name = "ChecklistRealizadoHistorico"
        verbose_name_plural = "ChecklistRealizadoHistorico"

    def __str__(self) -> str:
        return f"{self.id} {self.categoria} - {self.resposta}"


def get_condominio_pelo_imovel(
    registro_anterior_id=0,
    opcao=0,
    tipo_unidade="",
    imovel_atual_id=0,
):
    try:
        if opcao == 1:
            unidade = Unidade.objects.select_related("imovel").get(
                imovel_id=registro_anterior_id,
            )
            imovel = unidade.imovel
            ficha = FichaAuxiliar.objects.filter(pk=imovel.id).first()
            setor = ""
            numero_unidade = ""
            rua = ""
        else:
            unidade = Unidade.objects.select_related("imovel").get(
                id=registro_anterior_id,
            )
            imovel = unidade.imovel
            ficha = FichaAuxiliar.objects.filter(pk=imovel.id).first()
            setor = Lote.objects.get(unidade=unidade).setor
            numero_unidade = Unidade.objects.get(
                imovel_id=imovel_atual_id,
            ).numero_unidade
            rua = get_ruas(registro_anterior_id)

        return [
            imovel.tipo,
            imovel.numero,
            imovel.cartorio,
            ficha.nome if ficha else "",
            ficha.nome_incorporadora if ficha else "",
            ficha.data_incorporacao if ficha else "",
            ficha.numero_edificacao if ficha else "",
            numero_unidade,
            unidade.nome_edificio,
            str(get_tipo_da_unidade_pelo_id(tipo_unidade)),
            "",
            unidade.area,
            unidade.quadra,
            unidade.lote_auxiliar,
            setor,
            rua,
        ]

    except (Unidade.DoesNotExist, Lote.DoesNotExist, FichaAuxiliar.DoesNotExist):
        return []


def get_tipos_andamentos(tipo_andamento):
    """Obtém o serviço em andamento com base na chave fornecida."""
    cache_key = f"tipos_andamentos_{tipo_andamento}"
    servico = cache.get(cache_key)

    if servico is not None:
        return servico

    try:
        tipo_andamento = TipoAndamento.objects.filter(
            tipo_andamento=tipo_andamento,
        ).first()

        if tipo_andamento:
            servico = tipo_andamento.servico
            # Armazenar no cache por 300 segundos
            cache.set(cache_key, servico, 300)
            return servico

        return ""
    except Exception:
        # Você pode querer registrar a exceção aqui
        return ""


def get_regime_bens(descricao_regime):
    estado_civil = TipoRegimeCasamento.objects.filter(
        descricao_regime__iexact=descricao_regime,
    ).first()

    if estado_civil:
        return estado_civil.id

    return ""


def get_tipo_da_unidade_pelo_id(unidade_id):
    try:
        return Unidade.objects.get(pk=unidade_id).tipo
    except Unidade.DoesNotExist:
        return None


def get_ruas(unidade_id):
    # PEGANDO AS RUAS DO IMOVEL URBANO
    return Rua.objects.filter(unidade_id=unidade_id)


def get_numero_registro_pelo_id(imovel_id):
    imovel = Livro02.objects.filter(pk=imovel_id).first()
    return imovel.numero if imovel else ""


# CHECKLIST COM AS QUESTOES DO BALCAO
class ChecklistBalcao(models.Model):
    # O = opcao de escolha ou seja vira RADIOBUTTON
    # T = Texto para digitar   ou seja vira tabela ChecklistBalcaoAtoTexto

    text: str = models.CharField(max_length=300)
    atos = models.ForeignKey(AtoPratica, on_delete=models.CASCADE, default=0)
    ordem = models.BigIntegerField(default=0)
    tipo_pergunta: str = models.CharField(
        max_length=1,
        choices=(
            ("O", "Opcão"),
            ("T", "Texto"),
        ),
        default="O",
    )

    # R = So perguntas de imovel RURAL |
    # U = So perguntas de imovel URBANO |
    # T = Todas as classes de imovel
    tipo_do_imovel: str = models.CharField(
        max_length=1,
        choices=TipoClasseRegistro.CHOICES,
        default=TipoClasseRegistro.URBANO,
    )
    titulo_informacao: str = models.CharField(
        max_length=1,
        choices=(
            ("O", "Opcão"),
            ("T", "Texto"),
        ),
        default="T",
    )

    class Meta:
        verbose_name = "Checklist Balcao"
        verbose_name_plural = "Checklist Balcao"

    def __str__(self) -> str:
        return self.text


class ChecklistBalcaoAto(models.Model):
    checklist_balcao = models.ForeignKey(ChecklistBalcao, on_delete=models.CASCADE)
    texto_escolha: str = models.CharField(max_length=300, default=TipoSimNao.NAO)
    atos = models.ForeignKey(AtoPratica, on_delete=models.CASCADE, default=0)
    ordem = models.BigIntegerField(default=0)
    observacao = CKEditor5Field(
        "Conteudo",
        blank=True,
        null=True,
        config_name="default",
    )
    created_at: datetime = models.DateTimeField(auto_now_add=True)
    updated_at: datetime = models.DateTimeField(auto_now=True)
    impeditivo: bool = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Checklist Balcao Ato"
        verbose_name_plural = "Checklist Balcao Ato"

    def __str__(self) -> str:
        return self.texto_escolha


class ChecklistBalcaoAtoTexto(models.Model):
    checklist_balcao_ato = models.ForeignKey(
        ChecklistBalcaoAto,
        on_delete=models.CASCADE,
    )
    texto_escolha: str = models.CharField(max_length=300, default="NAO")
    grupo = models.BigIntegerField(default=0)
    observacao = CKEditor5Field(
        "Conteudo",
        blank=True,
        null=True,
        config_name="default",
    )
    created_at: datetime = models.DateTimeField(auto_now_add=True)
    updated_at: datetime = models.DateTimeField(auto_now=True)
    impeditivo: bool = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Checklist Balcao Ato Texto"
        verbose_name_plural = "Checklist Balcao Ato Texto"

    def __str__(self) -> str:
        return self.texto_escolha


# PERGUNTA AS QUESTOES DO BALCAO
class ChecklistBalcaoEscolha(models.Model):
    pergunta_ato = models.ForeignKey(ChecklistBalcaoAto, on_delete=models.CASCADE)
    texto_escolha: str = models.CharField(max_length=300)
    checked: bool = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Checklist Balcao Escolha"
        verbose_name_plural = "Checklist Balcao Escolha"

    def __str__(self) -> str:
        return self.texto_escolha


# ORDEM PARA DIGITALIZAR COM AS QUESTOES DO BALCAO
class OrdemDigitalizarBalcao(models.Model):
    text: str = models.CharField(max_length=300)

    class Meta:
        verbose_name = "Ordem para Digitalizar"
        verbose_name_plural = "Ordens para Digitalizar"

    def __str__(self) -> str:
        return self.text


class OrdemDigitalizarBalcaoAto(models.Model):
    pergunta = models.ForeignKey(OrdemDigitalizarBalcao, on_delete=models.CASCADE)
    atos = models.ForeignKey(AtoPratica, on_delete=models.CASCADE)
    ordem = models.BigIntegerField()

    class Meta:
        verbose_name = "Ordem para Digitalizar Ato"
        verbose_name_plural = "Ordens para Digitalizar Ato"

    def __str__(self) -> str:
        return self.pergunta


# PERGUNTA AS QUESTOES DO BALCAO
class OrdemDigitalizarEscolha(models.Model):
    pergunta_ato = models.ForeignKey(
        OrdemDigitalizarBalcaoAto,
        on_delete=models.CASCADE,
    )
    texto_escolha: str = models.CharField(max_length=300)
    checked: bool = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Ordem para Digitalizar Escolha"
        verbose_name_plural = "Ordens para Digitalizar Escolha"

    def __str__(self) -> str:
        return self.texto_escolha


class ImovelClasse(models.Model):
    tipo: str = models.CharField(max_length=1)
    descricao: str = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self) -> str:
        return self.tipo


class CertificadoDigital(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    usuarios = models.ManyToManyField(
        User,
        verbose_name="Usuários com Acesso",
        blank=True,
        help_text="Usuários com acesso ao certificado digital",
    )
    certificado = models.FileField(
        upload_to="certificados/",
        verbose_name="Certificado Digital",
        help_text="Arquivo do certificado digital (extensão .pfx)",
    )

    _senha: str = models.CharField(max_length=128)
    imagem_assinatura = models.ImageField(
        upload_to="imagens_assinatura/",
        blank=True,
        null=True,
        verbose_name="Imagem da Assinatura",
        help_text="A imagem será adicionada ao documento assinado digitalmente. Poder ser uma rubrica, uma informação ou uma logomarca.",
    )
    texto_assinatura: str = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        default="DOCUMENTO ASSINADO DIGITALMENTE",
    )

    class Meta:
        verbose_name = "Certificado Digital"
        verbose_name_plural = "Certificados Digitais"

    def __str__(self) -> str:
        return f"{self.cn} Valido até {self.data_validade}"

    def save(self, *args, **kwargs) -> None:
        super().save(*args, **kwargs)

    def set_senha(self, raw_password) -> None:
        self._senha = make_password(raw_password)

    def check_senha(self, raw_password):
        return check_password(raw_password, self._senha)

    @cached_property
    def cn(self) -> str:
        # Expressão regular para encontrar o padrão
        padrao = r"CN=([^:]+):(\d+)"

        # Busca no texto utilizando a expressão regular
        resultado = re.search(padrao, self.nome_certificado)

        return f"{resultado.group(1)}:{resultado.group(2)}"

    @property
    def senha(self) -> None:
        msg = "A senha não pode ser lida dessa forma."
        raise AttributeError(msg)

    @senha.setter
    def senha(self, value) -> None:
        self.set_senha(value)

    @cached_property
    def informacoes(self):
        if not self.certificado:
            return None

        try:
            from apps.home.utils.assinatura import extrair_informacoes_certificado

            return extrair_informacoes_certificado(self.certificado.path, self._senha)
        except Exception:
            print("Erro ao extrair informacoes certificado: ")
            return None

    @cached_property
    def nome_certificado(self):
        return self.informacoes.get("nome_completo", "")

    @cached_property
    def email_certificado(self):
        return self.informacoes.get("email", "")

    @cached_property
    def localizacao_certificado(self):
        return self.informacoes.get("localizacao", "")

    @cached_property
    def data_inicio_validade_certificado(self):
        return self.informacoes.get("data_inicio_validade", "")

    @cached_property
    def data_fim_validade_certificado(self):
        return self.informacoes.get("data_fim_validade", "")

    @cached_property
    def data_validade(self):
        return self.data_fim_validade_certificado


class MotivoAssinaturaDigital(models.Model):
    descricao: str = models.CharField(max_length=255)

    class Meta:
        verbose_name = "Motivo da Assinatura Digital"
        verbose_name_plural = "Motivos das Assinaturas Digitais"

    def __str__(self) -> str:
        return self.descricao


class TipoDocumentoAssinatura(models.Model):
    descricao: str = models.CharField(max_length=255)

    class Meta:
        verbose_name = "Tipo de Documento"
        verbose_name_plural = "Tipos de Documentos"

    def __str__(self) -> str:
        return self.descricao


class LogAssinaturaDigital(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    data_assinatura: datetime = models.DateTimeField(auto_now_add=True)
    documento = models.FileField(upload_to=helpers.get_documento_path)
    certificado = models.ForeignKey(CertificadoDigital, on_delete=models.CASCADE)
    motivo = models.ForeignKey(
        MotivoAssinaturaDigital,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        verbose_name = "Log de Assinatura Digital"
        verbose_name_plural = "Logs de Assinaturas Digitais"

    def __str__(self) -> str:
        return f"{self.motivo} - {self.certificado.nome_certificado}"


class Documento(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    criado_em: datetime = models.DateTimeField(auto_now_add=True)
    titulo: str = models.CharField(max_length=255, verbose_name="Título")
    arquivo = models.FileField(upload_to="documentos/", verbose_name="Arquivo")
    assinatura = models.BinaryField(
        null=True,
        blank=True,
        verbose_name="Assinatura Digital",
    )

    class Meta:
        verbose_name = "Documento"
        verbose_name_plural = "Documentos"
        ordering = ["-criado_em"]

    def __str__(self) -> str:
        return self.titulo

    def get_absolute_url(self):
        return reverse("home:documento_detail", args=[str(self.id)])


class GrupoDistribuicaoProtocolo(models.Model):
    id: uuid.uuid4 = UUIDPrimaryKeyField()
    colaborador = models.ForeignKey(Colaborador, on_delete=models.CASCADE, default="0")
    titulo = models.ForeignKey(Titulo, on_delete=models.CASCADE, blank=True, null=True)

    objects = models.Manager()

    class Meta:
        ordering = ["colaborador"]

    def __str__(self) -> str:
        field_values = []
        for field in self._meta.get_fields():
            field_values.append(str(getattr(self, field.name, "")))
        return " ".join(field_values)


class GrupoTipoAndamento(models.Model):
    id: uuid.uuid4 = UUIDPrimaryKeyField()

    tipo_andamento_principal = models.ForeignKey(
        TipoAndamento,
        on_delete=models.CASCADE,
        related_name="andamento_tipo_principal",
    )

    tipo_andamento_auxiliar = models.ForeignKey(
        TipoAndamento,
        on_delete=models.CASCADE,
        related_name="andamento_tipo_auxiliar",
    )

    ordem = models.BigIntegerField(null=True, default="0")

    class Meta:
        unique_together = ["tipo_andamento_principal", "tipo_andamento_auxiliar"]
        ordering = ["tipo_andamento_principal"]

    def __str__(self) -> str:
        field_values = []
        for field in self._meta.get_fields():
            field_values.append(str(getattr(self, field.name, "")))
        return " ".join(field_values)


class Backup(models.Model):
    arquivo = models.FileField(upload_to="backups/")
    criado_em: datetime = models.DateTimeField(auto_now_add=True)
    tamanho_arquivo = models.PositiveIntegerField(
        help_text="Tamanho do arquivo em bytes",
    )
    hash_verificacao: str = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        help_text="Hash SHA-256 do arquivo para verificação de integridade",
    )

    def __str__(self) -> str:
        return f"{self.arquivo.name} ({self.criado_em.strftime('%Y-%m-%d %H:%M')})"


class TipoModelo(models.Model):
    id: uuid.uuid4 = UUIDPrimaryKeyField()
    descricao: str = models.CharField(max_length=255)
    grupo_gerar_tipo_certidao: bool = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Modelo de Testo - Tipo"
        verbose_name_plural = "Modelo de Texto - Tipos"

    def __str__(self) -> str:
        return self.descricao


class ModeloTexto(models.Model):
    id: uuid.uuid4 = UUIDPrimaryKeyField()
    titulo: str = models.CharField(max_length=500)
    conteudo = CKEditor5Field("conteudo", null=True, blank=True)
    tipo = models.ForeignKey(TipoModelo, on_delete=models.CASCADE)
    ativo: bool = models.BooleanField(default=True)
    nome_cabecalho: str = models.CharField(max_length=100, null=True, blank=True)
    nome_rodape: str = models.CharField(max_length=100, null=True, blank=True)
    subtitulo: str = models.CharField(max_length=500, blank=True)
    created_at: datetime = models.DateTimeField(auto_now_add=True, null=True)
    updated_at: datetime = models.DateTimeField(auto_now=True, null=True)

    class Meta:
        verbose_name = "Modelo de Texto"
        verbose_name_plural = "Modelos de Textos"
        ordering = ["titulo"]

    def __str__(self) -> str:
        return self.titulo


class ChatRoom(models.Model):
    name: str = models.CharField(
        max_length=255,
        unique=True,
        verbose_name="Nome da Sala",
    )
    is_private: bool = models.BooleanField(default=False)
    participants = models.ManyToManyField(User, related_name="chatrooms")
    creator = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="created_rooms",
        verbose_name="Criador",
        null=True,
        blank=True,
    )
    created_at: datetime = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Criado em",
    )

    class Meta:
        verbose_name = "Sala de Chat"
        verbose_name_plural = "Salas de Chat"
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"{'Privado' if self.is_private else 'Grupo'}: Sala {self.id}"


class Message(models.Model):
    room = models.ForeignKey(
        ChatRoom,
        related_name="messages",
        on_delete=models.CASCADE,
        verbose_name="Sala",
    )
    author = models.ForeignKey(
        User,
        related_name="messages",
        on_delete=models.CASCADE,
        verbose_name="Autor",
    )
    content = models.TextField(verbose_name="Conteúdo")
    timestamp: datetime = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Enviada em",
    )

    class Meta:
        verbose_name = "Mensagem"
        verbose_name_plural = "Mensagens"
        ordering = ["timestamp"]

    def __str__(self) -> str:
        return f"{self.author}: {self.content[:50]}"


class Caixa(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    saldo_inicial = models.DecimalField(max_digits=10, decimal_places=2)
    saldo_atual = models.DecimalField(max_digits=10, decimal_places=2)
    data_abertura: datetime = models.DateTimeField(auto_now_add=True)
    data_fechamento: datetime = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Caixa {self.id} - {self.usuario.username}"


class Transacao(models.Model):
    caixa = models.ForeignKey(
        Caixa,
        on_delete=models.CASCADE,
        related_name="transacoes",
    )
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    descricao: str = models.CharField(max_length=255)
    data: datetime = models.DateTimeField(auto_now_add=True)
    tipo: str = models.CharField(
        max_length=10,
        choices=(("entrada", "Entrada"), ("saida", "Saída")),
    )

    def __str__(self):
        return f"{self.tipo} de R${self.valor}"


# class TipoUnidade(models.Model):
#     descricao:str = models.CharField(max_length=255)

#     def __str__(self):
#         return self.descricao

#     def get_default(self):
#         return TipoUnidade.objects.get_or_create(descricao="Padrão")[0]

#     @classmethod
#     def criar_padroes(cls) -> None:
#         # quadra, lote, eficicio, condominio, unidade
#         cls.objects.get_or_create(descricao="Quadra")
#         cls.objects.get_or_create(descricao="Lote")
#         cls.objects.get_or_create(descricao="Edifício")
#         cls.objects.get_or_create(descricao="Condomínio")
#         cls.objects.get_or_create(descricao="Unidade")
#         cls.objects.get_or_create(descricao="Fazenda")
#         cls.objects.get_or_create(descricao="Setor")
#         cls.objects.get_or_create(descricao="Rua")


class CertidaoEmitida(models.Model):
    matricula: str = models.CharField(max_length=100, verbose_name="Matrícula")
    usuario_emissor: str = models.CharField(
        max_length=100,
        verbose_name="Usuário Emissor",
    )
    data_emissao = models.DateField(verbose_name="Data de Emissão")
    protocolo_origem: str = models.CharField(
        max_length=100,
        verbose_name="Protocolo/Pedido de Origem",
    )

    def __str__(self):
        return f"{self.matricula} - {self.usuario_emissor}"


# Utiliza o operador walrus para lidar com valores None diretamente na conversão
def safe_decimal(value, fallback=0.0) -> Decimal:
    try:
        return Decimal(value)
    except (InvalidOperation, TypeError, ValueError):
        return Decimal(fallback)


class TipoArmazenamento(models.Model):
    nome: str = models.CharField(max_length=100, blank=True)

    class Meta:
        verbose_name = "Tipo de Armazenamento"
        verbose_name_plural = "Tipos de Armazenamento"

    def __str__(self) -> str:
        return self.nome


class Issqn(models.Model):
    data_inicio = models.DateField(default=settings.MINDATE, unique=True)
    percentual = models.DecimalField(
        blank=False,
        max_digits=5,
        decimal_places=2,
        default=0,
    )

    def __str__(self):
        return f"ISSQN de {self.data_inicio} até {self.data_fim if self.data_fim else 'indefinido'}"

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def clean(self):
        # Checa se já existe uma instância com a mesma data de início
        if (
            Issqn.objects.filter(data_inicio=self.data_inicio)
            .exclude(id=self.id)
            .exists()
        ):
            msg = "Já existe um período iniciado nesta data."
            raise ValidationError(msg)

    @property
    def data_fim(self):
        # Calcula a data de fim como um dia antes da data de início do próximo registro
        next_issqn = (
            Issqn.objects.filter(data_inicio__gt=self.data_inicio)
            .order_by("data_inicio")
            .first()
        )
        if next_issqn:
            return next_issqn.data_inicio - timedelta(days=1)
        return None

    @classmethod
    def create_default(cls) -> None:
        Issqn.objects.get_or_create(data_inicio=settings.MINDATE, percentual=3)


# class TipoCertidaoOnr(models.Model):
#     codigo:str = models.CharField(max_length=20, blank=True, null=True)
#     nome:str = models.CharField(max_length=100, blank=True, null=True)

#     def __str__(self):
#         return str(self.nome)

#     @classmethod
#     def popular_valores_padrao(cls) -> None:
#         valores_padrao = [
#             {"codigo": "1", "nome": "PROPRIEDADE/NEGATIVA DE PROPRIEDADE"},
#             {"codigo": "2", "nome": "VINTENÁRIA"},
#             {"codigo": "3", "nome": "MATRÍCULA DO IMÓVEL"},
#             {"codigo": "4", "nome": "TRANSCRIÇÃO"},
#             {"codigo": "5", "nome": "PACTO ANTENUPCIAL"},
#             {"codigo": "6", "nome": "ONUS"},
#             {"codigo": "7", "nome": "DOCUMENTO ARQUIVADO"},
#             {"codigo": "8", "nome": "CONVENÇÃO DE CONDOMÍNIO"},
#             {"codigo": "9", "nome": "LIVRO3-Garantias"},
#             {"codigo": "10", "nome": "OUTROS REGISTROS LIVRO3-Auxiliar"},
#             {"codigo": "12", "nome": "INTEIRO TEOR, ÔNUS E AÇÕES"},
#             {"codigo": "13", "nome": "POR QUESITO"},
#             {"codigo": "14", "nome": "NEGATIVA DE PENHOR"},
#             {"codigo": "15", "nome": "ÔNUS REAIS E AÇÕES REIPERSECUTÓRIAS"},
#         ]

#         for valor in valores_padrao:
#             cls.objects.get_or_create(codigo=valor["codigo"], defaults={"nome": valor["nome"]})


# class Anexo(models.Model):
#
#     nome_arquivo:str = models.CharField(max_length=100, blank=True)
#     endereco_arquivo:str = models.CharField(max_length=300, blank=True)
#     tipo_armazenamento = models.ForeignKey(
#         TipoArmazenamento,
#         on_delete=models.CASCADE,
#         null=True,
#     )
#     pedido = models.ForeignKey(PedidoCertidao, on_delete=models.CASCADE, null=True)

#     class Meta:
#         verbose_name = "Anexo"
#         verbose_name_plural = "Anexos"

#     def __str__(self) -> str:
#         return self.nome_arquivo


# class OrigemEvento(models.Model):
#     codigo:str = models.CharField(max_length=1, unique=True)
#     descricao:str = models.CharField(max_length=50)

#     def __str__(self):
#         return self.descricao


class SeloXML(models.Model):
    titulo: str = models.CharField(max_length=100)
    arquivo_xml = models.FileField(upload_to="documentos/")
    arquivo_assinado = models.FileField(
        upload_to="documentos_assinados/",
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = "Selo XML"
        verbose_name_plural = "Selos XML"

    def __str__(self) -> str:
        return self.titulo


class TipoCategoriaAvaliacao(models.Model):
    """Categoria Avalicao: Positiva, Negativa, Com Resalvas."""

    opcao: str = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        choices=(
            ("P", "Positiva"),
            ("N", "Negativa"),
            ("R", "Resalva"),
        ),
        default="P",
    )

    descricao: str = models.CharField(
        max_length=300,
        blank=True,
        null=True,
        default="",
        unique=True,
    )

    class Meta:
        verbose_name = "Categoria de Tipo de Avaliação"
        verbose_name_plural = "Categorias Tipo de Avaliações"
        ordering = ["descricao"]

    def __str__(self) -> str:
        return self.descricao


class AvaliacaoCategoria(BaseModel):
    id = models.BigAutoField(
        primary_key=True,
        verbose_name="ID",
        auto_created=True,
        serialize=False,
    )

    data: datetime = models.DateTimeField(
        db_index=True,
        blank=True,
        null=True,
        verbose_name="Data do Andamento",
    )

    categoria_avaliacao = models.ForeignKey(
        TipoCategoriaAvaliacao,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="categoria_avaliacao",
        verbose_name="Categoria_Avaliacao",
        help_text="Selecione a categoria",
    )

    texto = CKEditor5Field("Texto", config_name="default", blank=True, null=True)

    andamento = models.ForeignKey(
        Livro01Andamento,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="andamento_avaliacao",
        verbose_name="Andamento_Avaliacao",
        help_text="Selecione o andamento",
    )

    colaborador = models.ForeignKey(
        Colaborador,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="colaborador_avaliacao",
        verbose_name="Colaborador_Avaliacao",
        help_text="Selecione o colaborador",
    )

    class Meta:
        verbose_name = "Avaliação de Categoria"
        verbose_name_plural = "Tipo de Avaliações de Categorias"
        ordering = ["data"]

    def __str__(self) -> str:
        return self.data

class PerguntasIA(models.Model):
    pergunta = models.CharField(
        max_length=300,
        blank=True,
        null=False,
        default="",
        unique=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    enviado_email = models.BooleanField(default=False)

    def __str__(self):
        return self.pergunta or "(sem pergunta)"
