import logging
import re
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from functools import cached_property
from typing import TYPE_CHECKING
from urllib.parse import urlencode
import os
import httpx
from django.http import JsonResponse
from django.views.decorators.http import require_GET
import json

import unidecode
from auditlog.models import AuditlogHistoryField
from django.apps import apps
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError, models, transaction
from django.db.models import F, Max, Prefetch, Q, QuerySet, Sum
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.timezone import datetime
from django.utils.translation import gettext_lazy as _
from django_ckeditor_5.fields import CKEditor5Field

from apps.cartorios.models import Usuario as User
from apps.comum.mixins import (
    DocumentoMixin,
    EnderecoMixin,
)
from apps.comum.models import (
    BaseModel,
    DadosBancarios,
    Expediente,
    Feriado,
    PrazoLegal,
    TipoDocumento,
    TipoOrigem,
    TipoRegistroImobiliario,
)
from apps.comum.utils import calcular_data_com_workalendar
from apps.home import helpers, managers
from apps.home.mixins import PedidoONRMixin
from apps.home.models.models_home import (
    Colaborador,
    Configuracao,
    Event,
    Financeiro,
    Issqn,
    Livro02,
    Livro03,
    Livro05,
    ModeloTexto,
    SeloEletronico,
    TipoClasseRegistro,
    TipoTransacaoFinanceira,
    TipoTributacao,
    get_tributacao_outros_cobrar_taxa_judiciaria,
)
from apps.home.padroes import *
from apps.home.services import firebird, sqlserver
from core.middlewares import get_current_request
from core.utils.firebird_utils import FbConnection
from core.utils.formatacoes import (
    formatar_documento,
    formatar_nome,
)

logger = logging.getLogger(__name__)

logger.debug(f"Iniciando {__name__}")

imported = True

if TYPE_CHECKING:
    from django.db.models import Manager

    from apps.home.models import Andamentos


class Finalidade(models.Model):
    """Finalidades de um pedido de certidão de acordo com a ONR para atender a LPGD."""

    nome: str = models.CharField(max_length=300, blank=True, null=True)
    ativo: bool = models.BooleanField(default=True)

    objects: managers.FinalidadeManager = managers.FinalidadeManager()

    class Meta:
        verbose_name = "Finalidade"
        verbose_name_plural = "Finalidades"

    def __str__(self) -> str:
        return f"{self.nome}"

    def get_default_tipo_finalidade_id() -> int:
        return Finalidade.get_tipo_finalidade_default().id

    def get_tipo_finalidade_default() -> "Finalidade":
        return Finalidade.objects.get_or_create(id=99)[0]


class GrupoUsuarioAgendaCertidao(models.Model):
    colaborador = models.ForeignKey(Colaborador, on_delete=models.CASCADE, default="0")
    tipo_andamento = models.ForeignKey(
        "TipoAndamentoCertidao",
        to_field="codigo",
        on_delete=models.CASCADE,
    )

    class Meta:
        unique_together = ["colaborador", "tipo_andamento"]
        indexes = [
            models.Index(fields=["colaborador", "tipo_andamento"]),
        ]
        verbose_name = "Grupo de Usuario da Agenda de Certidao"
        verbose_name_plural = "Grupo de Usuario da Agenda de Certidao"

    def __str__(self) -> str:
        return f"{self.colaborador} - {self.tipo_andamento}"


class PedidoCertidao(BaseModel, PedidoONRMixin):
    numero_pedido = models.IntegerField(
        db_index=True,
        unique=True,
        verbose_name="Nº",
        help_text="Número do Pedido de Certidão.",
    )
    data_entrada: datetime = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Entrada",
        db_index=True,
    )
    data_pedido_onr: datetime = models.DateTimeField(
        null=True,
        verbose_name="Data do Pedido de Certidao na ONR",
    )
    observacao: str = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name="Anotações",
    )
    tipo_de_servico: str = models.CharField(max_length=1, blank=True, null=True)
    protocolo_onr: str = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        unique=True,
        db_index=True,
    )
    finalidade = models.ForeignKey(
        Finalidade,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    origem = models.ForeignKey(
        TipoOrigem,
        on_delete=models.CASCADE,
        null=True,
        related_name="certidoes_origem",
        default=TipoOrigem.get_default_tipo_origem,
        db_index=True,
    )  # type: ignore[assignment]

    numero_pedido_firebird: str = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Pedido de Certidão Firebird.",
        db_index=True,
    )

    cancelado_em: datetime = models.DateTimeField(
        null=True,
        verbose_name="Cancelamento",
    )
    data_selado: datetime = models.DateTimeField(null=True, verbose_name="Selado")

    senha_site: str = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        verbose_name="Senha do Site",
    )

    history: AuditlogHistoryField = AuditlogHistoryField()

    if TYPE_CHECKING:
        apresentante = Manager["Apresentante"]()
        imoveis = Manager["PedidoCertidaoImovel"]()
        pessoas = Manager["PedidoCertidaoPessoa"]()

    class Meta:
        verbose_name = "Pedido de Certidão"
        verbose_name_plural = "Pedidos de Certidões"
        indexes = [
            models.Index(fields=["numero_pedido"]),
            models.Index(fields=["origem_id", "data_entrada"]),
        ]

    def __str__(self: "PedidoCertidao") -> str:
        numero_pedido_formatado = f"Nº {self.numero_pedido}"
        data_entrada_formatada = (
            (f"Data: {self.data_entrada.strftime(settings.DATE_FORMAT_STR)}")
            if self.data_entrada
            else ""
        )
        nome_apresentante_formatado = (
            f"Apresentante: {self.nome_apresentante}" if self.nome_apresentante else ""
        )
        valor_total_formatado = (
            f"Total: R$ {self.total_pedido:.2f}" if self.total_pedido else ""
        )

        return f"{numero_pedido_formatado} | {data_entrada_formatada} | {nome_apresentante_formatado} | {valor_total_formatado} | {self.finalidade_formatada}"

    def save(self: "PedidoCertidao", *args, **kwargs) -> None:
        super().save(*args, **kwargs)

    def get_absolute_url(self: "PedidoCertidao"):
        return reverse("home:pedido_certidao_detalhes", kwargs={"pk": self.pk})

    def get_absolute_url_pessoa(self) -> str:
        return reverse("home:pedido_certidao_detalhes_imovel", kwargs={"pk": self.pk})

    def get_url_enviar_para_caixa(self: "PedidoCertidao") -> str:
        return reverse("home:pedido_certidao_enviar_ao_caixa", kwargs={"pk": self.pk})

    def get_url_emitir_etiqueta(self: "PedidoCertidao") -> str:
        return reverse("home:pedido_certidao_emitir_etiqueta", kwargs={"pk": self.pk})

    def get_url_gerar_selo_pedido_certidao(self: "PedidoCertidao") -> str:
        return reverse(
            "home:gerar_selo_pedido_certidao",
            kwargs={"pedido_id": self.pk, "origem_id": self.origem_id},
        )

    def get_url_pessoas_list(self):
        return reverse(
            "home:pedido_certidao_pessoas_list",
            kwargs={"pedido_id": self.pk},
        )

    def get_url_anexo_create(self):
        return reverse(
            "home:pedido_certidao_anexo_create",
            kwargs={"pedido_certidao_id": self.pk},
        )

    def get_url_anexos_list(self):
        return reverse(
            "home:pedido_certidao_anexos_list",
            kwargs={"pedido_certidao_id": self.pk},
        )

    @cached_property
    def primeiro(self) -> "PedidoCertidao":
        return PedidoCertidao.objects.all().order_by("numero_pedido").first()

    @cached_property
    def anterior(self) -> "PedidoCertidao":
        return (
            PedidoCertidao.objects.filter(numero_pedido__lt=self.numero_pedido)
            .order_by("numero_pedido")
            .last()
        )

    @cached_property
    def seguinte(self) -> "PedidoCertidao":
        return (
            PedidoCertidao.objects.filter(numero_pedido__gt=self.numero_pedido)
            .order_by("numero_pedido")
            .first()
        )

    @cached_property
    def ultimo(self) -> "PedidoCertidao":
        return PedidoCertidao.objects.all().order_by("numero_pedido").last()

    @cached_property
    def financeiro(self):
        return Financeiro.objects.filter(pedido_certidao_id=self.pk)

    @cached_property
    def descricao_cancelamento_financeiro(self):
        texto = (
            Financeiro.objects.filter(
                numero_pedido_certidao=self.numero_pedido,
                descricao_cancelado__isnull=False,
            )
            .values_list("descricao_cancelado", flat=True)
            .first()
        )

        return str(texto) if texto else ""

    @cached_property
    def quantidade_selos(self):
        """Retorna a quantidade de selos relacionados ao pedido de certidão."""
        quantide_selos_prime = len(self.selos)

        quantidade_de_selos_no_sqlserver = len(
            self.get_selos_do_pedido_certidao_sqlserver(),
        )

        quantidade_de_selos_no_firebird = len(
            self.get_selos_do_pedidod_certidao_firebird(),
        )

        return (
            quantide_selos_prime
            or quantidade_de_selos_no_sqlserver
            or quantidade_de_selos_no_firebird
        )

    @cached_property
    def forma_de_pagamento(self):
        operacoes = self.financeiro.values_list(
            "tipo_operacao_financeira__descricao",
            flat=True,
        ).distinct()

        # descricao de operações separadas por virgulas
        return ", ".join(operacoes)

    @cached_property
    def qualificacao(self):
        return f"Pedido de Certidão: {self.pk!s} - {self.nome_apresentante.upper()!s}"

    # DESVINCULAR o item CERTIDAO
    def desvicular_item_certidao(self, pedido_imovel, pedido_pessoa):
        # IMOVEL - DESVINCULAR
        if pedido_imovel:
            for item_imovel in pedido_imovel:
                certidoes = Certidao.objects.filter(imovel_id=item_imovel.id)
                for certidao in certidoes:
                    certidao.imovel_cancelado_id = certidao.imovel_id
                    certidao.imovel_id = None
                    certidao.save()

        # PESSOA - DESVINCULAR
        if pedido_pessoa:
            for item_pessoa in pedido_pessoa:
                certidoes = Certidao.objects.filter(pessoa_id=item_pessoa.id)
                for certidao in certidoes:
                    certidao.pessoa_cancelado_id = certidao.pessoa_id
                    certidao.pessoa_id = None
                    certidao.save()

    def registrar_andamento(
        self: "PedidoCertidao",
        tipo_andamento: "TipoAndamentoCertidao",
        descricao: str,
        usuario: "User",
    ) -> None:
        # Verifica se já existe um andamento com o mesmo tipo e descrição
        ultimo_andamento = self.andamentos.last()

        if (
            ultimo_andamento
            and ultimo_andamento.tipo_andamento == tipo_andamento
            and ultimo_andamento.descricao == descricao
        ):
            # Verifica se o tipo de andamento é o mesmo do último registrado
            # Caso o tipo e a descrição sejam os mesmos, não cria um novo andamento
            return

        # Cria um novo andamento caso não seja uma repetição
        PedidoCertidaoAndamento.objects.create(
            pedido=self,
            tipo_andamento=tipo_andamento,
            descricao=descricao,
            criado_por=usuario,
        )

    @property
    def request(self):
        return get_current_request()

    @cached_property
    def permitir_selar(self):
        return int(self.quantidade_certidoes) != int(self.quantidade_selos)

    @cached_property
    def certidoes(self: "PedidoCertidao") -> QuerySet["Certidao"]:
        return Certidao.objects.filter(
            Q(imovel__pedido__id=self.pk) | Q(pessoa__pedido__id=self.pk),
        )

    @cached_property
    def certidoes_de_imoveis(self: "PedidoCertidao") -> QuerySet["Certidao"]:
        return Certidao.objects.filter(imovel__pedido=self)

    @cached_property
    def certidoes_de_pessoas(self: "PedidoCertidao") -> QuerySet["Certidao"]:
        certidoes = Certidao.objects.filter(pessoa__pedido=self)
        return certidoes if certidoes else []

    @classmethod
    def get_proximo_numero_pedido(cls) -> int:
        ultimo_numero = (
            cls.objects.order_by("numero_pedido").last().numero_pedido
            if PedidoCertidao.objects.exists()
            else 0
        )
        return (ultimo_numero or 0) + 1

    def get_url_andamentos(self: "PedidoCertidao") -> str:
        return reverse("home:pedido_certidao_andamentos", kwargs={"pedido_id": self.pk})

    def registrar_andamento_recepcao(self: "PedidoCertidao") -> None:
        tipo_andamento_recepcao = self.get_recepcao
        PedidoCertidaoAndamento.objects.create(
            pedido=self,
            tipo_andamento=tipo_andamento_recepcao if tipo_andamento_recepcao else None,
            descricao=tipo_andamento_recepcao.descricao,
            criado_por=self.criado_por or User.get_current_user(),
            colaborador_destino=self.criado_por or User.get_current_user(),
        )

    def registrar_andamento_certidao(self: "PedidoCertidao", certidao) -> None:
        return PedidoCertidaoAndamento.objects.create(
            pedido=self,
            certidao=certidao,
            tipo_andamento=self.get_grupo_gerar_certidao,
            descricao="CERTIDAO",
            criado_por=self.criado_por or User.get_current_user(),
        )

    def registrar_andamento_selo(self: "PedidoCertidao", certidao=None) -> None:
        if PedidoCertidaoAndamento.objects.filter(
            certidao=certidao,
            tipo_andamento=PedidoCertidao.get_tipo_andamento_selo(),
        ).exists():
            msg = f"Com base nos andamentos, já existe ao menos um selo vinculado a este pedido de certidão: {self}"
            logger.warning(msg)
            return

        PedidoCertidaoAndamento.objects.create(
            pedido=self,
            certidao=certidao,
            tipo_andamento=PedidoCertidao.get_tipo_andamento_selo(),
            descricao="SELO ELETRONICO",
            criado_por=self.criado_por or User.get_current_user(),
        )

    @cached_property
    def andamentos(self: "PedidoCertidao") -> QuerySet["PedidoCertidaoAndamento"]:
        return PedidoCertidaoAndamento.objects.filter(pedido=self).order_by("data_hora")

    def get_first_andamento(self):
        return (
            PedidoCertidaoAndamento.objects.filter(pedido=self)
            .order_by("data_hora")
            .first()
        )

    def registrar_andamento_certidao_entregue(self, usuario) -> None:
        tipos_andamentos = TipoAndamentoCertidao.objects.filter(
            grupo_certidao_entregue=True,
        )

        if tipos_andamentos:
            for tipo_andamento in tipos_andamentos:
                PedidoCertidaoAndamento.objects.create(
                    pedido=self,
                    tipo_andamento=tipo_andamento,
                    data_hora=timezone.now(),
                    descricao="CERTIDAO ENTREGUE",
                    criado_por=usuario,
                    colaborador_destino=usuario,
                )

    def registrar_impressao_recibo(self: "PedidoCertidao", usuario) -> None:
        descricao = "Comprovante do pedido foi impresso."
        self.registrar_andamento(self.get_reciboimpresso, descricao, usuario)

    def registrar_cancelar_devolucao(self: "PedidoCertidao", usuario) -> None:
        descricao = "Cancelar e Devolver"
        devolvido = self.get_devolvido

        if devolvido:
            self.registrar_andamento(devolvido, descricao, usuario)

        # Cancelar o item CERTIDAO
        pedido_imovel = PedidoCertidaoImovel.objects.filter(pedido_id=self.pk)
        pedido_pessoa = PedidoCertidaoPessoa.objects.filter(pedido_id=self.pk)

        # DESVINCULAR o item CERTIDAO
        self.desvicular_item_certidao(pedido_imovel, pedido_pessoa)

    def registrar_andamento_pedido_recebido(self: "PedidoCertidao", usuario) -> None:
        descricao = "Pedido Recebido pelo colaborador."
        tipo_andamento_recebido = self.get_andamento_pedido_confirmado

        # BUSCAR ANDAMNTO RECEBIDO
        if not tipo_andamento_recebido:
            tipo_andamento_recebido = self.get_andamento_pedido_recebido
            self.registrar_andamento(tipo_andamento_recebido, descricao, usuario)

    def _sem_certidoes(self: "PedidoCertidao", conjunto) -> list:
        return [obj for obj in conjunto.all() if obj.quantidade_certidoes == 0]

    def get_anexos_url(self):
        return redirect("home:pedido_certidao_anexos")

    anexos = QuerySet["PedidoCertidaoAnexo"]

    @cached_property
    def anexos_count(self):
        return self.anexos.count()

    @cached_property
    def apresentante_sem_email(self: "PedidoCertidao") -> bool:
        # Verifica se o e-mail do apresentante não está cadastrado
        try:
            apresentante = self.apresentante
            _ = apresentante.email  # type: ignore[union-attr]
            return False
        except Apresentante.DoesNotExist:
            return True

    @cached_property
    def imoveis_sem_certidoes(self):
        return self._sem_certidoes(self.imoveis)

    @cached_property
    def pessoas_sem_certidoes(self):
        return self._sem_certidoes(self.pessoas)

    def _formatar_mensagem(self, objetos, tipo) -> str:
        quantidade = len(objetos)
        if quantidade > 0:
            # nomes = ", ".join(map(str, objetos))
            return f"{quantidade} {tipo} sem certidões."
        return ""

    @cached_property
    def mensagens(self):
        msgs = [
            self._formatar_mensagem(self.imoveis_sem_certidoes, "Imóveis"),
            self._formatar_mensagem(self.pessoas_sem_certidoes, "Pessoas"),
        ]
        if self.apresentante_sem_email:
            msgs.append(
                "Apresentante sem e-mail cadastrado. O e-mail é necessário para o envio de notificações.",
            )
        if not self.recibo_impresso:
            msgs.append("Recibo para o pedido ainda não foi impresso.")

        if self.quantidade_certidoes == 0:
            msgs.append("Nenhuma certidão foi adicionada ao pedido ainda.")

        return [msg for msg in msgs if msg]

    # VERIFICAR SE É NECESSÁRIO
    @staticmethod
    def get_proximo_numero_pedido_fb() -> int:
        from apps.home.services import firebird

        # max_val = PedidoCertidao.objects.aggregate(models.Max("numero_pedido"))["numero_pedido__max"] or 0
        # OBTER PROXIMO NUMERO DE PEDIDO FIREBIRD
        max_val = firebird.get_numero_pedido_certidao() or 0

        return int(max_val) + 1

    def verificar_pedido_cancelado(self: "PedidoCertidao") -> None:
        if self.cancelado_em:
            msg = "Pedido de Certidão cancelado. Não é possível selar certidões num pedido cancelado."
            logger.error(f"{msg} Pedido: {self.numero_pedido}")
            raise ValueError(msg)
        logger.debug(f"Pedido {self.numero_pedido} verificado: não está cancelado.")

    def selar_certdoes_no_firebird(self: "PedidoCertidao") -> None:
        with FbConnection() as db:
            try:
                logger.debug(
                    f"Iniciando selagem no Firebird para pedido {self.numero_pedido}.",
                )
                numero_selo, codigo_seguranca = (
                    firebird.selar_certidoes_do_pedido_certidao_fb(
                        self.numero_pedido,
                        db=db,
                    )
                )
                db.commit()

                if numero_selo and codigo_seguranca:
                    logger.debug(
                        f"Selagem bem-sucedida no Firebird para pedido {self.numero_pedido}.",
                    )
                    self.data_selado = timezone.now()
                    self.save()
                else:
                    msg = "Não foi possível selar este pedido. Verifique os dados do pedido."
                    logger.error(f"{msg} Pedido: {self.numero_pedido}")
                    raise ValueError(msg)

            except Exception as e:
                db.rollback()
                msg = f"ERRO ao tentar selar o pedido no Firebird: {e!s}"
                logger.exception(msg)
                raise

    def selar_certidoes_no_sqlserver(self: "PedidoCertidao") -> None:
        with sqlserver.SqlServerConnection():
            certidoes = self.certidoes_relacionadas
            logger.debug(
                f"Selando {certidoes.count()} certidões no SQLSERVER para o pedido {self.numero_pedido}.",
            )
            for certidao in certidoes:
                certidao.selar()

    @staticmethod
    def adicionar_andamento_selo(
        pedido_certidao: "PedidoCertidao",
    ) -> None:
        usuario = usuario or User.get_current_user()
        pedido_certidao.registrar_andamento(
            pedido_certidao.get_tipo_andamento_selo(),
            "Pedido de Certidão Selado.",
            usuario,
        )
        logger.debug(
            f"Andamento de selo registrado para pedido {pedido_certidao.numero_pedido} por {usuario.username}.",
        )

    def selar_certidoes_do_pedido(
        self: "PedidoCertidao",
        usuario: "User" = None,
    ) -> None:
        logger.info(f"Selando certidões do pedido {self.numero_pedido}.")

        self.verificar_pedido_cancelado()

        with transaction.atomic():
            if usuario.cartorio.usar_selo_sql_server != "S":
                self.selar_certdoes_no_firebird()
            else:
                self.selar_certidoes_no_sqlserver()

            self.registrar_andamento_selo()
            logger.info(f"Selagem concluída para o pedido {self.numero_pedido}.")

    @cached_property
    def recibo_impresso(self) -> bool:
        return PedidoCertidaoAndamento.objects.filter(
            pedido=self,
            tipo_andamento=TipoAndamentoCertidao.RECIBO_IMPRESSO,
        ).exists()

    # VERIFICAR SE É NECESSÁRIO

    def atualizar_numero_pedido(self, numero_pedido: str) -> None:
        """Atualiza o número do pedido após verificar se o novo número já está em uso."""
        # if PedidoCertidao.objects.filter(numero_pedido=novo_numero_pedido).exclude(id=self.id).exists():
        #    raise ValueError("Já existe um pedido com este número.")
        if self.numero_pedido == numero_pedido:
            return

        novo_numero_pedido = numero_pedido
        self.numero_pedido_firebird = novo_numero_pedido
        self.numero_pedido = novo_numero_pedido

        self.save()

    def get_certidoes_agrupadas(self):
        certidoes = self.certidoes_relacionadas.all()

        agrupamento = {}

        for certidao in certidoes:
            agrupamento_id = (
                certidao.nome_com_codigo,
                certidao.qualificacao,
                certidao.qualificacao_numero_imovel_pessoa,
                certidao.qualificacao_tributacao,
            )
            if agrupamento_id not in agrupamento:
                agrupamento[agrupamento_id] = {
                    "quantidade": Decimal("0.0"),
                    "emolumento_bruto_calculado": Decimal("0.0"),
                    "emolumento_liquido_calculado": Decimal("0.0"),
                    "taxa_fiscal_judiciaria_calculada": Decimal("0.0"),
                    "recompe_calculado": Decimal("0.0"),
                    "issqn_calculado": Decimal("0.0"),
                    "total": Decimal("0.0"),
                }
            agrupamento[agrupamento_id]["quantidade"] += 1
            agrupamento[agrupamento_id]["emolumento_bruto_calculado"] += (
                certidao.emolumento_bruto_calculado
            )
            agrupamento[agrupamento_id]["emolumento_liquido_calculado"] += (
                certidao.emolumento_liquido_calculado
            )
            agrupamento[agrupamento_id]["taxa_fiscal_judiciaria_calculada"] += (
                certidao.taxa_fiscal_judiciaria_calculada
            )
            agrupamento[agrupamento_id]["recompe_calculado"] += (
                certidao.recompe_calculado
            )
            agrupamento[agrupamento_id]["issqn_calculado"] += certidao.issqn_calculado
            agrupamento[agrupamento_id]["total"] += certidao.total

        return agrupamento

    @cached_property
    def finalidade_formatada(self) -> str:
        if self.finalidade:
            return (
                f"Finalidade: {self.finalidade.nome[:50]}"
                if self.finalidade.nome
                else ""
            )

        return "Finalidade: Não informado"

    @cached_property
    def quantidade_de_selos(self) -> int:
        """Retorna a quantidade de selos relacionados ao pedido de certidão."""
        certidoes: QuerySet[Certidao] = self.certidoes_relacionadas
        # Conta diretamente a quantidade de selos através das certidões relacionadas
        return certidoes.aggregate(total_selos=Count("selos_da_certidao"))[
            "total_selos"
        ]

    @cached_property
    def selos(self) -> list[SeloEletronico]:
        """Retorna todos os selos relacionados ao pedido de certidão."""
        certidoes: QuerySet[Certidao] = self.certidoes_relacionadas.prefetch_related(
            Prefetch("selos_da_certidao", queryset=SeloEletronico.objects.all()),
        )
        # Lista que vai acumular todos os objetos de selos
        todos_selos = []
        for certidao in certidoes:
            todos_selos.extend(certidao.selos_da_certidao.all())
        return todos_selos

    @cached_property
    def data_ultimo_selo(self: "PedidoCertidao") -> date | None:
        ultima_data = self.certidoes.annotate(
            ultima_data_hora=Max("selos_da_certidao__utilizado_em"),
        ).aggregate(
            ultima_data=Max("ultima_data_hora"),
        )["ultima_data"]

        # return ultima_data.date() if ultima_data else None
        return ultima_data if ultima_data else None

    @cached_property
    def ultimo_andamento(self: "PedidoCertidao") -> "PedidoCertidaoAndamento":
        return (
            PedidoCertidaoAndamento.objects.filter(pedido=self)
            .order_by("-data_hora")
            .first()
        )

    @cached_property
    # retonar a data dp prazo final do pedido com base no prazo do tipo de certidão com maior prazo.
    def data_prazo_final(self) -> date:
        """Retorna a data do prazo final do pedido."""
        prazo_final = None
        for certidao in self.certidoes_relacionadas:
            prazo_calculado = certidao.tipo_certidao.calcular_prazo_final(
                self.data_entrada,
            )
            if prazo_calculado and (not prazo_final or prazo_calculado > prazo_final):
                prazo_final = prazo_calculado

        # PRAZO DIAS UTEIS
        # prazo_default_dias_uteis = self.data_entrada + timedelta(days=5)

        # Atualizar a data prevista com base em dias uteis
        prazo_default_dias_uteis = helpers.get_data_util_em_x_dias(self.data_entrada, 5)

        return prazo_final or prazo_default_dias_uteis

    # @cached_property
    # def apresentante(self):
    #     return Apresentante.objects.filter(pedido=self).first()

    @cached_property
    def data_prevista(self) -> date:
        return self.data_prazo_final

    @cached_property
    def data_validade(self) -> date:
        return self.data_pedido + timedelta(days=5)

    @cached_property
    def apresentante(self) -> "Apresentante":
        return Apresentante.objects.filter(pedido=self).first()

    @cached_property
    def nome_apresentante(self) -> str:
        apresentante = Apresentante.objects.filter(pedido=self).first()
        return apresentante.nome if apresentante else "(Não Informado)"

    @cached_property
    def nome_interessado(self) -> str:
        apresentante: Apresentante | None = self.apresentante
        try:
            if apresentante is not None:
                return apresentante.interessado_nome or ""
            return ""
        except ObjectDoesNotExist:
            return ""

    @cached_property
    def certidoes_relacionadas(self) -> QuerySet["Certidao"]:
        return Certidao.objects.filter(
            Q(imovel__in=self.imoveis.all()) | Q(pessoa__in=self.pessoas.all()),
        ).distinct()

    @cached_property
    def quantidade_certidoes(self):
        total_certidoes_imovel = sum(
            imovel.quantidade_certidoes for imovel in self.imoveis.all()
        )
        total_certidoes_pessoa = sum(
            pessoa.quantidade_certidoes for pessoa in self.pessoas.all()
        )
        return total_certidoes_imovel + total_certidoes_pessoa

    @cached_property
    def total_emolumentos_pedido(self) -> Decimal:
        return sum(
            (
                certidao.emolumento_liquido_calculado
                for certidao in self.certidoes_relacionadas
            ),
            Decimal(0),
        )

    @cached_property
    def total_taxa_fiscal_judiciaria_pedido(self) -> Decimal:
        return sum(
            (
                certidao.taxa_fiscal_judiciaria_calculada
                for certidao in self.certidoes_relacionadas
            ),
            Decimal(0),
        )

    @cached_property
    def total_recompe_pedido(self) -> Decimal:
        return Decimal(
            sum(certidao.recompe_calculado for certidao in self.certidoes_relacionadas),
        )
        # print(valor)

    @cached_property
    def total_issqn_pedido(self) -> Decimal:
        valor = sum(
            Decimal(certidao.issqn_calculado)
            for certidao in self.certidoes_relacionadas
        )
        return Decimal(valor)

    @cached_property
    def total_pedido(self) -> Decimal:
        return Decimal(sum(certidao.total for certidao in self.certidoes_relacionadas))

    # property que organiza os valores totais numa string unica:
    @cached_property
    def descricao_valores_totais_pedido(self) -> str:
        return f"Emolumentos: R$ {self.total_emolumentos_pedido:.2f} | TFJ: R$ {self.total_taxa_fiscal_judiciaria_pedido:.2f} | RECOMPE: R$ {self.total_recompe_pedido:.2f} | ISSQN: R$ {self.total_issqn_pedido:.2f} | Total: R$ {self.total_pedido:.2f}"

    @cached_property
    def descricao_valores_totais_pedido_abreviado(self) -> str:
        return f"Emol: R$ {self.total_emolumentos_pedido:.2f} | TFJ: R$ {self.total_taxa_fiscal_judiciaria_pedido:.2f} | RECOMPE: R$ {self.total_recompe_pedido:.2f} | ISSQN: R$ {self.total_issqn_pedido:.2f} | Total: R$ {self.total_pedido:.2f}"

    @cached_property
    def protocolo_onr_formatado(self) -> str:
        return f"{self.protocolo_onr}" if self.protocolo_onr else ""

    @cached_property
    def origem_formatada(self) -> str:
        if self.protocolo_onr:
            return f"ONR: {self.protocolo_onr}"

        return f"{self.origem}" if self.origem else "Balcão"

    def get_origem_url(self):
        if self.protocolo_onr:
            return f"https://oficioeletronico.com.br/Cartorios/EmissaoCertidoes?modulo=cartoriospedidoscertidao&Protocolo={self.protocolo_onr}"
        return self.get_absolute_url()

    @cached_property
    def exportado(self) -> bool:
        if self.numero_pedido_firebird:
            return True
        else:
            with FbConnection() as db:
                return firebird.verificar_se_pedido_existe_por_numero_e_apresentante_no_firebird(
                    pedido_certidao_id=self.numero_pedido,
                    nome_apresentante=self.nome_apresentante,
                    opcao_pesquisa=0,
                    db=db,
                )

    @cached_property
    def selo_sqlserver(self):
        usar_selo_sql_server = Configuracao.usar_selo_sql_server()
        if not usar_selo_sql_server:
            return ""

        from apps.home.services import sqlserver

        with sqlserver.SqlServerConnection() as db:
            selo = db.get_selo_por_pedido_de_certidao(self.numero_pedido)

        if selo:
            selo = selo[0]

        return selo if selo else ""

    # @cached_property
    # def quantidade_selos(self):
    #     # Atualizar o selo no SQL SERVER
    #     usuario = get_current_user()

    #     if usuario.cartorio.usar_selo_sql_server == "S":
    #         return self.quantidade_selo_sqlserver
    #     else:
    #         certidoes = self.certidoes_relacionadas
    #         return SeloEletronico.objects.filter(certidao_id__in=certidoes).count()

    @cached_property
    def quantidade_selo_sqlserver(self):
        from apps.home.services import sqlserver

        with sqlserver.SqlServerConnection() as db:
            return db.get_quantidade_de_selos_por_pedido_de_certidao_inteiro(
                self.numero_pedido,
            )

    def atualizar_selo_principal_sqlserver(self):
        from apps.home.services import sqlserver

        with sqlserver.SqlServerConnection() as db:
            return db.set_atualizar_selo_princial(self.numero_pedido)

    def get_selos_do_pedido_certidao_sqlserver(self):
        from apps.home.services import sqlserver

        try:
            with sqlserver.SqlServerConnection() as db:
                selo = db.get_selo_por_pedido_de_certidao(self.numero_pedido)
        except Exception as e:
            logger.exception(f"ERRO SQLSERVER: {e!s}")
            return []

        return selo if selo else []

    def get_selos_do_pedidod_certidao_firebird(self) -> list:
        try:
            with FbConnection() as db:
                return firebird.get_selos_pedido_certidao(self.numero_pedido, db)
        except Exception as e:
            logger.exception(f"ERRO FIREBIRD: Ao buscar selos no Firebird: {e!s}")
            return []

    def calcular_data_prevista(self) -> date:
        """Calcula a data prevista para a entrega do pedido."""
        prazo_legal = PrazoLegal.objects.get(pk=1)
        return self.data_entrada + timedelta(days=prazo_legal.dias)

    def calcular_data_validade(self) -> date:
        """Calcula a data de validade do pedido."""
        prazo_legal = PrazoLegal.objects.get(pk=1)
        return self.data_entrada + timedelta(days=prazo_legal.dias_validade)

    # VERIFICAR SE ESSE PEDIDO FOI CANCELADO
    def verificar_se_pedido_cancelado(self):
        print(self.numero_pedido_firebird, "CANCELADO")
        with FbConnection() as db:
            quantidade = firebird.verificar_se_pedido_existe_por_numero_e_apresentante_no_firebird(
                pedido_certidao_id=self.numero_pedido,
                nome_apresentante__icontains="CANCELADO",
                opcao_pesquisa=0,
                db=db,
            )
        return quantidade or 0

    # VERIFICAR SE ESSE PEDIDO FOI CANCELADO
    def verificar_pedido(self):
        print(self.numero_pedido_firebird, "CANCELADO")
        with FbConnection() as db:
            quantidade = firebird.verificar_se_pedido_existe_por_numero_e_apresentante_no_firebird(
                pedido_certidao_id=self.numero_pedido_firebird,
                nome_apresentante="",
                opcao_pesquisa=1,
                db=db,
            )
        return quantidade or 0

    def enviar_para_caixa(self, usuario: User, valor_transacao) -> tuple[bool, str]:
        with transaction.atomic(), FbConnection() as db:
            """Exporta o pedido para o caixa."""
            financeiro = Financeiro.objects.registrar_pedido_de_certidao(self, usuario)

            if not financeiro:
                return (
                    False,
                    "Erro ao registrar o pedido de certidão no caixa. Verifique os dados do pedido.",
                )

            db.begin_transaction()
            caixa_fb, msg = firebird.gravar_caixa_fb(financeiro, db=db)
            db.commit()
            db.close()

            return (
                msg
                if msg
                else (True, "Pedido de {self.pk} Certidão enviado para o caixa.")
            )

        return False, "Erro ao enviar o pedido para o caixa."

    # REGISTRAR ENVIO PARA CAIXA NO POSTGRESQL
    @transaction.atomic
    def enviar_pagamento_certidao_onr_caixa(
        self,
        pk: int,
        numero_pedido: int,
        valor_transacao: Decimal,
        descricao: str,
        db: "FbConnection",
    ):
        data_original = timezone.now()
        tipo_operacao_financeira_id = 8  # ONR
        nome_pagador = ""
        tipo_transacao_id = TipoTransacaoFinanceira.get_receita().id or 1

        # COLABORADOR FINANCEIRO DA ONR
        colaborador_financeiro_id = User.get_usuario_caixa_certidao_onr_id() or 1

        # FILTRANDO PEDIDO DE CERTIDAO
        pedido_certidao = PedidoCertidao.objects.get(id=pk)

        pedido_certidao.enviar_para_pagamento_caixa(
            valor_transacao=valor_transacao,
            tipo_operacao_financeira_id=tipo_operacao_financeira_id,
            tipo_transacao_id=tipo_transacao_id,
            descricao=descricao,
            nome_pagador=nome_pagador,
            data_original=data_original,
            colaborador_financeiro_id=colaborador_financeiro_id,
        )

        # ATUALIZAR O PEDIDO DE CERTIDAO
        pedido_certidao.numero_pedido_firebird = pedido_certidao.numero_pedido
        pedido_certidao.save()

    @transaction.atomic
    def exportar_pedido_certidao_para_fb(
        self,
        descricao_observacao: str,
        origem_id: int,
        valor_transacao: Decimal,
        db: FbConnection,
    ) -> tuple[bool, str]:
        resultado, msg = self.pode_ser_exportado()
        if resultado is False:
            return (resultado, msg)

        # pedido_fb = firebird.get_pedido_por_numero_fb(self.numero_pedido, db)
        # if pedido_fb:
        #     msg = f"ERRO: PedidoCertidao {self.numero_pedido} já foi exportado."
        #     raise ValueError(msg)
        #     return False, msg

        try:
            pedido_fb = firebird.get_pedido_certidao_por_numero_fb(
                self.numero_pedido,
                db,
            )

            if not pedido_fb:
                pedido_fb = self.exportar_pedido_para_firebird(
                    descricao_observacao=descricao_observacao,
                    origem_id=origem_id,
                    valor_transacao=valor_transacao,
                    db=db,
                )

            # Pedido já foi exportado pelo signal, basta recupera-lo para continuar...

            if not pedido_fb:
                msg = "ERRO: ao tentar exportar o pedido. Pedido_fb é None."
                raise ValueError(msg)
                return False, msg

            try:
                self.exportar_pessoas_para_firebird(pedido_fb, db=db)
            except Exception as e:
                logger.exception(f"ERRO ao exportar pessoas para FB: {e}")
                raise

            try:
                self.exportar_imoveis_para_firebird(pedido_fb, db=db)
            except Exception as e:
                logger.exception(f"ERRO ao exportar imóveis para FB: {e}")
                raise

            try:
                self.exportar_andamento_para_firebird(pedido_fb, db=db)
            except Exception as e:
                logger.exception(f"ERRO ao exportar andamentos para FB: {e}")
                raise

            try:
                self.atualizar_numero_pedido(
                    numero_pedido=pedido_fb["CHAVE_PED_CERTIDOES"],
                )
            except Exception as e:
                logger.exception(f"ERRO ao atualizar o número do pedido: {e}")
                raise

            try:
                self.atualizar_pedido_firebird(pedido_fb, db=db)
            except Exception as e:
                logger.exception(f"ERRO ao atualizar o pedido de certidao no FB: {e}")
                raise

            try:
                self.exportar_caixa_para_firebird(pedido_fb, origem_id=origem_id, db=db)
            except Exception as e:
                logger.exception(f"ERRO ao exportar caixa para o FB: {e}")
                raise

            return (
                True,
                f"PedidoCertidao {self.numero_pedido} exportado com o ID {pedido_fb['CHAVE_PED_CERTIDOES']}.",
            )

        except Exception as e:
            msg = f"ERRO ao tentar exportar o pedido: {e}"
            logger.exception(msg)
            raise

    @cached_property
    def pode_exportar(self) -> bool:
        return self.numero_pedido_firebird is None

    def pode_ser_exportado(self) -> tuple[bool, str]:
        import apps.home.services.firebird as firebird

        # PROTOCOLO FIREBIRD ATUALIZAR
        numero_pedido_firebird = self.numero_pedido_firebird
        cartorio_model = apps.get_model("cartorios", "Cartorio")

        # LIMPAR TODO O PEDIDO PARA QUE SEJA ATUALIZADO NOVAMENTE
        atualizar_somente_caixa = cartorio_model.objects.all().values_list(
            "atualizar_somente_caixa",
            flat=True,
        )[0]
        if str(atualizar_somente_caixa) == "S":
            firebird.deletar_pedido_certidao_fb(self.numero_pedido)
            numero_pedido_firebird = None

        # VERIFICAR SE ESSE PEDIDO JA FOI ENVIADO OU DEU ERRO
        if numero_pedido_firebird:
            if self.exportado == 0:
                msg = f"Este pedido já foi exportado. {self.numero_pedido_firebird}. Verifique se é necessárioa atualizar os dados do pedido."
                print(msg)
                return False, msg
                # return False, msg
            elif self.exportado > 0:
                # APENAS ATUALIZAR O PEDIDO QUE FOI CANCELADO
                msg = f"Este pedido já foi exportado. Numero: {self.numero_pedido_firebird} Não pode ser exportado novamente. Verificar se foi cancelado."
                print(msg)
                return False, msg
                # return False, msg
            msg = f"Este pedido já foi exportado. Numero: {self.numero_pedido_firebird}. Não pode ser exportado novamente."
            print(msg)
            return False, msg

        msg = "Este pedido pode ser exportado."
        print(msg)
        return True, msg

    def exportar_andamento_para_firebird(
        self,
        pedido_fb: dict,
        db: FbConnection,
    ) -> None:
        andamentos: list[PedidoCertidaoAndamento] = self.andamentos.all()
        logger.info(f"Verificando {andamentos.count()} andamento(s) no pedido.")

        for andamento in andamentos:
            self.gravar_andamento_fb(
                andamento,
                pedido_fb,
                andamento.criado_por.id,
                db=db,
            )

    def atualizar_pedido_firebird(
        self: "PedidoCertidao",
        pedido_fb: dict,
        db: FbConnection,
    ) -> None:
        logger.info(f"Atualizando o pedido {self.numero_pedido}.")
        firebird.atualizar_ped_certidoes(pedido_fb, db)

    def enviar_para_pagamento(self):
        Financeiro.receber_pedido_certidao(self)

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
        Financeiro.receber_pedido_certidao_caixa(
            self,
            valor_transacao=valor_transacao,
            tipo_operacao_financeira_id=tipo_operacao_financeira_id,
            tipo_transacao_id=tipo_transacao_id,
            descricao=descricao,
            nome_pagador=nome_pagador,
            data_original=data_original,
            colaborador_financeiro_id=colaborador_financeiro_id,
        )

    def exportar_caixa_para_firebird(
        self: "PedidoCertidao",
        pedido_fb: dict,
        db: FbConnection,
        origem_id=0,
    ) -> None:
        logger.info(
            f"Exportando caixa do pedido de certidão, Numero: {self.numero_pedido}.",
        )

        try:
            # Atualizar o selo no SQL SERVER
            usuario = User.get_usuario_sistema()
            if usuario.cartorio.usar_selo_sql_server == "S":
                pass
            else:
                firebird.gravar_caixa_ped_certidao_fb(
                    pedido_fb=pedido_fb,
                    pedido=self,
                    origem_id=origem_id,
                    db=db,
                )
        except Exception as e:
            logger.exception(f"ERRO ao exportar caixa para o FB: {e}")

    def exportar_pedido_para_firebird(
        self,
        db: FbConnection,
        descricao_observacao=None,
        origem_id=1,
        valor_transacao=0,
    ) -> dict:
        logger.info(f"Exportando o pedido {self.numero_pedido}.")
        return firebird.gravar_ped_certidao_fb(
            pedido_certidao=self,
            descricao_observacao=descricao_observacao,
            origem_id=origem_id,
            valor_transacao=valor_transacao,
            db=db,
        )

    def exportar_pessoas_para_firebird(
        self: "PedidoCertidao",
        pedido_fb: dict,
        db: FbConnection,
    ) -> None:
        logger.info(f"Exportando pessoas do pedido {self.numero_pedido}.")
        pessoas: list[PedidoCertidaoPessoa] = self.pessoas.all()
        num_pessoas: int = pessoas.count()
        logger.info(f"Verificando a existência de {num_pessoas} pessoa(s) no pedido.")

        for pessoa in pessoas:
            pessoa_fb = self.gravar_pessoa_fb(pessoa, pedido_fb, db=db)

            if pessoa_fb is None:
                logger.error("ERRO ao gravar pessoa.")
                break

            certidoes = pessoa.certidoes_pessoa.all()
            num_certidoes = certidoes.count()

            if num_certidoes:
                print(
                    f"Iterando sobre as {num_certidoes} certidão(ões) da pessoa {pessoa.nome}.",
                )
                for certidao in certidoes:
                    resultado = self.gravar_certidao_fb(certidao, pedido_fb, db=db)
                    if resultado is None:
                        logger.error("ERRO ao gravar o tipo de certidão.")
                        break
            else:
                logger.info(f"{num_certidoes} certidão(ões) da pessoa {pessoa.nome}.")

    def gravar_pessoa_fb(
        self,
        pessoa: "PedidoCertidaoPessoa",
        pedido_fb: dict,
        db: FbConnection,
    ) -> None:
        estado_civil = pessoa.estado_civil.pk or 0 if pessoa.estado_civil else 0

        return firebird.gravar_pessoa_ped_certidao_fb(
            pedido_id=pedido_fb["CHAVE_PED_CERTIDOES"],
            nome=pessoa.nome or "",
            documento=pessoa.documento or "",
            estado_civil=estado_civil,
            complemento=pessoa.complemento or "",
            db=db,
        )

    def exportar_imoveis_para_firebird(self, pedido_fb: dict, db: FbConnection) -> None:
        imoveis = self.imoveis.all()
        num_imoveis = imoveis.count()
        logger.info(f"Verificando {num_imoveis} imóvel(is) no pedido.")

        for imovel in imoveis:
            resultado = self.gravar_imovel_fb(imovel, pedido_fb, db=db)

            if resultado is None:
                msg = f"ERRO ao gravar o imóvel: {imovel}."
                logger.exception(msg)
                raise ValueError(msg)

            certidoes_imovel = imovel.certidoes_imovel.all()

            for certidao in certidoes_imovel:
                resultado = self.gravar_certidao_fb(certidao, pedido_fb, db=db)
                if resultado is None:
                    msg = f"ERRO ao gravar o tipo de certidão. Certidão: {certidao}"
                    logger.exception(msg)
                    raise ValueError(msg)

    def gravar_imovel_fb(
        self,
        imovel: "PedidoCertidaoImovel",
        pedido_fb: dict,
        db: FbConnection,
    ) -> None:
        return firebird.gravar_imoveis_ped_certidao_fb(
            pedido_id=pedido_fb["CHAVE_PED_CERTIDOES"],
            matricula=imovel.numero_registro,
            cartorio=imovel.cartorio,
            livro=imovel.livro,
            db=db,
        )

    def gravar_andamento_fb(
        self: "PedidoCertidao",
        andamento: "Andamentos",
        pedido_fb: dict,
        user_id: int,
        db: FbConnection,
    ):
        return firebird.gravar_andamentos_pedido_certidao(
            pedido_id=pedido_fb["CHAVE_PED_CERTIDOES"],
            data=andamento.data_hora.strftime(settings.DATETIME_FIREBIRD_FORMAT),
            # funcionario_id=Configuracao.obter("funcionario_id_sistema_antigo"),
            funcionario_id=user_id,
            # tipo_andamento_id=andamento.pk,
            tipo_andamento_id=1,  # RECEPCAO
            db=db,
        )

    def gravar_certidao_fb(
        self: "PedidoCertidao",
        certidao,
        pedido_fb,
        db: FbConnection,
    ):
        logger.debug(
            f"Iniciando gravação da certidão para o pedido {pedido_fb['CHAVE_PED_CERTIDOES']}",
        )
        percentual_desconto = self.calcular_percentual_desconto(certidao)
        logger.debug(f"Percentual de desconto calculado: {percentual_desconto}")

        certidao_id_sistema_antigo = self.obter_certidao_id_sistema_antigo(
            certidao,
            percentual_desconto,
        )
        logger.debug(
            f"ID da certidão no sistema antigo obtido: {certidao_id_sistema_antigo}",
        )

        funcionario_id = self.obter_funcionario_id()
        logger.debug(f"ID do funcionário obtido: {funcionario_id}")

        codigo_tabela = self.verificar_codigo_tabela(certidao)
        logger.debug(f"Código da tabela verificado: {codigo_tabela}")

        certidao_id_sistema_antigo = self.verificar_certidao_id_sistema_antigo(
            certidao,
            certidao_id_sistema_antigo,
        )
        logger.debug(
            f"ID da certidão no sistema antigo verificado: {certidao_id_sistema_antigo}",
        )

        resultado = firebird.gravar_tipos_ped_certidao(
            pedido_id=pedido_fb["CHAVE_PED_CERTIDOES"],
            percentual_desconto=percentual_desconto,
            codigo_tabela=codigo_tabela,
            quantidade=1,
            funcionario_id=funcionario_id,
            certidao_id_sistema_antigo=certidao_id_sistema_antigo,
            tipo_tributacao_outros_id=certidao.tipo_tributacao.outros_codigo_trib_tj,
            db=db,
        )
        logger.debug(f"Resultado da gravação: {resultado}")
        return resultado

    def calcular_percentual_desconto(self, certidao):
        percentual_desconto = (
            certidao.tipo_tributacao.percentual_desconto
            if certidao.tipo_tributacao.percentual_desconto in [0, 50, 100]
            else 100
        )
        logger.debug(
            f"Calculado percentual de desconto: {percentual_desconto} para a certidão {certidao}",
        )
        return percentual_desconto

    def obter_certidao_id_sistema_antigo(self, certidao, percentual_desconto):
        if (
            percentual_desconto == 50
            and certidao.tipo_certidao.certidao_id_sistema_antigo_50
        ):
            certidao_id = certidao.tipo_certidao.certidao_id_sistema_antigo_50
        elif (
            percentual_desconto == 100
            and certidao.tipo_certidao.certidao_id_sistema_antigo_isento
        ):
            certidao_id = certidao.tipo_certidao.certidao_id_sistema_antigo_isento
        else:
            certidao_id = certidao.tipo_certidao.certidao_id_sistema_antigo
        logger.debug(
            f"Obtido ID da certidão no sistema antigo: {certidao_id} para a certidão {certidao}",
        )
        return certidao_id

    def obter_funcionario_id(self):
        try:
            funcionario_id = Configuracao.obter("funcionario_id_sistema_antigo", 1)
        except Exception as e:
            logger.exception(
                f"ERRO ao obter o ID do funcionário do sistema antigo. Definindo como 1: {e}",
            )
            funcionario_id = 1
        logger.debug(f"Obtido ID do funcionário: {funcionario_id}")
        return funcionario_id

    def verificar_codigo_tabela(self, certidao):
        codigo_tabela = certidao.tipo_certidao.codigo
        if str(codigo_tabela) == "0":
            logger.warning(
                f"Certidão {certidao} não possui código de tabela. Definindo como 8401-2.",
            )
            codigo_tabela = "8401-2"  # INTEIRO TEOR
        logger.debug(
            f"Verificado código da tabela: {codigo_tabela} para a certidão {certidao}",
        )
        return codigo_tabela

    def verificar_certidao_id_sistema_antigo(
        self,
        certidao,
        certidao_id_sistema_antigo,
    ):
        if str(certidao_id_sistema_antigo) == "0":
            logger.warning(
                f"Certidão {certidao} não possui ID no sistema antigo. Definindo como 375.",
            )
            certidao_id_sistema_antigo = "375"  # INTEIRO TEOR
        logger.debug(
            f"Verificado ID da certidão no sistema antigo: {certidao_id_sistema_antigo} para a certidão {certidao}",
        )
        return certidao_id_sistema_antigo

    # PEDIDOS DE CERTIDÃO DE MATRÍCULA VISUALIZADA NO DIA ATUAL
    def onr_matricula_visualizada(
        self: "PedidoCertidao",
        data_inicio=None,
        data_fim=None,
    ):
        # Se data_inicio for None, define como a data atual
        if data_inicio is None:
            data_inicio = timezone.now().date()
        else:
            # Garante que data_inicio esteja no formato correto
            try:
                data_inicio = timezone.datetime.strptime(data_inicio, "%Y-%m-%d").date()
            except ValueError as e:
                msg = "data_inicio deve estar no formato YYYY-MM-DD"
                raise ValueError(msg) from e

        # Se data_fim for None, define como o dia seguinte à data atual
        if data_fim is None:
            data_fim = data_inicio + timedelta(1)
        else:
            # Garante que data_fim esteja no formato correto
            try:
                data_fim = timezone.datetime.strptime(data_fim, "%Y-%m-%d").date()
            except ValueError as e:
                msg = "data_fim deve estar no formato YYYY-MM-DD"
                raise ValueError(msg) from e

        return PedidoCertidao.objects.filter(
            origem_id=2,
            data_entrada__range=[data_inicio, data_fim],
        ).order_by("numero_pedido")

    # PEDIDOS DE CERTIDÃO DE OFICIO NO DIA ATUAL
    def onr_oficio(
        self: "PedidoCertidao",
        data_inicio=None,
        data_fim=None,
    ):
        data_inicio = data_inicio or timezone.now().date()
        data_fim = data_fim or timezone.now().date() + timedelta(1)

        return PedidoCertidao.objects.filter(
            origem_id=3,
            data_entrada__range=[data_inicio, data_fim],
        ).order_by("numero_pedido")

    # @cached_property
    # def caixa(self):
    #     return Financeiro.objects.filter(pedido=self.pedido_id)

    @cached_property
    def valor_total_caixa_numero_pedido(self):
        # Método para atualizar as fases do protocolo
        return (
            Financeiro.objects.total_caixa_pedido_certidao_numero_pedido(
                self.numero_pedido,
            )
            or 0
        )

    @cached_property
    def valor_total_caixa(self):
        # Método para atualizar as fases do protocolo
        return Financeiro.objects.total_caixa_pedido_certidao(self.pk) or 0

    @cached_property
    def valor_diferenca(self):
        return (self.total_pedido - self.valor_total_caixa) or 0

    @cached_property
    def descricao_certidoes_imovel_relacionadas(self):
        imoveis_numeros = self.imoveis.all().values_list(
            "tipo_registro",
            "numero_registro",
            "logradouro",
            "quadra",
            "lote",
            "complemento",
            "descricao",
            "anotacoes",
        )

        # Cria uma lista de strings, cada uma representando uma tupla formatada
        # imoveis_numeros_str = [
        #     f"{tipo_registro}.{numero_registro} - {logradouro} - {quadra} - {lote} - {complemento} - {anotacoes} - {descricao}"
        #     for tipo_registro, numero_registro, logradouro, quadra, lote, complemento, anotacoes, descricao in imoveis_numeros
        # ]
        # Obtenha todos os tipos de registros imobiliários de uma vez
        tipos_registro_dict = {
            tipo.id: tipo.nome for tipo in TipoRegistroImobiliario.objects.all()
        }

        imoveis_numeros_str = []
        for (
            tipo_registro,
            numero_registro,
            logradouro,
            quadra,
            lote,
            complemento,
            anotacoes,
            descricao,
        ) in imoveis_numeros:
            tipo_registro_str = tipos_registro_dict.get(
                tipo_registro,
                "Tipo Desconhecido",
            )

            imoveis_numeros_str.append(
                f"{tipo_registro_str}: {numero_registro} - {logradouro} - {quadra} - {lote} - {complemento} - {anotacoes} - {descricao}",
            )

        # Junta essas strings em uma única string, separada por vírgulas
        imoveis_numeros_str = ", ".join(imoveis_numeros_str)
        return (
            str(imoveis_numeros_str)
            .replace("- None", "")
            .replace(" .", ".")
            .replace("None", "")
            .replace("None", "")
            .replace("- - -", "")
            .replace("- -", "")
            .replace("- - - -", "")
        )

    @cached_property
    def descricao_certidoes_pessoas_relacionadas(self):
        pessoas_numeros = self.pessoas.all().values_list(
            "nome",
            "documento",
            "complemento",
            "anotacoes",
            "endereco",
        )
        # Cria uma lista de strings, cada uma representando uma tupla formatada
        pessoas_numeros_str = [
            f"{nome} - {documento} - {complemento} - {anotacoes} - {endereco}"
            for nome, documento, complemento, anotacoes, endereco in pessoas_numeros
        ]
        # Junta essas strings em uma única string, separada por vírgulas
        pessoas_numeros_str = ", ".join(pessoas_numeros_str)
        return (
            str(pessoas_numeros_str)
            .replace("- None", "")
            .replace(" .", ".")
            .replace("None", "")
            .replace("None", "")
            .replace("- - -", "")
            .replace("- -", "")
            .replace("- - - -", "")
        )

    @cached_property
    def nome_pagador(self) -> str:
        nome_pagador = Financeiro.objects.filter(pedido_certidao_id=self.id).first()
        return nome_pagador.nome_interessado if nome_pagador else ""

    @property
    def cancelado(self):
        # Verificar se o pedido de certidao esta CANCELADO
        tipo_cancelado = list(
            TipoAndamentoCertidao.objects.filter(grupo_cancelado=True).values_list(
                "codigo",
                flat=True,
            ),
        )
        cancelado = PedidoCertidaoAndamento.objects.filter(
            pedido_id=self.id,
            ativo=True,
            tipo_andamento__in=tipo_cancelado,
        ).exists()

        return bool(cancelado)

    @property
    def exigencia(self):
        # Verificar se o pedido de certidao esta com EXIGENCIA
        tipo_exigencia = list(
            TipoAndamentoCertidao.objects.filter(
                grupo_certidao_exigencia=True,
            ).values_list(
                "codigo",
                flat=True,
            ),
        )
        exigencia = PedidoCertidaoAndamento.objects.filter(
            pedido_id=self.id,
            ativo=True,
            tipo_andamento__in=tipo_exigencia,
        ).exists()

        return bool(exigencia)

    @property
    def get_devolvido(self):
        # Verificar se o pedido de certidao esta CANCELADO
        tipo_devolucao = TipoAndamentoCertidao.objects.filter(
            grupo_devolucao=True,
        ).first()

        if tipo_devolucao:
            return tipo_devolucao
        else:
            codigo = (
                TipoAndamentoCertidao.objects.aggregate(
                    max_codigo=models.Max("codigo"),
                )["max_codigo"]
                + 1
            )
            # Verifica se já existe algum registro com "Devolução" na descrição
            tipo_devolucao, created = TipoAndamentoCertidao.objects.get_or_create(
                descricao__icontains="Devolução",
                defaults={"codigo": codigo, "grupo_devolucao": True},
            )

        return tipo_devolucao

    @property
    def get_grupo_gerar_certidao(self) -> "TipoAndamentoCertidao":
        # Verificar se o pedido de certidao está PRONTO PARA grupo_gerar_certidao
        gerar_certidao = TipoAndamentoCertidao.objects.filter(
            grupo_gerar_certidao=True,
        ).first()

        if gerar_certidao:
            return gerar_certidao
        else:
            try:
                # Tenta criar um novo objeto se não existir
                return TipoAndamentoCertidao.objects.create(
                    codigo=0,  # Certifique-se de que '0' não cause duplicação ou seja gerado dinamicamente
                    descricao="Pedido Gerado para Envio",
                    grupo_gerar_certidao=True,
                )
            except IntegrityError:
                # Se já existir, retorna o objeto existente or codigo 0
                return TipoAndamentoCertidao.objects.get(codigo=0)

    @property
    def get_recepcao(self) -> "TipoAndamentoCertidao":
        """
        Obtém o objeto TipoAndamentoCertidao com o grupo_recepcao definido como True.
        Se não existir, cria um novo com a descrição "Recepção".

        Returns
        -------
            Optional[TipoAndamentoCertidao]: O objeto TipoAndamentoCertidao correspondente ou None.

        """
        try:
            # Tenta recuperar o objeto com grupo_recepcao=True
            recepcao = TipoAndamentoCertidao.objects.filter(grupo_recepcao=True).first()

            # Se não encontrar, cria um novo com a descrição "Recepção"
            if not recepcao:
                recepcao, created = TipoAndamentoCertidao.objects.get_or_create(
                    descricao__icontains="Recepção",
                    defaults={"grupo_recepcao": True},
                )
                if created:
                    recepcao.grupo_recepcao = True
                    recepcao.save()
            return recepcao
        except ObjectDoesNotExist:
            return None

    @property
    def get_reciboimpresso(self) -> "TipoAndamentoCertidao":
        """
        Obtém o objeto TipoAndamentoCertidao com o grupo_reciboimpresso definido como True.
        Se não existir, cria um novo com a descrição "Recibo Impresso".

        Returns
        -------
            Optional[TipoAndamentoCertidao]: O objeto TipoAndamentoCertidao correspondente ou None.

        """
        try:
            reciboimpresso = TipoAndamentoCertidao.objects.filter(
                grupo_reciboimpresso=True,
            ).first()
            if not reciboimpresso:
                reciboimpresso, created = TipoAndamentoCertidao.objects.get_or_create(
                    descricao__icontains="Recibo Impresso",
                    defaults={"grupo_reciboimpresso": True},
                )
                if created:
                    reciboimpresso.grupo_reciboimpresso = True
                    reciboimpresso.save()
            return reciboimpresso
        except ObjectDoesNotExist:
            return None

    @staticmethod
    def get_tipo_andamento_selo() -> "TipoAndamentoCertidao":
        """
        Obtém o objeto TipoAndamentoCertidao com o grupo_selo definido como True.
        Se não existir, cria um novo com a descrição "Selo".

        Returns
        -------
            Optional[TipoAndamentoCertidao]: O objeto TipoAndamentoCertidao correspondente ou None.

        """
        try:
            selo = TipoAndamentoCertidao.objects.filter(grupo_selo=True).first()
            if not selo:
                selo, created = TipoAndamentoCertidao.objects.get_or_create(
                    descricao__icontains="Selo",
                    defaults={"grupo_selo": True},
                )
                if created:
                    selo.grupo_selo = True
                    selo.save()
            return selo
        except ObjectDoesNotExist:
            return None

    @cached_property
    def andamento_certidao_status(self) -> dict[str, bool]:
        # Obtém todos os tipos de andamentos relevantes em uma única consulta
        tipo_andamentos = TipoAndamentoCertidao.objects.filter(
            Q(grupo_cancelado=True)
            | Q(grupo_devolucao=True)
            | Q(grupo_fase_cartorio=True)
            | Q(grupo_pedido_confirmado=True)
            | Q(grupo_reciboimpresso=True)
            | Q(grupo_selo=True)
            | Q(grupo_recepcao=True)
            | Q(grupo_gerar_andamento_agenda=True)
            | Q(grupo_gerar_certidao=True)
            | Q(grupo_certidao_pronta=True)
            | Q(grupo_certidao_entregue=True)
            | Q(grupo_certidao_exigencia=True),
        ).values_list(
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
        )

        # Cria dicionários para cada grupo de andamentos
        grupos = {
            "grupo_cancelado": [],
            "grupo_devolucao": [],
            "grupo_fase_cartorio": [],
            "grupo_pedido_confirmado": [],
            "grupo_reciboimpresso": [],
            "grupo_selo": [],
            "grupo_recepcao": [],
            "grupo_gerar_andamento_agenda": [],
            "grupo_gerar_certidao": [],
            "grupo_certidao_pronta": [],
            "grupo_certidao_entregue": [],
            "grupo_certidao_exigencia": [],
        }

        # Popula os dicionários com os códigos correspondentes
        for codigo, *grupos_flags in tipo_andamentos:
            for i, flag in enumerate(grupos_flags):
                if flag:
                    grupos[list(grupos.keys())[i]].append(codigo)

        # Obtém todos os andamentos do pedido em uma única consulta
        andamentos = PedidoCertidaoAndamento.objects.filter(
            pedido_id=self.id,
            tipo_andamento__in=[
                codigo for sublist in grupos.values() for codigo in sublist
            ],
        ).values_list("tipo_andamento", flat=True)

        # Verifica a presença de andamentos em cada grupo
        return {
            group: any(andamento in codes for andamento in andamentos)
            for group, codes in grupos.items()
        }

    @cached_property
    def devolvido(self) -> bool:
        """
        Verifica se o pedido de certidão está devolvido, ou seja, se possui algum andamento
        do grupo_devolucao.

        Returns
        -------
            bool: True se o pedido estiver devolvido, False caso contrário.

        """
        try:
            tipo_devolucao = list(
                TipoAndamentoCertidao.objects.filter(grupo_devolucao=True).values_list(
                    "codigo",
                    flat=True,
                ),
            )
            return PedidoCertidaoAndamento.objects.filter(
                pedido_id=self.id,
                tipo_andamento__in=tipo_devolucao,
            ).exists()
        except ObjectDoesNotExist:
            return False

    @cached_property
    def ultimo_andamento_grupo_fase_cartorio(self) -> tuple[str, str, str]:
        """Obtém o último andamento do grupo_fase_cartorio e formata a descrição, colaborador destino e data."""
        try:
            tipo_andamento = list(
                TipoAndamentoCertidao.objects.filter(
                    grupo_fase_cartorio=True,
                ).values_list("codigo", flat=True),
            )

            andamento = (
                PedidoCertidaoAndamento.objects.filter(
                    pedido_id=self.id,
                    tipo_andamento__in=tipo_andamento,
                    ativo=True,
                )
                .order_by("data_hora")
                .last()
            )

            if andamento:
                data_para_formato_de_modelo = andamento.data_hora.strftime(
                    settings.SHORT_DATE_FORMAT_STR,
                )
                colaborador_destino = str(andamento.colaborador_destino).replace(
                    "None",
                    "",
                )

                return (
                    str(andamento.tipo_andamento.descricao),
                    str(colaborador_destino),
                    str(data_para_formato_de_modelo),
                )

            return "", "", ""
        except ObjectDoesNotExist:
            return "", "", ""

    @cached_property
    def andamento_pedido_confirmado(self):
        tipo_andamento = list(
            TipoAndamentoCertidao.objects.filter(
                grupo_pedido_confirmado=True,
            ).values_list("codigo", flat=True),
        )

        andamento_pedido_confirmado = PedidoCertidaoAndamento.objects.filter(
            pedido_id=self.id,
            tipo_andamento__in=tipo_andamento,
        ).last()

        return bool(andamento_pedido_confirmado)

    @property
    def get_andamento_pedido_confirmado(self):
        return self.andamento_certidao_status.get("grupo_pedido_confirmado", False)

    @property
    def get_andamento_pedido_recebido(self):
        descricao = "Recebido"

        # Tentar obter o objeto ou criar um novo se não existir
        andamento, created = TipoAndamentoCertidao.objects.get_or_create(
            descricao=descricao,
            defaults={
                # "codigo": str(TipoAndamentoCertidao.objects.aggregate(Max("codigo"))["codigo__max"] + 1),
                "codigo": str(99),
                "grupo_pedido_confirmado": True,
            },
        )

        return andamento

    @cached_property
    def certidao_entregue(self) -> bool:
        return self.andamentos.filter(
            tipo_andamento__grupo_certidao_entregue=True,
            ativo=True,
        ).exists()

    @property
    def andamento_certidao_entregue(self):
        # return self.andamento_certidao_status.get("grupo_certidao_entregue", False)
        return self.andamentos.filter(
            tipo_andamento__grupo_certidao_entregue=True,
            ativo=True,
        ).exists()

    @property
    def andamento_certidao_pronta(self) -> bool:
        return self.andamento_certidao_status.get("grupo_certidao_pronta", False)

    @property
    def andamento_certidao_exigencia(self) -> bool:
        return self.andamento_certidao_status.get("grupo_certidao_exigencia", False)

    # GERAR AGENDA PARA OS COLABORADORES ENVOLVIDAS
    def gerar_agenda_certidao_grupo_colaboradores(self, andamento):
        # FILTRANDO TODOS OS COLABORADORES ENVOLVIDOS
        grupo_colaborador = list(
            GrupoUsuarioAgendaCertidao.objects.filter(
                tipo_andamento_id=andamento.tipo_andamento.id,
            ).values_list("colaborador_id", flat=True),
        )

        # Adicionando o destinatario para os eventos
        if andamento.colaborador_destino:
            grupo_colaborador.append(andamento.colaborador_destino.id)

        # Adicionando 4 horas
        horario_atual = timezone.now()
        horario_atual_final = horario_atual + timedelta(hours=2)

        if grupo_colaborador:
            # REGISTRAR EVENTO NA AGENDA - Gravar o evento na agenda do dia
            for colaborador in grupo_colaborador:
                try:
                    Event.criar_evento_no_calendario(
                        user=colaborador,
                        auth_user=colaborador,
                        numero=str(self.numero_pedido),
                        title=str(andamento.tipo_andamento.descricao),
                        description=andamento.tipo_andamento.descricao,
                        origem="C",
                        horas_adicionais=0,
                        url="",
                        data_futura_inicio=horario_atual,
                        data_futura_fim=horario_atual_final,
                        gravar_apenas_data="N",
                        fase_agenda_id=1,
                        exibir_agenda="S",
                    )
                except Exception as e:
                    logger.exception(
                        f"Erro ao criar evento na agenda para o colaborador {colaborador}. {e}",
                    )

    @cached_property
    def numero_pedido_inteiro(self):
        return str(self.numero_pedido).replace(".", "") or 0


class PedidoCertidaoAnexo(models.Model):
    pedido_certidao = models.ForeignKey(
        PedidoCertidao,
        on_delete=models.CASCADE,
        related_name="anexos",
    )
    arquivo = models.FileField(upload_to="pedido_certidao_anexos/")
    descricao: str = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self) -> str:
        return self.descricao or self.arquivo.name


class TipoApresentante(BaseModel):
    nome: str = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        verbose_name = "Tipo de Apresentante"
        verbose_name_plural = "Tipos de Apresentante"

    def __str__(self) -> str:
        return self.nome or "Não informado"

    def get_default_tipo_apresentante_id() -> int:
        return TipoApresentante.get_tipo_apresentante_default().id

    def get_tipo_apresentante_pagador_id() -> int:
        return TipoApresentante.get_tipo_apresentante_pagador().id

    def get_tipo_apresentante_interessado_id() -> int:
        return TipoApresentante.get_tipo_apresentante_interessado().id

    def get_tipo_apresentante_default() -> "TipoApresentante":
        return TipoApresentante.objects.get_or_create(nome="Apresentante")[0]

    def get_tipo_apresentante_interessado() -> "TipoApresentante":
        return TipoApresentante.objects.get_or_create(nome="Interessado")[0]

    def get_tipo_apresentante_pagador() -> "TipoApresentante":
        return TipoApresentante.objects.get_or_create(nome="Pagador")[0]

    def get_tipo_apresentante_procurador() -> "TipoApresentante":
        return TipoApresentante.objects.get_or_create(nome="Procurador")[0]

    def get_tipo_apresentante_despachange() -> "TipoApresentante":
        return TipoApresentante.objects.get_or_create(nome="Despachante")[0]

    def criar_defaults() -> None:
        logger.info("Populando Tipos de Apresentante padrão.")
        try:
            TipoApresentante.objects.get_or_create(nome="Apresentante")
            TipoApresentante.objects.get_or_create(nome="Interessado")
            TipoApresentante.objects.get_or_create(nome="Procurador")
            TipoApresentante.objects.get_or_create(nome="Despachante")
            TipoApresentante.objects.get_or_create(nome="Pagador")
        except Exception as e:
            logger.exception(f"Erro ao criar Tipos de Apresentantes padrão. {e}")


def get_tipo_apresentante_pagador():
    tipo_apresentante, created = TipoApresentante.objects.get_or_create(nome="Pagador")
    return tipo_apresentante


class Apresentante(DocumentoMixin, EnderecoMixin, BaseModel):
    """Modelo de Apresentante. Apresentante é a pessoa que solicita a certidão."""

    pedido = models.OneToOneField(
        PedidoCertidao,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="apresentante",
    )
    nome: str = models.CharField(max_length=100, blank=True, null=True)
    telefone: str = models.CharField(max_length=40, blank=True, null=True)
    telefone_2: str = models.CharField(max_length=40, blank=True, null=True)
    observacao: str = models.CharField(max_length=500, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    tipo_apresentante = models.ForeignKey(
        TipoApresentante,
        on_delete=models.SET_NULL,
        null=True,
        default=TipoApresentante.get_default_tipo_apresentante_id,
    )

    documento: str = models.CharField(max_length=255, blank=True, null=True)

    dados_bancarios = models.OneToOneField(
        DadosBancarios,
        blank=True,
        null=True,
        on_delete=models.CASCADE,
    )

    interessado_nome: str = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Nome do Interessado",
        help_text="Interessado é quem o apresentante representa.",
    )
    interessado_tipo_documento = models.ForeignKey(
        TipoDocumento,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="interessado_tipo_documento",
        verbose_name="Tipo de Documento",
        help_text="Tipo de documento do interessado.",
    )
    interessado_documento: str = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Documento",
        help_text="Documento do interessado.",
    )
    interessado_telefone: str = models.CharField(
        max_length=40,
        blank=True,
        null=True,
        verbose_name="Telefone",
        help_text="Telefone do interessado.",
    )
    interessado_email = models.EmailField(
        blank=True,
        null=True,
        verbose_name="E-mail",
        help_text="E-mail do interessado.",
    )
    interessado_tipo = models.ForeignKey(
        TipoApresentante,
        on_delete=models.SET_NULL,
        null=True,
        default=get_tipo_apresentante_pagador,
        related_name="interessado_tipo",
        verbose_name="Tipo",
        help_text="Tipo de interessado. Ex: Procurador, Despachante.",
    )

    pagador_tipo = models.ForeignKey(
        TipoApresentante,
        on_delete=models.SET_NULL,
        null=True,
        default=TipoApresentante.get_tipo_apresentante_pagador_id,
        related_name="pagador_tipo",
        verbose_name="Tipo Pagador",
    )

    pagador_nome: str = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Nome do Pagador",
        help_text="Nome de quem pagou pela certidão para sair no recibo.",
    )

    class Meta:
        verbose_name = "Apresentante"
        verbose_name_plural = "Apresentantes"

    def __str__(self) -> str:
        nome_formatado = self.nome or "Não informado"

        return f"{nome_formatado} | {self.documento_formatado}"

    def get_absolute_url(self):
        return reverse(
            "home:pedido_certidao_editar_apresentante",
            kwargs={"pk": self.pk},
        )

    def get_update_url(self):
        return reverse(
            "home:pedido_certidao_editar_apresentante",
            kwargs={"pk": self.pk},
        )

    @cached_property
    def documento_formatado(self):
        """Retorna o documento formatado."""
        return formatar_documento(self.documento)

    @cached_property
    def documento_mascarado(self):
        """Retorna o documento formatado."""
        return helpers.mascarar_documento(self.documento)

    def novo_pedido_de_certidao(self: "Apresentante", usuario: User) -> PedidoCertidao:
        """Cria um novo pedido de certidão para o apresentante."""
        return PedidoCertidao.objects.criar_pedido(
            apresentante=self,
            criado_por=usuario,
        )


class PedidoCertidaoPessoa(BaseModel):
    # Campos Básicos

    nome: str = models.CharField(max_length=500, blank=True, null=True)

    # Campos de Documentação
    rg: str = models.CharField(max_length=20, blank=True, null=True, verbose_name="RG")
    tipo_documento = models.ForeignKey(
        TipoDocumento,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )

    documento: str = models.CharField(max_length=25, blank=True, null=True)
    nacionalidade: str = models.CharField(max_length=50, blank=True, null=True)
    profissao: str = models.CharField(max_length=50, blank=True, null=True)

    # Campos Adicionais
    complemento: str = models.CharField(max_length=100, blank=True, null=True)
    estado_civil = models.ForeignKey(
        "home.EstadoCivil",
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="Estado Civil",
        related_name="certidoes_Pessoa_estado_civil",
    )
    # anotacoes:str = models.CharField(
    #     max_length=500,
    #     blank=True,
    #     null=True,
    #     verbose_name="Anotações",
    # )
    anotacoes = models.TextField(blank=True, null=True, verbose_name="Anotações")

    # Relações
    pedido = models.ForeignKey(
        PedidoCertidao,
        on_delete=models.CASCADE,
        related_name="pessoas",
    )

    endereco: str = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name="Endereço do Imóvel Vinculado",
        help_text="Endereço do imóvel vinculado à pessoa",
    )

    nome_conjuge: str = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name="Nome do Cônjuge",
        help_text="Nome do cônjuge da pessoa",
    )

    tipo_documento_conjuge = models.ForeignKey(
        TipoDocumento,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="conjuge",
        verbose_name="Tipo de Documento do Cônjuge",
        help_text="Tipo de documento do cônjuge da pessoa",
    )

    documento_conjuge: str = models.CharField(
        max_length=25,
        blank=True,
        null=True,
        verbose_name="Documento do Cônjuge",
        help_text="Documento do cônjuge da pessoa",
    )

    class Meta:
        verbose_name = "Pessoa"
        verbose_name_plural = "Pessoas"

    def __str__(self) -> str:
        return self.pessoa_qualificada

    def get_absolute_url(self):
        return reverse("home:pedido_certidao_detalhes_pessoa", kwargs={"pk": self.pk})

    # PESQUISAR TODOS OS IMOVEIS E REGISTRO AUXILIAR DA PESSOA
    def get_buscar_pessoal_url(self):
        if self.nome:
            try:
                # nome = str(unidecode(self.nome)).strip()
                result = unidecode.unidecode(self.nome)
                nome = str(result).strip()
            except:
                nome = str(self.nome).strip()

            documento = (
                str("".join(re.findall("\\d+", self.documento)))
                if self.documento
                else "%"
            )

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
        else:
            return None

    def get_update_url(self):
        return reverse("home:pedido_certidao_pessoa_update", kwargs={"pk": self.pk})

    def get_delete_url(self):
        return reverse("home:pedido_certidao_excluir_pessoa", kwargs={"pk": self.pk})

    @cached_property
    def quantidade_certidoes(self):
        """Retorna a quantidade de certidões relacionadas à pessoa."""
        return self.certidoes_pessoa.count()

    @cached_property
    def total_valor_certidoes(self):
        """Retorna o valor total das certidões relacionadas à pessoa."""
        return (
            self.certidoes.aggregate(total=Sum("tipo_certidao__tipo_certidao_valor"))[
                "total"
            ]
            or 0
        )

    @cached_property
    def documento_formatado(self):
        """Retorna o documento formatado."""
        return formatar_documento(self.documento)

    @cached_property
    def nome_qualificado(self):
        """Constrói e retorna uma representação qualificada da pessoa."""
        return self.nome or "Nome não informado"

    @cached_property
    def pessoa_qualificada(self) -> str:
        """Constrói e retorna uma representação qualificada da pessoa."""
        nome_parte = f"{formatar_nome(self.nome_qualificado)}" or ""
        doc_parte = (
            f"{str(self.tipo_documento) + ':' if self.tipo_documento else ''}{self.documento_formatado or ''}"
            or ""
        )
        endereco_imovel_parte = (
            f"- Endereço: {self.endereco}" or "" if self.endereco else ""
        )

        return f"{nome_parte} | {doc_parte} {endereco_imovel_parte}"


class PedidoCertidaoImovel(EnderecoMixin, BaseModel):
    pedido = models.ForeignKey(
        PedidoCertidao,
        on_delete=models.CASCADE,
        related_name="imoveis",
    )
    numero_registro = models.CharField(
        "Número do Registro",
        max_length=100,
        blank=True,
        null=True,
    )
    tipo_registro = models.ForeignKey(
        TipoRegistroImobiliario,
        max_length=1,
        blank=True,
        verbose_name="Tipo Registro",
        null=True,
        on_delete=models.SET_NULL,
    )
    cartorio = models.CharField(
        max_length=2,
        blank=True,
        null=True,
        default="1",
        verbose_name="Cartório",
    )
    livro: str = models.CharField(max_length=100, blank=True, null=True, default="")
    descricao: str = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Descrição",
    )
    tipo_imovel = models.ForeignKey(
        TipoClasseRegistro,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="Tipo de Imóvel",
        help_text="Tipo de imóvel do Registro. Ex. Rural, Urbano, Loteamento, etc.",
    )

    # anotacoes:str = models.CharField(
    #     max_length=500,
    #     blank=True,
    #     null=True,
    #     verbose_name="Anotações",
    # )

    anotacoes = models.TextField(blank=True, null=True, verbose_name="Anotações Imovel")

    complemento: str = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name="Complemento de Endereço",
    )

    numero_registro_cnm: str = models.CharField(
        "Número do Registro CNM",
        max_length=100,
        blank=True,
        null=True,
    )

    class Meta:
        verbose_name = "Imóvel"
        verbose_name_plural = "Imóveis"

    def __str__(self) -> str:
        return self.identificacao or ""

    def get_absolute_url(self):
        return reverse("home:pedido_certidao_detalhes_imovel", kwargs={"pk": self.pk})

    @cached_property
    def quantidade_certidoes(self):
        return self.certidoes_imovel.count()

    @cached_property
    def numero_registro_qualificado(self) -> str:
        # verificar se tipo_registro é valido
        if self.tipo_registro and self.numero_registro:
            return f"{self.tipo_registro.sigla} {self.numero_registro_formatado}"
        if self.numero_registro:
            return f"M {self.numero_registro_formatado}"

        return ""

    @cached_property
    def numero_registro_formatado(self) -> str:
        try:
            # Extrair apenas números do numero
            numero_clean = int(re.sub(r"[^0-9]", "", str(self.numero_registro)))

            # Convertendo o valor para string e formatando com separador de ponto
            return f"{numero_clean:,.0f}".replace(",", ".")
        except Exception:
            logger.exception("Erro ao formatar o número do registro")
            return self.numero_registro

    @cached_property
    def numero_simples(self) -> str:
        try:
            # Remova tudo que não seja número ou letra
            return re.sub(r"[^a-zA-Z0-9]", "", str(self.numero_registro))
        except Exception:
            logger.exception("Erro ao formatar o número do registro")
            return self.numero_registro

    @cached_property
    def total_valor_certidoes(self):
        return (
            self.certidoes.aggregate(total=Sum("tipo_certidao__tipo_certidao_valor"))[
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

    def get_update_url(self):
        return reverse("home:pedido_certidao_update_imovel", kwargs={"pk": self.pk})

    # def get_delete_url(self):
    #     return reverse("home:pedido_certidao_update_imovel", kwargs={"pk": self.pk})

    def get_registro_url(self):
        # BUSCAR DO IMÓVEL
        if self.tipo_registro.sigla == "A":
            registro_auxiliar = Livro03.objects.filter(
                numero=self.numero_registro,
                cartorio=self.cartorio,
            ).first()
            imovel_id = registro_auxiliar.pk
        else:
            imovel = Livro02.objects.filter(
                numero=self.numero_registro,
                tipo=self.tipo_registro.sigla,
                cartorio=self.cartorio,
            ).first()
            imovel_id = imovel.pk if imovel else None

        if imovel_id:
            if self.tipo_registro.sigla == "A":
                base_url = reverse("home:livro03_imovel", args=[imovel_id])
            else:
                base_url = reverse("home:livro04_imovel", args=[imovel_id])
        else:
            base_url = reverse("home:livro02_list")

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


class TipoItemCertidao(BaseModel):
    """
    Modelo que representa os diferentes tipos de itens que uma certidão pode conter.

    Tipos:
        - Imóvel: Refere-se a certidões que contêm informações apenas sobre imóveis.
        - Pessoa: Refere-se a certidões que contêm informações apenas sobre pessoas.
        - Ambos: Refere-se a certidões que podem conter informações tanto sobre imóveis quanto sobre pessoas.
    """

    nome: str = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        unique=True,
    )
    explicacao: str = models.CharField(max_length=500, blank=True, null=True)

    class Meta:
        verbose_name = "Tipo de Item de Certidão"
        verbose_name_plural = "Tipos de Item de Certidão"

    def __str__(self) -> str:
        return f"{self.nome}"

    @staticmethod
    def get_default_tipo_item_certidao() -> "TipoItemCertidao":
        return TipoItemCertidao.objects.get_or_create(nome="Ambos")[0]

    @staticmethod
    def get_default_tipo_item_certidao_imovel() -> "TipoItemCertidao":
        return TipoItemCertidao.objects.get_or_create(nome="Imóvel")[0]

    @staticmethod
    def get_default_tipo_item_certidao_pessoa() -> "TipoItemCertidao":
        return TipoItemCertidao.objects.get_or_create(nome="Pessoa")[0]


class TipoCertidao(BaseModel):
    nome: str = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        db_index=True,
        help_text="Confome consta na tabela de emolumentos. Ex. 'Certidão de Ônus Reais', 'Certidão de Inteiro Teor'",
    )
    codigo: str = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        db_index=True,
        default="0",
        verbose_name="Código Legal",
        help_text="Codigo fornecido na tabela de emolumentos",
    )
    prazo_legal = models.ForeignKey(
        PrazoLegal,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        default=1,
        # default=PrazoLegal.get_default_prazo_legal,
    )
    tipo_item = models.ForeignKey(
        TipoItemCertidao,
        verbose_name="Tipo de Item",
        on_delete=models.SET_NULL,
        null=True,
        related_name="tipo_item",
        help_text="Indica se a certidão é para imóvel, pessoa ou ambos.",
        # default=TipoItemCertidao.get_default_tipo_item_certidao(),
    )
    codigo_onr: str = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        db_index=True,
        default="0",
        verbose_name="Código Legal da ONR",
        help_text="Codigo fornecido na tabela de emolumentos da ONR",
    )
    ativo: bool = models.BooleanField(default=True)
    certidao_id_sistema_antigo = models.BigIntegerField(null=True, default=0)
    certidao_id_sistema_antigo_isento = models.BigIntegerField(null=True, default=0)
    certidao_id_sistema_antigo_50 = models.BigIntegerField(null=True, default=0)

    objects: managers.TipoCertidaoManager = managers.TipoCertidaoManager()

    class Meta:
        verbose_name = "Tipo de Certidão"
        verbose_name_plural = "Tipos de Certidão"

    def __str__(self) -> str:
        return self.nome_com_codigo

    @staticmethod
    def get_default_tipo_certidao() -> "TipoCertidao":
        logger.info(
            "Obtendo ou criando o Tipo de Certidão padrão: Certidão de Inteiro Teor (8402-0)",
        )
        nome_default = "Certidão de Inteiro Teor"
        codigo_default = "8402-0"

        # Obter os valores default para prazo_legal e tipo_item
        prazo_legal_default = PrazoLegal.get_default_prazo_legal()
        tipo_item_default = TipoItemCertidao.get_default_tipo_item_certidao()

        # Tenta obter uma instância existente ou criar uma nova
        tipo_certidao, created = TipoCertidao.objects.update_or_create(
            nome=nome_default,
            defaults={
                "codigo": codigo_default,
                "prazo_legal": prazo_legal_default,
                "tipo_item": tipo_item_default,
            },
        )
        return tipo_certidao

    @classmethod
    def popular_valores_onr(cls) -> None:
        logger.info("Populando Tipos de Certidões da ONR")
        tipos_de_certidao_onr = [
            {"codigo_onr": "1", "nome": "PROPRIEDADE/NEGATIVA DE PROPRIEDADE"},
            {"codigo_onr": "2", "nome": "VINTENÁRIA"},
            {"codigo_onr": "3", "nome": "MATRÍCULA DO IMÓVEL"},
            {"codigo_onr": "4", "nome": "TRANSCRIÇÃO"},
            {"codigo_onr": "5", "nome": "PACTO ANTENUPCIAL"},
            {"codigo_onr": "6", "nome": "ONUS"},
            {"codigo_onr": "7", "nome": "DOCUMENTO ARQUIVADO"},
            {"codigo_onr": "8", "nome": "CONVENÇÃO DE CONDOMÍNIO"},
            {"codigo_onr": "9", "nome": "LIVRO3-Garantias"},
            {"codigo_onr": "10", "nome": "OUTROS REGISTROS LIVRO3-Auxiliar"},
            {"codigo_onr": "12", "nome": "INTEIRO TEOR, ÔNUS E AÇÕES"},
            {"codigo_onr": "13", "nome": "POR QUESITO"},
            {"codigo_onr": "14", "nome": "NEGATIVA DE PENHOR"},
            {"codigo_onr": "15", "nome": "ÔNUS REAIS E AÇÕES REIPERSECUTÓRIAS"},
        ]

        for tipo_de_certidao_onr in tipos_de_certidao_onr:
            try:
                cls.objects.get_or_create(
                    codigo_onr=tipo_de_certidao_onr["codigo_onr"],
                    defaults={"nome": tipo_de_certidao_onr["nome"]},
                )
            except cls.MultipleObjectsReturned:
                logger.warning(
                    f"Há mais de um Tipo de Certidão com o mesmo codigo da ONR: {tipo_de_certidao_onr}",
                )

    @cached_property
    def prazo_em_horas(self):
        if self.prazo_legal:
            return self.prazo_legal.em_horas
        return 0

    def calcular_prazo_em_dias(self):
        if self.prazo_legal:
            return self.prazo_legal.dias
        return 0

    @cached_property
    def prazo_final(self):
        return self.calcular_prazo_final(self.data_entrada)

    def calcular_prazo_final(self, data_inicio):
        prazo_em_horas = self.prazo_em_horas
        # if self.prazo_legal:
        #     print(
        #         f"Prazo Configurado: {self.prazo_legal.valor} {self.prazo_legal.unidade} | Convertido em {prazo_em_horas} horas {self.prazo_legal.tipo_prazo}"
        #     )
        if prazo_em_horas is None:
            return None

        if timezone.is_naive(data_inicio):
            data_inicio = timezone.make_aware(
                data_inicio,
                timezone.get_default_timezone(),
            )
        # logger.info(f"{data_inicio} Data de início (ajustada para time zone). ")

        data_final = data_inicio
        horas_restantes = prazo_em_horas

        while horas_restantes > 0:
            if (
                Feriado.objects.filter(data=data_final.date()).exists()
                or data_final.weekday() >= 5
            ):
                # print(
                #     f"{data_final.date()} é feriado ou fim de semana, pulando para o próximo dia útil."
                # )
                data_final += timedelta(days=1)
                continue

            weekdays = data_final.weekday()

            try:
                expediente = Expediente.get_default_expediente(weekdays)
            except Exception:
                # logger.info(f"Nenhum expediente encontrado para o dia da semana: ")
                # Decida o que fazer se não houver expediente para o dia da semana
                break  # ou continue com alguma lógica alternativa

            hora_inicio_expediente = timezone.make_aware(
                datetime.combine(data_final.date(), expediente.inicio),
                timezone.get_default_timezone(),
            )
            hora_fim_expediente = timezone.make_aware(
                datetime.combine(data_final.date(), expediente.fim),
                timezone.get_default_timezone(),
            )
            # print(                f"{data_final.date()}: Expediente: Início às {hora_inicio_expediente}, Fim às {hora_fim_expediente}"           )

            if data_final < hora_inicio_expediente or data_final >= hora_fim_expediente:
                # logger.info(f"{data_final}: Fora do expediente, ajustando para o próximo dia útil.")
                data_final = hora_inicio_expediente + timedelta(days=1)
                continue

            horas_uteis_no_dia = (hora_fim_expediente - data_final).seconds // 3600
            # logger.info(f"{data_final.date()}: Horas úteis no dia: {horas_uteis_no_dia} horas")
            horas_restantes -= horas_uteis_no_dia

            if horas_restantes > 0:
                # logger.info(f" Horas restantes: {horas_restantes}, avançando para o próximo dia útil.")
                data_final = hora_inicio_expediente + timedelta(days=1)
            else:
                data_final += timedelta(hours=horas_restantes)
                # logger.info(f"{data_final} - Prazo final atingido!")

        return calcular_data_com_workalendar(data_inicio, self.prazo_legal.dias)

    # def calcular_prazo_final(self, data_inicio):
    #     prazo_em_horas = self.prazo_em_horas
    #     print(
    #         f"Prazo Configurado: {self.prazo_legal.valor} {self.prazo_legal.unidade} | Convertido em {prazo_em_horas} horas {self.prazo_legal.tipo_prazo}"
    #     )

    #     if prazo_em_horas is None:
    #         return None

    #     if timezone.is_naive(data_inicio):
    #         data_inicio = timezone.make_aware(data_inicio, timezone.get_default_timezone())
    #     logger.info(f"{data_inicio} Data de início (ajustada para time zone).")

    #     data_final = data_inicio
    #     horas_restantes = prazo_em_horas
    #     calendario = Brazil()  # Use o  correspondente à sua localização

    #     while horas_restantes > 0:
    #         if not calendario.is_working_day(data_final):
    #             print(
    #                 f"{data_final.date()} é feriado ou fim de semana, pulando para o próximo dia útil."
    #             )
    #             data_final += timedelta(days=1)
    #             continue

    #         expediente = self.get_expediente(
    #             data_final
    #         )  # Supondo que você tem uma função para isso
    #         horas_uteis_no_dia = expediente.horas_uteis(
    #             data_final
    #         )  # Supondo que você tenha uma função para calcular isso

    #         logger.info(f"{data_final}: Horas úteis no dia: {horas_uteis_no_dia} horas")
    #         horas_restantes -= horas_uteis_no_dia

    #         if horas_restantes > 0:
    #             logger.info(f" Horas restantes: {horas_restantes}, avançando para o próximo dia útil.")
    #             data_final = calendario.add_working_days(data_final, 1)
    #         else:
    #             data_final += timedelta(hours=horas_restantes)
    #             logger.info(f"{data_final} - Prazo final atingido!")

    #     return data_final

    @cached_property
    def nome_com_codigo(self) -> str:
        return f"{self.nome} ({self.codigo})"

    def get_expediente(self, data):
        dia_da_semana = data.weekday()  # 0 para Segunda, 1 para Terça, etc.
        return Expediente.get_default_expediente(dia_da_semana)


class ValorCertidao(models.Model):
    tipo_certidao = models.ForeignKey(
        TipoCertidao,
        on_delete=models.CASCADE,
        related_name="tipo_certidao_valor",
        verbose_name="Tipo de Certidão",
        help_text="Ex.: Certidão de Ônus Reais, Certidão de Inteiro Teor, etc.",
    )
    data_inicio_validade = models.DateField()
    data_fim_validade = models.DateField(
        null=True,
        blank=True,
        help_text="Deixe em branco para valores permanentes.",
    )
    valor = models.DecimalField(
        default=0,
        blank=False,
        decimal_places=2,
        max_digits=10,
        help_text="Emolumento Bruto (Sem o desconto do RECOMPE)",
        verbose_name="Emolumento Bruto",
    )

    taxa_fiscal_judiciaria = models.DecimalField(
        default=0,
        blank=False,
        decimal_places=2,
        max_digits=10,
        verbose_name="TFJ $",
        help_text="Taxa Fiscal Judiciaria",
    )
    fundo_estado = models.DecimalField(
        default=0,
        blank=False,
        decimal_places=2,
        max_digits=10,
        verbose_name="Fundo Estado $",
        help_text="Fundo estadual, somado ao emolumento bruto, paga pelo cartório e não é repassada ao cliente final.",
    )
    issqn_percentual = models.DecimalField(
        default=0,
        blank=False,
        decimal_places=2,
        max_digits=5,
        verbose_name="ISSQN %",
        help_text="Imposto Municipal sobre Serviços de Qualquer Natureza. É repassado ao cliente final.",
    )  # Campo para o percentual do ISSQN

    certidao_pos_registro: bool = models.BooleanField(default=False, null=True)

    objects: managers.ValorCertidaoManager = managers.ValorCertidaoManager()

    class Meta:
        unique_together = ["tipo_certidao", "data_inicio_validade"]
        constraints = [
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_data_inicio_menor_que_data_fim",
                check=Q(data_inicio_validade__lte=F("data_fim_validade")),
            ),
        ]
        verbose_name = "Valor da Certidão"
        verbose_name_plural = "Valores da Certidão"

    def __str__(self) -> str:
        return (
            f"{self.tipo_certidao.nome}: "
            f"Emolumento Liquido: R$ {self.emolumento_sem_recomp:.2f} | "
            f"Fundo Estado: R$ {self.recompe_calculado:.2f} | "
            f"ISSQN: R$ {self.issqn_calculado:.2f} | "
            f"TFJ: R$ {self.taxa_fiscal_judiciaria:.2f} | "
            f"Total: R$ {self.total:.2f} | "
            f"Validade: {self.data_inicio_validade.strftime(settings.DATE_FORMAT_STR)} - "
            f"{self.data_fim_validade.strftime(settings.DATE_FORMAT_STR)}"
        )

    @cached_property
    def issqn_calculado(self) -> Decimal:
        try:
            logger.debug(
                f"Calculando ISSQN: issqn_percentual={self.issqn_percentual}, emolumento_sem_recomp={self.emolumento_sem_recomp}",
            )
            issqn_percentual_decimal = Decimal(self.issqn_percentual)
            emolumento_sem_recomp_decimal = Decimal(self.emolumento_sem_recomp)
            result = (
                issqn_percentual_decimal / Decimal("100")
            ) * emolumento_sem_recomp_decimal
            logger.debug(f"ISSQN calculado: {result}")
            return result
        except InvalidOperation as e:
            logger.exception(f"Erro ao calcular ISSQN: {e}")
            return Decimal("0.0")

    @cached_property
    def recompe_calculado(self) -> Decimal:
        """
        Calcula o valor do RECOMPE (Fundo Estadual) fazendo a multiplicação do
        fundo_estado pelo valor da certidão.
        """
        try:
            logger.debug(
                f"Calculando recompe: fundo_estado={self.fundo_estado}, valor={self.valor}",
            )
            result = Decimal((Decimal(self.fundo_estado) / 100) * Decimal(self.valor))
            logger.debug(f"Recompe calculado: {result}")
            return result
        except InvalidOperation as e:
            logger.exception(f"Erro ao calcular recompe: {e}")
            return Decimal("0.0")

    @cached_property
    def emolumento_sem_recomp(self) -> Decimal:
        """Calcula o emolumento descontado o fundo_estado."""
        try:
            logger.debug(
                f"Calculando emolumento sem recompe: valor={self.valor}, recompe_calculado={self.recompe_calculado}",
            )
            result = Decimal(self.valor) - self.recompe_calculado
            logger.debug(f"Emolumento sem recompe: {result}")
            return result
        except InvalidOperation as e:
            logger.exception(f"Erro ao calcular emolumento sem recompe: {e}")
            return Decimal("0.0")

    @cached_property
    def emolumento_liquido(self) -> Decimal:
        """Calcula o emolumento líquido descontado o fundo_estado."""
        try:
            logger.debug(
                f"Calculando emolumento líquido: valor={self.valor}, recompe_calculado={self.recompe_calculado}",
            )
            result = Decimal(self.valor) - self.recompe_calculado
            logger.debug(f"Emolumento líquido: {result}")
            return result
        except InvalidOperation as e:
            logger.exception(f"Erro ao calcular emolumento líquido: {e}")
            return Decimal("0.0")

    @cached_property
    def emolumento_bruto(self) -> Decimal:
        """Calcula o emolumento somado ao fundo_estado."""
        try:
            logger.debug(f"Calculando emolumento bruto: valor={self.valor}")
            result = Decimal(self.valor)
            logger.debug(f"Emolumento bruto: {result}")
            return result
        except InvalidOperation as e:
            logger.exception(f"Erro ao calcular emolumento bruto: {e}")
            return Decimal("0.0")

    @cached_property
    def total(self) -> Decimal:
        try:
            logger.debug(
                f"Calculando total: emolumento_sem_recomp={self.emolumento_sem_recomp}, recompe_calculado={self.recompe_calculado}, taxa_fiscal_judiciaria={self.taxa_fiscal_judiciaria}, issqn_calculado={self.issqn_calculado}",
            )
            result = (
                self.emolumento_sem_recomp
                + self.recompe_calculado
                + Decimal(self.taxa_fiscal_judiciaria)
                + self.issqn_calculado
            )
            logger.debug(f"Total calculado: {result}")
            return result
        except InvalidOperation as e:
            logger.exception(f"Erro ao calcular total: {e}")
            return Decimal("0.0")

    def clean(self) -> None:
        from apps.home.validators import validar_sobreposicao_data

        try:
            # Validando sobreposição de data
            validar_sobreposicao_data(self)
            logger.debug("Validação de sobreposição de data concluída com sucesso.")
        except Exception as e:
            logger.exception(f"Erro na validação de sobreposição de data: {e}")


class Certidao(BaseModel):
    tipo_certidao = models.ForeignKey(
        TipoCertidao,
        on_delete=models.CASCADE,
        null=True,
        related_name="tipo_certidao",
        verbose_name="Tipo de Certidão",
        help_text="Ex.: Certidão de Ônus Reais, Certidão de Inteiro Teor, etc.",
    )

    pessoa = models.ForeignKey(
        "PedidoCertidaoPessoa",
        on_delete=models.CASCADE,
        null=True,
        related_name="certidoes_pessoa",
    )

    imovel = models.ForeignKey(
        "PedidoCertidaoImovel",
        on_delete=models.CASCADE,
        null=True,
        related_name="certidoes_imovel",
    )

    data_emissao = models.DateField(null=True)

    tipo_tributacao = models.ForeignKey(
        TipoTributacao,
        on_delete=models.CASCADE,
        null=True,
        default=1,
        verbose_name="Tipo de Tributação",
        help_text="Tipo de tributação da certidão.",
    )

    pessoa_cancelado = models.ForeignKey(
        "PedidoCertidaoPessoa",
        on_delete=models.CASCADE,
        null=True,
        related_name="certidoes_pessoa_cancelado",
    )

    imovel_cancelado = models.ForeignKey(
        "PedidoCertidaoImovel",
        on_delete=models.CASCADE,
        null=True,
        related_name="certidoes_imovel_cancelado",
    )

    objects: managers.CertidaoManager = managers.CertidaoManager()

    class Meta:
        verbose_name = "Certidão"
        verbose_name_plural = "Certidões"

    def __str__(self) -> str:
        return f"{self.nome} {self.tributacao}"

    def _arredondar_valor(self, valor) -> Decimal:
        """Arredonda um valor decimal para duas casas decimais."""
        try:
            logger.debug(f"Arredondando valor: {valor}")
            valor_decimal = Decimal(valor)
            return valor_decimal.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        except Exception as e:
            logger.exception(f"Erro ao arredondar valor: {valor} - {e}")
            raise

    def get_prazo_calculado(self):
        """Retorna o prazo em horas da certidão, se disponível."""
        if self.tipo_certidao:
            return self.tipo_certidao.prazo_em_horas
        return None

    def get_valor_emolumento_bruto(self):
        """Retorna o valor bruto do emolumento, buscando do banco de dados se necessário."""
        if not hasattr(self, "_valor_emolumento_bruto"):
            try:
                logger.debug(f"Obtendo valor emolumento bruto: {self.tipo_certidao}")
                self._valor_emolumento_bruto = ValorCertidao.objects.filter(
                    tipo_certidao=self.tipo_certidao,
                ).first()
            except Exception as e:
                logger.exception(f"Erro ao obter valor emolumento bruto: {e}")
                raise
        return self._valor_emolumento_bruto

    @classmethod
    def gerar_item_certidao(
        cls,
        tipo_certidao,
        pessoa,
        imovel,
        data_atual,
        tipo_tributacao,
    ) -> None:
        """Cria um item de certidão no banco de dados."""
        logger.info(f"Gravar certidão única: {tipo_certidao}")
        try:
            cls.objects.create(
                tipo_certidao=tipo_certidao,
                pessoa=pessoa,
                imovel=imovel,
                data_emissao=data_atual or timezone.now().date(),
                tipo_tributacao=tipo_tributacao,
            )
        except Exception as e:
            logger.exception(f"Erro ao gerar item de certidão: {e}")
            raise

    @cached_property
    def item(self: "Certidao"):
        """Retorna o item associado à certidão (imóvel ou pessoa)."""
        if self.imovel:
            return self.imovel
        elif self.pessoa:
            return self.pessoa
        return None

    @cached_property
    def pedido(self: "Certidao"):
        """Retorna o pedido associado à certidão."""
        if self.imovel:
            return self.imovel.pedido
        elif self.pessoa:
            return self.pessoa.pedido
        return None

    @cached_property
    def nome_pessoa(self: "Certidao") -> str:
        """Retorna o nome da pessoa associada à certidão."""
        return self.pessoa.nome if self.pessoa else ""

    @cached_property
    def cpf_pessoa(self: "Certidao") -> str:
        """Retorna o CPF da pessoa associada à certidão."""
        return self.pessoa.documento if self.pessoa else ""

    @cached_property
    def cnpj_pessoa(self: "Certidao") -> str:
        """Retorna o CNPJ da pessoa associada à certidão."""
        return self.pessoa.documento if self.pessoa else ""

    @cached_property
    def rg_pessoa(self: "Certidao") -> str:
        """Retorna o RG da pessoa associada à certidão."""
        return self.pessoa.rg if self.pessoa else ""

    @cached_property
    def numero_pedido(self: "Certidao") -> str:
        """Retorna o número do pedido associado ao item da certidão."""
        return self.item.pedido.numero_pedido if self.item else ""

    @cached_property
    def get_valores(self):
        """Obtém os valores da certidão com base na validade."""
        try:
            logger.debug(
                f"Iniciando obtenção dos valores da certidão para tipo_certidao: {self.tipo_certidao} e data de criação: {self.criado_em}",
            )

            # Condição principal de validação das datas e tipo de certidão
            condicao_principal = Q(
                tipo_certidao=self.tipo_certidao,
                data_inicio_validade__lte=self.criado_em,
                data_fim_validade__gte=self.criado_em,
            )

            # Condição alternativa de validação pelo código do tipo de certidão
            condicao_alternativa = Q(
                tipo_certidao__codigo=self.tipo_certidao.codigo,
                data_inicio_validade__lte=self.criado_em,
                data_fim_validade__gte=self.criado_em,
            )

            # Combinação das condições com OR
            valor_certidao = (
                ValorCertidao.objects.filter(
                    condicao_principal | condicao_alternativa,
                )
                .order_by("data_inicio_validade")
                .last()
            )

            logger.debug(f"Valores da certidão obtidos: {valor_certidao}")
            return valor_certidao
        except Exception as e:
            logger.exception(f"Erro ao obter valores da certidão: {e}")
            return None

    @cached_property
    def desconto_tipo_tributacao(self) -> Decimal:
        """Calcula o desconto com base no tipo de tributação."""
        try:
            logger.debug(
                f"Iniciando cálculo do desconto de tributação para tipo_tributacao: {self.tipo_tributacao}",
            )
            calculo = Decimal("0.0")
            if self.tipo_tributacao:
                calculo = Decimal(self.tipo_tributacao.percentual_desconto) * Decimal(
                    "0.01",
                )
                logger.debug(f"Desconto calculado: {calculo}")
            return calculo
        except Exception as e:
            logger.exception(f"Erro ao calcular desconto de tributação: {e}")
            raise

    @cached_property
    def tributacao(self):
        """Retorna a descrição da tributação."""
        try:
            descricao_tributacao = (
                self.tipo_tributacao.descricao if self.tipo_tributacao else "Normal"
            )
            logger.debug(f"Descrição da tributação: {descricao_tributacao}")
            return descricao_tributacao
        except Exception as e:
            logger.exception(f"Erro ao obter descrição da tributação: {e}")
            return "Normal"

    @cached_property
    def taxa_fiscal_judiciaria_calculada(self) -> Decimal:
        """Calcula a taxa fiscal judiciária."""
        try:
            logger.debug("Iniciando o cálculo da taxa fiscal judiciária.")
            resultado = self.get_valores
            logger.debug(f"Resultado obtido de get_valores: {resultado}")
            if not resultado:
                logger.debug("Resultado é None ou vazio. Retornando 0.0.")
                return Decimal(0.0)
            valor = resultado.taxa_fiscal_judiciaria if resultado else 0
            logger.debug(f"Valor da taxa fiscal judiciária: {valor}")
            if self.tipo_tributacao.outros_codigo_trib_tj:
                logger.debug("Tipo de tributação tem outros_codigo_trib_tj.")
                if (
                    self.tipo_tributacao.outros_codigo_trib_tj
                    in get_tributacao_outros_cobrar_taxa_judiciaria(self)
                ):
                    logger.debug(
                        "Código de tributação encontrado na lista de cobrança.",
                    )
                    return valor
                else:
                    desconto = self.desconto_tipo_tributacao
                    logger.debug(
                        f"Código de tributação não encontrado. Aplicando desconto de {desconto}.",
                    )
                    return valor * (1 - desconto)
            else:
                desconto = self.desconto_tipo_tributacao
                logger.debug(
                    f"Sem código de tributação específico. Aplicando desconto de {desconto}.",
                )
                return valor * (1 - desconto)
        except Exception as e:
            logger.exception(f"Erro ao calcular taxa fiscal judiciária: {e}")
            raise

    @cached_property
    def emolumento_liquido_calculado(self) -> Decimal:
        """Calcula o valor do emolumento líquido (sem recompe)."""
        try:
            logger.debug("Iniciando o cálculo do emolumento líquido.")
            valores = self.get_valores
            logger.debug(f"Valores obtidos de get_valores: {valores}")
            valor = Decimal(valores.valor if valores else 0)
            logger.debug(f"Valor inicial: {valor}")
            recompe = Decimal(self.recompe_calculado)
            valor -= recompe
            logger.debug(f"Valor após subtrair recompe ({recompe}): {valor}")
            desconto = self.desconto_tipo_tributacao
            valor_final = valor * (1 - desconto)
            logger.debug(f"Valor após aplicar desconto de {desconto}: {valor_final}")
            valor_arredondado = self._arredondar_valor(valor_final)
            logger.debug(f"Valor final arredondado: {valor_arredondado}")
            return valor_arredondado
        except Exception as e:
            logger.exception(f"Erro ao calcular emolumento líquido: {e}")
            raise

    @cached_property
    def emolumento_bruto_calculado(self) -> Decimal:
        """Calcula o valor bruto do emolumento."""
        try:
            logger.debug("Iniciando cálculo do emolumento bruto.")
            resultado = self.get_valores
            logger.debug(f"Resultado obtido de get_valores: {resultado}")

            valor = resultado.valor if resultado else 0
            logger.debug(f"Valor inicial: {valor}")

            desconto = self.desconto_tipo_tributacao
            logger.debug(f"Desconto tipo tributação: {desconto}")

            valor_final = Decimal(valor) * (1 - desconto)
            logger.debug(f"Valor final antes do arredondamento: {valor_final}")

            valor_arredondado = self._arredondar_valor(valor_final)
            logger.debug(f"Valor final arredondado: {valor_arredondado}")

            return valor_arredondado
        except Exception as e:
            logger.exception(f"Erro ao calcular emolumento bruto: {e}")
            raise

    @cached_property
    def recompe_calculado(self) -> Decimal:
        """Calcula o valor do recompe baseado no valor bruto menos o desconto de tributação."""
        try:
            logger.debug("Iniciando o cálculo do recompe.")

            resultado = self.get_valores
            if resultado:
                valor = resultado.recompe_calculado
                logger.debug(f"Valor bruto obtido: {valor}")
            else:
                valor = 0
                logger.debug("Nenhum resultado encontrado, valor definido como 0.")

            desconto = 1 - self.desconto_tipo_tributacao
            logger.debug(
                f"Desconto de tributação: {self.desconto_tipo_tributacao} (fator de multiplicação: {desconto})",
            )

            valor_final = Decimal(valor) * Decimal(desconto)
            logger.debug(
                f"Valor final calculado antes do arredondamento: {valor_final}",
            )

            valor_final_arredondado = self._arredondar_valor(valor_final)
            logger.debug(f"Valor final após arredondamento: {valor_final_arredondado}")

            return valor_final_arredondado
        except Exception as e:
            logger.exception(f"Erro ao calcular recompe: {e}")
            raise

    @cached_property
    def total(self) -> Decimal:
        """Calcula o valor total da certidão."""
        logger.debug("Iniciando cálculo do valor total da certidão.")
        try:
            resultado = self.get_valores
            logger.debug(f"Valores obtidos: {resultado}")

            valor = resultado.total if resultado else 0
            logger.debug(f"Valor inicial: {valor}")

            desconto = self.desconto_tipo_tributacao
            logger.debug(f"Desconto aplicado: {desconto}")

            retorno = valor * (1 - desconto)
            valor_final = self._arredondar_valor(retorno)
            logger.debug(f"Valor total calculado (arredondado): {valor_final}")

            return valor_final
        except Exception as e:
            logger.exception(f"Erro ao calcular valor total: {e}")
            raise

    def get_issqn(self):
        """Obtém o ISSQN aplicável com base na data de emissão."""
        logger.debug("Iniciando obtenção do ISSQN.")
        try:
            if self.data_emissao:
                logger.debug(f"Data de emissão fornecida: {self.data_emissao}")
                issqn = (
                    Issqn.objects.filter(data_inicio__lte=self.data_emissao)
                    .order_by("-data_inicio")
                    .first()
                )
            else:
                logger.debug(
                    "Data de emissão não fornecida, usando o ISSQN mais recente.",
                )
                issqn = Issqn.objects.order_by("-data_inicio").first()
            logger.debug(f"ISSQN obtido: {issqn}")
            return issqn
        except Exception as e:
            logger.exception(f"Erro ao obter ISSQN: {e}")
            return None

    @cached_property
    def issqn_calculado(self) -> Decimal:
        logger.debug("Iniciando cálculo do ISSQN.")
        issqn = self.get_issqn()
        percentual_issqn = issqn.percentual if issqn else Decimal(0.0)
        logger.debug(f"Percentual de ISSQN: {percentual_issqn}")
        valor_final = (
            (Decimal(percentual_issqn) / Decimal(100))
            * (1 - Decimal(self.desconto_tipo_tributacao))
        ) * self.emolumento_liquido_calculado
        valor_arredondado = self._arredondar_valor(valor_final)
        logger.debug(f"ISSQN calculado (arredondado): {valor_arredondado}")
        return valor_arredondado

    def _arredondar_valor(self, valor: Decimal) -> Decimal:
        """Arredonda o valor para duas casas decimais."""
        valor_arredondado = valor.quantize(Decimal("0.01"))
        logger.debug(f"Valor arredondado: {valor_arredondado}")
        return valor_arredondado

    @cached_property
    def nome(self):
        return f"{self.tipo_certidao.nome}".title() if self.tipo_certidao else None

    @cached_property
    def codigo_fiscal(self):
        return self.tipo_certidao.codigo

    @cached_property
    def nome_com_codigo(self):
        return (
            f"{self.tipo_certidao.nome} ({self.tipo_certidao.codigo})".title()
            if self.tipo_certidao
            else None
        )

    @cached_property
    def qualificacao(self) -> str | None:
        if self.imovel:
            return f"{self.tributacao} → {self.imovel}"
        elif self.pessoa:
            return f"{self.tributacao} → {self.pessoa}"

        return None

    @cached_property
    def qualificacao_completa(self) -> str | None:
        return f"{self.nome_com_codigo} → {self.qualificacao}"

    @cached_property
    def qualificacao_numero_imovel_pessoa(self) -> str | None:
        if self.imovel:
            return f"{self.imovel}"
        elif self.pessoa:
            return f"{self.pessoa}"

        return None

    @cached_property
    def qualificacao_tributacao(self) -> str | None:
        if self.imovel or self.pessoa:
            return f"{self.tributacao}"

        return None

    def selar(self: "Certidao"):
        from apps.home.services import sqlserver

        pedido: PedidoCertidao = self.item.pedido

        with transaction.atomic():
            try:
                retorno = sqlserver.selar_certidao(self)
                if retorno:
                    pedido.registrar_andamento_selo(self)
                else:
                    msg = f"Não foi possivel selar: {pedido}. Verifique se já foi selada anteriormente."
                    raise Exception(msg)
            except Exception as e:
                logger.exception(
                    f"Erro ao selar certidão {pedido}: {e}",
                )
                raise

    def get_selos_sql_server(self: "Certidao", selos):
        if selos:
            SeloEletronico.criar_atualizar_selos_certidao(self, selos)

            # Atualizar o selo no SQL SERVER
            usuario = User.get_usuario_sistema()
            if usuario.cartorio.usar_selo_sql_server == "S":
                from apps.home.services.firebird import (
                    update_firebird_temporario_sql_server,
                )

                update_firebird_temporario_sql_server(selos)

        return self.selos_da_certidao.all()

    def get_selos(self):
        return self.selos_da_certidao.all()

    @cached_property
    def principal(self) -> str:
        selos = self.get_selos()
        return SIM if selos.count() > 1 else NAO

    def calcular_total(self):
        """Calcula o valor total das certidões de um mesmo tipo para uma pessoa."""
        # Filtra as certidões pela pessoa e tipo de certidão corretamente
        certidoes = Certidao.objects.filter(
            pessoa=self.pessoa,
            tipo_certidao__nome=self.tipo_certidao.nome,
        )
        # Soma os valores de 'total' para o conjunto de certidões filtrado

        return sum(c.total for c in certidoes)

    def get_update_url(self):
        return reverse("home:pedido_certidao_editar_certidao", kwargs={"pk": self.pk})

    def get_print_url(self):
        return reverse("home:pedido_certidao_imprimir_certidao", kwargs={"pk": self.pk})

    def get_delete_url(self):
        return reverse("home:pedido_certidao_excluir_certidao", kwargs={"pk": self.pk})

    @classmethod
    def atualizar_valores_selo_sqlserver(cls) -> None:
        from apps.home.services import sqlserver

        with transaction.atomic():
            try:
                sqlserver.atualizar_valores(cls)
            except Exception as e:
                logger.exception(
                    f"Erro ao atualizar valores certidão no sql_server: {e}",
                )
                raise

    @classmethod
    def atualizar_eh_principal_selo_sqlserver(cls, numero_pedido) -> None:
        from apps.home.services import sqlserver

        with transaction.atomic():
            try:
                sqlserver.atualizar_eh_principal(cls, numero_pedido)
            except Exception as e:
                logger.exception(
                    f"Erro ao atualizar valores certidão no sql_server: {e}",
                )
                raise

    @cached_property
    def numero_pedido_inteiro(self: "Certidao") -> str:
        """Retorna o número do pedido associado ao item da certidão."""
        return str(self.item.pedido.numero_pedido).replace(".", "").replace(",", "")


# class TipoAndamento(models.Model):
#     id: uuid.uuid4 = UUIDPrimaryKeyField()
#     nome:str = models.CharField(max_length=100, blank=True)

#
#     def __str__(self):
#         return self.nome

#     class Meta:
#         verbose_name = "Tipo de Andamento"
#         verbose_name_plural = "Tipos de Andamento"


class TipoAndamentoCertidao(BaseModel):
    CRIACAO_PEDIDO = "CP", _("Criação de Pedido do Certidão")
    # ALTERACAO_STATUS = "AS", _("Alteração de Status")
    # ATUALIZACAO_DADOS = "AD", _("Atualização de Dados")
    RECIBO_IMPRESSO = "RI", _("Recibo Impresso")

    NAO_CONSTA = "0", _("Sem Descrição")
    RECEPCAO = "1", _("Recepção")
    CONFECIONADA = "2", _("Passou para Confeccionada")
    ENTREGA = "3", _("Entrega de Certidão")
    SELO = "4", _("Gerar Selo")
    ACERTO_CAIXA = "5", _("Acerto Diferença caixa")
    EXIGENCIA = "6", _("Exigência")
    DIFERENCA_CAIXA = "7", _("Diferença de valor Certidão")
    PEDIDO_CERTIDAO_NAO_PODE_SER_FEITO = "8", _("Pedido não pode ser feito")
    PEDIDO_CANCELADO_GERAR_DEVOLUCAO = "9", _("Cancelar e devolver financeiro")
    PEDIDO_CANCELADO = "10", _("Somente Cancelar")
    PEDIDO_CERTIDAO_CONFIRMADO = "14", _("Pedido Confirmado")
    PEDIDO_POSTADO_ONR = "15", _("Pedido Postado ONR")
    IMPRESSAO = "16", _("Impressão de Certidão")

    CHOICES = [
        CRIACAO_PEDIDO,
        # ALTERACAO_STATUS,
        # ATUALIZACAO_DADOS,
        RECIBO_IMPRESSO,
        NAO_CONSTA,
        RECEPCAO,
        CONFECIONADA,
        ENTREGA,
        SELO,
        ACERTO_CAIXA,
        EXIGENCIA,
        DIFERENCA_CAIXA,
        PEDIDO_CERTIDAO_NAO_PODE_SER_FEITO,
        PEDIDO_CANCELADO_GERAR_DEVOLUCAO,
        PEDIDO_CANCELADO,
        PEDIDO_CERTIDAO_CONFIRMADO,
        PEDIDO_POSTADO_ONR,
        IMPRESSAO,
    ]

    descricao: str = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        unique=True,
    )
    codigo: str = models.CharField(
        max_length=2,
        choices=CHOICES,
        default=NAO_CONSTA[0],
        unique=True,
    )
    grupo_cancelado: bool = models.BooleanField(default=False)
    grupo_devolucao: bool = models.BooleanField(default=False)
    # grupo_pedido_recebido:bool = models.BooleanField(default=False)
    grupo_fase_cartorio: bool = models.BooleanField(default=False)
    grupo_pedido_confirmado: bool = models.BooleanField(default=False)
    grupo_reciboimpresso: bool = models.BooleanField(default=False)
    grupo_selo: bool = models.BooleanField(default=False)
    grupo_recepcao: bool = models.BooleanField(default=False)
    grupo_gerar_andamento_agenda: bool = models.BooleanField(default=False)
    grupo_gerar_certidao: bool = models.BooleanField(default=False)
    grupo_certidao_pronta: bool = models.BooleanField(default=False)
    grupo_certidao_entregue: bool = models.BooleanField(default=False)
    grupo_certidao_exigencia: bool = models.BooleanField(default=False)
    obrigatorio_selo: bool = models.BooleanField(default=False)

    exibir_botao_opcoes: bool = models.BooleanField(default=False)

    _choice_dict = dict(CHOICES)

    class Meta:
        verbose_name = "Tipo de Andamento de Certidão"
        verbose_name_plural = "Tipos de Andamento de Certidão"
        ordering = ["descricao"]

    def __str__(self) -> str:
        return self.descricao

    @classmethod
    def get_descricao(cls, value) -> str:
        return cls._choice_dict.get(value, "Outros")

    @staticmethod
    def criar_padroes() -> None:
        for codigo, descricao in TipoAndamentoCertidao.CHOICES:
            TipoAndamentoCertidao.objects.get_or_create(
                codigo=codigo,
                defaults={"descricao": descricao},
            )

    @classmethod
    def obter_exibir_botao_opcoes(cls) -> QuerySet:
        return cls.objects.filter(exibir_botao_opcoes=True)


class PedidoCertidaoAndamento(BaseModel):
    tipo_andamento: TipoAndamentoCertidao = models.ForeignKey(
        TipoAndamentoCertidao,
        to_field="codigo",
        on_delete=models.CASCADE,
        db_index=True,
    )
    pedido = models.ForeignKey(
        PedidoCertidao,
        on_delete=models.CASCADE,
        related_name="andamentos",
        null=True,
    )
    data_hora: datetime = models.DateTimeField(
        default=timezone.now,
        verbose_name="Data e Hora",
    )
    descricao = CKEditor5Field(
        config_name="default",
        null=True,
        blank=True,
        verbose_name="Descrição",
    )
    colaborador_destino = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="colaborador_destino",
        verbose_name="Encaminhado Para",
    )
    certidao = models.ForeignKey(
        Certidao,
        on_delete=models.CASCADE,
        related_name="andamentos_certidao",
        null=True,
    )

    # obrigatorio_selo:bool = models.BooleanField(null=True, default=False)
    ativo: bool = models.BooleanField(default=True)

    modelo = models.ForeignKey(ModeloTexto, on_delete=models.CASCADE, null=True)

    class Meta:
        verbose_name = "Certidao Andamento"
        verbose_name_plural = "Certidao Andamentos"
        ordering = ["-data_hora"]

    def __str__(self) -> str:
        # return f"{self.get_tipo_andamento_display()} - {self.data_hora.strftime(settings.DATE_FORMAT_STR)}"
        return f"{self.tipo_andamento.descricao} em {self.data_hora.strftime(settings.DATE_FORMAT_STR)} por {self.criado_por}"

    def save(self, *args, **kwargs):
        if self.get_andamento_certidao_obrigatorio_selo():
            return "SELO_OBRIGATORIO"

        if not self.colaborador_destino and self.criado_por:
            self.colaborador_destino = self.criado_por
        super().save(*args, **kwargs)
        return None

    # def save(self, *args, **kwargs):
    #     if not self.colaborador_destino and self.criado_por:
    #         self.colaborador_destino = self.criado_por
    #     super().save(*args, **kwargs)

    # def save(self, *args, **kwargs):
    #     #    GRAVAR SIGNALS
    #     super().save(*args, **kwargs)

    @staticmethod
    def get_adicionar_ao_pedido_url(pedido_id: int) -> str:
        return reverse(
            "home:pedido_certidao_andamento_adicionar",
            kwargs={"pedido_id": pedido_id},
        )

    def exportar_para_firebird(self, user_id: int) -> None:
        if self.tipo_andamento.codigo == "CP" or self.tipo_andamento.codigo == "RI":
            tipo_andamento_id = 0
        else:
            # self.tipo_andamento:
            tipo_andamento_id = self.tipo_andamento_id

        try:
            with FbConnection() as db:
                db.begin_transaction()
                firebird.gravar_andamentos_pedido_certidao(
                    pedido_id=self.pedido.numero_pedido,
                    data=self.data_hora.strftime(settings.DATE_FIREBIRD_FORMAT),
                    funcionario_id=user_id,
                    tipo_andamento_id=tipo_andamento_id,
                    db=db,
                )
                db.commit()
            msg = "Sucesso ao exportar andamento de pedido de certidão no Firebird!"
            print(msg)
        except Exception as e:
            msg = f"Erro ao gravar andamento de pedido de certidão no Firebird: {e}"

            logger.exception(msg)

    @classmethod
    def get_grupo_gerar_andamento_agenda(cls) -> bool:
        return TipoAndamentoCertidao.objects.filter(
            grupo_gerar_andamento_agenda=True,
        ).exists()

    @classmethod
    def get_modelos_de_texto_certidao(cls) -> QuerySet:
        # modelo_texto = ModeloTexto.objects.filter(tipo__descricao="Andamento")
        modelo_texto = ModeloTexto.objects.filter(tipo__grupo_gerar_tipo_certidao=True)
        if not modelo_texto:
            modelo_texto = ModeloTexto.objects.all()
        return modelo_texto if modelo_texto else None

    def get_andamento_certidao_pronta(self) -> bool:
        return bool(
            TipoAndamentoCertidao.objects.filter(
                codigo=self.tipo_andamento_id,
                grupo_certidao_pronta=True,
            ).exists(),
        )

    # VERIFICAR SE O ANDAMENTO ESTA VINCULADO AO CANCELAMENTO
    def get_andamento_certidao_cancelado(self) -> bool:
        return bool(
            TipoAndamentoCertidao.objects.filter(
                codigo=self.tipo_andamento_id,
                grupo_cancelado=True,
            ).exists(),
        )

    # VERIFICAR SE O ANDAMENTO ESTA VINCULADO A EXIGENCIA
    def get_andamento_certidao_exigencia(self) -> bool:
        return bool(
            TipoAndamentoCertidao.objects.filter(
                codigo=self.tipo_andamento_id,
                grupo_certidao_exigencia=True,
            ).exists(),
        )

    # VERIFICAR SE O ANDAMENTO ESTA SELADO - CASO NAO ESTEJA E CANCELADO O ANDAMENTO
    def get_andamento_certidao_obrigatorio_selo(self) -> bool:
        andamento_certidao = TipoAndamentoCertidao.objects.filter(
            codigo=self.tipo_andamento_id,
            obrigatorio_selo=True,
        ).exists()

        if andamento_certidao:
            if self.pedido.quantidade_selos > 0:
                return False
            return "SELO_OBRIGATORIO"

        return False


class Projeto(BaseModel, PedidoONRMixin):
    numero_projeto = models.IntegerField(
        db_index=True,
        unique=True,
        verbose_name="Nº",
        help_text="Número do Projeto.",
    )

    nome_projeto = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Nome do Projeto",
    )

    observacoes = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name="Energia a ser atendida kWh hora",
    )

    localidade = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name="Localização do Projeto",
    )

    data_inicio_projeto: datetime = models.DateTimeField(
        verbose_name="Data Inicio Projeto",
        null=True,
    )

    data_fim_projeto: datetime = models.DateTimeField(
        verbose_name="Data Fim do Projeto",
        null=True,
    )

    fotovoltaico = models.BooleanField(default=False)  # Campo booleano
    biogas = models.BooleanField(default=False)
    hidrogenio = models.BooleanField(default=False)
    baterias = models.BooleanField(default=False)

    CATEGORIA_CHOICES = [
        ("residencial", "Residencial"),
        ("comercial", "Comercial"),
        ("industrial", "Industrial"),
        ("outro", "Outro - Importar"),
    ]

    categoria_projeto = models.CharField(
        max_length=20,
        choices=CATEGORIA_CHOICES,
        default="residencial",
    )

    latitude = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Latitude",
    )

    longitude = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Longitude",
    )

    CATEGORIA_INSTALACAO = [
        ("solo", "Solo"),
        ("telhado", "Telhado"),
    ]

    categoria_instalacao = models.CharField(
        max_length=20,
        choices=CATEGORIA_INSTALACAO,
        default="solo",
    )

    area_disponível_instalacao = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Área disponível para instalação",
    )

    horario_inicio_sol_pleno = models.TimeField(verbose_name="Horário de Início Sol Pleno", blank=True, null=True)

    horario_fim_sol_pleno = models.TimeField(verbose_name="Horário de Fim Sol Pleno", null=True, blank=True)

    # Consumo médio mensal estimado em kWh
    consumo_mensal_kwh = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Consumo mensal estimado (kWh)",
        null=True,
        blank=True,
        default=Decimal("533.00"),
        help_text="Informe o consumo médio mensal de energia elétrica (em kWh) que o projeto deve suprir."
    )

    # Horas de sol pleno por dia (média)
    horas_sol_dia = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=4.5,
        verbose_name="Horas de Sol Pleno por Dia",
        help_text="Média diária de horas com sol pleno (ex: 4.5 para região Sudeste)."
    )

    # Fator de perda do sistema (devido a temperatura, sujeira, etc.)
    fator_perda = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=0.80,
        verbose_name="Fator de Perda do Sistema",
        help_text="Percentual de perdas esperadas no sistema (ex: 0.80 = 80% de aproveitamento)."
    )

    # Quantidade de dias por mês (usado para simulação, geralmente 30)
    dias_mes = models.PositiveIntegerField(
        default=30,
        verbose_name="Dias por Mês",
        help_text="Número de dias por mês considerados na simulação (geralmente 30)."
    )

    # Vida útil estimada do sistema (em anos)
    vida_util_anos = models.PositiveIntegerField(
        default=25,
        verbose_name="Vida útil do sistema (anos)",
        help_text="Tempo estimado de funcionamento dos equipamentos fotovoltaicos."
    )

    demanda_ponta = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Demanda de Ponta - Em quilowatts (kW) - (azul)",
    )

    demanda_fora_ponta = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Demanda fora de ponta - Em quilowatts (kW) - (azul)",
    )

    demanda_contratada = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Demanda contratada - Em quilowatts (kW) - (verde)",
    )

    modalidade = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Modalidade - bandeira tarifaria",
    )

    subgrupo_tarifario = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Subgrupo tarifário (B1, B2, B3, A4) conforme a ANEEL",
    )

    migracao_para_mercado_livre_energia = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Perguntar ao usuário.",
    )

    history: AuditlogHistoryField = AuditlogHistoryField()

    class Meta:
        verbose_name = "Projeto"
        verbose_name_plural = "Projetos"
        indexes = [
            models.Index(fields=["numero_projeto"]),
        ]

    def __str__(self: "Projeto") -> str:
        return f"{self.numero_projeto} "

    def save(self: "Projeto", *args, **kwargs) -> None:
    # 👉 Atualize o campo desejado antes de salvar

        if self.latitude is None or self.longitude is None:
            GEO = geocode_view(self.localidade)

            # transforma de bytes → string → lista Python
            lat, lon = json.loads(GEO.content.decode("utf-8"))

            self.latitude = lat
            self.longitude = lon

        super().save(*args, **kwargs)


class Bateria(BaseModel, PedidoONRMixin):
    numero_bateria = models.IntegerField(
        db_index=True,
        unique=True,
        verbose_name="Nº",
        help_text="Número da Bateria.",
    )

    marca = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Marca.",
    )

    modelo = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    tipo_de_bateria = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    tensao_celula = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    capacidade = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    taxa_de_descarga = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    eficiencia = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    estado_de_carga = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    profundidade_de_descarga = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    densidade_de_energia = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    numero_maximo_ciclos = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    history: AuditlogHistoryField = AuditlogHistoryField()

    class Meta:
        verbose_name = "Bateria"
        verbose_name_plural = "Baterias"
        indexes = [
            models.Index(fields=["numero_bateria"]),
        ]

    def __str__(self: "Bateria") -> str:
        return f"{numero_bateria} "

    def save(self: "Bateria", *args, **kwargs) -> None:
        super().save(*args, **kwargs)


class Hidrogenio(BaseModel, PedidoONRMixin):
    numero_hidrogenio = models.IntegerField(
        db_index=True,
        unique=True,
        verbose_name="Nº",
        help_text="Número Hidrogenio.",
    )

    marca = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Marca.",
    )

    modelo = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    tipo_de_celula = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    numero_celulas = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    numero_celulas_stack = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    pontencial_nominal = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    tensao_maxima_saida = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    tensao_nomimal_saida = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    corrente_nominal_saida = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    consumo_hidrogenio = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    eficiencia = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    degracao_tempo = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    curva_eficiencia = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    saida_agua = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    temperatura_maxima = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    history: AuditlogHistoryField = AuditlogHistoryField()

    class Meta:
        verbose_name = "Hidrogenio"
        verbose_name_plural = "Hidrogenios"
        indexes = [
            models.Index(fields=["numero_hidrogenio"]),
        ]

    def __str__(self: "Hidrogenio") -> str:
        return f"{numero_hidrogenio} "

    def save(self: "Hidrogenio", *args, **kwargs) -> None:
        super().save(*args, **kwargs)


class CecModule(models.Model):
    name = models.TextField(db_column="Name", null=True, blank=True)
    manufacturer = models.TextField(db_column="Manufacturer", null=True, blank=True)
    technology = models.TextField(db_column="Technology", null=True, blank=True)
    bifacial = models.TextField(db_column="Bifacial", null=True, blank=True)
    stc = models.TextField(db_column="STC", null=True, blank=True)
    ptc = models.TextField(db_column="PTC", null=True, blank=True)
    a_c = models.TextField(db_column="A_c", null=True, blank=True)
    length = models.TextField(db_column="Length", null=True, blank=True)
    width = models.TextField(db_column="Width", null=True, blank=True)
    n_s = models.TextField(db_column="N_s", null=True, blank=True)
    i_sc_ref = models.TextField(db_column="I_sc_ref", null=True, blank=True)
    v_oc_ref = models.TextField(db_column="V_oc_ref", null=True, blank=True)
    i_mp_ref = models.TextField(db_column="I_mp_ref", null=True, blank=True)
    v_mp_ref = models.TextField(db_column="V_mp_ref", null=True, blank=True)
    alpha_sc = models.TextField(db_column="alpha_sc", null=True, blank=True)
    beta_oc = models.TextField(db_column="beta_oc", null=True, blank=True)
    t_noct = models.TextField(db_column="T_NOCT", null=True, blank=True)
    a_ref = models.TextField(db_column="a_ref", null=True, blank=True)
    i_l_ref = models.TextField(db_column="I_L_ref", null=True, blank=True)
    i_o_ref = models.TextField(db_column="I_o_ref", null=True, blank=True)
    r_s = models.TextField(db_column="R_s", null=True, blank=True)
    r_sh_ref = models.TextField(db_column="R_sh_ref", null=True, blank=True)
    adjust = models.TextField(db_column="Adjust", null=True, blank=True)
    gamma_pmp = models.TextField(db_column="gamma_pmp", null=True, blank=True)
    bipv = models.TextField(db_column="BIPV", null=True, blank=True)
    version = models.TextField(db_column="Version", null=True, blank=True)
    date = models.TextField(db_column="Date", null=True, blank=True)

    class Meta:
        db_table = "cec_modules"
        verbose_name = "CEC Module"
        verbose_name_plural = "CEC Modules"

class PainelSolar(BaseModel, PedidoONRMixin):
    numero_hidrogenio = models.IntegerField(
        db_index=True,
        unique=True,
        verbose_name="Nº",
        help_text="Número Painel Solar.",
    )

    marca = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Informe a marca do painel solar, conforme especificado pelo fabricante. Exemplo: Trina, Canadian Solar, Jinko.",
    )

    modelo = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    tipo_de_celula = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    numero_celulas = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    numero_celulas_stack = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    tensao_maxima_saida = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    pontencial_nominal = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Indique a tensão nominal do equipamento em volts (V), como especificado pelo fabricante. Exemplo: 12V, 24V, 48V.",
    )

    tensao_nomimal_saida = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    corrente_nominal_saida = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    consumo_hidrogenio = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    eficiencia = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    degracao_tempo = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    curva_eficiencia = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    saida_agua = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    temperatura_maxima = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    voc = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    isc = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    vmp = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    mp = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    coef_temp_pot_max_upmax = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    coef_temp_voc_uvoc = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    coef_temp_isc_uisc = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    corrente_maxima_potencia = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    history: AuditlogHistoryField = AuditlogHistoryField()

    class Meta:
        verbose_name = "PaineSolar"
        verbose_name_plural = "PaineSolares"
        indexes = [
            models.Index(fields=["numero_hidrogenio"]),
        ]

    def __str__(self: "PaineSolar") -> str:
        return f"{numero_hidrogenio} "

    def save(self: "PaineSolar", *args, **kwargs) -> None:
        super().save(*args, **kwargs)


class Inversor(BaseModel, PedidoONRMixin):
    numero_hidrogenio = models.IntegerField(
        db_index=True,
        unique=True,
        verbose_name="Nº",
        help_text="Número Inversor.",
    )

    marca = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Marca.",
    )

    modelo = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    tipo_de_celula = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    numero_celulas = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    numero_celulas_stack = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    pontencial_nominal = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    tensao_nomimal_saida = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    corrente_nominal_saida = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    consumo_hidrogenio = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    eficiencia = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    degracao_tempo = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    curva_eficiencia = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    saida_agua = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    temperatura_maxima = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    pot_max_entrada = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Pot Max entrada",
    )

    n_mppta = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    corr_dc_maxa = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    corrente_dc_max_totala = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    intervalo_tensao_dc_inicial = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    intervalo_tensao_dc_final = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    tensao_dc_nominal = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    intervalo_tensao_mppt_inicial = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    intervalo_tensao_mppt_final = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    pot_ac_maxa = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    corrente_falha_maxima = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    duracao_maxima_falha = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    corrente_ac_maxa = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    eficiencia_maxa = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    intervalo_tensao_ac_inicial = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    intervalo_tensao_ac_final = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    frequencia = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    distorcoes_harmonicas_totais = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Distorções harmonicas totais (THD)",
        help_text="",
    )

    fator_de_potencia_fpa = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Fator de potencia (FP)",
        help_text="",
    )

    # CAMPOS FELIPE
    numero_paineis = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="",
    )

    numero_mppts = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="",
    )

    potencia_maxima_entrada = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="",
    )

    corrente_maxima = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="",
    )

    tensao_nominal_entrada = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="",
    )

    tensao_minima_entrada = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="",
    )

    tensao_maxima_entrada = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="",
    )

    mppt_tensao_minima = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="",
    )

    mppt_tensao_maxima = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="",
    )

    potencia_maxima_saida = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="",
    )

    corrente_maxima_saida = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="",
    )

    tensao_nominal_saida = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="",
    )

    frequencia_saida = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="",
    )

    eficiencia_inversor = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="",
    )

    maximo_tdh = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="",
    )

    fator_potencia = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="",
    )

    history: AuditlogHistoryField = AuditlogHistoryField()

    class Meta:
        verbose_name = "Inversor"
        verbose_name_plural = "inversores"
        indexes = [
            models.Index(fields=["numero_hidrogenio"]),
        ]

    def __str__(self: "Inversor") -> str:
        return f"{numero_hidrogenio} "

    def save(self: "Inversor", *args, **kwargs) -> None:
        super().save(*args, **kwargs)

class ProjetoPainelSolar(BaseModel, PedidoONRMixin):
    painelsolar = models.ForeignKey(PainelSolar, on_delete=models.CASCADE)
    projeto = models.ForeignKey(Projeto, on_delete=models.CASCADE)

class ProjetoInversor(BaseModel, PedidoONRMixin):
    inversor = models.ForeignKey(Inversor, on_delete=models.CASCADE)
    projeto = models.ForeignKey(Projeto, on_delete=models.CASCADE)


class DadosSimulacao(models.Model):
    pmp = models.FloatField(null=True, blank=True, default=178.65)
    isc = models.FloatField(null=True, blank=True, default=8.07)
    voc = models.FloatField(null=True, blank=True, default=29.35)
    imp = models.FloatField(null=True, blank=True, default=7.57)
    vmp = models.FloatField(null=True, blank=True, default=23.60)
    uisc = models.FloatField(null=True, blank=True, default=0.00222)
    uvoc = models.FloatField(null=True, blank=True, default=-0.107)
    upmp = models.FloatField(null=True, blank=True, default=-0.49)
    material_painel = models.CharField(max_length=100, blank=True, null=True, default="Silicio")
    eficiencia_painel = models.FloatField(null=True, blank=True, default=15)
    nm_paineis = models.FloatField(null=True, blank=True, default=18)
    nm_mppt = models.FloatField(null=True, blank=True, default=2)
    in_pmax = models.FloatField(null=True, blank=True, default=12.3)
    imax_mppt = models.FloatField(null=True, blank=True, default=18)
    in_vnom = models.FloatField(null=True, blank=True, default=420)
    in_vmin = models.FloatField(null=True, blank=True, default=80)
    in_vmax = models.FloatField(null=True, blank=True, default=1000)
    in_mpp_vmin = models.FloatField(null=True, blank=True, default=240)
    in_mpp_vmax = models.FloatField(null=True, blank=True, default=800)
    out_pmax = models.FloatField(null=True, blank=True, default=8.2)
    out_imax = models.FloatField(null=True, blank=True, default=34.2)
    out_vnom = models.FloatField(null=True, blank=True, default=220)
    out_freq = models.FloatField(null=True, blank=True, default=60)
    eficiencia_inv = models.FloatField(null=True, blank=True, default=0.98)
    max_thd = models.FloatField(null=True, blank=True, default=5)
    fator_potencia = models.FloatField(null=True, blank=True, default=0.85)

class SugestaoEquipamento(models.Model):
    pergunta = models.TextField()
    resposta = models.TextField()
    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.pergunta[:50]


class ResultadoAnalise(models.Model):
    projeto = models.ForeignKey("home.Projeto", on_delete=models.CASCADE)
    painel = models.ForeignKey("home.PainelSolar", on_delete=models.CASCADE)
    quantidade_paineis = models.PositiveIntegerField()
    producao_mensal = models.DecimalField(max_digits=10, decimal_places=2)
    custo_total = models.DecimalField(max_digits=12, decimal_places=2)
    custo_por_kwh = models.DecimalField(max_digits=6, decimal_places=4)
    gerado_em = models.DateTimeField(auto_now_add=True)


def geocode_view(cidade=None):
    NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
    USER_AGENT = os.getenv("GEOCODE_USER_AGENT", "sua-app/1.0 (contato: email@exemplo.com)")

    #if cidade:
    city = cidade
    #else:
    #city = request.GET.get("city")

    #country = request.GET.get("country")  # ex.: "br"
    country = "br"

    if not city or len(city) < 2:
        return JsonResponse({"detail": "Informe city"}, status=400)

    params = {
        "q": city,
        "format": "json",
        "limit": 1,
        "addressdetails": 0,
    }
    if country:
        params["countrycodes"] = country.lower()

    headers = {"User-Agent": USER_AGENT}

    try:
        with httpx.Client(timeout=10) as client:
            r = client.get(NOMINATIM_URL, params=params, headers=headers)
        if r.status_code != 200:
            return JsonResponse({"detail": "Erro ao consultar geocodificador"}, status=502)
        data = r.json()
        if not data:
            return JsonResponse({"detail": "Cidade não encontrada"}, status=404)
        item = data[0]

        # json = JsonResponse({
        #     "city": city,
        #     "lat": float(item["lat"]),
        #     "lon": float(item["lon"]),
        #     "display_name": item.get("display_name", city),
        # })

        return JsonResponse([float(item["lat"]), float(item["lon"])], safe=False)

    except Exception as e:
        return JsonResponse({"detail": f"Falha: {e}"}, status=500)

    from django.conf import settings
#from django.db import models

class Empresa(models.Model):
    id_externo = models.CharField("ID externo", max_length=64, blank=True, null=True)
    nome = models.CharField(max_length=200, db_index=True)
    preco_por_watt = models.DecimalField("Preço por Wp (R$)", max_digits=10, decimal_places=2)
    garantia_anos = models.PositiveIntegerField(default=25)
    nota_servico = models.DecimalField("Nota de serviço (0–5)", max_digits=3, decimal_places=1)
    eficiencia_modulo = models.DecimalField("Eficiência do módulo (%)", max_digits=4, decimal_places=1)

    class Meta:
        verbose_name = "Empresa FV"
        verbose_name_plural = "Empresas FV"
        ordering = ["-nota_servico", "preco_por_watt"]

    def __str__(self):
        return self.nome


class PerguntaCustom(models.Model):
    """Perguntas adicionais opcionais (executam código com uma função run(context))"""
    titulo = models.CharField(max_length=200)
    descricao = models.TextField(blank=True)
    codigo_handler = models.TextField(
        help_text=(
            "Defina uma função run(context) que retorne HTML seguro (string) "
            "ou um dicionário com {'html': '<...>'}. Use com cautela."
        )
    )
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criado_em"]

    def __str__(self):
        return self.titulo
