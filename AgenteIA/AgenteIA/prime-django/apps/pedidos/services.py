import decimal
import logging
from decimal import ROUND_HALF_UP, Decimal

import requests
from django.apps import apps
from django.conf import settings
from django.db import transaction
from django.db.models import QuerySet

from apps.cartorios.models import Usuario as User
from apps.home.models import models_home
from apps.home.padroes import ARQUIVAMENTO, PRENOTACAO, PROVISORIO
from apps.pedidos import firebird, models
from core.utils.firebird_utils import FbConnection

logger = logging.getLogger(__name__)

logger.debug(f"Iniciando {__name__}")

decimal.getcontext().prec = 6  # Precisão total de dígitos
decimal.getcontext().rounding = decimal.ROUND_HALF_UP


# Atualizar a observação de um pedido específico
def atualizar_observacao(itens_atos):
    # Define atos para retirar como um set para otimizar a operação de verificação "not in"
    atos_retirar = {PRENOTACAO, PROVISORIO, ARQUIVAMENTO}

    # Utiliza list comprehension para construir a observação de maneira eficiente
    try:
        observacao = ", ".join(
            [
                f"{item.ato_praticavel.nome} {item.imovel_tipo_registro.nome[0] or ''} {item.imovel_numero_registro or ''}".strip()
                for item in itens_atos
                if item.ato_praticavel.nome not in atos_retirar
            ],
        )
    except Exception:
        observacao = ""
        logger.exception("Erro ao tentar atualizar a observação do pedido")

    return str(observacao).upper()


class PedidoProtocolarNoFirebirdService:
    @staticmethod
    def protocolar_pedido_no_fb(
        pedido_fb: dict,
        pedido_item_fb: dict,
        pedido: "models.Pedido",
        user: User,
        db: FbConnection,
    ) -> None:
        try:
            numero_protocolo, protocolo_id = firebird.gravar_protocolo_firebird(
                pedido_id=pedido_fb["CHAVE_PEDIDOS"],
                titulo_id=0,
                observacao=pedido_fb["OBSERVACAO"],
                db=db,
            )
        except Exception:
            logger.exception("ERRO ao tentar protocolar o pedido no Firebird")
            raise

        # FIXOS - CAIXA
        Decimal(pedido_fb.get("total_pedido", 59.58)).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )

        # GRAVAR ANDAMENTO
        try:
            firebird.gravar_andamento_do_protocolo_no_fb(
                protocolo_id=protocolo_id,
                funcionario_id=user.pk,
                servico_id=models_home.TipoAndamento.get_prenotacao_id(),
                db=db,
            )
        except Exception:
            logger.exception(
                f"ERRO ao tentar gravar o andamento no Firebird para o protocolo {numero_protocolo}",
            )
            raise

        # COMENTANDO PARA QUE NO CAIXA O CLIENTE ESCOLHA A FORMA DE PAGAMENTO EM TELA SEPARADA
        # GRAVAR CAIXA
        # try:
        #     firebird.gravar_caixa_do_protocolo_no_firebird(
        #         pedido_id=pedido_fb["CHAVE_PEDIDOS"],
        #         valor=valor_transacao,
        #         funcionarios_id=user.id,
        #         descricao=str(
        #             "'" + "Prenotação - " + str(pedido.apresentante.nome) + "'",
        #         ),
        #         db=db,
        #     )
        # except Exception:
        #     logger.exception(
        #         f"ERRO ao tentar gravar o caixa no Firebird para o protocolo {numero_protocolo}",
        #     )
        #     raise  # repassa a exceção para o chamador para garantir o rollback

        # GRAVAR SELO
        if pedido_item_fb:
            try:
                # ALFENAS ADICIONAR CAMPOS PARA O SQLSERVER
                cartorio_model = apps.get_model("cartorios", "Cartorio")

                usar_selo_sql_server = cartorio_model.objects.all().values_list(
                    "usar_selo_sql_server",
                    flat=True,
                )[0]
                # SELAR NO SQL SERVER PROTOCOLO
                if usar_selo_sql_server == "S":
                    codigo_internet_firebird = ""

                    # PEGAR OS DADOS DA PRENOTACAO DO PROTOCOLO
                    ato_item_prenotacao = get_dados_prenotacao_postgresql(pedido)

                    # SELAR NO SQL SERVER PROTOCOLO
                    retorno = firebird.selar_protocolo_prenotacao_no_sql_server(
                        numero_protocolo=numero_protocolo,
                        pedido_id=pedido_fb["CHAVE_PEDIDOS"],
                        ato=ato_item_prenotacao,
                    )
                    # retorno = False

                    # BUSCAR SELO DO SQL SERVER
                    if retorno:
                        numero_selo_firebird = retorno["CODIGO_SEQUENCIAL_UNICO"]
                        codigo_seguranca_firebird = retorno["CODIGO_DE_SEGURANCA"]
                    else:
                        numero_selo_firebird = ""
                        codigo_seguranca_firebird = ""
                else:
                    (
                        numero_selo_firebird,
                        codigo_seguranca_firebird,
                        codigo_internet_firebird,
                    ) = firebird.selar_protocolo_no_firebird(
                        pedido_id=pedido_fb["CHAVE_PEDIDOS"],
                        pedido_item_id=pedido_item_fb,
                        db=db,
                    )
            except Exception:
                logger.exception(
                    f"ERRO ao tentar gravar o selo no Firebird para o protocolo {numero_protocolo}",
                )
                raise

            # ATUALIZAR PEDIDO
            try:
                pedido.numero_protocolo_firebird = numero_protocolo
                pedido.numero_selo_firebird = (
                    numero_selo_firebird if pedido_item_fb else ""
                )
                pedido.codigo_seguranca_firebird = (
                    codigo_seguranca_firebird if pedido_item_fb else ""
                )
                pedido.codigo_internet_firebird = (
                    codigo_internet_firebird if pedido_item_fb else ""
                )
                pedido.save()
            except Exception:
                logger.exception(
                    f"ERRO ao tentar atualizar o pedido no banco de dados para o protocolo {numero_protocolo}",
                )
                raise

        return protocolo_id


# Andamento Inicial
def get_andamento_inicial():
    tipo_andamento = models_home.TipoAndamento.objects.filter(
        servico__icontains="Prenota",
    ).first()
    return tipo_andamento.id if tipo_andamento else 12


# Emolumento Inicial
def get_default_emolumento_provisorio():
    tipo_emolumento = models_home.Emolumentos.objects.filter(
        nome__icontains=PROVISORIO,
    ).first()
    return tipo_emolumento.id if tipo_emolumento else 1377


# Ato Inicial
def get_default_ato_provisorio():
    tipo_ato = models_home.AtoPratica.objects.filter(
        tipo_ato__icontains=PROVISORIO,
    ).first()
    return tipo_ato.id if tipo_ato else 392


# Titulo Inicial
def get_default_titulo_provisorio():
    tipo_titulo = models_home.Titulo.objects.filter(
        tipo_titulo__icontains=PROVISORIO,
    ).first()
    return tipo_titulo.id if tipo_titulo else 96


# RETORNAR O CODIGO DA PRENOTACAO
def get_cod_prenotacao() -> str:
    return models_home.Configuracao.obter("CODIGO_EMOLUMENTO_PRENOTACAO_MG", "4701-9")


# BUSCAR DADOS DA PRENOTACAO
def get_dados_prenotacao_postgresql(pedido):
    """
    Busca dados da prenotação no banco de dados PostgreSQL.

    Args:
    ----
        pedido: Objeto de pedido para filtrar os dados.

    Returns:
    -------
        O primeiro objeto Ato encontrado ou None se não houver correspondências.

    """
    logger.debug("Iniciando a função get_dados_prenotacao_postgresql")

    # Obtendo o código de prenotação
    cod_prenotacao = get_cod_prenotacao()
    logger.debug(f"Obtido código de prenotação: {cod_prenotacao}")

    # Buscando o tipo de emolumento ativo com o código especificado
    tipo_emolumento = models.TipoEmolumento.objects.filter(
        codigo=cod_prenotacao,
        ativo=True,
    ).first()
    if tipo_emolumento:
        logger.debug(f"Tipo de emolumento encontrado: {tipo_emolumento}")
    else:
        logger.debug(
            f"Nenhum tipo de emolumento encontrado com o código especificado: {cod_prenotacao}",
        )
        return None

    # Buscando o primeiro ato que corresponda ao pedido e ao tipo de emolumento
    ato = (
        models.Ato.objects.filter(pedido=pedido, tipo_emolumento=tipo_emolumento)
        .select_related(
            "pedido",
            "tipo_titulo",
            "ato_praticavel",
            "tipo_emolumento",
            "imovel_tipo_registro",
            "tipo_tributacao",
            "ato",
        )
        .first()
    )
    if ato:
        logger.debug(f"Ato encontrado: {ato}")
    else:
        logger.debug("Nenhum ato encontrado para os critérios fornecidos")

    logger.debug("Finalizando a função get_dados_prenotacao_postgresql")
    return ato


# RETORNAR O CODIGO DA CERTIDAO POS REGISTRO
def get_cod_certidao_pos_registro() -> str:
    return models_home.Configuracao.obter(
        "CODIGO_EMOLUMENTO_CERTIDAO_POS_REGISTRO_MG",
        "8401-2",
    )


class PedidoFirebirdUtils:
    @staticmethod
    @transaction.atomic
    def exportar_pedido_de_protocolo_para_fb(
        pedido: "models.Pedido",
        atos: QuerySet["models.Ato"],
        user: User,
        db: FbConnection,
    ) -> dict:
        # FIXOS - PEDIDOS
        cartorio_model = apps.get_model("cartorios", "Cartorio")
        cartorio = cartorio_model.objects.select_related("municipio").first()
        municipio = cartorio.municipio.nome if cartorio and cartorio.municipio else ""

        pedido_item_fb = None
        documento_apresentante = 0
        numero_titulo = "1"
        uf = cartorio.codigo_uf
        # get_andamento_inicial()

        # Gerar o item do ato
        dados_de_atos = [ato.to_dict() for ato in atos]

        # Atualizar a observação do pedido
        observacao = models.Ato.construir_observacao(atos)

        # FIXOS - CAIXA
        getattr(pedido, "total_pedido", 59.58)

        try:
            # GRAVANDO O PEDIDO - PROTOCOLO
            pedido_fb = firebird.gravar_pedido_protocolo_fb(
                # Usar o numero do pedido como chave pois o id é uuid
                pedido_id=pedido.numero_pedido,
                numero_pedido=pedido.numero_pedido,
                data_entrada=pedido.data_entrada,
                data_prevista=(
                    pedido.data_prevista.strftime(settings.DATETIME_FIREBIRD_FORMAT)
                    if pedido.data_prevista
                    else ""
                ),
                data_validade=(
                    pedido.data_validade.strftime(settings.DATETIME_FIREBIRD_FORMAT)
                    if pedido.data_validade
                    else ""
                ),
                tipo_servico="R",
                nomeadquirente=pedido.apresentante.nome,
                nomeapresentante=pedido.apresentante.nome,
                nometransmitente=pedido.apresentante.nome,
                municipio=municipio,
                uf=uf,
                numero_talao=pedido.numero_pedido,
                observacao=((pedido.apresentante.observacao or "") + observacao),
                endereco=pedido.apresentante.observacao or "",
                tipo_documento_apresentante=documento_apresentante,
                documento_apresentante=pedido.apresentante.documento,
                # funcionario_codigo=Configuracao.obter("funcionario_id_sistema_antigo"),
                funcionario_id=user.id,
                fone=pedido.apresentante.telefone,
                email=pedido.apresentante.email,
                db=db,
            )

            if pedido_fb:
                # Atualiza o numero do pedido para alinhar com o firebird se a sequencia não estiver alinhada.
                # Originalmente o numero do pedido segue a mesma sequencia.
                pedido.numero_pedido = (
                    pedido_fb["NROPEDIDO"]
                    if (pedido.numero_pedido != pedido_fb["NROPEDIDO"])
                    else pedido.numero_pedido
                )

                # VERIFICAR SE O ITEM E DE PRENOTACAO
                pedido_item_fb_prenotacao = None

                # Gerar o item do pedido de todos cadastrados no pedido
                for item_ato in dados_de_atos:
                    # GRAVANDO O ITEM DO PEDIDO - PROTOCOLO
                    for _ in range(item_ato["QUANTIDADE"]):
                        pedido_item_fb, _ = firebird.gravar_pedido_item_protocolo_fb(
                            pedido_id=pedido_fb["CHAVE_PEDIDOS"],
                            valor_itbi=item_ato["VALOR_ITBI"],
                            valor_avaliacao=item_ato["VALOR_AVALIACAO"],
                            # valor_itbi=item_ato["VALOR_AVALIACAO"],
                            # valor_avaliacao=item_ato["VALOR_ITBI"],
                            tipo_imovel=item_ato["TIPO_IMOVEL"],
                            numero_imovel=item_ato["NUMERO_IMOVEL"],
                            emolumento_id=item_ato["CHAVE_EMOLUMENTOS"],
                            # quantidade=item_ato["QUANTIDADE"],
                            quantidade=1,
                            numero_ri=item_ato["NUMERO_RI"],
                            numero_titulo=numero_titulo,
                            numero_ato=item_ato["NUMERO_ATO"],
                            # colaborador_id=Configuracao.obter("funcionario_id_sistema_antigo"),
                            colaborador_id=user.pk,
                            ato_id=item_ato["ATO_ID"],
                            titulo_id=item_ato["TITULO_ID"],
                            tipo_tributacao_id=item_ato["TIPO_TRIBUTACAO_ID"],
                            codigo_tabela=item_ato["CODIGO_TABELA"],
                            valor_emolumento=item_ato["VALOR_EMOLUMENTO"],
                            valor_fundo_estado=item_ato["VALOR_FUNDO_ESTADO"],
                            valor_tfj=item_ato["VALOR_TFJ"],
                            valor_issqn=item_ato["VALOR_ISSQN"],
                            db=db,
                        )

                    # VERIFICAR SE O ITEM E DE PRENOTACAO
                    if item_ato["CODIGO_TABELA"] == get_cod_prenotacao():
                        pedido_item_fb_prenotacao = pedido_item_fb

                # CASO TENHA PRENOTACAO, RETORNAR O ITEM DO PEDIDO PARA SELAR
                pedido_item_fb = pedido_item_fb_prenotacao or pedido_item_fb

                # ATUALIZAR OS VALORES DO PEDIDOS
                firebird.atualizar_pedido_protocolo(
                    pedido_id=pedido_fb["CHAVE_PEDIDOS"],
                    coluna_pedido="VALORRECEITAADICIONAL",
                    coluna_item="VALORRECEITAADICIONAL1",
                    db=db,
                )

                # SELAR NO SQL SERVER PROTOCOLO
                cartorio_model = apps.get_model("cartorios", "Cartorio")
                usar_selo_sql_server = cartorio_model.objects.values_list(
                    "usar_selo_sql_server",
                    flat=True,
                ).first()
                coluna_emolumento_item = (
                    "VALOREMOLUMENTO - VALOR_FUNDOESTADO"
                    if usar_selo_sql_server == "S"
                    else "VALOREMOLUMENTO"
                )

                firebird.atualizar_pedido_protocolo(
                    pedido_id=pedido_fb["CHAVE_PEDIDOS"],
                    coluna_pedido="VALOREMOLUMENTO",
                    coluna_item=coluna_emolumento_item,
                    db=db,
                )

                firebird.atualizar_pedido_protocolo(
                    pedido_fb["CHAVE_PEDIDOS"],
                    "VALORFINAL",
                    "VALORTOTALITEM",
                    db,
                )

                firebird.atualizar_pedido_protocolo(
                    pedido_fb["CHAVE_PEDIDOS"],
                    "VALORACERTO",
                    "VALORTOTALITEM",
                    db,
                )

                firebird.atualizar_pedido_protocolo(
                    pedido_fb["CHAVE_PEDIDOS"],
                    "TAXA1",
                    "TAXA1",
                    db,
                )

                mensagem = f"SUCESSO! ID do pedido após a exportação: {pedido_fb['CHAVE_PEDIDOS']}"

                logger.info(mensagem)

                pedido.save()
            else:
                mensagem = """ERRO ao tentar exportar o pedido. Pedido_fb é None."""
                logger.error(mensagem)

        except Exception as e:
            mensagem = f"ERRO ao tentar exportar o pedido: {e}"
            logger.exception(mensagem)
            raise

        return pedido_fb, pedido_item_fb

    @staticmethod
    def gravar_evento(evento, pedido_fb, user_id, db: FbConnection) -> dict:
        # return firebird.gravar_andamentos_pedido_ato(
        return firebird.gravar_andamentos_pedido(
            pedido_id=pedido_fb["pedido_id"],
            data=evento.data,
            # funcionario_id=Configuracao.obter("funcionario_id_sistema_antigo"),
            funcionario_id=user_id,
            tipo_andamento_id=evento.pk,
            db=db,
        )

    @staticmethod
    def gravar_parte(parte, pedido_fb, db: FbConnection) -> dict:
        # return firebird.gravar_parte_ped_ato_fb(
        return firebird.gravar_pessoa_ped_protocolo_fb(
            pedido_id=pedido_fb["pedido_id"],
            nome=parte.nome,
            documento=parte.documento,
            estado_civil=parte.estado_civil,
            complemento=parte.complemento,
            db=db,
        )

    @staticmethod
    def protocolar_pedido_no_fb(
        pedido_fb: dict,
        pedido_item_fb: dict,
        pedido: "models.Pedido",
        user: User,
        db: FbConnection,
    ) -> None:
        try:
            numero_protocolo, protocolo_id = firebird.gravar_protocolo_firebird(
                pedido_id=pedido_fb["CHAVE_PEDIDOS"],
                titulo_id=0,
                observacao=pedido_fb["OBSERVACAO"],
                db=db,
            )
        except Exception:
            logger.exception("ERRO ao tentar protocolar o pedido no Firebird")
            raise

        # FIXOS - CAIXA
        Decimal(pedido_fb.get("total_pedido", 59.58)).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )

        # GRAVAR ANDAMENTO
        try:
            firebird.gravar_andamento_do_protocolo_no_fb(
                protocolo_id=protocolo_id,
                funcionario_id=user.pk,
                servico_id=models_home.TipoAndamento.get_prenotacao_id(),
                db=db,
            )
        except Exception:
            logger.exception(
                f"ERRO ao tentar gravar o andamento no Firebird para o protocolo {numero_protocolo}",
            )
            raise

        # COMENTANDO PARA QUE NO CAIXA O CLIENTE ESCOLHA A FORMA DE PAGAMENTO EM TELA SEPARADA
        # GRAVAR CAIXA
        # try:
        #     firebird.gravar_caixa_do_protocolo_no_firebird(
        #         pedido_id=pedido_fb["CHAVE_PEDIDOS"],
        #         valor=valor_transacao,
        #         funcionarios_id=user.id,
        #         descricao=str(
        #             "'" + "Prenotação - " + str(pedido.apresentante.nome) + "'",
        #         ),
        #         db=db,
        #     )
        # except Exception:
        #     logger.exception(
        #         f"ERRO ao tentar gravar o caixa no Firebird para o protocolo {numero_protocolo}",
        #     )
        #     raise  # repassa a exceção para o chamador para garantir o rollback

        # GRAVAR SELO
        if pedido_item_fb:
            try:
                # ALFENAS ADICIONAR CAMPOS PARA O SQLSERVER
                cartorio_model = apps.get_model("cartorios", "Cartorio")

                usar_selo_sql_server = cartorio_model.objects.all().values_list(
                    "usar_selo_sql_server",
                    flat=True,
                )[0]
                # SELAR NO SQL SERVER PROTOCOLO
                if usar_selo_sql_server == "S":
                    codigo_internet_firebird = ""

                    # PEGAR OS DADOS DA PRENOTACAO DO PROTOCOLO
                    ato_item_prenotacao = get_dados_prenotacao_postgresql(pedido)

                    # SELAR NO SQL SERVER PROTOCOLO
                    retorno = firebird.selar_protocolo_prenotacao_no_sql_server(
                        numero_protocolo=numero_protocolo,
                        pedido_id=pedido_fb["CHAVE_PEDIDOS"],
                        ato=ato_item_prenotacao,
                    )
                    # retorno = False

                    # BUSCAR SELO DO SQL SERVER
                    if retorno:
                        numero_selo_firebird = retorno["CODIGO_SEQUENCIAL_UNICO"]
                        codigo_seguranca_firebird = retorno["CODIGO_DE_SEGURANCA"]
                    else:
                        numero_selo_firebird = ""
                        codigo_seguranca_firebird = ""
                else:
                    (
                        numero_selo_firebird,
                        codigo_seguranca_firebird,
                        codigo_internet_firebird,
                    ) = firebird.selar_protocolo_no_firebird(
                        pedido_id=pedido_fb["CHAVE_PEDIDOS"],
                        pedido_item_id=pedido_item_fb,
                        db=db,
                    )
            except Exception:
                logger.exception(
                    f"ERRO ao tentar gravar o selo no Firebird para o protocolo {numero_protocolo}",
                )
                raise

            # ATUALIZAR PEDIDO
            try:
                pedido.numero_protocolo_firebird = numero_protocolo
                pedido.numero_selo_firebird = (
                    numero_selo_firebird if pedido_item_fb else ""
                )
                pedido.codigo_seguranca_firebird = (
                    codigo_seguranca_firebird if pedido_item_fb else ""
                )
                pedido.codigo_internet_firebird = (
                    codigo_internet_firebird if pedido_item_fb else ""
                )
                pedido.save()
            except Exception:
                logger.exception(
                    f"ERRO ao tentar atualizar o pedido no banco de dados para o protocolo {numero_protocolo}",
                )
                raise

        return protocolo_id


# app_consulta/services.py


def consulta_protocolo(numero_protocolo):
    url = f"http://localhost:8000/api/protocolos/?numero={numero_protocolo}"
    response = requests.get(url)
    if response.status_code == 200:
        protocolos = response.json()
        if protocolos:
            return protocolos[0]
        else:
            return "Nenhum protocolo encontrado."
    else:
        return "Erro ao acessar a API."


# RETORNAR O CODIGO DA PRENOTACAO
def get_requeremento_inicial_id() -> str:
    return models_home.Configuracao.obter("REQUERIMENTO_INICIAL_ID", "4")
