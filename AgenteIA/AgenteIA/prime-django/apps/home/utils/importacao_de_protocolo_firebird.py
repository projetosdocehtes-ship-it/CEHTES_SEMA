import logging
import re
import subprocess
import threading
from datetime import datetime, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING

import psycopg2
from django.apps import apps
from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.cartorios.models import Cartorio, Usuario
from apps.home.models import models_home as models
from apps.home.services import firebird
from apps.home.tipos import TipoImportacao
from apps.home.utils import importar_livro2, importar_livro3
from core.utils.firebird_utils import FbConnection

if TYPE_CHECKING:
    from apps.home.models import Livro01Andamento, Livro01Protocolo, PedidoItem


logger = logging.getLogger(__name__)


# VERIFICAR SE O COLABORADOR ESTA CADASTRADO NO HOME COLABORADOR - FIREBIRD
def checar_ou_criar_colaborador_fb(colaborador_id, db: FbConnection) -> None:
    query = "SELECT CHAVE_FUNCIONARIOS FROM FUNCIONARIOS WHERE CHAVE_FUNCIONARIOS = ?"

    try:
        result_sql = db.execute_query(query, (colaborador_id,))

        # NAO ENCONTROU COLABORADOR
        if len(result_sql) == 0:
            criar_funcionario_no_fb(colaborador_id, db)

    except Exception as e:
        logger.exception(
            f"Erro ao obter o colaborador: {e}",
        )
        return


# GRAVAR FUNCIONARIO  FIREBIRD
def criar_funcionario_no_fb(funcionario_id_fb, db: FbConnection) -> None:
    comando = """INSERT INTO FUNCIONARIOS(
                CHAVE_FUNCIONARIOS,
                NOME,
                SENHA,
                NOMECOMPLETO,
                CHAVE_PAPEIS
                )
                VALUES (
                    ?,
                    '2E252737152A342735',
                    '8iAOfNRsMMvs3eGov4K9rz4vEdDQDi7XEAAjaJQf/opYjSyOu8eh4cBZnpnQmU4gZqZlxJq83/RkROyOVY217EQK5NMazJKFRL6wg1E0GwUOe1dCbnV/G/Z2JHq5wWDC',
                    '07111229721C1204150809163D7E11E75412090FE01F10EFEFE339',
                    1);
            """

    db.execute_command(comando, (funcionario_id_fb,))


# GERAR AS TABELAS BASICAS PARA IMPORTACAO
def gerar_tabelas_base_postgresql() -> None:
    try:
        list_estado_civil = firebird.importar_estado_civil_regime_do_fb()
        gravar_estado_civil_postegresql(list_estado_civil)
    except Exception:
        ##logger.exception("ERRO")
        logger.exception("ERRO no list_estado_civil")

    # GERAR TABELAS BASES DO POSTGRESS
    try:
        # Verificar se vai solicitar o numero do LIVRO 01
        list_titulos = get_titulos()

        print("Gravar Titulos")
        gravar_titulos_postegresql(list_titulos)
        print("inserido titulos  ")
    except Exception:
        ##logger.exception("ERRO")
        logger.exception("ERRO no list_titulos")

    try:
        # Verificar se vai solicitar o numero do LIVRO 01
        list_atos = gerar_atos()
        gravar_atos_postegresql(list_atos)
        print("inserido atos  ")
    except Exception:
        # logger.exception("ERRO")
        logger.exception("ERRO no list_atos")

    try:
        # Verificar se vai solicitar o numero do LIVRO 01
        vigencia_dos_emolumentos = firebird.get_vigencia_dos_emolumentos_fb()
        criar_vigencia_dos_emolumentos(vigencia_dos_emolumentos)
        print("EMOLUMENTOS: nserido emolumento anos ")
    except Exception:
        # logger.exception("ERRO")
        logger.exception("ERRO na vigencia_dos_emolumentos")

    try:
        # Verificar se vai solicitar o numero do LIVRO 01
        list_emolumentos = firebird.get_emolumentos_fb()
        gravar_emolumentos_postegresql(list_emolumentos)
        print("inserido emolumento  ")
    except Exception:
        # logger.exception("ERRO")
        logger.exception("ERRO no list_emolumentos")

    try:
        # Verificar se vai solicitar o numero do LIVRO 01
        list_emolumentos_itens = get_emolumentos_itens_do_fb()
        gravar_emolumentos_itens_postegresql(list_emolumentos_itens)
    except Exception:
        # logger.exception("ERRO")
        logger.exception("ERRO no list_emolumentos_itens")

    try:
        # Verificar se vai solicitar o numero do LIVRO 01
        funcionarios = get_funcionarios_do_fb()
        models.Colaborador.criar_colaboradores_obtidos_do_fb(funcionarios)
        print("inserido funcionarios  ")
    except Exception:
        logger.exception("ERRO no list_funcionarios ")

    try:
        # Verificar se vai solicitar o numero do LIVRO 01
        list_tipos_andamentos = get_tipo_andamento()
        gravar_tipos_andamentos_postegresql(list_tipos_andamentos)
        print("inserido tipo_andamento  ")
    except Exception:
        # logger.exception("ERRO")
        logger.exception("ERRO no tipo_andamento")


def get_emolumentos_itens_do_fb():
    print("EMOLUMENTO ITENS: Obtendo os dados")
    # conn = firebird.get_conexao_firebird()
    db = FbConnection()
    query = """
        SELECT CHAVE_EMOLUMENTOS_ITENS, CHAVE_EMOLUMENTOS, VL_INICIO, VL_FIM,
               ADIC_EMOLUMENTO, ADIC_VALOR, DESCRICAO, CHAVE_VIGOR, TAXA1,
               TAXA2, TAXA3, TAXA4, TAXA5, TAXA6, CODIGO_TABELA, TEXTO, TIPOATO,
               FUNDO, TABELIAO, ADIC_TX_JUD, ADIC_TABELIAO, TX_JUD, FUNDESP,
               CHAVE_LIGACAO, EMOLUMENTO_ADICIONAL, FATOR_EMOLUMENTO_ADICIONAL,
               CALC_EMOLUMENTO_ADC_APARTIR, VALOR_MAXIMO_EMOLUMENTO, ATO_CORRELACIONADO,
               ATOCORRELACIONADO, TABELA, TABELA_ITEM, EMOLUMENTO, VALOR,
               ATUALIZADO, PERC_FUNEMP, CHAVE_FUNCIONARIOS, CHAVE_ATOS_SELOS,
               CODIGO_TABELA_GOIAS, EMOLUMENTO_BRUTO, CALCULAR_FARPEN,
               VALOR_MIN_EMOL_TAXA3
        FROM   EMOLUMENTOS_ITENS
    """
    return db.execute_query(query)
    # # Execute the SELECT statement:
    # list_emolumentos_itens = []
    # cur.execute(comando)

    # resultados = cur.fetchall()
    # resultados = firebird_utils.processar_resultados_e_converter_decimal_para_int(resultados)

    # cur.close()

    # for c in resultados:
    #     list_emolumentos_itens.append(c)

    # try:
    #     list_emolumentos_itens[0][0]
    # except Exception:
    #     # logger.exception("ERRO")
    #     list_emolumentos_itens = None

    # return list_emolumentos_itens


def get_titulos(db: FbConnection):
    # conn = firebird.get_conexao_firebird()

    query = """
       SELECT CHAVE_TITULOS,
                TIPOTITULO,
                PRAZO,
                EXIBIR,
                USAR_PERCENTUAL,
                REGISTRAR,
                EXIBIRPROTOCOLO,
                CALCULOPREVISAO,
                TIPODATAPREVISTA
       FROM TITULOS"""

    return db.execute_query(query)
    # list_titulos = list(resultados)
    # try:
    #     list_titulos[0][0]
    #     print(list_titulos[0][0], list_titulos[0][1])
    # except Exception:
    #     logger.exception("ERRO")
    #     list_titulos = None

    # return list_titulos


def get_tipo_andamento(db: FbConnection):
    query = " SELECT CHAVE_SERVICOS_ANDAMENTOS, SERVICO FROM SERVICOS_ANDAMENTOS "

    db = FbConnection() if db is None else db
    resultado = db.execute_query(query)
    return resultado[0] if resultado else None

    # Execute the SELECT statement:


#    list_tipos_andamentos = []
# cur.execute(comando)

# resultados = cur.fetchall()
# resultados = firebird_utils.processar_resultados_e_converter_decimal_para_int(resultados)
# cur.close()
# for c in resultados:
#     list_tipos_andamentos.append(c)

# try:
#     list_tipos_andamentos[0][0]
# except Exception:
#     # logger.exception("ERRO")
#     list_tipos_andamentos = None

# return list_tipos_andamentos


def get_funcionarios_do_fb(db: FbConnection):
    query = """
            SELECT CHAVE_FUNCIONARIOS, NOME
            FROM FUNCIONARIOS
            """

    return db.execute_query(query)


def gerar_atos(db: FbConnection) -> list:
    query = (
        " SELECT CHAVE_ATOS, TIPOATO, CODIGO_NATUREZA_JURIDICA, COM_ONUS,                   "
        "        EXIBIR, TIPO, DOI, EXIBIRPROTOCOLO, USAR_PERCENTUAL, CODIGO_DOI,           "
        "        TIPO_PROCESSO_ERIDF, GRAUDIFICULDADE, TEMPOMEDIO, ORDEM_ATOS_REL_PROT,     "
        "        ORDEM_ATOS_PRATICADOS, NROOBRIGATORIO, CHAVE_ANDAMENTOS,                   "
        "        INDICAR_ATO_LIVROPROTOCOLO,                                                "
        "        SOLICITARVALOR, SOLICITARVALORALIENACAO, NROOBRIGATORIOATO, CHAVE_GRUPOS,  "
        "        TIPO_REQUERIMENTO_CENTRAL, CHAVE_TIPO_TRANSACAO                            "
        " FROM    ATOS                                                                      "
    )

    return db.execute_query(query)


# def Gerar_Caixa( CHAVE_PEDIDOS):
#     # Comando SQL a executar
#     comando = (
#         " SELECT CHAVE CAIXA, CHAVE PEDIDOS, DATAPAGAMENTO, DESCRICAO, TIPOTRANSACAO, TIPODOCUMENTO, "
#         + "        VALOR, CHEQUE, CHAVE PED CERTIDOES, COLABORADOR, NROORDEM EC                 "
#         + " FROM   CAIXA WHERE CHAVE PEDIDOS = "
#         + STR(CHAVE PEDIDOS)
#         + " ORDER BY CHAVE CAIXA ASC "
#     )

#     cur = conn.cursor()

#     # Execute the SELECT statement:
#     list_caixa = []
#     cur.execute(comando)
#     for c in cur.fetchall():
#         list_caixa.append(c)

#     if len(list_caixa) == 0:
#         return list_caixa

#     # Variaveis de Pedidos
#     try:
#         CHAVE_CAIXA = list_caixa[0][0]
#     except Exception as e:
#         #logger.exception("ERRO")
#         print("ERRO Gerar_Caixa")
#         print(comando)

#         list_caixa = None

#     return list_caixa


# def Gerar_Andamentos( CHAVE_PROTOCOLOS, OPCAO="0"):
#     # Comando SQL a executar

#     order = " ORDER BY DATA ASC "
#     if str(OPCAO) == "1":
#         order = " ORDER BY DATA DESC "

#     comando = (
#         " SELECT CHAVE_ANDAMENTOS, CHAVE_PROTOCOLOS, DATA, CHAVE_FUNCIONARIOS, CHAVE_SERVICOS_ANDAMENTOS, "
#         + "        CHAVE_FUNCIONARIOS_DESTINO "
#         + " FROM   ANDAMENTOS WHERE CHAVE_PROTOCOLOS = "
#         + str(CHAVE_PROTOCOLOS)
#         # + " ORDER BY DATA ASC "
#         + order
#     )

#     cur = conn.cursor()

#     # Execute the SELECT statement:
#     list_andamentos = []
#     cur.execute(comando)
#     for c in cur.fetchall():
#         list_andamentos.append(c)

#     # Variaveis de Pedidos
#     try:
#         CHAVE_PROTOCOLOS = list_andamentos[0][1]
#         CHAVE_FUNCIONARIOS_DESTINO = list_andamentos[0][5]
#     except Exception as e:
#         #logger.exception("ERRO")
#         print("ERRO Gerar_Andamentos: ", comando)

#         list_andamentos = None

#     return list_andamentos


# Gerar pedidos itens a ser importado
# def Gerar_Selo( CHAVE_PEDIDOS):
#     # Comando SQL a executar
#     comando = (
#         " SELECT CHAVE_SELO_DIGITAL_MG, CODIGO_SEQUENCIAL_UNICO, CODIGO_DE_SEGURANCA ,                     "
#         + "        DATA_IMPORTACAO , DATA_UTILIZACAO , SELO_PARA_CONSULTA  , UTILIZADO   ,                   "
#         + "        CANCELADO   , CHAVE_PEDIDOS   , CHAVE_PEDIDOS_ITENS , CHAVE_PED_CERTIDOES ,               "
#         + "        CHAVE_PED_CERTIDOES_TIPOS   , CHAVE_PED_CERTIDOES_TIPOS_CANC  ,                           "
#         + "        CHAVE_PED_CERTIDOES_CANC, CHAVE_PEDIDOS_ITENS_CANC, CHAVE_PEDIDOS_CANC  ,                 "
#         + "        DATA_CANCELAMENTO   , CHAVE_FUNCIONARIOS  , DATA_ENVIO  , CHAVE_FUNCIONARIOS_CANC ,       "
#         + "        CHAVE_FUNCIONARIOS_ENVIO, CONFIRMADO  , ENVIADO , SELOSITE, DATASELOSITE,                 "
#         + "        CHAVE_SELOS_EXPORTACAO_WEB  , NUMERO_IMOVEL   , CHAVE_PED_CERTIDOES_IMOVEIS               "
#         + "        FROM SELO_DIGITAL_MG WHERE CHAVE_PEDIDOS = "
#         + str(CHAVE_PEDIDOS)
#         + "        ORDER BY CHAVE_SELO_DIGITAL_MG ASC "
#     )

#     # Execute the SELECT statement:
#     list_selo = []

#     cur = conn.cursor()

#     try:
#         cur.execute(comando)
#         # print("sucesso abrir tabela selo")

#     except Exception as e:
#         #logger.exception("ERRO")
#         print("ERRO abrir tabela selo")

#     for c in cur.fetchall():
#         # print("Selecionando selo: ", c)
#         list_selo.append(c)
#         # print(comando)

#     if len(list_selo) == 0:
#         return list_selo

#     # Variaveis de Pedidos
#     try:
#         CODIGO_SEQUENCIAL_UNICO = list_selo[0][1]
#         CODIGO_DE_SEGURANCA = list_selo[0][2]
#         SELO_PARA_CONSULTA = list_selo[0][5]
#         CHAVE_PEDIDOS_ITENS = list_selo[0][10]

#         print("O Pedido Item e ", str(CHAVE_PEDIDOS_ITENS))
#         print("Selo Gravado: ", str(CODIGO_SEQUENCIAL_UNICO))
#     except Exception as e:
#         #logger.exception("ERRO")
#         print("ERRO Gerar_Selo: ", comando)

#         list_selo = None

#     return list_selo


# INICIAR PROCESSOS DE GRAVAR
def gravar_emolumentos_postegresql(list_emolumentos) -> None:
    for item in list_emolumentos:
        pk = str(item[0])
        nome = str(item[1])
        str(item[2])
        str(item[3])
        desconto = str(item[4])
        utilizado = str(item[5])
        str(item[6])
        str(item[7])
        str(item[8])
        descricao = str(item[9])
        str(item[10])
        str(item[11])
        inativo = str(item[12])
        gerarselo = str(item[13])
        str(item[14])
        str(item[15])
        str(item[16])
        str(item[17])
        str(item[18])
        codigo_tabela_inicial = str(item[19])
        str(item[20])
        str(item[21])
        str(item[22])
        str(item[23])
        str(item[24])
        str(item[25])
        str(item[26])
        str(item[27])
        str(item[28])
        str(item[29])
        str(item[30])
        str(item[31])
        str(item[32])
        str(item[33])
        str(item[34])
        str(item[35])
        str(item[36])
        str(item[37])
        str(item[38])
        str(item[39])
        str(item[40])
        str(item[41])
        str(item[42])
        str(item[43])
        str(item[44])
        str(item[45])
        str(item[46])
        str(item[47])
        str(item[48])
        str(item[49])
        str(item[50])
        str(item[51])
        str(item[52])
        str(item[53])
        str(item[54])
        str(item[55])
        str(item[56])
        str(item[57])
        str(item[58])
        str(item[59])
        str(item[60])
        str(item[61])
        str(item[62])
        str(item[63])
        str(item[64])
        str(item[65])
        str(item[66])
        str(item[67])
        str(item[68])
        str(item[69])
        str(item[70])
        str(item[71])
        str(item[72])
        str(item[73])
        str(item[74])
        str(item[75])
        str(item[76])
        str(item[77])
        str(item[78])
        str(item[79])
        str(item[80])
        str(item[81])
        str(item[82])
        str(item[83])
        str(item[84])
        str(item[85])
        str(item[86])

        if str(desconto) == "None":
            desconto = 0
        if str(utilizado) == "None":
            utilizado = ""
        if str(descricao) == "None":
            descricao = ""
        if str(inativo) == "None":
            inativo = ""
        if str(gerarselo) == "None":
            gerarselo = ""
        if str(codigo_tabela_inicial) == "None":
            codigo_tabela_inicial = "0"

        if not models.Emolumentos.objects.filter(id=pk).exists():
            emolumento = models.Emolumentos.objects.create(
                id=pk,
                nome=nome,
                desconto=desconto,
                utilizado=utilizado,
                descricao=descricao,
                inativo=inativo,
                gerarselo=gerarselo,
                codigo_tabela_inicial=codigo_tabela_inicial,
            )
            logger.info(f"EMOLUMENTOS: Emolumento gravado : {emolumento.nome}")


def gravar_emolumentos_itens_postegresql(list_emolumentos_itens) -> None:
    objeto_emolumentos_itens = []
    for item in list_emolumentos_itens:
        pk = str(item[0])
        emolumento_id = str(item[1])
        faixa_inicio = str(item[2])
        faixa_fim = str(item[3])
        valor_adicionado = str(item[4])
        valor_adicionado_2 = str(item[5])
        descricao = str(item[6])
        vigencia_id = str(item[7])
        percentual_issqn = str(item[8])
        str(item[9])
        str(item[10])
        str(item[11])
        str(item[12])
        str(item[13])
        codigo_tabela = str(item[14])
        str(item[15])
        str(item[16])
        str(item[17])
        str(item[18])
        str(item[19])
        str(item[20])
        str(item[21])
        str(item[22])
        str(item[23])
        str(item[24])
        str(item[25])
        str(item[26])
        str(item[27])
        str(item[28])
        str(item[29])
        str(item[30])
        str(item[31])
        emolumento = str(item[32])
        valor = str(item[33])
        str(item[34])
        str(item[35])
        str(item[36])
        str(item[37])
        str(item[38])
        str(item[39])
        str(item[40])
        str(item[41])

        faixa_inicio = faixa_inicio if faixa_inicio else 0
        faixa_fim = faixa_fim if faixa_fim else 0
        vigencia_id = vigencia_id if vigencia_id else 0
        descricao = descricao if descricao else ""

        faixa_fim = round(Decimal(faixa_fim), 2)
        if faixa_fim > 9999999990.00:
            faixa_fim = 9999999999.00

        valor_adicionado = valor_adicionado if valor_adicionado else 0
        valor_adicionado_2 = valor_adicionado_2 if valor_adicionado_2 else 0
        percentual_issqn = percentual_issqn if percentual_issqn else 0
        emolumento = emolumento if emolumento else 0
        valor = valor if valor else 0
        emolumento = str(round(Decimal(emolumento), 2))
        valor = str(round(Decimal(valor), 2))

        try:
            # curAtual = conPostGresql.cursor()
            # curAtual.execute(
            #     sql,
            #     (
            #         id,
            #         emolumento_id,
            #         vigencia_id,
            #         descricao,
            #         faixa_inicio,
            #         faixa_fim,
            #         valor_adicionado,
            #         valor_adicionado_2,
            #         issqn,
            #         codigo_tabela,
            #         emolumento,
            #         valor,
            #     ),
            # )
            # conPostGresql.commit()
            if models.EmolumentoValor.objects.filter(id=pk).exists():
                print("EMOLUMENTOS_ITENS: Emolumento já existe: ", pk)
                continue
            objeto_emolumentos_itens.append(
                models.EmolumentoValor(
                    id=pk,
                    emolumento_id=emolumento_id,
                    vigencia_id=vigencia_id,
                    descricao=descricao,
                    faixa_inicio=faixa_inicio,
                    faixa_fim=faixa_fim,
                    valor_adicionado=valor_adicionado,
                    valor_adicionado_2=valor_adicionado_2,
                    percentual_issqn=percentual_issqn,
                    codigo_tabela=codigo_tabela,
                    emolumento=emolumento,
                    valor=valor,
                ),
            )

        except (Exception, psycopg2.DatabaseError):
            pass
            # logger.error(f"ERRO ao gravar emolumentos_itens: {error}", exc_info=True)

            # # error_code = error.pgcode
            # if str(error.pgcode) == "23505":
            #     # "23505" está associado a violações de restrições de chave única.
            #     pass
            # else:
            #     text = conPostGresql.query.decode("utf-8")
            #     logger.info(f"Query executada: {text}")
            #     print("ERRO deletado. ", sql)
            #     print(error)
            #     print(error.pgcode)

            # conPostGresql.rollback()

    models.EmolumentoValor.objects.bulk_create(
        objeto_emolumentos_itens,
        ignore_conflicts=True,
    )
    logger.info(f"EMOLUMENTOS_ITENS: {len(objeto_emolumentos_itens)} inseridos!")


def criar_vigencia_dos_emolumentos(vigencia_dos_emolumentos) -> None:
    for vigencia in vigencia_dos_emolumentos:
        pk = str(vigencia[0])
        # data_inicial = str("'" + formatar_data(str(item[1])) + "'")
        # data_final = str("'" + formatar_data(str(item[2])) + "'")
        data_inicial = vigencia[1]
        data_final = vigencia[2]
        descricao_periodo = str(vigencia[3])

        try:
            # curAtual = conPostGresql.cursor()
            # curAtual.execute(sql, (id, data_inicial, data_final, descricao_periodo))
            # conPostGresql.commit()

            if not models.EmolumentoAno.objects.filter(id=pk).exists():
                print("EMOLUMENTOS: Inserido EmolumentoAnos: ", pk)
                models.EmolumentoAno.objects.create(
                    id=pk,
                    data_inicial=data_inicial,
                    data_final=data_final,
                    descricao_periodo=descricao_periodo,
                )

            # print("inserido EmolumentoAnos : ", id)
        except (Exception, psycopg2.DatabaseError):
            pass
            # logger.error(f"ERRO ao gravar EmolumentoAnos: {error}", exc_info=True)

            # # error_code = error.pgcode
            # if str(error.pgcode) == "23505":
            #     # "23505" está associado a violações de restrições de chave única.
            #     pass
            # else:
            #     print(error)
            #     print(error.pgcode)

            # conPostGresql.rollback()


# GRAVAR IMOVEL VINCULADO
def gravar_estado_civil_postegresql(list_estado_civil) -> None:
    if not models.EstadoCivil.objects.filter(id=0).exists():
        models.EstadoCivil.objects.create(id=0, descricao_estado_civil="")

    for estado_civil in list_estado_civil:
        pk = str(estado_civil[0])
        descricao = str(estado_civil[1])

        if not models.EstadoCivil.objects.filter(id=pk).exists():
            print("ESTADO_CIVIL: Inserido estado_civil : ", pk)
            models.EstadoCivil.objects.create(id=pk, descricao_estado_civil=descricao)
        # curestado_civil = conPostGresql.cursor()
        # curestado_civil.execute(sql, (id, descricao))
        # conPostGresql.commit()


def gravar_titulos_postegresql(list_titulos) -> None:
    for item in list_titulos:
        pk = str(item[0])
        tipo_titulo = str(item[1])
        prazo = str(item[2])
        exibir = str(item[3])

        if str(prazo) == "None":
            prazo = 0
        if str(exibir) == "None":
            exibir = ""

        try:
            if not models.Titulo.objects.filter(id=pk).exists():
                models.Titulo.objects.create(
                    id=pk,
                    tipo_titulo=tipo_titulo,
                    prazo=prazo,
                    exibir=exibir,
                    prazo_reentrada=0,
                    prazo_validade=0,
                    prazo_nota_devolucao=0,
                )

            # curAtual = conPostGresql.cursor()
            # curAtual.execute(sql, (id, tipo_titulo, prazo, exibir))
            # conPostGresql.commit()

        except (Exception, psycopg2.DatabaseError):
            pass
            #
            # logger.error(f"ERRO ao gravar titulos: {error}", exc_info=True)

            # # error_code = error.pgcode
            # if str(error.pgcode) == "23505":
            #     # "23505" está associado a violações de restrições de chave única.
            #     pass
            # else:
            #     print(error)
            #     print(error.pgcode)

            # conPostGresql.rollback()


def gravar_tipos_andamentos_postegresql(list_tipos_andamentos) -> None:
    for servico in list_tipos_andamentos:
        if not models.TipoAndamento.objects.filter(pk=servico[0]).exists():
            models.TipoAndamento.objects.create(
                tipo_andamento=servico[0],
                servico=servico[1],
                atualizar_status_protocolo="N",
            )


def criar_funcionarios_obtidos_do_fb(funcionarios) -> None:
    for funcionario in funcionarios:
        funcionario_id = funcionario["CHAVE_FUNCIONARIOS"]
        funcionario_nome = models.Colaborador.get_nome_mapeado(funcionario["NOME"])

        try:
            if not models.Colaborador.objects.filter(pk=funcionario_id).exists():
                models.Colaborador.objects.create(
                    pk=funcionario_id,
                    nome=funcionario_nome,
                )

        except Exception as e:
            logger.exception(
                f"ERRO ao gravar funcionario: {funcionario_id}. Detalhes: {e!s}",
            )
            raise
            # logger.error(f"ERRO ao gravar colaborador: {e}", exc_info=True)


def gravar_atos_postegresql(list_atos) -> None:
    for item in list_atos:
        pk = str(item[0])
        tipo_ato = str(item[1])

        try:
            if not models.AtoPratica.objects.filter(id=pk).exists():
                logger.info(f"ATO: Tentando criar ato : {pk}")
                models.AtoPratica.objects.create(
                    id=pk,
                    tipo_ato=tipo_ato,
                    dias_uteis_reentrada=0,
                )
                logger.info(f"ATO: Inserido ato  : {pk}")
            # curAtual = conPostGresql.cursor()
            # curAtual.execute(sql, (id, tipo_ato))
            # conPostGresql.commit()
        except (Exception, psycopg2.DatabaseError) as error:
            logger.exception(f"ERRO ao gravar atos: {error}")

            # logger.error(f"ERRO ao gravar atos: {error}", exc_info=True)

            # error_code = error.pgcode
            # if str(error.pgcode) == "23505":
            #     # "23505" está associado a violações de restrições de chave única.
            #     pass
            # else:
            #     print(error)
            #     print(error.pgcode)

            # conPostGresql.rollback()


# # VERIFICAR QUAIS EVENTO DA AGENDA DEVE SER CANCELADOS
# def finalizar_evento_importado(status_id, numero_ordem_id, exibir_agenda_protocolo="S"):
#     # protocolo_id = get_protocolo_pelo_id(protocolo_id)

#     # FINALIZAR EVENTO DO PROTOCOLO - EXIGENCIA
#     if str(status_id) == "1":
#         # finalizar_evento(
#         #     numero_ordem_id, "P", "Q", exibir_agenda_protocolo
#         # )  # return str("Qualificar ")
#         # finalizar_evento(
#         #     numero_ordem_id, "P", "N", exibir_agenda_protocolo
#         # )  # return str("Exigência ")
#         # finalizar_evento(
#         #     numero_ordem_id, "P", "Z", exibir_agenda_protocolo
#         # )  # return str("Prazo Registro ")
#         pass

#     # FINALIZAR EVENTO DO PROTOCOLO - CANCELADO ou REGISTRADO
#     elif str(status_id) == "2" or str(status_id) == "3":
#         # print("Finalizar Evento REGISTRADO")
#         # finalizar_evento(
#         #     numero_ordem_id, "P", "P", exibir_agenda_protocolo
#         # )  # return str("Protocolo ")
#         # finalizar_evento(
#         #     numero_ordem_id, "P", "Q", exibir_agenda_protocolo
#         # )  # return str("Qualificar ")
#         # finalizar_evento(
#         #     numero_ordem_id, "P", "N", exibir_agenda_protocolo
#         # )  # return str("Exigência ")
#         # finalizar_evento(
#         #     numero_ordem_id, "P", "R", exibir_agenda_protocolo
#         # )  # return str("Previsto ")
#         # finalizar_evento(
#         #     numero_ordem_id, "P", "V", exibir_agenda_protocolo
#         # )  # return str("Validade ")
#         # finalizar_evento(
#         #     numero_ordem_id, "P", "D", exibir_agenda_protocolo
#         # )  # return str("Registrado ")
#         # finalizar_evento(
#         #     numero_ordem_id, "P", "C", exibir_agenda_protocolo
#         # )  # return str("Cancelado ")
#         # finalizar_evento(
#         #     numero_ordem_id, "P", "E", exibir_agenda_protocolo
#         # )  # return str("Verificar ")
#         # finalizar_evento(
#         #     numero_ordem_id, "P", "Z", exibir_agenda_protocolo
#         # )  # return str("Prazo Registro ")
#         pass

#     # FINALIZAR EVENTO DO PROTOCOLO - EM REGISTRO
#     elif str(status_id) == "5":
#         # finalizar_evento(
#         #     numero_ordem_id, "P", "Q", exibir_agenda_protocolo
#         # )  # return str("Qualificar ")
#         # finalizar_evento(
#         #     numero_ordem_id, "P", "N", exibir_agenda_protocolo
#         # )  # return str("Exigência ")
#         pass

#     # FINALIZAR EVENTO DO PROTOCOLO - PRONTO PARA REGISTRAR
#     elif str(status_id) == "6":
#         # finalizar_evento(
#         #     numero_ordem_id, "P", "E", exibir_agenda_protocolo
#         # )  # return str("Verificar ")
#         # finalizar_evento(
#         #     numero_ordem_id, "P", "N", exibir_agenda_protocolo
#         # )  # return str("Exigência ")
#         # # print("FINALIZAR EVENTOS PRONTO PARA REGISTRO")
#         # # finalizar_evento(protocolo_id, "P", "Q")
#         # # finalizar_evento(protocolo_id, "P", "N")
#         pass

#     # FINALIZAR EVENTO DO PROTOCOLO - DISTRIBUICAO
#     elif str(status_id) == "7":
#         # finalizar_evento(
#         #     numero_ordem_id, "P", "P", exibir_agenda_protocolo
#         # )  # return str("Protocolo ")
#         # finalizar_evento(
#         #     numero_ordem_id, "P", "I", exibir_agenda_protocolo
#         # )  # return str("Distribuido ")
#         pass


# # ATUALIZANDO OS DADOS NO PROTOCOLO DO COLABORADOR ATUAL
def atualizar_status_atual_protocolo(protocolo, numero_id, status_id) -> None:
    try:
        # ATUALIZAR O PROTOCOLO
        # protocolo = models.Livro01Protocolo.objects.get(pk=protocolo_id)
        protocolo.status_id = status_id
        protocolo.save()

        print("Atualizado Colaborador Atual.")

        # # FINALIZAR EVENTO DO PROTOCOLO
        # if str(status_id) == "3":
        #     finalizar_evento(protocolo_id, "P", "P")

    except Exception:
        logger.exception("ERRO")
        raise


# # ATUALIZANDO OS DADOS NO PROTOCOLO DO COLABORADOR ATUAL
def atualizar_data_finalizado_atual_protocolo(
    protocolo_id,
    numero_id,
    data,
    status_id,
) -> None:
    print("PROTOCOLO: Atualizando a Data de Finalizado.")
    try:
        # ATUALIZAR O PROTOCOLO
        protocolo = models.Livro01Protocolo.objects.get(pk=protocolo_id)
        protocolo.data_finalizado = data
        protocolo.status_id = status_id
        protocolo.save()

        print("PROTOCOLO: Data de Finalizado atualizado .")

    except Exception:
        logger.exception("ERRO")
        raise


# # ATUALIZANDO OS DADOS NO PROTOCOLO DO COLABORADOR ATUAL
def atualizar_colaborador_atual_protocolo(
    protocolo_id,
    colaborador_id,
    tipo_andamento_id,
    data_andamento,
) -> None:
    colaborador_atual_id = str(colaborador_id)
    protocolo_atual_id = str(protocolo_id)

    print("colaborador_atual_id: ", colaborador_atual_id)
    print("protocolo_atual_id: ", protocolo_atual_id)

    try:
        # ATUALIZAR O PROTOCOLO
        protocolo = models.Livro01Protocolo.objects.get(pk=protocolo_atual_id)
        protocolo.fases_protocolo_colaborador_atual_id = colaborador_atual_id
        protocolo.fases_protocolo_colaborador_atual_data = data_andamento

        # ATUALIZAR A DATA DE DISTRIBUICAO
        if protocolo.data_distribuicao is None:
            protocolo.data_distribuicao = data_andamento

        protocolo.save()

        print("Atualizado Data Finalização.")
    except Exception:
        logger.exception("Erro")


# Atualizar ultimo status da TABELA AGENDA
def encerrar_evento_pela_data_do_andamento(andamento_fb) -> None:
    protocolo_id = andamento_fb["CHAVE_PROTOCOLOS"]
    tipo_andamento_id = andamento_fb["CHAVE_SERVICOS_ANDAMENTOS"]
    data = andamento_fb["DATA"]

    # FILTRAR OS EVENTOS DO SERVICOS ANDAMENTOS
    fase_agenda_itens_andamentos = models.FaseAgendaItemAndamento.objects.filter(
        tipo_andamento_id=tipo_andamento_id,
    )

    protocolo = models.Livro01Protocolo.get_pelo_id(protocolo_id)

    if not protocolo:
        return

    for evento in fase_agenda_itens_andamentos:
        titulo = (
            evento.fase_agenda.nome
        )  # FaseAgenda.objects.filter(self=evento).values_list("nome", flat=True)
        titulo_baixar = f"{titulo} {protocolo.numero_protocolo!s}"
        models.Event.objects.encerrar_evento_pelo_titulo(
            titulo=titulo_baixar,
            data=data,
        )


# Atualizar ultimo status da TABELA PROTOCOLO
# def Atualizar_Status_Protocolo(protocolo_id, tipo_andamento_id, colaborador_id, data):
#     print("PROTOCOLO: Atualizar Status do Protocolo: ", str(tipo_andamento_id))

#     tipo_andamento_id = int(tipo_andamento_id)
#     protocolo = get_protocolo_pelo_id(protocolo_id)
#     # data = str(data.strftime(settings.DATE_FIREBIRD_FORMAT))

#     # Atualizar STATUS DO PROTOCOLO com a data de FINALIZAÇÃO
#     if tipo_andamento_id in get_ids_tipo_registrado():
#         # ATUALIZANDO OS DADOS NO PROTOCOLO DO COLABORADOR ATUAL
#         protocolo.atualizar_data_finalizado_atual(data=data, status_id=3)
#         # atualizar_data_finalizado_atual_protocolo(protocolo_id, numero_protocolo, data, 3)

#     elif tipo_andamento_id in get_ids_de_tipo_distribuicao():
#         print("Atualizar DISTRIBUICAO")

#         titulo = f"{get_descricao_servico_distribuido()} {protocolo.numero_protocolo}"
#         eventos_do_protocolo = get_eventos_do_protocolo(protocolo, titulo)
#         exibir_agenda_protocolo = "S"

#         if eventos_do_protocolo:
#             exibir_agenda_protocolo = "N"

#         views.tarefa_protocolo_distribuido(
#             "",
#             str(colaborador_id),
#             protocolo,
#             data,
#         )
#         finalizar_evento_importado(7, protocolo_id, exibir_agenda_protocolo)

#     elif tipo_andamento_id in get_ids_de_tipo_exigencia():
#         print("Atualizar EXIGENCIA")
#         # ATUALIZANDO OS DADOS NO PROTOCOLO         STATUS 1 = EXIGENCIA
#         protocolo.atualizar_data_finalizado_atual(data=None, status_id=1)

#     elif tipo_andamento_id in get_ids_de_tipo_subjudice():
#         print("Atualizar SUBJUDICE")
#         protocolo.atualizar_status("SubJudice")
#         protocolo.atualizar_data_finalizado_atual(data=None, status_id=4)  # 4 SUBJUDICE

#     elif tipo_andamento_id in get_ids_de_tipo_reentrada():
#         print("Atualizar REENTRADA")
#         protocolo.atualizar_data_reentrada(tipo_andamento_id)
#         protocolo.atualizar_status("Em Andamento")
#         protocolo.atualizar_data_finalizado_atual(data=None, status_id=0)  # 0 - EM ANDAMENTO

#     elif tipo_andamento_id in get_ids_de_tipo_cancelado():
#         print("Atualizar DATA FINALIZACAO")
#         protocolo.atualizar_data_finalizado_atual(data=data, status_id=2)  # 2 - CANCELADOS

#     elif tipo_andamento_id in get_ids_de_tipo_exigencia_positiva():
#         print("Atualizar EXIGENCIA POSITIVA")
#         protocolo.atualizar_data_finalizado_atual(data=data, status_id=1)

#     elif tipo_andamento_id in filtrar_por_tipo_em_registro():
#         print("Atualizar EM REGISTRO")
#         protocolo.atualizar_status("Em Registro")
#         protocolo.atualizar_data_finalizado_atual(data=None, status_id=5)  # 5 = EM REGISTRO

#     elif tipo_andamento_id in get_ids_de_tipo_pronto_registrar():
#         print("Atualizar PRONTO PARA REGISTRAR")
#         # ATUALIZANDO OS DADOS NO PROTOCOLO
#         protocolo.atualizar_data_finalizado_atual(
#             data=None, status_id=6
#         )  # STATUS 6 = PRONTO REGISTRAR

#     servicos_que_devem_ter_status_atualizado = TipoAndamento.objects.filter(
#         atualizar_status_protocolo="S"
#     ).values_list("tipo_andamento", flat=True)

#     if tipo_andamento_id in servicos_que_devem_ter_status_atualizado:
#         print("COLABORADOR_ATUAL: Atualizar status no colaborador: ", str(tipo_andamento_id))
#         # ATUALIZANDO OS DADOS NO PROTOCOLO DO COLABORADOR ATUAL
#         protocolo.atualizar_colaborador_atual(colaborador_id, data)

#     # Encerrando os eventos pela data do andamento na agenda
#     encerrar_evento_pela_data_do_andamento(protocolo_id, tipo_andamento_id, data)


# def criar_andamentos(protocolo, andamentos_fb):
#     objetos_andamentos = []


#         andamento = Livro01Andamento.objects.criar_andamento_obtido_no_firebird(andamento_fb)
#         # if andamento:
#         #     logger.info(f"ANDAMENTOS: Inserido . PK: {andamento.pk}")

#         #     protocolo.objects.atualizar_status(andamento)

#         #     # Atualizar_Status_Protocolo(
#         #     #     andamento_fb["CHAVE_PROTOCOLOS"],
#         #     #     andamento_fb["CHAVE_SERVICOS_ANDAMENTOS"],
#         #     #     andamento_fb["CHAVE_FUNCIONARIOS_DESTINO"] or andamento_fb["CHAVE_FUNCIONARIOS"],
#         #     #     andamento_fb["DATA"],
#         #     # )

#         #     # IMPORTAR O TEXTO DO ANDAMENTO
#         #     # import_rtf_from_firebird(
#         #     #     numerointeiro=andamento_fb["CHAVE_ANDAMENTOS"],
#         #     #     protocolo_id=andamento_fb["CHAVE_PROTOCOLOS"],
#         #     #     # data=andamento_fb["DATA"],
#         #     #     colaborador=andamento_fb["CHAVE_FUNCIONARIOS"],
#         #     #     tipo_andamento_id=andamento_fb["CHAVE_SERVICOS_ANDAMENTOS"],
#         #     #     colaborador_destino=andamento_fb["CHAVE_FUNCIONARIOS_DESTINO"]
#         #     #     or andamento_fb["CHAVE_FUNCIONARIOS"],
#         #     # )
#         #     objetos_andamentos.append(andamento)

#     return objetos_andamentos


def gravar_selo(
    pedido_id,
    pedido_item_id,
    codigo_sequencial_unico,
    selo_id,
    data_utilizacao,
    codigo_de_seguranca,
    selo_de_consulta,
) -> None:
    try:
        with transaction.atomic():
            # Assumindo que data_utilizacao já está no formato correto
            # Se necessário, converta data_utilizacao para o tipo de dado apropriado (datetime.date)
            models.SeloEletronico.objects.create(
                id=selo_id,
                pedido_id=pedido_id,
                pedido_item_id=pedido_item_id,
                codigo_sequencial_unico=codigo_sequencial_unico,
                utilizado_em=data_utilizacao,
                codigo_de_seguranca=codigo_de_seguranca,
                selo_de_consulta=selo_de_consulta,
            )
            # print("Inserido SELO : ", codigo_sequencial_unico)
    except Exception as error:
        # Aqui você pode adicionar um tratamento de erro específico, se necessário
        logger.info(f"ERRO ao criar SELO: {error}")
        # O rollback é implícito com o uso de 'transaction.atomic()' em caso de exceção


def gravar_selos_em_massa(selos) -> None:
    instancias_selos = [
        models.SeloEletronico(
            pedido_id=selo["CHAVE_PEDIDOS"],
            pedido_item_id=selo["CHAVE_PEDIDOS_ITENS"],
            codigo_sequencial_unico=selo["CODIGO_SEQUENCIAL_UNICO"],
            id=selo["CHAVE_SELO_DIGITAL_MG"],
            utilizado_em=selo["DATA_UTILIZACAO"],
            codigo_de_seguranca=selo["CODIGO_DE_SEGURANCA"],
            selo_de_consulta=selo["SELO_PARA_CONSULTA"],
        )
        for selo in selos
    ]

    # Usar transaction.atomic para garantir que todas as instâncias sejam gravadas
    with transaction.atomic():
        models.SeloEletronico.objects.bulk_create(
            instancias_selos,
            ignore_conflicts=True,
        )
        logger.info(f"SELOS: {len(instancias_selos)} selos gravados .")


def gravar_selo_postegresql_nao_usado(
    codigo_sequencial_unico,
    selo_id_digital_mg,
    codigo_de_seguranca,
) -> None:
    try:
        with transaction.atomic():
            novo_selo = models.SeloEletronico.objects.create(
                codigo_sequencial_unico=codigo_sequencial_unico,
                id=selo_id_digital_mg,
                codigo_de_seguranca=codigo_de_seguranca,
            )
            logger.info(f"SELO Inserido . PK: {novo_selo.pk}")
    except Exception:
        logger.exception("ERRO ao criar SELO")


# OBTER NOVO EMOUMENTO DA TRIBUTACAO DIFERENTE DE NORMAL
def get_novo_emolumento_do_fb(emolumento_id, tributacao_id, db: FbConnection):
    comando = "SELECT MAX(CHAVE_VIGOR) FROM EMOLUMENTOS_VIGOR"
    vigencia_id = str(db.execute_query(comando)[0]["MAX"])
    emolumento_id = str(emolumento_id)
    tributacao_id = str(tributacao_id)

    # Comando SQL a executar - OBTER O EMOLUMENTO
    comando = f"""
        SELECT FIRST 1 E.CHAVE_EMOLUMENTOS, E.DESCONTO
        FROM   EMOLUMENTOS AS E, EMOLUMENTOS_ITENS AS EI
        WHERE  E.CHAVE_EMOLUMENTOS = EI.CHAVE_EMOLUMENTOS
        AND    E.DESCONTO = {tributacao_id!s}
        AND    EI.CHAVE_VIGOR = {vigencia_id!s}
        AND    EI.CODIGO_TABELA IN (
            SELECT FIRST 1 I.CODIGO_TABELA
            FROM   EMOLUMENTOS_ITENS AS I
            WHERE  I.CHAVE_EMOLUMENTOS = {emolumento_id!s}
            AND    I.CHAVE_VIGOR = {vigencia_id!s} )
        """

    # Lista com os valores do emolumento
    resultados = db.execute_query(comando)
    emolumento_id = str(resultados[0]["CHAVE_EMOLUMENTOS"])
    tributacao_id = str(resultados[0]["DESCONTO"])

    # Comando SQL a executar - OBTER A TRIBUTACAO
    comando = f""" SELECT CODIGO_TRIB_TJ
                   FROM TIPO_TRIBUTACAO
                   WHERE CHAVE_TIPO_TRIBUTACAO = {tributacao_id!s}
               """
    tributacao_id = str(db.execute_query(comando)[0]["CODIGO_TRIB_TJ"])

    return emolumento_id, tributacao_id


# OBTER O ULTIMO NUMERO DE ATO FIREBIRD NO PROTOCOLO
def get_ultimo_numero_ato_fb(
    numero_registro: str,
    tipo_registro: str,
    numero_ri: str,
    db: FbConnection,
) -> int:
    comando = (
        f"SELECT PI.NUMEROATO FROM PEDIDOS_ITENS PI WHERE PI.NUMERO_IMOVEL = '{numero_registro}' "
        f"AND PI.TIPO_IMOVEL = '{tipo_registro}' "
        f"AND PI.NUMERO_RI = '{numero_ri}' "
        "AND PI.NUMEROATO <> ''"
    )
    db = db or FbConnection()
    resultados = db.execute_query(comando)

    # Filtrar apenas os valores inteiros da lista de resultados e retornar o maior valor
    lista_valores_inteiro = [
        int(re.sub("[^0-9]", "", item[0])) for item in resultados if item[0].isdigit()
    ]
    return max(lista_valores_inteiro) if lista_valores_inteiro else 0


# Atualizar o FIREBIRD
def firebird_atualizar_imovel(
    imovel_id,
    unidade_id,
    coluna_tabela_origem,
    resposta_correta,
    opcao,
) -> None:
    comando = ""

    # IMOVEL
    if opcao == 1:
        # Executar as insercoes e alteracoes
        if str(coluna_tabela_origem).upper() == "MUNICIPIO":
            comando = (
                " UPDATE IMOVEIS SET MUNICIPIO = '"
                + str(resposta_correta)
                + "' WHERE CHAVE_IMOVEIS = "
                + str(imovel_id)
            )
        elif str(coluna_tabela_origem).upper() == "NUMERO_NIRF":
            comando = (
                " UPDATE IMOVEIS SET NUMERO_NIRF = '"
                + str(resposta_correta)
                + "' WHERE CHAVE_IMOVEIS = "
                + str(imovel_id)
            )
        elif str(coluna_tabela_origem).upper() == "NUMERO_CCIRR":
            comando = (
                " UPDATE IMOVEIS SET NUMERO_CCIR = '"
                + str(resposta_correta)
                + "' WHERE CHAVE_IMOVEIS = "
                + str(imovel_id)
            )
        elif str(coluna_tabela_origem).upper() == "NUMERO_CAR":
            comando = (
                " UPDATE IMOVEIS SET CADAMBRURAL_CAR = '"
                + str(resposta_correta)
                + "' WHERE CHAVE_IMOVEIS = "
                + str(imovel_id)
            )
        elif str(coluna_tabela_origem).upper() == "NUMERO_INCRA":
            comando = (
                " UPDATE IMOVEIS SET CERTPOLIGONAL_INCRA = '"
                + str(resposta_correta)
                + "' WHERE CHAVE_IMOVEIS = "
                + str(imovel_id)
            )
        elif str(coluna_tabela_origem).upper() == "AREA_CONSTRUIDA_RESIDENCIAL":
            comando = (
                " UPDATE IMOVEIS SET AREACONSTRUIDA =     '"
                + str(resposta_correta)
                + "'"
                + "                , AREACONSTRUIDA_RES = '"
                + str(resposta_correta)
                + "'"
                + "                , AREACONSTRUIDA_COM = '"
                + str(resposta_correta)
                + "'"
                + " WHERE CHAVE_IMOVEIS = "
                + str(imovel_id)
            )
    # RURAL
    elif opcao == 2:
        # Executar as insercoes e alteracoes
        if str(coluna_tabela_origem).upper() == "NOME_FAZENDA":
            comando = (
                " UPDATE RURAIS_NOMES SET NOME = '"
                + str(resposta_correta)
                + "' WHERE CHAVE_IMOVEIS = "
                + str(imovel_id)
            )
        elif str(coluna_tabela_origem).upper() == "CARACTERISTICA_FAZENDA":
            comando = (
                " UPDATE RURAIS_NOMES SET LOCALIZACAO = '"
                + str(resposta_correta)
                + "' WHERE CHAVE_IMOVEIS = "
                + str(imovel_id)
            )
        elif str(coluna_tabela_origem).upper() == "AREA_FAZENDA":
            comando = (
                " UPDATE RURAIS_NOMES SET AREA = '"
                + str(resposta_correta)
                + "' WHERE CHAVE_IMOVEIS = "
                + str(imovel_id)
            )
        elif str(coluna_tabela_origem).upper() == "RESERVA_LEGAL":
            comando = (
                " UPDATE RURAIS SET RESERVA_FLORESTAL = '"
                + str(resposta_correta)
                + "' WHERE CHAVE_IMOVEIS = "
                + str(imovel_id)
            )
        elif str(coluna_tabela_origem).upper() == "GEOREFENCIADA":
            comando = (
                " UPDATE RURAIS SET GEOREFERENCIAL = '"
                + str(resposta_correta)
                + "' WHERE CHAVE_IMOVEIS = "
                + str(imovel_id)
            )

        elif str(coluna_tabela_origem).upper() == "REMANESCENTE":
            comando = (
                " UPDATE RURAIS SET REMANESCENTE = '"
                + str(resposta_correta)
                + "' WHERE CHAVE_IMOVEIS = "
                + str(imovel_id)
            )
    # URBANO
    elif opcao == 3:
        # Executar as insercoes e alteracoes
        if str(coluna_tabela_origem).upper() == "AREA":
            comando = (
                " UPDATE LOTES SET AREA = '"
                + str(resposta_correta)
                + "' WHERE CHAVE_UNIDADES = "
                + str(unidade_id)
            )
        elif str(coluna_tabela_origem).upper() == "QUADRA":
            comando = (
                " UPDATE LOTES SET QUADRA = '"
                + str(resposta_correta)
                + "' WHERE CHAVE_UNIDADES = "
                + str(unidade_id)
            )
        elif str(coluna_tabela_origem).upper() == "LOTE":
            comando = (
                " UPDATE LOTES SET NUMERO_UNIDADE = '"
                + str(resposta_correta)
                + "' WHERE CHAVE_UNIDADES = "
                + str(unidade_id)
            )
        elif str(coluna_tabela_origem).upper() == "SETOR":
            comando = (
                " UPDATE LOTES SET SETOR = '"
                + str(resposta_correta)
                + "' WHERE CHAVE_UNIDADES = "
                + str(unidade_id)
            )

    if comando != "":
        with FbConnection() as db:
            db.execute_command(comando)


# VERIFICAR POR DATA OS PROTOCOLOS FALTANTES - FIREBIRD
def importar_caixa_faltantes(db: FbConnection) -> list:
    print("Importar caixa faltantes")

    movimentacao_caixa = firebird.get_caixa_modificados_ultimo_dia_util(db)

    # ITENS DO CAIXA
    for caixa in movimentacao_caixa:
        gravar_caixa = False
        data_transacao = str(caixa["DATAPAGAMENTO"])[:10]
        pedido_id = caixa["CHAVE_PEDIDOS"]

        # VERIFICAR A OPERACAO FINANCEIRA
        operacacao_financeira_id = 1
        chave_pagamento = caixa["CHAVE_PAGAMENTO"]

        if chave_pagamento:
            chave_pagamento = int(chave_pagamento)

            try:
                tipo_operacao_financeira = (
                    models.TipoOperacaoFinanceira.objects.filter(
                        tipo_pagamento_id_sistema_antigo=chave_pagamento,
                    )
                    .values_list("id", flat=True)
                    .first()
                )
                operacacao_financeira_id = int(tipo_operacao_financeira)
            except Exception:
                operacacao_financeira_id = 1

        # VERIFICAR A CATEGORIA
        categorida_financeira_id = 1

        if caixa["CHAVE_PEDIDOS"]:
            categorida_financeira_id = 2

        if caixa["CHAVE_PED_CERTIDOES"]:
            categorida_financeira_id = 3

        # VERIFICAR PARA GRAVAR CAIXA PROTOCOLO
        if pedido_id is not None:
            print("Importar do caixa o pedido: ", pedido_id)

            try:
                protocolo = firebird.get_protocolo_fb_por_pedido_id(pedido_id, db)
                numero_protocolo = protocolo["NROORDEM"]
            except:
                numero_protocolo = 0

            print("Caixa do protocolo: ", numero_protocolo)
            # if (
            #     str(numero_protocolo) == "158657"
            #     or str(numero_protocolo) == "158812"
            #     or str(numero_protocolo) == "158815"
            # ):
            #     print("158855")

            # PROTOCOLO NAO EXISTE
            if int(numero_protocolo) > 0:
                if not models.Livro01Protocolo.objects.filter(
                    numero_protocolo=numero_protocolo,
                ).exists():
                    try:
                        protocolo = importar_protocolo_por_numero_fb(
                            numero_protocolo=numero_protocolo,
                            tipo_importacao=TipoImportacao.Parcial,
                            db=db,
                        )
                    except:
                        print(
                            "IMPORTAR PROTOCOLO = Erro IntegrityError at /verificar_protocolos_nao_importado/P  (registro_anterior_id)=(229274) ",
                        )

                    gravar_caixa = False
                else:
                    gravar_caixa = True
        else:
            gravar_caixa = True

        # NAO IMPORTAR PEDIDO DE CERTIDAO
        if caixa["CHAVE_PED_CERTIDOES"]:
            print(" PEDIDO DE CERTIDAO APENAS NO PRIME ")
            # if models.Financeiro.objects.filter(numero_pedido_certidao=caixa["CHAVE_PED_CERTIDOES"]).exists():
            #    print("Caixa ja existe")
            gravar_caixa = False

        # NAO IMPORTAR PROTOCOLO JA IMPORTADO
        if caixa["CHAVE_PEDIDOS"]:
            chave_pedido_fb = caixa["CHAVE_PEDIDOS"]

            protocolo = models.Livro01Protocolo.objects.filter(
                numero_protocolo=numero_protocolo,
            ).first()

            pedido_id_pg = protocolo.pedido_id if protocolo else None

            # SE JA EXISTIR A CHAVE PEDIDO - CHAVE_PEDIDOS_SISTEMA_ANTERIOR - NO DIA ATUAL NAO SINCRNROZAR
            if (
                chave_pedido_fb
                and models.Financeiro.objects.filter(
                    data_transacao__gte=data_transacao,
                    pedido_id=chave_pedido_fb,
                ).exists()
            ):
                gravar_caixa = False

            # SE JA EXISTIR A CHAVE PEDIDO - CHAVE_PEDIDOS_SISTEMA_ATUAL - NO DIA ATUAL NAO SINCRNROZAR
            if (
                pedido_id_pg
                and models.Financeiro.objects.filter(
                    data_transacao__gte=data_transacao,
                    pedido_id=pedido_id_pg,
                ).exists()
            ):
                gravar_caixa = False

        # GRAVAR CAIXA DESPESA
        if gravar_caixa:
            exists_caixa = False
            caixa_id = caixa["CHAVE_CAIXA"]

            # PROCURANDO NO CAIXA O ID - VERIFICAR SE JA NAO FOI IMPORTADO
            if models.Financeiro.objects.filter(pk=caixa_id).exists():
                exists_caixa = True

                # protocolo nao localizado no caixa, sequence pode estar errada
                # if int(caixa["CHAVE_PEDIDOS"]) != int(pedido_id):
                if not models.Financeiro.objects.filter(
                    data_transacao__gte=data_transacao,
                    pedido_id=pedido_id,
                ).exists():
                    caixa_id = db.sequence("CAIXA_SEQ").proximo
                    exists_caixa = False

            if exists_caixa:
                # print(caixa)
                print("Caixa ja existe: ", caixa_id)
                print("PEDIDO_ID: ", caixa["CHAVE_PEDIDOS"])

                # VERIFICAR PARA ATUALIZAR APENAS TIPO DE PAGAMENTO DE PEDIDOS
                if caixa["CHAVE_PEDIDOS"]:
                    # pedido = models.Financeiro.objects.get(pk=caixa["CHAVE_CAIXA"])
                    pedido = models.Financeiro.objects.get(pk=caixa_id)
                    print("Pedido Postgresql: ", pedido)

                    if pedido:
                        try:
                            print(
                                "Operação Financeira: ",
                                str(operacacao_financeira_id),
                            )
                            pedido.tipo_operacao_financeira_id = str(
                                operacacao_financeira_id,
                            )
                            pedido.tipo_categoria_financeira_id = str(
                                categorida_financeira_id,
                            )
                            pedido.save()
                            print("Salvo no postgresql")

                            print(
                                "CHAVE_CAIXA: ",
                                caixa_id,
                                ", TIPO_PAGAMENTO: ",
                                operacacao_financeira_id,
                            )
                        except:
                            print(
                                "ERRO AO GRAVAR CHAVE_CAIXA: ",
                                caixa_id,
                                ", TIPO_PAGAMENTO: ",
                                operacacao_financeira_id,
                            )
            else:
                print("Gravar receita ou despesa: ", caixa["CHAVE_CAIXA"])

                # VERIFICAR SE O PEDIDO E MESMO NO PRIME E NO SISTEMA ANTERIOR
                pedido_id = caixa["CHAVE_PEDIDOS"]

                if pedido_id:
                    protocolo = models.Livro01Protocolo.objects.filter(
                        numero_protocolo=numero_protocolo,
                    ).first()
                    if protocolo:
                        pedido_id = protocolo.pedido_id

                models.Financeiro.criar_financeiro_despesa_receita_pelo_id(
                    pk=caixa_id,
                    pedido_id=pedido_id,
                    pedido_certidao_id=caixa["CHAVE_PED_CERTIDOES"],
                    tipo_transacao_id=1,
                    tipo_categoria_financeira_id=categorida_financeira_id,
                    tipo_operacao_financeira_id=operacacao_financeira_id,
                    colaborador_id=caixa["CHAVE_FUNCIONARIOS"],
                    colaborador_confirmado_id=None,
                    data_transacao=str(data_transacao),
                    data_original_transacao=str(data_transacao),
                    valor_transacao=caixa["VALOR"],
                    dadp="N",
                    imposto_renda="N",
                    descricao=caixa["DESCRICAO"],
                    quantidade_parcelas=1,
                    recorrencia_id=1,
                    user_id=caixa["CHAVE_FUNCIONARIOS"],
                )


# VERIFICAR POR DATA OS PROTOCOLOS FALTANTES - FIREBIRD
def importar_protocolos_faltantes(
    tipo_importacao: TipoImportacao,
    db: FbConnection,
) -> list:
    logger.info("Importando protocolos faltantes")

    # PEGAR OS PROTOCOLOS DOS ULTIMOS DOIS DIAS
    protocolos_modificados = firebird.get_protocolos_modificados_ultimo_dia_util(db)
    logger.debug(
        f"Importando Protocolos dos ultimos dois dias: {protocolos_modificados}",
    )

    # Acessando os valores da coluna 'NROORDEM'
    valores_nroordem = [dado["NROORDEM"] for dado in protocolos_modificados]
    print("Valores de NROORDEM: ", valores_nroordem)
    protocolos_modificados = sorted(valores_nroordem)

    # print("Livro01Protocolo a atualizar:")
    # print(protocolos_dos_ultimos_dois_dias)
    # import time

    # LISTAR E IMPORTAR APENAS OS NAO IMPORTADOS
    for indice, numero_protocolo in enumerate(protocolos_modificados):
        # Imprime várias linhas vazias e depois uma linha com asteriscos
        logger.info("\n\n\n*************************************")
        logger.info(
            f"Verificando Protocolo: {numero_protocolo} - {indice + 1} de {len(protocolos_modificados)}  *********************************",
        )

        # FILTRAR O PROTOCOLO PELO ANDAMENTO DO DIA
        protocolo: Livro01Protocolo = models.Livro01Protocolo.objects.filter(
            numero_protocolo=numero_protocolo,
        ).first()
        importar_protocolo, atualizar_andamento = False, False

        # ENCONTROU PROTOCOLO JA IMPORTADO
        if protocolo:
            print("Importar os andamentos do protocolo: ", numero_protocolo)
            # Verificação da necessidade de atualização - FIREBIRD
            quantidade_andamento_firebird = get_quantidade_andamentos_no_fb(
                protocolo,
                db,
            )["COUNT"]

            # Verificação da necessidade de atualização - POSTGRESQL
            quantidade_andamento_postgresql = protocolo.quantidade_andamentos

            # CASO HAJA DIFERENCA DE ANDAMENTOS
            if int(quantidade_andamento_firebird) != int(
                quantidade_andamento_postgresql,
            ):
                atualizar_andamento = True

            logger.debug(
                f"Quantidade andamentos no firebird: {quantidade_andamento_firebird}",
            )
            logger.debug(
                f"Quantidade andamentos no postgresql: {quantidade_andamento_postgresql}",
            )

            # IMPORTACAO COMPLETA DE TODOS OS ANDAMENTOS DO DIA
            if tipo_importacao == TipoImportacao.Total:
                atualizar_andamento = True

            # protocolo.atualizar_colaborador_atual_pelo_ultimo_andamento()
        else:
            # Necessidade de importação
            logger.debug("Importar todo o protocolo: {numero_protocolo}")
            importar_protocolo = True

        # APENAS ATUALIZAR O ANDAMENTO
        if atualizar_andamento:
            try:
                print("Atualizando andamento do protocolo: ", numero_protocolo)
                # SELECIONAR TODOS OS ANDAMENTOS DO PROTOCOLO A IMPORTAR
                importar_andamentos_protocolos_pelo_id(protocolo, tipo_importacao, db)
            except Exception:
                logger.exception(
                    f"Erro ao atualizar andamento do protocolo: {numero_protocolo}",
                )

        # IMPORTAR TUDO
        if importar_protocolo:
            try:
                print("Importando todo o protocolo: ", numero_protocolo)
                protocolo = importar_protocolo_por_numero_fb(
                    numero_protocolo=numero_protocolo,
                    tipo_importacao=None,
                    db=db,
                )
            except Exception:
                logger.exception(
                    f"Erro ao importar todo o protocolo: {numero_protocolo}",
                )

    # Atualizar horario do sincronismo
    # Cartorio.atualizar_sincronismo()

    return protocolos_modificados


# Inicio do Programa para converter
@transaction.atomic
def importar_protocolo_por_numero_fb(
    numero_protocolo: int,
    tipo_importacao: TipoImportacao,
    db: FbConnection,
) -> tuple["Livro01Protocolo", str]:
    logger.info(f"PROTOCOLO: Importar do fb por numero {numero_protocolo}")
    msg = None
    protocolo = None
    # ATUALIZAR SOMENTE CAIXA - PELA TELA SEPARADA
    cartorio_model = apps.get_model("cartorios", "Cartorio")
    atualizar_somente_caixa = cartorio_model.objects.all().values_list(
        "atualizar_somente_caixa",
        flat=True,
    )[0]
    str(atualizar_somente_caixa) != "S"

    tipo_importacao = tipo_importacao or TipoImportacao.Total

    protocolo: Livro01Protocolo = None

    protocolo_fb = firebird.get_protocolo_fb(numero_protocolo, db) or None

    if not protocolo_fb:
        msg = f"Protocolo {numero_protocolo} não encontrado no Firebird"
        logger.warning(msg)
        raise ValueError(msg)
        return protocolo, msg

    protocolo_id = protocolo_fb["CHAVE_PROTOCOLOS"] or 0
    pedido_id = protocolo_fb["CHAVE_PEDIDOS"] or 0

    pedido_fb = firebird.get_pedido_fb(pedido_id, db) or None

    if not pedido_fb:
        msg = f"Pedido {pedido_id} não encontrado no Firebird"
        logger.warning(msg)
        raise ValueError(msg)
        return protocolo, msg

    models.CheckListRealizado.objects.deletar_por_pedido_id(pedido_id)

    models.PedidoParte.objects.deletar_por_pedido_id(pedido_id)

    # GRAVAR CAIXA
    # if salvar_caixa:
    models.Financeiro.objects.deletar_por_pedido_id(pedido_id)

    models.Livro01Andamento.objects.deletar_por_protocolo(pedido_id)

    models.SeloEletronico.objects.deletar_por_pedido_id(pedido_id)

    models.Livro02Texto.objects.deletar_por_pedido_id(pedido_id)

    models.PedidoItemImovel.objects.deletar_por_pedido_id(pedido_id)

    models.PedidoParteAto.objects.deletar_por_pedido_id(pedido_id)

    # PedidoItem.objects.deletar_por_pedido_id(pedido_id)

    models.ProtocoloEmFase.objects.deletar_por_pedido_id(pedido_id=pedido_id)

    models.Pedido.objects.deletar_por_pedido_id(pedido_id=pedido_id)

    # ERRO AO GRAVAR
    # funcionarios_fb = get_funcionarios_do_fb()

    # Colaborador.processar_colaboradores(funcionarios_fb)

    # INICIO GRAVANDO
    pedido: models.Pedido = models.Pedido.objects.criar_do_fb(pedido_fb=pedido_fb)

    if not pedido:
        msg = f"Pedido {pedido_id} não foi criado"
        logger.warning(msg)
        raise ValueError(msg)
        return protocolo, msg

    # models.PedidoParte.objects.criar_do_fb(pedido, pedido_fb)
    pedido.criar_partes_do_fb(pedido_fb)

    models.Livro01Protocolo.objects.deletar_por_pedido_id(pedido_id)

    protocolo = models.Livro01Protocolo.criar_ou_atualizar_protocolo_obtido_do_fb(
        protocolo_fb,
    )

    if not protocolo:
        msg = f"Protocolo {numero_protocolo} não foi criado"
        logger.warning(msg)
        raise ValueError(msg)
        return None, msg

    pedido_itens_fb = firebird.get_pedido_itens_fb(
        pedido_id=pedido.pk,
        pedido_id_item=None,
        db=db,
    )

    if not pedido_itens_fb:
        msg = f"Pedido {pedido_id} não possui itens"
        logger.warning(msg)
        raise ValueError(msg)
        return protocolo, msg

    models.PedidoItem.objects.deletar_por_pedido_id(pedido_id)

    # ALFENAS ADICIONAR CAMPOS PARA O SQLSERVER
    usar_selo_sql_server = Cartorio.objects.all().values_list(
        "usar_selo_sql_server",
        flat=True,
    )[0]
    if usar_selo_sql_server == "S":
        # VERIFICAR A QUANTIDADE SELOS - SQL SERVER
        # selos_do_pedido_fb = protocolo.quantidade_selo_sqlserver if usar_selo_sql_server == "S" else []
        selos_do_pedido_fb = []
    else:
        selos_do_pedido_fb = firebird.get_selos_do_pedido_fb(pedido_id=pedido_id, db=db)

    for pedido_item_fb in pedido_itens_fb:
        ato_fb = firebird.get_ato_fb_por_id(
            ato_id=pedido_item_fb["CHAVE_ATOS"],
            db=db,
        )

        ato = models.AtoPratica.objects.criar_do_fb(ato_fb)

        pedido_item = models.PedidoItem.objects.criar_do_fb(
            pedido_fb,
            pedido_item_fb,
            ato,
        )

        # EXISTEM INTES A IMPORTAR
        if pedido_item:
            # CASO SEJA IMPORTACAO PARCIAL - NAO IMPORTAR LIVRO 2 OU 3
            if (
                tipo_importacao != TipoImportacao.Parcial
                and pedido_item_fb["TIPO_IMOVEL"]
                and pedido_item_fb["NUMERO_IMOVEL"]
            ):
                if pedido_item_fb["TIPO_IMOVEL"] != "A":
                    if pedido_item_fb:
                        importar_livro2.converter_livro02_do_fb(pedido_item_fb, db)
                else:
                    importar_livro3.importar_livro03_do_fb(pedido_item_fb, db)

            if selos_do_pedido_fb:
                models.SeloEletronico.objects.criar_selos_obtidos_do_fb(
                    pedido_item,
                    selos_do_pedido_fb,
                )
            else:
                logger.warning("Não há selos para importar")

    andamentos_fb = firebird.get_andamentos_do_protocolo_no_fb(
        protocolo_id=protocolo_id,
        db=db,
    )

    if andamentos_fb:
        andamentos: list[models.Livro01Andamento] = (
            protocolo.criar_andamentos_obtidos_do_fb(andamentos_fb, db)
        )

        if andamentos:
            for andamento in andamentos:
                # protocolo.atualizar_status_pelo_andamento(andamento_id=andamento.pk)
                if andamento.tipo_andamento_id:
                    andamento.encerrar_eventos()
        else:
            msg = (
                f"Não foi possível criar os andamentos do protocolo {numero_protocolo}"
            )
            logger.warning(msg)

    # importanto caixa e gravando no postgress
    registros_caixa_fb = firebird.get_registros_caixa_do_pedido_fb(pedido_id, db)

    # GRAVAR CAIXA
    # if salvar_caixa:
    if registros_caixa_fb:
        print("Obter registros de caixa do pedido fb: ", len(registros_caixa_fb))

    if registros_caixa_fb:
        # Financeiro.objects.deletar_por_pedido_id(pedido_id)
        models.Financeiro.objects.criar_registros_de_caixa_obtidos_do_fb(
            pedido,
            registros_caixa_fb,
        )

    # # VERIFICAR O HISTORICO DO FINANCEIRO
    # historico_financeiro = models.FinanceiroHistorico.objects.filter(
    #     pedido_id=protocolo.pedido_id
    # )
    # if historico_financeiro:
    #     copiar_historico_financeiro(historico_financeiro)

    # NECESSARIO VERIFICAR SE O VALOR CADASTRADO NO FINANCEIRO EQUIVALE A DIFERENCA LANCADA NO PROTOCOLO DO SISTEMA ANTERIOR
    # valor_depositado_sistema_antigo = pedido_fb["VALORACERTO"]

    # valor_financeiro_sistema_atual = models.Financeiro.objects.filter(
    #     pedido_id=protocolo.pedido_id,
    # ).aggregate(Sum("valor_transacao"))["valor_transacao__sum"]

    # if valor_depositado_sistema_antigo is None:
    #     valor_depositado_sistema_antigo = 0

    # if valor_financeiro_sistema_atual is None:
    #     valor_financeiro_sistema_atual = 0

    # valor_diferenca_sistema_antigo = (
    #     valor_depositado_sistema_antigo - valor_financeiro_sistema_atual
    # )

    # if valor_diferenca_sistema_antigo != 0:
    #     # FINALIZAR NO PRIME PARA NAO TER PROBLEMAS ENQUANTO SINCRONIZA O SISTEMA ANTIGO
    #     data_entrada = str(pedido_fb["DATAENTRADA"])[:10]
    #     gerar_financeiro(
    #         protocolo.pedido.id,
    #         valor_diferenca_sistema_antigo,
    #         data_entrada,
    #     )

    # ATUALIZAR FASES DO PROTOCOLO
    protocolo.atualizar_fases()

    # ENCERRAR TODA A AGENDA DO PROTOCOLO
    protocolo.apagar_eventos()

    # GERAR A AGENDA DO PROTOCOLO
    protocolo.criar_eventos()

    # ATUALIZAR O EMAIL BUSCANDO O PROTOCOLO ANTERIOR ATUAL DO PROTOCOLO
    if str(pedido_fb["EMAIL"]) != "":
        try:
            verificar_protocolo_email(pedido_fb["EMAIL"], numero_protocolo)
        except:
            pass

    # # ordenar os andamentos por data desc
    # andamentos_fb_desc = sorted(andamentos_fb, key=lambda x: x["DATA"], reverse=True)

    # for andamento_fb in andamentos_fb_desc:
    #     # ERRO AO GRAVAR
    #     if andamento_fb["CHAVE_FUNCIONARIOS"]:
    #         models.Colaborador.checar_ou_criar_colaborador(andamento_fb["CHAVE_FUNCIONARIOS"])

    #     if andamento_fb["CHAVE_SERVICOS_ANDAMENTOS"]:
    #         protocolo.encerrar_evento_pela_data_do_andamento(andamentos)

    #         tipo_status_protocolo: TipoStatusProtocolo = None
    #         tipo_evento = None
    #         # TODO: verificar como obter o status IDcorreto e o efeito dele na agenda
    #         if tipo_status_protocolo:
    #             evento = models.Event.criar_evento_na_agenda(
    #                 numero_protocolo=numero_protocolo,
    #                 tipo_status_protocolo=tipo_status_protocolo,
    #                 data_finalizado=andamento_fb["DATA"],
    #                 colaborador_id=andamento_fb["CHAVE_FUNCIONARIOS"],
    #             )
    #             if evento:
    #                 logger.info(f"Evento {tipo_evento} criado para o protocolo {numero_protocolo}")

    # ATUALIZAR NO EVENTO O QUE JA FOI FINALIZADO
    # encerrar_evento_pela_data_do_andamento(
    #     protocolo_id,
    #     andamento_fb["CHAVE_SERVICOS_ANDAMENTOS"],
    #     andamento_fb["DATA"],
    # )
    # resincronizar anexos
    # protocolo.get_anexos()

    # protocolo.atualizar_colaborador_atual_pelo_ultimo_andamento()

    logger.info(
        f"********* IMPORTAÇÃO DO PROTOCOLO {numero_protocolo} FINALIZADA *********",
    )
    print("   ")
    print("   ")
    print("   ")

    return (protocolo, msg)


def get_andamentos_colaborador_no_dia_fb(
    colaborador_id: int,
    db: FbConnection,
) -> list:
    query = f"""
        SELECT DISTINCT(P.NROORDEM)
        FROM   ANDAMENTOS A, PROTOCOLOS P
        WHERE  A.CHAVE_PROTOCOLOS = P.CHAVE_PROTOCOLOS
        AND    A.CHAVE_FUNCIONARIOS_DESTINO = {colaborador_id}
        AND    A.DATA >= CURRENT_DATE
        """

    db = FbConnection() if db is None else db
    resultados = db.execute_query(query)
    return resultados if resultados else []


# PASSA O OBJETO PROTOCOLO
def get_quantidade_andamentos_no_fb(
    protocolo: "Livro01Protocolo",
    db: FbConnection,
) -> int:
    query = f"""
        SELECT COUNT(A.DATA)
        FROM   ANDAMENTOS A, PROTOCOLOS P
        WHERE  A.CHAVE_PROTOCOLOS = P.CHAVE_PROTOCOLOS
        AND    P.NROORDEM = {protocolo.numero_protocolo}
        """

    resultado = db.execute_query(query)
    return resultado[0] if resultado else 0


# PASSA O OBJETO PROTOCOLO
def get_ultima_data_de_andamentos_no_fb(
    protocolo: "Livro01Protocolo",
    db: FbConnection,
) -> datetime.date:
    query = """
        SELECT MAX(A.DATA)
        FROM   ANDAMENTOS A, PROTOCOLOS P
        WHERE  A.CHAVE_PROTOCOLOS = P.CHAVE_PROTOCOLOS
        AND    P.NROORDEM = ?
        """
    parametros = (protocolo.numero_protocolo,)
    resultado = db.execute_query(query, parametros)
    return resultado[0] if resultado else None


def get_quantidade_de_andamentos_no_fb(
    pedido_id: int,
    tipo_andamento_id: int,
    db: FbConnection,
) -> int:
    if pedido_id is None or tipo_andamento_id is None:
        return 0

    query = f"""
        SELECT COUNT(A.CHAVE_PROTOCOLOS)
        FROM ANDAMENTOS A, PROTOCOLOS P
        WHERE A.CHAVE_PROTOCOLOS = P.CHAVE_PROTOCOLOS
        AND P.CHAVE_PEDIDOS = {pedido_id}
        AND A.CHAVE_SERVICOS_ANDAMENTOS = {tipo_andamento_id}
        AND A.DATA > CURRENT_DATE
        """

    resultado = db.execute_query(query)
    return resultado[0] if resultado else 0


# Remover o item do pedido
def firebird_remover_pedido_item(pedido_item_id: int, db: FbConnection) -> None:
    if pedido_item_id is None:
        msg = "O ID do pedido_item não pode ser nulo"
        raise ValueError(msg)

    command = (
        f" DELETE FROM PEDIDOS_ITENS WHERE CHAVE_PEDIDOS_ITENS = {pedido_item_id!s}"
    )

    db.execute_command(command)


def exportar_andamento_para_firebird(andamento: "Livro01Andamento") -> None:
    if andamento:
        with FbConnection() as db:
            criar_andamento_no_fb(andamento, db)


def criar_andamento_fb(
    pedido_id: int,
    colaborador_id: int,
    tipo_andamento_id: int,
    colaborador_encaminhado_id: int,
    db: FbConnection,
) -> int:
    quantidade_de_andamentos = get_quantidade_de_andamentos_no_fb(
        pedido_id=pedido_id,
        tipo_andamento_id=tipo_andamento_id,
        db=db,
    )

    db = FbConnection() if db is None else db

    query = (
        f"SELECT CHAVE_PROTOCOLOS FROM PROTOCOLOS WHERE CHAVE_PEDIDOS = {pedido_id!s}"
    )
    andamentos_seq = db.sequence("ANDAMENTOS_SEQ")
    andamento_id_fb = andamentos_seq.proximo

    protocolo_id_fb = db.execute_query(query)[0]["CHAVE_PROTOCOLOS"]

    if not protocolo_id_fb:
        logger.warning(f"Protocolo não encontrado para o pedido {pedido_id}")
        msg = "Protocolo não encontrado"
        raise ValueError(msg)

    if protocolo_id_fb and quantidade_de_andamentos["COUNT"] == 0:
        comando = """ INSERT INTO ANDAMENTOS (CHAVE_ANDAMENTOS, CHAVE_PROTOCOLOS,
                                            DATA, CHAVE_FUNCIONARIOS, CHAVE_FUNCIONARIOS_DESTINO,
                                            CHAVE_SERVICOS_ANDAMENTOS)
                        VALUES(GEN_ID("ANDAMENTOS_SEQ", 1),
                            :CHAVE_PROTOCOLOS,
                            :DATA, :CHAVE_FUNCIONARIOS, :CHAVE_FUNCIONARIOS_DESTINO,
                            :CHAVE_SERVICOS_ANDAMENTOS);"""

        comando = comando.replace(":CHAVE_PROTOCOLOS", str(protocolo_id_fb))
        comando = comando.replace(":DATA", "CURRENT_TIMESTAMP")
        comando = comando.replace(
            ":CHAVE_FUNCIONARIOS_DESTINO",
            str(colaborador_encaminhado_id or 0) or str(colaborador_id or 0),
        )
        comando = comando.replace(":CHAVE_FUNCIONARIOS", str(colaborador_id))
        comando = comando.replace(":CHAVE_SERVICOS_ANDAMENTOS", str(tipo_andamento_id))

        # # GRAVAR TEXTO  EXTERNO
        # if arquivo_docx:
        #     gravar_texto_andamento_no_fb(andamento_id_fb=andamento_id_fb, arquivo_docx=arquivo_docx, db=db)

        # GRAVANDO NO BANCO DE DADOS FIREBIRD - VIA SECAO COMMIT
        db.execute_command(comando)

        # Atualizar pelo andamento
        pedido = models.Pedido.objects.get(pk=pedido_id)
        protocolo = pedido.protocolo
        protocolo.atualizar_status_pelo_andamento(andamento_id=andamento_id_fb)

    return protocolo_id_fb


def gravar_texto_andamento_no_fb(
    andamento_id_fb,
    arquivo_docx,
    db: FbConnection,
) -> None:
    arquivo_docx = str(arquivo_docx)
    arquivo_rtf = str(arquivo_docx).replace(".docx", ".rtf")

    command = (
        "python /utils/gerar_arquivo_word_rtf.py "
        + str(arquivo_docx)
        + " "
        + str(arquivo_rtf)
    )

    # Execute o comando e capture a saída padrão e a saída de erro
    process = subprocess.Popen(
        command,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    stdout, stderr = process.communicate()

    with open(arquivo_rtf, "rb") as docx_file:
        docx_content = docx_file.read()

    comando = " UPDATE ANDAMENTOS SET OBSERVACAO=(?) WHERE CHAVE_ANDAMENTOS = " + str(
        andamento_id_fb,
    )

    db.execute_command(command=comando, params=(docx_content,))


def get_numero_do_protocolo_no_fb_pelo_id_do_pedido(
    pedido_id: int,
    db: FbConnection,
) -> int:
    query = " SELECT CHAVE_PROTOCOLOS FROM PROTOCOLOS WHERE CHAVE_PEDIDOS = " + str(
        pedido_id,
    )

    firebird.get_sequence_firebird("ANDAMENTOS_SEQ", db)["GEN_ID"]

    if db is None:
        db = FbConnection()
        resultado = db.execute_query(query)
        db.close()
    else:
        resultado = db.execute_query(query)

    return resultado["CHAVE_PROTOCOLOS"] if resultado else 0


def criar_andamento_no_fb(andamento: "Livro01Andamento", db: FbConnection) -> None:
    logger.info(f"Criar andamento no firebird: {andamento}")

    if andamento is None:
        msg = "O andamento não pode ser nulo"
        raise ValueError(msg)

    command = f"""
            INSERT INTO ANDAMENTOS (CHAVE_ANDAMENTOS,
                                    CHAVE_PROTOCOLOS,
                                    DATA,
                                    CHAVE_FUNCIONARIOS,
                                    CHAVE_FUNCIONARIOS_DESTINO,
                                    CHAVE_SERVICOS_ANDAMENTOS,
                                    OBSERVACAO)
            VALUES(GEN_ID("ANDAMENTOS_SEQ", 1),
                    (SELECT CHAVE_PROTOCOLOS FROM PROTOCOLOS WHERE NROORDEM = {andamento.protocolo.numero_protocolo}),
                    CURRENT_TIMESTAMP,
                    {andamento.colaborador_id},
                    {andamento.colaborador_destino_id},
                    {andamento.tipo_andamento_id},
                    ?);
            """

    parametros = (andamento.texto_rtf,)

    # GRAVANDO NO BANCO DE DADOS FIREBIRD - VIA SECAO COMMIT
    try:
        db.execute_command(command, parametros)
    except IntegrityError:
        logger.warning("Funcionario não existe. Usando o usuario padrão.")
        andamento.colaborador_id = models.Configuracao.obter(
            "funcionario_id_sistema_antigo",
            999998,
        )
        criar_andamento_no_fb(andamento, db)


# Pesquisar por numero em aberto
def importar_protocolos_de_hoje():
    print("IMPORTAÇÃO: Obtendo protocolos do dia para importar")

    # Exibir os protocolos
    data_entrada = timezone.now().date().strftime("%Y-%m-%d")
    with FbConnection() as db:
        protocolos_fb = firebird.get_protocolos_por_data_de_entrada_fb(
            data_entrada,
            data_entrada,
            db,
        )

    print("IMPORTAÇÃO: Quantidade de protocolos para importar: ", len(protocolos_fb))

    if protocolos_fb:
        return importar_protocolos_fb(protocolos_fb)

    return []


# LISTAR OS ANDAMENTOS - PELO ID
def importar_andamentos_protocolos_pelo_id(
    protocolo: "Livro01Protocolo",
    tipo_importacao: TipoImportacao,
    db: FbConnection,
) -> list:
    if db is None:
        db = FbConnection()

    with transaction.atomic():
        try:
            logger.info(f"Deletar todos os andamentos do protocolo: {protocolo}")
            models.Livro01Andamento.objects.deletar_por_protocolo(protocolo.pk)

            print(
                "Iniciar a Atualizar o andamento. OBTER A CHAVE_PROTOCOLOS: ",
            )
            # OBTER A CHAVE_PROTOCOLOS
            protocolo_id_firebird = firebird.get_protocolo_fb(
                protocolo.numero_protocolo,
                db,
            )["CHAVE_PROTOCOLOS"]

            try:
                andamentos_protocolo_fb = firebird.get_andamentos_do_protocolo_no_fb(
                    protocolo_id=protocolo_id_firebird,
                    db=db,
                )
            except Exception:
                msg = f"Erro ao obter andamento do protocolo: {protocolo_id_firebird!s}"
                logger.exception(msg)
                logger.exception(msg)
                raise

            print(
                "Quantidade de andamentos: ",
                len(andamentos_protocolo_fb),
            )

            # ANDAMENTOS
            if andamentos_protocolo_fb:
                print("Existem no FIREBIRD: ", len(andamentos_protocolo_fb))

                for andamento_fb in andamentos_protocolo_fb:
                    # VERIFICAR SE O PROTOCOLO JA FOI IMPORTADO
                    print("Importar o protocolo", protocolo)

                    # CASO EXISTA O PROTOCOLO ATUALIZAR O ANDAMENTO DELE
                    if protocolo:
                        try:
                            print(
                                "ANDAMENTOS: Iniciar atualização do andamento. Protocolo: ",
                                protocolo,
                            )
                            protocolo.criar_andamento_obtido_no_firebird(andamento_fb)
                            print(
                                "atualizar_andamentos_protocolos",
                                protocolo,
                                andamento_fb["CHAVE_ANDAMENTOS"],
                            )
                        except Exception:
                            msg = f"Erro ao atualizar andamento {andamento_fb['CHAVE_ANDAMENTOS']} do protocolo: {protocolo}"
                            logger.exception(msg)
                            logger.exception(msg)
                            raise

                    # NAO EXISTIR IMPORTA DO ZERO - TOTAL
                    else:
                        print(
                            "Importar o protocolo completo pelo andamento ",
                            protocolo,
                        )
                        protocolo_fb = firebird.get_protocolo_fb_por_id(protocolo.pk)

                        if protocolo_fb:
                            protocolo = importar_protocolo_por_numero_fb(
                                numero_protocolo=protocolo,
                                tipo_importacao=tipo_importacao,
                                db=db,
                            )

                            print(
                                "Finalizou protocolo completo pelo andamento ",
                                protocolo,
                            )

            # protocolo.atualizar_colaborador_atual_pelo_ultimo_andamento()

            # db.commit()
            # db.close()
        except Exception:
            # db.rollback()
            db.close()
            msg = f"Erro ao importar andamentos do protocolo. Protocolo: {protocolo}"
            logger.exception(msg)
            logger.exception(msg)
            raise

    return andamentos_protocolo_fb


# LISTAR OS ANDAMENTOS
def importar_andamentos_modificados(db: FbConnection):
    """OBTEM TODOS OS PROTOCOLOS MODIFICANDOS APOS A ULTIMA SINCRONIZAÇÃO."""
    andamentos_protocolo_fb = firebird.get_andamentos_protocolos_modificados(db=db)

    if not andamentos_protocolo_fb:
        print("Nenhum andamento modificado encontrado para importar")
        return []

    for andamento_fb in andamentos_protocolo_fb:
        protocolo: Livro01Protocolo = models.Livro01Protocolo.objects.filter(
            pk=andamento_fb["CHAVE_PROTOCOLOS"],
        ).first()

        # CASO EXISTA O PROTOCOLO ATUALIZAR O ANDAMENTO DELE
        if protocolo:
            try:
                protocolo.criar_andamento_obtido_no_firebird(andamento_fb)
            except Exception:
                logger.exception(
                    f"Erro ao atualizar andamento do protocolo: {protocolo}",
                )
                raise

            # ATUALIZAR O STATUS DO PROTOCOLO PELO ANDAMENTO
            try:
                protocolo.atualizar_status_pelo_andamento(
                    andamento_id=andamento_fb["CHAVE_ANDAMENTOS"],
                )
            except Exception:
                logger.exception(f"Erro ao atualizar status do protocolo: {protocolo}")
                raise
        # NAO EXISTIR IMPORTA DO ZERO - TOTAL
        else:
            protocolo_fb = firebird.get_protocolo_fb_por_id(
                protocolo_id=andamento_fb["CHAVE_PROTOCOLOS"],
                db=db,
            )
            if protocolo_fb:
                protocolo = importar_protocolo_por_numero_fb(
                    numero_protocolo=protocolo_fb["NROORDEM"],
                    tipo_importacao=None,
                    db=db,
                )

    return andamentos_protocolo_fb


# Pesquisar por numero em aberto
def importar_protocolos_modificados_ultimos_2_dias() -> list:
    protocolos_dos_ultimos_dois_dias = (
        firebird.get_protocolos_modificados_ultimos_2_dias()
    )

    # Acessando os valores da coluna 'NROORDEM'
    valores_nroordem = [dado["NROORDEM"] for dado in protocolos_dos_ultimos_dois_dias]
    protocolos_dos_ultimos_dois_dias = valores_nroordem

    protocolo_importados = []

    db = FbConnection()

    for numero_protocolo in protocolos_dos_ultimos_dois_dias:
        try:
            db.begin_transaction()
            protocolo = importar_protocolo_por_numero_fb(
                numero_protocolo=numero_protocolo,
                tipo_importacao=None,
                db=db,
            )
            db.commit()
        except Exception:
            logger.exception(f"ERRO IMPORTAR PROTOCOLO: {numero_protocolo}")
            continue

    db.close()

    protocolo_importados.append(protocolo)

    return protocolo_importados if protocolo_importados else []


def importar_protocolos_fb_modificados_na_ultima_hora() -> list:
    protocolos_modificados_fb = firebird.get_protocolos_modificados_na_ultima_hora()

    if protocolos_modificados_fb:
        return importar_protocolos_fb(protocolos_modificados_fb)

    return []


def importar_protocolos_fb(protocolos_fb) -> list:
    protocolos_numeros_importados = []

    db = FbConnection()
    db.begin_transaction()

    for x, protocolo in enumerate(protocolos_fb):
        numero_protocolo = next(iter(protocolo.values()))

        if numero_protocolo:
            print(
                f"IMPORTAÇÃO: Protocolo: {numero_protocolo}, {x}/{len(protocolos_fb)}",
            )

            try:
                firebird.importar_protocolo_por_numero_fb(
                    numero_protocolo=numero_protocolo,
                    tipo_importacao=None,
                    db=db,
                )
                db.commit()
            except Exception:
                logger.exception(f"ERRO IMPORTAR PROTOCOLO: {numero_protocolo}")
                continue

            protocolos_numeros_importados.append(numero_protocolo)

            print("#Protocolo importado: ", protocolos_numeros_importados)

    db.close()
    return protocolos_numeros_importados


def importar_protocolos_fb_ou_atualizar_andamento(protocolos_fb) -> list:
    protocolos_numeros_importados = []

    db = FbConnection()
    db.begin_transaction()

    for x, protocolo in enumerate(protocolos_fb):
        numero_protocolo = next(iter(protocolo.values()))

        if numero_protocolo:
            print(
                f"IMPORTAÇÃO: Protocolo: {numero_protocolo}, {x}/{len(protocolos_fb)}",
            )

            # LOCALIZAR PROTOCOLO
            livro01 = models.Livro01Protocolo.objects.filter(
                numero_protocolo=numero_protocolo,
            ).first()

            try:
                if livro01:
                    livro01.verificar_andamentos_sistema_antigo()
                else:
                    firebird.importar_protocolo_por_numero_fb(
                        numero_protocolo=numero_protocolo,
                        tipo_importacao=None,
                        db=db,
                    )

                db.commit()
            except Exception:
                logger.exception(f"ERRO IMPORTAR PROTOCOLO: {numero_protocolo}")
                continue

            protocolos_numeros_importados.append(numero_protocolo)

            print("#Protocolo importado: ", protocolos_numeros_importados)

    db.close()
    return protocolos_numeros_importados


# Pesquisar por numero em aberto
def importar_protocolos_modificados_30_dias() -> list:
    db = firebird.FbConnection()
    protocolos_fb = firebird.get_protocolos_fb_modificados_nos_ultimos_30_dias(db)

    # return importar_protocolos_fb(protocolos_fb)
    return importar_protocolos_fb_ou_atualizar_andamento(protocolos_fb)


def importar_protocolos_por_data_entrada(
    data_inicio,
    data_fim,
    user_id,
    db: FbConnection,
) -> list:
    protocolos_fb = firebird.get_protocolos_por_data_de_entrada_fb(
        data_inicio,
        data_fim,
        db,
    )

    # Acessando os valores da coluna 'NROORDEM'
    numeros = [dado["NROORDEM"] for dado in protocolos_fb]

    numeros = sorted(set(numeros))

    if numeros:
        # ENVIAR POR NUMERO PARA A IMPORTACAO COMPLETA NAO QUEBRAR
        return importar_protocolos_fb(protocolos_fb)

    return []


# verificar se os andamentos estao sincronizados com sistema antigo
def pesquisar_andamentos_do_protocolo_pela_data(protocolo, data):
    ultima_data = data.strftime("%Y-%m-%d %H:%M:%S")

    andamentos_fb = get_ultimos_andamentos_no_fb(
        protocolo.numero_protocolo,
        ultima_data,
    )

    # CADASTRAR OS ANDAMENTOS PARA SINCRONIZAR COM O SISTEMA ATUAL
    if andamentos_fb:
        db = firebird.FbConnection()
        protocolo.criar_andamentos_obtidos_do_fb(andamentos_fb, db)


# Importar o protocolo pelo numero
def importar_protocolos_por_colaborador(colaborador_id, db: FbConnection) -> None:
    # OBTER LISTA DE TODOS OS ANDAMENTOS QUE FORAM ALTERADOS PARA O COLABORADOR
    andandentos_firebird = get_andamentos_colaborador_no_dia_fb(colaborador_id, db)

    if not andandentos_firebird:
        return

    for indice, protocolo in enumerate(andandentos_firebird):
        logger.info(
            f"\n\n\n IMPORTAÇÃO: Protocolo {protocolo}: {indice}/{len(andandentos_firebird)} #########",
        )

        importar_protocolo_por_numero_fb(
            numero_protocolo=protocolo["NROORDEM"],
            tipo_importacao=None,
            db=db,
        )

        logger.info(f"IMPORTAÇÃO CONCLUIDA: Protocolo {protocolo} #########")

    # # Pesquisar por COLABORADOR DISTRIBUIDO OU ENCAMINHADO
    # protocolos = models.Livro01Protocolo.objects.filter(
    #     colaborador=colaborador_id,
    #     data_finalizado__isnull=True,
    # ).order_by("-data_protocolo")

    # for indice, protocolo in enumerate(protocolos):
    #     if protocolo:
    #         logger.info(f"\n\n\n IMPORTAÇÃO: Protocolo {protocolo}: {indice}/{len(protocolos)} #########")

    #     try:
    #         importar_protocolo_por_numero_fb(numero_protocolo=protocolo.numero_protocolo)
    #         logger.info(f"IMPORTAÇÃO CONCLUIDA: Protocolo {protocolo} #########")
    #     except Exception:
    #         # logger.error(f"ERRO ao importar o protocolo: {protocolo} ")
    #         continue


# IMPORTAR ITEM UNICO E GRAVAR
def importar_e_criar_pedido_item_do_fb(
    pedido_id,
    pedido_id_item,
    db: FbConnection,
) -> list["PedidoItem"]:
    db = FbConnection() if db is None else db
    itens_do_fb = firebird.get_pedido_itens_fb(
        pedido_id=pedido_id,
        pedido_id_item=pedido_id_item,
        db=db,
    )

    # FILTRAR PEDIDO - ORIGINAL
    pedido_fb = firebird.get_pedido_fb(pedido_id=pedido_id, db=db)

    db.close()

    pedidos_item = []
    for pedido_item_fb in itens_do_fb:
        with transaction.atomic():
            try:
                # pedido_item = PedidoItem.objects.criar_do_fb(pedido_item_fb)
                ato_fb = firebird.get_ato_fb_por_id(
                    ato_id=pedido_item_fb["CHAVE_ATOS"],
                    db=db,
                )
                ato = models.AtoPratica.objects.criar_do_fb(ato_fb)
                pedido_item = models.PedidoItem.objects.criar_do_fb(
                    pedido_fb,
                    pedido_item_fb,
                    ato,
                )
                pedidos_item.append(pedido_item)
            except Exception:
                logger.exception("ERRO")
                continue

    print(
        "IMPORTAÇÃO: Pedido Item importado: ",
        pedido_id_item,
        " do pedido: ",
        pedido_id,
    )

    return pedidos_item


def get_data_atual():
    data_atual = timezone.now()
    return data_atual.strftime(settings.DATE_FORMAT_STR)


def get_numeros_inteiro(variavel):
    resultado = re.search(r"\d+", variavel)
    if resultado:
        return int(resultado.group())
    else:
        msg = f"Nenhum número inteiro encontrado em: {variavel}"
        raise ValueError(msg)


# Gerando a agenda do protocolo


# Obter a data de entrada dos protocolos
def verificar_protocolos_vencendo(
    opcao,
    protocolo: "Livro01Protocolo",
    fase_agenda,
    # data_protocolo,
    # data_finalizado,
    # status_id,
    # protocolos_id,
) -> None:
    # Gerando os colaboradores
    # Lista com o colaborador_id que sao vinculados ao PROTOCOLO VENCENDO
    if str(opcao) == "V":
        usuarios_com_protocolo_vencendo = Usuario.get_usuarios_com_protocolo_vencendo()
        for _usuario in usuarios_com_protocolo_vencendo:
            protocolo.criar_evento(
                fase_agenda=fase_agenda,
                # fase_atual,
                # data_agenda,
                # data_finalizado,
                # colaborador_id,
                # status_id,
                # protocolos_id,
                exibir_agenda="N",
                informar_prazo=False,
            )
    else:
        pass


# Gerar a agenda do protocolo


def importar_protocolos_por_data_entrada_nao_importado(data_inicio, data_fim):
    # TODOS OS PROTOCOLOS - FIREBIRD - Chamada da função que retorna uma lista de dicionários
    with FbConnection() as db:
        protocolos_base_firebird = firebird.get_protocolos_por_data_de_entrada_fb(
            data_inicio,
            data_fim,
            db,
        )

    # PROTOCOLOS JA IMPORTADO - POSTREGSQL
    protocolos_base_postgresql = models.Livro01Protocolo.objects.filtrar_por_data(
        data_inicio,
        data_fim,
    )

    # Extração dos valores da coluna NROORDEM
    protocolos_firebird = [int(x["NROORDEM"]) for x in protocolos_base_firebird]

    # REVER CODIGO
    # Extração dos valores da coluna NUMERO PROTOCOLO
    protocolos_postgresql = [
        (int(str(protocolo.get("protocolo", "0")).replace(".", "")))
        for protocolo in protocolos_base_postgresql
    ]

    # Supondo que 'protocolos_postgresql' seja uma lista de objetos ou dicionários - retirar protocolos ja importados e unificar as listas
    protocolos_a_importar = list(set(protocolos_firebird) - set(protocolos_postgresql))

    # Verificar se existem protocolos para importar
    if not protocolos_a_importar:
        return None  # Não há protocolos novos para importar

    # Importar protocolos não importados
    resultados_importacao = []
    db = FbConnection()
    for numero_protocolo in protocolos_a_importar:
        try:
            db.begin_transaction()
            protocolo = importar_protocolo_por_numero_fb(
                numero_protocolo=numero_protocolo,
                tipo_importacao=None,
                db=db,
            )
            db.commit()
            resultados_importacao.append(protocolo.numero_protocolo)
        except Exception:
            logger.exception(f"ERRO AO IMPORTAR PROTOCOLO: {numero_protocolo}")
            continue
    db.close()

    return resultados_importacao


# Inicio do Programa para converter
@transaction.atomic
def importar_somente_protocolo_por_numero_do_fb(
    numero_protocolo: int,
    db: FbConnection,
) -> tuple["Livro01Protocolo", str]:
    protocolo: Livro01Protocolo = None
    protocolo_fb = firebird.get_protocolo_fb(numero_protocolo, db) or None

    if protocolo_fb:
        protocolo_id = protocolo_fb["CHAVE_PROTOCOLOS"] or 0
        pedido_id = protocolo_fb["CHAVE_PEDIDOS"] or 0

        if not protocolo_id or protocolo_id == 0:
            msg = "Protocolo não encontrado no Firebird"
            print(msg)
            raise ValueError(msg)
            return None, msg

        if not pedido_id or pedido_id == 0:
            msg = "Pedido não encontrado no Firebird"
            print(msg)
            raise ValueError(msg)
            return None, msg

        pedido_fb = firebird.get_pedido_fb(pedido_id, db) or None

        if not pedido_fb:
            msg = "Pedido não encontrado no Firebird"
            print(msg)
            raise ValueError(msg)
            return None, msg

        # LIMPAR OS DADOS DO POSTGRESS DO PROTOCOLO ATUAL
        models.CheckListRealizado.objects.deletar_por_pedido_id(pedido_id)
        models.Livro02Texto.objects.deletar_por_pedido_id(pedido_id)
        models.PedidoItemImovel.objects.deletar_por_pedido_id(pedido_id)
        models.PedidoParteAto.objects.deletar_por_pedido_id(pedido_id)
        # PedidoItem.objects.deletar_por_pedido_id(pedido_id)
        models.ProtocoloEmFase.objects.deletar_por_pedido_id(pedido_id)
        models.Pedido.objects.deletar_por_pedido_id(pedido_id)

        pedido = models.Pedido.objects.criar_do_fb(pedido_fb)

        if not pedido:
            msg = "Pedido não foi criado"
            print(msg)
            raise ValueError(msg)
            return None, msg

        selos_do_pedido_fb = firebird.get_selos_do_pedido_fb(pedido_id, db)

        models.PedidoParte.objects.criar_do_fb(pedido, pedido_fb)

        # Livro01Protocolo.objects.deletar_por_pedido_id(pedido_id)
        protocolo = models.Livro01Protocolo.criar_ou_atualizar_protocolo_obtido_do_fb(
            protocolo_fb,
        )

        if not protocolo:
            msg = "Protocolo não foi criado"
            print(msg)
            raise ValueError(msg)
            return None, msg

        pedido_itens_fb = firebird.get_pedido_itens_fb(
            pedido_id=pedido.pk,
            pedido_id_item=None,
            db=db,
        )

        if not pedido_itens_fb:
            msg = "Não há itens de pedido para importar"
            print(msg)
            raise ValueError(msg)
            return protocolo, msg

        models.PedidoItem.objects.deletar_por_pedido_id(pedido_id)

        for pedido_item_fb in pedido_itens_fb:
            ato_fb = firebird.get_ato_fb_por_id(
                ato_id=pedido_item_fb["CHAVE_ATOS"],
                db=db,
            )

            ato = models.AtoPratica.objects.criar_do_fb(ato_fb)
            pedido_item = models.PedidoItem.objects.criar_do_fb(
                pedido,
                pedido_item_fb,
                ato,
            )

            if pedido_item:
                # GRAVAR_LIVRO_2 OU 3
                if pedido_item_fb["TIPO_IMOVEL"] and pedido_item_fb["NUMERO_IMOVEL"]:
                    # if pedido_item_fb["TIPO_IMOVEL"] != "A":
                    #     if pedido_item_fb:
                    #         importar_livro2.converter_livro02_do_fb(pedido_item_fb)
                    # else:
                    #     importar_livro03_do_fb(pedido_item_fb)
                    pass

                models.SeloEletronico.objects.criar_selos_obtidos_do_fb(
                    pedido_item,
                    selos_do_pedido_fb,
                )

        andamentos_fb = firebird.get_andamentos_do_protocolo_no_fb(
            protocolo_id=protocolo_id,
            db=db,
        )

        if andamentos_fb:
            # Livro01Andamento.objects.deletar_por_protocolo(protocolo)
            andamentos = protocolo.criar_andamentos_obtidos_do_fb(andamentos_fb, db)

            if andamentos:
                for andamento in andamentos:
                    protocolo.atualizar_status_pelo_andamento(andamento_id=andamento.pk)
                    if andamento.tipo_andamento_id:
                        andamento.encerrar_eventos()

                # importanto caixa e gravando no postgress
                registros_caixa_fb = firebird.get_registros_caixa_do_pedido_fb(
                    pedido_id,
                    db,
                )

                if registros_caixa_fb:
                    # Financeiro.objects.deletar_por_pedido_id(pedido_id)
                    models.Financeiro.objects.criar_registros_de_caixa_obtidos_do_fb(
                        pedido,
                        registros_caixa_fb,
                    )

                # ATUALIZAR FASES DO PROTOCOLO
                protocolo.atualizar_fases()

                # APAGAR TODA A AGENDA DO PROTOCOLO
                protocolo.apagar_eventos()

                # GERAR A AGENDA DO PROTOCOLO
                # protocolo.criar_eventos()

                # protocolo.atualizar_colaborador_atual_pelo_ultimo_andamento()

    logger.info(
        f"********* IMPORTAÇÃO DO PROTOCOLO {numero_protocolo} FINALIZADA *********",
    )
    print("   ")
    print("   ")
    print("   ")

    return None


def atualizar_data_sincronismo() -> None:
    # Subtrai 3 horas do horário atual
    horario_ajustado = timezone.now() - timedelta(hours=3)
    Cartorio.objects.update_or_create(
        id=1,
        defaults={"data_hora_sincronismo": horario_ajustado},
    )


# ATUALIZANDO DADOS NO FIREBIRD
def atualizar_dados_firebird(command) -> None:
    try:
        db = FbConnection()
        db.begin_transaction()
        db.execute_command(command)
        db.commit()
        db.close()
    except Exception as e:
        db.rollback()
        db.close()
        print("Erro ao atualizar firebird: ", command, e)


def executar_em_thread(command: str) -> None:
    # Cria uma nova thread para executar a função
    thread = threading.Thread(target=atualizar_dados_firebird, args=(command,))
    thread.start()
    # Você pode escolher se deseja aguardar a conclusão da thread ou não.
    # Se quiser aguardar, use thread.join()


# VERIFICAR SE EXISTE ANTERIOR OU POSTERIO
def verificar_protocolo_email(text_protocolo, numero_protocolo):
    from apps.home.views import atualizar_protocolo_anterior

    try:
        text_protocolo = text_protocolo.strip()
    except:
        text_protocolo = None

    # APENAS SE EXISTE TEXTO
    if text_protocolo:
        if "Anterior" in text_protocolo:
            protocolo_posterior = text_protocolo.split("Anterior:")[1].strip()
            if protocolo_posterior:
                atualizar_protocolo_anterior(protocolo_posterior, numero_protocolo)
        elif "Posterior" in text_protocolo:
            protocolo_anterior = text_protocolo.split("Posterior:")[1].strip()
            if protocolo_anterior:
                atualizar_protocolo_anterior(numero_protocolo, protocolo_anterior)
        else:
            print('A string não contém "Anterior" ou "Posterior".')


# VERIFICAR SE EXISTE ANTERIOR OU POSTERIO
def gerar_financeiro(pedido_id, valor_diferenca_sistema_antigo, data_entrada):
    models.Financeiro.criar_financeiro_despesa_receita(
        pedido_id=pedido_id,
        pedido_certidao_id=None,
        tipo_transacao_id=1,
        tipo_categoria_financeira_id=1,
        tipo_operacao_financeira_id=1,
        colaborador_id=1,
        colaborador_confirmado_id=None,
        data_transacao=data_entrada,
        data_original_transacao=None,
        valor_transacao=valor_diferenca_sistema_antigo,
        dadp="N",
        imposto_renda="N",
        descricao="DEPOSITO DE PAGAMENTO",
        user_id=1,
        quantidade_parcelas=1,
        recorrencia_id=1,
    )


# Inserir múltiplos registros de uma vez
def copiar_historico_financeiro(historico_queryset):
    # Lista para armazenar novos objetos Financeiro
    novos_financeiros = []

    # Criar novos objetos Financeiro a partir dos objetos FinanceiroHistorico
    for historico in historico_queryset:
        novo_financeiro = models.Financeiro(
            pedido=historico.pedido,
            data_transacao=historico.data_transacao,
            descricao=historico.descricao,
            tipotransacao=historico.tipotransacao,
            tipodocumento=historico.tipodocumento,
            valor_transacao=historico.valor_transacao,
            cheque=historico.cheque,
            pedido_certidao_id=historico.pedido_certidao_id,
            colaborador=historico.colaborador,
            numero_protocolo_ec=historico.numero_protocolo_ec,
            numero_pedido_certidao=historico.numero_pedido_certidao,
            colaborador_confirmado=historico.colaborador_confirmado,
            dadp=historico.dadp,
            imposto_renda=historico.imposto_renda,
            tipo_transacao=historico.tipo_transacao,
            tipo_operacao_financeira=historico.tipo_operacao_financeira,
            tipo_categoria_financeira=historico.tipo_categoria_financeira,
            ativo=historico.ativo,
            data_transacao_cancelado=historico.data_transacao_cancelado,
            valor_transacao_cancelado=historico.valor_transacao_cancelado,
            colaborador_transacao_cancelado=historico.colaborador_transacao_cancelado,
            descricao_cancelado=historico.descricao_cancelado,
            numero_parcela=historico.numero_parcela,
            quantidade_parcela=historico.quantidade_parcela,
            data_original_transacao=historico.data_original_transacao,
            nome_interessado=historico.nome_interessado,
            data_transacao_colaborador_confirmado=historico.data_transacao_colaborador_confirmado,
        )
        novos_financeiros.append(novo_financeiro)

    # Usar bulk_create para inserir os novos registros na tabela Financeiro
    with transaction.atomic():
        models.Financeiro.objects.bulk_create(novos_financeiros)

    print("FinanceiroHistorico copiado para Financeiro")


# Inicio do Programa para converter - IMPORTAR QUANDO TIVER CERTEZA QUE NAO TEM O PROTOCOLO NO SISTEMA
@transaction.atomic
def importar_protocolo_por_numero_fb_apenas_inserir(
    numero_protocolo: int,
    tipo_importacao: TipoImportacao,
    db: FbConnection,
) -> tuple["Livro01Protocolo", str]:
    logger.info(f"PROTOCOLO: Importar do fb por numero {numero_protocolo}")

    # ATUALIZAR SOMENTE CAIXA - PELA TELA SEPARADA
    cartorio_model = apps.get_model("cartorios", "Cartorio")
    atualizar_somente_caixa = cartorio_model.objects.all().values_list(
        "atualizar_somente_caixa",
        flat=True,
    )[0]
    str(atualizar_somente_caixa) != "S"

    tipo_importacao = tipo_importacao or TipoImportacao.Total

    protocolo: Livro01Protocolo = None

    protocolo_fb = firebird.get_protocolo_fb(numero_protocolo, db) or None

    if not protocolo_fb:
        msg = f"Protocolo {numero_protocolo} não encontrado no Firebird"
        logger.warning(msg)
        raise ValueError(msg)
        return protocolo, msg

    protocolo_id = protocolo_fb["CHAVE_PROTOCOLOS"] or 0
    pedido_id = protocolo_fb["CHAVE_PEDIDOS"] or 0

    pedido_fb = firebird.get_pedido_fb(pedido_id, db) or None

    if not pedido_fb:
        msg = f"Pedido {pedido_id} não encontrado no Firebird"
        logger.warning(msg)
        raise ValueError(msg)
        return protocolo, msg

    # INICIO GRAVANDO
    pedido: models.Pedido = models.Pedido.objects.criar_do_fb(pedido_fb=pedido_fb)

    if not pedido:
        msg = f"Pedido {pedido_id} não foi criado"
        logger.warning(msg)
        raise ValueError(msg)
        return protocolo, msg

    pedido.criar_partes_do_fb(pedido_fb)

    protocolo = models.Livro01Protocolo.criar_ou_atualizar_protocolo_obtido_do_fb(
        protocolo_fb,
    )

    if not protocolo:
        msg = f"Protocolo {numero_protocolo} não foi criado"
        logger.warning(msg)
        raise ValueError(msg)
        return None, msg

    pedido_itens_fb = firebird.get_pedido_itens_fb(
        pedido_id=pedido.pk,
        pedido_id_item=None,
        db=db,
    )

    if not pedido_itens_fb:
        msg = f"Pedido {pedido_id} não possui itens"
        logger.warning(msg)
        raise ValueError(msg)
        return protocolo, msg

    # ALFENAS ADICIONAR CAMPOS PARA O SQLSERVER
    usar_selo_sql_server = Cartorio.objects.all().values_list(
        "usar_selo_sql_server",
        flat=True,
    )[0]
    if usar_selo_sql_server == "S":
        selos_do_pedido_fb = []
    else:
        selos_do_pedido_fb = firebird.get_selos_do_pedido_fb(pedido_id=pedido_id, db=db)

    for pedido_item_fb in pedido_itens_fb:
        ato_fb = firebird.get_ato_fb_por_id(
            ato_id=pedido_item_fb["CHAVE_ATOS"],
            db=db,
        )

        ato = models.AtoPratica.objects.criar_do_fb(ato_fb)

        pedido_item = models.PedidoItem.objects.criar_do_fb(
            pedido_fb,
            pedido_item_fb,
            ato,
        )

        # EXISTEM INTES A IMPORTAR
        if pedido_item:
            # CASO SEJA IMPORTACAO PARCIAL - NAO IMPORTAR LIVRO 2 OU 3
            if (
                tipo_importacao != TipoImportacao.Parcial
                and pedido_item_fb["TIPO_IMOVEL"]
                and pedido_item_fb["NUMERO_IMOVEL"]
            ):
                if pedido_item_fb["TIPO_IMOVEL"] != "A":
                    if pedido_item_fb:
                        importar_livro2.converter_livro02_do_fb(pedido_item_fb, db)
                else:
                    importar_livro3.importar_livro03_do_fb(pedido_item_fb, db)

            if selos_do_pedido_fb:
                models.SeloEletronico.objects.criar_selos_obtidos_do_fb(
                    pedido_item,
                    selos_do_pedido_fb,
                )
            else:
                logger.warning("Não há selos para importar")

    andamentos_fb = firebird.get_andamentos_do_protocolo_no_fb(
        protocolo_id=protocolo_id,
        db=db,
    )

    if andamentos_fb:
        andamentos: list[models.Livro01Andamento] = (
            protocolo.criar_andamentos_obtidos_do_fb(andamentos_fb, db)
        )

        if andamentos:
            for andamento in andamentos:
                if andamento.tipo_andamento_id:
                    andamento.encerrar_eventos()
        else:
            msg = (
                f"Não foi possível criar os andamentos do protocolo {numero_protocolo}"
            )
            logger.warning(msg)

    # ATUALIZAR FASES DO PROTOCOLO
    protocolo.atualizar_fases()

    # ENCERRAR TODA A AGENDA DO PROTOCOLO
    protocolo.apagar_eventos()

    # GERAR A AGENDA DO PROTOCOLO
    protocolo.criar_eventos()

    # ATUALIZAR O EMAIL BUSCANDO O PROTOCOLO ANTERIOR ATUAL DO PROTOCOLO
    if str(pedido_fb["EMAIL"]) != "":
        try:
            verificar_protocolo_email(pedido_fb["EMAIL"], numero_protocolo)
        except:
            pass

    logger.info(
        f"********* IMPORTAÇÃO DO PROTOCOLO {numero_protocolo} FINALIZADA *********",
    )
    print("   ")
    print("   ")
    print("   ")

    return protocolo or None


# FILTRAR OS ANDAMENTOS DO PROTOCOLO
def get_ultimos_andamentos_no_fb(numero_protocolo: int, data: datetime.date):
    db = firebird.FbConnection()

    query = f"""
        SELECT A.*
        FROM   ANDAMENTOS A, PROTOCOLOS P
        WHERE  A.CHAVE_PROTOCOLOS = P.CHAVE_PROTOCOLOS
        AND    P.NROORDEM = {numero_protocolo}
        AND    A.DATA >= '{data}'
        """

    resultado = db.execute_query(query)
    return resultado if resultado else None
