import logging
from decimal import Decimal
from typing import TYPE_CHECKING, Any

import numpy as np
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.home.helpers import get_custas_firebird
from apps.home.padroes import PROVISORIO
from apps.home.services import firebird, sqlserver
from core.utils.firebird_utils import FbConnection

if TYPE_CHECKING:
    from apps.home.models import Emolumentos
    from apps.pedidos.models import Ato

logger = logging.getLogger(__name__)

logger.debug(f"Iniciando {__name__}")


# def extrair_valor(results, index, default=0, to_real=True):
#     try:
#         value = results[0][index]
#         return real(value) if to_real else value
#     except (IndexError, TypeError):
#         logger.info(f"ERRO ao extrair valor do resultado: {results}")
#         raise


def extrair_valor(
    results: list[list[Any]],
    index: int,
    default: Decimal = 0,
    to_real=None,
) -> Decimal:
    """
    Extrai um valor de uma lista de resultados, converte para real se necessário.

    Args:
    ----
        results (List[List[Any]]): Lista de listas contendo os resultados.
        index (int): Índice do valor a ser extraído.
        default (float): Valor padrão a ser retornado se o valor não puder ser extraído.
        to_real (bool): Se True, converte o valor para um número real.

    Returns:
    -------
        float: Valor extraído e possivelmente convertido para real.

    """
    to_real = to_real or True

    try:
        value = results[0][index]
        return np.real(value) if to_real else value
    except (IndexError, TypeError) as e:
        logger.info(f"ERRO ao extrair valor do resultado: {results} - {e}")
        return default


def get_valores_protocolo_fb(
    vigencia_id,
    tabela_id,
    estado_civil_id,
    db: FbConnection,
):
    if not all([vigencia_id, tabela_id, estado_civil_id]):
        logging.error(
            "Parâmetros inválidos fornecidos para obter valores da protocolo.",
        )
        print(estado_civil_id, ", ", tabela_id, " , ", vigencia_id)
        return None

    print("Obtendo valores da protocolo...")
    query = """
        SELECT FIRST 1
            VALOR, CODIGO_VALORES_CERTIDOES, TAXAJUDICIARIA,
            CODIGO_TABELA, ADIC_VALOR, CATEGORIA, TAXA1
        FROM VALORES_CERTIDOES
        WHERE CHAVE_VIGOR = ?
        AND CODIGO_TABELA = ?
        AND CATEGORIA = ?
    """

    params = (vigencia_id, tabela_id, estado_civil_id)

    try:
        results = db.execute_query(query, params)
        if not results:
            logging.warning("Nenhum resultado retornado da consulta.")
            return None
    except Exception:
        logging.exception("ERRO ao obter valores da protocolo: ")
        return None

    emolumento = extrair_valor(results, 0)
    valor = extrair_valor(results, 0)
    tipo_protocolo = extrair_valor(results, 1, to_real=False)
    tx_judiciaria = extrair_valor(results, 2)
    valor_adicionado = extrair_valor(results, 4)
    quantidade = "1"
    valor_fundo_estado = extrair_valor(results, 6)

    valor += valor_adicionado + tx_judiciaria

    return {
        "emolumento": emolumento,
        "valor": valor,
        "tipo_protocolo": tipo_protocolo,
        "tx_judiciaria": tx_judiciaria,
        "valor_adicionado": valor_adicionado,
        "quantidade": quantidade,
        "valor_fundo_estado": valor_fundo_estado,
    }


def get_tipo_de_livro(livro):
    logger.info(f"Obtendo tipo de livro {livro}...")
    tipos = {"L2": "M", "2": "M", "L3": "A", "3": "A", "T": "T"}
    resultado = tipos.get(livro, "M")
    logger.info(f"Tipo de livro obtido:{resultado}")
    return resultado


def get_valor_parametro_ini_fb(secao, estacao, nome, colunas, db: FbConnection):
    logger.info(
        f"""
        Obtendo valor do parâmetro INI no Firebird:
        Secao: {secao},
        Estacao: {estacao},
        Nome: {nome},
        Colunas {colunas},
        """,
    )
    query = "SELECT ? FROM INI WHERE SECAO = ? AND ESTACAO = ? AND NOME = ?"
    params = (secao, estacao, nome)

    try:
        results = db.execute_query(query, params)[0]
    except Exception:
        logging.exception("ERRO ao obter valor do parâmetro INI.: ")
        raise
    return results


def atualizar_caixa_do_pedido(pedido_id, db: FbConnection):
    logger.info(f"Atualizando CAIXA do pedido: {pedido_id}")
    comando = """
        UPDATE CAIXA
        SET VALOR = (
            SELECT VALOR_CALC
            FROM PED_CERTIDOES
            WHERE CHAVE_PED_CERTIDOES = ?
        )
        WHERE CHAVE_PED_CERTIDOES = ?
    """

    params = (pedido_id, pedido_id)

    try:
        db.execute_command(comando, params)
    except Exception:
        logging.exception(f"ERRO ao atualizar CAIXA do pedido. ID: '{pedido_id}'.: ")
        raise


def get_vigencia_atual_firebird(db: FbConnection):
    """
    Obtém o ID da vigencia mais recente dos emolumentos a partir do banco de dados Firebird.

    Returns
    -------
        int: ID da vigencia mais recente.

    Raises
    ------
        Exception: Caso haja algum problema na consulta ao banco de dados.

    """
    query = "SELECT MAX(CHAVE_VIGOR) FROM EMOLUMENTOS_VIGOR"

    try:
        results = db.execute_query(query)[0]
        logger.info(f"Obtendo chave do Vigor atual no FB: {results}")
        return results
    except Exception:
        logging.exception(f"ERRO ao obter chave da vigencia atual no FB: {query}")
        raise


def get_prox_numero_do_pedido_fb(db: FbConnection) -> int:
    resultado = db.sequence("PEDIDOS_SEQ").proximo
    print("FB: PEDIDO_FB proximo numero: ", resultado)

    return resultado


def get_numero_cri(numero_pedido, db: FbConnection):
    print("FB: Obtendo número do CRI. Numero do pedido: ", numero_pedido)

    query = (
        " SELECT MAX(CHAVE_PED_CERTIDOES) FROM PED_CERTIDOES WHERE NUMEROPEDIDOCRI = '"
        + str(numero_pedido)
        + "'"
    )

    db = FbConnection() if db is None else db
    results = db.execute_query(query)[0]

    return ".".join([str(value) for value in results])


def get_numero_cri_2(numero_pedido_cri, db: FbConnection):
    print("FB: Obtendo número do CRI...")

    query = f"""SELECT CHAVE_PED_CERTIDOES
                FROM PED_CERTIDOES
                WHERE NUMEROPEDIDOCRI = {numero_pedido_cri!s}"""

    db = FbConnection() if db is None else db
    results = db.execute_query(query)[0]

    return ".".join([str(value) for value in results])


def gravar_caixa_ped_protocolo_fb(
    pedido_id,
    data_pedido,
    colaborador,
    descricao,
    valor,
    pagamento_id,
    reprotocolo,
    db: FbConnection,
) -> int:
    if str(pedido_id) != "":
        caixa_id = db.sequence("CAIXA_SEQ").proximo

        tipo_transacao = "1"
        tipo_documento = "1"
        query = None
        params = None
        valor = 0
        pagamento_id = "6"

        comando = """
            INSERT INTO CAIXA (
                CHAVE_CAIXA,
                DATAPAGAMENTO,
                DESCRICAO,
                TIPOTRANSACAO,
                TIPODOCUMENTO,
                VALOR,
                CHAVE_PED_CERTIDOES,
                CHAVE_PAGAMENTO,
                CHAVE_FUNCIONARIOS
            )
            VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?
            );
        """

        params = (
            caixa_id,
            data_pedido,
            descricao,
            tipo_transacao,
            tipo_documento,
            valor,
            pedido_id,
            pagamento_id,
            colaborador,
        )
        logger.info(f"FB: Gravando caixa do pedido. ID: {pedido_id}")
        try:
            if query and params:
                db = FbConnection() if db is None else db
                db.execute_command(comando, params)

        except Exception:
            logging.exception(f"ERRO ao gravar CAIXA do pedido. ID: '{pedido_id}'.: ")
            raise

    return 1


def gravar_pedido_protocolo_fb(
    pedido_id,
    numero_pedido,
    data_entrada,
    data_prevista,
    data_validade,
    tipo_servico,
    nomeadquirente,
    nomeapresentante,
    nometransmitente,
    municipio,
    uf,
    numero_talao,
    observacao,
    endereco,
    tipo_documento_apresentante,
    documento_apresentante,
    funcionario_id,
    fone,
    email,
    db: FbConnection,
):
    nome = nomeapresentante if nomeapresentante else "SEM NOME"

    comando = """
        INSERT INTO PEDIDOS (
            CHAVE_PEDIDOS,
            NROPEDIDO,
            DATAENTRADA,
            DATAPREVISTA,
            DATA_VALIDADE,
            TIPOSERVICO,
            NOMEADQUIRENTE,
            NOMEAPRESENTANTE,
            NOMETRANSMITENTE,
            MUNICIPIO,
            UF,
            OBSERVACAO,
            ENDERECO,
            TIPODOCUMENTOAPRES,
            NUMERODOCUMENTOAPRES,
            CHAVE_FUNCIONARIOS
        ) VALUES ( ?,?,CURRENT_TIMESTAMP,?,?,?,?,?,?,?,?,?,?,?,?,? ); """

    parametros = (
        pedido_id,  # CHAVE_PEDIDOS
        pedido_id,  # NROPEDIDO
        data_prevista,  # DATAPREVISTA
        data_validade,  # DATA_VALIDADE
        tipo_servico,  # TIPOSERVICO
        nome,  # NOMEADQUIRENTE
        nome,  # NOMEAPRESENTANTE
        nome,  # NOMETRANSMITENTE
        municipio,  # MUNICIPIO
        uf,  # UF
        observacao,  # OBSERVACAO
        endereco,  # ENDERECO
        tipo_documento_apresentante,  # TIPODOCUMENTOAPRES
        documento_apresentante,  # NUMERODOCUMENTOAPRES
        funcionario_id,  # CHAVE_FUNCIONARIOS
    )
    try:
        logger.info(f"FB: Gravando pedido do FB. ID: {pedido_id}")
        db.execute_command(comando, parametros)

        pedido_fb = firebird.get_pedido_fb(pedido_id, db)

        if not pedido_fb:
            logger.warning(f"FB: O pedido {pedido_id} foi encontrado.")
            return None

        return pedido_fb
    except Exception:
        logger.exception(f"ERRO gravar Pedido de Protocolo. ID: {pedido_id}. Erro: ")
        raise


# Emolumento Inicial
def get_default_emolumento_provisorio():
    from apps.home.models import Emolumentos

    tipo_emolumento = Emolumentos.objects.filter(nome__icontains=PROVISORIO).first()
    return tipo_emolumento.id if tipo_emolumento else 1377


# Ato Inicial
def get_default_ato_provisorio():
    from apps.home.models import AtoPratica

    tipo_ato = AtoPratica.objects.filter(tipo_ato__icontains=PROVISORIO).first()
    return tipo_ato.id if tipo_ato else 392


# Titulo Inicial
def get_default_titulo_provisorio():
    from apps.home.models import Titulo

    tipo_titulo = Titulo.objects.filter(tipo_titulo__icontains=PROVISORIO).first()
    return tipo_titulo.id if tipo_titulo else 96


def obter_data_pagamento() -> str:
    """Obtém a data de pagamento formatada."""
    data_pagamento = timezone.now().date().strftime(settings.DATE_FIREBIRD_FORMAT)
    logger.debug(f"Data de pagamento obtida: {data_pagamento}")
    return data_pagamento


def obter_numero_ou_default(numero: str, default: str = "") -> str:
    """Retorna o número ou um valor padrão."""
    resultado = numero or default
    logger.debug(f"Numero obtido: {resultado} (Default: {default})")
    return resultado


def obter_titulo_ou_default(titulo_id: int, default_titulo: int) -> int:
    """Retorna o ID do título ou um valor padrão."""
    resultado = titulo_id or default_titulo
    logger.debug(f"Titulo ID obtido: {resultado} (Default: {default_titulo})")
    return resultado


def calcular_custas(tipo_tributacao_id: int, emolumento) -> int:
    """Calcula as custas baseado no tipo de tributação e emolumento."""
    custas_por_tipo, emolumento_exportar_id = get_custas_firebird(
        tipo_tributacao_id,
        emolumento.pk,
    )

    resultado = (
        custas_por_tipo.get(int(tipo_tributacao_id), 1)
        if emolumento.valores.codigo_tabela != "0"
        else 1
    )

    logger.debug(
        f"Custas calculadas: {resultado} para Tipo Tributacao ID: {tipo_tributacao_id}",
    )

    return resultado, emolumento_exportar_id


def calcular_valor_total(
    valor_emolumento: Decimal,
    valor_fundo_estado: Decimal,
    valor_tfj: Decimal,
    valor_issqn: Decimal,
) -> Decimal:
    """Calcula o valor total do item."""
    total = valor_emolumento + valor_fundo_estado + valor_tfj + valor_issqn
    logger.debug(f"Valor total calculado: {total}")
    return total


def obter_chave_emolumento_ws_go(
    usar_selo_sql_server: str,
    codigo_tabela: str,
    custas: int,
) -> int:
    """Obtém a chave do emolumento para o webservice."""
    chave = (
        get_codigo_webservice_selo(codigo_tabela, custas)
        if usar_selo_sql_server == "S"
        else 0
    )
    logger.debug(
        f"Chave emolumento WS GO obtida: {chave} (Usar selo SQL Server: {usar_selo_sql_server})",
    )
    return chave


def buscar_emolumento(emolumento_id: int, valor_itbi: Decimal) -> "Emolumentos":
    """Busca o emolumento no banco de dados."""
    from apps.home.models import Emolumentos

    emolumento = Emolumentos.obter(
        emolumento_id=emolumento_id,
        valor_documento=valor_itbi,
    )
    logger.debug(
        f"Emolumento buscado: {emolumento} (ID: {emolumento_id}, Valor ITBI: {valor_itbi})",
    )
    return emolumento


def obter_dados_sqlserver() -> str:
    """Verifica se o selo SQL Server deve ser usado."""
    from apps.cartorios.models import Cartorio

    usar_selo_sql_server = Cartorio.objects.all().values_list(
        "usar_selo_sql_server",
        flat=True,
    )[0]
    logger.debug(f"Usar selo SQL Server: {usar_selo_sql_server}")
    return usar_selo_sql_server


def gravar_pedido_item_protocolo_fb(
    pedido_id: int,
    valor_itbi: Decimal,
    valor_avaliacao: Decimal,
    tipo_imovel: str,
    numero_imovel: str,
    emolumento_id: int,
    quantidade: int,
    numero_ri: str,
    numero_titulo: str,
    numero_ato: str,
    colaborador_id: int,
    ato_id: int,
    titulo_id: int,
    tipo_tributacao_id: int = 1,
    codigo_tabela: str = "0",
    valor_emolumento: Decimal = Decimal("0"),
    valor_fundo_estado: Decimal = Decimal("0"),
    valor_tfj: Decimal = Decimal("0"),
    valor_issqn: Decimal = Decimal("0"),
    db: FbConnection = None,
) -> tuple[int, str]:
    from apps.home.models import Emolumentos

    """Insere um novo item de pedido no banco de dados e retorna o ID do item inserido e a data de pagamento."""
    try:
        pedido_item_id = db.sequence("PEDIDOS_ITENS_SEQ").proximo
        data_pagamento = db.now()

        numero_imovel = obter_numero_ou_default(numero_imovel)
        numero_ato = obter_numero_ou_default(numero_ato)
        logger.debug(f"Numero Imovel: {numero_imovel}, Numero Ato: {numero_ato}")

        titulo_id = obter_titulo_ou_default(titulo_id, get_default_titulo_provisorio())
        ato_id = obter_titulo_ou_default(ato_id, get_default_ato_provisorio())
        logger.debug(f"Titulo ID: {titulo_id}, Ato ID: {ato_id}")

        emolumento = buscar_emolumento(emolumento_id, valor_itbi)
        custas, emolumento_exportar_id = calcular_custas(tipo_tributacao_id, emolumento)

        # VERIFICAR SE O EMOLUMENTO É EXPORTADO DE OUTRO ITEM - ISENTO, 50 OU 75%
        if emolumento_exportar_id:
            emolumento = Emolumentos.objects.filter(id=emolumento_exportar_id).first()

            # NAO ENCONTROU EMOLUMENTO EXPORTAR
            if not emolumento:
                emolumento = Emolumentos.objects.filter(
                    id=emolumento_id,
                ).first()

            valor_emolumento, valor_fundo_estado, valor_tfj, valor_issqn = (
                calcular_valor_para_exportar(
                    tipo_tributacao_id,
                    valor_emolumento,
                    valor_fundo_estado,
                    valor_tfj,
                    valor_issqn,
                )
            )

            print("EMOLUMENTO EXPORTADO: ", emolumento)

        valor_total = calcular_valor_total(
            valor_emolumento,
            valor_fundo_estado,
            valor_tfj,
            valor_issqn,
        )

        chave_emolumento_ws_go = obter_chave_emolumento_ws_go(
            obter_dados_sqlserver(),
            codigo_tabela,
            custas,
        )

        logger.debug(
            f"Emolumento: {emolumento}, Custas: {custas}, Valor Total: {valor_total}, Chave WS GO: {chave_emolumento_ws_go}",
        )

        codigo_atoselo = (
            codigo_tabela[:4] if codigo_tabela else emolumento.codigo_tabela
        )

        # NAO ENCONTROU TRIBUTACAO = WS
        if chave_emolumento_ws_go is None or chave_emolumento_ws_go == 0:
            chave_emolumento_ws_go = 122

        # Enviar o Emolumento ID
        try:
            emolumento_id = emolumento.pk
        except:
            emolumento_id = emolumento

        # NAO ENCONTROU EMOLUMENTO EXPORTAR
        # if not emolumento_id:
        #    emolumento_id = emolumento

        # Inserir o pedido no banco de dados
        inserir_pedido_item(
            db=db,
            pedido_item_id=pedido_item_id,
            pedido_id=pedido_id,
            ato_id=ato_id,
            titulo_id=titulo_id,
            colaborador_id=colaborador_id,
            emolumento_id=emolumento_id,
            data_pagamento=data_pagamento,
            quantidade=quantidade,
            tipo_imovel=tipo_imovel,
            numero_imovel=numero_imovel,
            numero_ri=numero_ri,
            numero_ato=numero_ato,
            codigo_tabela=codigo_tabela,
            valor_emolumento=valor_emolumento,
            valor_fundo_estado=valor_fundo_estado,
            valor_tfj=valor_tfj,
            valor_issqn=valor_issqn,
            valor_itbi=valor_itbi,
            valor_avaliacao=valor_avaliacao,
            numero_titulo=numero_titulo,
            valor_total=valor_total,
            custas=custas,
            codigo_atoselo=codigo_atoselo,
            chave_emolumento_ws_go=chave_emolumento_ws_go,
        )

        logger.info(f"FB: Sucesso comando - gravar pedido {pedido_item_id}")

        return (
            pedido_item_id,
            emolumento.codigo_tabela if emolumento else codigo_tabela or 0,
        )

    except Exception:
        logger.exception(f"ERRO. FB: gravar pedido ITEM. ID: {pedido_item_id}. Erro: ")
        raise


def inserir_pedido_item(
    db: FbConnection,
    pedido_item_id,
    pedido_id,
    ato_id,
    titulo_id,
    colaborador_id,
    emolumento_id,
    data_pagamento,
    quantidade,
    tipo_imovel,
    numero_imovel,
    numero_ri,
    numero_ato,
    codigo_tabela,
    valor_emolumento,
    valor_fundo_estado,
    valor_tfj,
    valor_issqn,
    valor_itbi,
    valor_avaliacao,
    numero_titulo,
    valor_total,
    custas,
    codigo_atoselo,
    chave_emolumento_ws_go,
) -> dict:
    vigencia_id = get_vigencia_atual_firebird(db)["MAX"]

    # CUSTAS ISENTO
    if custas == 0:
        codigo_tipo_tribucao = 10
    # CUSTAS SFH
    elif custas == 4:
        codigo_tipo_tribucao = 4
    else:
        codigo_tipo_tribucao = custas

    chave_emolumento_ws_go = chave_emolumento_ws_go if chave_emolumento_ws_go else None

    """Insere o pedido item no banco de dados usando parâmetros para evitar injeção de SQL."""

    comando = """
        INSERT INTO PEDIDOS_ITENS (
            CHAVE_PEDIDOS_ITENS, CHAVE_PEDIDOS, CHAVE_ATOS, CHAVE_TITULOS, CHAVE_FUNCIONARIOS,
            TABELACALCULO, CHAVE_VIGOR, DATA_PAGAMENTO, CDHU, TIPO_IMOVEL, NUMERO_IMOVEL,
            NUMERO_RI, NUMEROATO, CODIGO_TABELA, VALOREMOLUMENTO, VALORRECEITAADICIONAL1,
            TAXA1, VALOR_FUNDOESTADO, VALORITBI, VALORAVALIACAO, NROTITULO, VALORTOTALITEM,
            ANO_REFERENCIA_TABELA, CODIGO_TIPO_TRIBUTACAO, CODIGO_ATOSELO, DATA_ACERTO_ITEM,
            GRUPOLANCAMENTO, EMOLUMENTOLIQ, CHAVE_EMOLUMENTO_WS_GO, CUSTAS
        ) VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
        );
    """
    parametros = (
        pedido_item_id,  # CHAVE_PEDIDOS_ITENS
        pedido_id,  # CHAVE_PEDIDOS
        ato_id,  # CHAVE_ATOS
        titulo_id,  # CHAVE_TITULOS
        colaborador_id,  # CHAVE_FUNCIONARIOS
        emolumento_id,  # TABELACALCULO
        vigencia_id,  # CHAVE_VIGOR
        data_pagamento,  # DATA_PAGAMENTO
        quantidade,  # CDHU
        tipo_imovel,  # TIPO_IMOVEL
        numero_imovel,  # NUMERO_IMOVEL
        numero_ri,  # NUMERO_RI
        numero_ato,  # NUMEROATO
        codigo_tabela,  # CODIGO_TABELA
        valor_emolumento,  # VALOREMOLUMENTO
        valor_tfj,  # VALORRECEITAADICIONAL1
        valor_issqn,  # TAXA1
        valor_fundo_estado,  # VALOR_FUNDOESTADO
        valor_itbi,  # VALORITBI
        valor_avaliacao,  # VALORAVALIACAO
        numero_titulo,  # NROTITULO
        valor_total,  # VALORTOTALITEM
        timezone.now().year,  # ANO_REFERENCIA_TABELA
        codigo_tipo_tribucao,  # CODIGO_TIPO_TRIBUTACAO
        codigo_atoselo,  # CODIGO_ATOSELO
        data_pagamento,  # DATA_ACERTO_ITEM
        1,  # GRUPOLANCAMENTO
        valor_emolumento,  # EMOLUMENTOLIQ
        chave_emolumento_ws_go,  # CHAVE_EMOLUMENTO_WS_GO
        custas,  # CUSTAS
    )
    try:
        db.execute_command(comando, parametros)

        return firebird.get_pedido_item(pedido_item_id, db)
    except Exception as e:
        logger.exception(f"Erro ao inserir pedido item no banco de dados: {e!s}")
        raise


def gravar_pessoa_ped_protocolo_fb(
    pedido_id: int,
    nome: str,
    documento: str,
    estado_civil: str,
    complemento: str,
    db: FbConnection,
) -> None:
    print("Iniciando o processo de gravação de pessoa e pedido.")

    db = FbConnection() if db is None else db

    def get_max_ped_protocolo_pessoas() -> int:
        print("Obtendo o maior valor da chave em PED_CERTIDOES_PESSOAS.")
        query = "SELECT MAX(CHAVE_PED_CERTIDOES_PESSOAS) FROM PED_CERTIDOES_PESSOAS"
        result = db.execute_query(query)[0]
        logger.info(f"Valor máximo encontrado: {result[0]}")
        return int(result[0])

    def restart_sequence_with_value(value) -> None:
        logger.info(f"Reiniciando a sequência com o valor {value}.")
        comando = f"ALTER SEQUENCE PED_CERTIDOES_PESSOAS_SEQ RESTART WITH {value}"
        db.execute_command(comando)

    def insert_ped_protocolos_pessoas(
        pedido_id: int,
        nome: str,
        documento: str,
        complemento: str,
        estado_civil=0,
        valor_coluna="T",
    ) -> None:
        logger.info(
            f"Preparando para inserir dados do pedido {pedido_id} e pessoa {nome}.",
        )

        comando = """INSERT INTO PED_CERTIDOES_PESSOAS
                   (CHAVE_PED_CERTIDOES, CHAVE_PED_CERTIDOES_PESSOAS, NOME,
                   DOCUMENTO, COMPLEMENTO, CREGISTRO, ESTADOCIVIL)
                   VALUES (?, GEN_ID(PED_CERTIDOES_PESSOAS_SEQ, 1), ?, ?, ?, ?, ?)"""

        parameters = (
            pedido_id,
            nome,
            documento,
            complemento,
            valor_coluna,
            estado_civil,
        )

        try:
            logger.info(f"Inserindo dados do pedido {pedido_id} e pessoa {nome}.")
            db.execute_command(comando, parameters)
            print("Dados inseridos .")
        except Exception:
            logging.exception(
                f"ERRO ao adicionar PESSOAS do pedido com o ID: '{pedido_id}'. Detalhes do erro",
            )
            raise

    max_ped_protocolo_pessoas = get_max_ped_protocolo_pessoas()
    restart_sequence_with_value(max_ped_protocolo_pessoas)
    insert_ped_protocolos_pessoas(pedido_id, nome, documento, complemento, estado_civil)


# def gravar_imoveis_ped_protocolo_fb(
#     pedido_id: int,
#     matricula: int,
#     cartorio: str,
#     livro: str,
#     descricao: str,
#     db: FbConnection,
# ):
#     try:
#         if matricula:
#             int(matricula)
#     except Exception:
#         matricula = 0
#     sequence_pedido_imoveis = 0

#     # if int(matricula) > 0:
#     tipo_livro = get_tipo_de_livro(livro)
#     valor_col = "T"
#     # if int(matricula) > 0:
#     tipo_livro = get_tipo_de_livro(livro)
#     valor_col = "T"

#     query = "SELECT MAX(CHAVE_PED_CERTIDOES_PESSOAS) FROM PED_CERTIDOES_IMOVEIS"
#     db = FbConnection() if db is None else db
#     response = db.execute_query(query)
#     max_ped_protocolo_imoveis = int(response[0]["MAX"])

#     # Agora, usando a formatação de strings do Python para inserir o valor na consulta:
#     adjustment_query = f"ALTER SEQUENCE PED_CERTIDOES_IMOVEIS_SEQ RESTART WITH {max_ped_protocolo_imoveis}"

#     db.execute_command(adjustment_query)

#     sequence_pedido_imoveis = db.sequence("PED_CERTIDOES_IMOVEIS_SEQ").proximo

#     query = """
#         INSERT INTO PED_CERTIDOES_IMOVEIS
#             (CHAVE_PED_CERTIDOES, CHAVE_PED_CERTIDOES_IMOVEIS,
#             MATRICULA, CARTORIO, CMATRICULA, TIPO)
#         VALUES (?, ?, ?, ?, ?, ?)
#     """

#     params = (
#         pedido_id,
#         sequence_pedido_imoveis,
#         matricula,
#         cartorio,
#         valor_col,
#         tipo_livro,
#     )

#     logger.info(f"FB: Gravando imóvel {matricula} do pedido. ID: {pedido_id}")

#     try:
#         db.execute_command(query, params)
#     except Exception:
#         logging.exception(f"ERRO ao gravar IMOVEIS no pedido. ID: '{pedido_id}'.: ")
#         raise
#     # else:
#     #     logger.info(f"Imóvel {matricula} do pedido {pedido_id} não foi gravado.")

#     return sequence_pedido_imoveis


# Armazena a protocolo em si. Que constratá no pedido. Incluindo os valores e as quantidade.
def gravar_tipos_ped_protocolo(
    pedido_id: int,
    estado_civil_id: int,
    codigo_tabela: int,
    quantidade: int,
    funcionario_id: int,
    db,
):
    sequence_tipo_protocolo = db.sequence("PED_CERTIDOES_TIPOS_SEQ").proximo
    data_pedido = str(timezone.now().date())
    vigencia_id = str(get_vigencia_atual_firebird(db))
    valores = get_valores_protocolo_fb(
        vigencia_id,
        codigo_tabela,
        estado_civil_id,
        db,
    )

    if valores is None:
        logging.error(
            "Não foi possível obter os valores da protocolo. Verifique os parâmetros.",
        )
        return None

    valor_fundo_estado = "{:,.2f}".format(
        Decimal(valores["emolumento"] * (valores["valor_fundo_estado"] / 100)),
    )

    valor = Decimal(valores["valor"]) + Decimal(valores["valor_fundo_estado"])

    comando = """
    INSERT INTO PED_CERTIDOES_TIPOS (
        CHAVE_PED_CERTIDOES_TIPOS, CHAVE_PED_CERTIDOES, TIPO_CERTIDAO, QUANTIDADE,
        VALOR, TX_JUDICIARIA, CODIGO_TABELA, ADIC_VALOR, CHAVE_FUNCIONARIOS,
        TAXA1, DATAPEDIDO, CATEGORIA, CHAVE_VIGOR, VALOR_FUNDOESTADO
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """

    params = (
        sequence_tipo_protocolo,
        pedido_id,
        valores["tipo_protocolo"],
        quantidade,
        valor,
        valores["tx_judiciaria"],
        codigo_tabela,
        valores["valor_adicionado"],
        funcionario_id,
        valor_fundo_estado,
        data_pedido,
        estado_civil_id,
        vigencia_id,
        valores["valor_adicionado"],
    )

    logger.info(f"FB: Gravando tipos do pedido. ID: {pedido_id}")

    try:
        db.execute_command(comando, params)
    except Exception:
        logging.exception(f"ERRO ao gravar TIPOS do pedido: '{pedido_id}'.: ")
        raise

    return sequence_tipo_protocolo


def gravar_andamentos_pedido(
    pedido_id,
    data,
    funcionario_id,
    tipo_andamento_id,
    db: FbConnection,
):
    andamento_id = db.sequence("ANDAMENTOS_PED_CERTIDOES_SEQ").proximo

    comando = """
        INSERT INTO ANDAMENTOS_PED_CERTIDOES (
            CHAVE_ANDAMENTOS, CHAVE_PED_CERTIDOES, DATA,
            CHAVE_FUNCIONARIOS, CHAVE_SERVICOS_ANDAMENTOS,
            CHAVE_FUNCIONARIOS_DESTINO
        )
        VALUES (?, ?, CURRENT_TIMESTAMP, ?, ?, ?)
    """
    parametros = (
        andamento_id,
        pedido_id,
        funcionario_id,
        tipo_andamento_id,
        funcionario_id,
    )

    logger.info(f"FB: GRAVANDO ANDAMENTO DO PEDIDO DE CERTIDÃO NO FB. ID: {pedido_id}")

    try:
        db.execute_command(comando, parametros)
    except Exception:
        logging.exception(f"ERRO AO GRAVAR ANDAMENTO DO PEDIDO. ID: '{pedido_id}': ")
        raise

    return andamento_id


def atualizar_pedido(
    pedido_id: int | str,
    coluna_pedido: str,
    coluna_item: str,
    db,
) -> int:
    """
    Atualiza o valor de uma coluna específica em um pedido no banco de dados com base na soma de uma coluna relacionada.

    Parâmetros:
    - pedido_id: Identificador do pedido (int ou str).
    - coluna_pedido: Nome da coluna do pedido a ser atualizada.
    - coluna_item: Nome da coluna dos itens a ser somada.
    - db: Conexão com o banco de dados (deve implementar o método execute_command).

    Retorno:
    - 1 se a operação for bem-sucedida, 0 se ocorrer um erro.
    """
    # Valida se o pedido_id foi informado
    if not pedido_id:
        logging.error("ID do pedido não foi fornecido.")
        return 0

    try:
        # Prepara o comando SQL usando parâmetros para evitar SQL Injection
        comando = f"""
            UPDATE PED_CERTIDOES
            SET {coluna_pedido} = (
                SELECT SUM({coluna_item})
                FROM PED_CERTIDOES_TIPOS
                WHERE CHAVE_PED_CERTIDOES = ?
            )
            WHERE CHAVE_PED_CERTIDOES = ?
        """

        parametros = (pedido_id, pedido_id)

        # Log da operação
        logging.info(f"FB: Atualizando pedido. ID: {pedido_id}")

        # Executa o comando SQL com os parâmetros fornecidos
        db.execute_command(comando, parametros)

    except Exception as e:
        # Log detalhado do erro ocorrido
        logging.exception(f"ERRO ao ATUALIZAR pedido. ID: '{pedido_id}': {e}")
        return 0

    # Retorna 1 indicando sucesso
    return 1


def atualizar_pedido_talao(pedido_id, valor_coluna, db: FbConnection) -> int:
    if not pedido_id:
        return 1

    str_id = str(pedido_id)
    comando = f"""
            UPDATE PEDIDOS SET NROTALAO = {valor_coluna}
            WHERE CHAVE_PEDIDOS = {str_id}
        """
    logger.info(f"FB: Atualizando pedido. ID: {str_id}")

    try:
        db.execute_command(comando)
    except Exception:
        logging.exception(f"ERRO ao ATUALIZAR pedido. ID: '{str_id}': ")
        raise

    return 1


def atualizar_pedido_protocolo(
    pedido_id,
    coluna_pedido,
    coluna_item,
    db: FbConnection,
) -> int:
    if not pedido_id:
        return 1

    pedido_id = str(pedido_id)
    try:
        comando = f"""
            UPDATE PEDIDOS SET {coluna_pedido} = (
                SELECT SUM({coluna_item})
                FROM PEDIDOS_ITENS
                WHERE CHAVE_PEDIDOS = {pedido_id}
            )
            WHERE CHAVE_PEDIDOS = {pedido_id}
        """
        logger.info(
            f"FB: Atualizando pedido protocolo. ID {pedido_id}. "
            "Somando {coluna_item} em {coluna_pedido}",
        )

        db.execute_command(comando)

    except Exception:
        logging.exception(f"ERRO ao ATUALIZAR pedido. ID: '{pedido_id}': ")
        raise

    return 1


def atualizar_contador_pedido(db: FbConnection):
    comando = """ UPDATE CONTADOR SET NROPEDIDO = NROPEDIDO + 1 """

    try:
        db = FbConnection() if db is None else db
        db.execute_command(comando)

    except Exception:
        logging.exception("ERRO ID: ")
        raise


def atualizar_contador_nroordem(db: FbConnection) -> None:
    comando = """ UPDATE CONTADOR
                SET NROORDEM  = NROORDEM  + 1,
                    NROTALAO  = NROTALAO  + 1
            """

    try:
        db.execute_command(comando)
    except Exception:
        logging.exception("ERRO ao atualizar CAIXA do pedido. ID: ")
        raise


# Obter o numero do pedido
def get_contador(item: str, db: FbConnection):
    logger.info(f"Obtendo contador para {item.upper()}.")
    if not item:
        logger.error("Item não pode ser None.")
        return None

    query = f"SELECT {item.upper()} FROM CONTADOR"

    try:
        resultados = db.execute_query(query)
        if not resultados:
            logger.warning(f"Nenhum resultado retornado na consulta de {item}.")
            return None

        result = resultados[0]
        values = list(result.values())

        if not values:
            logger.warning(f"Nenhum valor encontrado para {item}.")
            return None

        contador = values[0]
        logger.info(f"Sequencia para {item.upper()} é: {contador}")
        return contador

    except Exception as e:
        logger.exception(f"ERRO ao obter {item}: {e}")
        return None


# Atualizar os parameetros de data
def atualizar_parametro(texto, origem, destino):
    return texto.replace(origem, destino)


def gravar_caixa_do_protocolo_no_firebird(
    pedido_id: int,
    valor: Decimal,
    funcionarios_id: int,
    descricao: str,
    db: FbConnection,
) -> int | dict | None:
    """
    Grava uma transação de caixa no banco de dados Firebird e retorna o registro inserido.

    Parâmetros:
    - pedido_id (int): ID do pedido associado à transação.
    - valor (Decimal): Valor da transação.
    - funcionarios_id (int): ID do funcionário que executou a transação.
    - descricao (str): Descrição da transação.
    - db (FbConnection): Conexão com o banco de dados Firebird.

    Retorna:
    - int: 1 em caso de falha devido a pedido_id inválido.
    - dict: Dicionário com os dados do registro inserido em caso de sucesso.
    - None: em caso de falha ao executar a consulta ou outro erro não específico.
    """
    # Verifica se o pedido_id é válido
    if not pedido_id:
        return 1

    try:
        # Obtém a data atual no formato do banco de dados
        data = db.data_str

        # Gera a próxima chave para o registro no CAIXA
        caixa_id = db.sequence("CAIXA_SEQ").proximo

        # Monta o comando SQL usando placeholders para evitar injeção de SQL
        comando_insert = """
            INSERT INTO CAIXA (CHAVE_CAIXA, TIPOTRANSACAO, TIPODOCUMENTO,
            CHAVE_PEDIDOS, DATAPAGAMENTO, VALOR, CHAVE_FUNCIONARIOS, DESCRICAO, CHEQUE)
            VALUES (?, 1, 1, ?, ?, ?, ?, ?, 'F');
        """

        # Dados que serão inseridos na query
        parametros_insert = (
            caixa_id,  # CHAVE_CAIXA
            pedido_id,  # CHAVE_PEDIDOS
            data,  # DATAPAGAMENTO
            valor,  # VALOR
            funcionarios_id,  # CHAVE_FUNCIONARIOS
            descricao.replace(
                "'",
                "`",
            ),  # DESCRICAO (evita injeção SQL removendo aspas simples)
        )

        # Executa o comando de inserção no banco de dados
        db.execute_command(comando_insert, parametros_insert)

        # Consulta para obter o registro completo recém-inserido
        comando_select = """
            SELECT * FROM CAIXA WHERE CHAVE_CAIXA = ?;
        """
        parametros_select = (caixa_id,)

        # Executa a consulta e retorna o resultado
        resultado = db.execute_query(comando_select, parametros_select)

        # Retorna o primeiro registro encontrado
        return resultado[0] if resultado else None

    except Exception as e:
        # Loga o erro e retorna uma indicação de falha
        print(f"Erro ao gravar no CAIXA ou recuperar o registro: {e}")
        return None


def selar_protocolo_prenotacao_no_sql_server(
    numero_protocolo: int,
    pedido_id: int,
    ato,
):
    print("Iniciando a selagem do protocolo no SQL SERVER. Pedido ID: ", pedido_id)

    # valores individuais
    # codigo_tabela, emolumento, recompe, tfj, issqn = ato.get_codigo_tabela_emolumento

    with transaction.atomic():
        try:
            retorno = sqlserver.selar_protocolo(numero_protocolo, ato)
            if retorno:
                # PedidoCertidao.registrar_andamento_selo(numero_protocolo)
                return retorno
            else:
                (
                    "Não foi possivel selar: Verifique se já foi selada anteriormente. Protocolo: "
                    + str(numero_protocolo)
                )
                # raise Exception(msg)
                return None
        except Exception as e:
            logger.exception(f"Erro ao selar certidão: {e}")
            raise


def obter_data_utilizacao(db: FbConnection) -> str:
    """Obtém a data de utilização no formato esperado para a consulta SQL."""
    return f"'{db.data()!s}'"


def atualizar_selo_no_firebird(
    pedido_id: int,
    pedido_item_id: int,
    db: FbConnection,
) -> None:
    if isinstance(pedido_item_id, tuple):
        pedido_item_id = pedido_item_id[0]
    elif isinstance(pedido_item_id, int):
        # Se já for um inteiro, pode continuar com o valor como está
        pedido_item_id = int(pedido_item_id)
    else:
        # Opcional: Lidar com outros tipos inesperados
        pedido_item_id = 0

    """Atualiza o selo no banco de dados Firebird para marcar como utilizado."""
    comando = """
        UPDATE SELO_DIGITAL_MG
        SET UTILIZADO = 'S',
            CHAVE_PEDIDOS = :CHAVE_PEDIDOS,
            CHAVE_PEDIDOS_ITENS = :CHAVE_ITENS,
            DATA_UTILIZACAO = :DATA_UTILIZACAO,
            SELO_PARA_CONSULTA = 'S'
        WHERE CODIGO_SEQUENCIAL_UNICO = (
            SELECT MIN(CODIGO_SEQUENCIAL_UNICO)
            FROM SELO_DIGITAL_MG
            WHERE CANCELADO = 'N'
            AND UTILIZADO = 'N'
        );
    """

    comando = comando.replace(":CHAVE_PEDIDOS", str(pedido_id))
    comando = comando.replace(":CHAVE_ITENS", str(pedido_item_id))
    comando = comando.replace(":DATA_UTILIZACAO", obter_data_utilizacao(db))

    try:
        db.execute_command(comando)
    except Exception as e:
        logging.exception("Erro ao atualizar o selo no Firebird: %s", e)
        raise


def buscar_selo(db: FbConnection, pedido_item_id: int) -> tuple[Any, Any] | None:
    if isinstance(pedido_item_id, tuple):
        pedido_item_id = pedido_item_id[0]
    elif isinstance(pedido_item_id, int):
        # Se já for um inteiro, pode continuar com o valor como está
        pedido_item_id = int(pedido_item_id)
    else:
        # Opcional: Lidar com outros tipos inesperados
        pedido_item_id = 0

    """Busca o selo no banco de dados Firebird com base no ID do item do pedido."""
    try:
        results = db.execute_query(
            f"""
            SELECT CODIGO_SEQUENCIAL_UNICO, CODIGO_DE_SEGURANCA
            FROM SELO_DIGITAL_MG
            WHERE CHAVE_PEDIDOS_ITENS = {pedido_item_id!s}
            """,
        )
        if not results:
            logging.warning(
                "Nenhum selo encontrado para o item do pedido: %s",
                pedido_item_id,
            )
            return None
        return results[0]["CODIGO_SEQUENCIAL_UNICO"], results[0]["CODIGO_DE_SEGURANCA"]
    except Exception as e:
        logging.exception("Erro ao buscar o selo no Firebird: %s", e)
        raise


def buscar_senha_consulta(db: FbConnection, pedido_id: int) -> str | None:
    """Busca a senha de consulta no banco de dados Firebird com base no ID do pedido."""
    try:
        results_senha = db.execute_query(
            f"""
            SELECT FSENHACONSULTA
            FROM PROTOCOLOS
            WHERE CHAVE_PEDIDOS = {pedido_id!s}
            """,
        )
        if not results_senha:
            logging.warning(
                "Nenhuma senha de consulta encontrada para o pedido: %s",
                pedido_id,
            )
            return None
        return results_senha[0]["FSENHACONSULTA"]
    except Exception as e:
        logging.exception("Erro ao buscar a senha de consulta no Firebird: %s", e)
        raise


def selar_protocolo_no_firebird(
    pedido_id: int,
    pedido_item_id: int,
    db: FbConnection,
) -> tuple[Any, Any, str] | None:
    """
    Sela o protocolo no banco de dados Firebird, marcando o selo como utilizado e retornando as informações necessárias.

    Retorna uma tupla com o código sequencial, código de segurança e senha de consulta, ou None se não for possível selar o protocolo.
    """
    if not pedido_item_id:
        logging.warning("ID do item do pedido não fornecido.")
        return None

    try:
        # Atualiza o selo no Firebird
        atualizar_selo_no_firebird(pedido_id, pedido_item_id, db)

        # Busca o selo atualizado
        selo = buscar_selo(db, pedido_item_id)
        if selo is None:
            return None

        # Busca a senha de consulta
        senha_consulta = buscar_senha_consulta(db, pedido_id)
        if senha_consulta is None:
            return None

        return selo[0], selo[1], senha_consulta

    except Exception as e:
        logging.exception("Erro ao selar o protocolo no Firebird: %s", e)
        raise


def gravar_andamento_do_protocolo_no_fb(
    protocolo_id: int,
    funcionario_id: int,
    servico_id: int,
    db: FbConnection,
) -> int | None:
    """Grava o andamento do protocolo no banco de dados Firebird."""
    if not protocolo_id:
        return 1

    comando = """
        INSERT INTO ANDAMENTOS (
            CHAVE_ANDAMENTOS,
            CHAVE_PROTOCOLOS,
            DATA,
            CHAVE_FUNCIONARIOS,
            CHAVE_SERVICOS_ANDAMENTOS
        )
        VALUES (?, ?, CURRENT_TIMESTAMP, ?, ?);
    """

    andamento_id = db.sequence("ANDAMENTOS_SEQ").proximo

    parametros = (
        andamento_id,  # CHAVE_ANDAMENTOS
        protocolo_id,  # CHAVE_PROTOCOLOS
        funcionario_id,  # CHAVE_FUNCIONARIOS
        servico_id,  # CHAVE_SERVICOS_ANDAMENTOS
    )

    # Salvar no banco de dados
    try:
        db.execute_command(comando, parametros)
    except Exception:
        logging.exception(f"ERRO ao atualizar PROTOCOLO. ID: {protocolo_id}")
        raise


def gravar_protocolo_firebird(
    pedido_id: int,
    titulo_id: int,
    observacao: str,
    db: FbConnection,
) -> tuple[int, int]:
    if not pedido_id:
        return (1, 1)

    comando = """
        INSERT INTO PROTOCOLOS (CHAVE_PROTOCOLOS, NROORDEM, CHAVE_PEDIDOS,
            DATAPROTOCOLO, CHAVE_TITULOS, NRORECIBOUSADO, OBSERVACAO, NUMEROPEDIDOCRI, COD_INTERNET)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """

    # GERAR SENHA ALEATÓRIA
    numero_senha_aleatorio = gerar_numero_aleatorio(6)

    protocolo_id = db.sequence("PROTOCOLOS_SEQ").proximo

    nroordem = int(get_contador("NROORDEM", db)) + 1
    atualizar_contador_nroordem(db)

    numero_talao = int(get_contador("NROTALAO", db)) + 1

    numero_recibo_usado = int(get_contador("NRORECIBO", db)) + 1
    atualizar_contador_pedido(db)

    data_protocolo = db.data()
    numero_pedido_cri = ""  # Aqui representando o valor vazio, anteriormente concatenado como uma string vazia

    observacao = observacao if observacao != "None" else ""

    parametros = (
        protocolo_id,
        nroordem,
        pedido_id,
        data_protocolo,
        titulo_id,
        numero_recibo_usado,
        observacao,
        numero_pedido_cri,
        numero_senha_aleatorio,
    )

    # Salvar no banco de dados - PEDIDOS ITENS
    try:
        db.execute_command(comando, parametros)

        # ATUALIZAR O TALÃO
        atualizar_pedido_talao(pedido_id, numero_talao, db)

        return nroordem, protocolo_id
    except Exception:
        logging.exception("ERRO ao atualizar PROTOCOLO. Chave")
        raise


# Gerar um número aleatório inteiro entre 0 e 999999
def gerar_numero_aleatorio(quantidade_digitos=6):
    import random

    numero_senha_aleatorio = random.randint(0, 999999)

    # Formatá-lo como uma string de tamanho 6
    return str(numero_senha_aleatorio).zfill(quantidade_digitos)


def get_codigo_webservice_selo(codigo_tabela="0000-0", tributacao_id=1):
    """BUSCAR NA BASE O HISTORICO DE CODIGO DE WEBSERVICE."""
    print("FB: Obtendo número do CODIGO_WEBSERVICE. Codigo tabela: ", codigo_tabela)

    query = """
        SELECT DISTINCT(CHAVE_EMOLUMENTO_WS_GO)
        FROM PEDIDOS_ITENS
        WHERE CHAVE_EMOLUMENTO_WS_GO IS NOT NULL
        AND   ANO_REFERENCIA_TABELA = :ano_vigencia
        AND   CODIGO_TABELA = :codigo_tabela
        AND   CODIGO_TIPO_TRIBUTACAO = :codigo_tipo_tributacao
    """

    ano_vigencia = str(timezone.now().year)
    codigo_tabela = str("'" + codigo_tabela + "'")

    # SQL SEM TRIBUTACAO
    query_sem_tributacao = str(
        str(query).replace(
            "AND   CODIGO_TIPO_TRIBUTACAO = :codigo_tipo_tributacao",
            "",
        ),
    )

    query = str(query).replace(":ano_vigencia", ano_vigencia)
    query = str(query).replace(":codigo_tabela", codigo_tabela)
    query = str(query).replace(":codigo_tipo_tributacao", str(tributacao_id))

    # SQL SEM TRIBUTACAO
    query_sem_tributacao = str(query_sem_tributacao).replace(
        ":ano_vigencia",
        ano_vigencia,
    )
    query_sem_tributacao = str(query_sem_tributacao).replace(
        ":codigo_tabela",
        codigo_tabela,
    )
    query_sem_tributacao = str(query_sem_tributacao).replace(
        " SELECT DISTINCT(CHAVE_EMOLUMENTO_WS_GO) ",
        " SELECT MAX(CHAVE_EMOLUMENTO_WS_GO) AS CHAVE_EMOLUMENTO_WS_GO ",
    )

    print(query)

    with FbConnection() as db:
        db.begin_transaction()

        try:
            result = db.execute_query(query)[0]
        except Exception:
            result = db.execute_query(query_sem_tributacao)[0]

    return result["CHAVE_EMOLUMENTO_WS_GO"] if result else 66


def calcular_valor_para_exportar(
    tipo_tributacao_id,
    valor_emolumento,
    valor_fundo_estado,
    valor_tfj,
    valor_issqn,
):
    """
    Calcula os valores para exportação com base no tipo de tributação.
    Verificando se o emolumento é exportado de outro item, e aplicando o percentual correspondente.
    Exemplo: ISENTO, 50 OU 75%.
    """
    from apps.home.templatetags.home_formatos import arrendamento_bancario

    percentuais = {
        50: Decimal(0.5),
        75: Decimal(0.25),
        100: Decimal(0),
    }
    percentual = percentuais.get(tipo_tributacao_id, Decimal(1))

    valores = [valor_emolumento, valor_fundo_estado, valor_tfj, valor_issqn]

    # Aplica o percentual e arredonda todos os valores em uma única linha
    valores = [arrendamento_bancario(valor * percentual, 2) for valor in valores]

    return tuple(valores)


class AtoUtils:
    """Classe utilitária para manipulação de atos entre o Postgres e o Firebird."""

    def obter_ato_no_fb(self: "Ato", db: FbConnection):
        if not self.id:
            msg = "O ato não possui um ID válido."
            raise ValueError(msg)

        if not self.pedido_id:
            msg = "O ato não possui um pedido associado."
            raise ValueError(msg)

        query = """
            SELECT *
            FROM PEDIDOS_ITENS
            WHERE CHAVE_PEDIDOS = ?
            AND CODIGO_TABELA = ?
        """

        parametros = (self.pedido_id, self.id)

        try:
            return db.execute_query(query, parametros)[0]
        except Exception as e:
            logging.exception(f"Erro ao obter ato no Firebird: {e}")
            raise

    def excluir_ato_no_fb(self: "Ato", db: FbConnection):
        """Exclui todos os registros do ato no Firebird relacionados ao pedido."""
        if not self.numero_pedido:
            msg = "O ato não possui um numero de pedido válido."
            raise ValueError(msg)

        if not self.codigo_tabela:
            msg = "O ato não possui um código de tabela válido."
            raise ValueError(msg)

        db.execute_command(
            "DELETE FROM PEDIDOS_ITENS WHERE CHAVE_PEDIDOS = ? AND CODIGO_TABELA = ?",
            (self.numero_pedido, self.codigo_tabela),
        )

    def criar_ato_no_fb(self: "Ato", db: FbConnection):
        """Cria um novo ato no Firebird."""
        data_pagamento = db.now()
        return inserir_pedido_item(
            db=db,
            pedido_item_id=db.sequence("PEDIDOS_ITENS_SEQ").proximo,
            pedido_id=self.pedido.chave_pedido_fb,
            ato_id=self.home_ato_id,
            titulo_id=self.tipo_titulo.home_titulo_protocolo_id,
            colaborador_id=self.criado_por_id,
            emolumento_id=self.emolumento.home_emolumento_id,
            data_pagamento=data_pagamento,
            quantidade=self.quantidade,
            tipo_imovel=self.imovel_tipo_registro_sigla,
            numero_imovel=self.imovel_numero_registro,
            numero_ri=self.imovel_cartorio,
            numero_ato=self.numero_ato,
            codigo_tabela=self.codigo_tabela,
            valor_emolumento=self.valor_emolumento,
            valor_fundo_estado=self.valor_fundo_estado,
            valor_tfj=self.valor_tfj,
            valor_issqn=self.valor_issqn,
            valor_itbi=self.valor_itbi,
            valor_avaliacao=self.valor_avaliacao,
            numero_titulo=self.numero_titulo,
            valor_total=self.valor_total,
            custas=self.custas,
            codigo_atoselo=self.codigo_ato_selo,
            chave_emolumento_ws_go=self.chave_emolumento_ws_go,
        )


def obter_chave_pedido_fb_pelo_numero(numero_pedido: str) -> str:
    db = FbConnection()
    query = """
        SELECT CHAVE_PEDIDOS
        FROM PEDIDOS
        WHERE NROPEDIDO = ?
    """
    try:
        result = db.execute_query(query, (numero_pedido,))
        return str(result[0]["CHAVE_PEDIDOS"]) if result else None
    except Exception as e:
        logging.exception(f"Erro ao obter chave do pedido no Firebird: {e}")
        raise
