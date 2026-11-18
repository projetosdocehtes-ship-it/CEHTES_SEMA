import logging
import os
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import TYPE_CHECKING, Any

import numpy as np
from django.apps import apps
from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone

from apps.home import helpers, models
from apps.home.helpers import apenas_numeros, get_custas_firebird
from apps.home.padroes import PRENOTACAO, PROVISORIO
from apps.home.utils.importacao_de_protocolo_firebird import *
from apps.home.utils.libreoffice import converter_rtf_para_html
from core.utils.firebird_utils import FbConnection
from core.utils.formatacoes import somente_numeros

logger = logging.getLogger(__name__)
logger.debug(f"Iniciando {__name__}")

if TYPE_CHECKING:
    from apps.home.models import (
        Colaborador,
        Financeiro,
        Livro01Andamento,
        PedidoCertidao,
    )


def get_parametros_de_conexao_postgre():
    logger.info("POSTGRE: Carregando parametros de conexão com o banco de dados.")

    parametros_postgre = {
        "host": os.getenv("DB_HOST", "127.0.0.1"),
        "database": os.getenv("DB_NAME", "cartorio"),
        "user": os.getenv("DB_USERNAME", "postgres"),
        "password": os.getenv("DB_PASS", "password"),
    }

    logger.info(
        f"POSTGRE: Parametros de conexão carregados: {parametros_postgre['host']}:{parametros_postgre['database']}",
    )

    return parametros_postgre


def get_pedido_fb(pedido_id, db: FbConnection):
    logger.info(f"Obtendo pedido: {pedido_id}")

    # query SQL a executar
    query = f"""
        SELECT CHAVE_PEDIDOS, TIPOSERVICO, NROTALAO, TALAOIMPRESSO, NRORECIBO,
            DATAENTRADA, DATAPREVISTA, DATAENTREGA, TIPOCERTIDAO, TIPOREGISTRO,
            NUMEROREGISTRO, SETOR, QUADRA, LOTE, RUA, NUMERODOCUMENTOAPRES,
            ENDERECO, TELEFONE, MUNICIPIO, UF, NUMERODOCUMENTOCONJUGE,
            NOMEADQUIRENTE, NOMETRANSMITENTE, OBSERVACAO, VALORPEDIDO,
            VALOREMOLUMENTO, VALORRECEITAADICIONAL, VALORFINAL, VALORACERTO,
            HORAENTRADA, VALORRECEITAADICIONAL2, EMAIL, HISTORICO, NROPEDIDO,
            NOMEAPRESENTANTE, TIPODOCUMENTOAPRES, TAXA1, TAXA2, TAXA3, TAXA4,
            TAXA5, TAXA6, HISTORICO2, CHAVE_PEDIDOS_ANTERIOR, VALORRECIBO,
            NUMERODOCUMENTOADIQ, TEXTONOMES, BANCO, AGENCIA, CONTA_CORRENTE,
            TIPO_CONTA, FONEMANOMEAPRESENTANTE, FONEMANOMEADQUIRENTE,
            FONEMANOMETRANSMITENTE, DATAESCRITURA, VALORDEVOLVIDO,
            VALORESZERADOS, CHAVE_FUNCIONARIOS, VALOR_ITEM_SEPARADO,
            CHAVE_ESPECIE_TITULOS, CHAVE_TIPOS_REGISTROS, CHAVE_NATUREZAS_ESCRITURAS,
            LAVRADO_RIO, SELO_ESCRITURA, CHAVE_SERVENTIAS, DATA_ESCRITURA,
            LIVRO_ESCRITURA, FOLHA_INI_ESCRITURA, FOLHA_FIM_ESCRITURA, ATO_ESCRITURA,
            POR_PROCURACAO, CHAVE_TIPOS_AVERBACOES, ULTIMO_REGISTRO, OUTROS,
            SELOPRENOTACAO, OBSERVACAO2, NROPEDIDO_ORIGEM, PEDIDO_IMPRESSO,
            CHAVE_PED_CERTIDOES, CUPOMIMPRESSO, PAGAMENTO, NOMEFUNCRESPONSAVEL,
            OBSERVACAO_TEMP, COD_ISENCAO, MOTIVO_ISENCAO, TEXTONOTADEVOLUCAO,
            TITULAR_CONTA, DOCUMENTO_TITULAR, QTD_RECIBO_IMPRESSO, CODIGODEPOSITOPREVIO,
            EXIBIRDUPLICADO, VALOR_FUNARPENRJ, OBSADICIONAL, VALOR_FUNEMP, PROTOCOLO_ANTERIOR,
            PROTOCOLO_POSTERIOR, TIPOTRANSACAO, VINCULAR_PEDIDO_CERTIDAO, TELEFONE5,
            TELEFONE4, TELEFONE1, TELEFONE2, TELEFONE3, NUMERO_SELO_NOTAS, TAXA7, TAXA8,
            TAXA9, TAXA10, TAXA11, TAXA12, TAXA13, TAXA14, TAXA15, DATANOTA,
            DATABASECALCULO, NOME_SERVENTIA, NUMEROPEDIDOCRI, DETALHES, OPERACAO,
            DOCUMENTO_CONSUMIDOR, NRONOTADEVOLUCAO, CHAVE_FUNCIONARIOS_DISTR, STATUS_DISTRIBUICAO,
            ORDEMDISTRIBUICAOORC, NOME_MAE_APRES, NOME_PAI_APRES, PROFISSAO_APRES,
            UNIAO_ESTAVEL_APRES, CHAVE_CATEGORIAS_APRES, NACIONALIDADE_APRES, DATA_VALIDADE,
            NOVO_PEDIDO_BASE_NESTE
        FROM PEDIDOS
        WHERE CHAVE_PEDIDOS = {pedido_id!s}
    """
    resultado = db.execute_query(query)

    if not resultado:
        msg = "Pedido não encontrado."
        logger.error(msg)
        return None

    logger.debug(f"O pedido obtido é: {resultado[0]['CHAVE_PEDIDOS']}")

    return resultado[0]


def get_pedido_por_numero_fb(numero_pedido: str, db: FbConnection):
    logger.info(f"Obtendo pedido pelo numero: {numero_pedido}")

    # query SQL a executar
    query = """
        SELECT CHAVE_PEDIDOS, TIPOSERVICO, NROTALAO, TALAOIMPRESSO, NRORECIBO,
            DATAENTRADA, DATAPREVISTA, DATAENTREGA, TIPOCERTIDAO, TIPOREGISTRO,
            NUMEROREGISTRO, SETOR, QUADRA, LOTE, RUA, NUMERODOCUMENTOAPRES,
            ENDERECO, TELEFONE, MUNICIPIO, UF, NUMERODOCUMENTOCONJUGE,
            NOMEADQUIRENTE, NOMETRANSMITENTE, OBSERVACAO, VALORPEDIDO,
            VALOREMOLUMENTO, VALORRECEITAADICIONAL, VALORFINAL, VALORACERTO,
            HORAENTRADA, VALORRECEITAADICIONAL2, EMAIL, HISTORICO, NROPEDIDO,
            NOMEAPRESENTANTE, TIPODOCUMENTOAPRES, TAXA1, TAXA2, TAXA3, TAXA4,
            TAXA5, TAXA6, HISTORICO2, CHAVE_PEDIDOS_ANTERIOR, VALORRECIBO,
            NUMERODOCUMENTOADIQ, TEXTONOMES, BANCO, AGENCIA, CONTA_CORRENTE,
            TIPO_CONTA, FONEMANOMEAPRESENTANTE, FONEMANOMEADQUIRENTE,
            FONEMANOMETRANSMITENTE, DATAESCRITURA, VALORDEVOLVIDO,
            VALORESZERADOS, CHAVE_FUNCIONARIOS, VALOR_ITEM_SEPARADO,
            CHAVE_ESPECIE_TITULOS, CHAVE_TIPOS_REGISTROS, CHAVE_NATUREZAS_ESCRITURAS,
            LAVRADO_RIO, SELO_ESCRITURA, CHAVE_SERVENTIAS, DATA_ESCRITURA,
            LIVRO_ESCRITURA, FOLHA_INI_ESCRITURA, FOLHA_FIM_ESCRITURA, ATO_ESCRITURA,
            POR_PROCURACAO, CHAVE_TIPOS_AVERBACOES, ULTIMO_REGISTRO, OUTROS,
            SELOPRENOTACAO, OBSERVACAO2, NROPEDIDO_ORIGEM, PEDIDO_IMPRESSO,
            CHAVE_PED_CERTIDOES, CUPOMIMPRESSO, PAGAMENTO, NOMEFUNCRESPONSAVEL,
            OBSERVACAO_TEMP, COD_ISENCAO, MOTIVO_ISENCAO, TEXTONOTADEVOLUCAO,
            TITULAR_CONTA, DOCUMENTO_TITULAR, QTD_RECIBO_IMPRESSO, CODIGODEPOSITOPREVIO,
            EXIBIRDUPLICADO, VALOR_FUNARPENRJ, OBSADICIONAL, VALOR_FUNEMP, PROTOCOLO_ANTERIOR,
            PROTOCOLO_POSTERIOR, TIPOTRANSACAO, VINCULAR_PEDIDO_CERTIDAO, TELEFONE5,
            TELEFONE4, TELEFONE1, TELEFONE2, TELEFONE3, NUMERO_SELO_NOTAS, TAXA7, TAXA8,
            TAXA9, TAXA10, TAXA11, TAXA12, TAXA13, TAXA14, TAXA15, DATANOTA,
            DATABASECALCULO, NOME_SERVENTIA, NUMEROPEDIDOCRI, DETALHES, OPERACAO,
            DOCUMENTO_CONSUMIDOR, NRONOTADEVOLUCAO, CHAVE_FUNCIONARIOS_DISTR, STATUS_DISTRIBUICAO,
            ORDEMDISTRIBUICAOORC, NOME_MAE_APRES, NOME_PAI_APRES, PROFISSAO_APRES,
            UNIAO_ESTAVEL_APRES, CHAVE_CATEGORIAS_APRES, NACIONALIDADE_APRES, DATA_VALIDADE,
            NOVO_PEDIDO_BASE_NESTE
        FROM PEDIDOS
        WHERE NROPEDIDO = ?
    """
    parametros = (numero_pedido,)
    resultado = db.execute_query(query, parametros)

    if not resultado:
        msg = "Pedido não encontrado."
        logger.error(msg)
        return None

    # logger.debug(f"O pedido obtido é: {resultado[0]["CHAVE_PEDIDOS"]}")
    logger.debug(f"O pedido obtido do FB possui o ID: {resultado[0]['CHAVE_PEDIDOS']}")

    return resultado[0]


def get_pedido_por_numero_onr_fb(numero_pedido_onr: str, db: FbConnection):
    if not numero_pedido_onr:
        return None

    logger.info(f"Obtendo pedido pelo numero da ONR: {numero_pedido_onr}")

    # query SQL a executar
    query = """
        SELECT *
        FROM PED_CERTIDOES
        WHERE NUMEROPEDIDOCRI = ?
    """
    parametros = (numero_pedido_onr,)
    resultado = db.execute_query(query, parametros)

    if not resultado:
        msg = "Pedido não encontrado."
        logger.error(msg)
        return None

    # logger.debug(f"O pedido obtido é: {resultado[0]["CHAVE_PEDIDOS"]}")
    logger.debug(
        f"O pedido obtido do FB possui o ID: {resultado[0]['CHAVE_PED_CERTIDOES']}",
    )

    return resultado[0]


def get_pedido_itens_fb(
    pedido_id: int,
    pedido_id_item: int,
    db: FbConnection,
) -> dict:
    print("ITENS: Obtendo itens para o Pedido: ", pedido_id)
    parcial = f"AND CHAVE_PEDIDOS_ITENS = {pedido_id_item}" if pedido_id_item else ""

    query = f"""
        SELECT CHAVE_PEDIDOS_ITENS, CHAVE_PEDIDOS, CHAVE_ATOS, CHAVE_TITULOS, PRENOTACAO,
            BUSCA, UNIDADES, HIPOTECA, MATRICULA, CERTIDAO, SFH, FOLHASARQUIVO, NROIMOVEIS,
            VALORITBI, VALORAVALIACAO, VALOREMOLUMENTO, VALORRECEITAADICIONAL1, VALORTOTALITEM,
            TIPO_IMOVEL, NUMERO_IMOVEL, ENCERRADO, ALTERACAO, UNIDADE, QUADRA, NUMEROATO,
            REGISTRADO, VALORRECEITAADICIONAL2, CUSTAS, TABELACALCULO, CDHU, NUMERO_RI,
            FATOR, IMPDAE, TAXA1, TAXA2, TAXA3, TAXA4, TAXA5, TAXA6, LIVRO, FOLHA, DATA_PAGAMENTO,
            NROTITULO, IMPETIQUETA, SELO, CHAVE_VIGOR, COMPLEMENTO, INDICACAO, INFORMARATO,
            CODIGO_TABELA, CHAVE_FUNCIONARIOS, NUMSELO, TIPO_GUIA, NUMERO_GUIA, LIVRO_MATRICULA,
            FOLHA_MATRICULA, TEXTOCONVERSAO, NROCHAVEPEDIDO_ANTERIOR, NAORECOLHERDAE, VALORESZERADOS,
            NRO_ITEM_GESCART, NRORECIBO, PEDIDO_ITEM_PRINCIPAL, TABELA, TABELA_ITEM, INDICADOXML,
            CHAVE_ESCREVENTE, ULTIMO_REGISTRO, CHAVE_ESPECIE_TITULOS, CHAVE_TIPOS_REGISTROS,
            CHAVE_NATUREZAS_ESCRITURAS, LAVRADO_RIO, SELO_ESCRITURA, CHAVE_SERVENTIAS, DATA_ESCRITURA,
            LIVRO_ESCRITURA, FOLHA_INI_ESCRITURA, FOLHA_FIM_ESCRITURA, ATO_ESCRITURA, POR_PROCURACAO,
            CHAVE_TIPOS_AVERBACOES, OUTROS, NOME_SERVENTIA, NUMEROATO_DOI, CHAVE_EMOLUMENTOS_GRUPOS,
            NUMEROATOINTEIRO, ETQ_MARCADA, FOLHAINTEIRO, NUMERO_IMOVEL_INT, SELO_ANO, SELO_LOTE,
            VALORIMPOSTO, ARRECADADORA, APENAS_MOV_SELO, CHAVE_FUNCIONARIOS_ALT, SELOS_ITENS,
            DATA_GERACAO_SELO, OBS_ATO, NRORELATORIO, VALOR_FUNARPENRJ, EMOLUMENTOLIQ, VALOR_FUNEMP,
            MOTIVODAREDUCAO, VALOR_FUNDOESTADO, TEXTO1, TEXTO2, TEXTO3, TEXTO4,
            TEXTO5, GERANDO_ETQ, NROETIQUETA, GRUPOLANCAMENTO, DATA_ACERTO_ITEM, TEXTO6, TEXTO7,
            TEXTO8, TEXTO9, TEXT10, TIPO_ATO_DISTRIBUICAO, CIDADE_ESCRITURA, FICHA, QTDE_ESCRITURA,
            UF_ESCRITURA, NUMERO_REGAUX, GUIA_DARJ_PE, CODIGO_TRIB_ISENCAO, CUPOMIMPRESSOITEM,
            NUMEROATO_AUX, CODIGO_VALIDACAO, CODIGO_ATOSELO, ATO_GRATUITO, TAXA7, TAXA8, TAXA9,
            TAXA10, TAXA14, TAXA13, TAXA15, CHAVE_EMOLUMENTO_WS_GO, TAXA11, TAXA12, COD_ISENCAO,
            MOTIVO_ISENCAO, ATO_IMPRESSO, USOMINUTA, ORIGEM_ITEM_DAJE, IDENTIFICACAO_PAGAMENTO,
            CODIGO_TIPO_TRIBUTACAO, ANO_REFERENCIA_TABELA, HECTARE, NUMERO_PEDIDO_ELETRONICO,
            CHAVE_REDUCAO, QTDE_MATRICULA, CHAVE_DESCONTO_LEGAL, CHAVE_TIPO_ISENCAO, LEI_3525_TO,
            POSTERGADO
        FROM PEDIDOS_ITENS
        WHERE CHAVE_PEDIDOS = {pedido_id!s}

        {parcial}

        ORDER BY CHAVE_PEDIDOS_ITENS ASC
    """

    db = FbConnection() if db is None else db
    resultados = db.execute_query(query)

    if not resultados:
        print("Não foram encontrados itens para o pedido:", pedido_id)
        return None

    print(
        "ITENS: obtidos:",
        [item["CHAVE_PEDIDOS_ITENS"] for item in resultados],
    )

    return resultados


def protocolo_posterior_existe_fb(
    numero_protocolo: str,
    texto_localizar: str,
    db: FbConnection,
) -> bool:
    """Verifica se um protocolo existe no Firebird e retorna True ou False."""
    query = f"SELECT PE.EMAIL FROM PROTOCOLOS PR, PEDIDOS PE WHERE PR.NROORDEM = {numero_protocolo!s} AND PR.CHAVE_PEDIDOS = PE.CHAVE_PEDIDOS AND PE.EMAIL LIKE {texto_localizar!s} "
    resultado = db.execute_query(query)

    if resultado:
        return resultado[0]["EMAIL"]
    else:
        return None


def protocolo_existe_fb(numero_protocolo: str, db: FbConnection) -> bool:
    """Verifica se um protocolo existe no Firebird e retorna True ou False."""
    query = f"SELECT COUNT(NROORDEM) FROM PROTOCOLOS WHERE NUMEROPEDIDOCRI = {numero_protocolo!s}"
    quantidade = db.execute_query(query)[0]["COUNT"]

    return quantidade > 0


def get_selos_do_pedido_fb(pedido_id, db: FbConnection):
    print("SELOS: Obtendo selos para o Pedido: ", pedido_id)
    # Comando SQL a executar
    query = f"""
        SELECT CHAVE_SELO_DIGITAL_MG, CODIGO_SEQUENCIAL_UNICO, CODIGO_DE_SEGURANCA,
            DATA_IMPORTACAO, DATA_UTILIZACAO, SELO_PARA_CONSULTA, UTILIZADO,
            CANCELADO, CHAVE_PEDIDOS, CHAVE_PEDIDOS_ITENS, CHAVE_PED_CERTIDOES,
            CHAVE_PED_CERTIDOES_TIPOS, CHAVE_PED_CERTIDOES_TIPOS_CANC,
            CHAVE_PED_CERTIDOES_CANC, CHAVE_PEDIDOS_ITENS_CANC, CHAVE_PEDIDOS_CANC,
            DATA_CANCELAMENTO, CHAVE_FUNCIONARIOS, DATA_ENVIO, CHAVE_FUNCIONARIOS_CANC,
            CHAVE_FUNCIONARIOS_ENVIO, CONFIRMADO, ENVIADO, SELOSITE, DATASELOSITE,
            CHAVE_SELOS_EXPORTACAO_WEB, NUMERO_IMOVEL, CHAVE_PED_CERTIDOES_IMOVEIS
        FROM SELO_DIGITAL_MG
        WHERE CHAVE_PEDIDOS = {pedido_id}
        ORDER BY CHAVE_SELO_DIGITAL_MG ASC
    """

    db = FbConnection() if db is None else db
    resultados = db.execute_query(query)
    # return resultado[0] if resultado else None

    if not resultados:
        print("Não foram encontrados selos para o pedido:", pedido_id)
        return None

    # print("Os selos obtidos são:", [selo["CHAVE_SELO_DIGITAL_MG"] for selo in retorno])

    return resultados


def get_andamentos_do_protocolo_no_fb(protocolo_id, db: FbConnection):
    logger.info(f"ANDAMENTOS: Obtendo andamentos para o Protocolo ID: {protocolo_id}")

    query = f"""
        SELECT CHAVE_ANDAMENTOS,
               CHAVE_PROTOCOLOS,
               DATA,
               CHAVE_FUNCIONARIOS,
               CHAVE_SERVICOS_ANDAMENTOS,
               CHAVE_FUNCIONARIOS_DESTINO,
               OBSERVACAO
        FROM ANDAMENTOS
        WHERE CHAVE_PROTOCOLOS = {protocolo_id}
        ORDER BY DATA DESC
        """

    db = FbConnection() if db is None else db
    resultados = db.execute_query(query)

    for andamento_fb in resultados:
        print("ANDAMENTOS: Importando andamento. ID:", andamento_fb["CHAVE_ANDAMENTOS"])
        andamento_fb["OBSERVACAO"] = converter_rtf_blob_para_html(
            blob_original=andamento_fb["OBSERVACAO"],
        )

    if not resultados:
        logger.info(
            f"ANDAMENTOS: Não foram encontrados andamentos para o protocolo com ID: {protocolo_id}",
        )
        return None

    logger.info(
        f"ANDAMENTOS: {len(resultados)} andamentos obtidos para o protocolo com ID: {protocolo_id}",
    )

    return resultados


def get_registros_caixa_do_pedido_fb(pedido_id, db: FbConnection):
    query = f"""
        SELECT CHAVE_CAIXA, CHAVE_PEDIDOS, DATAPAGAMENTO, DESCRICAO, TIPOTRANSACAO, TIPODOCUMENTO,
            VALOR, CHEQUE, CHAVE_PED_CERTIDOES, CHAVE_FUNCIONARIOS, NROORDEM_EC, CHAVE_FUNCIONARIOS_PAGO
        FROM CAIXA
        WHERE CHAVE_PEDIDOS = {pedido_id}
        ORDER BY CHAVE_CAIXA ASC
        """

    db = FbConnection() if db is None else db
    resultado = db.execute_query(query)
    # return resultado[0] if resultado else None

    if not resultado:
        logger.warning(f"Não foram encontrados caixa para o pedido: {pedido_id}")
        return None

    print(
        "CAIXA: A quantidade de registros de caixa obtido é:",
        len(resultado),
    )

    return resultado


def get_protocolo_fb(numero_protocolo, db: FbConnection) -> dict:
    query = f"""
        SELECT CHAVE_PROTOCOLOS, NROORDEM, CHAVE_PEDIDOS, DATAPROTOCOLO, CHAVE_TITULOS,
            OBSVALORES, FORAHORARIO, NAORECOLHERDAE, NRORECIBOUSADO, STATUS, OBSERVACAO,
            CODIGO_STATUS, SELECIONAR, LEMBRETES, CHAVE_FUNCIONARIOS, NROVIAS, FSENHACONSULTA,
            DATARELATORIO, OBSERVACAO2, COD_INTERNET, CHAVE_FASE, ORIGEM_PEDIDO, NOMEFUNCBUSCA, NUMEROPEDIDOCRI
        FROM PROTOCOLOS
        WHERE NROORDEM = {numero_protocolo}
    """

    resultado = db.execute_query(query)

    if not resultado:
        logger.warning(
            f"Não foram encontrados protocolos com o número: {numero_protocolo}",
        )
        return None

    print("PROTOCOLOS: Protocolo: Nº ", numero_protocolo)

    return resultado[0] if resultado else None


def get_protocolo_fb_por_id(protocolo_id, db: FbConnection):
    query = f"""
        SELECT CHAVE_PROTOCOLOS, NROORDEM, CHAVE_PEDIDOS, DATAPROTOCOLO, CHAVE_TITULOS,
            OBSVALORES, FORAHORARIO, NAORECOLHERDAE, NRORECIBOUSADO, STATUS, OBSERVACAO,
            CODIGO_STATUS, SELECIONAR, LEMBRETES, CHAVE_FUNCIONARIOS, NROVIAS, FSENHACONSULTA,
            DATARELATORIO, OBSERVACAO2, COD_INTERNET, CHAVE_FASE, ORIGEM_PEDIDO, NOMEFUNCBUSCA
        FROM PROTOCOLOS
        WHERE CHAVE_PROTOCOLOS = {protocolo_id}
    """

    resultado = db.execute_query(query)
    resultado = resultado[0] if resultado else None

    if not resultado:
        logger.warning(f"Não foram encontrados protocolos com o ID: {protocolo_id}")
        return None

    print("PROTOCOLOS: Protocolo: Nº ", resultado["NROORDEM"])

    return resultado


def get_protocolo_fb_por_pedido_id(pedido_id, db: FbConnection):
    query = f"""
        SELECT CHAVE_PROTOCOLOS, NROORDEM, CHAVE_PEDIDOS, DATAPROTOCOLO, CHAVE_TITULOS,
            OBSVALORES, FORAHORARIO, NAORECOLHERDAE, NRORECIBOUSADO, STATUS, OBSERVACAO,
            CODIGO_STATUS, SELECIONAR, LEMBRETES, CHAVE_FUNCIONARIOS, NROVIAS, FSENHACONSULTA,
            DATARELATORIO, OBSERVACAO2, COD_INTERNET, CHAVE_FASE, ORIGEM_PEDIDO, NOMEFUNCBUSCA
        FROM PROTOCOLOS
        WHERE CHAVE_PEDIDOS = {pedido_id}
    """

    resultado = db.execute_query(query)
    resultado = resultado[0] if resultado else None

    if not resultado:
        logger.warning(f"Não foram encontrados protocolos com o ID: {pedido_id}")
        return None

    print("PROTOCOLOS: Protocolo: Nº ", resultado["NROORDEM"])

    return resultado


def get_emolumentos_fb():
    query = """
        SELECT CHAVE_EMOLUMENTOS, NOME, TIPO, ANOVIGOR, DESCONTO, UTILIZADO, UTILIZADO,
            ATOCORELACIONADO, RECOLHERFUNDO, DESCRICAO, ORDEM, CHAVE_ATOS_SELOS, INATIVO ,
            GERARSELO, SELO_ISENTO, MOTIVOREDUCAO, MOTIVOISENCAO, CODISENCAO, ANOTACOES,
            CODIGO_TABELA_INICIAL, ATIVARTAXA1 , ATIVARTAXA3 , ATIVARTAXA4 , ATIVARTAXA5 ,
            ATIVARTAXA6 , TIPOCALCULOTAXA1, TIPOCALCULOTAXA3, TIPOCALCULOTAXA4, TIPOCALCULOTAXA5,
            TIPOCALCULOTAXA6, USARCODIGO_ATODOITEM, USARFATOREMOLUMENTO , TIPOCALCULOTAXA2,
            ATIVARTAXA2 ,CALCULO_ROUND_TRUNC1, CALCULO_ROUND_TRUNC2, CALCULO_ROUND_TRUNC3,
            CALCULO_ROUND_TRUNC4, CALCULO_ROUND_TRUNC6, CALCULO_ROUND_TRUNC5, GERAR_SELOS_PRENOTACAO,
            ATIVARTAXA8 , ATIVARTAXA7 , NOMETAXA1, NOMETAXA15, CALCULO_ROUND_TRUNC13, ATIVARTAXA13,
            ATIVARTAXA12, ATIVARTAXA15, ATIVARTAXA11, ATIVARTAXA10, ATIVARTAXA9 , NOMETAXA14,
            NOMETAXA4, NOMETAXA7, NOMETAXA6, NOMETAXA5, NOMETAXA8, NOMETAXA3, NOMETAXA2,
            CHAVE_EMOLUMENTO_WS_GO, NOMETAXA13, NOMETAXA12, NOMETAXA11, NOMETAXA10, NOMETAXA9,
            CALCULO_ROUND_TRUNC14, CALCULO_ROUND_TRUNC11, CALCULO_ROUND_TRUNC12, TIPOCALCULOTAXA15,
            TIPOCALCULOTAXA14, CALCULO_ROUND_TRUNC10, ATIVARTAXA14, TIPOCALCULOTAXA13,
            TIPOCALCULOTAXA12, TIPOCALCULOTAXA11, CALCULO_ROUND_TRUNC15, TIPOCALCULOTAXA7,
            TIPOCALCULOTAXA8, TIPOCALCULOTAXA10, CALCULO_ROUND_TRUNC7, CALCULO_ROUND_TRUNC8,
            TIPOCALCULOTAXA9, CALCULO_ROUND_TRUNC9, ORIGEM_CERTIDAO , CHAVE_ROTINAS_SELO_MA,
            CODIGO_ATO
        FROM EMOLUMENTOS
        """

    # Execute the SELECT statement:
    emolumentos = []
    with FbConnection() as db:
        resultados = db.execute_query(query)

    [emolumentos.append(emolumento) for emolumento in resultados]

    try:
        emolumentos[0][0]
    except Exception:
        logger.exception("ERRO")
        emolumentos = None

    return emolumentos


def get_vigencia_do_emolumentos_fb(db: FbConnection):
    print("VIGORES: Obtenda vigencia.")
    query = """
       SELECT CHAVE_VIGOR, INICIO, FIM, DESCRICAO, VALOR_UFESP,
            ATUALIZOU_ATOS_SELOS
            EXIBIR_TABELA_VIGOR, REFERENCIA, CODIGO_ATO_TABELA
       FROM EMOLUMENTOS_VIGOR
    """
    db = FbConnection() if db is None else db
    resultados = db.execute_query(query)
    vigencia_do_emolumentos_fb = list(resultados)

    try:
        vigencia_do_emolumentos_fb[0]["CHAVE_VIGOR"]
    except Exception:
        logger.exception("ERRO")
        vigencia_do_emolumentos_fb = None

    return vigencia_do_emolumentos_fb


def get_protocolos_por_data_de_entrada_fb(
    data_entrada_inicio,
    data_entrada_fim,
    db: FbConnection,
):
    query = f"""
        SELECT NROORDEM
        FROM PROTOCOLOS
        WHERE DATAPROTOCOLO >= '{data_entrada_inicio} 00:00:00'
        AND DATAPROTOCOLO <= '{data_entrada_fim} 23:59:59'
        ORDER BY NROORDEM DESC
        """
    db = FbConnection() if db is None else db
    resultado = db.execute_query(query)
    return resultado if resultado else []


def get_protocolos_por_data_de_andamento_fb(
    data_andamento_inicio,
    data_andamento_fim,
    db: FbConnection,
):
    query = f"""
        SELECT DISTINCT(NROORDEM)
        FROM PROTOCOLOS AS P
        JOIN ANDAMENTOS A ON A.CHAVE_PROTOCOLOS = P.CHAVE_PROTOCOLOS
        WHERE A.DATA >= '{data_andamento_inicio} 00:00:00'
        AND A.DATA <= '{data_andamento_fim} 23:59:59'
        ORDER BY NROORDEM DESC
        """
    db = FbConnection() if db is None else db
    resultado = db.execute_query(query)
    return resultado if resultado else []


# Gravar Pedido Item no FIRBIRD
def criar_pedido_item_no_fb(
    pedido_id: int,
    ato_id: int,
    titulo_id: int,
    emolumento_id: int,
    numero_id: int,
    tipo_id: int,
    tributacao_id: int,
    valor_documento: Decimal,
    valor_avaliacao: Decimal,
    numero_ato_id: int,
    quantidade: int,
    custas_id: int,
    ri_id: int,
    colaborador: "Colaborador",
    db: FbConnection,
):
    db_era_none = db is None
    if db is None:
        db_era_none = True
        db = FbConnection()
        db.begin_transaction()

    pedidos_itens_seq = db.sequence("PEDIDOS_ITENS_SEQ").proximo

    pedidos_item_id = str(pedidos_itens_seq) if pedidos_itens_seq is not None else None

    # Get o ATO e TITULO
    ato_id = str(ato_id)
    titulo_id = str(titulo_id)
    emolumento_id = str(emolumento_id)
    quantidade = str(quantidade)

    ato_id = int(str(ato_id))
    titulo_id = int(str(titulo_id))
    emolumento_id = int(str(emolumento_id))
    quantidade = int(str(quantidade))

    # VALORES DO DOCUMENTO
    # valor_documento = str(valor_documento).replace(".", "")
    valor_documento = str(valor_documento).replace(",", "")
    # valor_avaliacao = str(valor_avaliacao).replace(".", "")
    valor_avaliacao = str(valor_avaliacao).replace(",", "")

    query = " SELECT MAX(CHAVE_VIGOR) FROM EMOLUMENTOS_VIGOR "
    resultado = db.execute_query(query)
    # return resultado if resultado else []

    vigencia_id = (
        str(resultado[0]["MAX"])
        if resultado is not None and len(resultado) > 0 and len(resultado[0]) > 0
        else None
    )

    lista_valores = firebird_get_emolumento(
        valor_documento,
        emolumento_id,
        vigencia_id,
        db,
    )

    # emolumento_id = Emolumentos.objects.get(nome=PROVISORIO)

    try:
        valor_issqn = (Decimal(lista_valores[0][5] * quantidade) / 100) * Decimal(
            lista_valores[0][0] * quantidade,
        )
    except Exception:
        valor_issqn = 0

        try:
            valor_total_item = str(
                Decimal(lista_valores[0][0] * quantidade)
                + Decimal(lista_valores[0][1] * quantidade)
                + Decimal(lista_valores[0][2] * quantidade)
                + Decimal(valor_issqn),
            )
        except Exception:
            logger.exception("ERRO")
            valor_total_item = 0

        data_pagamento = db.now()

        # colaborador_id = 0
        ano_id = 0

        comando = """
        INSERT INTO PEDIDOS_ITENS (
            CHAVE_PEDIDOS_ITENS,
            CHAVE_PEDIDOS,
            CHAVE_ATOS,
            CHAVE_TITULOS,
            VALORITBI,
            VALORAVALIACAO,
            VALOREMOLUMENTO,
            VALORRECEITAADICIONAL1,
            VALORTOTALITEM,
            TIPO_IMOVEL,
            NUMERO_IMOVEL,
            NUMEROATO,
            CUSTAS,
            TABELACALCULO,
            CDHU,
            NUMERO_RI,
            DATA_PAGAMENTO,
            NROTITULO,
            CHAVE_VIGOR,
            CODIGO_TABELA,
            CHAVE_FUNCIONARIOS,
            VALOR_FUNDOESTADO,
            DATA_ACERTO_ITEM,
            ANO_REFERENCIA_TABELA,
            UNIDADES,
            HIPOTECA,
            MATRICULA,
            CERTIDAO,
            SFH,
            FOLHASARQUIVO,
            TAXA1,
            VALORRECEITAADICIONAL2,
            TAXA2,
            TAXA3,
            TAXA4,
            TAXA5,
            TAXA6,
            EMOLUMENTOLIQ,
            TABELA_ITEM,
            CHAVE_EMOLUMENTOS_GRUPOS,
            TAXA9,
            TAXA10,
            TAXA7,
            TAXA8,
            TAXA14,
            TAXA15,
            TAXA13,
            TAXA12,
            TAXA11,
            CODIGO_ATOSELO,
            CODIGO_TIPO_TRIBUTACAO,
            ENCERRADO
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """

        parametros = (
            pedidos_item_id,  # CHAVE_PEDIDOS_ITENS
            pedido_id,  # CHAVE_PEDIDOS
            ato_id,  # CHAVE_ATOS
            titulo_id,  # CHAVE_TITULOS
            valor_avaliacao,  # VALORITBI
            valor_documento,  # VALORAVALIACAO
            lista_valores[0][0] * quantidade,  # VALOREMOLUMENTO
            lista_valores[0][1] * quantidade,  # VALORRECEITAADICIONAL1
            valor_total_item,  # VALORTOTALITEM
            tipo_id,  # TIPO_IMOVEL
            numero_id,  # NUMERO_IMOVEL
            numero_ato_id,  # NUMEROATO
            custas_id,  # CUSTAS
            emolumento_id,  # TABELACALCULO
            quantidade,  # CDHU
            ri_id,  # NUMERO_RI
            data_pagamento,  # DATA_PAGAMENTO
            titulo_id,  # NROTITULO
            vigencia_id,  # CHAVE_VIGOR
            lista_valores[0][3],  # CODIGO_TABELA
            colaborador.pk,  # CHAVE_FUNCIONARIOS
            lista_valores[0][2] * quantidade,  # VALOR_FUNDOESTADO
            data_pagamento,  # DATA_ACERTO_ITEM
            ano_id,  # ANO_REFERENCIA_TABELA
            0,  # UNIDADES
            "F",  # HIPOTECA
            0,  # MATRICULA
            0,  # CERTIDAO
            "F",  # SFH
            0,  # FOLHASARQUIVO
            valor_issqn,  # TAXA1
            0,  # VALORRECEITAADICIONAL2
            0,  # TAXA2
            0,  # TAXA3
            0,  # TAXA4
            0,  # TAXA5
            0,  # TAXA6
            0,  # EMOLUMENTOLIQ
            0,  # TABELA_ITEM
            0,  # CHAVE_EMOLUMENTOS_GRUPOS
            0,  # TAXA9
            0,  # TAXA10
            0,  # TAXA7
            0,  # TAXA8
            0,  # TAXA14
            0,  # TAXA15
            0,  # TAXA13
            0,  # TAXA12
            0,  # TAXA11
            0,  # CODIGO_ATOSELO
            1,  # CODIGO_TIPO_TRIBUTACAO,
            "F",  # ENCERRADO
        )

        if db_era_none:
            db = FbConnection()
            db.begin_transaction()
            db.execute_command(comando, parametros)
            db.commit()
            db.close()
        else:
            db.execute_command(comando, parametros)

    return pedidos_item_id, pedido_id


# Exibir os dados do protocolo - Item
def firebird_get_emolumento(
    valor,
    emolumento_id,
    vigencia_id,
    db: FbConnection,
) -> list:
    query = f"""
        SELECT EI.EMOLUMENTO, EI.VALOR, EI.ADIC_EMOLUMENTO, EI.CODIGO_TABELA, EI.CHAVE_EMOLUMENTOS_ITENS, TAXA1
        FROM EMOLUMENTOS_ITENS EI
        JOIN EMOLUMENTOS E ON E.CHAVE_EMOLUMENTOS = EI.CHAVE_EMOLUMENTOS
        WHERE {valor!s} BETWEEN EI.VL_INICIO AND EI.VL_FIM
        AND EI.CHAVE_EMOLUMENTOS = {emolumento_id!s}
        AND EI.CHAVE_VIGOR = {vigencia_id!s}
        """

    db = FbConnection() if db is None else db
    resultado = db.execute_query(query)
    return resultado[0] if resultado else []


# # Exibir os dados do protocolo - Item
# def firebird_get_todos_emolumento(codigo_tabela) -> list:
#     codigo_tabela = "'" + str(codigo_tabela) + "%'"

#     query = """
#         SELECT EI.VL_INICIO, EI.VL_FIM, EI.EMOLUMENTO, EI.VALOR, EI.ADIC_EMOLUMENTO, EI.CODIGO_TABELA, EI.CHAVE_EMOLUMENTOS_ITENS, TAXA1
#         FROM EMOLUMENTOS_ITENS EI
#         WHERE EI.CODIGO_TABELA LIKE (codigo_tabela)
#         ORDER BY EI.CHAVE_EMOLUMENTOS_ITENS DESC
#         """
#     query = query.replace("codigo_tabela", codigo_tabela)

#     # print(query)

#     db = FbConnection()
#     return db.execute_query(query)


# Selecionar Sequence
def get_sequence_firebird(nome_sequence, db: FbConnection) -> int:
    query = f" SELECT GEN_ID({nome_sequence}, 1) FROM RDB$DATABASE "
    db = FbConnection() if db is None else db
    resultado = db.execute_query(query)
    # return resultado[0] if resultado else None
    if resultado and len(resultado) > 0:
        return resultado[0]
    else:
        logger.warning("Nenhum resultado encontrado ou falha na consulta.")
        return None  # ou lançar uma exceção


def converter_rtf_blob_para_html(blob_original: bytes):
    # Verifica se o blob é nulo, vazio ou contém apenas bytes nulos
    if blob_original is None or not blob_original.strip(b"\x00"):
        print("Não há texto para converter.")
        return None

    # Assume que a função converter_rtf_para_html espera uma sequência de bytes
    return converter_rtf_para_html(blob_original) or None


# Gerar protocolo a ser importado
def get_partes_do_pedido(pedido_id, db: FbConnection) -> dict:
    query = f"""
        SELECT P.CHAVE_PEDIDOS, P.NOMEADQUIRENTE, P.NOMEAPRESENTANTE, P.NOMETRANSMITENTE
        FROM   PEDIDOS P
        WHERE  P.CHAVE_PEDIDOS = {pedido_id!s}
    """

    db = FbConnection() if db is None else db
    resultados = db.execute_query(query)

    if not resultados:
        logger.info(f"Não foram encontrados PESSOAS para o pedido: {pedido_id}")
        return None

    print("Pessoa encontrada para o pedido.")

    return resultados


def get_atos_fb():
    query = """
            SELECT CHAVE_ATOS, TIPOATO, CODIGO_NATUREZA_JURIDICA, COM_ONUS,
                EXIBIR, TIPO, DOI, EXIBIRPROTOCOLO, USAR_PERCENTUAL, CODIGO_DOI, TIPO_PROCESSO_ERIDF,
                GRAUDIFICULDADE, TEMPOMEDIO, ORDEM_ATOS_REL_PROT, ORDEM_ATOS_PRATICADOS, NROOBRIGATORIO,
                CHAVE_ANDAMENTOS, INDICAR_ATO_LIVROPROTOCOLO, SOLICITARVALOR, SOLICITARVALORALIENACAO, NROOBRIGATORIOATO,
                CHAVE_GRUPOS, TIPO_REQUERIMENTO_CENTRAL,
                CHAVE_TIPO_TRANSACAO, CODIGO_TIPO_SELO
            FROM ATOS
            """

    with FbConnection() as db:
        resultados = db.execute_query(query)

    if not resultados:
        logger.warning("Nenhum Ato foi encontrado.")
        return None

    print("A quantidade de ATOS obtida é:", len(resultados))

    return resultados


def get_ato_fb_por_id(ato_id, db: FbConnection):
    # logger.info(f"Obtendo ATO com ID: {ato_id}")
    query = f"""
        SELECT CHAVE_ATOS, TIPOATO, CODIGO_NATUREZA_JURIDICA, COM_ONUS,
            EXIBIR, TIPO, DOI, EXIBIRPROTOCOLO, USAR_PERCENTUAL, CODIGO_DOI, TIPO_PROCESSO_ERIDF,
            GRAUDIFICULDADE, TEMPOMEDIO, ORDEM_ATOS_REL_PROT, ORDEM_ATOS_PRATICADOS, NROOBRIGATORIO,
            CHAVE_ANDAMENTOS, INDICAR_ATO_LIVROPROTOCOLO, SOLICITARVALOR, SOLICITARVALORALIENACAO, NROOBRIGATORIOATO,
            CHAVE_GRUPOS, TIPO_REQUERIMENTO_CENTRAL, CHAVE_TIPO_TRANSACAO, CODIGO_TIPO_SELO
        FROM ATOS
        WHERE CHAVE_ATOS = {ato_id}
        """

    if db is None:
        db = FbConnection()
        resultado = db.execute_query(query)
        db.close()
    else:
        resultado = db.execute_query(query)

    if not resultado:
        print("Nenhum foi atos foi encontrado.")
        return None

    return resultado[0] if resultado else None


# Gerar todas os imovel_vinculado
def importar_tipo_regime_casamento_do_fb(
    estado_id_civil: str,
    db: FbConnection,
) -> dict:
    query = f"""
                SELECT CHAVE_CATEGORIAS, TIPOCATEGORIA
                FROM CATEGORIAS
                WHERE CHAVE_CATEGORIAS = {estado_id_civil}
            """

    resultado = db.execute_query(query)
    resultado = resultado[0] if resultado else None

    if not resultado:
        print("Não foi encontrado CATEGORIA com o ID:", estado_id_civil)
        return None

    return resultado


def importar_estado_civil_regime_do_fb():
    query = """ SELECT CHAVE_CATEGORIAS, TIPOCATEGORIA
                FROM CATEGORIAS
                """

    with FbConnection() as db:
        resultados = db.execute_query(query)

    if not resultados:
        print("Não foi encontrado CATEGORIAS")
        return None

    return resultados


# Gerar pedidos itens a ser importado
def get_selos_nao_usados_do_fb():
    query = """
        SELECT CODIGO_SEQUENCIAL_UNICO, CHAVE_SELO_DIGITAL_MG, CODIGO_DE_SEGURANCA
        FROM SELO_DIGITAL_MG
        WHERE CHAVE_PEDIDOS IS NULL
        AND CHAVE_PED_CERTIDOES IS NULL
        AND CANCELADO = 'N'
        ORDER BY CHAVE_SELO_DIGITAL_MG ASC
        """

    with FbConnection() as db:
        resultados = db.execute_query(query)

    if not resultados:
        print("Nenhum foi SELO foi encontrado.")
        return None

    print(f"A quantidade de SELOS obtida é: {len(resultados)}")

    return resultados


# Pesquisar por numero em aberto
def get_protocolos_modificados_na_ultima_hora(db: FbConnection) -> list:
    query = """
            SELECT DISTINCT(P.NROORDEM)
            FROM ANDAMENTOS A
            JOIN PROTOCOLOS P ON A.CHAVE_PROTOCOLOS = P.CHAVE_PROTOCOLOS
            WHERE A.DATA BETWEEN DATEADD(HOUR, -1, CURRENT_TIMESTAMP) AND CURRENT_TIMESTAMP
            ORDER BY P.NROORDEM DESC
        """

    db = FbConnection() if db is None else db
    resultados = db.execute_query(query)

    if not resultados:
        print("Nenhum protocolo foi modificado na última hora.")

    return resultados if resultados else []


def get_protocolos_fb_modificados_nos_ultimos_30_dias(db: FbConnection) -> list:
    query = """
            SELECT DISTINCT(P.NROORDEM)
            FROM ANDAMENTOS A
            JOIN PROTOCOLOS P ON A.CHAVE_PROTOCOLOS = P.CHAVE_PROTOCOLOS
            WHERE CAST(A.DATA AS DATE) BETWEEN CAST(DATEADD(-1000 DAY TO CURRENT_DATE) AS DATE)
            AND CAST(CURRENT_DATE AS DATE)
            ORDER BY P.NROORDEM DESC
        """

    db = FbConnection() if db is None else db
    resultados = db.execute_query(query)

    if not resultados:
        logger.info("Nenhum protocolo foi modificado nos últimos 30 dias.")

    return resultados if resultados else []


# OBTER OS ANDAMENTOS DO PROTOCOLO DO ULTIMO DIA UTIL
def get_protocolos_modificados_ultimo_dia_util(db: FbConnection) -> list:
    # Dicionário para mapear o dia da semana a um valor específico
    mapeamento_dias = {5: 1, 6: 2}  # Sábado mapeado para 1, Domingo para 2

    # Usar o método get para retornar o valor correspondente ao dia da semana, ou 0 se não for sábado ou domingo
    try:
        dias_uteis = mapeamento_dias.get(timezone.now().date().weekday(), 1)
    except:
        dias_uteis = 40

    # OBTER A DATA DO DIA ATUAL
    query = f"""
            SELECT DISTINCT(P.NROORDEM)
            FROM ANDAMENTOS A
            JOIN PROTOCOLOS P ON A.CHAVE_PROTOCOLOS = P.CHAVE_PROTOCOLOS
            WHERE CAST(A.DATA AS DATE) BETWEEN CAST(DATEADD(-{dias_uteis!s} DAY TO CURRENT_DATE) AS DATE)
            AND CAST(CURRENT_DATE AS DATE)
            ORDER BY P.NROORDEM DESC
        """

    db = FbConnection() if db is None else db
    resultado = db.execute_query(query)
    logger.info(f"Resultado do protocolo modificado no último dia útil: {resultado}")
    return resultado if resultado else []


# OBTER O CAIXA DO ULTIMO DIA UTIL
def get_caixa_modificados_ultimo_dia_util(db: FbConnection) -> list:
    # Usar o método get para retornar o valor correspondente ao dia da semana, ou 0 se não for sábado ou domingo
    dias_uteis = 1

    # OBTER A DATA DO DIA ATUAL
    query = f"""
            SELECT C.*
            FROM CAIXA C
            WHERE CAST(C.DATAPAGAMENTO AS DATE) BETWEEN CAST(DATEADD(-{dias_uteis!s} DAY TO CURRENT_DATE) AS DATE)
            AND CAST(CURRENT_DATE AS DATE)
            ORDER BY C.CHAVE_CAIXA DESC
        """

    db = FbConnection() if db is None else db
    resultado = db.execute_query(query)
    logger.info(f"Resultado do caixa modificado no último dia útil: {resultado}")
    return resultado if resultado else []


def get_protocolos_modificados_ultimos_2_dias(db: FbConnection) -> list:
    query = """
            SELECT DISTINCT(P.NROORDEM)
            FROM ANDAMENTOS A
            JOIN PROTOCOLOS P ON A.CHAVE_PROTOCOLOS = P.CHAVE_PROTOCOLOS
            WHERE CAST(A.DATA AS DATE) BETWEEN CAST(DATEADD(-2 DAY TO CURRENT_DATE) AS DATE)
            AND CAST(CURRENT_DATE AS DATE)
            ORDER BY P.NROORDEM DESC
        """

    resultado = db.execute_query(query)
    return resultado if resultado else []


def get_andamentos_protocolos_modificados(db: FbConnection) -> list:
    cartorio_model = apps.get_model("cartorios", "Cartorio")

    # DATA DO SINCRONIS
    data_sincronismo = cartorio_model.data_hora_sincronismo
    if not data_sincronismo:
        data_sincronismo = datetime.datetime.now() - datetime.timedelta(days=3)
        data_sincronismo = data_sincronismo.strftime(settings.DATETIME_FIREBIRD_FORMAT)

    query = f"""
                SELECT A.CHAVE_ANDAMENTOS, A.CHAVE_PROTOCOLOS, A.DATA,
                    A.CHAVE_FUNCIONARIOS, A.CHAVE_SERVICOS_ANDAMENTOS, A.CHAVE_FUNCIONARIOS_DESTINO
                FROM ANDAMENTOS A
                WHERE A.DATA >= '{data_sincronismo}'
                """

    resultado = db.execute_query(query)
    return resultado if resultado else []


def get_andamentos_protocolos_modificados_pelo_id(
    andamento: "Livro01Andamento",
    db: FbConnection,
) -> list:
    print("get_andamentos_protocolos_modificados_pelo_id")

    # Converter a lista de ids em uma string separada por vírgulas
    lista_andamentos_ids = ", ".join(
        str(andamento_id) for andamento_id in andamento.values_list("id", flat=True)
    )
    if not lista_andamentos_ids:
        return []

    query = f"""
            SELECT A.CHAVE_ANDAMENTOS, A.CHAVE_PROTOCOLOS, A.DATA,
                A.CHAVE_FUNCIONARIOS, A.CHAVE_SERVICOS_ANDAMENTOS, A.CHAVE_FUNCIONARIOS_DESTINO
            FROM ANDAMENTOS A
            WHERE A.CHAVE_ANDAMENTOS IN ( {lista_andamentos_ids!s} )
            """

    print("Resultado da lista_andamento")

    resultado = db.execute_query(query)
    return resultado if resultado else []


def get_andamentos_protocolo_pk(protocolo_id: int, db: FbConnection) -> list:
    print("Iniciando o get_andamentos_protocolos protocolo_pk", str(protocolo_id))

    if not protocolo_id:
        return []

    query = f"""
            SELECT A.CHAVE_ANDAMENTOS, A.CHAVE_PROTOCOLOS, A.DATA,
                A.CHAVE_FUNCIONARIOS, A.CHAVE_SERVICOS_ANDAMENTOS, A.CHAVE_FUNCIONARIOS_DESTINO
            FROM ANDAMENTOS A
            WHERE A.CHAVE_PROTOCOLOS = {protocolo_id!s}
            """

    print("Resultado do protocolo pk: ", str(protocolo_id))

    resultado = db.execute_query(query)
    return resultado if resultado else []


# GRAVANDO NO FIREBIRD - CAIXA
def gravar_caixa_do_protocolo_no_firebird(
    pedido_id,
    valor,
    funcionarios_id,
    descricao,
    db: FbConnection,
) -> None:
    comando = """
            INSERT INTO CAIXA(CHAVE_CAIXA, TIPOTRANSACAO, TIPODOCUMENTO,
                CHAVE_PEDIDOS, DATAPAGAMENTO, VALOR, CHAVE_FUNCIONARIOS, DESCRICAO, CHEQUE)
            VALUES(:CHAVE_CAIXA, 1, 1,
                :CHAVE_PEDIDOS, :DATAPAGAMENTO, :VALOR, :CHAVE_FUNCIONARIOS, ' :DESCRICAO ', 'F');
            """

    caixa_id = db.sequence("CAIXA_SEQ").proximo

    # FORMATAR OS VALORES
    # valor = re.sub(r"(\d)\.(\d{3})", r"\1\2", valor).replace(",", ".")
    valor = str(valor)

    comando = comando.replace(":CHAVE_CAIXA", str(caixa_id))
    comando = comando.replace(":CHAVE_PEDIDOS", str(pedido_id))
    comando = comando.replace(":DATAPAGAMENTO", db.data_str)
    comando = comando.replace(":VALOR", valor)
    comando = comando.replace(":CHAVE_FUNCIONARIOS", str(funcionarios_id))
    comando = comando.replace(":DESCRICAO", str(descricao))

    try:
        db.execute_command(comando)
    except Exception:
        logging.exception("ERRO ao atualizar PROTOCOLO")
        raise


def atualizar_valor_acerto_no_fb(pedido_id: int, db: FbConnection) -> None:
    # from core.utils.firebird_utils import FbConnection

    # if not valor_coluna:
    #     return None

    if not pedido_id:
        return 1

    str_id = str(pedido_id)

    # FORMATAR OS VALORES
    # valor_coluna = re.sub(r"(\d)\.(\d{3})", r"\1\2", valor_coluna).replace(",", ".")

    try:
        comando = f"""
            UPDATE PEDIDOS
            SET VALORACERTO = ( SELECT SUM(VALOR) FROM CAIXA WHERE CHAVE_PEDIDOS = {str_id} )
            WHERE CHAVE_PEDIDOS = {str_id}
        """
        logger.info(f"Atualizando valor do pedido. ID: {str_id}")

        if db is None:
            db = FbConnection()
            db.begin_transaction()
            db.execute_command(comando)
            db.commit()
            db.close()
        else:
            db.execute_command(comando)

    except Exception:
        logging.exception(f"ERRO ao ATUALIZAR. ID: '{str_id}'")
        raise


# GRAVANDO NO FIREBIRD - PEDIDOS
def gravar_protocolo_firebird(
    pedido_id,
    titulo_id,
    observacao,
    origem_pedido_id,
    numero_pedido_cri,
    db: FbConnection,
) -> tuple[int, int]:
    # from core.utils.firebird_utils import FbConnection

    if not pedido_id:
        return 1

    comando = """
                INSERT INTO PROTOCOLOS (CHAVE_PROTOCOLOS, NROORDEM, CHAVE_PEDIDOS,
                    DATAPROTOCOLO, CHAVE_TITULOS, NRORECIBOUSADO, OBSERVACAO, NUMEROPEDIDOCRI, ORIGEM_PEDIDO)
                VALUES(:CHAVE_PROTOCOLOS, :NROORDEM, :CHAVE_PEDIDOS, :DATAPROTOCOLO, :CHAVE_TITULOS,
                    :NRORECIBOUSADO, :OBSERVACAO, :NUMEROPEDIDOCRI, :ORIGEM_PEDIDO)
                """

    protocolo_id = db.sequence("PROTOCOLOS_SEQ").proximo
    nroordem = int(get_contador("NROORDEM", db)) + 1
    atualizar_contador_nroordem(db)
    numero_talao = int(get_contador("NROTALAO", db)) + 1
    numero_recibo_usado = int(get_contador("NRORECIBO", db)) + 1
    atualizar_contador_pedido(db)

    data_protocolo = "'" + str(db.datahora()) + "'"
    # numero_pedido_cri = "'" + "" + "'"
    numero_pedido_cri = "'" + str(numero_pedido_cri).replace("None", "") + "'"
    observacao = "'" + str(observacao).replace("None", "") + "'"

    comando = comando.replace(":CHAVE_PROTOCOLOS", str(protocolo_id))
    comando = comando.replace(":NROORDEM", str(nroordem))
    comando = comando.replace(":CHAVE_PEDIDOS", str(pedido_id))
    comando = comando.replace(":DATAPROTOCOLO", str(data_protocolo))
    comando = comando.replace(":CHAVE_TITULOS", str(titulo_id))
    comando = comando.replace(":NRORECIBOUSADO", str(numero_recibo_usado))
    comando = comando.replace(":OBSERVACAO", str(observacao))
    comando = comando.replace(":NUMEROPEDIDOCRI", str(numero_pedido_cri or ""))
    comando = comando.replace(":ORIGEM_PEDIDO", str(origem_pedido_id or 0))

    # print(comando)

    # Salvar no banco de dados - PEDIDOS ITENS
    try:
        if db is None:
            db = FbConnection()
            db.begin_transaction()
            db.execute_command(comando)
            atualizar_pedido_talao(pedido_id, numero_talao, db)
            db.commit()
            db.close()
        else:
            db.execute_command(comando)
            atualizar_pedido_talao(pedido_id, numero_talao, db)

        return nroordem, protocolo_id
    except Exception:
        db.close()
        logging.exception("ERRO ao atualizar PROTOCOLO. Chave")
        return 0, 0


# Obter o numero do pedido
# def get_contador(item: str, db: FbConnection):
#     # from core.utils.firebird_utils import FbConnection
#     logger.info(f"Obtendo contador para {item.upper()}.")
#     if item:
#         query = f"SELECT  {item.upper()} FROM CONTADOR"
#     else:
#         return None

#     try:
#         resultado = db.execute_query(query)[0]
#         results = list(resultado.values())

#         if not results:
#             logging.warning(f"Nenhum resultado retornado na consulta de {item} .")
#             return None

#         logger.info(f"Sequencia para {item.upper()} é:{ results[0]}")

#     except Exception:
#         logging.exception(f"ERRO ao obter {item}")
#         return None

#     return results


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


def atualizar_contador_nroordem(db: FbConnection):
    command = """ UPDATE CONTADOR
                SET NROORDEM  = NROORDEM  + 1,
                    NROTALAO  = NROTALAO  + 1
            """

    try:
        db = FbConnection() if db is None else db
        db.execute_command(command)
    except Exception:
        logging.exception(f"ERRO ao atualizar CAIXA do pedido. command: {command}")
        raise


def atualizar_contador_pedido(db: FbConnection):
    # from core.utils.firebird_utils import FbConnection

    command = """ UPDATE CONTADOR SET NROPEDIDO = NROPEDIDO + 1 """

    try:
        db = FbConnection() if db is None else db
        db.execute_command(command)

    except Exception:
        logging.exception(f"ERRO ao atualizar contador do pedido: command: {command}")
        raise


def atualizar_pedido_talao(pedido_id: str, valor_coluna: str, db: FbConnection) -> int:
    if not pedido_id:
        return 1

    str_id = str(pedido_id)

    try:
        comando = f"""
            UPDATE PEDIDOS SET NROTALAO = {valor_coluna}
            WHERE CHAVE_PEDIDOS = {str_id}
        """
        logger.info(f"Atualizando pedido. ID: {str_id}")

        if db is None:
            db = FbConnection()
            db.begin_transaction()
            db.execute_command(comando)
            db.commit()
            db.close()
        else:
            db.execute_command(comando)

    except Exception:
        logging.exception(f"ERRO ao ATUALIZAR pedido. ID: '{str_id}'")
        raise

    return 1


# Andamento Inicial
def get_andamento_inicial():
    tipo_andamento = models.TipoAndamento.objects.filter(
        servico__icontains="Prenota",
    ).first()
    return tipo_andamento.id if tipo_andamento else 12


# Emolumento Inicial
def get_default_emolumento_provisorio():
    tipo_emolumento = models.Emolumentos.objects.filter(
        nome__icontains=PROVISORIO,
    ).first()
    return tipo_emolumento.id if tipo_emolumento else 1377


# Ato Inicial
def get_default_ato_provisorio():
    tipo_ato = models.AtoPratica.objects.filter(
        tipo_ato__icontains=PROVISORIO,
    ).first()
    return tipo_ato.id if tipo_ato else 392


# Titulo Inicial
def get_default_titulo_provisorio():
    tipo_titulo = models.Titulo.objects.filter(
        tipo_titulo__icontains=PROVISORIO,
    ).first()
    return tipo_titulo.id if tipo_titulo else 96


# def get_dados_de_atos_em_dict(ato):
#     itens_atos = []
#     for ato_individual in ato:
#         # Gerando os itens da tabela "pedidos_ato"
#         print(
#             ato_individual.id,
#             ato_individual.pedido_id,  # pedidos_pedido
#             ato_individual.ato_praticavel.nome,  # pedidos_naturezaato
#             ato_individual.pedido.numero_pedido,  # pedidos_pedido
#             ato_individual.tipo_emolumento.nome,  # pedidos_tipoemolumento
#             ato_individual.tipo_titulo_id,
#             # ato_individual.tipo_titulo.nome,  # pedidos_tipotitulo
#         )

#         valor_itbi = ato_individual.valor_titulo
#         valor_avaliacao = ato_individual.valor_avaliacao
#         quantidade = ato_individual.quantidade
#         numero_ri = ato_individual.imovel_cartorio
#         numero_ato = ato_individual.numero_ato
#         numero_imovel = ato_individual.imovel_numero_registro

#         tipo_imovel = ato_individual.imovel_tipo_registro.nome[0] if ato_individual.imovel_tipo_registro_id else ""

#         # BUSCAR TITULO
#         if ato_individual.tipo_titulo_id:
#             # titulo_id = ato_individual.tipo_titulo.mapeamento_antigo.pk
#             titulo_id = ato_individual.tipo_titulo.home_titulo_protocolo_id
#         else:
#             titulo_id = get_default_titulo_provisorio()

#         if titulo_id is None:
#             titulo_id = get_default_titulo_provisorio()

#         # BUSCAR ATO
#         if ato_individual.ato_praticavel_id:
#             # ato_id = ato_individual.ato_praticavel.mapeamento_antigo.pk
#             ato_id = ato_individual.ato_praticavel.home_atos_id
#         else:
#             ato_id = get_default_ato_provisorio()

#         if ato_id is None:
#             ato_id = get_default_ato_provisorio()

#         # BUSCAR EMOLUMENTO
#         if ato_individual.tipo_emolumento.home_emolumento_id:
#             # emolumento_id = ato_individual.tipo_emolumento.mapeamento_antigo.pk
#             emolumento_id = ato_individual.tipo_emolumento.home_emolumento_id
#         else:
#             emolumento_id = Emolumentos.get_default_provisorio()

#         # Criando um dicionário com as informações
#         item_ato = {
#             "VALOR_ITBI": valor_itbi,
#             "VALOR_AVALIACAO": valor_avaliacao,
#             "TIPO_IMOVEL": tipo_imovel,
#             "QUANTIDADE": quantidade,
#             "NUMERO_RI": numero_ri,
#             "NUMERO_ATO": numero_ato,
#             "ATO_ID": ato_id,
#             "CHAVE_EMOLUMENTOS": emolumento_id,
#             "TITULO_ID": titulo_id,
#             "NUMERO_IMOVEL": numero_imovel,
#             "TIPO_TRIBUTACAO_ID": ato_individual.tipo_tributacao.percentual_desconto,
#         }

#         itens_atos.append(item_ato)

#     return itens_atos


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
    except:
        observacao = ""

    return str(observacao).upper()


# GRAVANDO NO FIREBIRD - PEDIDOS
def gravar_pedido_firebird(
    pedido_id,
    observacao,
    user_id,
    numero_protocolo_anterior,
    db: FbConnection,
) -> tuple[int, int]:
    from apps.home.helpers import get_data_util_em_x_dias

    # GERAR NOVO PEDIDO DO REPROTOCOLO
    pedido_id_reprotocolo = db.sequence("PEDIDOS_SEQ").proximo

    # # FILTRAR PEDIDO - ORIGINAL
    pedido = get_pedido_fb(pedido_id, db)

    email = str("Protocolo Anterior: " + str(numero_protocolo_anterior))

    # Atualizar a data prevista com base em dias uteis
    max_dias_uteis = 20
    data_entrada = timezone.now().date()
    data_prevista = get_data_util_em_x_dias(data_entrada, int(max_dias_uteis))
    data_validade = get_data_util_em_x_dias(data_entrada, int(max_dias_uteis) + 1)
    pedido_fb = None
    fone = ""

    try:
        # GRAVANDO O PEDIDO - PROTOCOLO
        pedido_fb = gravar_pedido_protocolo_fb(
            pedido_id=pedido_id_reprotocolo,
            numero_pedido=pedido_id_reprotocolo,
            data_entrada=data_entrada,
            data_prevista=data_prevista,
            data_validade=data_validade,
            tipo_servico="R",
            nomeadquirente=pedido["NOMEADQUIRENTE"],
            nomeapresentante=pedido["NOMEAPRESENTANTE"],
            nometransmitente=pedido["NOMETRANSMITENTE"],
            municipio=pedido["MUNICIPIO"],
            uf=pedido["UF"],
            numero_talao=pedido["NROPEDIDO"],
            observacao=observacao,
            endereco=observacao,
            tipo_documento_apresentante="1",
            documento_apresentante="",
            funcionario_id=user_id,
            fone=fone,
            email=email,
            nrotalao=pedido_id_reprotocolo,
            db=db,
        )

    except Exception as e:
        mensagem = f"ERRO ao tentar exportar o pedido: {e}"
        logger.exception(mensagem)
        raise
        # traceback_str = traceback.format_exc()
        # logger.error(traceback_str)

    return pedido_fb if pedido_fb else None


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
    nrotalao=0,
    db=None,
) -> dict:
    # from core.utils.firebird_utils import FbConnection

    nome = str(nomeapresentante).replace("'", "")
    # pedido_id = db.sequence("PEDIDOS_SEQ").proximo
    pedido_data = str(timezone.now().date().strftime("%d.%m.%Y"))
    observacao = str(observacao).replace("None", "")
    endereco = str(endereco).replace("None", "")
    # Definindo o comando SQL com placeholders
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
            EMAIL,
            TELEFONE,
            NROTALAO
        ) VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
        );
    """

    # Preparando os valores para os placeholders
    valores = (
        pedido_id,
        pedido_id,
        pedido_data,
        data_prevista,
        data_validade,
        tipo_servico,
        nome,
        nome,
        nome,
        municipio,
        uf,
        observacao,
        endereco,
        tipo_documento_apresentante,
        documento_apresentante,
        email,
        fone,
        nrotalao,
    )

    logger.info(f"Gravando pedido. ID: {pedido_id}")

    # Executando o comando SQL com parâmetros
    try:
        db.execute_command(comando, valores)
    except Exception as e:
        logger.exception(f"Erro ao gravar o pedido: {e}")

    pedido_fb = get_pedido_fb(pedido_id, db)

    if not pedido_fb:
        logger.warning(f"O pedido {pedido_id} foi encontrado.")
        return None

    return pedido_fb


# Função para tentar converter a data no formato esperado
def converter_data(data_str):
    formatos = ["%d.%m.%Y", "%d/%m/%Y", "%Y-%m-%d"]
    for formato in formatos:
        try:
            data_str = data_str.replace("'", "")
            return datetime.strptime(data_str, formato).strftime("%Y-%m-%d")
        except ValueError:
            continue
    # Se nenhum formato funcionar, levantar um erro
    msg = f"Data no formato inválido: {data_str}"
    raise ValueError(msg)


# Montando o dados para o SQL
def gravar_pedido_item_protocolo_fb(
    pedido_id,
    valor_itbi,
    valor_avaliacao,
    tipo_imovel,
    numero_imovel,
    emolumento_id,
    quantidade,
    numero_ri,
    numero_titulo,
    numero_ato,
    colaborador_id,
    ato_id,
    titulo_id,
    tipo_tributacao_id=1,
    livro="",
    folha="",
    data_escritura="",
    codigo_tabela="0",
    valor_emolumento="0",
    valor_fundo_estado="0",
    valor_tfj="0",
    valor_issqn="0",
    db=None,
) -> dict:
    """Insere um novo item de pedido no banco de dados e retorna o ID do item inserido e a data de pagamento."""
    pedido_item_id = db.sequence("PEDIDOS_ITENS_SEQ").proximo
    data_pagamento = timezone.now().date()

    # NUMERO DO IMOVEL - SE NÃO EXISTIR
    numero_imovel = numero_imovel or ""

    # VERIFICAR TITULO
    titulo_id = titulo_id or get_default_titulo_provisorio()

    # VERIFICAR ATO
    ato_id = ato_id or get_default_ato_provisorio()

    # BUSCAR EMOLUMENTO
    emolumento = models.Emolumentos.obter(emolumento_id, valor_documento=valor_itbi)
    emolumento_id = emolumento.pk
    emolumento_vigencia_id = emolumento.valores.vigencia.id
    valor_emolumento = emolumento.valores.valor_emolumento
    valor_emolumento_liquido = emolumento.valores.valor_emolumento
    valor_tfj = emolumento.valores.valor_tfj
    valor_issqn = emolumento.valores.valor_issqn
    valor_fundo_estado = emolumento.valores.valor_fundo_estado
    valor_total = emolumento.valores.valor_total

    # NUMERO DO ATO - SE NÃO EXISTIR
    numero_ato = numero_ato or ""

    # calculado = emolumento.calcular(valor_documento=valor_itbi)

    # # VALOR TOTAL DO ITEM
    # valor_total = valor_adicionado + issqn + emolumento + valor

    # COBRANCA NORMAL, 50 POR CENTOU OU ISENTO
    # custas = 1 if valor_total > 0 else 0
    # Definindo um dicionário com os tipos de tributação como chaves e as custas como valores

    # CUSTAS FIREBIRD
    # custas_por_tipo = {100: 0, 50: 5}
    custas_por_tipo, emolumento_exportar_id = get_custas_firebird(
        tipo_tributacao_id,
        emolumento.pk,
    )

    # Convertendo tipo_tributacao_id para inteiro e buscando no dicionário
    # O método get retorna o valor associado à chave, ou 1 caso a chave não seja encontrada
    custas = (
        custas_por_tipo.get(int(tipo_tributacao_id), 1)
        if emolumento.codigo_tabela != "0"
        else 1
    )

    codigo_tipo_tributacao = custas

    # ALFENAS ADICIONAR CAMPOS PARA O SQLSERVER
    ano_referencia_tabela = timezone.now().year

    # IMPORTAR PRENOTACAO
    # TEMPORARIO CORRIGIR EXPORTACAO NO SQL SERVER
    cartorio_model = apps.get_model("cartorios", "Cartorio")

    usar_selo_sql_server = cartorio_model.objects.all().values_list(
        "usar_selo_sql_server",
        flat=True,
    )[0]

    emolumento_id = emolumento.pk
    emolumento_vigencia_id = emolumento.vigencia_atual_id
    grupo_lancamento = None
    chave_emolumento_ws_go = None
    codigo_atoselo = codigo_tabela[:4] or 4701

    # ALFENAS
    if (
        usar_selo_sql_server == "S"
        and custas == 1
        and codigo_tabela == get_cod_prenotacao()
    ):
        (
            valor_emolumento,
            valor_fundo_estado,
            valor_tfj,
            valor_emolumento_liquido,
            valor_issqn,
        ) = get_valor_prenotacao()

        valor_total = valor_emolumento + valor_fundo_estado + valor_tfj + valor_issqn

        # ALFENAS - ALTERACOES PARA SEDI
        valor_emolumento_liquido = valor_emolumento
        valor_emolumento = valor_emolumento + valor_fundo_estado

        # ALFENAS FIXO
        emolumento_id = 172
        emolumento_vigencia_id = 27
        chave_emolumento_ws_go = 66
        grupo_lancamento = 2

    # GRAVANDO NO FIREBIRD
    comando = """
        INSERT INTO PEDIDOS_ITENS (
            CHAVE_PEDIDOS_ITENS,
            CHAVE_PEDIDOS,
            CHAVE_ATOS,
            CHAVE_TITULOS,
            CHAVE_FUNCIONARIOS,
            TABELACALCULO,
            CHAVE_VIGOR,
            DATA_PAGAMENTO,
            CDHU,
            TIPO_IMOVEL,
            NUMERO_IMOVEL,
            NUMERO_RI,
            NUMEROATO,
            CODIGO_TABELA,
            VALOREMOLUMENTO,
            VALORRECEITAADICIONAL1,
            TAXA1,
            VALOR_FUNDOESTADO,
            VALORITBI,
            VALORAVALIACAO,
            NROTITULO,
            VALORTOTALITEM,
            LIVRO_ESCRITURA,
            FOLHA_INI_ESCRITURA,
            FOLHA_FIM_ESCRITURA,
            DATA_ESCRITURA,
            EMOLUMENTOLIQ,
            CUSTAS,
            CODIGO_TIPO_TRIBUTACAO,
            ANO_REFERENCIA_TABELA,
            CHAVE_EMOLUMENTO_WS_GO,
            CODIGO_ATOSELO,
            GRUPOLANCAMENTO
        )
        VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
        );
    """

    # Convertendo data_escritura para o formato 'YYYY-MM-DD' se estiver definida
    data_escritura_formatada = (
        converter_data(data_escritura) if data_escritura else None
    )

    parametros = (
        pedido_item_id,
        pedido_id,
        ato_id,
        titulo_id,
        colaborador_id,
        emolumento_id,
        emolumento_vigencia_id,
        data_pagamento,
        quantidade,
        tipo_imovel,
        numero_imovel,
        numero_ri,
        numero_ato,
        codigo_tabela,
        valor_emolumento,
        valor_tfj,
        valor_issqn,
        valor_fundo_estado,
        valor_itbi,
        valor_avaliacao,
        numero_titulo,
        valor_total,
        livro,
        folha,
        folha,
        data_escritura_formatada if data_escritura_formatada else None,
        valor_emolumento_liquido,
        custas,
        codigo_tipo_tributacao,
        ano_referencia_tabela,
        chave_emolumento_ws_go,
        codigo_atoselo,
        grupo_lancamento,
    )

    logger.info(f"gravar_pedido_item_protocolo_fb Item ID: {pedido_item_id}")

    try:
        db.execute_command(comando, parametros)
    except Exception as e:
        logger.exception(f"Erro ao gravar item do pedido (pedido_item_id): {e}")
        raise

    return pedido_item_id


# RETORNAR O CODIGO DA PRENOTACAO
def get_cod_prenotacao() -> str:
    return "4701-9"


# RETORNAR O VALOR DA PRENOTACAO
def get_valor_prenotacao() -> str:
    from apps.pedidos.models import Emolumento, TipoEmolumento

    tipo_emolumento = TipoEmolumento.objects.filter(
        codigo=firebird.get_cod_prenotacao(),
        ativo=True,
    ).first()
    pedido_item_valores = Emolumento.objects.filter(
        tipo_emolumento_id=tipo_emolumento,
    ).first()

    return (
        pedido_item_valores.valor,
        pedido_item_valores.fundo1_valor,
        pedido_item_valores.taxa_fiscal_judiciaria,
        (pedido_item_valores.valor - pedido_item_valores.fundo1_valor),
        ((pedido_item_valores.issqn_percentual / 100) * pedido_item_valores.valor),
    )


# def atualizar_pedido_protocolo(pedido_id, coluna_pedido, coluna_item, db: FbConnection):
#     from core.utils.firebird_utils import FbConnection

#     if not pedido_id:
#         return 1

#     pedido_id = str(pedido_id)
#     try:
#         comando = f"""
#             UPDATE PEDIDOS SET {coluna_pedido} = (
#                 SELECT SUM({coluna_item})
#                 FROM PEDIDOS_ITENS
#                 WHERE CHAVE_PEDIDOS = {pedido_id}
#             )
#             WHERE CHAVE_PEDIDOS = {pedido_id}
#         """
#         logger.info(f"Atualizando pedido protocolo. ID {pedido_id}")

#         db = FbConnection() if db is None else db
#         db.execute_command(comando)

#     except Exception as e:
#         logging.exception(f"ERRO ao ATUALIZAR pedido. ID: '{pedido_id}': ")
#         raise


def selar_protocolo_no_firebird(pedido_id, pedidos_id_itens, db: FbConnection):
    # from core.utils.firebird_utils import FbConnection
    print("Iniciando a selagem do protocolo no Firebird. Pedido ID: ", pedido_id)
    if not pedidos_id_itens:
        return 1

    if isinstance(pedidos_id_itens, tuple):
        pedidos_id_itens = pedidos_id_itens[0]
    elif isinstance(pedidos_id_itens, int):
        # Se já for um inteiro, pode continuar com o valor como está
        pedidos_id_itens = int(pedidos_id_itens)
    else:
        # Opcional: Lidar com outros tipos inesperados
        pedidos_id_itens = 0

    comando2 = """
                    UPDATE SELO_DIGITAL_MG
                    SET UTILIZADO = :UTILIZADO,
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

    data = "'" + str(db.data()) + "'"

    # Atualizar os parametros de data
    comando2 = comando2.replace(":UTILIZADO", "'S'")
    comando2 = comando2.replace(":CHAVE_PEDIDOS", str(pedido_id))
    comando2 = comando2.replace(":CHAVE_ITENS", str(pedidos_id_itens))
    comando2 = comando2.replace(":DATA_UTILIZACAO", str(data))
    # comando2 = Atualizar_Parametro(comando2, ':CODIGO_SEQUENCIAL_UNICO',    str( "'" + CODIGO_SELO + "'"))

    try:
        # db = FbConnection() if db is None else db
        # results1 = db.execute_query(comando1)
        db.execute_command(comando2)

        # BUSCAR O SELO
        results = db.execute_query(
            " SELECT CODIGO_SEQUENCIAL_UNICO, CODIGO_DE_SEGURANCA FROM SELO_DIGITAL_MG WHERE CHAVE_PEDIDOS_ITENS = "
            + str(pedidos_id_itens),
        )

        # BUSCAR A SENHA CONSULTA
        results_senha = db.execute_query(
            " SELECT FSENHACONSULTA FROM PROTOCOLOS WHERE CHAVE_PEDIDOS = "
            + str(pedido_id),
        )

        results_senha = (
            results_senha[0]["FSENHACONSULTA"] if len(results_senha) > 0 else ""
        )

        if not results:
            logging.warning("Nenhum resultado retornado da consulta.")
            return None
        else:
            logger.info(
                f"FB: Sucesso comando - Selar protocolo no Firebird. {results[0]['CODIGO_SEQUENCIAL_UNICO']} Pedido ID: {pedido_id}",
            )
            return (
                results[0]["CODIGO_SEQUENCIAL_UNICO"],
                results[0]["CODIGO_DE_SEGURANCA"],
                results_senha,
            )

    except Exception:
        logging.exception("ERRO ao obter valores da protocolo: ")
        return None


# PEGAR O EMOLUMENTO DE PRENOTACAO
def get_tipo_emolumento_prenotacao() -> int:
    tipo_emolumento = (
        models.Emolumentos.objects.filter(emolumento_prenotacao="S")
        .order_by("nome")
        .first()
    )
    return tipo_emolumento.id if tipo_emolumento else 86


def get_tipo_emolumento_prenotacao_obj() -> "models.Emolumentos":
    tipo_emolumento = (
        models.Emolumentos.objects.filter(emolumento_prenotacao="S")
        .order_by("nome")
        .first()
    )
    return tipo_emolumento if tipo_emolumento else None


# # PEGAR O ATO DE REPROTOCOLAR
# def get_andamento_reprotocolar():
#     tipo_andamento = TipoAndamento.objects.filter(grupo_reprotocolado="S").first()
#     return tipo_andamento.id if tipo_andamento else 12


# PEGAR O ATO DE PRENOTACAO
def get_ato_praticavel_prenotacao():
    tipo_ato = (
        models.AtoPratica.objects.filter(ato_prenotacao="S")
        .order_by("tipo_ato")
        .first()
    )
    return tipo_ato.id if tipo_ato else 86


# PEGAR O TITULO DE PRENOTACAO
def get_default_titulo_prenotacao():
    tipo_titulo = (
        models.Titulo.objects.filter(titulo_prenotacao="S")
        .order_by("tipo_titulo")
        .first()
    )
    return tipo_titulo.id if tipo_titulo else 96


# GRAV
def gravar_caixa_ped_protocolo_fb(
    pedido_id,
    colaborador,
    descricao,
    valor,
    pagamento_id,
    caixa_id=0,
    tipotransacao=1,
    tipodocumento=1,
    reprotocolo=False,
    db=None,
) -> None:
    if caixa_id == 0:
        caixa_id = db.sequence("CAIXA_SEQ").proximo

    descricao = "'" + descricao + "'"

    # CASO SEJA REPROTOCOLO ELE VAI APENAS JOGAR
    # DATA FICTICIA PARA NAO ATRAPALHAR OS RELATORIOS
    data = "'2000-01-01'" if reprotocolo is True else "'" + str(db.data()) + "'"

    comando = """
            INSERT INTO CAIXA (
                CHAVE_CAIXA, DATAPAGAMENTO, DESCRICAO, TIPOTRANSACAO, TIPODOCUMENTO,
                VALOR, CHAVE_PEDIDOS, CHAVE_PAGAMENTO, CHAVE_FUNCIONARIOS
            )
            VALUES (
                :CHAVE_CAIXA, :DATAPAGAMENTO, ' :DESCRICAO ', :TIPOTRANSACAO, :TIPODOCUMENTO,
                :VALOR, :CHAVE_PEDIDOS, :CHAVE_PAGAMENTO, :CHAVE_FUNCIONARIOS
            );
        """

    descricao = str(descricao).replace("''", "")
    valor = Decimal(valor) if valor else 0

    try:
        valor_arredondado = valor.quantize(Decimal("0.00"), rounding=ROUND_HALF_UP)
    except:
        valor_arredondado = 0

    comando = comando.replace(":CHAVE_CAIXA", str(caixa_id))
    comando = comando.replace(":DESCRICAO", str(descricao))
    comando = comando.replace(":DATAPAGAMENTO", str(data))
    comando = comando.replace(":TIPOTRANSACAO", str(tipotransacao))
    comando = comando.replace(":TIPODOCUMENTO", str(tipodocumento))
    comando = comando.replace(":VALOR", str(valor_arredondado))
    comando = comando.replace(":CHAVE_PEDIDOS", str(pedido_id))
    comando = comando.replace(":CHAVE_PAGAMENTO", str(pagamento_id))
    comando = comando.replace(":CHAVE_FUNCIONARIOS", str(colaborador))

    logger.info(f"Gravando caixa do pedido. ID: {pedido_id}")

    # SALVANDO O COMANDO NO BANCO DE DADOS FIREBIRD
    if db is None:
        db = FbConnection()
        db.begin_transaction()
        db.execute_command(comando)
        db.commit()
        db.close()
    else:
        print(comando)
        db.execute_command(comando)


# ATUALIZAR OS VALORES DO PEDIDOS FIREBIRD
def atualizar_pedido_protocolo(
    pedido_id,
    coluna_pedido,
    coluna_item,
    db: FbConnection,
) -> None:
    comando = f"""
            UPDATE PEDIDOS SET {coluna_pedido} = (
                SELECT SUM({coluna_item})
                FROM PEDIDOS_ITENS
                WHERE CHAVE_PEDIDOS = {pedido_id}
            )
            WHERE CHAVE_PEDIDOS = {pedido_id}
        """

    # SALVANDO O COMANDO NO BANCO DE DADOS FIREBIRD
    if db is None:
        db = FbConnection() if db is None else db
        db.begin_transaction()
        db.execute_command(comando)
        db.commit()
        db.close()
    else:
        db.execute_command(comando)


# ATUALIZAR OS VALORES DO PEDIDOS
def atualizar_valores_pedido_firebird(pedido_id, db: FbConnection) -> None:
    atualizar_pedido_protocolo(
        pedido_id,
        "VALORRECEITAADICIONAL",
        "VALORRECEITAADICIONAL1",
        db,
    )
    atualizar_pedido_protocolo(pedido_id, "VALOREMOLUMENTO", "VALOREMOLUMENTO", db)
    atualizar_pedido_protocolo(pedido_id, "VALORFINAL", "VALORTOTALITEM", db)
    atualizar_pedido_protocolo(pedido_id, "VALORACERTO", "VALORTOTALITEM", db)
    atualizar_pedido_protocolo(pedido_id, "TAXA1", "TAXA1", db)


# Gravar ato caso precisa
def criar_ato_auxiliar_no_fb(
    pedido_id: int,
    titulo_protocolo_id: int,
    colaborador,
    codigo_tabela_prenotacao,
    db: FbConnection,
) -> None:
    # OBTER O NUMERO DO IMOVEL NA PRENOTACAO
    pedido_item = models.PedidoItem.objects.filter(
        pedido_id=pedido_id,
        codigo_tabela=codigo_tabela_prenotacao,
    ).first()

    try:
        numero_registro = pedido_item.numero_registro if pedido_item else None
        tipo_registro = pedido_item.tipo_registro if pedido_item else None
        numero_ri = pedido_item.numero_ri if pedido_item else None
    except Exception:
        logger.exception("ERRO")
        raise

    # print("Numero Imovel", numero_registro)
    # print(pedido_id, codigo_tabela_prenotacao)

    comando = f""" UPDATE PEDIDOS_ITENS
                SET NUMERO_REGISTRO = NULL,
                    TIPO_REGISTRO = NULL,
                    NUMERO_RI =  '1'
                WHERE CHAVE_PEDIDOS = {pedido_id!s}
                AND CODIGO_TABELA = '{codigo_tabela_prenotacao!s}'
            """

    # GRAVAR UM NOVO ATO E ADICIONAR O NOVO NUMERO
    try:
        if not pedido_item.numero_registro:
            # print(pedido_id)
            # emolumento_id = Emolumentos.objects.get(nome=PROVISORIO)
            # emolumento_item_id = 1377
            # tipo_ato_protocolo_id = 392
            # titulo_id = titulo_protocolo_id

            emolumento_item_id = helpers.get_emolumento_item()
            tipo_ato_protocolo_id = helpers.get_ato_item()

            # CRIAR PEDIDO ITEM no FIREBIRD
            criar_pedido_item_no_fb(
                pedido_id=pedido_id,
                ato_id=tipo_ato_protocolo_id,
                titulo_id=titulo_protocolo_id,
                emolumento_id=emolumento_item_id,
                numero_id=numero_registro,
                tipo_id=tipo_registro,
                tributacao_id=1,
                valor_documento=0,
                valor_avaliacao=0,
                numero_ato_id="",
                quantidade=1,
                custas_id=1,
                ri_id=numero_ri,
                colaborador=colaborador,
                db=db,
            )
            db.execute_command(comando)
    except Exception:
        logger.exception("ERRO")
        raise


# GRAVAR ANDAMENTO NO FIREBIRD
def gravar_protocolo_andamento_firebird(
    protocolo_id,
    funcionario_id,
    servico_id,
    andamento_id,
    db: FbConnection,
) -> int | None:
    if not protocolo_id:
        return 1

    comando = """
                INSERT INTO ANDAMENTOS (CHAVE_ANDAMENTOS, CHAVE_PROTOCOLOS,
                    DATA, CHAVE_FUNCIONARIOS, CHAVE_SERVICOS_ANDAMENTOS)
                VALUES(:CHAVE_ANDAMENTOS, :CHAVE_PROTOCOLOS,
                    :DATA, :CHAVE_FUNCIONARIOS, :CHAVE_SERVICOS_ANDAMENTOS);
                """

    data = db.data_str

    # BUSCAR APENAS SE NAO FOR INFORMADO
    andamento_id = andamento_id or 0
    if andamento_id == 0:
        andamento_id = db.sequence("ANDAMENTOS_SEQ").proximo

    comando = comando.replace(":CHAVE_ANDAMENTOS", str(andamento_id))
    comando = comando.replace(":CHAVE_PROTOCOLOS", str(protocolo_id))
    comando = comando.replace(":DATA", str(data))
    comando = comando.replace(":CHAVE_FUNCIONARIOS", str(funcionario_id))
    comando = comando.replace(":CHAVE_SERVICOS_ANDAMENTOS", str(servico_id))

    # SALVANDO O COMANDO NO BANCO DE DADOS FIREBIRD
    db.execute_command(comando)

    return None


# SELECIONAR O COMANDO
def get_comando_firebird(comando, db=None):
    query = comando

    db = FbConnection() if db is None else db
    resultado = db.execute_query(query)

    return resultado if resultado else None


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
    default: float = 0,
    to_real=None,
) -> float:
    """Extrai um valor de uma lista de resultados, converte para real se necessário."""
    to_real = to_real or True
    try:
        value = results[0][index]
        return np.real(value) if to_real else value
    except (IndexError, TypeError) as e:
        logger.info(f"ERRO ao extrair valor do resultado: {results} - {e}")
        return default


def verificar_se_pedido_existe_por_numero_e_apresentante_no_firebird(
    pedido_certidao_id: int,
    nome_apresentante: str,
    opcao_pesquisa: int | None,
    db: FbConnection,
) -> int | None:
    """
    Verifica se um pedido de certidão já foi exportado com base no número do pedido
    e no nome do apresentante.

    :param pedido_certidao_id: ID do pedido de certidão.
    :param nome_apresentante: Nome do apresentante.
    :param opcao_pesquisa: Opção de pesquisa (0 para pesquisar por nome e número, qualquer outro valor para pesquisar apenas pelo número).
    :param db: Conexão com o banco de dados Firebird.
    :return: Quantidade de pedidos encontrados ou None se houver erro.
    """
    try:
        logger.info(
            f"Verificando se o pedido {pedido_certidao_id} já foi exportado. Nome do apresentante: {nome_apresentante}.",
        )
        opcao_pesquisa = opcao_pesquisa or 0
        logger.debug(f"Opção de pesquisa: {opcao_pesquisa}")

        # Construção da consulta com base na opção de pesquisa
        if opcao_pesquisa == 0:
            query = f"""
                SELECT COUNT(CHAVE_PED_CERTIDOES)
                FROM PED_CERTIDOES
                WHERE CHAVE_PED_CERTIDOES = {pedido_certidao_id}
                AND UPPER(NOMEAPRESENTANTE) = UPPER('{nome_apresentante}')
            """
            logger.debug(f"Consulta construída para opção de pesquisa 0: {query}")
        else:
            query = f"""
                SELECT COUNT(CHAVE_PED_CERTIDOES)
                FROM PED_CERTIDOES
                WHERE CHAVE_PED_CERTIDOES = {pedido_certidao_id}
            """
            logger.debug(f"Consulta construída para outra opção de pesquisa: {query}")

        try:
            result = db.execute_query(query)
            logger.debug(f"Resultado da consulta: {result}")

            if not result:
                logger.warning("Nenhum resultado retornado da consulta.")
                return None

            saida = result[0]["COUNT"]
            logger.info(f"Quantidade de pedidos encontrados: {saida}")

            return int(saida)

        except Exception:
            logger.exception("Erro ao executar a consulta no banco de dados:")
            return None

    except Exception:
        logger.exception("Erro ao verificar o pedido de certidão:")
        return None


def get_valores_certidao_fb(
    vigencia_id,
    tabela_id,
    estado_civil_id,
    db: FbConnection,
):
    if not all([vigencia_id, tabela_id, estado_civil_id]):
        logging.error("Parâmetros inválidos fornecidos para obter valores da certidão.")
        print(estado_civil_id, ", ", tabela_id, " , ", vigencia_id)
        return None

    print("Obtendo valores da certidão...")
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
        db = FbConnection() if db is None else db
        results = db.execute_query(query, params)[0]
        if not results:
            logging.warning("Nenhum resultado retornado da consulta.")
            return None
    except Exception:
        logging.exception("ERRO ao obter valores da certidão:")
        return None

    tipo_certidao_id = results["CODIGO_VALORES_CERTIDOES"]
    emolumento_liquido = results["VALOR"]
    tx_judiciaria = results["TAXAJUDICIARIA"]
    valor_adicionado = results["ADIC_VALOR"]
    valor_fundo_estado = results["TAXA1"]

    valor_calculado = emolumento_liquido + valor_adicionado + tx_judiciaria

    return {
        "emolumento": emolumento_liquido,
        "valor": valor_calculado,
        "tipo_certidao_id": tipo_certidao_id,
        "tx_judiciaria": tx_judiciaria,
        "valor_adicionado": valor_adicionado,
        "quantidade": "1",
        "valor_fundo_estado": valor_fundo_estado,
    }


def get_tipo_de_livro(livro: str) -> str:
    logger.info(f"Obtendo tipo de livro {livro}...")
    tipos = {"L2": "M", "2": "M", "L3": "A", "3": "A", "T": "T"}
    resultado = tipos.get(livro, "M")
    logger.info(f"Tipo de livro obtido: {resultado}")
    return resultado


def get_valor_parametro_ini_fb(secao, estacao, nome, colunas, db: FbConnection):
    print(
        "Obtendo valor do parâmetro INI. ",
        "Secao:",
        secao,
        "Estacao:",
        estacao,
        "Nome:",
        nome,
        "Colunas",
        colunas,
    )
    query = "SELECT ? FROM INI WHERE SECAO = ? AND ESTACAO = ? AND NOME = ?"
    params = (secao, estacao, nome)

    try:
        db = FbConnection() if db is None else db
        results = db.execute_query(query, params)[0]
    except Exception:
        logging.exception("ERRO ao obter valor do parâmetro INI")
        raise
    return results


def atualizar_caixa_do_pedido(pedido_id, db: FbConnection):
    print(
        "Atualizando CAIXA do pedido:",
        pedido_id,
    )
    query = """
        UPDATE CAIXA
        SET VALOR = (
            SELECT VALOR_CALC
            FROM PED_CERTIDOES
            WHERE CHAVE_PED_CERTIDOES = ?
        )
        WHERE CHAVE_PED_CERTIDOES = ?
    """

    params = (pedido_id, pedido_id)

    db = FbConnection() if db is None else db

    try:
        db.execute_command(
            query,
            params,
        )  # Considerando que você alterou o método para aceitar parâmetros.
    except Exception:
        logging.exception(f"ERRO ao atualizar CAIXA do pedido. ID: '{pedido_id}'.:")
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
        results = db.execute_query(query)
        results = results[0] if results else None

        # NAO ENCONTROU VIGOR
        if results["MAX"] is None:
            query = " SELECT MAX(CHAVE_VIGOR) FROM PEDIDOS_ITENS "
            results = db.execute_query(query)
            results = results[0]["MAX"] if results else None

        logger.info(f"Chave do Vigor atual: {results}")
        return results["MAX"]
    except Exception:
        logging.exception("ERRO ao obter vigencia atual:")
        raise


def checar_lacunas_e_get_sequence(sequence, tabela, db: FbConnection, coluna_id="id"):
    print("Checando por lacunas na sequência...")
    query_lacunas = f"""
        SELECT a.{coluna_id} + 1 AS start_gap
        FROM (
            SELECT FIRST 25 {coluna_id}
            FROM {tabela}
            WHERE CAST(DATAPEDIDO AS DATE) = CURRENT_DATE
            ORDER BY {coluna_id} DESC
        ) AS a
        LEFT JOIN {tabela} AS b ON a.{coluna_id} + 1 = b.{coluna_id}
        LEFT JOIN {tabela} AS c ON a.{coluna_id} + 2 = c.{coluna_id}
        WHERE b.{coluna_id} IS NULL AND c.{coluna_id} IS NOT NULL
        ORDER BY a.{coluna_id} DESC;
    """

    try:
        db = FbConnection() if db is None else db
        lacunas = db.execute_query(query_lacunas)
        if lacunas:
            # print("Lacuna encontrada. Usando ID faltante: ", lacunas[0]["start_gap"])
            # return lacunas[0]["start_gap"]
            print("Lacuna encontrada. Usando ID faltante: ", lacunas[0]["start_gap"])
            return lacunas[0]["start_gap"]
        else:
            return db.sequence(sequence).proximo
    except Exception:
        logging.exception("Falha ao checar por lacunas ou obter a sequence.")
        raise


# OBTER O NUMERO DO PEDIDO DE CERTIDAO
def get_numero_pedido_certidao(db: FbConnection):
    query = " SELECT MAX(CHAVE_PED_CERTIDOES) FROM PED_CERTIDOES "

    results = db.execute_query(query)
    results = results[0] if results else None

    delimiter = "."
    return delimiter.join([str(value) for value in results])


def get_numero_cri(numero_pedido, db: FbConnection):
    print("Obtendo número do CRI. Numero do pedido: ", numero_pedido)

    query = (
        " SELECT MAX(CHAVE_PED_CERTIDOES) FROM PED_CERTIDOES WHERE NUMEROPEDIDOCRI = '"
        + str(numero_pedido)
        + "'"
    )

    results = db.execute_query(query)
    results = results[0] if results else None

    delimiter = "."
    return delimiter.join([str(value) for value in results])


def get_numero_cri_2(numero_pedido_cri, db: FbConnection):
    print("Obtendo número do CRI...")

    query = f" SELECT CHAVE_PED_CERTIDOES FROM PED_CERTIDOES WHERE NUMEROPEDIDOCRI = {numero_pedido_cri!s}"

    results = db.execute_query(query)
    results = results[0] if results else None

    delimiter = "."
    return delimiter.join([str(value) for value in results])


def gravar_caixa_ped_certidao_fb(
    pedido_fb: dict,
    pedido: "PedidoCertidao",
    origem_id: int,
    db: FbConnection,
) -> int:
    origem_id = origem_id or 1
    # print(pedido_fb)

    if pedido_fb:
        caixa_id = db.sequence("CAIXA_SEQ").proximo
        pedido_id = pedido.id
        data_pedido = pedido.data_entrada.strftime("%Y-%m-%d")
        funcionario_pedido = pedido.criado_por_id

        valor = pedido.valor_diferenca

        # ERRO NO VISUALIZA MATRICULA - TEMPORARIO
        if int(origem_id) == 2:
            valor = 8.8

        tipo_transacao = "1"
        tipo_documento = "1"
        query = None
        params = ()

        descricao = str(
            "Pedido de Certidão: "
            + str(pedido_id)
            + " - "
            + str(pedido.nome_apresentante),
        )
        pagamento_id = "6"

        query = """
                INSERT INTO CAIXA (
                    CHAVE_CAIXA, DATAPAGAMENTO, DESCRICAO, TIPOTRANSACAO, TIPODOCUMENTO,
                    VALOR, CHAVE_PED_CERTIDOES, CHAVE_PAGAMENTO, CHAVE_FUNCIONARIOS )
                VALUES ( ?, ?, ?, ?, ?, ?, ?, ?, ? );
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
            funcionario_pedido,
        )

        try:
            if query and params:
                logger.info(
                    f"CAIXA: Criando transação do Pedido de Certidão no FB: {pedido_fb}",
                )
                db.execute_command(query, params)

        except Exception:
            logging.exception(
                f"ERRO ao gravar CAIXA do pedido. ID: '{pedido_id}'. pedido_fb: {pedido_fb}.:",
            )
            # raise
    else:
        logging.warning("Nenhum pedido fornecido para gravar no Caixa Fb.")
        return None
    return 1


def gravar_caixa_fb(financeiro: "Financeiro", db: FbConnection) -> tuple:
    from apps.home.models import Financeiro

    if not financeiro or not isinstance(financeiro, Financeiro):
        msg = "Nenhum objeto Financeiro fornecido para gravar no Fb."
        raise ValueError(msg)

    caixa_fb = get_transacao_caixa_firebird(financeiro.pk, db)
    # caixa_pedido_fb = get_transacao_caixa_firebird_pelo_pedido_id(financeiro.pedido_certidao_id, db)

    if caixa_fb:
        msg = f"Transação '{financeiro.descricao}' já existe no Caixa Fb."
        logger.warning(msg)
        return caixa_fb, msg

    caixa_id = financeiro.pk  # db.sequence("CAIXA_SEQ").proximo
    pedido_id = financeiro.pedido_id
    data_pedido = financeiro.data_transacao
    funcionario_pedido = financeiro.colaborador_id
    tipo_transacao = financeiro.tipotransacao
    tipo_documento = financeiro.tipodocumento
    valor = financeiro.valor_transacao
    descricao = financeiro.descricao
    pagamento_id = "6"

    comando = """
            INSERT INTO CAIXA (
                CHAVE_CAIXA, DATAPAGAMENTO, DESCRICAO, TIPOTRANSACAO, TIPODOCUMENTO,
                VALOR, CHAVE_PED_CERTIDOES, CHAVE_PAGAMENTO, CHAVE_FUNCIONARIOS )
            VALUES ( ?, ?, ?, ?, ?, ?, ?, ?, ? );
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
        funcionario_pedido,
    )
    try:
        if comando and params:
            logger.info(f"CAIXA: Criando transação '{financeiro.descricao}' no FB.")
            db.execute_command(comando, params)

    except Exception:
        logging.exception(f"ERRO ao gravar CAIXA. ID: '{caixa_id}'.")
        raise

    caixa_fb = get_transacao_caixa_firebird(financeiro.pk, db)
    msg = f"Transação '{financeiro.descricao}' gravada."
    return caixa_fb, msg


def get_transacao_caixa_firebird(pk, db: FbConnection):
    query = f"""
        SELECT CHAVE_CAIXA, DATAPAGAMENTO, DESCRICAO, TIPOTRANSACAO, TIPODOCUMENTO,
                    VALOR, CHAVE_PED_CERTIDOES, CHAVE_PAGAMENTO, CHAVE_FUNCIONARIOS
        FROM CAIXA
        WHERE CHAVE_CAIXA = {pk}
    """

    resultado = db.execute_query(query)

    return resultado[0] if resultado else None


def get_transacao_caixa_firebird_pelo_pedido_id(pedido_certidao_id, db: FbConnection):
    if not pedido_certidao_id:
        msg = "pedido_certidao_id não foi fornecido para obter a transação do caixa."
        raise ValueError(msg)

    query = f"""
        SELECT CHAVE_CAIXA, DATAPAGAMENTO, DESCRICAO, TIPOTRANSACAO, TIPODOCUMENTO,
            VALOR, CHAVE_PED_CERTIDOES, CHAVE_PAGAMENTO, CHAVE_FUNCIONARIOS
        FROM CAIXA
        WHERE CHAVE_PED_CERTIDOES = {pedido_certidao_id}
    """

    resultado = db.execute_query(query)[0]

    return resultado if resultado else None


def construir_query_valores_certidao(
    usar_selo_sql_server: str,
    certidao_id_sistema_antigo: str,
    codigo_tabela: str,
) -> str:
    logging.debug(
        f"Iniciando construção da query. usar_selo_sql_server={usar_selo_sql_server}, certidao_id_sistema_antigo={certidao_id_sistema_antigo}",
    )
    query = ""
    if usar_selo_sql_server == "S":
        if certidao_id_sistema_antigo:
            query = (
                "SELECT VALOR_SQLSERVER as VALOR, CODIGO_VALORES_CERTIDOES, TAXAJUDICIARIA_SQLSERVER as TAXAJUDICIARIA, "
                "CODIGO_TABELA, ADIC_VALOR_SQLSERVER as ADIC_VALOR, CATEGORIA, TAXA1_SQLSERVER as TAXA1, CHAVE_EMOLUMENTO_WS_GO "
                "FROM VALORES_CERTIDOES "
                f"WHERE CODIGO_VALORES_CERTIDOES = {certidao_id_sistema_antigo!s} ORDER BY NOME "
            )
        else:
            msg = (
                "Nenhum valor fornecido para construir a query de valores da certidão. "
                "é necessario informar o certidao_id_sistema_antigo para SQLSERVER."
            )
            raise ValueError(
                msg,
            )
    else:
        if codigo_tabela and not certidao_id_sistema_antigo:
            query = (
                "SELECT FIRST 1 VALOR, CODIGO_VALORES_CERTIDOES, TAXAJUDICIARIA, "
                "CODIGO_TABELA, ADIC_VALOR, CATEGORIA, TAXA1, CHAVE_EMOLUMENTO_WS_GO "
                "FROM VALORES_CERTIDOES "
                f"WHERE CODIGO_TABELA = '{codigo_tabela!s}' "
                "ORDER BY CHAVE_VIGOR DESC"
            )
        elif certidao_id_sistema_antigo:
            query = (
                "SELECT VALOR, CODIGO_VALORES_CERTIDOES, TAXAJUDICIARIA, "
                "CODIGO_TABELA, ADIC_VALOR, CATEGORIA, TAXA1, CHAVE_EMOLUMENTO_WS_GO "
                "FROM VALORES_CERTIDOES "
                f"WHERE CODIGO_VALORES_CERTIDOES = {certidao_id_sistema_antigo!s} "
            )
        elif not codigo_tabela and not certidao_id_sistema_antigo:
            msg = (
                "Nenhum valor fornecido para construir a query de valores da certidão. "
                "é necessario informar o codigo_tabela ou certidao_id_sistema_antigo para FB."
            )
            raise ValueError(
                msg,
            )
    logging.debug(f"Query construída: {query}")
    return query


def obter_usar_selo_sql_server() -> str:
    logging.debug("Obtendo valor de usar_selo_sql_server.")
    cartorio_model = apps.get_model("cartorios", "Cartorio")
    usar_selo_sql_server = cartorio_model.objects.all().values_list(
        "usar_selo_sql_server",
        flat=True,
    )[0]
    logging.debug(f"Valor obtido: usar_selo_sql_server={usar_selo_sql_server}")
    return usar_selo_sql_server


def executar_query(db: Any, query: str, params: tuple) -> dict[str, Any]:
    logging.debug(f"Executando query: {query} com params: {params}")
    try:
        result_sql = db.execute_query(query, params)
        if not result_sql:
            logging.warning("Nenhum resultado retornado da consulta.")
            return {}
        logging.debug(f"Resultado da query: {result_sql}")
        return result_sql[0]
    except Exception:
        logging.exception("ERRO ao obter valores da certidão:")
        raise


def processar_resultados(
    result_sql: dict[str, Any],
    usar_selo_sql_server: str,
) -> dict[str, Any]:
    logging.debug(f"Processando resultados da query: {result_sql}")
    valores = {
        "valor_emolumento": Decimal(result_sql["VALOR"]) if result_sql["VALOR"] else 0,
        "valor_certidao": Decimal(result_sql["VALOR"]) if result_sql["VALOR"] else 0,
        "tipo_certidao": result_sql["CODIGO_VALORES_CERTIDOES"] if result_sql else 0,
        "valor_tfj": Decimal(result_sql["TAXAJUDICIARIA"])
        if result_sql["TAXAJUDICIARIA"]
        else 0,
        "valor_fundo_estado": Decimal(result_sql["ADIC_VALOR"])
        if result_sql["ADIC_VALOR"]
        else 0,
        "quantidade": 1,
        "percentual_issqn": Decimal(result_sql["TAXA1"]) if result_sql["TAXA1"] else 0,
        "chave_emolumento_ws_go": result_sql["CHAVE_EMOLUMENTO_WS_GO"],
        "valor_issqn_formatada": "0.00",
        "valor_total": 0,
    }

    valor_issqn = valores["valor_emolumento"] * (
        valores["percentual_issqn"] / Decimal("100")
    )
    valores["valor_issqn_formatada"] = f"{valor_issqn:,.2f}"
    valores["valor_certidao"] += valor_issqn
    valores["valor_total"] = (
        valores["valor_emolumento"]
        + valores["valor_fundo_estado"]
        + valores["valor_tfj"]
        + valor_issqn
    )
    logging.debug(f"Valores processados: {valores}")
    return valores


def get_valores_certidao_fb_2(
    vigencia_id: str,
    codigo_tabela: str,
    categoria_id: str,
    certidao_id_sistema_antigo: str,
    db: Any,
) -> dict[str, Any]:
    logging.debug(
        f"Iniciando get_valores_certidao_fb_2 com vigencia_id={vigencia_id}, codigo_tabela={codigo_tabela}, categoria_id={categoria_id}, certidao_id_sistema_antigo={certidao_id_sistema_antigo}",
    )
    usar_selo_sql_server = obter_usar_selo_sql_server()
    query = construir_query_valores_certidao(
        usar_selo_sql_server,
        certidao_id_sistema_antigo,
        codigo_tabela,
    )
    params = ()  # (codigo_tabela) if usar_selo_sql_server != "S" else ()
    result_sql = executar_query(db, query, params)
    if not result_sql:
        valores_iniciais = {
            "valor_emolumento": 0,
            "valor_certidao": 0,
            "tipo_certidao": 0,
            "valor_tfj": 0,
            "valor_fundo_estado": 0,
            "quantidade": 1,
            "percentual_issqn": 0,
            "chave_emolumento_ws_go": "",
            "valor_issqn_formatada": "0.00",
            "valor_total": 0,
        }
        logging.debug(
            f"Nenhum resultado encontrado, retornando valores iniciais: {valores_iniciais}",
        )
        return valores_iniciais
    valores_processados = processar_resultados(result_sql, usar_selo_sql_server)
    logging.debug(f"Valores finais processados: {valores_processados}")
    return valores_processados


def numero_disponivel_no_fb(numero_pedido, db: FbConnection) -> bool:
    """Verifica se o número do pedido está disponível para ser utilizado."""
    logger.info(f"Verificando se o número do pedido {numero_pedido} está livre.")

    query = f"SELECT COUNT(CHAVE_PED_CERTIDOES) FROM PED_CERTIDOES WHERE CHAVE_PED_CERTIDOES = {numero_pedido}"
    try:
        ped_certidoes = db.execute_query(query)[0]
    except Exception:
        logging.exception(
            f"ERRO ao verificar se o número do pedido {numero_pedido} está livre.",
        )
        raise

    if ped_certidoes["COUNT"] > 0:
        msg = f"O número do pedido {numero_pedido} não está disponível."
        logger.warning(msg)
        return False

    logger.info(f"O número do pedido {numero_pedido} está disponível no FB.")
    return True


def gravar_ped_certidao_fb(
    pedido_certidao: "PedidoCertidao",
    descricao_observacao,
    origem_id: int,
    valor_transacao: Decimal,
    db: FbConnection,
):
    from apps.home.models import Configuracao

    origem_id = origem_id or 1
    valor_transacao = valor_transacao or 0
    descricao_observacao = descricao_observacao or ""

    logger.info(
        f"Gravando pedido de certidão {pedido_certidao.numero_pedido} no Firebird .",
    )

    # numero_proximo_pedido_firebird = db.sequence("PED_CERTIDOES_SEQ").proximo

    # proximo_pedido = numero_proximo_pedido_firebird

    # Verifica se o número do pedido atual no firebird é igual ao número do pedido de certidão
    # if numero_proximo_pedido_firebird == pedido_certidao.numero_pedido:
    #    proximo_pedido = pedido_certidao.numero_pedido

    # Verifica se o número do pedido atual no firebird é menor que o número do pedido do certidão
    # e define o próximo pedido do firebird como o número do pedido do certidão atual.
    # atualizando a sequence do firebird
    # if numero_proximo_pedido_firebird < pedido_certidao.numero_pedido:
    #    proximo_pedido = db.sequence("PED_CERTIDOES_SEQ").proximo

    # Verifica se o número do pedido atual está disponível no Firebird
    # if numero_disponivel_no_fb(pedido_certidao.numero_pedido, db):
    # Se estiver disponível, define pedido_id como o número atual do pedido
    #    pedido_id = pedido_certidao.numero_pedido

    # else:
    # Caso contrário, entra em um loop para encontrar o próximo número de pedido disponível
    #    while (
    #        numero_disponivel_no_fb(proximo_pedido, db) is False
    #        or proximo_pedido < pedido_certidao.numero_pedido
    #    ):
    # Obtém o próximo número da sequência de pedidos do Firebird
    #        proximo_pedido = db.sequence("PED_CERTIDOES_SEQ").proximo

    # Define pedido_id como o próximo número de pedido disponível
    #    pedido_id = proximo_pedido
    # Atualiza o número de pedido no Firebird com o novo número encontrado
    #    pedido_certidao.numero_pedido_firebird = pedido_id
    # Salva as alterações no banco de dados
    #    pedido_certidao.save()

    # Garante que a sequence do Firebird esteja atualizada para qualquer cenário.
    # while db.sequence("PED_CERTIDOES_SEQ").atual < pedido_id:
    #    _ = db.sequence("PED_CERTIDOES_SEQ").proximo

    nome = str(pedido_certidao.apresentante.nome).replace("'", "")

    # OBSERVACAO
    observacao_apresentante = str(pedido_certidao.apresentante.observacao).replace(
        "'",
        "",
    )

    # SENHA DO SITE
    senha_site = str(pedido_certidao.senha_site) if pedido_certidao.senha_site else ""

    observacao = (
        descricao_observacao
        if descricao_observacao
        else (
            pedido_certidao.observacao
            if pedido_certidao.observacao
            else pedido_certidao.protocolo_onr
            if pedido_certidao.protocolo_onr
            else ""
        )
    )

    if str(observacao) == "":
        observacao = observacao_apresentante

    pedido_data = db.datahora()
    funcionario_id = (
        pedido_certidao.criado_por_id
        if pedido_certidao.criado_por_id
        # else Configuracao.obter("funcionario_id_sistema_antigo", 999998)
        else Configuracao.obter("funcionario_id_sistema_antigo", 1)
    )

    data_prevista = pedido_certidao.data_prazo_final.strftime(
        settings.DATETIME_FIREBIRD_FORMAT,
    )
    tipo_certidao_cri = ""
    numero_pedido_cri = (
        pedido_certidao.protocolo_onr if pedido_certidao.protocolo_onr else ""
    )
    nome_busca = pedido_certidao.apresentante.nome
    fone = pedido_certidao.apresentante.telefone
    valor_fundo_estado = pedido_certidao.total_recompe_pedido
    taxa_judic = pedido_certidao.total_taxa_fiscal_judiciaria_pedido
    var_cpf = pedido_certidao.apresentante.documento
    email = pedido_certidao.apresentante.email
    validacao_crimg = ""
    detalhes = ""

    # ALFENAS ADICIONAR CAMPOS PARA O SQLSERVER
    cartorio_model = apps.get_model("cartorios", "Cartorio")
    usar_selo_sql_server = cartorio_model.objects.all().values_list(
        "usar_selo_sql_server",
        flat=True,
    )[0]
    if usar_selo_sql_server == "S":
        valor_transacao = (
            pedido_certidao.total_pedido
            + pedido_certidao.total_taxa_fiscal_judiciaria_pedido
            + pedido_certidao.total_recompe_pedido
            + pedido_certidao.total_issqn_pedido
        )

    # valor_issqn = f"{Decimal(var_emol * (issqn / 100)):,.2f}"
    valor_pedido = Decimal(valor_transacao) + valor_fundo_estado
    observacao = str(observacao) + " - " + str(validacao_crimg)
    var_cpf = apenas_numeros(var_cpf)

    # NOVO ID
    # pedido_id = pedido_certidao.numero_pedido

    comando = """
    INSERT INTO PED_CERTIDOES (
        CHAVE_PED_CERTIDOES, NOMEAPRESENTANTE, OBS, DATAPEDIDO,
        CHAVE_FUNCIONARIOS, ORIGEM_PEDIDO, TAXA1, VALOR_CALC, TX_JUDICIARIA,
        VALOR_PAGO, TIPOCERTIDAOCRI, NUMEROPEDIDOCRI, DATAPREVISTA, NOMEFUNCBUSCA,
        TELEFONE, CPF, CPF_CNPJ_APRESENTANTE, EMAIL_APRESENTANTE, DETALHES,
        ENDERECO, CODIGO_VALIDACAO_CRIMG, FSENHACONSULTA
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """

    # PEGAR O USER CONECTADO
    funcionario_id = funcionario_id if funcionario_id else "1"

    # 1 = Eletronica, 2 = Serventia
    origem_id = (
        1 if origem_id > 2 or origem_id is None or origem_id is None else origem_id
    )

    pedido_certidao_id = pedido_certidao.numero_pedido

    params = (
        # pedido_certidao.id,
        pedido_certidao_id,
        nome,
        observacao,
        pedido_data,
        funcionario_id,
        origem_id,
        valor_fundo_estado,
        valor_pedido,
        taxa_judic,
        valor_pedido,
        tipo_certidao_cri,
        numero_pedido_cri,
        data_prevista,
        nome_busca,
        fone,
        var_cpf,
        var_cpf,
        email,
        detalhes,
        detalhes[:298],
        validacao_crimg,
        senha_site,
    )

    logger.info(f"Gravando pedido. ID: {pedido_certidao.numero_pedido}")

    try:
        db.execute_command(comando, params)
        logger.info(
            f"FB: Sucesso comando - gravar pedido: {pedido_certidao.numero_pedido} - {nome}",
        )

        # pedido_certidao_id = pedido_certidao.id
        pedido_certidao_id = pedido_certidao.numero_pedido

        return {
            "CHAVE_PED_CERTIDOES": pedido_certidao_id,
            "nome": nome,
            "observacao": observacao,
            "pedido_data": pedido_data,
            "funcionario_codigo": funcionario_id,
            "origem_id": origem_id,
            "valor_fundo_estado": valor_fundo_estado,
            "valor_transacao": valor_pedido,
            "taxa_judic": taxa_judic,
            "tipo_certidao_cri": tipo_certidao_cri,
            "pedido_numero_cri": numero_pedido_cri,
            "data_prevista": data_prevista,
            "nome_busca": nome_busca,
            "fone": fone,
            "var_cpf": var_cpf,
            "email": email,
            "detalhes": detalhes,
            "validacao_crimg": validacao_crimg,
        }

    except Exception as e:
        logger.exception(
            f"ERRO gravar pedido de Certidao. ID: {pedido_certidao.numero_pedido}. Erro: {e}",
        )
        raise


'''
def gravar_pessoa_ped_certidao_fb(
    pedido_id,
    nome,
    documento,
    estado_civil,
    complemento,
    db: FbConnection,
) -> bool:
    print("Iniciando o processo de gravação de pessoa e pedido de certidão.")

    db = FbConnection() if db is None else db

    def get_max_ped_certidao_pessoas():
        print("Obtendo o maior valor da chave em PED_CERTIDOES_PESSOAS.")
        query = " SELECT MAX(CHAVE_PED_CERTIDOES_PESSOAS) FROM PED_CERTIDOES_PESSOAS "
        result = db.execute_query(query)[0]
        logger.info(f"Valor máximo encontrado: {result[0]}")
        return int(result[0]) + 1

    def restart_sequence_with_value(value) -> None:
        logger.info(f"Reiniciando a sequência com o valor {value}.")
        query = f" ALTER SEQUENCE PED_CERTIDOES_PESSOAS_SEQ RESTART WITH {value}"
        db.execute_command(query)

    def insert_ped_certidoes_pessoas(
        pedido_id,
        nome,
        documento,
        complemento,
        estado_civil=0,
        valor_coluna="T",
        # db: FbConnection,
    ) -> None:
        logger.info(f"Preparando para inserir dados do pedido {pedido_id} e pessoa {nome}.")

        query = """ INSERT INTO PED_CERTIDOES_PESSOAS
                (CHAVE_PED_CERTIDOES, CHAVE_PED_CERTIDOES_PESSOAS, NOME, DOCUMENTO, 110350, CREGISTRO, ESTADOCIVIL)
                VALUES (:CHAVE_PED_CERTIDOES, GEN_ID(PED_CERTIDOES_PESSOAS_SEQ, 1), :NOME, :DOCUMENTO, :COMPLEMENTO, :CREGISTRO, :ESTADOCIVIL)"""

        query = str(query).replace(":CHAVE_PED_CERTIDOES", str(pedido_id))
        query = str(query).replace(":NOME", "'" + str(nome) + "'")
        query = str(query).replace(":DOCUMENTO", "'" + str(documento) + "'")
        query = str(query).replace(":COMPLEMENTO", "'" + str(complemento) + "'")
        query = str(query).replace(":CREGISTRO", "'" + str(valor_coluna) + "'")
        query = str(query).replace(":ESTADOCIVIL", str(estado_civil))

        print(query)

        # parameters = (
        #     pedido_id,
        #     nome,
        #     documento,
        #     complemento,
        #     valor_coluna,
        #     estado_civil,
        # )

        # db = FbConnection() if db is None else db

        try:
            logger.info(f"Inserindo dados do pedido {pedido_id} e pessoa {nome}.")
            # db.execute_command(query, parameters)
            db.execute_command(query)

            print("Dados inseridos .")
        except Exception as e:
            logging.exception(
                f"ERRO ao adicionar PESSOAS do pedido com o ID: '{pedido_id}'. Detalhes do erro: {e}",
            )
            raise

    max_ped_certidao_pessoas = get_max_ped_certidao_pessoas()
    restart_sequence_with_value(max_ped_certidao_pessoas + 1)
    insert_ped_certidoes_pessoas(pedido_id, nome, documento, complemento, estado_civil, "T")

    return True
'''


def gravar_pessoa_ped_certidao_fb(
    pedido_id: int,
    nome: str,
    documento: str,
    estado_civil: str,
    complemento: str,
    db: FbConnection,
) -> int:
    print(
        f"Iniciando o processo de gravação de pessoa e pedido de certidão. ID: {pedido_id}.",
    )
    db = FbConnection() if db is None else db
    # query = " SELECT MAX(CHAVE_PED_CERTIDOES_PESSOAS) FROM PED_CERTIDOES_PESSOAS "
    # response = db.execute_query(query)
    # max_ped_certidao_pessoas = int(response[0][0]) + 2

    # # Agora, usando a formatação de strings do Python para inserir o valor na consulta:
    # adjustment_query = f"ALTER SEQUENCE PED_CERTIDOES_PESSOAS_SEQ RESTART WITH {max_ped_certidao_pessoas}"
    # db.execute_command(adjustment_query)

    sequence_id = db.alinhar_e_get_sequence(
        table_name="PED_CERTIDOES_PESSOAS",
        field_name="CHAVE_PED_CERTIDOES_PESSOAS",
        sequence_name="PED_CERTIDOES_PESSOAS_SEQ",
    )

    # GERAR PROXIMO ID DE SEQUENCE
    sequence_id += 1
    print(sequence_id)

    query = f"""INSERT INTO PED_CERTIDOES_PESSOAS
                (CHAVE_PED_CERTIDOES,
                CHAVE_PED_CERTIDOES_PESSOAS,
                NOME,
                DOCUMENTO,
                COMPLEMENTO,
                CREGISTRO,
                ESTADOCIVIL)
                VALUES (
                    {pedido_id!s},
                    {sequence_id},
                    '{nome!s}',
                    '{documento!s}',
                    '{complemento!s}',
                    'T',
                    {estado_civil!s}
                )"""

    print()
    logger.info(f"Gravando pessoa {sequence_id} - {nome} do pedido: {pedido_id}")

    try:
        db.execute_command(query)
        print("Exportado pessoa com sucesso.")

    except Exception:
        logging.exception(f"ERRO ao gravar IMOVEIS no pedido. ID: '{pedido_id}'")
        raise

    return sequence_id


def gravar_imoveis_ped_certidao_fb(
    pedido_id,
    matricula,
    cartorio,
    livro,
    db: FbConnection,
) -> int:
    logger.info(f"Gravando imóvel {matricula} do pedido. ID: {pedido_id}")

    matricula = somente_numeros(matricula)

    try:
        if matricula:
            int(matricula)
    except Exception:
        msg = f"ERRO ao converter matricula para inteiro: '{matricula}'"
        logger.exception(msg)
        logger.exception(msg)
        matricula = 0

    sequence_pedido_imoveis = 0

    # if int(matricula) > 0:
    tipo_livro = get_tipo_de_livro(livro)
    valor_col = "T"
    # if int(matricula) > 0:
    tipo_livro = get_tipo_de_livro(livro)
    valor_col = "T"

    # query = " SELECT MAX(CHAVE_PED_CERTIDOES_IMOVEIS) FROM PED_CERTIDOES_IMOVEIS"
    # db = FbConnection() if db is None else db
    # response = db.execute_query(query)
    # max_ped_certidao_imoveis = int(response[0][0])

    # # Agora, usando a formatação de strings do Python para inserir o valor na consulta:
    # adjustment_query = f"ALTER SEQUENCE PED_CERTIDOES_IMOVEIS_SEQ RESTART WITH {max_ped_certidao_imoveis}"
    # db.execute_command(adjustment_query)

    sequence_pedido_imoveis = db.alinhar_e_get_sequence(
        table_name="PED_CERTIDOES_IMOVEIS",
        field_name="CHAVE_PED_CERTIDOES_IMOVEIS",
        sequence_name="PED_CERTIDOES_IMOVEIS_SEQ",
    )

    query = """
        INSERT INTO PED_CERTIDOES_IMOVEIS
            (CHAVE_PED_CERTIDOES, CHAVE_PED_CERTIDOES_IMOVEIS, MATRICULA, CARTORIO, CMATRICULA, TIPO)
        VALUES (?, ?, ?, ?, ?, ?)
        """

    params = (
        pedido_id,
        sequence_pedido_imoveis,
        matricula,
        cartorio,
        valor_col,
        tipo_livro,
    )
    try:
        db.execute_command(query, params)

    except Exception:
        logging.exception(f"ERRO ao gravar IMOVEIS no pedido. ID: '{pedido_id}'")
        raise
    # else:
    #     logger.info(f"Imóvel {matricula} do pedido {pedido_id} não foi gravado.")

    return sequence_pedido_imoveis


def gravar_tipos_ped_certidao(
    pedido_id,
    percentual_desconto,
    codigo_tabela,
    quantidade,
    funcionario_id,
    certidao_id_sistema_antigo,
    tipo_tributacao_outros_id,
    db: FbConnection,
):
    """Armazena a Certidão em si. Que constratá no pedido. Incluindo os valores e as quantidade."""
    logger.info(f"Gravando tipos do pedido. ID: {pedido_id}")

    db.sequence("PED_CERTIDOES_TIPOS_SEQ").alinhar(
        "CHAVE_PED_CERTIDOES_TIPOS",
        "PED_CERTIDOES_TIPOS",
    )

    sequence_tipo_certidao = db.sequence("PED_CERTIDOES_TIPOS_SEQ").proximo
    data_pedido = db.datahora()
    vigencia_id = str(get_vigencia_atual_firebird(db))
    # valores = get_valores_certidao_fb(vigencia_id, codigo_tabela, estado_civil_id)

    # ALFENAS ADICIONAR CAMPOS PARA O SQLSERVER
    ano_referencia_tabela = timezone.now().year

    codigo_tabela_int = codigo_tabela[0:4]
    valor_emolumentos_bruto = 0
    valor_total = 0
    chave_emolumento_ws_go = 0
    chave_ped_certidoes_imoveis = 0

    valores = get_valores_certidao_fb_2(
        vigencia_id=vigencia_id,
        codigo_tabela=codigo_tabela,
        categoria_id=percentual_desconto,
        certidao_id_sistema_antigo=certidao_id_sistema_antigo,
        db=db,
    )

    if valores is None:
        logging.error(
            "Não foi possível obter os valores da certidão. Verifique os parâmetros.",
        )
        return None

    # issqn = "{:,.2f}".format(Decimal((valores["valor"] * (valores["issqn"] / 100))))
    # valor = Decimal(valores["valor"]) + Decimal(valores["issqn"])

    funcionario_id = "1"

    comando = """
            INSERT INTO PED_CERTIDOES_TIPOS (
                CHAVE_PED_CERTIDOES_TIPOS,
                CHAVE_PED_CERTIDOES,
                TIPO_CERTIDAO, QUANTIDADE,
                VALOR,
                TX_JUDICIARIA,
                CODIGO_TABELA,
                ADIC_VALOR,
                CHAVE_FUNCIONARIOS,
                TAXA1,
                DATAPEDIDO, CATEGORIA,
                CHAVE_VIGOR, VALOR_FUNDOESTADO,
                ANO_REFERENCIA_TABELA,
                CODIGO_TIPO_TRIBUTACAO,
                CODIGO_ATOSELO,
                VALOR_EMOLUMENTOS_BRUTO, VALOR_TOTAL,
                CHAVE_EMOLUMENTO_WS_GO,
                CHAVE_PED_CERTIDOES_IMOVEIS
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """

    # EXPORTAR VALORES
    valor_tfj = valores["valor_tfj"]
    emolumento_total = valores["valor_total"]
    valor_fundo_estado = valores["valor_fundo_estado"]
    valor_issqn_formatada = valores["valor_issqn_formatada"]
    valor_fundo_estado = valores["valor_fundo_estado"]

    # ALFENAS ADICIONAR CAMPOS PARA O SQLSERVER
    cartorio_model = apps.get_model("cartorios", "Cartorio")
    usar_selo_sql_server = cartorio_model.objects.all().values_list(
        "usar_selo_sql_server",
        flat=True,
    )[0]

    if usar_selo_sql_server == "S":
        emolumento_total = valores["valor_emolumento"]
        ano_referencia_tabela = timezone.now().year

        codigo_tabela_int = codigo_tabela[0:4]
        valor_emolumentos_bruto = (
            valores["valor_emolumento"] + valores["valor_fundo_estado"]
        )
        valor_total = (
            valor_emolumentos_bruto
            + valores["valor_tfj"]
            + (
                valores["valor_emolumento"]
                * (valores["percentual_issqn"] / Decimal("100"))
            )
        )
        chave_emolumento_ws_go = valores["chave_emolumento_ws_go"]

        # CORRIGINDO O CODIGO PARA O FIREBIR
        if chave_emolumento_ws_go == "":
            if codigo_tabela_int == "4902":
                chave_emolumento_ws_go = "140"
            elif codigo_tabela_int == "8101":
                chave_emolumento_ws_go = "120"
            elif codigo_tabela_int == "8301":
                chave_emolumento_ws_go = "121"
            elif codigo_tabela_int == "8401":
                chave_emolumento_ws_go = "122"
            elif codigo_tabela_int == "8402":
                chave_emolumento_ws_go = "123"
            else:
                chave_emolumento_ws_go = "122"

        chave_ped_certidoes_imoveis = 1

    # PEGANDO NO FIBERBIRD OS VALORES
    certidao_id_sistema_antigo = (
        certidao_id_sistema_antigo
        if certidao_id_sistema_antigo
        else valores["tipo_certidao"]
    )

    # PERCENTUAL DE DESCONTO PARA FIREBIRD = 1 NORMAL
    if percentual_desconto == 0:
        codigo_tipo_tributacao = 1
        percentual_desconto = 1

        # VERIFICAR COMPLEMENTARES - 28 Ato retificador/renovador em razão de erro imputável ao próprio cartório
        if int(tipo_tributacao_outros_id) == 28:
            valor_total = valor_tfj
            (
                valor_fundo_estado,
                valor_issqn_formatada,
                valor_emolumentos_bruto,
                emolumento_total,
            ) = 0, 0, 0, 0

            codigo_tipo_tributacao = tipo_tributacao_outros_id

    elif percentual_desconto == 100:
        codigo_tipo_tributacao = 10
        percentual_desconto = 100
    else:
        codigo_tipo_tributacao = percentual_desconto

    params = (
        sequence_tipo_certidao,
        pedido_id,
        certidao_id_sistema_antigo,
        quantidade,
        emolumento_total,
        valor_tfj,
        codigo_tabela,
        valor_fundo_estado,
        funcionario_id,
        valor_issqn_formatada,
        data_pedido,
        percentual_desconto,
        vigencia_id,
        valor_fundo_estado,
        ano_referencia_tabela,
        codigo_tipo_tributacao if codigo_tipo_tributacao else 1,
        codigo_tabela_int,
        valor_emolumentos_bruto,
        valor_total,
        chave_emolumento_ws_go,
        chave_ped_certidoes_imoveis,
    )

    logger.info(f"Gravando tipos do pedido. ID: {pedido_id}")
    try:
        db = FbConnection() if db is None else db
        db.execute_command(comando, params)
    except Exception:
        logging.exception(f"ERRO ao gravar TIPOS do pedido: '{pedido_id}'")
        raise

    return sequence_tipo_certidao


def atualizar_ped_certidoes(pedido_fb, db: FbConnection) -> None:
    queries = []
    parameter = pedido_fb["CHAVE_PED_CERTIDOES"]

    queries.append(
        f"""
        UPDATE PED_CERTIDOES
        SET VALOR_CALC = (
            SELECT SUM(VALOR)
            FROM PED_CERTIDOES_TIPOS
            WHERE CHAVE_PED_CERTIDOES = {parameter}
        )
        WHERE CHAVE_PED_CERTIDOES = {parameter};""",
    )

    queries.append(
        f"""
        UPDATE PED_CERTIDOES
        SET VALOR_PAGO = (
            SELECT SUM(VALOR)
            FROM PED_CERTIDOES_TIPOS
            WHERE CHAVE_PED_CERTIDOES = {parameter}
        )
        WHERE CHAVE_PED_CERTIDOES = {parameter};""",
    )

    queries.append(
        f"""
        UPDATE PED_CERTIDOES
        SET TX_JUDICIARIA = (
            SELECT SUM(TX_JUDICIARIA)
            FROM PED_CERTIDOES_TIPOS
            WHERE CHAVE_PED_CERTIDOES = {parameter}
        )
        WHERE CHAVE_PED_CERTIDOES = {parameter};""",
    )

    queries.append(
        f"""
        UPDATE PED_CERTIDOES
        SET TAXA1 = (
            SELECT SUM(TAXA1)
            FROM PED_CERTIDOES_TIPOS
            WHERE CHAVE_PED_CERTIDOES = {parameter}
        )
        WHERE CHAVE_PED_CERTIDOES = {parameter};""",
    )

    # ALFENAS ADICIONAR CAMPOS PARA O SQLSERVER
    cartorio_model = apps.get_model("cartorios", "Cartorio")
    usar_selo_sql_server = cartorio_model.objects.all().values_list(
        "usar_selo_sql_server",
        flat=True,
    )[0]
    if usar_selo_sql_server == "S":
        queries.clear()
        queries.append(
            f"""
            UPDATE PED_CERTIDOES AS P
            SET
                P.VALOR_CALC = (
                    SELECT SUM(VALOR + TX_JUDICIARIA + VALOR_FUNDOESTADO + TAXA1)
                    FROM PED_CERTIDOES_TIPOS T
                    WHERE T.CHAVE_PED_CERTIDOES = {parameter}
                ),

                P.valor_adicional = (
                    SELECT SUM(VALOR_FUNDOESTADO)
                    FROM PED_CERTIDOES_TIPOS T
                    WHERE T.CHAVE_PED_CERTIDOES = {parameter}
                ),

                P.VALOR_PAGO = (
                    SELECT SUM(VALOR + TX_JUDICIARIA + VALOR_FUNDOESTADO + TAXA1)
                    FROM PED_CERTIDOES_TIPOS T
                    WHERE T.CHAVE_PED_CERTIDOES = {parameter}
                ),
                P.TX_JUDICIARIA = (
                    SELECT SUM(TX_JUDICIARIA)
                    FROM PED_CERTIDOES_TIPOS T
                    WHERE T.CHAVE_PED_CERTIDOES = {parameter}
                ),
                P.TAXA1 = (
                    SELECT SUM(TAXA1)
                    FROM PED_CERTIDOES_TIPOS T
                    WHERE T.CHAVE_PED_CERTIDOES = {parameter}
                )
            WHERE P.CHAVE_PED_CERTIDOES = {parameter}
        """,
        )

    #    params = (pedido_fb["pedido_id"],) * 6

    try:
        for query in queries:
            db.execute_command(query)
    except Exception:
        logging.exception(
            f"ERRO ao atualizar PED_CERTIDOES. ID: '{pedido_fb['pedido_id']}'",
        )
        raise

    # if usar_selo_sql_server == "S":
    #     comando = """
    #         UPDATE ped_certidoes as p
    #         set p.valor_adicional = (   SELECT SUM(t.valor_fundoestado)
    #                                     FROM ped_certidoes_tipos t
    #                                     WHERE t.chave_ped_certidoes =  ?
    #                                 )
    #         WHERE p.ped_certiddoes = ?
    #     """
    #     params = (pedido_fb["pedido_id"],) * 5
    #     try:
    #     db = FbConnection() if db is None else db
    #     db.execute_command(query, params)
    # except Exception:
    #     logging.exception(
    #         f"ERRO ao atualizar PED_CERTIDOES. ID: '{pedido_fb['pedido_id']}'",
    #     )
    #     raise

    update_tx_judiciaria_fb(pedido_fb["CHAVE_PED_CERTIDOES"], db)


def update_tx_judiciaria_fb(pedido_certidao_id, db: FbConnection) -> None:
    query = """
            SELECT TX_JUDICIARIA
            FROM PED_CERTIDOES_TIPOS
            WHERE CHAVE_PED_CERTIDOES = ?
            """

    # Obtém todos os valores em uma lista
    results = db.execute_query(query, (pedido_certidao_id,))

    # total_tx_judiciaria = (
    #     sum(Decimal(row[0]) for row in results) if results else Decimal("0.00")
    # )
    total_tx_judiciaria = (
        sum(Decimal(row["TX_JUDICIARIA"]) for row in results)
        if results
        else Decimal("0.00")
    )

    # 2. Realizar a soma e arredondar
    total_arredondado = total_tx_judiciaria.quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )

    command = """
           UPDATE PED_CERTIDOES
           SET TX_JUDICIARIA = ?
           WHERE CHAVE_PED_CERTIDOES = ?
            """
    db.execute_command(command, (total_arredondado, pedido_certidao_id))


def gravar_andamentos_pedido_certidao(
    pedido_id,
    data,
    funcionario_id,
    tipo_andamento_id,
    db: FbConnection,
):
    logger.info(f"Gravando ANDAMENTOS do pedido. ID: {pedido_id}")
    andamento_id = db.sequence("ANDAMENTOS_PED_CERTIDOES_SEQ").proximo
    # data_atual = str(timezone.now())
    data_atual = db.datahora()

    comando = f"""
        INSERT INTO ANDAMENTOS_PED_CERTIDOES (
            CHAVE_ANDAMENTOS, CHAVE_PED_CERTIDOES, DATA,
            CHAVE_FUNCIONARIOS, CHAVE_SERVICOS_ANDAMENTOS, CHAVE_FUNCIONARIOS_DESTINO
        )
        VALUES (
            {andamento_id}, {pedido_id}, '{data_atual}',
            {funcionario_id}, {tipo_andamento_id}, {funcionario_id}
        )
    """

    logger.info(f"Gravando ANDAMENTOS do pedido. ID: {pedido_id}")

    try:
        db.execute_command(comando)
    except Exception:
        logging.exception(f"ERRO ao gravar ANDAMENTOS do pedido. ID: '{pedido_id}':")
        raise

    return andamento_id


def deletar_pedido_certidao_fb(pedido_id: str) -> None:
    logging.debug("Iniciando a função deletar_pedido_certidao_fb")

    try:
        with FbConnection() as db:
            logging.debug("Conexão com o banco de dados Firebird estabelecida")
            db.begin_transaction()
            logging.debug("Iniciando transação")

            try:
                quantidade = (
                    verificar_se_pedido_existe_por_numero_e_apresentante_no_firebird(
                        pedido_certidao_id=pedido_id,
                        nome_apresentante="",
                        opcao_pesquisa=1,
                        db=db,
                    )
                )
                logging.debug(f"Quantidade de pedidos encontrados: {quantidade}")
            except Exception:
                logging.exception(
                    f"Erro ao verificar existência do pedido. ID: '{pedido_id}'",
                )
                raise

            # quantidade = 0

            # APENAS ATUALIZAR
            if quantidade > 0:
                str_id = str(pedido_id)
                logging.debug(f"ID do pedido convertido para string: {str_id}")

                try:
                    # DELETAR NO FIREBIRD PARA GERAR NOVO PEDIDO
                    db.execute_command(
                        "DELETE FROM CERTIDOES_IMPRESSAS WHERE CHAVE_PED_CERTIDOES = "
                        + str_id,
                    )
                    logging.debug(
                        f"Deletado da tabela CERTIDOES_IMPRESSAS para ID: {str_id}",
                    )

                    db.execute_command(
                        "DELETE FROM ANDAMENTOS_PED_CERTIDOES WHERE CHAVE_PED_CERTIDOES = "
                        + str_id,
                    )
                    logging.debug(
                        f"Deletado da tabela ANDAMENTOS_PED_CERTIDOES para ID: {str_id}",
                    )

                    db.execute_command(
                        "DELETE FROM CAIXA WHERE CHAVE_PED_CERTIDOES = " + str_id,
                    )
                    logging.debug(f"Deletado da tabela CAIXA para ID: {str_id}")

                    db.execute_command(
                        "DELETE FROM PED_CERTIDOES_IMOVEIS WHERE CHAVE_PED_CERTIDOES = "
                        + str_id,
                    )
                    logging.debug(
                        f"Deletado da tabela PED_CERTIDOES_IMOVEIS para ID: {str_id}",
                    )

                    db.execute_command(
                        "DELETE FROM PED_CERTIDOES_PESSOAS WHERE CHAVE_PED_CERTIDOES = "
                        + str_id,
                    )
                    logging.debug(
                        f"Deletado da tabela PED_CERTIDOES_PESSOAS para ID: {str_id}",
                    )

                    db.execute_command(
                        "DELETE FROM PED_CERTIDOES_TIPOS WHERE CHAVE_PED_CERTIDOES = "
                        + str_id,
                    )
                    logging.debug(
                        f"Deletado da tabela PED_CERTIDOES_TIPOS para ID: {str_id}",
                    )

                    db.execute_command(
                        "DELETE FROM PED_CERTIDOES WHERE CHAVE_PED_CERTIDOES = "
                        + str_id,
                    )
                    logging.debug(f"Deletado da tabela PED_CERTIDOES para ID: {str_id}")

                    db.commit()
                    logging.debug("Transação commitada com sucesso")

                except Exception:
                    db.rollback()
                    logging.exception(f"Erro ao deletar pedido. ID: '{pedido_id}'")
                    raise
            else:
                db.rollback()
                logging.debug("Pedido não encontrado. Criar Novo")

                # DIRECIONAR PARA UMA PAGINA DE CADASTRO
                url = reverse("home:pedido_certidao_exportar", args=[pedido_id])
                return redirect(url)

    except Exception as e:
        print(e)

        logging.exception(
            f"Erro geral ao processar pedido de certidão. ID: '{pedido_id}'",
        )
        raise


# CANCELAR O PEDIDO CASO DE ERRO
def cancelar_pedido_certidao_fb(pedido_id, db: FbConnection) -> int:
    if not pedido_id:
        return 1

    try:
        comando = """ INSERT INTO PED_CERTIDOES
            (CHAVE_PED_CERTIDOES, DATAPEDIDO, NOMEAPRESENTANTE,
            VALOR_CALC, VALOR_PAGO, OBS, DATAPREVISTA, TX_JUDICIARIA,
            CANCELADO, CHAVE_FUNCIONARIOS)
        VALUES (?, CURRENT_TIMESTAMP, 'CANCELADO', 0, 0, ' -', CURRENT_TIMESTAMP, 0, 'T',  999998); """

        parametros = (pedido_id,)

        logger.info(f"Cancelando o pedido. ID: {pedido_id}")

        db.execute_command(comando, parametros)

        # LIMPAR NO PEDIDO DE CERTIDAO - POSTGRESQL
        desvincular_numero_pedido_firebird(pedido_id)

    except Exception:
        logging.exception(f"ERRO ao ATUALIZAR pedido. ID: '{pedido_id}'")
        raise

    return 1


# DESVINCULAR NUMERO PEDIDO FIREBIRD
def desvincular_numero_pedido_firebird(numero_pedido) -> None:
    from apps.home.models import PedidoCertidao

    """DESVINCULAR  número do pedido após verificar se o novo número já está em uso."""
    pedido = PedidoCertidao.objects.get(numero_pedido=numero_pedido)

    pedido.numero_pedido_firebird = None
    pedido.save()


def selar_item_no_firebird(
    db: FbConnection,
    ped_certidoes_id: int,
    pedido_certidao_item_id: int,
):
    logger.debug(
        f"Iniciando selar_item com ped_certidoes_id={ped_certidoes_id} e pedido_certidao_item_id={pedido_certidao_item_id}",
    )

    selo_para_consulta = "S"
    if pedido_certidao_ja_possui_qualquer_selo(ped_certidoes_id, db):
        selo_para_consulta = None

    logger.debug(f"selo_para_consulta definido como {selo_para_consulta}")

    comando = """
        UPDATE SELO_DIGITAL_MG
        SET UTILIZADO = 'S',
            CHAVE_PED_CERTIDOES = ?,
            CHAVE_PED_CERTIDOES_TIPOS = ?,
            DATA_UTILIZACAO = CURRENT_TIMESTAMP,
            SELO_PARA_CONSULTA = ?
        WHERE CODIGO_SEQUENCIAL_UNICO = (
            SELECT MIN(CODIGO_SEQUENCIAL_UNICO)
            FROM SELO_DIGITAL_MG
            WHERE CANCELADO = 'N' AND UTILIZADO = 'N'
        );
    """
    parametros = (
        ped_certidoes_id,
        pedido_certidao_item_id,
        selo_para_consulta,
    )
    logger.debug(f"Executando comando SQL: {comando} com parâmetros {parametros}")
    db.execute_command(comando, parametros)
    registrar_andamento_fb(db, ped_certidoes_id)

    logger.debug("Finalizado selar_item com sucesso.")


def pedido_certidao_ja_possui_qualquer_selo(
    pedido_certidao_id: int,
    db: FbConnection,
) -> bool:
    logger.debug(
        f"Verificando se o pedido_certidao_id={pedido_certidao_id} já possui qualquer selo.",
    )

    if not pedido_certidao_id:
        msg = "Pedido de certidão não informado."
        logger.error(msg)
        raise ValueError(msg)

    query = """
        SELECT COUNT(*)
        FROM SELO_DIGITAL_MG
        WHERE CHAVE_PED_CERTIDOES = ?
    """
    parametros = (pedido_certidao_id,)
    logger.debug(f"Executando consulta SQL: {query} com parâmetros {parametros}")
    saida = db.execute_query(query, parametros)

    possui_selo = saida[0]["COUNT"] != 0
    logger.debug(
        f"O pedido_certidao_id={pedido_certidao_id} possui selo: {possui_selo}",
    )

    return possui_selo


def selar_certidoes_do_pedido_certidao_fb(
    ped_certidoes_id: int,
    db: FbConnection,
) -> tuple[int | None, str | None]:
    logger.debug(
        f"Iniciando selar_certidoes_do_pedido_certidao_fb com ped_certidoes_id={ped_certidoes_id}",
    )

    if not ped_certidoes_id:
        logger.warning("ped_certidoes_id não fornecido, retornando erro.")
        return 1, None, None

    lista_ped_certidoes_tipos = get_itens_pedido_certidao_fb(db, ped_certidoes_id)

    if not lista_ped_certidoes_tipos:
        msg = "Nenhum item encontrado no FB para este Pedido de certidão."
        raise ValueError(msg)

    logger.debug(f"Lista de itens do pedido: {lista_ped_certidoes_tipos}")

    for pedido_certidao_item_id in lista_ped_certidoes_tipos:
        logger.debug(f"Processando item: {pedido_certidao_item_id}")
        if verificar_item_nao_selado_fb(db, pedido_certidao_item_id):
            logger.debug(f"Item {pedido_certidao_item_id} não selado, aplicando selo.")
            selar_item_no_firebird(db, ped_certidoes_id, pedido_certidao_item_id)
            processar_financeiro(db, ped_certidoes_id)

    resultado = get_primeiro_selo_pedido_certidao_fb(db, ped_certidoes_id)
    logger.debug(f"Resultado do selar_certidoes_do_pedido_certidao_fb: {resultado}")

    return resultado


def get_itens_pedido_certidao_fb(db: FbConnection, ped_certidoes_id: int) -> list[int]:
    logger.debug(f"Buscando itens do pedido com ped_certidoes_id={ped_certidoes_id}")

    query = """
        SELECT CHAVE_PED_CERTIDOES_TIPOS
        FROM PED_CERTIDOES_TIPOS
        WHERE CHAVE_PED_CERTIDOES = ?
    """
    parametros = (ped_certidoes_id,)
    itens = db.execute_query(query, parametros)
    if itens:
        itens = [item["CHAVE_PED_CERTIDOES_TIPOS"] for item in itens]
    logger.debug(f"Itens retornados: {itens}")

    return itens


def verificar_item_nao_selado_fb(
    db: FbConnection,
    pedido_certidao_item_id: int,
) -> bool:
    logger.debug(f"Verificando se o item {pedido_certidao_item_id} não foi selado.")

    query = """
        SELECT COUNT(CHAVE_PED_CERTIDOES_TIPOS)
        FROM SELO_DIGITAL_MG
        WHERE CHAVE_PED_CERTIDOES_TIPOS = ?
    """
    parametros = (pedido_certidao_item_id,)
    logger.debug(f"Executando consulta SQL: {query} com parâmetros {parametros}")

    resultados = db.execute_query(query, parametros)

    if resultados is None:
        logger.warning(
            f"Resultados retornaram None para pedido_certidao_item_id={pedido_certidao_item_id}",
        )
        return False

    nao_selado = resultados[0]["COUNT"] == 0
    logger.debug(f"O item {pedido_certidao_item_id} está não selado: {nao_selado}")

    return nao_selado


def registrar_andamento_fb(db: FbConnection, ped_certidoes_id: int) -> None:
    logger.debug(f"Registrando andamento para ped_certidoes_id={ped_certidoes_id}")

    andamento_id = db.sequence("ANDAMENTOS_PED_CERTIDOES_SEQ").proximo

    comando = """
        INSERT INTO ANDAMENTOS_PED_CERTIDOES (
            CHAVE_ANDAMENTOS, CHAVE_PED_CERTIDOES, DATA,
            CHAVE_FUNCIONARIOS, CHAVE_SERVICOS_ANDAMENTOS, CHAVE_FUNCIONARIOS_DESTINO
        )
        VALUES (?, ?, CURRENT_TIMESTAMP, ?, ?, ?)
    """
    parametros = (andamento_id, ped_certidoes_id, 1, 4, 1)
    logger.debug(f"Executando comando SQL: {comando} com parâmetros {parametros}")

    db.execute_command(comando, parametros)

    logger.debug("Andamento registrado com sucesso.")


def processar_financeiro(db: FbConnection, ped_certidoes_id: int) -> None:
    from apps.home.models import PedidoCertidao

    pedido_certidao = PedidoCertidao.objects.get(pk=ped_certidoes_id)
    if pedido_certidao.valor_diferenca > 0:
        pedido_fb = firebird.get_pedido_certidao_por_numero_fb(ped_certidoes_id, db)
        firebird.gravar_caixa_ped_certidao_fb(pedido_fb, pedido_certidao, 2, db)

        # pedido_certidao.enviar_pagamento_certidao_onr_caixa(
        #     pk=ped_certidoes_id,
        #     numero_pedido=ped_certidoes_id,
        #     valor_transacao=pedido_fb["VALOR_CALC"],
        #     descricao=pedido_fb["NOMEAPRESENTANTE"],
        #     db=db,
        # )

        data_transacao = timezone.now().strftime("%Y-%m-%d")
        financeiro = models.Financeiro.criar_financeiro_despesa_receita(
            pedido_id=None,
            pedido_certidao_id=ped_certidoes_id,
            tipo_transacao_id=1,
            tipo_categoria_financeira_id=1,
            tipo_operacao_financeira_id=1,
            colaborador_id=1,
            colaborador_confirmado_id=None,
            data_transacao=data_transacao,
            data_original_transacao=None,
            valor_transacao=pedido_certidao.valor_diferenca,
            dadp="N",
            imposto_renda="N",
            descricao=pedido_certidao.nome_apresentante,
            quantidade_parcelas=1,
            recorrencia_id=1,
            user_id=1,
        )
        print(financeiro)


def get_primeiro_selo_pedido_certidao_fb(
    db: FbConnection,
    ped_certidoes_id: int,
) -> tuple[int | None, str | None]:
    try:
        query = """
            SELECT FIRST 1 CODIGO_SEQUENCIAL_UNICO, CODIGO_DE_SEGURANCA
            FROM SELO_DIGITAL_MG
            WHERE CHAVE_PED_CERTIDOES = ?
        """
        parametros = (ped_certidoes_id,)

        results = db.execute_query(query, parametros)

        if not results:
            logging.warning("Nenhum resultado retornado da consulta de SELOELETRONICO.")
            return None, None, None
        return (
            results[0]["CODIGO_SEQUENCIAL_UNICO"],
            results[0]["CODIGO_DE_SEGURANCA"],
        )

    except Exception:
        db.rollback()
        logging.exception("ERRO ao selar o pedido de certidão")
        return None, None, None


def importar_cartorio_fb() -> None:
    nomes_colunas = [
        "NOMECARTORIO",
        "CARTORIO",
        "ENDECARTORIO",
        "CNPJCARTORIO",
        "FONECARTORIO",
        "NOMECARTORIOABREV",
        "CNPJCGCCARTORIO",
        "NOMEOFICIAL",
    ]

    # Query para obter o cartório
    query = """
            SELECT VALOR
            FROM
                INI
            WHERE
                SECAO = 'PRINCIPAL'
            AND ESTACAO = 'TODOS'
            AND NOME IN ('NOMECARTORIO', 'CARTORIO', 'ENDECARTORIO',
                'CNPJCARTORIO', 'FONECARTORIO', 'NOMECARTORIOABREV',
                'CNPJCGCCARTORIO', 'NOMEOFICIAL')
            """

    with FbConnection() as fb:
        fb.begin_transaction()
        resultados = fb.execute_query(query)

    # Convert resultado de 1 coluna em um dicionario
    try:
        dicionario_resultados = {
            nome: resultado["VALOR"]
            for nome, resultado in zip(nomes_colunas, resultados, strict=False)
        }
    except KeyError as e:
        print("Erro ao acessar chave do dicionário:", e)
        print("Resultados:", resultados)
        print("Resultados:", dicionario_resultados)
        raise
    except Exception as e:
        print("Erro desconhecido:", e)
        raise

    cartorio_model = apps.get_model("cartorios", "Cartorio")
    cartorio = cartorio_model.objects.order_by("id").first()

    if not cartorio:
        cartorio = cartorio_model()

    cartorio.nome = dicionario_resultados["NOMECARTORIO"]
    cartorio.logradouro = dicionario_resultados["ENDECARTORIO"]
    cartorio.cnpj = somente_numeros(dicionario_resultados["CNPJCARTORIO"])
    cartorio.telefone = dicionario_resultados["FONECARTORIO"]
    # cartorio.cnpj = dicionario_resultados["CNPJCGCCARTORIO"]
    try:
        cartorio.save()
    except Exception as e:
        print("Erro ao salvar cartório:", e)
        raise

    logger.info(f"Cartório importado com sucesso: {cartorio}")


# # GRAVAR ANDAMENTO NO FIREBIRD
# def gravar_protocolo_andamento_firebird(
#     protocolos_id,
#     funcionario_id,
#     servico_id,
#     andamentos_id,
#     db: FbConnection,
# ) -> int:
#     andamentos_id = andamentos_id or 0

#     if not protocolos_id:
#         return 1

#     comando = """
#                 INSERT INTO ANDAMENTOS (CHAVE_ANDAMENTOS, CHAVE_PROTOCOLOS, DATA, CHAVE_FUNCIONARIOS, CHAVE_SERVICOS_ANDAMENTOS)
#                 VALUES(:CHAVE_ANDAMENTOS, :CHAVE_PROTOCOLOS, :DATA, :CHAVE_FUNCIONARIOS, :CHAVE_SERVICOS_ANDAMENTOS);
#                 """

#     # BUSCAR APENAS SE NAO FOR INFORMADO
#     if andamentos_id == 0:
#         andamentos_id = db.sequence("ANDAMENTOS_SEQ").proximo

#     comando = comando.replace(":CHAVE_ANDAMENTOS", str(andamentos_id))
#     comando = comando.replace(":CHAVE_PROTOCOLOS", str(protocolos_id))
#     comando = comando.replace(":DATA", db.data_str)
#     comando = comando.replace(":CHAVE_FUNCIONARIOS", str(funcionario_id))
#     comando = comando.replace(":CHAVE_SERVICOS_ANDAMENTOS", str(servico_id))

#     # SALVANDO O COMANDO NO BANCO DE DADOS FIREBIRD
#     db.execute_command(comando)

#     return andamentos_id


# ATUALIZAR OS DADOS QUE TEM NO SQL SERVER NA TABELA TEMPORARIA DO PRIMEIRO BANCO - FIREBIRD
def update_firebird_temporario_sql_server(selos):
    with FbConnection() as db:
        db.begin_transaction()

        for selo in selos:
            print(
                "Selo atualizado: ",
                selo.get("CODIGO_SEQUENCIAL_UNICO", ""),
                " - Pesquisando selo",
                selo.get("PROTOCOLO", ""),
            )

            # FORMATAR DATA DE UTILIZACAO
            data_utilizacao = str(selo.get("DATA_UTILIZACAO", "")).split(".")[0]

            # LIMPAR O ARQUIVO PARA GARANTIR SINCRONISMO
            comando_deletar = (
                " DELETE FROM SELOS_SQL_SERVER WHERE SELO = '"
                + selo.get("CODIGO_SEQUENCIAL_UNICO", "")
                + "'"
            )

            # SQL para gravar no banco firebird
            comando_inserir = (
                " INSERT INTO SELOS_SQL_SERVER ("
                "        SELO, DATA_UTILIZACAO, IDENTIFICACAO, ROTINA, PROTOCOLO, "
                "        CODIGO_FISCAL_DO_ATO, TIPO_TRIBUTACAO,                   "
                "        VALOR_EMOLUMENTO, VALOR_FINAL_USUARIO, VALOR_TFJ,        "
                "        TX_RECOMPE, TX_ISSQN, CODIGO_DE_SEGURANCA)               "
                " VALUES ("
                "'" + selo.get("CODIGO_SEQUENCIAL_UNICO", "") + "'"
                ", "
                "'" + data_utilizacao + "'"
                ", "
                + str(selo.get("IDENTIFICACAO", ""))
                + ", "
                + str(selo.get("ROTINA", ""))
                + ", "
                + str(selo.get("PROTOCOLO", ""))
                + ", "
                + str(selo.get("CODIGO_FISCAL_DO_ATO", ""))
                + ", "
                + str(selo.get("TIPO_TRIBUTACAO", ""))
                + ", "
                + str(selo.get("VALOR_EMOLUMENTO", ""))
                + ", "
                + str(selo.get("VALOR_FINAL_USUARIO", ""))
                + ", "
                + str(selo.get("VALOR_TFJ", ""))
                + ", "
                + str(selo.get("TX_RECOMPE", ""))
                + ", "
                + str(selo.get("TX_ISSQN", ""))
                + ", '"
                + str(selo.get("CODIGO_DE_SEGURANCA", ""))
                + "'"
                + "); "
            )

            # EXCLUINDO E INSERINDO NO FIREBIRD
            db.execute_command(comando_deletar)
            db.execute_command(comando_inserir)

        db.commit()

    try:
        print("Selos gravados no SELOS_SQL_SERVER: ", comando_inserir)
    except Exception:
        print("Erro ao atualizar no SELOS_SQL_SERVER.", comando_inserir)


def acertar_valor_pago_firebird(
    numero_protocolo: int,
    valor_transacao: Decimal,
    db: FbConnection,
):
    """DAR BAIXA NO PROTOCOLO FIREBIRD."""
    logger.debug(
        f"Iniciando a função acertar_valor_pago_firebird com numero_protocolo: {numero_protocolo}, valor_transacao: {valor_transacao}",
    )

    command = """
        UPDATE PEDIDOS
        SET VALORACERTO = VALORACERTO + :valor_transacao
        WHERE CHAVE_PEDIDOS = (SELECT MAX(CHAVE_PEDIDOS) FROM PROTOCOLOS WHERE NROORDEM = :nroordem)
    """

    command = command.replace(":nroordem", str(numero_protocolo))
    command = command.replace(":valor_transacao", str(valor_transacao))

    logger.debug(f"Comando SQL gerado: {command}")

    try:
        db.execute_command(command)
        db.commit()
        logger.info(
            f"Comando executado com sucesso para numero_protocolo: {numero_protocolo}",
        )
    except Exception:
        logger.exception(
            f"ERRO ao atualizar valor pago do PROTOCOLO. command: {command}",
        )
        raise


def descontar_valor_novo_deposito_firebird(
    pedido_id,
    valor_transacao,
    valor_complementar,
):
    """DAR BAIXA NO PROTOCOLO FIREBIRD."""
    print(pedido_id, valor_transacao)

    command = """
        UPDATE PEDIDOS
        SET   VALORACERTO = VALORACERTO - :valor_transacao - :valor_complementar
        WHERE CHAVE_PEDIDOS = :pedido_id
    """

    command = str(command).replace(":pedido_id", str(pedido_id))
    command = str(command).replace(":valor_transacao", str(valor_transacao))
    command = str(command).replace(":valor_complementar", str(valor_complementar))

    try:
        with FbConnection() as db:
            db.begin_transaction()
            db.execute_command(command)
            db.commit()
    except Exception:
        logging.exception(
            f"ERRO ao atualizar valor pago do PROTOCOLO. command: {command}",
        )
        raise


def get_pedido_certidao_por_numero_fb(numero_pedido_certidao: str, db: FbConnection):
    logger.info(f"Obtendo pedido de certidão pelo numero: {numero_pedido_certidao}")

    # query SQL a executar
    query = f"""  SELECT *
                  FROM PED_CERTIDOES
                  WHERE CHAVE_PED_CERTIDOES = {numero_pedido_certidao!s}
    """

    resultado = db.execute_query(query)

    if not resultado:
        msg = "Pedido certidão não encontrado."
        logger.error(msg)
        return None

    logger.debug(f"O pedido certidão obtido é: {resultado[0]['CHAVE_PED_CERTIDOES']}")

    return resultado[0]


def get_pedido_item(pedido_item_id: int, db: FbConnection):
    query = """
        SELECT *
        FROM PEDIDOS_ITENS
        WHERE CHAVE_PEDIDOS_ITENS = ?
    """
    try:
        result = db.execute_query(query, (pedido_item_id,))
        return result[0] if result else None
    except Exception as e:
        logging.exception(f"Erro ao obter pedido item no Firebird: {e}")
        raise


def get_selos_pedido_certidao(pedido_certidao_id: int, db: FbConnection):
    query = """
        SELECT *
        FROM SELO_DIGITAL_MG
        WHERE CHAVE_PED_CERTIDOES = ?
    """
    try:
        return db.execute_query(query, (pedido_certidao_id,))
    except Exception as e:
        logging.exception(f"Erro ao obter selos do pedido de certidão no Firebird: {e}")
        raise


def baixar_valor_acerto_final_no_fb(pedido_id: int, db: FbConnection) -> None:
    if not pedido_id:
        return 1

    str_id = str(pedido_id)

    try:
        comando = f"""
            UPDATE PEDIDOS
            SET VALORACERTO = VALORFINAL
            WHERE CHAVE_PEDIDOS = {str_id}
        """
        logger.info(f"Atualizando valor do pedido. ID: {str_id}")

        db.execute_command(comando)

    except Exception:
        logging.exception(f"ERRO ao ATUALIZAR. ID: '{str_id}'")
        raise


def corrigir_tributacao_protocolos(protocolos: list):
    logger.info(f"Corrigindo tributação dos protocolos: {protocolos}")
    logger.debug(f"Quantidade de protocolos: {len(protocolos)}")

    for protocolo in protocolos:
        with FbConnection() as db:
            logger.debug(f"Corrigindo protocolo: {protocolo}")
            # passar a tributacao e custas para 75%
            comando75_1 = """
                    UPDATE PEDIDOS_ITENS PI
                    SET PI.CUSTAS = 14,
                        PI.codigo_tipo_tributacao = 14
                    WHERE PI.chave_pedidos =
                    (
                        SELECT PR.chave_pedidos
                        FROM PROTOCOLOS PR
                        WHERE PR.nroordem = ?
                    )
                    """

            db.execute_command(comando75_1, (protocolo,))

            comando75_2 = """
                    UPDATE PEDIDOS_ITENS PI
                    SET  PI.tabelacalculo = 412,
                        PI.CUSTAS = 14,
                        PI.codigo_tipo_tributacao = 14,
                        PI.valortotalitem = 15.12,
                        PI.valoremolumento = 11.43,
                        PI.valorreceitaadicional1 = 2.44,
                        PI.valor_fundoestado = 0.68,
                        PI.TAXA1 = 0.57
                    WHERE PI.chave_pedidos =
                    (
                        SELECT PR.chave_pedidos
                        FROM PROTOCOLOS PR
                        WHERE PR.nroordem = ?
                    )
                        AND PI.codigo_tabela = '4701-9'
                    """

            db.execute_command(comando75_2, (protocolo,))

            comando75_3 = """
                    UPDATE PEDIDOS_ITENS PI
                    SET  PI.tabelacalculo = 412,
                        PI.CUSTAS = 14,
                        PI.codigo_tipo_tributacao = 14,
                        PI.valortotalitem = 15.12,
                        PI.valoremolumento = 11.42,
                        PI.valorreceitaadicional1 = 2.45,
                        PI.valor_fundoestado = 0.57,
                        PI.TAXA1 = 1.14
                    WHERE PI.chave_pedidos =
                    (
                    SELECT PR.chave_pedidos
                    FROM PROTOCOLOS PR
                    WHERE PR.nroordem = ?
                    )
                    AND PI.codigo_tabela = '4139-2'
                    """

            db.execute_command(comando75_3, (protocolo,))

            comando75_4 = """
                    UPDATE PEDIDOS_ITENS PI
                    SET  PI.tabelacalculo = 413,
                        PI.CUSTAS = 14,
                        PI.codigo_tipo_tributacao = 14,
                        PI.valortotalitem = 3.17,
                        PI.valoremolumento = 2.2,
                        PI.valorreceitaadicional1 = 0.73,
                        PI.valor_fundoestado = 0.13,
                        PI.TAXA1 = 0.11
                    WHERE PI.chave_pedidos =
                    (
                    SELECT PR.chave_pedidos
                    FROM PROTOCOLOS PR
                    WHERE PR.nroordem = ?
                    )
                    AND PI.codigo_tabela = '8101-8'

                    """

            db.execute_command(comando75_4, (protocolo,))

            comando75_5 = """
                    UPDATE PEDIDOS_ITENS PI
                    SET  PI.tabelacalculo = 327,
                        PI.CUSTAS = 14,
                        PI.codigo_tipo_tributacao = 14,
                        PI.valortotalitem = 9.69,
                        PI.valoremolumento = 6.53,
                        PI.valorreceitaadicional1 = 2.44,
                        PI.valor_fundoestado = 0.39,
                        PI.TAXA1 = 0.33
                    WHERE PI.chave_pedidos =
                    (
                    SELECT PR.chave_pedidos
                    FROM PROTOCOLOS PR
                    WHERE PR.nroordem = ?
                    )
                    AND PI.codigo_tabela = '8401-2'


                    """

            db.execute_command(comando75_5, (protocolo,))

            comando75_6 = """
                    UPDATE PEDIDOS_ITENS PI
                    SET  PI.tabelacalculo = 409,
                        PI.CUSTAS = 14,
                        PI.codigo_tipo_tributacao = 14,
                        PI.valortotalitem = 10.29,
                        PI.valoremolumento = 7.14,
                        PI.valorreceitaadicional1 = 2.36,
                        PI.valor_fundoestado = 0.43,
                        PI.TAXA1 = 0.36
                    WHERE PI.chave_pedidos =
                    (
                    SELECT PR.chave_pedidos
                    FROM PROTOCOLOS PR
                    WHERE PR.nroordem = ?
                    )
                    AND PI.codigo_tabela = '4138-4'


                    """

            db.execute_command(comando75_6, (protocolo,))

            ### FIM DOS COMANDOS SQL PARA 75%

            ### INICIO DOS COMANDOS SQL PARA 50%

            comando50_1 = """
                    UPDATE PEDIDOS_ITENS PI
                    SET  PI.CUSTAS = 5,
                        PI.codigo_tipo_tributacao = 5
                    WHERE PI.chave_pedidos =
                    (
                        SELECT PR.chave_pedidos
                        FROM PROTOCOLOS PR
                        WHERE PR.nroordem = ?
                    );
                    """

            db.execute_command(comando50_1, (protocolo,))

            comando50_2 = """
                    UPDATE PEDIDOS_ITENS PI
                    SET  PI.tabelacalculo = 185,
                        PI.CUSTAS = 5,
                        PI.codigo_tipo_tributacao = 5,
                        PI.valortotalitem = 30.25,
                        PI.valoremolumento = 22.85,
                        PI.emolumentoliq = 22.85,
                        PI.valorreceitaadicional1 = 4.89,
                        PI.valor_fundoestado = 1.37,
                        PI.TAXA1 = 1.14
                    WHERE PI.chave_pedidos =
                    (
                        SELECT PR.chave_pedidos
                        FROM PROTOCOLOS PR
                        WHERE PR.nroordem = ?
                    )
                    AND PI.codigo_tabela = '4701-9'
                    ;
                    """

            db.execute_command(comando50_2, (protocolo,))

            comando50_3 = """
                    UPDATE PEDIDOS_ITENS PI
                    SET  PI.tabelacalculo = 123,
                        PI.CUSTAS = 5,
                        PI.codigo_tipo_tributacao = 5,
                        PI.valortotalitem = 2241.82,
                        PI.valoremolumento = 1320.82,
                        PI.emolumentoliq = 1320.82,
                        PI.valorreceitaadicional1 = 775.72,
                        PI.valor_fundoestado = 79.24,
                        PI.TAXA1 = 66.04
                    WHERE PI.chave_pedidos =
                    (
                        SELECT PR.chave_pedidos
                        FROM PROTOCOLOS PR
                        WHERE PR.nroordem = ?
                    )
                    AND PI.codigo_tabela = '4543-5'
                    ;
                    """

            db.execute_command(comando50_3, (protocolo,))

            comando50_4 = """
                UPDATE PEDIDOS_ITENS PI
                SET  PI.tabelacalculo = 123,
                    PI.CUSTAS = 5,
                    PI.codigo_tipo_tributacao = 5,
                    PI.valortotalitem = 1994.65,
                    PI.valoremolumento = 1244.67,
                    PI.emolumentoliq = 1244.67,
                    PI.valorreceitaadicional1 = 613.08,
                    PI.valor_fundoestado = 74.67,
                    PI.TAXA1 = 62.23
                WHERE PI.chave_pedidos =
                (
                    SELECT PR.chave_pedidos
                    FROM PROTOCOLOS PR
                    WHERE PR.nroordem = ?
                )
                AND PI.codigo_tabela = '4542-7'
                ;
                """

            db.execute_command(comando50_4, (protocolo,))

            comando50_5 = """
                    UPDATE PEDIDOS_ITENS PI
                    SET  PI.tabelacalculo = 408,
                        PI.CUSTAS = 5,
                        PI.codigo_tipo_tributacao = 5,
                        PI.valortotalitem = 6.34,
                        PI.valoremolumento = 4.4,
                        PI.valorreceitaadicional1 = 1.46,
                        PI.valor_fundoestado = 0.26,
                        PI.TAXA1 = 0.22
                    WHERE PI.chave_pedidos =
                    (
                    SELECT PR.chave_pedidos
                    FROM PROTOCOLOS PR
                    WHERE PR.nroordem = ?
                    )
                    AND PI.codigo_tabela = '8101-8'
                    ;
                """

            db.execute_command(comando50_5, (protocolo,))

            comando50_6 = """
                    UPDATE PEDIDOS_ITENS PI
                    SET  PI.tabelacalculo = 167,
                        PI.CUSTAS = 5,
                        PI.codigo_tipo_tributacao = 5,
                        PI.valortotalitem = 5.29,
                        PI.valoremolumento = 3.68,
                        PI.valorreceitaadicional1 = 1.21,
                        PI.valor_fundoestado = 0.22,
                        PI.TAXA1 = 0.18
                    WHERE PI.chave_pedidos =
                    (
                    SELECT PR.chave_pedidos
                    FROM PROTOCOLOS PR
                    WHERE PR.nroordem = ?
                    )
                    AND PI.codigo_tabela = '4301-8'
                    ;
                """

            db.execute_command(comando50_6, (protocolo,))

            comando50_7 = """
                UPDATE PEDIDOS_ITENS PI
                SET  PI.tabelacalculo = 383,
                    PI.CUSTAS = 5,
                    PI.codigo_tipo_tributacao = 5,
                    PI.valortotalitem = 19.68,
                    PI.valoremolumento = 13.06,
                    PI.valorreceitaadicional1 = 4.89,
                    PI.valor_fundoestado = 0.78,
                    PI.TAXA1 = 0.65
                WHERE PI.chave_pedidos =
                (
                SELECT PR.chave_pedidos
                FROM PROTOCOLOS PR
                WHERE PR.nroordem = ?
                )
                AND PI.codigo_tabela = '8401-2'
                ;
            """

            db.execute_command(comando50_7, (protocolo,))


def get_protocolo_fb_por_numero_onr(numero_protocolo_onr: int, db: FbConnection):
    query = """
        SELECT *
        FROM PROTOCOLOS
        WHERE NUMEROPEDIDOCRI = ?
    """
    try:
        result = db.execute_query(query, (numero_protocolo_onr,))
        return result[0] if result else None
    except Exception as e:
        logging.exception(f"Erro ao obter protocolo no Firebird: {e}")
        raise
