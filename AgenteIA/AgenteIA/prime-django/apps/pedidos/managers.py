import logging
from datetime import MAXYEAR, date, datetime, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING

from django.db import models
from django.db.models import Count, DecimalField, Sum
from django.utils import timezone

from core.utils.firebird_utils import FbConnection

if TYPE_CHECKING:
    from apps.pedidos.models import Emolumento, Tabela, TipoEmolumento

logger = logging.getLogger(__name__)

logger.debug(f"Iniciando {__name__}")


class ImovelManager(models.Manager):
    def ativos(self):
        return self.filter(ativo=True)

    def total_valor_atos(self):
        return (
            self.aggregate(
                total=models.Sum("atos__ato_praticavel__ato_praticavel_valor"),
            )["total"]
            or 0
        )

    def get_ultimo_imovel(self):
        return self.latest("id")


class PedidoManager(models.Manager):
    def get_pedido_por_numero(self, numero_pedido: int) -> models.QuerySet:
        resultado = self.get(numero=numero_pedido)
        if resultado:
            return resultado
        else:
            msg = "Nenhum pedido encontrado para o número fornecido."
            raise ValueError(msg)

    def get_pedido_por_id(self, pedido_id: int) -> models.QuerySet:
        resultado = self.get(id=pedido_id)
        if resultado:
            return resultado
        else:
            msg = "Nenhum pedido encontrado para o ID fornecido."
            raise ValueError(msg)

    def listar_numeros_nao_usados(self) -> list:
        # verifica os numeros não usados a partir do 0 até o max na coluna numero_pedido do model Pedido
        return [
            i
            for i in range(1, self.all().count() + 2)
            if not self.filter(numero=i).exists()
        ]


class PedidoFirebirdManager(models.Manager):
    def get_numero_proximo_pedido_fb(self, db: FbConnection) -> int:
        from apps.pedidos.firebird import get_prox_numero_do_pedido_fb

        return get_prox_numero_do_pedido_fb(db=db)


class TabelaManager(models.Manager):
    def get_queryset(self) -> models.QuerySet:
        """
        Sobrescreve o método padrão get_queryset para retornar um queryset filtrado.

        Este método pessoaliza o comportamento do queryset padrão do modelo associado,
        retornando apenas os registros onde o campo 'data_inicio_validade' é menor ou igual
        (less than or equal to) à data atual. Isso é particularmente útil para restringir
        a consulta aos registros que são considerados válidos ou ativos baseados na data de
        início de sua validade.

        Returns
        -------
            QuerySet: Um QuerySet do Django contendo os registros que satisfazem o critério
                    de filtro, isto é, registros cuja 'data_inicio_validade' é hoje ou
                    uma data anterior.

        """
        return (
            super()
            .get_queryset()
            .filter(data_inicio_validade__lte=timezone.now().date())
        )

    def nova_tabela(self, tabela, inicio_validade=None):
        inicio_validade = inicio_validade or timezone.now().date() + timedelta(days=1)
        from apps.pedidos.models import Emolumento, Tabela

        # Atualiza a data de fim de validade da tabela anterior
        tabela_anterior = self.get_tabela_vigente()
        if tabela_anterior:
            # Define a data de fim da tabela anterior como um dia antes da nova data de início
            tabela_anterior.data_fim_validade = inicio_validade - timedelta(days=1)
            tabela_anterior.save()

        nova_tabela = Tabela.objects.create(
            data_inicio_validade=inicio_validade,
            data_fim_validade=date(MAXYEAR, 12, 31),
        )
        for valor in tabela.custas_tabela.all():
            Emolumento.objects.create(
                ato_praticavel=valor.ato_praticavel,
                tabela=nova_tabela,
                valor=valor.valor,
                faixa_valor_inicio=valor.faixa_valor_inicio,
                faixa_valor_fim=valor.faixa_valor_fim,
                taxa_fiscal_judiciaria=valor.taxa_fiscal_judiciaria,
                fundo1_valor=valor.fundo_estado,
                issqn_percentual=valor.issqn_percentual,
            )
        return nova_tabela

    def get_emolumento(
        self,
        valor_documento: Decimal,
        tipo_emolumento: "TipoEmolumento",
        data_pratica_ato: date | None = None,
    ) -> "Emolumento":
        """Calcula o valor do emolumento com base na data do ato, no valor do documento e no tipo de ato."""
        logger.debug(
            f"Iniciando cálculo do emolumento para o valor do documento: {valor_documento}",
        )
        try:
            # Verifica e converte a data do ato para o formato datetime.date
            data_pratica_ato = self._get_data_pratica_ato(data_pratica_ato)
            # Encontra a tabela correspondente à data do ato
            tabela = self.get_tabela(data_pratica_ato)
            # Encontra o valor do emolumento na tabela
            return self._get_emolumento_da_tabela(
                tabela,
                tipo_emolumento,
                valor_documento,
            )
        except ValueError as ve:
            logger.exception(f"Erro de valor ao calcular o emolumento: {ve}")
            raise
        except Exception as e:
            logger.exception(f"Erro inesperado ao calcular o emolumento: {e}")
            raise

    def _get_data_pratica_ato(self, data_ato: str | None) -> datetime.date:
        """Verifica e converte a data do ato para o formato datetime.date."""
        if not data_ato:
            logger.debug(
                "Data da prática do ato não fornecida. Utilizando a data atual.",
            )
            return datetime.now(tz=datetime.UTC).date()

        logger.debug(f"Data da prática do ato fornecida: {data_ato}")
        if isinstance(data_ato, str):
            try:
                data_ato = datetime.fromisoformat(data_ato).date()
                logger.info(
                    f"Data da prática do ato convertida para objeto date: {data_ato}",
                )
            except ValueError:
                msg = f"Formato de data inválido: {data_ato}"
                logger.exception(msg)
                raise ValueError(msg) from None
        return data_ato

    def get_tabela(self, data_ato: date) -> "Tabela":
        """
        Encontra a tabela correspondente à data do ato.
        Se mais de uma tabela corresponder aos critérios, a mais recente será selecionada e um alerta será registrado.
        """
        tabelas = self.filter(
            data_inicio_validade__lte=data_ato,
            data_fim_validade__gte=data_ato,
        ).order_by("-data_inicio_validade")

        if not tabelas:
            msg = f"Nenhuma tabela encontrada para a data do ato: {data_ato}"
            logger.error(msg)
            raise ValueError(msg)

        tabela = tabelas.first()

        if tabelas.count() > 1:
            logger.warning(
                f"Mais de uma tabela encontrada para a data {data_ato}. Selecionando a mais recente: {tabela}",
            )
        else:
            logger.info(f"Tabela encontrada para a data {data_ato}: {tabela}")

        return tabela

    def _get_emolumento_da_tabela(
        self,
        tabela: "Tabela",
        tipo_emolumento: "TipoEmolumento",
        valor_documento: Decimal,
    ) -> "Emolumento":
        """
        Encontra o valor do emolumento na tabela, garantindo que o emolumento mais recente seja selecionado.

        Args:
        ----
            tabela (Tabela): Instância da tabela que contém os emolumentos.
            tipo_emolumento (TipoEmolumento): Tipo do emolumento a ser buscado.
            valor_documento (Decimal): Valor do documento que será utilizado para buscar o emolumento correspondente.

        Returns:
        -------
            Emolumento: Emolumento encontrado de acordo com os critérios especificados.

        Raises:
        ------
            ValueError: Se nenhum emolumento correspondente for encontrado na tabela.

        """
        # Filtra os emolumentos na tabela com base no tipo e na faixa de valor do documento
        emolumentos = tabela.emolumentos.filter(
            tipo_emolumento=tipo_emolumento,
            faixa_valor_inicio__lte=valor_documento,
            faixa_valor_fim__gte=valor_documento,
        )

        # Adiciona log de debug com os critérios de busca
        logger.debug(
            "Critérios de busca:\n"
            f"tabela={tabela},\n"
            f"tipo_emolumento={tipo_emolumento},\n"
            f"faixa_valor_inicio__lte={valor_documento},\n"
            f"faixa_valor_fim__gte={valor_documento},\n",
        )

        # Verifica se existe algum emolumento correspondente
        if emolumentos.exists():
            emolumentos_ids = list(emolumentos.values_list("id", flat=True))
            # Adiciona log com os IDs dos emolumentos encontrados
            logger.debug(f"Emolumentos encontrados (IDs): {emolumentos_ids}")

            # Se houver mais de um, emite um aviso e seleciona o mais recente
            if emolumentos.count() > 1:
                logger.warning(
                    f"Mais de um emolumento correspondente. Selecionando o mais recente: {emolumentos.last()}",
                )
            emolumento = emolumentos.last()
            logger.info(f"Emolumento correspondente encontrado: \n{emolumento}")
            return emolumento
        else:
            # Se não houver emolumento correspondente, prepara os critérios para debug e levanta um erro
            criterios = {
                "tabela": tabela,
                "tipo_emolumento": tipo_emolumento,
                "faixa_valor_inicio__lte": valor_documento,
                "faixa_valor_fim__gte": valor_documento,
            }
            msg = f"""
                A tabela selecionada não possui um emolumento que corresponde aos critérios fornecidos:
                {criterios}.
                Verifique se a tabela está correta e se deveria conter um emolumento com os parâmetros informados."""
            logger.error(msg)
            # raise ValueError(msg)

        return None


class AtosQuerySet(models.QuerySet):
    def get_dados_em_dict(self):
        """Processa os dados dos atos e devolve uma lista com as informações necessárias para exportar."""
        return [ato.to_dict() for ato in self]


class AtoManager(models.Manager):
    def get_queryset(self):
        return AtosQuerySet(self.model, using=self._db)

    def get_atos_principais(self, pedido_id) -> models.QuerySet:
        return self.filter(pedido_id=pedido_id, ato_id__isnull=True)

    def get_atos_complementares(self, ato_principal_id) -> models.QuerySet:
        return self.filter(ato_id=ato_principal_id)

    def get_atos_orfaos(self, pedido_id) -> models.QuerySet:
        atos_ids = self.filter(pedido_id=pedido_id).values_list("id", flat=True)
        return self.filter(pedido_id=pedido_id, ato_id__isnull=False).exclude(
            ato_id__in=atos_ids,
        )

    def get_atos_principais_agrupados(self, pedido_id) -> models.QuerySet:
        atos_principais = self.get_atos_principais(pedido_id)
        # Supondo que 'nome' e 'tipo_emolumento' são campos do modelo Ato
        return (
            atos_principais.values("ato_praticavel_id", "tipo_emolumento_id")
            .annotate(
                quantidade=Count("id"),
                total_emolumento=Sum(
                    "valor_titulo",
                    output_field=DecimalField(localize=True),
                ),  # Assumindo que 'valor_titulo' pode ser um campo relevante
            )
            .order_by("ato_praticavel_id", "tipo_emolumento_id")
        )

    def get_atos_com_complementares(self, pedido_id) -> list:
        resultado = []
        atos_principais = self.filter(pedido_id=pedido_id, ato_id__isnull=True)
        for ato_principal in atos_principais:
            complementares = self.filter(ato_id=ato_principal.id)
            resultado.append(
                {"principal": ato_principal, "complementares": complementares},
            )
        return resultado
