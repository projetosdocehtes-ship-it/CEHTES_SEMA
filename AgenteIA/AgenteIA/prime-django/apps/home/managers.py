import base64
import contextlib
import functools
import logging
import operator
import re
import time
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING

import webdriver_manager
from dateutil.relativedelta import relativedelta
from django.apps import apps
from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError, OperationalError, transaction
from django.db.models import (
    Case,
    Count,
    IntegerField,
    Manager,
    Max,
    OuterRef,
    Q,
    QuerySet,
    Subquery,
    Sum,
    Value,
    When,
)
from django.db.models.functions import TruncDate
from django.utils import timezone

from apps.home import models
from apps.home.helpers import (
    adicionar_fuso_horario_em_data,
    converter_string_para_data,
    formatar_cnpj,
    formatar_cpf,
    formatar_variavel,
    get_data_util_em_x_dias,
    get_user_id_2,
)
from apps.home.padroes import NAO, PROVISORIO, SIM
from apps.home.tipos import TipoClasseRegistro, TipoParte, TipoRegistro, TipoSimNao
from core.utils.firebird_utils import FbConnection
from core.utils.formatacoes import formatar_nome

logger = logging.getLogger(__name__)
logger.debug(f"Iniciando {__name__}")


def upper_case(text: str) -> str:
    """
    Converte uma string para maiúsculas.

    Args:
    ----
        text (str): A string a ser convertida.

    Returns:
    -------
        str: A string convertida para maiúsculas.

    """
    return text.upper()


if TYPE_CHECKING:
    from apps.home.models import (
        AtoPratica,
        Colaborador,
        Event,
        Financeiro,
        Livro01Andamento,
        Livro01Protocolo,
        Livro05,
        PedidoCertidao,
        PedidoItem,
        PedidoParte,
        SeloEletronico,
        TipoAndamento,
        Vinculo,
    )
    from apps.home.models import Pedido as PedidoCetidao


class PedidoItemManager(Manager):
    def criar_do_fb(
        self,
        pedido_fb: dict,
        pedido_item_fb: dict,
        ato: "AtoPratica",
    ) -> "PedidoItem":
        from apps.home.models import models_home

        pedido_item_id = pedido_item_fb["CHAVE_PEDIDOS_ITENS"]
        numero_registro = pedido_item_fb.get("NUMERO_IMOVEL")
        numero_ato = pedido_item_fb.get("NUMEROATO")
        numero_ri = pedido_item_fb.get("NUMERO_RI")

        if numero_registro:
            numero_registro = (
                str(numero_registro)
                .replace(".", "")
                .replace("-", "")
                .replace("/", "")
                .replace("'", "")
            )

        if not numero_registro or numero_registro == 0 or numero_registro == "":
            numero_registro = None
            numero_ato = None
            numero_ri = None

        numero_ri = None if not numero_registro else numero_ri

        models_home.ChecklistRealizadoHistorico.objects.deletar_por_pedido_item_id(
            pedido_item_id,
        )

        models_home.NotaDevolucaoTexto.objects.deletar_por_pedido_item_id(
            pedido_item_id,
        )

        # BUSCANDO COLABORADOR
        if pedido_item_fb["CHAVE_FUNCIONARIOS"]:
            colaborador = pedido_item_fb["CHAVE_FUNCIONARIOS"]
        else:
            colaborador = models_home.Colaborador.get_or_create_default()
            colaborador = colaborador.antigo_id

        try:
            with transaction.atomic():
                cartorio_model = apps.get_model("cartorios", "Cartorio")

                valor_emolumento = pedido_item_fb["VALOREMOLUMENTO"]
                valor_fundoestado = pedido_item_fb["VALOR_FUNDOESTADO"]

                # ALFENAS ADICIONAR CAMPOS PARA O SQLSERVER
                usar_selo_sql_server = cartorio_model.objects.all().values_list(
                    "usar_selo_sql_server",
                    flat=True,
                )[0]
                if usar_selo_sql_server == SIM:
                    valor_emolumento = valor_emolumento - valor_fundoestado

                obj, created = models_home.PedidoItem.objects.update_or_create(
                    pk=pedido_item_id,
                    defaults={
                        # "pedido": self,
                        "pedido_id": pedido_fb["CHAVE_PEDIDOS"],
                        # "ato_id": ato.pk if ato else None
                        "ato_id": pedido_item_fb["CHAVE_ATOS"],
                        "cdhu": pedido_item_fb["CDHU"],
                        "valor_avaliacao": (
                            pedido_item_fb["VALORAVALIACAO"]
                            if pedido_item_fb["VALORAVALIACAO"]
                            else 0
                        ),
                        # "valor_total": pedido_item_fb["VALORTOTALITEM"] if pedido_item_fb["VALORTOTALITEM"] else 0,
                        "codigo_tabela": pedido_item_fb["CODIGO_TABELA"],
                        "tipo_registro": (
                            pedido_item_fb["TIPO_IMOVEL"]
                            if pedido_item_fb["TIPO_IMOVEL"]
                            else None
                        ),
                        "numero_registro": numero_registro,
                        "numero_ato": numero_ato,
                        "numero_ri": numero_ri,
                        "custas_id": pedido_item_fb["CUSTAS"],
                        "tabelacalculo_id": pedido_item_fb["TABELACALCULO"],
                        "valor_emolumento": (
                            valor_emolumento if valor_emolumento else 0
                        ),
                        "valor_tfj": (
                            pedido_item_fb["VALORRECEITAADICIONAL1"]
                            if pedido_item_fb["VALORRECEITAADICIONAL1"]
                            else 0
                        ),
                        "valor_issqn": (
                            pedido_item_fb["TAXA1"] if pedido_item_fb["TAXA1"] else 0
                        ),
                        "valor_fundo_estado": (
                            valor_fundoestado if valor_fundoestado else 0
                        ),
                        "colaborador": colaborador,
                        "titulo_id": pedido_item_fb["CHAVE_TITULOS"],
                        "numero_titulo": pedido_item_fb["NROTITULO"],
                        "data_pagamento": pedido_item_fb["DATA_PAGAMENTO"],
                        "valor_itbi": (
                            Decimal(pedido_item_fb["VALORITBI"])
                            if pedido_item_fb["VALORITBI"]
                            else 0.0
                        ),
                        "ato_numero": 0,
                        "vigencia_id": pedido_item_fb["CHAVE_VIGOR"],
                    },
                )
                if created:
                    logger.info(f"PEDIDO ITEM Inserido. PK: {obj.pk}")
                else:
                    logger.info(f"PEDIDO ITEM Atualizado. PK: {obj.pk}")
            return obj
        except Exception as e:
            logger.exception(f"ERRO ao criar PEDIDO ITEM: {e}")
            return None

    def get_registros_por_pedido(self, pedido_id: int):
        return self.filter(
            pedido=pedido_id,
            tipo_registro=TipoRegistro.MATRICULA,
            numero_registro__isnull=False,
            numero_registro__gte=1,
        ).order_by("numero_registro", "ato_numero")

    def get_registros_auxiliares_por_pedido(self, pedido_id: int):
        return self.filter(
            pedido_id=pedido_id,
            tipo_registro="A",
            numero_registro__isnull=False,
            numero_registro__gte=1,
        )

    def get_atos_principais_por_pedido(
        self,
        pedido_id: int,
    ) -> QuerySet["PedidoItem"]:
        from apps.home.models import models_home

        # Primeiro, obtenha os IDs de atos relacionados à ID do pedido fornecida
        atos_do_pedido = models_home.AtoPratica.objects.filter(ato_principal=SIM)

        return self.filter(
            pedido=pedido_id,
            numero_registro__gte=0,
            numero_registro__isnull=False,
            tipo_registro__in=[
                TipoRegistro.AVERBACAO,
                TipoRegistro.MATRICULA,
                TipoRegistro.TRANSCRICAO,
            ],
            ato__in=atos_do_pedido,
        ).order_by("numero_registro", "ato_numero")

    def get_titulos_principais_por_pedido(self, pedido_id):
        return self.filter(
            pedido=pedido_id,
            numero_registro__gte=0,
            numero_registro__isnull=False,
            tipo_registro__in=[
                TipoRegistro.AVERBACAO,
                TipoRegistro.MATRICULA,
                TipoRegistro.TRANSCRICAO,
            ],
        ).order_by("numero_registro", "ato_numero")

    def valor_total_emolumentos(self, pedido_id):
        resultado = self.filter(pedido=pedido_id).aggregate(Sum("valor_emolumento"))
        return resultado.get("valor_emolumento__sum", 0)

    def valor_total_tfj(self, pedido_id):
        resultado = self.filter(pedido=pedido_id).aggregate(Sum("valor_tfj"))
        return resultado.get("valor_tfj__sum", 0)

    def valor_total_issqn(self, pedido_id):
        resultado = self.filter(pedido=pedido_id).aggregate(Sum("valor_issqn"))
        return resultado.get("valor_issqn__sum", 0)

    def valor_total_recompe(self, pedido_id):
        resultado = self.filter(pedido=pedido_id).aggregate(Sum("valor_fundo_estado"))
        return resultado.get("valor_fundo_estado__sum", 0)

    def valor_total_protocolo(self, pedido_id):
        resultado = self.filter(pedido=pedido_id).aggregate(Sum("valor_total"))
        return resultado.get("valor_total__sum", 0)

    def deletar_por_pedido_id(self, pedido_id) -> None:
        logger.info(f"PEDIDO_ITEM: Deletando itens do Pedido {pedido_id}")
        # Filtra e deleta os objetos PedidoItem baseados no pedido_id
        self.get_queryset().filter(pedido_id=pedido_id).delete()

    def deletar_por_pedido_item_id(self, pk) -> None:
        self.get_queryset().filter(pk=pk).delete()

    def get_numero_ato_anterior(self, pedido_item):
        return (
            self.filter(
                pk__lt=pedido_item.pk,
                pedido_id=pedido_item.pedido.pk,
                numero_registro=pedido_item.numero_registro,
            )
            .values_list("numero_ato", flat=True)
            .last()
        )


# class Livro01ProtocoloManager(Manager):
#     def get_queryset(self) -> "Livro01ProtocoloQuerySet":
#         return Livro01ProtocoloQuerySet(self.model, using=self._db)

#     def filtrar_por_id(self, pk) -> "Livro01ProtocoloQuerySet":
#         return self.get_queryset().filtrar_por_id(pk)


class Livro01ProtocoloQuerySet(QuerySet):
    # def filter(self, *args, **kwargs):
    #     """Sobrescreve o método filter para adicionar data_reentrada por padrão."""
    #     qs = super().filter(*args, **kwargs)
    #     return qs._anotar_data_reentrada()._anotar_ultimo_colaborador()

    def deletar_por_pedido_id(self: "Livro01ProtocoloQuerySet", pedido_id) -> None:
        # Filtra e deleta os objetos baseados no pedido_id
        logger.info(f"Deletando protocolos do Pedido id: {pedido_id}.")
        protocolo = self.filter(pedido_id=pedido_id)
        logger.info(f"Protocolos deletados: {protocolo.count()}")
        protocolo.delete()

    def filtrar_por_id(
        self: "Livro01ProtocoloQuerySet",
        pk,
    ) -> "Livro01ProtocoloQuerySet":
        """Apenas o protocolo com o ID informado."""
        logger.debug(f"Filtrando protocolos pelo ID: {pk}")
        return self.filter(pk=pk)

    def filtrar_por_ids(
        self: "Livro01ProtocoloQuerySet",
        pks,
    ) -> "Livro01ProtocoloQuerySet":
        """Apenas os protocolos com os IDs informados."""
        logger.debug(f"Filtrando protocolos pelos IDs: {pks}")
        return self.filter(id__in=pks)

    def ordenar_por_numero(
        self: "Livro01ProtocoloQuerySet",
    ) -> "Livro01ProtocoloQuerySet":
        """Ordena os protocolos pelo número do protocolo."""
        logger.debug("Ordenando protocolos por número.")
        return self.order_by("-numero_protocolo")

    def filtrar_por_sem_fase(
        self: "Livro01ProtocoloQuerySet",
    ) -> "Livro01ProtocoloQuerySet":
        """Apenas os protocolos que não possuem fases_protocolo."""
        logger.debug("Filtrando protocolos sem fases.")
        return self.filter(fases_protocolo__isnull=True)

    def filtrar_por_data_distribuicao(
        self: "Livro01ProtocoloQuerySet",
        start_date,
        end_date,
    ) -> "Livro01ProtocoloQuerySet":
        """Apenas os protocolos distribuídos no período fornecido."""
        logger.debug(
            f"Filtrando protocolos distribuídos no período de {start_date} a {end_date}.",
        )
        return (
            self.filter(data_distribuicao__range=[start_date, end_date])
            .order_by("numero_protocolo")
            .select_related("fases_protocolo_colaborador")
        )

    def filtrar_concluidos(
        self: "Livro01ProtocoloQuerySet",
    ) -> "Livro01ProtocoloQuerySet":
        """Apenas os protocolos que estão com status de concluído."""
        # return self.filter(status_id=models.StatusProtocolo.get_id_status_concluido)
        logger.debug("Filtrando protocolos concluídos.")
        from apps.home.models import models_home

        return self.filter(status__descricao=models_home.StatusProtocolo.REGISTRADO)

    def filtrar_cancelados(
        self: "Livro01ProtocoloQuerySet",
    ) -> "Livro01ProtocoloQuerySet":
        from apps.home.models import models_home

        """Apenas os protocolos que estão com status de cancelado."""
        logger.debug("Filtrando protocolos cancelados.")
        return self.filter(status__descricao=models_home.StatusProtocolo.CANCELADO)

    def filtrar_concluidos_e_cancelados(
        self: "Livro01ProtocoloQuerySet",
    ) -> "Livro01ProtocoloQuerySet":
        """Apenas os protocolos que estão com status de REGISTRADO OU CANCELADO."""
        from apps.home.models import models_home

        return self.filter(
            status__descricao__in=[
                models_home.StatusProtocolo.REGISTRADO,
                models_home.StatusProtocolo.CANCELADO,
            ],
        )

    def filtrar_em_andamento(
        self: "Livro01ProtocoloQuerySet",
    ) -> "Livro01ProtocoloQuerySet":
        from apps.home.models import models_home

        """Mantem no queryset os protocolos que NÃO estão com o status cancelado, concluído, ou em exigencia."""
        return self.exclude(
            status_descricao__in=[
                models_home.StatusProtocolo.REGISTRADO,
                models_home.StatusProtocolo.CANCELADO,
                models_home.StatusProtocolo.EXIGENCIA,
            ],
        )

    def filtrar_em_exigencia(
        self: "Livro01ProtocoloQuerySet",
    ) -> "Livro01ProtocoloQuerySet":
        from apps.home.models import models_home

        """Apenas os protocolos que estão com status de exigência."""
        return self.filter(status__descricao=models_home.StatusProtocolo.EXIGENCIA)

    def filtrar_em_exigencia_positiva(
        self: "Livro01ProtocoloQuerySet",
    ) -> "Livro01ProtocoloQuerySet":
        from apps.home.models import models_home

        # Apenas os protocolos que estão com status de exigência positiva
        return self.filter(status__descricao=models_home.StatusProtocolo.EXIGENCIA)

    def filtrar_por_periodo(self: "Livro01ProtocoloQuerySet", start_date, end_date):
        """Apenas os protocolos que foram protocolados no período fornecido."""
        logger.debug(
            f"Filtrando protocolos protocolados no período de {start_date} a {end_date}.",
        )
        return self.filter(data_protocolo__range=[start_date, end_date])

    def filtrar_por_data(
        self: "Livro01ProtocoloQuerySet",
        start_date,
        end_date,
    ) -> "Livro01ProtocoloQuerySet":
        return (
            self.filter(
                data_protocolo__range=[start_date, end_date],
            ).ordenar_por_numero()
            or self.none()
        )

    def filtrar_por_digitalizar(
        self: "Livro01ProtocoloQuerySet",
    ) -> "Livro01ProtocoloQuerySet":
        return self.filter(fases_protocolo__grupo_digitalizar=SIM)

    def filtrar_pendentes_de_digitalizacao(
        self: "Livro01ProtocoloQuerySet",
    ) -> "Livro01ProtocoloQuerySet":
        """Apenas os protocolos que estão pendentes de digitalização."""
        logger.debug("Filtrando protocolos pendentes de digitalização.")
        from apps.home.models import models_home

        protocolos_ids = (
            models_home.Livro01Andamento.objects.get_queryset()
            .filter(
                tipo_andamento__grupo_digitalizar=SIM,
            )
            .values_list("protocolo", flat=True)
        )

        # Protocolos - A PARTIR DE UM PONTO
        protocolos = self.filter(
            numero_protocolo__gt=models_home.Configuracao.obter(
                "PRIMEIRO_PROTOCOLO_DIGITALIZACAO",
                0,
            ),
        )

        # Filtrar protocolos que não estão em andamentos
        protocolos_exclusivos = protocolos.exclude(pk__in=protocolos_ids)

        # Lista dos valores de protocolo dos protocolos exclusivos
        protocolos_ids_exclusivos = [
            protocolo.pk for protocolo in protocolos_exclusivos
        ]

        # GERANDO NUMEROS INTEIROS
        return self.filtrar_por_ids(protocolos_ids_exclusivos).ordenar_por_numero()

    def filtrar_em_aberto(
        self: "Livro01ProtocoloQuerySet",
    ) -> "Livro01ProtocoloQuerySet":
        """Apenas os protocolos que não estão finalizados."""
        return self.filtrar_nao_finalizados()

    def filtrar_nao_finalizados(
        self: "Livro01ProtocoloQuerySet",
    ) -> "Livro01ProtocoloQuerySet":
        """Apenas os protocolos que não estão finalizados."""
        logger.debug("Filtrando protocolos não finalizados.")

        return self.filter(data_finalizado__isnull=True)

    def filtrar_por_distribuidos_em_periodo(
        self: "Livro01ProtocoloQuerySet",
        start_date: date,
        end_date: date,
    ) -> "Livro01ProtocoloQuerySet":
        """Apenas os protocolos distribuídos no período fornecido."""
        logger.debug(
            f"Filtrando protocolos distribuídos no período de {start_date} a {end_date}.",
        )

        return self.filter(data_distribuicao__range=[start_date, end_date])

    def filtrar_por_colaborador(
        self: "Livro01ProtocoloQuerySet",
        colaborador: "Colaborador",
    ) -> "Livro01ProtocoloQuerySet":
        """Apenas os protocolos que estão atribuídos ao colaborador informado com base no último andamento."""
        logger.debug(f"Filtrando protocolos pelo colaborador {colaborador}.")
        from apps.home.models import models_home

        # Obter o ID máximo dos protocolos onde o colaborador é o destinatário
        subquery = (
            models_home.Livro01Andamento.objects.filter(protocolo=OuterRef("pk"))
            .values("protocolo")
            .annotate(max_id=Max("id"))
            .values("max_id")
        )

        # Filtrar diretamente utilizando a subquery
        return self.filter(
            andamentos_do_protocolo__id__in=subquery,
            andamentos_do_protocolo__colaborador_destino=colaborador,
        )

    def _anotar_data_reentrada(
        self: "Livro01ProtocoloQuerySet",
    ) -> "Livro01ProtocoloQuerySet":
        """Anota a data de reentrada de cada protocolo com base no último andamento de reentrada."""
        protocolo_anotado = self.annotate(
            data_reentrada=Max(
                "andamentos_do_protocolo__data",
                filter=Q(andamentos_do_protocolo__tipo_andamento__servico="Reentrada"),
            ),
        )
        for protocolo in protocolo_anotado:
            logger.debug(
                f"Protocolo {protocolo.numero_protocolo}",
            )
            for andamento in protocolo.andamentos_do_protocolo.all():
                logger.debug(
                    f"Protocolo {protocolo.numero_protocolo} - Andamento: {andamento}",
                )
            logger.debug(
                f"Protocolo {protocolo.numero_protocolo} - Data de reentrada: {protocolo.data_reentrada}",
            )
        return protocolo_anotado or self.none()

    def _anotar_ultimo_colaborador(
        self: "Livro01ProtocoloQuerySet",
    ) -> "Livro01ProtocoloQuerySet":
        """Anota o colaborador do último andamento de cada protocolo no queryset."""
        from apps.home.models import models_home

        subquery_colaborador = (
            models_home.Livro01Andamento.objects.filter(protocolo=OuterRef("pk"))
            .order_by("-id")
            .values("colaborador_destino")[:1]
        )

        return self.annotate(ultimo_colaborador_destino=Subquery(subquery_colaborador))

    def filtrar_por_data_reentrada(
        self: "Livro01ProtocoloQuerySet",
        data,
    ) -> "Livro01ProtocoloQuerySet":
        """Filtra os protocolos pela data de reentrada."""
        return self._anotar_data_reentrada().filter(data_reentrada=data)

    def filtrar_com_reentrada(
        self: "Livro01ProtocoloQuerySet",
    ) -> "Livro01ProtocoloQuerySet":
        """Apenas os protocolos que possuem data de reentrada."""
        logger.debug("Filtrando protocolos com reentrada.")
        return self._anotar_data_reentrada().filter(data_reentrada__isnull=False)

    def filtrar_sem_reentrada(
        self: "Livro01ProtocoloQuerySet",
    ) -> "Livro01ProtocoloQuerySet":
        """Apenas os protocolos que não possuem data de reentrada."""
        return self._anotar_data_reentrada().filter(data_reentrada__isnull=True)

    def filtrar_sem_colaborador(
        self: "Livro01ProtocoloQuerySet",
    ) -> "Livro01ProtocoloQuerySet":
        """Apenas os protocolos que não possuem colaborador_destino."""
        from apps.home.models import models_home

        subquery_colaborador_destino = (
            models_home.Livro01Andamento.objects.filter(protocolo=OuterRef("pk"))
            .order_by("-data")
            .values("colaborador_destino__pk")[:1]
        )

        # Filtra os protocolos onde o último colaborador_destino é nulo (não atribuído)
        return (
            self.filter(data_finalizado__isnull=True)
            .annotate(
                ultimo_colaborador_destino_pk=Subquery(subquery_colaborador_destino),
            )
            .filter(
                Q(ultimo_colaborador_destino_pk__isnull=True)
                | Q(ultimo_colaborador_destino_pk=""),
            )
        )

    def anotar_peso_total(self) -> "Livro01ProtocoloQuerySet":
        """Atribui o peso total de cada protocolo no queryset baseado nos pesos dos títulos associados."""
        return self.filter().annotate(
            peso_total=Sum("pedido__itens_do_pedido__ato__peso_titulo"),
        )

    def filtrar_distribuir_por_periodo(
        self,
        start_date: date,
        end_date: date,
    ) -> "Livro01ProtocoloQuerySet":
        """Apenas os protocolos a distribuir no período fornecido."""
        if not start_date or not end_date:
            logger.warning("ERRO: Data de início ou fim não informada.")
            return self.none()
        logger.info(
            f"Obtendo protocolos a distribuir por período de {start_date} a {end_date}",
        )
        return (
            self.filter(
                data_protocolo__range=[start_date, end_date],
                data_distribuicao__isnull=True,
            )
            or self.none()
        ).ordenar_por_numero()

    def filtrar_distribuidos_por_periodo(
        self,
        start_date: date,
        end_date: date,
    ) -> "Livro01ProtocoloQuerySet":
        if not start_date or not end_date:
            logger.warning("ERRO: Data de início ou fim não informada.")
            return self.none()
        return (
            self.filter(
                data_distribuicao__range=[start_date, end_date],
            )
            or self.none()
        ).ordenar_por_numero()

    def filtrar_distribuidos_nos_ultimos_x_dias(
        self,
        dias: int,
    ) -> "Livro01ProtocoloQuerySet":
        """Apenas os protocolos distribuídos nos últimos x dias."""
        logger.debug(f"Filtrando protocolos distribuídos nos últimos {dias} dias.")
        data_inicio = timezone.now() - timedelta(days=dias)
        data_fim = timezone.now()
        return self.filter(data_distribuicao__range=(data_inicio, data_fim))

    def filtrar_distribuidos(self):
        """Apenas os protocolos com fases_protocolo_id prenchido."""
        return self.filter(fases_protocolo_id__isnull=False)

    def filtrar_por_numero(
        self: "Livro01ProtocoloQuerySet",
        numero_protocolo: int,
    ) -> "Livro01Protocolo":
        """Filtra os protocolos pelo número do protocolo que contem."""
        self.filter(numero_protocolo__icontains=numero_protocolo) or self.none()

    def ordernar_por_data_e_numero_protocolo(
        self: "Livro01ProtocoloQuerySet",
    ) -> "Livro01ProtocoloQuerySet":
        """Ordena os protocolos pela data de protocolo e pelo número do protocolo."""
        return self.filter().order_by("-data_protocolo", "-numero_protocolo")

    def filtrar_por_multiplas_listas(self, *protocolos) -> "Livro01ProtocoloQuerySet":
        """Filtra os protocolos com base em listas de IDs fornecidas e os organiza em um dicionário."""
        # Cria um conjunto de IDs únicos a partir de todas as listas fornecidas
        all_ids = {item for _, lista in protocolos for item in lista}

        # Filtra o queryset com base nos IDs e anota a data truncada do protocolo,
        # em seguida ordena pelo 'truncated_date' e pelo 'numero_protocolo' decrescente
        queryset = self.filtrar_por_ids(all_ids).ordernar_por_data_e_numero_protocolo()

        # Cria um dicionário onde cada chave é um protocolo e o valor é o evento associado
        # eventos_agrupados = {evento.protocolo: evento for evento in queryset}
        eventos_agrupados = {evento.numero_protocolo: evento for evento in queryset}

        # Inicializa o dicionário que armazenará os eventos filtrados por cada lista
        eventos = {}
        # Itera sobre cada nome e lista dentro dos protocolos informados
        for nome, lista in protocolos:
            lista_set = set(
                lista,
            )  # Converte a lista em um conjunto para otimizar a busca
            # Compila uma nova lista de eventos com as chaves presentes no dicionário de eventos agrupados
            eventos[nome] = [
                eventos_agrupados[chave]
                for chave in lista_set
                if chave in eventos_agrupados
            ]

        # Retorna o dicionário de eventos organizados por nome
        return eventos

    def filtrar_sem_reentrada_por_colaborador(
        self,
        colaborador_id,
    ) -> "Livro01ProtocoloQuerySet":
        """Apenas os protocolos que não possuem reentrada e estão atribuídos ao colaborador informado."""
        protocolos = (
            self.filtrar_por_colaborador(colaborador_id)
            .filtrar_nao_finalizados()
            .ordenar_por_numero()
        )

        return [
            protocolo
            for protocolo in protocolos
            if protocolo.data_reentrada is not None
        ]

    def filtrar_protocolos_distribuidos_por_colaborador(
        self,
        colaborador_id,
    ) -> "Livro01ProtocoloQuerySet":
        """Apenas os protocolos que estão distribuídos para o colaborador informado."""
        return (
            self.filtrar_por_colaborador(colaborador_id)
            .filtrar_nao_finalizados()
            .ordenar_por_numero()
        )

    def filtrar_distribuidos_para_colaborador_no_periodo(
        self,
        colaborador_id: int,
        start_date: date,
        end_date: date,
    ) -> "Livro01Protocolo":
        """Filtra os protocolos distribuídos para o colaborador informado no período fornecido."""
        return (
            self.filtrar_por_colaborador(colaborador_id)
            .filtrar_distribuidos_por_periodo(start_date, end_date)
            .ordenar_por_numero()
        )

    def filtrar_com_reentrada_por_colaborador(
        self,
        colaborador_id,
    ) -> "Livro01Protocolo":
        """Apenas os protocolos que possuem reentrada e estão atribuídos ao colaborador informado."""
        return (
            self.filtrar_por_colaborador(colaborador_id)
            .filtrar_nao_finalizados()
            .filtrar_com_reentrada()
            .ordernar_por_data_e_numero_protocolo()
        )


class ProtocoloEmFaseManager(Manager):
    def get_fases_por_protocolo_id(self, protocolo_id):
        """Retorna as fases de um protocolo específico."""
        return self.filter(id=protocolo_id).order_by("ordem")

    def deletar_por_pedido_id(self, pedido_id) -> None:
        """Deleta os objetos ProtocoloEmFase baseados no pedido_id fornecido."""
        from apps.home.models import models_home

        # Primeiro, obtenha os IDs de Protocolos relacionados à ID do pedido fornecida
        protocolos_ids = models_home.Livro01Protocolo.objects.filter(
            pedido_id=pedido_id,
        ).values_list("id", flat=True)

        # Em seguida, use esses IDs para filtrar e deletar os objetos ProtocoloEmFase correspondentes
        self.get_queryset().filter(id__in=protocolos_ids).delete()


class AndamentosManager(Manager):
    def get_queryset(self) -> QuerySet["Livro01Andamento"]:
        """Retorna o queryset padrão com os andamentos e os tipos de andamento relacionados."""
        return super().get_queryset()

    def filtrar_por_data_andamento(self, start_date, end_date):
        """Filtra registros pela data de andamento."""
        logger.debug("Filtrando registros pela data de andamento.")
        return self.filter(data__range=[start_date, end_date])

    def filtrar_por_data_andamento_registrado(self, start_date, end_date):
        """Filtra registros pela data de andamento e pelo grupo registrado."""
        logger.debug("Filtrando registros pelo tipo de andamento registrado.")

        return self.filter(
            data__range=[start_date, end_date],
            tipo_andamento__grupo_registrado=SIM,
        ).select_related("tipo_andamento")

    def filtrar_por_protocolo(
        self,
        protocolo: "Livro01Protocolo",
    ) -> QuerySet["Livro01Andamento"]:
        """Filtra registros pelo protocolo, ordenando por data truncada e data completa."""
        logger.debug(f"Filtrando registros pelo protocolo {protocolo}.")
        return (
            self.filter(protocolo=protocolo)
            .annotate(truncated_date=TruncDate("data"))
            .order_by("truncated_date", "data")
        ).select_related("tipo_andamento")

    def filtrar_registrados(self):
        """Filtra registros pelo primeiro tipo de andamento do grupo registrado."""
        logger.debug(
            "Filtrando registros pelo primeiro tipo de andamento do grupo registrado.",
        )

        from apps.home.models import models_home

        registrado = models_home.TipoAndamento.grupos.registrado().first()
        return self.filter(tipo_andamento=registrado).select_related("tipo_andamento")

    def agrupar_por_status(self, protocolos: list):
        logger.debug("Agrupando protocolos por status.")
        from apps.home.models import models_home

        # Obtendo dinamicamente as colunas que começam com "grupo_"
        grupo_columns = [
            field.name
            for field in models_home.TipoAndamento._meta.fields
            if field.name.startswith("grupo_")
        ]

        # Criando o dicionário dinamicamente com os IDs dos serviços por status.
        servico_status_ids = {
            column_name.replace(
                "grupo_",
                "",
            ): models_home.TipoAndamento.objects.get_ids_by_column_value(column_name)
            for column_name in grupo_columns
        }

        status = {status_nome: [] for status_nome in servico_status_ids}
        status.update(
            {f"colaborador_{status_nome}": [] for status_nome in servico_status_ids},
        )
        status.update(
            {f"data_andamento_{status_nome}": [] for status_nome in servico_status_ids},
        )
        status.update(
            {
                f"colaborador_destino_{status_nome}": []
                for status_nome in servico_status_ids
            },
        )

        # Realização de uma consulta única ao banco de dados, filtrando pelos protocolos recebidos e pelos IDs dos serviços.
        tipo_andamento_ids = functools.reduce(
            operator.iadd,
            [list(ids) for ids in servico_status_ids.values()],
            [],
        )
        queryset = (
            self.filter(
                protocolo_id__in=protocolos,
                tipo_andamento__in=tipo_andamento_ids,
            )
            .select_related("tipo_andamento")
            .values(
                "protocolo",
                "tipo_andamento",
                "colaborador_id",
                "data",
                "colaborador_destino_id",
            )
        )

        # Iteração sobre os resultados da consulta para agrupar os protocolos por status.
        for item in queryset:
            servico_id = item["tipo_andamento"]
            colaborador_destino_id = item["colaborador_destino_id"]

            # Validação do ID do colaborador destinatário antes de processar.
            if (
                colaborador_destino_id is not None
                and str(colaborador_destino_id).isdigit()
            ):
                for status_nome, ids in servico_status_ids.items():
                    if servico_id in ids:
                        # Adiciona os dados nos respectivos lugares do dicionário 'status'
                        status[status_nome].append(item["protocolo"])
                        status[f"colaborador_{status_nome}"].append(
                            int(item["colaborador_id"]),
                        )
                        status[f"data_andamento_{status_nome}"].append(item["data"])
                        status[f"colaborador_destino_{status_nome}"].append(
                            int(colaborador_destino_id),
                        )
                        break

        # Retorna o dicionário com os protocolos agrupados por status.
        return status

    def deletar_por_protocolo(self, protocolo) -> None:
        logger.debug(f"Deletando andamentos do Protocolo {protocolo}")
        # Filtra e deleta os objetos Andamentos baseados na protocolo_id
        self.get_queryset().filter(protocolo=protocolo).delete()

    def filtrar_andamento_data_registrado(self, protocolo_id):
        logger.debug(f"Buscando data do último andamento de protocolo {protocolo_id}")
        from apps.home.models import models_home

        servicos_registrados_id = (
            models_home.TipoAndamento.objects.get_ids_tipo_registrado()
        )

        return self.filter(
            Q(protocolo_id=protocolo_id)
            & Q(tipo_andamento__in=servicos_registrados_id),
        ).aggregate(
            maior_data=Max("data"),
        )["maior_data"]


class ExigenciasManager(Manager):
    def get_queryset(self) -> QuerySet["Livro01Andamento"]:
        logger.debug(" Obtendo queryset de exigências.")
        qs = super().get_queryset().select_related("tipo_andamento")
        return qs.filter(tipo_andamento__grupo_exigencia=SIM)

    def filtrar_por_protocolo(self, protocolo) -> QuerySet["Livro01Andamento"]:
        logger.debug(f" Filtrando exigências por protocolo {protocolo}")
        return self.get_queryset().filter(protocolo=protocolo).order_by("data")


class RegistradosManager(Manager):
    def get_queryset(self) -> QuerySet["Livro01Andamento"]:
        qs = super().get_queryset().select_related("tipo_andamento")
        return qs.filter(tipo_andamento__grupo_registrado=SIM)

    def filtrar_por_protocolo(self, protocolo) -> QuerySet["Livro01Andamento"]:
        return self.get_queryset().filter(protocolo=protocolo).order_by("data")


class TipoAndamentoGrupoManager(Manager):
    def registrado(self: "TipoAndamentoGrupoManager") -> QuerySet["TipoAndamento"]:
        return self.filter(grupo_registrado=SIM)

    def exigencia(self: "TipoAndamentoGrupoManager") -> QuerySet["TipoAndamento"]:
        return self.filter(grupo_exigencia=SIM)

    # TRAZER OS ITENS QUE ESTAO NO GRUPO DE REPROTOCOLAR
    def reprotocolar(self: "TipoAndamentoGrupoManager") -> QuerySet["TipoAndamento"]:
        return self.filter(grupo_reprotocolado=SIM)

    # TRAZER OS ITENS QUE ESTAO NO GRUPO DE RECEPCAO
    def get_recepcao(self: "TipoAndamentoGrupoManager") -> QuerySet["TipoAndamento"]:
        return self.filter(grupo_recepcao=SIM)


class TipoAndamentoManager(Manager):
    def get_ids_by_column_value(
        self,
        column_name: str,
        value: str = SIM,
    ) -> QuerySet[int]:
        return self.filter(**{column_name: value}).values_list("pk", flat=True)

    def registrar_andamento_protocolo_entregue(
        self: "TipoAndamentoManager",
    ) -> QuerySet["TipoAndamento"]:
        return self.filter(grupo_protocolo_entregue=SIM)

    def grupo_exigencia_s(self: "TipoAndamentoManager") -> QuerySet["TipoAndamento"]:
        return self.filter(grupo_exigencia=SIM)

    def get_ids_tipo_registrado(self: "TipoAndamentoManager") -> QuerySet[int]:
        return self.filter(grupo_registrado=SIM).values_list("pk", flat=True)

    def get_ids_de_tipo_cancelado(self: "TipoAndamentoManager") -> QuerySet[int]:
        return self.filter(grupo_cancelado=SIM).values_list("pk", flat=True)

    def get_ids_de_tipo_exigencia(self: "TipoAndamentoManager") -> QuerySet[int]:
        return self.filter(grupo_exigencia=SIM).values_list("pk", flat=True)

    def filtrar_por_tipo_em_registro(self: "TipoAndamentoManager") -> QuerySet[int]:
        return self.filter(grupo_em_registro=SIM).values_list("pk", flat=True)

    def get_ids_de_tipo_subjudice(self: "TipoAndamentoManager") -> QuerySet[int]:
        return self.filter(grupo_subjudice=SIM).values_list("pk", flat=True)

    def get_ids_de_tipo_pronto_registrar(self: "TipoAndamentoManager") -> QuerySet[int]:
        qs = self.filter(grupo_pronto_registrar=SIM).values_list("pk", flat=True)
        try:
            # Tenta converter cada elemento da lista para inteiro
            return [int(item) for item in qs]
        except ValueError:
            # Retorna uma lista vazia se houver um erro na conversão
            return []

    def get_ids_de_tipo_reentrada(self: "TipoAndamentoManager") -> QuerySet[int]:
        return self.filter(grupo_reentrada=SIM).values_list("pk", flat=True)

    def get_ids_de_tipo_reentrada_pagamento(
        self: "TipoAndamentoManager",
    ) -> QuerySet[int]:
        return self.filter(grupo_reentrada_pagamento=SIM).values_list("pk", flat=True)

    def get_ids_de_tipo_finalizado(self: "TipoAndamentoManager") -> QuerySet[int]:
        return self.filter(grupo_finalizado=SIM).values_list("pk", flat=True)

    def get_ids_de_tipo_exigencia_positiva(
        self: "TipoAndamentoManager",
    ) -> QuerySet[int]:
        return self.filter(grupo_exigencia_positiva=SIM).values_list("pk", flat=True)

    def get_ids_de_tipo_digitalizar(self: "TipoAndamentoManager") -> QuerySet[int]:
        return self.filter(grupo_digitalizar=SIM).values_list("pk", flat=True)

    def get_ids_de_tipo_distribuicao(self: "TipoAndamentoManager") -> QuerySet[int]:
        return self.filter(grupo_distribuicao=SIM).values_list("pk", flat=True)

    def eh_registrados(self: "TipoAndamentoManager", pk: int) -> bool:
        """Verifica se o tipo de andamento é do grupo de registrados."""
        return self.filter(grupo_registrado=SIM, pk=pk).exists()

    def eh_cancelados(self: "TipoAndamentoManager", pk: int) -> bool:
        return self.filter(grupo_cancelado=SIM, pk=pk).exists()

    def eh_exigencia(self: "TipoAndamentoManager", pk: int) -> bool:
        return self.filter(grupo_exigencia=SIM, pk=pk).exists()

    def eh_registro(self: "TipoAndamentoManager", pk: int) -> bool:
        return self.filter(grupo_em_registro=SIM, pk=pk).exists()

    def eh_subjudice(self: "TipoAndamentoManager", pk: int) -> bool:
        return self.filter(grupo_subjudice=SIM, pk=pk).exists()

    def eh_recebido(self: "TipoAndamentoManager", pk: int) -> bool:
        return self.filter(grupo_servico_recebido=SIM, pk=pk).exists()

    def eh_pronto_registrar(self: "TipoAndamentoManager", pk: int) -> bool:
        return self.filter(grupo_pronto_registrar=SIM, pk=pk).exists()

    def eh_reentrada(self: "TipoAndamentoManager", pk: int) -> bool:
        return self.filter(grupo_reentrada=SIM, pk=pk).exists()

    def eh_reentrada_pagamento(self: "TipoAndamentoManager", pk: int) -> bool:
        return self.filter(grupo_reentrada_pagamento=SIM, pk=pk).exists()

    def eh_finalizado(self: "TipoAndamentoManager", pk: int) -> bool:
        return self.filter(grupo_finalizado=SIM, pk=pk).exists()

    def eh_exigencia_positiva(self: "TipoAndamentoManager", pk: int) -> bool:
        return self.filter(grupo_exigencia_positiva=SIM, pk=pk).exists()

    def eh_digitalizar(self: "TipoAndamentoManager", pk: int) -> bool:
        return self.filter(grupo_digitalizar=SIM, pk=pk).exists()

    def eh_distribuicao(self: "TipoAndamentoManager", pk: int) -> bool:
        return self.filter(grupo_distribuicao=SIM, pk=pk).exists()

    def eh_distribuicao_id(self: "TipoAndamentoManager", pk: int) -> bool:
        tipo_andamento_distribuido = self.filter(grupo_distribuicao=SIM, pk=pk).first()
        return tipo_andamento_distribuido.pk if tipo_andamento_distribuido else None

    def eh_atualizar_status_protocolo(self: "TipoAndamentoManager", pk: int) -> bool:
        return self.filter(atualizar_status_protocolo=SIM, pk=pk).exists()

    def importar_do_fb(self: "TipoAndamentoManager") -> None:
        # from constance import config

        # if not config.FIREBIRD_ENABLED:
        #     logger.error("Firebird não habilitado!")
        #     return None

        query = """  SELECT CHAVE_SERVICOS_ANDAMENTOS, SERVICO as SERVICO
                     FROM SERVICOS_ANDAMENTOS """

        with FbConnection() as db:
            servicos = db.execute_query(query)

        tipos_andamentos = []

        for servico in servicos:
            descricao_servico = servico["SERVICO"]
            grupo_cancelado = NAO
            grupo_registrado = NAO
            grupo_exigencia = NAO
            grupo_cancelado_registrado = NAO
            grupo_subjudice = NAO
            atualizar_status_protocolo = NAO
            grupo_reentrada = NAO
            grupo_finalizado = NAO
            grupo_exigencia_positiva = NAO
            grupo_em_registro = NAO
            grupo_pronto_registrar = NAO
            grupo_distribuicao = NAO
            grupo_digitalizar = NAO
            grupo_ultimo_andamento = NAO

            try:
                if "SUB JUDICE" in upper_case(servico["SERVICO"]):
                    grupo_exigencia = SIM
                    atualizar_status_protocolo = SIM
            except Exception:
                logger.exception("Erro ao verificar se é sub judice")

            try:
                if "REENTRADA" in upper_case(servico["SERVICO"]):
                    grupo_reentrada = SIM
                    atualizar_status_protocolo = SIM
            except Exception:
                logger.exception("Erro ao verificar se é reentrada")

            try:
                if (
                    "PAGAMENTO do T"
                    in upper_case(servico.get("SERVICO", "TITULO APTO"))
                    in upper_case(servico["SERVICO"])
                ):
                    grupo_exigencia_positiva = SIM
                    atualizar_status_protocolo = SIM
            except Exception:
                logger.exception("Erro ao verificar se é exigência positiva")

            try:
                if "EXIG" in upper_case(servico["SERVICO"]):
                    grupo_exigencia = SIM
                    atualizar_status_protocolo = SIM
            except Exception:
                logger.exception("Erro ao verificar se é exigência")

            try:
                if "DISTRIBUIDO" in upper_case(servico["SERVICO"]):
                    grupo_distribuicao = SIM
                    atualizar_status_protocolo = SIM
            except Exception:
                logger.exception("Erro ao verificar se é distribuição")

            try:
                if "DIGITALIZ" in upper_case(servico["SERVICO"]):
                    grupo_digitalizar = SIM
                    atualizar_status_protocolo = SIM
            except Exception:
                logger.exception("Erro ao verificar se é digitalização")

            try:
                if "DEVOLU" in upper_case(
                    servico["SERVICO"],
                ) or "TITULO INAPTO" in upper_case(
                    servico["SERVICO"],
                ):
                    grupo_finalizado = SIM
                    grupo_ultimo_andamento = SIM
                    atualizar_status_protocolo = SIM
            except Exception:
                logger.exception("Erro ao verificar se é finalizado")

            try:
                if "CONFERENCIA" in upper_case(servico["SERVICO"]):
                    grupo_pronto_registrar = SIM
                    atualizar_status_protocolo = SIM
            except Exception:
                logger.exception("Erro ao verificar se é pronto para registrar")

            try:
                if "ADCIONAL DE PGTO" in upper_case(servico["SERVICO"]):
                    grupo_reentrada = SIM
                    atualizar_status_protocolo = SIM
            except Exception:
                logger.exception("Erro ao verificar se é reentrada")

            try:
                if "CONCLUSO" in upper_case(servico["SERVICO"]):
                    grupo_em_registro = SIM
                    atualizar_status_protocolo = SIM
            except Exception:
                logger.exception("Erro ao verificar se é em registro")

            try:
                # gRUPOS dE cANCELADOS
                if "CANCELADO" in upper_case(
                    servico["SERVICO"],
                ) or "CANC." in upper_case(
                    servico["SERVICO"],
                ):
                    grupo_cancelado = SIM
                    grupo_cancelado_registrado = SIM
                    atualizar_status_protocolo = SIM
            except Exception:
                logger.exception("Erro ao verificar se é cancelado")

            try:
                # gRUPOS dE cANCELADOS
                if "REGISTRADO" in upper_case(
                    servico["SERVICO"],
                ) or "REGISTRO" in upper_case(
                    servico["SERVICO"],
                ):
                    grupo_registrado = SIM
                    grupo_cancelado_registrado = SIM
                    atualizar_status_protocolo = SIM
            except Exception:
                logger.exception("Erro ao verificar se é registrado")

            obj, created = self.update_or_create(
                pk=servico["CHAVE_SERVICOS_ANDAMENTOS"],
                defaults={
                    "servico": servico["SERVICO"],
                    "descricao_servico": descricao_servico,
                    "grupo_cancelado": grupo_cancelado,
                    "grupo_registrado": grupo_registrado,
                    "grupo_exigencia": grupo_exigencia,
                    "grupo_cancelado_registrado": grupo_cancelado_registrado,
                    "grupo_subjudice": grupo_subjudice,
                    "atualizar_status_protocolo": atualizar_status_protocolo,
                    "grupo_reentrada": grupo_reentrada,
                    "grupo_finalizado": grupo_finalizado,
                    "grupo_exigencia_positiva": grupo_exigencia_positiva,
                    "grupo_em_registro": grupo_em_registro,
                    "grupo_pronto_registrar": grupo_pronto_registrar,
                    "grupo_distribuicao": grupo_distribuicao,
                    "grupo_digitalizar": grupo_digitalizar,
                    "grupo_ultimo_andamento": grupo_ultimo_andamento,
                },
            )

            tipos_andamentos.append(obj)

        logger.info(
            f"SERVICOS_ANDAMENTOS: {len(tipos_andamentos)} serviços gravados .",
        )

        return tipos_andamentos or None

    def criar_defaults(self):
        # AGENDA ITENS
        tipo_de_andamentos = [
            {"tipo_andamento_id": 6, "fase_agenda_id": 60},
            {"tipo_andamento_id": 6, "fase_agenda_id": 80},
            {"tipo_andamento_id": 26, "fase_agenda_id": 100},
            {"tipo_andamento_id": 26, "fase_agenda_id": 120},
            {"tipo_andamento_id": 23, "fase_agenda_id": 20},
            {"tipo_andamento_id": 23, "fase_agenda_id": 40},
            {"tipo_andamento_id": 125, "fase_agenda_id": 1},
            {"tipo_andamento_id": 23, "fase_agenda_id": 1},
            {"tipo_andamento_id": 6, "fase_agenda_id": 1},
            {"tipo_andamento_id": 126, "fase_agenda_id": 20},
            {"tipo_andamento_id": 126, "fase_agenda_id": 40},
            {"tipo_andamento_id": 9, "fase_agenda_id": 60},
            {"tipo_andamento_id": 9, "fase_agenda_id": 80},
            {"tipo_andamento_id": 9, "fase_agenda_id": 1},
            {"tipo_andamento_id": 6, "fase_agenda_id": 100},
            {"tipo_andamento_id": 6, "fase_agenda_id": 120},
            {"tipo_andamento_id": 9, "fase_agenda_id": 40},
            {"tipo_andamento_id": 9, "fase_agenda_id": 100},
            {"tipo_andamento_id": 9, "fase_agenda_id": 120},
            {"tipo_andamento_id": 10, "fase_agenda_id": 60},
            {"tipo_andamento_id": 10, "fase_agenda_id": 80},
            {"tipo_andamento_id": 10, "fase_agenda_id": 1},
            {"tipo_andamento_id": 10, "fase_agenda_id": 40},
            {"tipo_andamento_id": 10, "fase_agenda_id": 100},
            {"tipo_andamento_id": 10, "fase_agenda_id": 120},
            {"tipo_andamento_id": 11, "fase_agenda_id": 60},
            {"tipo_andamento_id": 11, "fase_agenda_id": 80},
            {"tipo_andamento_id": 11, "fase_agenda_id": 1},
            {"tipo_andamento_id": 11, "fase_agenda_id": 40},
            {"tipo_andamento_id": 11, "fase_agenda_id": 100},
            {"tipo_andamento_id": 11, "fase_agenda_id": 120},
            {"tipo_andamento_id": 1, "fase_agenda_id": 120},
            {"tipo_andamento_id": 11, "fase_agenda_id": 120},
            {"tipo_andamento_id": 69, "fase_agenda_id": 60},
            {"tipo_andamento_id": 69, "fase_agenda_id": 80},
            {"tipo_andamento_id": 69, "fase_agenda_id": 1},
            {"tipo_andamento_id": 69, "fase_agenda_id": 40},
            {"tipo_andamento_id": 69, "fase_agenda_id": 100},
            {"tipo_andamento_id": 69, "fase_agenda_id": 120},
        ]
        with transaction.atomic():
            for item in tipo_de_andamentos:
                try:
                    obj, created = self.get_or_create(pk=item["tipo_andamento_id"])
                    from apps.home.models import models_home

                    models_home.FaseAgendaItemAndamento.objects.update_or_create(
                        tipo_andamento_id=obj.pk,
                        fase_agenda_id=item["fase_agenda_id"],
                        defaults=item,
                    )
                except Exception:
                    msg = f"Erro ao criar item de andamento {item['tipo_andamento_id']}"
                    logger.exception(msg)
                    logger.exception(msg)

        # # Mensagem de sucesso
        logger.info("Tabela Fase Agenda Itens Andamento adicionada!")

    def filtrar_por_ativos(self):
        return self.filter(ativo=True).order_by("servico")


class AtosManager(Manager):
    def get_queryset(self):
        return super().get_queryset().filter(exibir=SIM)

    def get_dias_uteis(self, atos_id, data, opcao=0):
        atos_dias_uteis_reentrada = 0

        atos_dias_uteis = max(self.filter(id__in=atos_id).values_list("dias_uteis"))

        # ACRESCENTAR DATA DA REENTRADA
        if opcao == 1:
            atos_dias_uteis_reentrada = max(
                self.filter(id__in=atos_id).values_list("dias_uteis_reentrada"),
            )
            atos_dias_uteis_reentrada = str(str(atos_dias_uteis))

        # Dias de cada ato
        atos_dias_uteis = str(str(atos_dias_uteis))
        atos_dias_uteis = atos_dias_uteis + atos_dias_uteis_reentrada

        # Atualizar a data prevista com base em dias uteis
        # Converter de string para date abaixo
        data_prevista = get_data_util_em_x_dias(data, int(atos_dias_uteis))
        data_validade = get_data_util_em_x_dias(data, int(atos_dias_uteis) + 1)

        data_prevista_date = converter_string_para_data(
            data_prevista,
            settings.DATE_FORMAT_STR,
            0,
        )[0].date()

        # Calcula a diferença entre as datas
        dias_restante = relativedelta(data_prevista_date, timezone.now()).days

        return [atos_dias_uteis, str(data_prevista), str(data_validade), dias_restante]

    def get_atos_por_id(self, atos_id):
        return self.filter(id__in=atos_id).values_list("descricao", flat=True)

    def criar_do_fb(self, ato_fb) -> "AtoPratica":
        if not ato_fb:
            return None

        ato_id = int(ato_fb["CHAVE_ATOS"])
        # ato_id = int(ato_fb[0]["CHAVE_ATOS"])
        ato_id = ato_fb["TIPOATO"]

        logger.info(f"ATO: Criando ato {ato_id} com dados")

        try:
            return ato_id

            # pass
            # print(tipo_ato)

            # obj, created = self.get_or_create(
            # obj, created = self.update_or_create(
            #     id=ato_id,
            #     defaults={
            #         "tipo_ato": tipo_ato,
            #         "dias_uteis_reentrada": 0,
            #         "peso_titulo": 0,
            #     },
            # )

            # if not created:
            #     obj.tipo_ato = tipo_ato
            #     obj.dias_uteis_reentrada = 0
            #     obj.peso_titulo = 0
            #     obj.save()

            # return obj
        except ObjectDoesNotExist:
            logger.exception("ERRO ATO 1")
            return self.create(
                id=ato_id,
                tipo_ato=ato_fb["TIPOATO"],
                dias_uteis_reentrada=0,
                peso_titulo=0,
            )

        except IntegrityError:
            logger.exception("ERRO ATO 2")
            logger.exception(
                f"Erro de integridade ao criar/atualizar ato {ato_id} a partir",
            )

        except Exception:
            logger.exception("ERRO ATO 3")
            logger.exception(
                f"Erro inesperado ao criar/atualizar ato {ato_id} a partir:",
            )

    def get_atos_doi(self):
        return self.filter(codigo_doi_id__gte=0).values_list("id", flat=True)

    def get_nome_atos_doi(self):
        return self.filter(codigo_doi_id__gte=0).order_by("tipo_ato")

    def importar_do_fb(self):
        with FbConnection() as db:
            query = " SELECT CHAVE_ATOS, TIPOATO FROM ATOS "
            atos_fb = db.execute_query(query)
        # print("Iniciar criar ATOS")
        # print(atos_fb)

        for ato_fb in atos_fb:
            # print("Nome do ato", ato_fb["CHAVE_ATOS"])
            ato_id = int(ato_fb["CHAVE_ATOS"])
            obj = self.filter(pk=ato_id).exists()
            # obj = self.get(pk=ato_id)

            # print(obj)
            # import time

            if obj:
                logger.info(f"Ato já existe {ato_id!s}")
                # obj.tipo_ato = ato_fb["TIPOATO"]
                # obj.save()

                obj, created = self.update_or_create(
                    pk=ato_id,
                    defaults={"tipo_ato": ato_fb["TIPOATO"]},
                )
            else:
                logger.info(f"Ato não existe {ato_id}")

                try:
                    # obj = self.create(
                    obj, created = self.update_or_create(
                        pk=ato_id,
                        defaults={"tipo_ato": ato_fb["TIPOATO"]},
                    )

                    # obj = self.update_or_create(
                    #     pk=ato_id,
                    #     tipo_ato=ato_fb["TIPOATO"],
                    # )

                except Exception as e:
                    logger.exception(f"Erro ao criar/atualizar ato a partir: {e}")
        try:
            self.update_or_create(tipo_ato=PROVISORIO, defaults={"ato_default": SIM})
        except Exception:
            logger.exception("Erro ao criar ato provisório: ")


class CheckListRealizadoManager(Manager):
    def deletar_por_estado_civil(
        self: "CheckListRealizadoManager",
        pedido_item_id: int,
        estado_civil: str,
    ) -> None:
        logger.info(f"Excluindo CheckListRealizado por estado_civil: {estado_civil}")
        self.filter(pedido_item_id=pedido_item_id, estado_civil=estado_civil).delete()

    def deletar_por_pedido_id(
        self: "CheckListRealizadoManager",
        pedido_id: int,
    ) -> None:
        from apps.home.models import models_home

        excluir = self.filter(
            pedido_item_id__in=models_home.PedidoItem.objects.filter(
                pedido_id=pedido_id,
            ).values_list("pk", flat=True),
        )
        if excluir.exists():
            logger.info(f"Excluindo CheckListRealizado por pedido_id: {pedido_id}")
            excluir.delete()

    def deletar_por_pedido_item_id(
        self: "CheckListRealizadoManager",
        pedido_item_id: int,
    ) -> None:
        logger.info(
            f"Excluindo CheckListRealizado por pedido_item_id: {pedido_item_id}",
        )
        self.filter(pedido_item_id=pedido_item_id).delete()

    def salvar(
        self: "CheckListRealizadoManager",
        estado_civil_id: int,
        item_id: int,
        pergunta_id: int,
        pessoa_id: int,
        funcionario_id: int,
        pedido_item_id: int,
        resposta: str,
        resposta_correta: str,
        tabela_origem_id: int,
        nome_tabela_origem: str,
        coluna_tabela_origem: str,
        ordem: int,
    ) -> None:
        try:
            return self.create(
                estado_civil=estado_civil_id,
                item=item_id,
                perguntas_id=pergunta_id,
                pessoa_id=pessoa_id,
                colaborador=funcionario_id,
                pedido_item_id=pedido_item_id,
                resposta=resposta,
                resposta_correta=resposta_correta,
                tabela_origem_id=tabela_origem_id,
                nome_tabela_origem=nome_tabela_origem,
                coluna_tabela_origem=coluna_tabela_origem,
                ordem=ordem,
            )

        except Exception:
            logger.exception("ERRO")
            raise

    def gravar(
        self,
        estado_civil_id: int,
        item_id: int,
        pergunta_id: int,
        pessoa_id: int,
        funcionario_id: int,
        pedido_item_id: int,
        resposta: str = "",
        resposta_enviada_correta: str = "",
        tabela_origem_id: int = 0,
        nome_tabela_origem: str = "",
        coluna_tabela_origem: str = "",
    ) -> None:
        from apps.home.models import Pergunta

        resposta_correta, ordem = Pergunta.get_resposta_correta(
            pergunta_id,
            pedido_item_id,
        )

        self.salvar_checklist(
            self,
            estado_civil_id=estado_civil_id,
            item_id=item_id,
            pergunta_id=pergunta_id,
            pessoa_id=pessoa_id,
            funcionario_id=funcionario_id,
            pedido_item_id=pedido_item_id,
            resposta=resposta.tite() if resposta else " ",
            resposta_correta=(
                resposta_enviada_correta
                if resposta_enviada_correta
                else resposta_correta.tite()
                if resposta
                else " "
            ),
            tabela_origem_id=tabela_origem_id,
            nome_tabela_origem=nome_tabela_origem,
            coluna_tabela_origem=coluna_tabela_origem,
            ordem=ordem,
        )


class PedidoParteManager(Manager):
    def deletar_por_pedido_id(self, pedido_id) -> None:
        logger.info(f"Deletando partes do pedido {pedido_id}")
        self.get_queryset().filter(pedido_id=pedido_id).delete()

    def criar_do_fb(self, pedido, pedido_fb) -> list["PedidoParte"]:
        logger.debug("PARTES: Criando/atualizando PARTES do Pedido")

        objetos_partes = []

        def get_or_create_livro05(nome) -> "Livro05":
            """Função auxiliar para obter ou criar uma pessoa em Livro05."""
            from apps.home.models import models_home

            try:
                with transaction.atomic():
                    pessoa, created = models_home.Livro05.objects.get_or_create(
                        nome=nome,
                        cpf=None,
                    )
            except models_home.Livro05.MultipleObjectsReturned:
                pessoa = (
                    models_home.Livro05.objects.filter(nome=nome, cpf=None)
                    .order_by("-criado_em")
                    .first()
                )
            except IntegrityError as e:
                if "duplicate key value violates unique constraint" in str(e):
                    pessoa = (
                        models_home.Livro05.objects.filter(nome=nome, cpf=None)
                        .order_by("-criado_em")
                        .first()
                    )
                else:
                    raise
            return pessoa

        def adicionar_parte(nome, papel) -> None:
            """Função auxiliar para adicionar uma parte ao pedido."""
            pessoa_mais_recente = get_or_create_livro05(nome)
            try:
                with transaction.atomic():
                    obj, created = self.get_or_create(
                        pessoa=pessoa_mais_recente,
                        pedido=pedido,
                        papel=papel,
                    )
                    if obj:
                        objetos_partes.append(obj)
            except IntegrityError as e:
                if "duplicate key value violates unique constraint" in str(e):
                    logger.info(
                        f"Erro de duplicação de chave: A chave (id)={pessoa_mais_recente.id} já existe.",
                    )
                else:
                    raise

        # Adicionar SOLICITANTE
        if pedido_fb["NOMEAPRESENTANTE"]:
            nome = formatar_nome(str(pedido_fb["NOMEAPRESENTANTE"]))
            adicionar_parte(nome, TipoParte.SOLICITANTE)

        # Adicionar ADQUIRENTE
        if pedido_fb["NOMEADQUIRENTE"]:
            nome = formatar_nome(str(pedido_fb["NOMEADQUIRENTE"]))
            adicionar_parte(nome, TipoParte.ADQUIRENTE)

        # Adicionar TRANSMITENTE
        if pedido_fb["NOMETRANSMITENTE"]:
            nome = formatar_nome(pedido_fb["NOMETRANSMITENTE"])
            adicionar_parte(nome, TipoParte.TRANSMITENTE)

        logger.info(f"PARTES: {len(objetos_partes)} partes gravadas.")
        return objetos_partes


class FinanceiroManager(Manager):
    def deletar_por_pedido_id(self, pedido_id) -> None:
        logger.debug(f"Deletando registros de caixa do pedido {pedido_id}")
        # Filtra e deleta os objetos Financeiro baseados na pedido_id
        self.get_queryset().filter(pedido_id=pedido_id).delete()

    def total_caixa(self, pedido_id) -> Decimal:
        aggregate = self.filter(pedido=pedido_id).aggregate(
            valor_pago_sum=Sum("valor_transacao"),
        )
        return (
            Decimal(aggregate["valor_pago_sum"])
            if aggregate["valor_pago_sum"]
            else Decimal(0)
        )

    def total_caixa_pedido_certidao_numero_pedido(
        self,
        numero_pedido_certidao,
    ) -> Decimal:
        aggregate = self.filter(
            numero_pedido_certidao=numero_pedido_certidao,
        ).aggregate(
            valor_pago_sum=Sum("valor_transacao"),
        )
        return (
            Decimal(aggregate["valor_pago_sum"])
            if aggregate["valor_pago_sum"]
            else Decimal(0)
        )

    def total_caixa_pedido_certidao(self, pedido_certidao_id) -> Decimal:
        aggregate = self.filter(pedido_certidao_id=pedido_certidao_id).aggregate(
            valor_pago_sum=Sum("valor_transacao"),
        )
        return (
            Decimal(aggregate["valor_pago_sum"])
            if aggregate["valor_pago_sum"]
            else Decimal(0)
        )

    def registrar_pedido_de_certidao(
        self,
        pedido_certidao: "PedidoCertidao",
        usuario=None,
    ) -> "Financeiro":
        obj, created = self.update_or_create(
            pedido_certidao_id=pedido_certidao.pk,
            defaults={
                "descricao": f"Pedido de Certidão {pedido_certidao.numero_pedido} - {pedido_certidao.nome_apresentante}",
                "valor_transacao": pedido_certidao.total_pedido,
                "data_transacao": pedido_certidao.data_entrada,
                "colaborador_id": (
                    pedido_certidao.criado_por.id
                    if pedido_certidao.criado_por
                    else usuario.id
                    if usuario
                    else 1
                ),
            },
        )
        return obj

    def criar_registros_de_caixa_obtidos_do_fb(
        self,
        pedido: "PedidoCetidao",
        registros_caixa,
    ) -> list["Financeiro"]:
        for registro in registros_caixa:
            logger.debug(
                f"CAIXA: Transação do Pedido: {pedido}. Transacao ID: {registro['CHAVE_CAIXA']}",
            )

            if pedido:
                # Aqui você pode adicionar lógica para tratar os valores antes de inseri-los
                datapagamento = (
                    registro["DATAPAGAMENTO"]
                    if registro["DATAPAGAMENTO"]
                    else timezone.now()
                )

                # Atualiza ou cria um novo registro baseado na chave única 'id'
                obj, created = self.update_or_create(
                    id=registro["CHAVE_CAIXA"],
                    defaults={
                        "pedido_id": registro["CHAVE_PEDIDOS"],
                        "data_transacao": adicionar_fuso_horario_em_data(datapagamento),
                        "descricao": registro["DESCRICAO"],
                        "tipotransacao": registro["TIPOTRANSACAO"],
                        "tipodocumento": registro["TIPODOCUMENTO"],
                        "valor_transacao": registro["VALOR"],
                        "cheque": registro["CHEQUE"],
                        "pedido_certidao_id": registro["CHAVE_PED_CERTIDOES"],
                        "colaborador_id": registro["CHAVE_FUNCIONARIOS"],
                        "numero_protocolo_ec": registro["NROORDEM_EC"],
                        "colaborador_confirmado_id": registro[
                            "CHAVE_FUNCIONARIOS_PAGO"
                        ],
                    },
                )

                if created:
                    logger.info(
                        f"CAIXA: Transação de {registro['DESCRICAO']} - R$ {registro['VALOR']}. ID: {registro['CHAVE_CAIXA']} criado.",
                    )
                else:
                    logger.info(
                        f"CAIXA: Transação de {registro['DESCRICAO']} {registro['VALOR']} {registro['CHAVE_CAIXA']} atualizada.",
                    )

            else:
                logger.info(
                    f"CAIXA: Pedido {registro['CHAVE_PEDIDOS']} não encontrado para criar/atualizar registro de caixa",
                )

        return []


class SeloManager(Manager):
    def filter_numero_pedido(self):
        return (
            super()
            .get_queryset()
            .annotate(
                numero_pedido=Case(
                    When(
                        certidao__isnull=False,
                        then=Case(
                            When(
                                certidao__imovel_id__isnull=False,
                                then="certidao__imovel__pedido__numero_pedido",
                            ),
                            When(
                                certidao__pessoa_id__isnull=False,
                                then="certidao__pessoa__pedido__numero_pedido",
                            ),
                            default=Value(None),
                            output_field=IntegerField(),
                        ),
                    ),
                    default=Value(None),
                    output_field=IntegerField(),
                ),
            )
        )

    def filtrar_por_protocolo(self, protocolo):
        pedido_itens = protocolo.pedido.itens_do_pedido.all()
        return self.filter(pedido_item__in=pedido_itens)

    def filtrar_proximo_disponivel(self) -> "SeloEletronico":
        return (
            self.filter(data_selo__isnull=True, cancelado_em__isnull=True)
            .order_by()
            .select_for_update()
            .first()
        )

    def deletar_por_pedido_id(self, pedido_id) -> None:
        logger.debug(f"Deletando selos do pedido {pedido_id}")
        from apps.home.models import models_home

        # Filtra e deleta os objetos SeloEletronico baseados no pedido_id
        pedidos_itens_ids = models_home.PedidoItem.objects.filter(
            pedido_id=pedido_id,
        ).values_list(
            "pk",
            flat=True,
        )

        # self.filter(pedido_id=pedido_id).delete()
        self.get_queryset().filter(pedido_item_id__in=pedidos_itens_ids).delete()

    def deletar_pelo_id(self, pk) -> None:
        """
        Deleta um selo com o ID especificado.

        :param id: O ID do selo a ser deletado.
        """
        selo = self.filter(id=pk)
        selo.delete()

    def deletar_por_ids(self, ids) -> None:
        """
        Deleta selos com os IDs especificados.

        :param ids: Uma lista de IDs dos selos a serem deletados.
        """
        self.get_queryset().filter(id__in=ids).delete()

    def deletar_selos_obtidos_do_fb(self, selos_fb) -> None:
        # receber um dicionario de selos, extrair o ID (selo_fb["CHAVE_PEDIDOS"]) e deletar
        ids = [selo["CHAVE_SELO_DIGITAL_MG"] for selo in selos_fb]

        self.deletar_por_ids(ids)

    def criar_selos_obtidos_do_fb(
        self,
        pedido_item,
        selos_fb,
    ) -> list["SeloEletronico"]:
        from apps.home.models import SeloEletronico

        logger.info(f"SELOS: Importando selos do PedidoItem: {pedido_item.pk}")
        pedido_item_id = pedido_item.pk

        # Filtra os selos que correspondem ao pedido_item_id
        selos_filtrados = [
            selo for selo in selos_fb if selo["CHAVE_PEDIDOS_ITENS"] == pedido_item_id
        ]
        logger.info(
            f"SELOS: Importando {len(selos_filtrados)} do PedidoItem: {pedido_item_id}",
        )

        if selos_filtrados:
            selos_para_criar = []
            selos_para_atualizar = []

            # Busca os IDs dos selos que já existem no banco de dados
            selos_existentes_ids = set(
                self.filter(
                    id__in=[selo["CHAVE_SELO_DIGITAL_MG"] for selo in selos_filtrados],
                ).values_list(
                    "id",
                    flat=True,
                ),
            )

            for selo_fb in selos_filtrados:
                selo_id = selo_fb["CHAVE_SELO_DIGITAL_MG"]
                selo_data = {
                    # "pedido": pedido_item.pedido,
                    "pedido_item": pedido_item,
                    "codigo_sequencial_unico": selo_fb["CODIGO_SEQUENCIAL_UNICO"],
                    "utilizado_em": selo_fb["DATA_UTILIZACAO"],
                    "codigo_de_seguranca": selo_fb["CODIGO_DE_SEGURANCA"],
                    "selo_de_consulta": selo_fb["SELO_PARA_CONSULTA"],
                }

                if selo_id in selos_existentes_ids:
                    # Atualiza os selos existentes
                    selos_para_atualizar.append(SeloEletronico(id=selo_id, **selo_data))
                else:
                    # Cria novos selos
                    selos_para_criar.append(SeloEletronico(id=selo_id, **selo_data))

            with transaction.atomic():
                # Bulk create para novos selos
                if selos_para_criar:
                    self.bulk_create(selos_para_criar, ignore_conflicts=True)

                # Bulk update para selos existentes
                if selos_para_atualizar:
                    self.bulk_update(
                        selos_para_atualizar,
                        fields=[
                            # "pedido",
                            "pedido_item",
                            "codigo_sequencial_unico",
                            "utilizado_em",
                            "codigo_de_seguranca",
                            "selo_de_consulta",
                        ],
                    )

            selos_gravados = selos_para_criar + selos_para_atualizar
            logger.info(f"SELOS: {len(selos_gravados)} selos gravados.")

            return selos_gravados
        return []

    def get_selo_usados_e_nao_enviado(self):
        return self.filter(utilizado_em__isnull=False, enviado_em__isnull=True)


class Livro02TextoManager(Manager):
    def deletar_por_pedido_id(self, pedido_id) -> None:
        logger.debug(f"Deletando textos do pedido {pedido_id}")
        from apps.home.models import models_home

        # Primeiro, obtenha os IDs de PedidoItem relacionados à ID do pedido fornecida
        pedidos_itens_ids = models_home.PedidoItem.objects.filter(
            pedido_id=pedido_id,
        ).values_list(
            "pk",
            flat=True,
        )

        # Em seguida, use esses IDs para filtrar e deletar os objetos Livro02Texto correspondentes
        self.get_queryset().filter(pedido_item_id__in=pedidos_itens_ids).delete()

    def gravar_html_bd_livro02(
        self,
        pedido_item_id,
        arquivo_gerado_final_html,
        numero_ato,
    ) -> None:
        # Gerar apenas numero inteiro
        numero_ato = int(re.sub("[^0-9]", "", numero_ato))

        # Leitura do arquivo HTML
        with open(arquivo_gerado_final_html, encoding="utf_8") as file:
            html_content = file.read()

        self.create(
            id=pedido_item_id,
            imovel=None,
            pedido_item_id=pedido_item_id,
            numero_ato=numero_ato,
            texto=html_content,
        )


class PedidosItensDadosImovelManager(Manager):
    def deletar_por_pedido_id(self, pedido_id) -> None:
        from apps.home.models import models_home

        # Primeiro, obtenha os IDs de PedidoItem relacionados à ID do pedido fornecida
        pedidos_itens_ids = models_home.PedidoItem.objects.filter(
            pedido_id=pedido_id,
        ).values_list(
            "pk",
            flat=True,
        )

        # Em seguida, use esses IDs para filtrar e deletar os objetos PedidoItemImovel correspondentes
        self.get_queryset().filter(pedido_item_id__in=pedidos_itens_ids).delete()


class PedidosPartesAtoManager(Manager):
    def deletar_por_pedido_id(self, pedido_id) -> None:
        from apps.home.models import models_home

        # Primeiro, obtenha os IDs de PedidoItem relacionados à ID do pedido fornecida
        pedidos_itens_ids = models_home.PedidoItem.objects.filter(
            pedido_id=pedido_id,
        ).values_list("pk", flat=True)

        # Em seguida, use esses IDs para filtrar e deletar os objetos PedidoParteAto correspondentes
        self.get_queryset().filter(pedido_item_id__in=pedidos_itens_ids).delete()


class PedidosManager(Manager):
    def deletar_por_pedido_id(self, pedido_id) -> None:
        logger.debug(f"Deletando pedido {pedido_id}")
        # Filtra e deleta o objeto Pedidos baseado no pedido
        self.filter(pk=pedido_id).delete()

    def criar_do_fb(self, pedido_fb):
        logger.info(f"PEDIDO: Criando pedido {pedido_fb['CHAVE_PEDIDOS']}")

        defaults = {
            "uf": pedido_fb["UF"],
            "data_prevista": (
                pedido_fb["DATAPREVISTA"] if pedido_fb["DATAPREVISTA"] else None
            ),
            "data_validade": (
                pedido_fb["DATA_VALIDADE"]
                if pedido_fb["DATA_VALIDADE"]
                else timezone.now()
            ),
            "endereco": pedido_fb["ENDERECO"] if pedido_fb["ENDERECO"] else None,
            "telefone": pedido_fb["TELEFONE"],
            "municipio": str(pedido_fb["MUNICIPIO"]).title(),
            "observacao": pedido_fb["OBSERVACAO"],
            "email": pedido_fb["EMAIL"],
            "tipo_documento_apresentante": pedido_fb["TIPODOCUMENTOAPRES"],
            "documento_apresentante": pedido_fb["NUMERODOCUMENTOAPRES"],
            "data_entrada": pedido_fb["DATAENTRADA"].date(),
            "numero_talao": pedido_fb["NROTALAO"],
            "numero": pedido_fb["NROPEDIDO"],
        }

        obj, created = self.update_or_create(
            pk=pedido_fb["CHAVE_PEDIDOS"],
            defaults=defaults,
        )
        if created:
            logger.info(
                f"PEDIDO criado: {pedido_fb['CHAVE_PEDIDOS']}: {pedido_fb['OBSERVACAO']}",
            )
        else:
            logger.info(
                f"PEDIDO atualizado: {pedido_fb['CHAVE_PEDIDOS']}: {pedido_fb['OBSERVACAO']}",
            )

        return obj


class ChecklistRealizadoHistoricoManager(Manager):
    """Manager para ChecklistRealizadoHistorico."""

    def deletar_por_pedido_item_id(self, pedido_item_id) -> None:
        """Deleta os objetos ChecklistRealizadoHistorico baseados no pedido_item_id."""
        # Filtra e deleta os objetos ChecklistRealizadoHistorico baseados no pedido_item_id
        self.get_queryset().filter(pedido_item_id=pedido_item_id).delete()


class NotaDevolucaoTextoManager(Manager):
    def deletar_por_pedido_item_id(self, pedido_item_id) -> None:
        """Deleta os objetos NotaDevolucaoTexto baseados no pedido_item_id."""
        # Filtra e deleta os objetos NotaDevolucaoTexto baseados no pedido_item_id
        self.get_queryset().filter(pedido_item_id=pedido_item_id).delete()


class FasesProtocoloManager(Manager):
    def get_fase_conferencia(self):
        return self.update_or_create(
            descricao="P",
            nome="Conferencia",
            defaults={"prazo_dias": 5, "grupo": 1},
        )

    def filtrar_ordenadas_por_nome(self):
        return self.get_queryset().order_by("nome")

    def criar_defaults(self):
        logger.info("Populando dados para TipoFaseProtocolo")
        fases_do_protocolo = [
            {
                "id": 1,
                "ordem": 1,
                "descricao": "P",
                "nome": "Recepção",
                "prazo_dias": 0,
                "grupo": 1,
            },
            {
                "id": 2,
                "ordem": 3,
                "descricao": "F",
                "nome": "Extato de Ficha",
                "prazo_dias": 1,
                "grupo": 1,
            },
            {
                "id": 3,
                "ordem": 2,
                "descricao": "P",
                "nome": "Digitalização",
                "prazo_dias": 1,
                "grupo": 1,
            },
            {
                "id": 4,
                "ordem": 4,
                "descricao": "P",
                "nome": "Análise",
                "prazo_dias": 2,
                "grupo": 1,
            },
            {
                "id": 5,
                "ordem": 6,
                "descricao": "P",
                "nome": "Conferência",
                "prazo_dias": 5,
                "grupo": 1,
            },
            {
                "id": 6,
                "ordem": 7,
                "descricao": "P",
                "nome": "Concluido",
                "prazo_dias": 1,
                "grupo": 1,
            },
            {
                "id": 7,
                "ordem": 5,
                "descricao": "D",
                "nome": "Registro",
                "prazo_dias": 10,
                "grupo": 1,
            },
            {
                "id": 8,
                "ordem": 5,
                "descricao": "F",
                "nome": "Registro",
                "prazo_dias": 4,
                "grupo": 1,
            },
            {
                "id": 9,
                "ordem": 3,
                "descricao": "D",
                "nome": "Extato de Ficha",
                "prazo_dias": 2,
                "grupo": 1,
            },
            {
                "id": 10,
                "ordem": 1,
                "descricao": "F",
                "nome": "Reentrada",
                "prazo_dias": 1,
                "grupo": 2,
            },
            {
                "id": 11,
                "ordem": 1,
                "descricao": "D",
                "nome": "Reentrada",
                "prazo_dias": 2,
                "grupo": 2,
            },
            {
                "id": 12,
                "ordem": 1,
                "descricao": "D",
                "nome": "Reentrada Exigencia",
                "prazo_dias": 20,
                "grupo": 2,
            },
            {
                "id": 13,
                "ordem": 1,
                "descricao": "D",
                "nome": "Reentrada Exigencia Ultimo Dia",
                "prazo_dias": 5,
                "grupo": 2,
            },
        ]

        for fase in fases_do_protocolo:
            self.update_or_create(
                id=fase["id"],
                defaults={k: v for k, v in fase.items() if k != "id"},
            )

        # # Mensagem de sucess
        logger.info("Tabela Fase Protocolo adicionada!")


class StatusProtocoloManager(Manager):
    def get_status_em_andamento(self):
        obj, created = self.get_or_create(descricao="Em Andamento")
        return obj

    def criar_defaults(self):
        # ATUALIZAR STATUS DO PROTOCOLO
        from apps.home.models import models_home

        status = [
            {
                "id": 0,
                "descricao": models_home.StatusProtocolo.EM_ANDAMENTO,
                "finalizar": NAO,
            },
            {
                "id": 1,
                "descricao": models_home.StatusProtocolo.EXIGENCIA,
                "finalizar": NAO,
            },
            {
                "id": 5,
                "descricao": models_home.StatusProtocolo.EM_REGISTRO,
                "finalizar": NAO,
            },
            {
                "id": 6,
                "descricao": models_home.StatusProtocolo.PRONTO_PARA_REGISTRAR,
                "finalizar": NAO,
            },
            {
                "id": 7,
                "descricao": models_home.StatusProtocolo.DISTRIBUIDO,
                "finalizar": NAO,
            },
            {
                "id": 2,
                "descricao": models_home.StatusProtocolo.CANCELADO,
                "finalizar": SIM,
            },
            {
                "id": 3,
                "descricao": models_home.StatusProtocolo.REGISTRADO,
                "finalizar": SIM,
            },
            {
                "id": 4,
                "descricao": models_home.StatusProtocolo.SUBJUDICE,
                "finalizar": SIM,
            },
        ]

        for item in status:
            self.update_or_create(id=item["id"], defaults=item)
        # # Mensagem de sucesso
        logger.info("Tabela Status Protocolo adicionada!")


class EventManager(Manager):
    def _convert_event_timezone(self, event) -> "Event":
        event.start_time = timezone.localtime(event.start_time)
        event.end_time = timezone.localtime(event.end_time)
        return event

    def get_all_events(self, user, opcao) -> list["Event"]:
        # Pasando o username do usuario e pegando o id dele
        auth_user_id, is_staff = get_user_id_2(user)

        # events = Event.objects.filter(user=user, is_active=True, is_deleted=False)
        if opcao == "A":
            events = self.filter(
                auth_user_id=user.pk,
                is_active=True,
                is_deleted=False,
                end_time_checked__isnull=True,
            )
        else:
            events = self.filter(auth_user_id=user.pk, is_active=True, is_deleted=False)

        # Ajustar o fuso horário de cada evento
        return [self._convert_event_timezone(event) for event in events]

    def get_running_events(self, user) -> list["Event"]:
        # print("Rodando Evento", user)
        # Pasando o username do usuario e pegando o id dele
        # auth_user_id, is_staff = get_user_id_2(user)

        # EXIBIR TODOS OS EVENTOS QUE NAO TENHA SIDO FINALIZADOS
        events = self.filter(
            # user=user,
            auth_user_id=user.pk,
            is_active=True,
            is_deleted=False,
            end_time_checked__isnull=True,
            # end_time__gte=timezone.now().date(),
        ).order_by("start_time")

        # Ajustar o fuso horário de cada evento
        return [self._convert_event_timezone(event) for event in events]

    def get_por_numeros(self, origem, numeros) -> list["Event"]:
        # print("Exibir Protocolo ou Pedido de Certidao")
        return (
            self.filter(origem=origem, numero__in=numeros, exibir_agenda_protocolo=SIM)
            .distinct(
                "numero",
                "title",
                "start_time",
                "end_time_checked",
                "fase_agenda_id",
            )
            .order_by("numero", "fase_agenda_id", "start_time")
            # .order_by("numero", "start_time")
        )

        # lista_id = [event.numero for event in events]
        # lista_title = [event.title for event in events]
        # lista_start_time = [event.start_time for event in events]
        # lista_end_time_checked = [event.end_time_checked for event in events]

        # Ajustar o fuso horário de cada evento
        # events = [self._convert_event_timezone(event) for event in events]
        # return lista_id, lista_title, lista_start_time, lista_end_time_checked

    def apagar_eventos_pelo_numero(self, numero) -> None:
        # Filtrar eventos pelo número e apagar
        self.filter(numero=str(numero)).delete()

    def encerrar_evento_pelo_titulo(
        self,
        titulo,
        data=None,
        exibir_agenda_protocolo=SIM,
    ) -> None:
        if data is None:
            data = timezone.now().date()

        # Filtrar eventos em uma única consulta
        events_to_update = self.filter(title=str(titulo), end_time_checked__isnull=True)

        # Atualizar todos os eventos em lote
        events_to_update.update(end_time_checked=data - timedelta(days=0))


class TipoRegimeCasamentoManager(Manager):
    def get_queryset(self):
        return super().get_queryset().filter(id__gte=0, exibir=TipoSimNao.SIM)

    def importar_tipo_regime_casamento_do_fb_por_id(self, tipo_regime_id: int):
        from apps.home.services.firebird import importar_tipo_regime_casamento_do_fb

        # Tenta importar o estado_civil
        tipo_regime_fb = importar_tipo_regime_casamento_do_fb(tipo_regime_id)

        if tipo_regime_fb:
            # Cria ou atualiza o estado_civil com base nos dados importados
            obj, created = self.update_or_create(
                id=tipo_regime_fb["CHAVE_CATEGORIAS"],
                defaults={
                    "descricao_regime": str(tipo_regime_fb["TIPOCATEGORIA"]).title(),
                },
            )
            return obj

        return None

    def get_descricao_por_id(self, tipo_regime_id: int):
        # Tentativa de converter o id para um inteiro, caso contrário retorna None
        try:
            tipo_regime_id = int(tipo_regime_id)
        except ValueError:
            return None

        # Retorna a descrição do regime ou None se não encontrar
        objeto = self.get_queryset().filter(id=tipo_regime_id).first()
        return objeto.descricao_regime if objeto else None

    def get_ou_criar_tipo_regime_casamento(self, descricao: str):
        # Retorna o estado_civil ou cria uma nova se não encontrar
        obj, created = self.update_or_create(descricao_regime=descricao)
        return obj

    def criar_defaults(self) -> None:
        self.update_or_create(
            id=3,
            defaults={
                "descricao_regime": "Separação de Bens Convencional (obrigatório Pacto)",
                "pacto": SIM,
            },
        )
        self.update_or_create(
            id=6,
            defaults={"descricao_regime": "Regime Aquestros", "pacto": SIM},
        )
        self.update_or_create(id=2, defaults={"descricao_regime": "Viúvo"})
        self.update_or_create(id=4, defaults={"descricao_regime": "Divorciado"})
        self.update_or_create(
            id=7,
            defaults={"descricao_regime": "Separado Consensual."},
        )
        self.update_or_create(
            id=5,
            defaults={"descricao_regime": "Jurídico", "pacto": SIM},
        )
        self.update_or_create(id=1, defaults={"descricao_regime": "Solteiro"})
        self.update_or_create(id=0, defaults={"descricao_regime": "Casado"})
        self.update_or_create(id=8, defaults={"descricao_regime": "Casado8"})
        self.update_or_create(id=9, defaults={"descricao_regime": "Casado9"})
        self.update_or_create(id=10, defaults={"descricao_regime": "Casado10"})
        self.update_or_create(id=11, defaults={"descricao_regime": "Casado11"})
        self.update_or_create(id=12, defaults={"descricao_regime": "Casado12"})
        self.update_or_create(id=13, defaults={"descricao_regime": "Casado13"})

        with contextlib.suppress(Exception):
            self.update_or_create(id=-1, defaults={"descricao_regime": ""})

        logger.info("Tipos de Regime de Casamento básicos criadas!")

    def lista_tipo_regime_casamento(self):
        return list(
            self.values_list("id", "descricao_regime").order_by("descricao_regime"),
        )


class ColaboradorManager(Manager):
    def filtrar_por_default(self):
        from apps.home.models import models_home

        try:
            return self.get(default=True)
        except ObjectDoesNotExist:
            return models_home.Colaborador.get_or_create_default()

    def filtrar_por_default_id(self):
        from apps.home.models import models_home

        try:
            return self.get(default=True).id
        except ObjectDoesNotExist:
            colaborador = models_home.Colaborador.get_or_create_default()
            return colaborador.id

    def filtrar_por_ativos(self):
        return (
            self.get_queryset()
            .filter(inativo=NAO, usuario__is_active=True)
            .order_by("usuario__first_name")
        )

    def filtrar_por_pode_receber_protocolos_do_balcao(self):
        colaboradores = self.filter(recebe_protocolos_do_balcao=True)
        if not colaboradores:
            colaboradores = self.filter(inativo=NAO)
        return colaboradores

    def filtrar_por_exibir_nome_caixa(self) -> QuerySet["Colaborador"]:
        colaboradores = self.filter(exibir_nome_caixa=True)
        # print(colaboradores)
        if not colaboradores:
            colaboradores = self.filter(inativo=NAO)
        return colaboradores

    def importar_do_fb(self):
        # from constance import config

        from apps.home.models import models_home

        # if not config.FIREBIRD_ENABLED:
        #     logger.error("Firebird não habilitado!")
        #     return

        with FbConnection() as db:
            funcionarios_fb = db.execute_query("SELECT * FROM FUNCIONARIOS")

        nomes_criptografados = [funcionario["NOME"] for funcionario in funcionarios_fb]
        nomes_descriptografados = descriptografar_lista(nomes_criptografados)

        for i, funcionario_fb in enumerate(funcionarios_fb):
            nome_descriptografado = nomes_descriptografados[i]
            with transaction.atomic():
                try:
                    obj, created = models_home.Usuario.objects.update_or_create(
                        id=funcionario_fb["CHAVE_FUNCIONARIOS"],
                        defaults={
                            "first_name": nome_descriptografado,
                            "username": nome_descriptografado,
                            "is_active": True,
                            "cartorio_id": 1,
                            "password": make_password("CONFIGURAR_LOCALMENTE"),
                        },
                    )

                    self.update_or_create(
                        id=funcionario_fb["CHAVE_FUNCIONARIOS"],
                        defaults={
                            "nome": nome_descriptografado,
                            "usuario_id": obj.id,
                            "inativo": NAO,
                        },
                    )
                except Exception as e:
                    logger.exception(
                        f"Erro ao importar colaborador {funcionario_fb}: {e}",
                    )

                logger.info(
                    f"Colaborador {obj.first_name} criado! ID: {funcionario_fb['CHAVE_FUNCIONARIOS']}",
                )


class FaseAgendaItensManager(Manager):
    def get_fase_agenda_por_id(self, pk):
        # Retorna a descrição da fase da agenda ou None se não encontrar
        objeto = self.get_queryset().filter(id=pk).first()
        return objeto.descricao if objeto else None


class FaseAgendaMananager(Manager):
    def get_fase_agenda_por_id(self, pk):
        # Retorna a descrição da fase da agenda ou None se não encontrar
        objeto = self.get_queryset().filter(id=pk).first()
        return objeto.descricao if objeto else None


class Livro02Manager(Manager):
    def get_imovel_por_id(self, pk):
        # Retorna a descrição da fase da agenda ou None se não encontrar
        objeto = self.get_queryset().filter(id=pk).first()
        return objeto.descricao if objeto else None

    def get_tipo_do_imovel_pelo_id(self, pk):
        objeto = self.get_queryset().filter(id=pk).first()
        return objeto.tipo if objeto else "M"

    def excluir_por_id(self, pk):
        from apps.home.models import models_home

        logger.info(f"Excluindo Livro02 por ID: {pk}")
        vinculos = models_home.Vinculo.objects.filter(imovel_id=pk)
        if vinculos:
            ids_vinculos = [int(vinculo.pk) for vinculo in vinculos]
            models_home.PedidoParteAto.objects.filter(
                vinculo_id__in=ids_vinculos,
            ).delete()

        # RETIRAR DO REGISTRO ANTERIOR
        unidades = []
        for unidade in models_home.Unidade.objects.filter(registro_anterior_id=pk):
            models_home.FichaAuxiliar.objects.filter(unidade_id=unidade.id).delete()
            unidades.append(unidade.id)

        # RETIRAR DO REGISTRO ANTERIOR
        if unidades:
            for unidade_id in unidades:
                models_home.Rua.objects.filter(unidade_id=unidade_id).delete()
                models_home.Lote.objects.filter(unidade_id=unidade_id).delete()
                models_home.Unidade.objects.filter(id=unidade_id).delete()

        models_home.FichaAuxiliar.objects.filter(id=pk).delete()

        unidade = models_home.Unidade.objects.filter(imovel_id=pk).first()
        if unidade:
            models_home.Rua.objects.filter(unidade_id=unidade.pk).delete()
            models_home.Lote.objects.filter(unidade_id=unidade.pk).delete()
            models_home.Unidade.objects.filter(id=unidade.pk).delete()
            models_home.FichaAuxiliar.objects.filter(unidade_id=unidade.pk).delete()

        models_home.Contribuintes.objects.filter(imovel_id=pk).delete()
        models_home.Anterior.objects.filter(imovel_id=pk).delete()
        models_home.Unidade.objects.filter(imovel_id=pk).delete()
        models_home.RuralNome.objects.filter(imovel_id=pk).delete()
        models_home.Rural.objects.filter(imovel_id=pk).delete()
        models_home.Vinculo.objects.filter(imovel_id=pk).delete()
        models_home.Unidade.objects.filter(imovel_id=pk).delete()
        models_home.Livro02.objects.filter(pk=pk).delete()
        models_home.Unidade.objects.filter(imovel_id=pk).delete()

    def criar_registro_com_dados_do_fb(self, registro_fb: dict) -> QuerySet:
        # converte o dicionario numa lista para acessar as posições
        # melhorar depois para obter pela chave.
        registro = list(registro_fb.values())

        logger.info(f"REGISTRO: Construindo com dados do FB: ID: {registro[0]!s}")

        numero = (
            "".join([char for char in registro[5] if char.isdigit()])
            if not registro[10]
            else str(int(registro[10]))
        )

        try:
            try:
                tipo_unidade = (
                    models.TipoUnidade.objects.get_or_create(
                        descricao=registro[7],
                    )[0]
                    if registro[7]
                    else ""
                )
            except Exception as e:
                logger.exception(f"Erro ao criar tipo de unidade: {e}")
                tipo_unidade = ""

            obj_registro = self.create(
                pk=str(registro[0]),
                classe=str(registro[1]),
                data_abertura="1899-01-01" if not registro[2] else registro[2],
                encerrado=str(registro[3]) if registro[3] else "F",
                registro_anterior=str(registro[4]) if registro[4] else "0",
                numero=numero,
                tipo=str(registro[6]) if registro[6] else "",
                tipo_unidade=tipo_unidade if tipo_unidade else "",
                cartorio=str(registro[8]) if registro[8] else "1",
                municipio=str(registro[9]) if registro[9] else "",
                # numinteiro=numero_inteiro,
                cep="" if not registro[11] else str(registro[11]),
                criado_em="1899-01-01" if registro[12] is None else registro[12],
                ultimo_livro="" if not registro[13] else str(registro[13]),
                ultimo_folha="" if not registro[14] else str(registro[14]),
                area_construida="" if not registro[15] else str(registro[15]),
                numero_nirf="" if not registro[16] else str(registro[16]),
                numero_ccirr="" if not registro[17] else str(registro[17]),
                numero_car="" if not registro[18] else str(registro[18]),
                numero_incra="" if not registro[19] else str(registro[19]),
                area_construida_residencial=(
                    "" if not registro[20] else str(registro[20])
                ),
                area_construida_comercial="" if not registro[21] else str(registro[21]),
                cnm="" if not registro[22] else str(registro[22]),
            )

            # COMENTANDO POIS ESTAVA DANDO ERRO NA IMPORTAÇÃO
            # registro.update(registro_anterior_id=0 if not registro[0] else str(registro[0]))

            logger.info(f"REGISTRO: Criado  .: {obj_registro}")
            return obj_registro
        except IntegrityError as e:
            msg = "Erro ao criar registro"
            logger.exception(f"{msg} {e}")
            raise

        return None

    def criar_defaults(self):
        try:
            # Cria um imóvel com id 0 (zero) se ele não existir
            obj, created = self.update_or_create(
                pk=0,
                defaults={
                    "classe": TipoClasseRegistro.LOTE,
                    "numero": 0,
                    "tipo": TipoRegistro.MATRICULA,
                    "cartorio": "1",
                },
            )
            if created:
                logger.info("Imovel 0adicionado!")
            return obj
        except Exception:
            msg = "Erro ao criar imovel 0"
            logger.exception(msg)
            logger.exception(msg)

            return None

    def get_pelo_pedido_item(self, pedido_item):
        return self.filter(
            numero=pedido_item.numero_registro,
            tipo=pedido_item.tipo_registro,
            cartorio=pedido_item.numero_ri,
        ).first()

    def localizar_imovel(self, numero, tipo, cartorio) -> None:
        self.filter(
            numero=numero,
            tipo=tipo,
            cartorio=cartorio,
        )

    def get_registro_pelo_livro03(self, livro03):
        return self.filter(
            numero=livro03.numero,
            tipo=TipoRegistro.MATRICULA,
            cartorio=livro03.cartorio,
        ).first()

    # Todas as entradas distintas da coluna classe de dados, independentemente do valor que possuam, e ordená-las.
    def get_classe_imovel(self):
        return self.values_list("classe", flat=True).distinct().order_by("classe")


class Livro05Manager(Manager):
    def get_por_id(self, pk):
        # Retorna a descrição da fase da agenda ou None se não encontrar
        objeto = self.get_queryset().filter(id=pk).first()
        return objeto.descricao if objeto else None

    def criar_defaults(self):
        try:
            # Cria um imóvel com id 0 (zero) se ele não existir
            obj, created = self.update_or_create(
                pk=0,
                defaults={
                    "cpf": "",
                    "nome": "Nao Consta",
                    "criado_em": settings.MINDATE,
                    "naturalidade": "",
                    "cidade": "",
                    "uf": "",
                    "estado_civil_id": 0,
                },
            )
            return obj
        except Exception:
            logger.exception("Erro ao criar pessoa 0: ")
            return None


class TituloManager(Manager):
    def get_por_id(self, pk):
        # Retorna a descrição da fase da agenda ou None se não encontrar
        objeto = self.get_queryset().filter(id=pk).first()
        return objeto.descricao if objeto else None

    def filtrar_por_principais(self):
        return self.filter(ato_principal=SIM).order_by("tipo_titulo")

    def importar_do_fb(self):
        from apps.home.models import models_home

        query = """ SELECT CHAVE_TITULOS, TIPOTITULO, PRAZO, EXIBIR, USAR_PERCENTUAL,
                            REGISTRAR, EXIBIRPROTOCOLO, CALCULOPREVISAO, TIPODATAPREVISTA
                    FROM TITULOS
                """
        with FbConnection() as db:
            titulos_fb = db.execute_query(query)

        titulos_de_protocolo = []

        for titulo_fb in titulos_fb:
            logger.info(
                f"Importando titulo {titulo_fb['TIPOTITULO']} ID: {titulo_fb['CHAVE_TITULOS']}",
            )
            # Converte a string para um objeto UUID
            titulo, created = models_home.Titulo.objects.update_or_create(
                pk=titulo_fb["CHAVE_TITULOS"],
                defaults={
                    "tipo_titulo": titulo_fb["TIPOTITULO"],
                    "exibir": titulo_fb["EXIBIR"],
                    "prazo": (
                        titulo_fb["PRAZO"] if titulo_fb["PRAZO"] is not None else 20
                    ),
                    "prazo_reentrada": 3,
                    "prazo_validade": 2,
                    "ato_principal": SIM,
                    "prazo_nota_devolucao": 10,
                },
            )

            titulos_de_protocolo.append(titulo)

        if titulos_de_protocolo:
            logger.info(
                f"TABELA BASICA: 'Titulos' {len(titulos_de_protocolo)} adicionados ou atualizados!",
            )

        return titulos_de_protocolo


class VinculoManager(Manager):
    def get_vinculos_do_imovel(self, imovel_id: int):
        return (
            self.select_related("estado_civil", "pessoa", "tipo_vinculo")
            .filter(imovel_id=imovel_id)
            .order_by("numero_ato")
        )

    def get_vinculos_de_proprietarios_atuais(self, imovel_id: int) -> list:
        from apps.home.models import models_home

        return (
            self.filter(
                imovel_id=imovel_id,
                situacao="F",
                tipo_vinculo_id__in=models_home.Configuracao.obter(
                    "proprietario_id",
                    "7",
                ),
            )
            .select_related("pessoa", "tipo_vinculo")
            .order_by("numero_ato")
        )

        # Vinculo do LIVRO 2

    def get_lista_proprietarios_do_imovel(self, imovel_id: int) -> list:
        from apps.home.models import models_home

        return list(
            self.filter(
                imovel_id=imovel_id,
                situacao="F",
                tipo_vinculo=models_home.TipoVinculo.get_proprietario(),
            )
            .values_list("id", "tipo_ato", "numero_ato", "area_pecentual", "pessoa")
            .order_by("numero_ato"),
        )

    def get_hipotecas_do_imovel(self, imovel_id: int) -> list:
        from apps.home.models import models_home

        return self.filter(
            imovel_id=imovel_id,
            situacao="F",
            tipo_vinculo_id__in=models_home.Configuracao.obter("hipoteca_id", 4),
        ).order_by("numero_ato")

    def filtrar_alienacoes_do_imovel(self, imovel_id: int) -> QuerySet["Vinculo"]:
        from apps.home.models import models_home

        return self.filter(
            imovel_id=imovel_id,
            situacao="F",
            tipo_vinculo_id__in=models_home.Configuracao.obter("alienacao_id", 2),
        ).order_by("numero_ato")


class LoteManager(Manager):
    def get_lote_por_id(self, pk):
        objeto = self.get_queryset().filter(id=pk).first()
        return objeto.descricao if objeto else None

    def criar_defaults(self) -> None:
        self.update_or_create(id=0, defaults={"id": 0, "unidade_id": 0})


class UnidadeManager(Manager):
    def criar_defaults(self) -> None:
        logger.info("UNIDADES: Criando unidade default. ID: 0!")
        obj, created = self.update_or_create(
            id=0,
            defaults={
                "imovel_id": 0,
                "id": 0,
                "registro_anterior_id": 0,
                "criado_em": settings.MINDATE,
                "sequencial": 0,
            },
        )


# class TipoVinculoManager(Manager):
#     def importar_do_fb(self) -> None:
#         from apps.home.utils import firebird

#         query = " SELECT CHAVE_FIGURAS, TIPOFIGURA FROM FIGURAS "
#         figuras = firebird.executar_e_get_resultados_em_dict(query)

#         # Loop para criar ou atualizar figuras
#         for figura in figuras:
#             # Converte a string para um objeto UUID
#             self.update_or_create(
#                 pk=figura["CHAVE_FIGURAS"],
#                 defaults={
#                     "descricao": str(figura["TIPOFIGURA"]).title(),
#                 },
#             )
#         # # Mensagem de sucesso
#         logger.info("Tabelas Tipo_Vinculo adicionadas!")

#     def importar_tipo_de_vinculo_do_fb_por_id(self, id, db: FbConnection = None):
#         # Tenta importar o estado_civil
#         query = f"""
#                 SELECT CHAVE_FIGURAS, TIPOFIGURA
#                 FROM FIGURAS
#                 WHERE CHAVE_FIGURAS = {id!s}"""
# #     def importar_tipo_de_vinculo_do_fb_por_id(self, id, db: FbConnection = None):
#         # Tenta importar o estado_civil
#         query = f"""
#                 SELECT CHAVE_FIGURAS, TIPOFIGURA
#                 FROM FIGURAS
#                 WHERE CHAVE_FIGURAS = {id!s}"""

#         db = FbConnection() if db is None else db
#         tipo_vinculo_fb = db.execute_query(query)

#         if tipo_vinculo_fb:
#             # Cria ou atualiza o estado_civil com base nos dados importados
#             obj, created = self.update_or_create(
#                 id=tipo_vinculo_fb["CHAVE_FIGURAS"],
#                 defaults={"descricao": str(tipo_vinculo_fb["TIPOFIGURA"]).title()},
#             )
#             logger.info(f"Tipo de Vinculo {obj} criado!")
#             return obj
#         else:
#             return None


class RegistroAuxiliarManager(Manager):
    def get_registro_auxiliar_por_id(self, pk):
        objeto = self.get_queryset().filter(id=pk).first()
        return objeto.descricao if objeto else None

    def get_registro_auxiliar_por_numero(self, numero):
        objeto = self.get_queryset().filter(numero=numero).first()
        return objeto.descricao if objeto else None

    def get_registro_auxiliar_por_pedido_item(self, pedido_item):
        if pedido_item.numero_registro:
            return self.filter(
                numero=pedido_item.numero_registro,
                # tipo=pedido_item.tipo_registro,
                cartorio=pedido_item.numero_ri,
            ).first()
        else:
            return None

    def get_dados_do_livro03_em_dict(self, numero) -> dict:
        from apps.home.models import models_home
        from apps.home.utils import formatar_data
        from apps.home.views import get_descricao_documento

        (
            numero_cedula,
            data_abertura,
            devedor,
            credor,
            garantias,
            tipo_ato,
            numero_registro,
            credor_cpf,
        ) = ("", "", "", "", "", "", "", "")

        # Obter os dados do LIVRO 3
        registro_auxiliar = self.filter(numero=numero)
        for item in registro_auxiliar:
            registro_auxiliar_id = str(item.id)
            numero_cedula = str(item.numero_cedula)
            data_abertura = str(item.data_abertura)

        # Obter os dados da PESSOAS
        credor_atual = models_home.Livro03Ligacao.objects.filter(
            registro_auxiliar_id=registro_auxiliar_id,
            figuras_id__in=models_home.Configuracao.get_lista("credor_id", "INTEIRO"),
        )
        credor = credor + ", " + str(credor_atual.pessoa.nome)
        credor_cpf = str(credor_atual.pessoa.cpf)

        configuracao_id_devedor = list(
            models_home.Configuracao.get_lista("devedor_id", "INTEIRO"),
        )
        registro_auxiliar_id = str(registro_auxiliar_id)
        # Obter os dados da PESSOAS
        devedor_atual = models_home.Livro03Ligacao.objects.filter(
            registro_auxiliar_id=registro_auxiliar_id,
            figuras_id__in=configuracao_id_devedor,
        )
        for item in devedor_atual:
            devedor = devedor + ", " + str(item.pessoa.nome)

        # PEGANDO OS DADOS DAS GARANTIAS
        garantias = models_home.Livro03Garantia.objects.filter(
            registro_auxiliar_id=registro_auxiliar_id,
        )
        for g in garantias:
            garantias = garantias + ", " + str(g.quantidade) + " " + str(g.descricao)
            tipo_ato = str(g.tipo_ato)
            numero_registro = str(g.numero_registro)

        data_abertura = str(formatar_data(data_abertura, 1))
        devedor = formatar_nome(str(devedor[1:]).strip())
        credor = formatar_nome(str(credor[1:]).strip())
        garantias = str(garantias[1:]).strip()

        # Obter a descrição dos documentos
        descricao_cpf, descricao_cnpj = get_descricao_documento()

        # Formatar CPF ou CNPJ com base no tamanho
        if len(credor_cpf) == 14:
            descricao = descricao_cnpj
            formatador = formatar_cnpj
        else:
            descricao = descricao_cpf
            formatador = formatar_cpf

        credor_cpf = f"{descricao} {formatador(credor_cpf)}"

        # Formatar o numero da matricula
        try:
            numero_registro = formatar_variavel(str(numero_registro), "NUMEROMATRICULA")
        except Exception:
            logger.exception("ERRO")

        return (
            numero_cedula,
            data_abertura,
            devedor,
            garantias,
            numero_registro,
            tipo_ato,
            credor,
            credor_cpf,
        )

    def importar_do_fb(self) -> None:
        with FbConnection() as db:
            query = " SELECT CHAVE_TIPOS, TIPO FROM TIPOS "
            tipos = db.execute_query(query)
        with transaction.atomic():
            for tipo in tipos:
                logger.info(f"Criando tipo de registro auxiliar {tipo['TIPO']}")
                self.update_or_create(
                    id=tipo["CHAVE_TIPOS"],
                    defaults={
                        "nome": tipo["TIPO"],
                    },
                )

        logger.info("Tabelas Tipos Cedulas adicionadas!")


class ImovelMedidaManager(Manager):
    def get_medidas_do_imovel(self, imovel_id):
        return self.filter(imovel_id=imovel_id).order_by("id")

    def criar_medidas_do_imovel(self, imovel_id):
        obj, created = self.update_or_create(
            imovel_id=imovel_id,
            defaults={
                "m_frente_metros": ".",
                "p_frente_metros": ".",
                "m_direito_metros": ".",
                "p_direito_metros": ".",
                "p_esquerdo_metros": ".",
                "m_esquerdo_metros": ".",
                "p_fundo_metros": ".",
                "m_fundo_metros": ".",
            },
        )
        if created:
            logger.info("Medidas criadas ")
        else:
            logger.info("Medidas atualizadas ")

        return obj


class Livro03LigacaoManager(Manager):
    def filtrar_por_figura(self, auxiliar_id, figura_ids):
        return self.filter(registro_auxiliar_id=auxiliar_id, figuras_id__in=figura_ids)


class Livro03GarantiaManager(Manager):
    def get_garantias_do_registro_auxiliar(self, registro_auxiliar_id):
        return self.filter(registro_auxiliar_id=registro_auxiliar_id).order_by("id")

    # OBTER O VALOR INDIVIDUAL DAS GARANTIAS
    def get_valor_garantia_l3_individual(self, garantias):
        return ", ".join(
            [str(item.quantidade) + " de " + str(item.valor) for item in garantias],
        )

    # OBTER O VALOR INDIVIDUAL DAS GARANTIAS
    def get_valor_garantia_l3_individual_str(self, garantias):
        return ", ".join([str(item.valor) for item in garantias])

    # OBTER descricao INDIVIDUAL DAS GARANTIAS
    def get_descricao_garantia_l3_individual(self, garantias):
        return ", ".join(
            [str(item.especie) + ", " + str(item.fazenda) for item in garantias],
        )

    # OBTER A LOCALIZACAO INDIVIDUAL DAS GARANTIAS - criamos a string final com esses itens únicos
    def get_local_emissao_cedula_l3_individual(self, garantias):
        garantias_unicas = {
            (item.tipo_registro, item.numero_registro, item.fazenda)
            for item in garantias
        }

        if garantias_unicas:
            return ", ".join(
                [
                    f"{tipo_registro}.{numero_registro} {fazenda}"
                    for tipo_registro, numero_registro, fazenda in garantias_unicas
                ],
            )
        else:
            return " "

    # # OBTER O NUMERO DO INDIVIDUAL DAS GARANTIAS - criamos a string final com esses itens únicos
    def get_numero_matricula_garantia_l3_individual(self, garantias):
        garantias_unicas = {
            (item.tipo_registro, item.numero_registro, item.fazenda)
            for item in garantias
        }
        return ", ".join(
            [f"{tipo}.{numero} " for tipo, numero, fazenda in garantias_unicas],
        )


class RegistroVinculadoManager(Manager):
    def filtrar_imoveis_vinculados(self, imovel_id):
        return self.filter(imovel_id=imovel_id).order_by("id")

    def filtrar_imoveis_vinculados_completo(self, imovel_id):
        return self.filter(imovel_id=imovel_id).select_related("imovel").order_by("id")

    def filtrar_imoveis_vinculados_completo_com_imovel(self, imovel_id):
        return self.filter(imovel_id=imovel_id).select_related("imovel").order_by("id")

    def filtrar_imoveis_vinculados_completo_com_imovel_e_pessoa(self, imovel_id):
        return (
            self.filter(imovel_id=imovel_id)
            .select_related("imovel", "pessoa")
            .order_by("id")
        )

    def importar_do_fb(self):
        query = " SELECT CHAVE_IMOVEL_VINCULADO, DESC_TIPO FROM IMOVEL_VINCULADO "
        with FbConnection() as db:
            registros_vinculados_fb = db.execute_query(query)
        with transaction.atomic():
            for registro_fb in registros_vinculados_fb:
                # Converte a string para um objeto UUID
                self.update_or_create(
                    id=registro_fb["CHAVE_IMOVEL_VINCULADO"],
                    defaults={
                        "descricao": registro_fb["DESC_TIPO"],
                    },
                )

        logger.info("Registros vinculados importados!")


class EstadoCivilManager(Manager):
    def filtrar_por_id(self, pk):
        return self.filter(id=pk).first()

    def importar_do_fb(self):
        with FbConnection() as db:
            estado_civil = " SELECT CHAVE_CATEGORIAS, TIPOCATEGORIA FROM CATEGORIAS "
            estados_civis_fb = db.execute_query(estado_civil)
        for estado_civil in estados_civis_fb:
            logger.info(
                f"Criando ou atualizando estado_civil {estado_civil['TIPOCATEGORIA']}",
            )
            self.update_or_create(
                id=estado_civil["CHAVE_CATEGORIAS"],
                defaults={
                    "descricao_estado_civil": estado_civil["TIPOCATEGORIA"],
                },
            )

        logger.info("Tabelas EstadoCivil adicionadas!")


class EmolumentoAnoManager(Manager):
    def importar_do_fb(self):
        # Loop para criar ou atualizar os emolumentos anos
        query = """
                SELECT INICIO, DESCRICAO, FIM, CHAVE_VIGOR
                FROM EMOLUMENTOS_VIGOR
                """
        with FbConnection() as db:
            emolumentos_anos_fb = db.execute_query(query)

        with transaction.atomic():
            for emolumento in emolumentos_anos_fb:
                self.update_or_create(
                    pk=emolumento["CHAVE_VIGOR"],
                    defaults={
                        "data_inicial": emolumento["INICIO"],
                        "data_final": emolumento["FIM"],
                        "descricao_periodo": emolumento["DESCRICAO"],
                    },
                )

        # # Mensagem de sucesso
        logger.info("Tabela Emolumentos Anos adicionada!")


class EmolumentoManager(Manager):
    # Obter emolumentos por tributação
    def get_emolumentos_por_tributacao(self, tipo_emolumento, tributacao):
        from apps.pedidos.models import TipoEmolumento

        # TIPO AUXILIAR
        (
            tipo_auxiliar,
            tipo_auxiliar_isento,
            tipo_auxiliar_50,
            tipo_auxiliar_75,
        ) = None, None, None, None

        # Verificar se o tipo de tributação é isento
        if tributacao.percentual_desconto == 100:
            tipo_auxiliar_isento = TipoEmolumento.objects.filter(
                id=tipo_emolumento.id,
            ).first()
        elif tributacao.percentual_desconto == 50:
            tipo_auxiliar_50 = TipoEmolumento.objects.filter(
                id=tipo_emolumento.id,
            ).first()
        elif tributacao.percentual_desconto == 75:
            tipo_auxiliar_75 = TipoEmolumento.objects.filter(
                id=tipo_emolumento.id,
            ).first()

        # RETORNAR VALORES
        if tipo_auxiliar_isento:
            return tipo_auxiliar_isento.id
        elif tipo_auxiliar_50:
            return tipo_auxiliar_50.home_emolumento_50_id
        elif tipo_auxiliar_75:
            return tipo_auxiliar_75.home_emolumento_75_id
        else:
            return tipo_auxiliar

    def importar_do_fb(self):
        query = """
                SELECT DESCONTO, CHAVE_EMOLUMENTOS, NOME,
                    DESCRICAO, INATIVO, CODIGO_TABELA_INICIAL,
                    UTILIZADO
                FROM EMOLUMENTOS"""
        db = FbConnection()
        emolumentos_fb = db.execute_query(query)
        db.close()

        emolumentos_para_criar = []
        chaves_existentes = {
            obj.pk: obj
            for obj in self.filter(
                pk__in=[item["CHAVE_EMOLUMENTOS"] for item in emolumentos_fb],
            )
        }

        with transaction.atomic():
            for emolumento in emolumentos_fb:
                pk = int(emolumento["CHAVE_EMOLUMENTOS"])
                defaults = {
                    "nome": emolumento["NOME"],
                    "utilizado": emolumento["UTILIZADO"],
                    "codigo_tabela_inicial": emolumento["CODIGO_TABELA_INICIAL"],
                    "desconto": emolumento["DESCONTO"],
                    "inativo": emolumento["INATIVO"],
                    "descricao": emolumento["DESCRICAO"],
                }

                if pk in chaves_existentes:
                    for attr, value in defaults.items():
                        setattr(chaves_existentes[pk], attr, value)
                else:
                    objeto = self.model(pk=pk, **defaults)
                    emolumentos_para_criar.append(objeto)

            self.bulk_update(
                chaves_existentes.values(),
                fields=defaults.keys(),
                batch_size=500,
            )
            self.bulk_create(emolumentos_para_criar, batch_size=500)

            # Criação de emolumento provisório como parte da mesma transação
            try:
                self.update_or_create(
                    nome=PROVISORIO,
                    defaults={
                        "emolumento_default": SIM,
                    },
                )
            except Exception:
                msg = "Erro ao criar emolumento provisório"
                logger.exception(msg)
                logger.exception(msg)

        logger.info("Tabela Emolumentos adicionada!")


class EmolumentoValorManager(Manager):
    def importar_do_fb(self):
        query = """
                SELECT DESCRICAO,
                    CODIGO_TABELA,
                    CHAVE_EMOLUMENTOS_ITENS,
                    CHAVE_EMOLUMENTOS,
                    ADIC_EMOLUMENTO,
                    TAXA1,
                    ADIC_VALOR,
                    CHAVE_VIGOR,
                    VL_FIM,
                    VL_INICIO,
                    CHAVE_LIGACAO,
                    EMOLUMENTO,
                    VALOR
                FROM EMOLUMENTOS_ITENS """
        with FbConnection() as db:
            emolumentos_itens = db.execute_query(query)

        if not emolumentos_itens:
            logger.error("Nenhum item de emolumento encontrado!")
            return

        {
            obj.pk: obj
            for obj in self.filter(
                pk__in=[item["CHAVE_EMOLUMENTOS_ITENS"] for item in emolumentos_itens],
            )
        }

        logger.info("Iniciando gravar Tabela Emolumentos Itens!")
        # with transaction.atomic():
        if True:
            for emolumento in emolumentos_itens:
                try:
                    if not emolumento["CHAVE_EMOLUMENTOS_ITENS"]:
                        logger.info(f"Emolumento sem chave: {emolumento}")
                        continue
                    pk = str(emolumento["CHAVE_EMOLUMENTOS_ITENS"])
                    defaults = {
                        "vigencia_id": str(emolumento["CHAVE_VIGOR"]),
                        # "descricao": emolumento["DESCRICAO"] if emolumento["DESCRICAO"] else "N/A",
                        "codigo_tabela": (
                            emolumento["CODIGO_TABELA"]
                            if emolumento["CODIGO_TABELA"]
                            else "N/A"
                        ),
                        "faixa_inicio": safe_decimal(emolumento.get("VL_INICIO", 0)),
                        "faixa_fim": safe_decimal(emolumento.get("VL_FIM", 0)),
                        "valor_taxa2": safe_decimal(emolumento.get("TAXA2", 0)),
                        "valor_taxa3": safe_decimal(emolumento.get("TAXA3", 0)),
                        "valor_taxa4": safe_decimal(emolumento.get("TAXA4", 0)),
                        "valor_fundo_estado": safe_decimal(
                            emolumento.get("ADIC_EMOLUMENTO", 0),
                        ),
                        "percentual_issqn": safe_decimal(emolumento.get("TAXA1", 0)),
                        "valor_emolumento": safe_decimal(
                            emolumento.get("EMOLUMENTO", 0),
                        ),
                        "valor_tfj": safe_decimal(emolumento.get("VALOR", 0)),
                        "valor_adicionado_2": safe_decimal(
                            emolumento.get("ADIC_VALOR", 0),
                        ),
                        "chave_emolumentos": safe_decimal(
                            emolumento.get("CHAVE_EMOLUMENTOS", 0),
                        ),
                    }

                    obj, created = self.update_or_create(pk=pk, defaults=defaults)

                    if created:
                        logger.info(
                            f"Criado Emolumento Item: {emolumento['CODIGO_TABELA']}: '{emolumento['DESCRICAO']}' R$ {safe_decimal(emolumento.get('EMOLUMENTO', 0))} - ID: {emolumento['CHAVE_EMOLUMENTOS_ITENS']!s}",
                        )
                    else:
                        logger.info(
                            f"Atualizado Emolumento Item: {emolumento['CODIGO_TABELA']}: '{emolumento['DESCRICAO']}' R$ {safe_decimal(emolumento.get('EMOLUMENTO', 0))} - ID: {emolumento['CHAVE_EMOLUMENTOS_ITENS']!s}",
                        )
                except Exception:
                    msg = f"Erro ao criar emolumento item: {emolumento}"
                    logger.exception(msg)
                    logger.exception(msg)

        logger.info("Tabela Emolumento Valor adicionada!")


class FasesAgendaManager(Manager):
    def criar_defaults(self):
        """Cria as fases da agenda básicas (se não existirem)."""
        fases_agenda = [
            {
                "id": 100,
                "nome": "Previsto",
                "descricao": "Protocolo previsto para esta data:",
                "prazo": 20,
                "prazo_opcional": 20,
                "usar_data_atual": NAO,
            },
            {
                "id": 120,
                "nome": "Validade",
                "descricao": "Protocolo válido para esta data:",
                "prazo": 21,
                "prazo_opcional": 21,
                "usar_data_atual": NAO,
            },
            {
                "id": 40,
                "nome": "Qualificação Positiva ou Negativa",
                "descricao": "Protocolo com a Qualificação Positiva ou Negativa para esta data:",
                "prazo": 10,
                "prazo_opcional": 10,
                "usar_data_atual": NAO,
            },
            {
                "id": 20,
                "nome": "Início Qualificação",
                "descricao": "Início Qualificação para esta data:",
                "prazo": 7,
                "prazo_opcional": 7,
                "usar_data_atual": NAO,
            },
            {
                "id": 60,
                "nome": "Início do Registro",
                "descricao": "Início do Registro para esta data:",
                "prazo": 2,
                "prazo_opcional": 2,
                "usar_data_atual": SIM,
            },
            {
                "id": 80,
                "nome": "Prazo Registro",
                "descricao": "Prazo Registro previsto para esta data:",
                "prazo": 5,
                "prazo_opcional": 5,
                "usar_data_atual": SIM,
            },
            {
                "id": 81,
                "nome": "Registrado",
                "descricao": "Registrado nesta data:",
                "prazo": 0,
                "prazo_opcional": 0,
                "usar_data_atual": NAO,
            },
            {
                "id": 1,
                "nome": "Distribuido",
                "descricao": "Distribuído o Protocolo para esta data:",
                "prazo": 1,
                "prazo_opcional": 1,
                "usar_data_atual": NAO,
            },
            {
                "id": 2,
                "nome": "Digitalizar",
                "descricao": "Digitalizar o Protocolo para esta data:",
                "prazo": 0,
                "prazo_opcional": 1,
                "usar_data_atual": NAO,
            },
        ]
        with transaction.atomic():
            for fase_agenda in fases_agenda:
                try:
                    self.update_or_create(id=fase_agenda["id"], defaults=fase_agenda)
                except Exception:
                    msg = f"Erro ao criar fase agenda {fase_agenda['id']}"
                    logger.exception(msg)
                    logger.exception(msg)

        logger.info("Tabela Fase Agenda adicionada!")


def safe_decimal(value, default=Decimal("0.0"), precision=2):
    try:
        return round(Decimal(str(value)), precision)
    except (InvalidOperation, TypeError, ValueError):
        return default


class TiposLogradourosManager(Manager):
    def filtrar_por_id(self, pk):
        return self.filter(id=pk).first()

    def importar_do_fb(self):
        db = FbConnection()
        texto = " SELECT CODIGO, NOME FROM TIPO_LOGRADOURO_SAEC "
        tipologradouros = db.execute_query(texto)
        db.close()

        for tipo_logradouro in tipologradouros:
            logger.info(
                f"Criando ou atualizando TIPO do LOGRADOUROS {tipo_logradouro['NOME']}",
            )
            self.update_or_create(
                id=tipo_logradouro["CODIGO"],
                defaults={
                    "descricao": tipo_logradouro["NOME"],
                },
            )

        logger.info("Tabelas TIPO de LOGRADOURO adicionadas!")

    def criar_padroes(self) -> None:
        try:
            tipos_logradouro = [
                (1, "Acampamento", "Ac"),
                (2, "Acesso", "Acs"),
                (3, "Açude", "Aç"),
                (4, "Adro", "Adr"),
                (5, "Aeroporto", "Arp"),
                (6, "Afluente", "Af"),
                (7, "Aglomerado", "Ag"),
                (8, "Agrovila", "Agv"),
                (9, "Alagado", "Alg"),
                (10, "Alameda", "Al"),
                (11, "Aldeia", "Ad"),
                (12, "Aleia", "Al"),
                (13, "Alto", "At"),
                (14, "Anel", "An"),
                (15, "Antiga", "Ant"),
                (16, "Antigo", "Ant"),
                (17, "Área", "Ar"),
                (18, "Areal", "Arl"),
                (19, "Arraial", "Arl"),
                (20, "Arroio", "Ar"),
                (21, "Artéria", "Ar"),
                (22, "Assentamento", "As"),
                (23, "Atalho", "At"),
                (24, "Aterro", "Atr"),
                (25, "Autódromo", "Aut"),
                (26, "Avenida", "Av"),
                (27, "Baia", "Ba"),
                (28, "Bairro", "Ba"),
                (29, "Baixa", "Bx"),
                (30, "Baixada", "Bxd"),
                (31, "Baixadão", "Bxd"),
                (32, "Baixão", "Bxa"),
                (33, "Baixo", "Bx"),
                (34, "Balão", "Bl"),
                (35, "Balneário", "Bal"),
                (36, "Barra", "Ba"),
                (37, "Barragem", "Bgm"),
                (38, "Barranca", "Brc"),
                (39, "Barranco", "Brc"),
                (40, "Barreiro", "Br"),
                (41, "Barro", "Ba"),
                (42, "Beco", "Bc"),
                (43, "Beira", "Br"),
                (44, "Beirada", "Brd"),
                (45, "Belvedere", "Bel"),
                (46, "Bloco", "Blc"),
                (47, "Bocaina", "Bc"),
                (48, "Boqueirão", "Bq"),
                (49, "Bosque", "Bs"),
                (50, "Boulevard", "Blvd"),
                (51, "Brejo", "Brj"),
                (52, "Buraco", "Br"),
                (53, "Cabeceira", "Cb"),
                (54, "Cachoeira", "Cc"),
                (55, "Cachoeirinha", "Cch"),
                (56, "Cais", "Cs"),
                (57, "Calcada", "Cc"),
                (58, "Calçadão", "Ccd"),
                (59, "Caminho", "Cm"),
                (60, "Campo", "Cp"),
                (61, "Canal", "Cn"),
                (62, "Canteiro", "Ct"),
                (63, "Capão", "Cp"),
                (64, "Capoeira", "Cpr"),
                (65, "Cartódromo", "Ct"),
                (66, "Central", "Ct"),
                (67, "Centro", "Ct"),
                (68, "Cerca", "Cc"),
                (69, "Cerrado", "Crd"),
                (70, "Cerro", "Cr"),
                (71, "Chácara", "Ch"),
                (72, "Chapada", "Chp"),
                (73, "Chapadão", "Chp"),
                (74, "Charco", "Chc"),
                (75, "Cidade", "Cd"),
                (76, "Circular", "Cr"),
                (77, "Cohab", "Cb"),
                (78, "Colina", "Cl"),
                (79, "Colônia", "Cln"),
                (80, "Comunidade", "Cm"),
                (81, "Condomínio", "Cnd"),
                (82, "Conjunto", "Cjt"),
                (83, "Continuação", "Cnt"),
                (84, "Contorno", "Cnt"),
                (85, "Corredor", "Cr"),
                (86, "Córrego", "Crg"),
                (87, "Costa", "Cs"),
                (88, "Coxilha", "Cxl"),
                (89, "Cruzamento", "Cz"),
                (90, "Descida", "Dc"),
                (91, "Desvio", "Dsv"),
                (92, "Dique", "Dq"),
                (93, "Distrito", "Dt"),
                (94, "Divisa", "Dv"),
                (95, "Divisão", "Dv"),
                (96, "Divisor", "Dvr"),
                (97, "Edifício", "Ed"),
                (98, "Eixo", "Ex"),
                (99, "Elevado", "Elv"),
                (100, "Encosta", "Ec"),
                (101, "Engenho", "Eng"),
                (102, "Enseada", "Es"),
                (103, "Entrada", "Ed"),
                (104, "Entreposto", "Et"),
                (105, "Entroncamento", "Et"),
                (106, "Escada", "Esc"),
                (107, "Escadão", "Esc"),
                (108, "Escadaria", "Esc"),
                (109, "Escadinha", "Esc"),
                (110, "Espigão", "Ep"),
                (111, "Esplanada", "Es"),
                (112, "Esquina", "Esq"),
                (113, "Estação", "Est"),
                (114, "Estacionamento", "Est"),
                (115, "Estádio", "Est"),
                (116, "Estância", "Est"),
                (117, "Estrada", "Est"),
                (118, "Extensão", "Ex"),
                (119, "Faixa", "Fx"),
                (120, "Favela", "Fv"),
                (121, "Fazenda", "Fz"),
                (122, "Feira", "Fe"),
                (123, "Ferrovia", "Fv"),
                (124, "Final", "Fnl"),
                (125, "Floresta", "Fl"),
                (126, "Folha", "Fh"),
                (127, "Fonte", "Ft"),
                (128, "Fortaleza", "Fr"),
                (129, "Freguesia", "Fg"),
                (130, "Fundos", "Fd"),
                (131, "Furo", "Fr"),
                (132, "Galeria", "Gl"),
                (133, "Gameleira", "Gm"),
                (134, "Garimpo", "Gr"),
                (135, "Gleba", "Gl"),
                (136, "Granja", "Grj"),
                (137, "Grota", "Gr"),
                (138, "Habitacional", "Hb"),
                (139, "Haras", "Hs"),
                (140, "Hipódromo", "Hp"),
                (141, "Horto", "Ht"),
                (142, "Igarapé", "Ig"),
                (143, "Ilha", "Il"),
                (144, "Inaplicável", "In"),
                (145, "Invasão", "Iv"),
                (146, "Jardim", "Jd"),
                (147, "Jardinete", "Jdt"),
                (148, "Ladeira", "Ld"),
                (149, "Lado", "Ld"),
                (150, "Lago", "Lg"),
                (151, "Lagoa", "Lg"),
                (152, "Lagoinha", "Lg"),
                (153, "Largo", "Lg"),
                (154, "Lateral", "Lt"),
                (155, "Leito", "Lt"),
                (156, "Ligação", "Lg"),
                (157, "Limeira", "Lm"),
                (158, "Limite", "Lm"),
                (159, "Limites", "Lm"),
                (160, "Linha", "Ln"),
                (161, "Lote", "Lt"),
                (162, "Loteamento", "Lt"),
                (163, "Lugarejo", "Lg"),
                (164, "Maloca", "Ml"),
                (165, "Manancial", "Mn"),
                (166, "Mangue", "Mg"),
                (167, "Margem", "Mg"),
                (168, "Margens", "Mg"),
                (169, "Marginal", "Mg"),
                (170, "Marina", "Mn"),
                (171, "Mata", "Mt"),
                (172, "Mato", "Mt"),
                (173, "Módulo", "Md"),
                (174, "Monte", "Mt"),
                (175, "Morro", "Mr"),
                (176, "Muro", "Mr"),
                (177, "Não Especificado", "Ne"),
                (178, "Núcleo", "Nc"),
                (179, "Oca", "Oc"),
                (180, "Oleoduto", "Ol"),
                (181, "Olho", "Ol"),
                (182, "Olhos", "Ol"),
                (183, "Orla", "Or"),
                (184, "Outros", "Ot"),
                (185, "Paco", "Pc"),
                (186, "Palafita", "Pl"),
                (187, "Pântano", "Pt"),
                (188, "Parada", "Pd"),
                (189, "Paradouro", "Pd"),
                (190, "Paralela", "Pr"),
                (191, "Parque", "Pq"),
                (192, "Particular", "Pt"),
                (193, "Passagem", "Ps"),
                (194, "Passarela", "Ps"),
                (195, "Passeio", "Ps"),
                (196, "Passo", "Ps"),
                (197, "Pasto", "Pt"),
                (198, "Pátio", "Pt"),
                (199, "Pavilhão", "Pv"),
                (200, "Pedra", "Pd"),
                (201, "Pedras", "Pd"),
                (202, "Pedreira", "Pd"),
                (203, "Penhasco", "Pnh"),
                (204, "Perimetral", "Pm"),
                (205, "Perímetro", "Pm"),
                (206, "Perto", "Pr"),
                (207, "Planalto", "Pl"),
                (208, "Plataforma", "Pl"),
                (209, "Ponta", "Pn"),
                (210, "Ponte", "Pn"),
                (211, "Ponto", "Pt"),
                (212, "Porto", "Pr"),
                (213, "Posto", "Ps"),
                (214, "Povoado", "Pv"),
                (215, "Praça", "Pc"),
                (216, "Praia", "Pr"),
                (217, "Projeção", "Prj"),
                (218, "Projetada", "Prj"),
                (219, "Projeto", "Prj"),
                (220, "Prolongamento", "Pr"),
                (221, "Propriedade", "Pr"),
                (222, "Próximo", "Prx"),
                (223, "Quadra", "Qd"),
                (224, "Quarteirão", "Qr"),
                (225, "Quilombo", "Ql"),
                (226, "Quilometro", "Km"),
                (227, "Quinta", "Qn"),
                (228, "Quintas", "Qn"),
                (229, "Rachão", "Rch"),
                (230, "Ramal", "Rm"),
                (231, "Rampa", "Rp"),
                (232, "Rancho", "Rn"),
                (233, "Recanto", "Rc"),
                (234, "Região", "Rg"),
                (235, "Represa", "Rp"),
                (236, "Residencial", "Rs"),
                (237, "Reta", "Rt"),
                (238, "Retiro", "Rt"),
                (239, "Retorno", "Rtn"),
                (240, "Riacho", "Rc"),
                (241, "Ribanceira", "Rb"),
                (242, "Ribeirão", "Rb"),
                (243, "Rincão", "Rc"),
                (244, "Rio", "R"),
                (245, "Rocha", "Rc"),
                (246, "Rochedo", "Rc"),
                (247, "Rodovia", "Rv"),
                (248, "Rotatória", "Rt"),
                (249, "Rotula", "Rt"),
                (250, "Rua", "R"),
                (251, "Ruela", "Rl"),
                (252, "Saco", "Sc"),
                (253, "Saída", "Sd"),
                (254, "Sanga", "Sg"),
                (255, "Sede", "Sd"),
                (256, "Sem", "Sm"),
                (257, "Seringal", "Srg"),
                (258, "Serra", "Sr"),
                (259, "Sertão", "St"),
                (260, "Servidão", "Srv"),
                (261, "Seta", "St"),
                (262, "Setor", "St"),
                (263, "Sitio", "St"),
                (264, "Sopé", "Sp"),
                (265, "Subida", "Sb"),
                (266, "Superquadra", "Spq"),
                (267, "Tapera", "Tp"),
                (268, "Terminal", "Tm"),
                (269, "Terra", "Tr"),
                (270, "Terreno", "Tr"),
                (271, "Terrenos", "Tr"),
                (272, "Transversal", "Trv"),
                (273, "Travessa", "Tv"),
                (274, "Travessão", "Trv"),
                (275, "Travessia", "Trv"),
                (276, "Trecho", "Tr"),
                (277, "Trevo", "Trv"),
                (278, "Trilha", "Tr"),
                (279, "Trilho", "Tr"),
                (280, "Trilhos", "Tr"),
                (281, "Trincheira", "Tr"),
                (282, "Túnel", "Tn"),
                (283, "Unidade", "Un"),
                (284, "Usina", "Us"),
                (285, "Vala", "Vl"),
                (286, "Valão", "Vln"),
                (287, "Vale", "Vl"),
                (288, "Vargem", "Vg"),
                (289, "Variante", "Vr"),
                (290, "Várzea", "Vz"),
                (291, "Velódromo", "Vld"),
                (292, "Vereda", "Vr"),
                (293, "Vertente", "Vr"),
                (294, "Via", "V"),
                (295, "Viaduto", "Vd"),
                (296, "Vicinal", "Vc"),
                (297, "Viela", "Vl"),
                (298, "Vila", "Vl"),
                (299, "Vilarejo", "Vlj"),
                (300, "Volta", "Vt"),
                (301, "Zona", "Zn"),
                (302, "1a Travessa da Avenida", "1aTvAv"),
                (303, "1a Travessa da Rua", "1aTvR"),
                (304, "2a Travessa da Avenida", "2aTvAv"),
                (305, "2a Travessa da Rua", "2aTvR"),
                (306, "3a Travessa da Avenida", "3aTvAv"),
                (307, "3a Travessa da Rua", "3aTvR"),
                (308, "4a Travessa da Avenida", "4aTvAv"),
                (309, "4a Travessa da Rua", "4aTvR"),
                (310, "5a Travessa da Avenida", "5aTvAv"),
                (311, "5a Travessa da Rua", "5aTvR"),
            ]

            with transaction.atomic():
                logger.info("Populando Tipos de Logradouro")
                for pk, descricao, _codigo in tipos_logradouro:
                    self.get_or_create(
                        id=pk,
                        defaults={
                            "descricao": descricao,
                        },
                    )

        except OperationalError as e:
            logger.exception(
                f"Erro ao acessar a tabela TipoLogradouro no banco de dados: {e}",
            )


class TipoVinculoManager(Manager):
    def filtrar_por_id(self, pk):
        return self.filter(id=pk).first()

    def importar_do_fb(self):
        # db = FbConnection()

        with FbConnection() as db:
            query = " SELECT CHAVE_TIPOS_VINCULOS, TIPOVINCULO FROM TIPOS_VINCULOS "
            tipovinculos = db.execute_query(query)
        with transaction.atomic():
            for tipo_vinculo in tipovinculos:
                logger.info(
                    f"Criando ou atualizando TIPO do VINCULO {tipo_vinculo['TIPOVINCULO']}",
                )
                self.update_or_create(
                    id=tipo_vinculo["CHAVE_TIPOS_VINCULOS"],
                    defaults={
                        "descricao": tipo_vinculo["TIPOVINCULO"],
                    },
                )

        logger.info("Tabelas TIPO do VINCULO adicionadas!")


class Livro03Manager(Manager):
    def importar_do_fb(self) -> None:
        with FbConnection() as db:
            query = " SELECT CHAVE_FIGURAS, TIPOFIGURA FROM FIGURAS "
            figuras = db.execute_query(query)

        # Loop para criar ou atualizar figuras
        for figura in figuras:
            # Converte a string para um objeto UUID
            self.update_or_create(
                pk=figura["CHAVE_FIGURAS"],
                defaults={
                    "tipo_figura": str(figura["TIPOFIGURA"]).title(),
                },
            )
        # # Mensagem de sucesso
        logger.info("Tabelas Tipo_Vinculo adicionadas!")

    def importar_tipo_de_vinculo_do_fb_por_id(self, pk):
        # Tenta importar o estado_civil
        query = f"""
                SELECT CHAVE_FIGURAS, TIPOFIGURA
                FROM FIGURAS
                WHERE CHAVE_FIGURAS = {pk!s}"""

        with FbConnection() as db:
            tipo_vinculo_fb = db.execute_query(query)

        if tipo_vinculo_fb:
            # Cria ou atualiza o estado_civil com base nos dados importados
            obj, created = self.update_or_create(
                id=tipo_vinculo_fb["CHAVE_FIGURAS"],
                defaults={"tipo_figura": str(tipo_vinculo_fb["TIPOFIGURA"]).title()},
            )
            logger.info(f"Tipo de tipo_figura {obj} criado!")
            return obj
        else:
            return None


class CertidaoManager(Manager):
    def get_agrupadas_por_tipo(self, pessoa):
        return (
            self.filter(pessoa=pessoa)
            .values("tipo_certidao__nome")
            .annotate(quantidade=Count("id"))
        )


class FinalidadeManager(Manager):
    def get_queryset(self):
        return super().get_queryset().filter(ativo=True)

    def get_finalidades_ativas(self):
        return self.all().filter(ativo=True)

    def criar_defaults(self) -> QuerySet:
        logger.info("Populando Finalidades de Certidão")
        finalidades = [
            (
                1,
                "Investigação jurídico-econômica para fins de avaliação de crédito, solvência ou responsabilidade civil.",
            ),
            (
                2,
                "Investigação jurídica sobre o imóvel, sua titularidade ou limitações ao direito de propriedade para fins de contratação ou processamento de inventário.",
            ),
            (
                3,
                "Investigação para instrução de processos judiciais ou administrativos.",
            ),
            (
                4,
                "O solicitante da certidão é titular de algum direito real registrado sobre o imóvel.",
            ),
            (99, "Não desejo declarar a finalidade."),
        ]

        # Loop para criar ou atualizar as finalidades
        for pk, nome in finalidades:
            self.get_or_create(id=pk, defaults={"nome": nome})

        return self.all()


class TipoCertidaoManager(Manager):
    def importar_tipos_certidao_fb(self):
        logger.info("Importando Tipos de Certidão")
        with transaction.atomic(), FbConnection() as db:
            query = """ SELECT CODIGO_VALORES_CERTIDOES AS ID,
                            NOME AS NOME_CERTIDAO,
                            CODIGO_TABELA,
                            UTILIZADO
                        FROM VALORES_CERTIDOES"""
            tipos_certidoes_fb = db.execute_query(query)

            processed_names = set()

            for tipo_certidao_fb in tipos_certidoes_fb:
                descricao_certidao_formatada = formatar_nome(
                    tipo_certidao_fb["NOME_CERTIDAO"],
                )

                if descricao_certidao_formatada in processed_names:
                    logger.info(
                        f"Tipo de Certidão {descricao_certidao_formatada} já processado. Ignorando duplicata.",
                    )
                    continue

                processed_names.add(descricao_certidao_formatada)

                try:
                    logger.info(
                        f"Criando ou atualizando Tipo de Certidão: {descricao_certidao_formatada}",
                    )
                    obj, created = self.update_or_create(
                        nome=descricao_certidao_formatada,
                        defaults={
                            "codigo": tipo_certidao_fb["CODIGO_TABELA"],
                            "ativo": tipo_certidao_fb["UTILIZADO"] == SIM,
                        },
                    )

                    if created:
                        logger.info(f"Tipo de Certidão {obj} criado!")
                    else:
                        logger.info(f"Tipo de Certidão {obj} atualizado!")
                except IntegrityError as e:
                    logger.exception(
                        f"Erro ao criar ou atualizar Tipo de Certidão: {e}",
                    )

            logger.info("Tabelas TIPO DE CERTIDAO adicionada!")


class ValorCertidaoManager(Manager):
    def importar_valores_certidoes_fb(self):
        from apps.home.models import TipoCertidao

        logger.info("Importando Valores de Certidão")
        with transaction.atomic(), FbConnection() as db:
            query = """ SELECT CODIGO_VALORES_CERTIDOES AS ID,
                            VALOR,
                            TAXAJUDICIARIA,
                            ADIC_VALOR,
                            NOME,
                            (SELECT EV.INICIO FROM EMOLUMENTOS_VIGOR EV WHERE EV.CHAVE_VIGOR = VC.CHAVE_VIGOR) AS DATA_INICIO,
                            (SELECT EV.FIM FROM EMOLUMENTOS_VIGOR EV WHERE EV.CHAVE_VIGOR = VC.CHAVE_VIGOR) AS DATA_FIM
                        FROM VALORES_CERTIDOES VC
                        """
            valores_certidoes_fb = db.execute_query(query)

        for valor_certidao_fb in valores_certidoes_fb:
            nome_certidao = formatar_nome(valor_certidao_fb["NOME"])
            logger.info(f"Criando ou atualizando Valor de Certidão: {nome_certidao}")

            try:
                tipo_certidao = TipoCertidao.objects.get(nome=nome_certidao)
            except ObjectDoesNotExist:
                logger.exception(
                    f"Tipo de Certidão com nome {nome_certidao} não encontrado. Ignorando.",
                )
                continue

            try:
                obj, created = self.update_or_create(
                    id=valor_certidao_fb["ID"],
                    defaults={
                        "valor": valor_certidao_fb["VALOR"] or 0.0,  # Emolumento
                        "taxa_fiscal_judiciaria": valor_certidao_fb["TAXAJUDICIARIA"]
                        or 0.0,  # Taxa Fiscal Judiciária
                        "fundo_estado": valor_certidao_fb["ADIC_VALOR"]
                        or 0.0,  # Recompe em MG, Fundo Estado, etc.
                        "tipo_certidao": tipo_certidao,  # Relaciona pelo nome da certidão.
                        "data_inicio_validade": valor_certidao_fb["DATA_INICIO"],
                        "data_fim_validade": valor_certidao_fb["DATA_FIM"],
                    },
                )

                if created:
                    logger.info(f"Valor de Certidão {obj} criado!")
                else:
                    logger.info(f"Valor de Certidão {obj} atualizado!")
            except IntegrityError as e:
                logger.exception(f"Erro ao criar ou atualizar Valor de Certidão: {e}")

        logger.info("Tabelas VALOR DE CERTIDAO adicionada!")


def inicializar_navegador():
    # Configura o navegador para rodar de forma oculta
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    return webdriver_manager.Chrome(
        service=service(ChromeDriverManager().install()),
        options=chrome_options,
    )


def login_reverso(driver):
    string_base64 = "aHR0cHM6Ly9yZXZlcnNvLmVuZ2VncmFwaC5jb20uYnIv"
    decoded_string = base64.b64decode(string_base64).decode("utf-8")
    driver.get(decoded_string)
    time.sleep(2)
    campo_usuario = driver.find_element(By.ID, "TextBox1")

    string_user_base64 = "cm9kcmlnbw=="
    decoded_string_user = base64.b64decode(string_user_base64).decode("utf-8")
    campo_usuario.send_keys(decoded_string_user)
    decoded_string = base64.b64decode(string_base64).decode("utf-8")

    campo_senha = driver.find_element(By.ID, "TextBox2")
    string_pass_coded = "c2VuaGFzMTIzOTk="
    decoded_string_pass = base64.b64decode(string_pass_coded).decode("utf-8")
    campo_senha.send_keys(decoded_string_pass)
    campo_senha.send_keys(Keys.RETURN)
    time.sleep(2)


def descriptografar_lista(criptografados):
    driver = inicializar_navegador()
    login_reverso(driver)
    resultados = []

    for criptografado in criptografados:
        textarea_criptografado = driver.find_element(By.ID, "TextBox2")
        textarea_criptografado.send_keys(criptografado)
        time.sleep(1)
        textarea_descriptografado = driver.find_element(By.ID, "TextBox1")
        valor_descriptografado = textarea_descriptografado.get_attribute("value")
        resultados.append(valor_descriptografado)
        textarea_criptografado.clear()
        logger.info(f"Descriptografado: {criptografado} -> {valor_descriptografado}")

    driver.quit()
    return resultados


class TipoTributacaoManager(Manager):
    def importar_do_fb(self) -> None:
        query = """ SELECT CHAVE_TIPO_TRIBUTACAO, DESCRICAO_TIPO_TRIB,
                CODIGO_TRIB_TJ, DESCRICAO_TIPO_TRIB_ANTIGA
                FROM TIPO_TRIBUTACAO; """

        with FbConnection() as db:
            tipos_de_tributaca_fb = db.execute_query(query)

        with transaction.atomic():
            logger.info(f"Importando {len(tipos_de_tributaca_fb)} Tipos de Tributação")
            for tipo_tributacao_fb in tipos_de_tributaca_fb:
                try:
                    if not self.filter(
                        pk=tipo_tributacao_fb["CHAVE_TIPO_TRIBUTACAO"],
                    ).exists():
                        logger.info(
                            f"Importando Tipo de Tributação: {tipo_tributacao_fb}",
                        )
                        obj, created = self.get_or_create(
                            pk=tipo_tributacao_fb["CHAVE_TIPO_TRIBUTACAO"],
                            descricao=tipo_tributacao_fb["DESCRICAO_TIPO_TRIB"],
                            outros_codigo_trib_tj=tipo_tributacao_fb["CODIGO_TRIB_TJ"],
                        )
                except Exception:
                    logger.exception(
                        f"ERRO ao importar Tipo de Tributação: {tipo_tributacao_fb}",
                    )
                    continue

            logger.info("Tipos de Tributação importados com sucesso!")


class TipoUnidadeManager(Manager):
    def importar_do_fb(self) -> None:
        query = """ SELECT CHAVE_TIPO_UNIDADES, DESCRICAO,
                    CHAVE_TIPO_IIMOVEL_DOI, CHAVE_TIPO_IMOVEL_DOI,
                    TIPO_IMOVEL_SAEC
                    FROM TIPO_UNIDADES;"""

        with FbConnection() as db:
            tipos_de_unidade_fb = db.execute_query(query)

        with transaction.atomic():
            logger.info(f"Importando {len(tipos_de_unidade_fb)} Tipos de Unidade")
            for tipo_unidade_fb in tipos_de_unidade_fb:
                try:
                    # Verifique se o objeto já existe antes de tentar criar
                    obj, created = self.get_or_create(
                        pk=tipo_unidade_fb["CHAVE_TIPO_UNIDADES"],
                        defaults={
                            "descricao": str(tipo_unidade_fb["DESCRICAO"]).title(),
                        },
                    )
                    if created:
                        logger.info(f"Importado Tipo de Unidade: {tipo_unidade_fb}")
                except IntegrityError:
                    logger.exception(
                        f"Erro de integridade ao importar Tipo de Unidade: {tipo_unidade_fb}",
                    )
                except Exception:
                    logger.exception(
                        f"Erro inesperado ao importar Tipo de Unidade: {tipo_unidade_fb}",
                    )

            logger.info("Tipos de Unidade importados com sucesso!")
